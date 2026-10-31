"""Opt-in Gemini proposal probe on a synthetic screenshot. Executes ZERO returned actions."""
import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from gdhq import live
from gdhq.database import Database
from gdhq.gemini import probe_fixture


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--config', type=Path)
    parser.add_argument('--trial-home', type=Path)
    parser.add_argument('--confirm', default='')
    args = parser.parse_args()
    if args.confirm != 'GEMINI_SYNTHETIC_PROPOSAL':
        print(json.dumps({'status': 'NOT_EXECUTED', 'model_called': False,
                          'requires': 'Explicit config, new trial-home and --confirm GEMINI_SYNTHETIC_PROPOSAL'}))
        return 0
    db = None
    try:
        if not args.config or not args.trial_home: raise ValueError('Missing configuration')
        config = live.clean_config(json.loads(args.config.read_text(encoding='utf-8')))
        if config.get('protocol') != 'gemini_interactions' or config.get('browser_fixture') is not True:
            raise ValueError('Explicit Gemini synthetic screenshot authorization required')
        live.auth(config)  # No empty key or implicit public subscription access.
        from playwright.sync_api import sync_playwright
        # Refuse any existing directory: never migrate or reuse an owner database.
        args.trial_home.mkdir(mode=0o700, parents=True, exist_ok=False)
        db = Database(args.trial_home)
        live.init(db)
        db.set_setting('paused', False)
        cid = live.import_connectors(db, config)['ids'][0]
        live.approve_connectors(db, [cid], True)
        row = db.one('SELECT * FROM live_connectors WHERE id=?', (cid,))
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            try: report = probe_fixture(db, None, row, browser)
            finally: browser.close()
        report['reserved_usd'] = config['max_cost_usd']
        report['cost_note'] = 'Local conservative reservation, not measured invoice or provider hard cap'
        report['calls'] = db.all('SELECT id,reserved_usd,status FROM connector_calls ORDER BY id')
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return 0 if report['status'] == 'PROPOSAL_RECEIVED_NOT_EXECUTED' else 1
    except Exception:
        calls = db.all('SELECT id,reserved_usd,status FROM connector_calls ORDER BY id') if db else []
        print(json.dumps({'status': 'BLOCKED', 'actions_executed': 0,
                          'model_called': None if calls else False, 'calls': calls,
                          'reason': 'Configuration, credential, browser or provider unavailable; inspect local prerequisites'}))
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
