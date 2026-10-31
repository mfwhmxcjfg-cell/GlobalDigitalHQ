"""Run a synthetic, offline browser trial, never a paid model call."""
import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from gdhq.computer_use_trial import run_browser_trial


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run-offline-fixture', action='store_true')
    args = parser.parse_args()
    if not args.run_offline_fixture:
        print(json.dumps({'status': 'NOT_EXECUTED', 'model_called': False,
                          'next': 'Use --run-offline-fixture for synthetic local browser validation only'}))
        return 0
    try:
        from playwright.sync_api import sync_playwright
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            try: report = run_browser_trial(browser)
            finally: browser.close()
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return 0 if report['status'] == 'HARNESS_VERIFIED_MODEL_NOT_TESTED' else 1
    except Exception:
        print(json.dumps({'status': 'BLOCKED', 'reason': 'Browser trial failed or Playwright/Chromium unavailable',
                          'model_called': False}))
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
