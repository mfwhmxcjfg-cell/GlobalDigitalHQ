"""Read-only model inventory; no Service startup, migrations, secrets or network calls."""
import argparse
from contextlib import closing
import json
from pathlib import Path
import re
import sqlite3
import sys

ROOT = Path(__file__).resolve().parent.parent
if __package__ in (None, ''):
    sys.path.insert(0, str(ROOT))
from gdhq.model_lifecycle import catalog, model_status


def inspect(database=None, root=ROOT):
    policy = catalog()
    result = {'catalog_verified_at': policy['verified_at'], 'source': policy['source'],
              'repository': [], 'runtime': [], 'database': 'NOT_SUPPLIED',
              'network_called': False, 'modified': False,
              'limitations': ['Liste partielle et datée ; absence dans la liste ne prouve pas la disponibilité.',
                              'Routage réel des proxys et modèles locaux non vérifié.',
                              'Réservations de coût déclarées, jamais assimilées à une facture.']}
    retired = {m for e in policy['retirements'] for m in e['models']}
    # Scan executable/configuration areas, excluding docs, fixtures and this policy itself.
    pattern = re.compile(r'(?<![\w.-])(?:' + '|'.join(re.escape(m) for m in sorted(retired, key=len, reverse=True)) + r')(?![\w.-])')
    for area in ('gdhq', 'scripts', 'seed', '.github/workflows'):
        for path in sorted((Path(root)/area).rglob('*')):
            if path.suffix not in ('.py', '.json', '.yml', '.yaml') or path.name == 'model_lifecycle.json':
                continue
            if path.is_symlink():
                continue
            for number, line in enumerate(path.read_text(encoding='utf-8').splitlines(), 1):
                for model in sorted(set(pattern.findall(line))):
                    result['repository'].append({'file': path.relative_to(root).as_posix(), 'line': number, 'model': model,
                                                 'status': 'REFERENCE_REQUIRES_REVIEW'})
    if database is None:
        return result
    path = Path(database).resolve()
    if not path.is_file():
        result['database'] = 'NOT_FOUND'
        return result
    try:
        with closing(sqlite3.connect(path.as_uri()+'?mode=ro', uri=True)) as con:
            con.execute('PRAGMA query_only=ON')
            tables = {r[0] for r in con.execute("SELECT name FROM sqlite_master WHERE type='table'")}
            if 'live_connectors' not in tables:
                result['database'] = 'SCHEMA_UNSUPPORTED'
                return result
            for cid, approved, raw in con.execute('SELECT id,approved,config FROM live_connectors ORDER BY id'):
                c = json.loads(raw)
                if not isinstance(c, dict):
                    raise ValueError('Invalid connector configuration')
                if c.get('kind') != 'MODEL':
                    continue
                # Never output config, URL, key names, prompts or connector names.
                result['runtime'].append({'connector_id': cid, 'approved': bool(approved),
                                          'lifecycle': model_status(c)})
            result['database'] = 'READ_ONLY_OK'
            if 'connector_calls' in tables:
                result['cost_reservations'] = [dict(zip(('connector_id', 'calls', 'reserved_usd'), r))
                    for r in con.execute('SELECT connector_id,count(*),sum(reserved_usd) FROM connector_calls GROUP BY connector_id')]
    except (sqlite3.Error, ValueError, TypeError, KeyError):
        result['database'] = 'UNREADABLE_OR_INVALID'
    return result


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--database', help='Chemin explicite vers global.sqlite3 (lecture seule)')
    args = parser.parse_args(argv)
    report = inspect(args.database)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    if report['database'] not in ('NOT_SUPPLIED', 'READ_ONLY_OK'):
        return 2
    return int(bool(report['repository']) or any(x['approved'] and x['lifecycle']['status'] in
               ('RETIRED', 'MODE_RETIRED', 'MODE_DEPRECATED') for x in report['runtime']))


if __name__ == '__main__':
    sys.exit(main())
