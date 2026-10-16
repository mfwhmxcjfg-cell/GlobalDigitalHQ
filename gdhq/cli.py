import argparse,json,sys
from pathlib import Path
from .service import Service
from .auditing import run_audit
from .migration import inspect,import_projects

def main(argv=None):
    p=argparse.ArgumentParser(description='Global Digital HQ Next - noyau local')
    p.add_argument('command',choices=['serve','audit','verify','backup','inspect-legacy','import-legacy','models'])
    p.add_argument('--source',default='',help='Base source en lecture seule')
    p.add_argument('--host',default='127.0.0.1')
    p.add_argument('--port',default=8824,type=int)
    a=p.parse_args(argv)
    if a.command in ('inspect-legacy','import-legacy') and not a.source:p.error('--source obligatoire')
    if a.command=='inspect-legacy': print(json.dumps(inspect(a.source),ensure_ascii=False,indent=2));return 0
    s=Service()
    if a.command=='serve':
        if a.host!='127.0.0.1':p.error('Serveur limité à 127.0.0.1')
        from .webapp import serve
        serve(s,a.host,a.port);return 0
    if a.command=='audit': print(json.dumps(run_audit(s.db,s.home,s.provider),ensure_ascii=False,indent=2));return 0
    if a.command=='verify':
        from .builder import check_project
        print(json.dumps({'database_integrity':s.db.integrity(),'roles':len(__import__('gdhq.roles',fromlist=['ROLES']).ROLES),'mode':'NO_SPEND','projects':len(s.projects())},ensure_ascii=False,indent=2));return 0
    if a.command=='backup':
        from datetime import datetime,timezone
        path=Path(s.home)/'backups'/('global-'+datetime.now(timezone.utc).strftime('%Y%m%d-%H%M%S')+'.sqlite3')
        print(json.dumps(s.db.backup(path),ensure_ascii=False,indent=2));return 0
    if a.command=='import-legacy':print(json.dumps(import_projects(s.db,a.source),ensure_ascii=False,indent=2));return 0
    if a.command=='models':
        try:print(json.dumps({'models':s.provider.models()},ensure_ascii=False));return 0
        except Exception as e:print(str(e),file=sys.stderr);return 2
    return 1

if __name__=='__main__':sys.exit(main())
