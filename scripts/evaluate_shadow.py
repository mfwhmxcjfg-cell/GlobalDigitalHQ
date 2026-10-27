"""Offline CLI: never reads credentials, contacts providers or modifies routing."""
import argparse
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from gdhq.shadow_evaluation import prepare, evaluate


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--suite', required=True)
    parser.add_argument('--observations')
    args = parser.parse_args()
    try:
        suite = json.loads(Path(args.suite).read_text(encoding='utf-8'))
        if args.observations:
            result = evaluate(suite, json.loads(Path(args.observations).read_text(encoding='utf-8')))
        else:
            result = prepare(suite)
            # Presence only. Never print, copy or test the secret value.
            result['credential_presence_in_this_process'] = bool(os.environ.get('OPENAI_API_KEY'))
        print(json.dumps(result, indent=2, ensure_ascii=False, allow_nan=False))
        return 1 if result['status'] == 'REJECTED' else 0
    except (ValueError, OSError, TypeError, KeyError):
        # Do not echo paths, prompts, JSON fragments or credentials on failure.
        print(json.dumps({'status': 'BLOCKED', 'reason': 'Invalid or incomplete evaluation inputs; see docs/TERRA_SHADOW.md'}))
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
