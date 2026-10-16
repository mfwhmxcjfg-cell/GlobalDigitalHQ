"""Hardened localhost HTTP server. No web framework or internet installation needed."""
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlsplit,parse_qs
import html,json,secrets,threading,traceback
from .settings import ROOT
from .builder import read_preview
from .auditing import run_audit
from .governance import decision

class AppServer(ThreadingHTTPServer):
    daemon_threads=True
    allow_reuse_address=True
    def __init__(self,address,service):
        self.service=service
        self.owner_token=secrets.token_urlsafe(40)
        super().__init__(address,Handler)

class Handler(BaseHTTPRequestHandler):
    server_version='GlobalHQNext/1.0'
    def log_message(self,format,*args):
        # no request data or credentials in logs
        pass
    def reply(self,body,status=200,mime='application/json; charset=utf-8',policy=None):
        if not isinstance(body,bytes):
            if isinstance(body,str):body=body.encode('utf-8')
            else:body=json.dumps(body,ensure_ascii=False).encode('utf-8')
        self.send_response(status)
        for key,value in [('Content-Type',mime),('Content-Length',str(len(body))),('Cache-Control','no-store'),('X-Content-Type-Options','nosniff'),('X-Frame-Options','DENY' if policy is None else 'SAMEORIGIN'),('Referrer-Policy','no-referrer'),('Cross-Origin-Resource-Policy','same-origin' if policy is None else 'cross-origin'),('Content-Security-Policy',policy or "default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data:; connect-src 'self'; frame-src 'self'; frame-ancestors 'none'; form-action 'none'; base-uri 'none'")]:
            self.send_header(key,value)
        self.end_headers()
        self.wfile.write(body)
    def authorized_host(self):
        return self.headers.get('Host','')==f'127.0.0.1:{self.server.server_port}'
    def authorized(self):
        return secrets.compare_digest(self.headers.get('X-GDHQ-Token',''),self.server.owner_token)
    def error(self,message,status=400):self.reply({'ok':False,'error':str(message)},status)
    def do_GET(self):
        if not self.authorized_host():return self.error('Hôte non autorisé',403)
        route=urlsplit(self.path).path
        s=self.server.service
        try:
            if route=='/':
                page=(ROOT/'web'/'index.html').read_text(encoding='utf-8').replace('__OWNER_TOKEN__',html.escape(self.server.owner_token,quote=True))
                return self.reply(page,mime='text/html; charset=utf-8')
            if route in ('/assets/app.js','/assets/style.css'):
                file=ROOT/'web'/route.split('/')[-1]
                mime='text/javascript; charset=utf-8' if file.suffix=='.js' else 'text/css; charset=utf-8'
                return self.reply(file.read_bytes(),mime=mime)
            if route=='/health':return self.reply({'status':'UP','version':'1.3.1','mode':'LOCAL_ONLY'})
            if route.startswith('/preview/'):
                parts=route.split('/')
                if len(parts)!=4 or not parts[2].isdigit():return self.error('Chemin refusé',404)
                kind={'index.html':'text/html; charset=utf-8','app.js':'text/javascript; charset=utf-8','styles.css':'text/css; charset=utf-8'}
                if parts[3] not in kind:return self.error('Fichier non autorisé',404)
                csp="default-src 'none'; script-src 'self'; style-src 'self'; img-src 'self' data:; connect-src 'none'; form-action 'none'; frame-ancestors 'self'; sandbox allow-scripts"
                return self.reply(read_preview(s.home,int(parts[2]),parts[3]),mime=kind[parts[3]],policy=csp)
            if not self.authorized():return self.error('Jeton propriétaire requis',401)
            if route=='/api/providers':
                from .cockpit import providers
                return self.reply(providers(s))
            if route=='/api/cockpit':
                from .cockpit import snapshot
                return self.reply(snapshot(s))
            if route=='/api/dashboard':return self.reply(s.dashboard())
            if route=='/api/projects':return self.reply(s.projects())
            if route=='/api/roles':return self.reply([{'id':a['id'],'name':a['name'],'department':a['department'],'mission':a['mission']} for a in __import__('gdhq.roles',fromlist=['ROLES']).ROLES])
            if route=='/api/gates':return self.reply(s.db.all('SELECT * FROM gates ORDER BY id DESC LIMIT 100'))
            if route=='/api/audits':return self.reply(s.db.all('SELECT * FROM audits ORDER BY id DESC LIMIT 30'))
            if route=='/api/logs':return self.reply(s.db.all('SELECT * FROM events ORDER BY id DESC LIMIT 100'))
            if route=='/api/models':
                try: models=s.provider.models()
                except Exception: return self.error('LM Studio indisponible. Charge le modèle et démarre le serveur local 1234.',503)
                return self.reply({'models':models,'endpoint':'http://127.0.0.1:1234/v1'})
            if route=='/api/settings':return self.reply({'paused':s.db.setting('paused'),'model':s.db.setting('model'),'emergency_stop':s.db.setting('emergency_stop'),'provider':s.db.setting('provider'),'spend_mode':'DISABLED'})
            if route.startswith('/api/projects/'):
                parts=route.split('/')
                if len(parts)==4 and parts[3].isdigit():return self.reply(s.project(int(parts[3])))
                if len(parts)==5 and parts[3].isdigit() and parts[4]=='source':
                    filename=parse_qs(urlsplit(self.path).query).get('file',[''])[0]
                    return self.reply({'name':filename,'content':read_preview(s.home,int(parts[3]),filename).decode('utf-8')})
            return self.error('Route inconnue',404)
        except FileNotFoundError:return self.error('Aucun prototype généré',404)
        except ValueError as e:return self.error(e,400)
        except Exception as e:return self.error('Erreur du serveur : '+type(e).__name__,500)
    def do_POST(self):
        if not self.authorized_host():return self.error('Hôte non autorisé',403)
        if self.headers.get('Origin')!=f'http://127.0.0.1:{self.server.server_port}':return self.error('Origine interdite',403)
        if not self.authorized():return self.error('Jeton propriétaire requis',401)
        if self.headers.get('Content-Type','').split(';')[0].strip()!='application/json':return self.error('application/json exigé',415)
        try:size=int(self.headers.get('Content-Length','-1'))
        except ValueError:return self.error('Longueur invalide',400)
        if size<0 or size>25000:return self.error('Taille de requête excessive',413)
        try:data=json.loads(self.rfile.read(size))
        except (ValueError,UnicodeDecodeError):return self.error('JSON incorrect',400)
        if not isinstance(data,dict):return self.error('Objet JSON attendu',400)
        route=urlsplit(self.path).path;s=self.server.service
        try:
            if route=='/api/providers':
                from .cockpit import save_provider
                return self.reply(save_provider(s,data))
            if route.startswith('/api/cockpit/'):
                from .cockpit import mutate
                return self.reply(mutate(s,route.rsplit('/',1)[-1],data))
            if route=='/api/projects':
                pid=s.engine.create(str(data.get('name','')),str(data.get('brief','')),str(data.get('kind','general')))
                return self.reply({'ok':True,'project_id':pid},201)
            if route=='/api/settings':
                key=data.get('key');value=data.get('value')
                if key in ('paused','emergency_stop','privacy_gate') and type(value)!=bool:raise ValueError('Booléen requis')
                if key=='model' and (not isinstance(value,str) or len(value)>160):raise ValueError('Modèle invalide')
                if key=='provider' and value not in ('lmstudio','agents_sdk_local'):raise ValueError('Fournisseur distant interdit')
                if key=='audit_hours' and value!=2:raise ValueError('Audit fixé à 2 heures')
                if key=='autonomous_mode' and value!='DRAFT_ONLY':raise ValueError('Mode de sécurité non modifiable')
                s.db.set_setting(key,value)
                if key=='provider':
                    from .sdk_provider import AgentsSDKLocal
                    from .providers import LMStudio
                    s.provider=AgentsSDKLocal() if value=='agents_sdk_local' else LMStudio()
                    s.engine.ai=s.provider
                s.db.event('SETTING',f'{key} modifié')
                return self.reply({'ok':True})
            if route=='/api/audits/run':return self.reply(run_audit(s.db,s.home,s.provider))
            if route=='/api/backup':
                from datetime import datetime,timezone
                dest=s.home/'backups'/('global-'+datetime.now(timezone.utc).strftime('%Y%m%d-%H%M%S')+'.sqlite3')
                return self.reply(s.db.backup(dest))
            parts=route.split('/')
            if len(parts)==5 and parts[:3]==['','api','projects'] and parts[3].isdigit():
                pid=int(parts[3]);action=parts[4]
                if action=='run':return self.reply(s.engine.begin(pid))
                if action=='demo':return self.reply(s.engine.build_demo(pid))
                if action=='metric':return self.reply(s.add_metric(pid,data))
                if action=='improve':return self.reply(s.engine.improve(pid,data.get('instruction','')))
            if len(parts)==4 and parts[:3]==['','api','gates'] and parts[3].isdigit():
                return self.reply(decision(s.db,int(parts[3]),str(data.get('decision',''))))
            return self.error('Route inconnue',404)
        except PermissionError as e:return self.error(e,403)
        except ValueError as e:return self.error(e,409)
        except Exception as e:return self.error('Erreur interne : '+type(e).__name__,500)

def serve(service,host='127.0.0.1',port=8824):
    if host!='127.0.0.1':raise ValueError('Interdiction de réseau externe')
    with AppServer((host,port),service) as server:
        print(f'Global Digital HQ Next : http://127.0.0.1:{server.server_port}',flush=True)
        print('100 % local. Aucune publication ni dépense possible.',flush=True)
        try:server.serve_forever(poll_interval=0.5)
        except KeyboardInterrupt:pass
