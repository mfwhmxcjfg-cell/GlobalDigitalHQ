"""Read-only Windows runtime diagnostics. Never include keys, prompts or source contents."""
import argparse,json,sqlite3,sys,os,importlib.util
from pathlib import Path
from contextlib import closing
from urllib.request import build_opener,ProxyHandler,HTTPRedirectHandler,Request


def inspect(home):
    home=Path(home);report={'installed':(home/'app/gdhq/live.py').is_file(),'playwright_python':bool(importlib.util.find_spec('playwright')),'browser_directory_present':(home/'browsers').is_dir(),'server':'NOT_REACHABLE'}
    class NoRedirect(HTTPRedirectHandler):
        def redirect_request(self,*args,**kwargs):return None
    try:
        with build_opener(ProxyHandler({}),NoRedirect()).open(Request('http://127.0.0.1:8824/health'),timeout=3) as response:
            data=json.loads(response.read(5000));report['server']=data.get('status');report['version']=data.get('version')
    except Exception:pass
    path=home/'data/global.sqlite3'
    if not path.is_file():report['database']='NOT_FOUND';return report
    try:
        with closing(sqlite3.connect(path.resolve().as_uri()+'?mode=ro',uri=True)) as con:
            report['database']='READABLE'
            report['connectors']=[{'id':r[0],'approved':bool(r[1]),'last_status':r[2]} for r in con.execute('SELECT id,approved,last_status FROM live_connectors')]
            report['project_states']=[{'id':r[0],'state':r[1]} for r in con.execute('SELECT id,state FROM projects')]
            report['open_resource_requests']=con.execute("SELECT count(*) FROM resource_requests WHERE status='OPEN'").fetchone()[0]
            report['evidence_count']=con.execute('SELECT count(*) FROM live_evidence').fetchone()[0]
            report['latest_evidence_at']=con.execute('SELECT max(observed_at) FROM live_evidence').fetchone()[0]
            report['calls']=[{'status':r[0],'count':r[1]} for r in con.execute('SELECT status,count(*) FROM connector_calls GROUP BY status')]
    except Exception as exc:report['database']='UNAVAILABLE_'+type(exc).__name__
    return report

if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('--home',default='D:\\GlobalDigitalHQ');args=ap.parse_args()
    print(json.dumps(inspect(args.home),ensure_ascii=False,indent=2))
