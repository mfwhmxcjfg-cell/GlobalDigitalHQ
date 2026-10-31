import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

from gdhq import live
from gdhq.database import Database
from gdhq.gemini import URL, interact, probe_fixture, proposal_summary
from gdhq.model_council import RemoteModel
from gdhq.public_http import ConnectorError


class GeminiTests(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.db = Database(Path(tmp.name))
        live.init(self.db)
        self.db.set_setting('paused', False)
        self.config = {'name': 'Gemini trial', 'kind': 'MODEL', 'url': URL,
                       'model': 'gemini-3.8-flash', 'protocol': 'gemini_interactions',
                       'secret_env': 'TEST_GEMINI_KEY', 'daily_calls': 1,
                       'max_cost_usd': 0.1, 'daily_budget_usd': 0.1, 'browser_fixture': True}
        cid = live.import_connectors(self.db, self.config)['ids'][0]
        live.approve_connectors(self.db, [cid], True)
        self.row = self.db.one('SELECT * FROM live_connectors WHERE id=?', (cid,))
        self.env = patch.dict(os.environ, {'TEST_GEMINI_KEY': 'mock-key-private'})
        self.env.start()
        self.addCleanup(self.env.stop)

    def response(self, **extra):
        return {'status': 'completed', 'steps': [
            {'type': 'thought', 'summary': 'DO NOT EXPOSE'},
            {'type': 'model_output', 'content': [{'type': 'text', 'text': 'Answer mock-key-private'}]}], **extra}

    def test_official_endpoint_and_auth_only(self):
        valid = live.clean_config(self.config)
        self.assertEqual((valid['auth_header'], valid['auth_prefix']), ('x-goog-api-key', ''))
        for changes in ({'url': 'https://other.example/v1/interactions'}, {'url': URL+'?key=abc'},
                        {'secret_env': ''}, {'auth_prefix': 'Bearer '}, {'local': True},
                        {'browser_fixture': 'true'}, {'protocol': 'openai'}):
            with self.subTest(changes=changes), self.assertRaises(ValueError):
                live.clean_config({**self.config, **changes})

    def test_text_council_stateless_no_tools_private_thoughts(self):
        with patch('gdhq.gemini.fetch', return_value=(json.dumps(self.response()).encode(), {})) as transport:
            result = RemoteModel(self.db, None, self.row).chat('system', 'public sources', max_tokens=100)
        self.assertNotIn('mock-key-private', result)
        self.assertNotIn('DO NOT EXPOSE', result)
        url, headers, payload = transport.call_args.args
        self.assertEqual(url, URL)
        self.assertEqual(headers, {'x-goog-api-key': 'mock-key-private'})
        self.assertFalse(payload['store']); self.assertFalse(payload['stream'])
        self.assertNotIn('tools', payload); self.assertNotIn('previous_interaction_id', payload)
        self.assertEqual(payload['generation_config']['max_output_tokens'], 100)

    def test_missing_key_no_reservation_or_network(self):
        with patch.dict(os.environ, {'TEST_GEMINI_KEY': ''}), patch('gdhq.gemini.fetch') as transport:
            with self.assertRaises(ConnectorError): interact(self.db, None, self.row, '', '')
        transport.assert_not_called()
        self.assertEqual(self.db.one('SELECT count(*) AS n FROM connector_calls')['n'], 0)

    def test_revocation_pause_and_revision_fail_before_network(self):
        for state in ('revoked', 'paused', 'changed'):
            with self.subTest(state=state), patch('gdhq.gemini.fetch') as transport:
                if state == 'revoked': live.approve_connectors(self.db, [self.row['id']], False)
                elif state == 'paused': self.db.set_setting('paused', True)
                else: live.import_connectors(self.db, {**self.config, 'daily_calls': 2})
                with self.assertRaises((ConnectorError, PermissionError)):
                    interact(self.db, None, self.row, '', '')
                transport.assert_not_called()
                self.db.set_setting('paused', False)

    def test_failed_call_consumes_budget_and_sanitizes_errors(self):
        with patch('gdhq.gemini.fetch', side_effect=RuntimeError('mock-key-private')) as transport:
            with self.assertRaises(ConnectorError) as error: interact(self.db, None, self.row, '', '')
            self.assertNotIn('mock-key-private', str(error.exception))
            with self.assertRaises(ConnectorError): interact(self.db, None, self.row, '', '')
        self.assertEqual(transport.call_count, 1)
        self.assertEqual(self.db.one('SELECT status FROM connector_calls')['status'], 'FAILED')

    def test_incomplete_and_tool_results_not_council_answers(self):
        for response in (self.response(status='incomplete'), self.response(steps=[{'type': 'function_call'}])):
            with patch('gdhq.gemini.interact', return_value=response):
                with self.assertRaises(ConnectorError): RemoteModel(self.db, None, self.row).chat('', '')

    def test_fixture_one_call_no_actions_or_arguments_in_report(self):
        browser = MagicMock()
        page = browser.new_context.return_value.new_page.return_value
        page.screenshot.return_value = b'\x89PNG\r\n\x1a\nfixture'
        response = {'status': 'requires_action', 'steps': [{'type': 'function_call', 'name': 'click',
                     'arguments': {'x': 100, 'y': 120, 'intent': 'PRIVATE INTENT'}}]}
        with patch('gdhq.gemini.fetch', return_value=(json.dumps(response).encode(), {})) as transport:
            result = probe_fixture(self.db, None, self.row, browser)
        self.assertEqual(result['status'], 'PROPOSAL_RECEIVED_NOT_EXECUTED')
        self.assertEqual(result['actions_executed'], 0)
        page.mouse.click.assert_not_called(); page.keyboard.type.assert_not_called()
        browser.new_context.return_value.close.assert_called_once()
        payload = transport.call_args.args[2]
        self.assertEqual(payload['input'][1]['mime_type'], 'image/png')
        self.assertTrue(payload['tools'][0]['enable_prompt_injection_detection'])
        self.assertNotIn('PRIVATE INTENT', json.dumps(result))
        self.assertNotIn('arguments', json.dumps(result))

    def test_screenshot_requires_separate_approval_and_size_limit(self):
        for png in (b'not png', b'\x89PNG\r\n\x1a\n'+b'x'*262144):
            with patch('gdhq.gemini.fetch') as transport, self.assertRaises(ValueError):
                interact(self.db, None, self.row, '', '', fixture_png=png)
            transport.assert_not_called()
        cid = live.import_connectors(self.db, {**self.config, 'browser_fixture': False})['ids'][0]
        row = self.db.one('SELECT * FROM live_connectors WHERE id=?', (cid,))
        with patch('gdhq.gemini.fetch') as transport, self.assertRaises(ConnectorError):
            interact(self.db, None, row, '', '', fixture_png=b'\x89PNG\r\n\x1a\nfixture')
        transport.assert_not_called()

    def test_unsafe_proposals_blocked_never_executed(self):
        for step in ({'type': 'function_call', 'name': 'navigate', 'arguments': {'url': 'https://example.org'}},
                     {'type': 'function_call', 'name': 'click', 'arguments': {'x': float('nan'), 'y': 1}},
                     {'type': 'function_call', 'name': 'click', 'arguments': {'x': 1, 'y': 1}, 'safety_decision': 'require_confirmation'},
                     {'type': 'mcp_server_tool_call'}, {'type': 'function_call', 'name': 'click', 'arguments': []}):
            report = proposal_summary({'status': 'requires_action', 'steps': [step]})
            self.assertEqual(report['status'], 'PROPOSAL_BLOCKED')
            self.assertEqual(report['actions_executed'], 0)


if __name__ == '__main__': unittest.main()
