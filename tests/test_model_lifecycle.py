import hashlib
import json
import sqlite3
import tempfile
import unittest
from contextlib import closing
from datetime import date
from pathlib import Path
from unittest.mock import patch

from gdhq import live
from gdhq.database import Database
from gdhq.model_council import RemoteModel
from gdhq.model_lifecycle import ensure_model_available, model_status
from gdhq.public_http import ConnectorError
from scripts.audit_models import inspect, main


def config(model='gpt-image-1', **extra):
    return {'name': 'OpenAI test', 'kind': 'MODEL', 'url': 'https://api.openai.com/v1/chat/completions',
            'model': model, 'protocol': 'openai', 'max_cost_usd': .1, 'daily_budget_usd': 1, **extra}


class ModelLifecycleTests(unittest.TestCase):
    def test_retirement_boundary_and_aliases(self):
        for model in ('gpt-image-1', 'gpt-4', 'gpt-4-turbo', 'o3-mini', 'o4-mini', 'gpt-3.5-turbo'):
            self.assertEqual(model_status(config(model), date(2026, 10, 22))['status'], 'DEPRECATED')
            self.assertEqual(model_status(config(model), date(2026, 10, 23))['status'], 'RETIRED')

    def test_current_unknown_and_local_do_not_claim_availability(self):
        self.assertEqual(model_status(config('gpt-6.1-sol'))['status'], 'NOT_LISTED_AVAILABILITY_UNVERIFIED')
        self.assertEqual(model_status(config(url='http://127.0.0.1:1234/v1/chat/completions', local=True))['status'], 'LOCAL_OR_ROUTER_UNVERIFIED')
        self.assertEqual(model_status(config(url='https://router.example/v1/chat/completions'))['status'], 'PROVIDER_UNVERIFIED')
        self.assertEqual(model_status(config(url='https://api.openai.com.attacker.example/v1/chat/completions'))['status'], 'PROVIDER_UNVERIFIED')
        ensure_model_available(config(url='http://127.0.0.1:1234/v1/chat/completions', local=True))

    def test_finetune_ids_and_exact_matching(self):
        self.assertEqual(model_status(config('ft:gpt-4-0613:org:custom:id'))['status'], 'RETIRED')
        for model in ('ft:babbage-002:org:custom:id', 'ft:davinci-002:org:custom:id', 'ft:gpt-4.1-nano-2025-04-14:org:custom:id'):
            self.assertEqual(model_status(config(model))['status'], 'RETIRED')
        self.assertEqual(model_status(config('gpt-image-1-mini'))['status'], 'NOT_LISTED_AVAILABILITY_UNVERIFIED')

    def test_import_batch_is_atomic_when_retired_model_is_present(self):
        with tempfile.TemporaryDirectory() as t:
            db = Database(Path(t)); live.init(db)
            with self.assertRaisesRegex(ValueError, 'retiré'):
                live.import_connectors(db, [{'name':'Good source', 'kind':'WEB', 'url':'https://example.org'}, config()])
            self.assertEqual(db.all('SELECT * FROM live_connectors'), [])

    def test_existing_retired_config_never_reserves_or_calls_network(self):
        with tempfile.TemporaryDirectory() as t:
            db = Database(Path(t)); live.init(db); db.set_setting('paused', False)
            c = config(secret_env='TEST_API_KEY')
            cid = db.write('INSERT INTO live_connectors(name,config,approved) VALUES(?,?,1)', ('Legacy', json.dumps(c)))
            row = db.one('SELECT * FROM live_connectors WHERE id=?', (cid,))
            with patch('gdhq.model_council.fetch') as network:
                with self.assertRaisesRegex(ConnectorError, 'retiré'):
                    RemoteModel(db, None, row).chat('system', 'public data')
                network.assert_not_called()
            self.assertEqual(db.all('SELECT * FROM connector_calls'), [])
            self.assertTrue(db.one('SELECT approved FROM live_connectors')['approved'])

    def test_read_only_inventory_preserves_runtime_and_hides_config(self):
        with tempfile.TemporaryDirectory() as t:
            path = Path(t)/'runtime.sqlite3'
            with closing(sqlite3.connect(path)) as c, c:
                c.execute('CREATE TABLE live_connectors(id INTEGER, approved INTEGER, config TEXT)')
                c.execute('CREATE TABLE connector_calls(connector_id INTEGER, reserved_usd REAL)')
                c.execute('INSERT INTO live_connectors VALUES(1,1,?)', (json.dumps(config(secret_env='PRIVATE_SECRET_KEY',purpose='private prompt')),))
                c.executemany('INSERT INTO connector_calls VALUES(1,?)', [(.25,), (.25,), (.25,), (.25,)])
            before = hashlib.sha256(path.read_bytes()).hexdigest()
            report = inspect(path)
            self.assertEqual(report['database'], 'READ_ONLY_OK')
            self.assertEqual(report['runtime'][0]['lifecycle']['status'], 'RETIRED')
            self.assertEqual(report['cost_reservations'][0]['reserved_usd'], 1)
            self.assertEqual(report['cost_reservations'][0]['calls'], 4)
            for private in ('PRIVATE_SECRET_KEY', 'private prompt', 'api.openai.com'):
                self.assertNotIn(private, json.dumps(report))
            self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(), before)
            self.assertFalse(report['modified']); self.assertFalse(report['network_called'])

    def test_missing_database_is_not_created_or_reported_successful(self):
        with tempfile.TemporaryDirectory() as t:
            path = Path(t)/'missing.sqlite3'
            self.assertEqual(inspect(path)['database'], 'NOT_FOUND')
            self.assertFalse(path.exists())
            with patch('builtins.print'):
                self.assertEqual(main(['--database', str(path)]), 2)

    def test_runtime_model_guard_is_reported_without_migration(self):
        with tempfile.TemporaryDirectory() as t:
            db = Database(Path(t)); live.init(db)
            db.write('INSERT INTO live_connectors(name,config) VALUES(?,?)', ('Old', json.dumps(live.clean_config(config('current-test-model')))))
            c = live.clean_config(config('current-test-model')); c['model'] = 'gpt-4'
            db.write('UPDATE live_connectors SET config=?', (json.dumps(c),))
            self.assertEqual(live.connector_rows(db)[0]['model_lifecycle']['status'], 'RETIRED')
            cid = db.one('SELECT id FROM live_connectors')['id']
            with self.assertRaisesRegex(ValueError, 'retiré'):
                live.approve_connectors(db, [cid], True)
            self.assertFalse(db.one('SELECT approved FROM live_connectors')['approved'])

    def test_failed_reservations_survive_reimport_and_database_reopen(self):
        with tempfile.TemporaryDirectory() as t:
            db = Database(Path(t)); live.init(db); db.set_setting('paused', False)
            cid = live.import_connectors(db, config('current-test-model', daily_calls=4, max_cost_usd=.25))['ids'][0]
            live.approve_connectors(db, [cid], True)
            row = db.one('SELECT * FROM live_connectors WHERE id=?', (cid,))
            for _ in range(4):
                call = live.reserve(db, row)
                db.write("UPDATE connector_calls SET status='FAILED' WHERE id=?", (call,))
            reopened = Database(Path(t)); live.init(reopened)
            live.import_connectors(reopened, config('current-test-model', daily_calls=4, max_cost_usd=.25))
            row = reopened.one('SELECT * FROM live_connectors WHERE id=?', (cid,))
            with self.assertRaisesRegex(ConnectorError, 'Quota|budget'):
                live.reserve(reopened, row)
            totals = inspect(reopened.path)['cost_reservations'][0]
            self.assertEqual(totals, {'connector_id': cid, 'calls': 4, 'reserved_usd': 1})


if __name__ == '__main__':
    unittest.main()
