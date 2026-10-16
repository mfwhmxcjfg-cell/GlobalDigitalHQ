import json, os,sqlite3,sys,tempfile,time,unittest,threading
from pathlib import Path
from unittest.mock import patch
from gdhq.database import Database
from gdhq.service import Service
from gdhq.providers import LMStudio,ModelUnavailable
from gdhq.settings import local_endpoint
from gdhq.governance import require_gate,decision,block_external
from gdhq.roles import ROLES,team_for,skill_text
from gdhq.builder import scaffold,read_preview,check_project,apply_candidate,restore_checkpoint,validate_candidate
from gdhq.migration import inspect,import_projects
from gdhq.auditing import run_audit
from gdhq.webapp import AppServer
from urllib.request import Request,urlopen
from urllib.error import HTTPError

class FakeProvider:
    def models(self):return ['qwen-test']
    def chat(self,system,user,model,max_tokens=1100):
        if '"evidence_id":1' in system:return __import__('json').dumps({'verdict':'SUPPORTED','claims':[{'statement':'Observation de test','evidence_id':1,'quote':'Données fictives de test uniquement','kpi':''}],'missing':[],'recommendation':'Recommandation de test'})
        if '"verdict":"ACCEPT"' in system:return json.dumps({'verdict':'ACCEPT','reason':'Livrable de test acceptable'})
        return 'Proposition locale non vérifiée. Testez le marché avant toute dépense.'

class Tests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.home=Path(self.tmp.name)/'data'
        self.s=Service(self.home,FakeProvider())
        self.s.engine.research=lambda *args: {'context':'Données fictives de test uniquement','reports':[],'evidence':[{'id':1,'content':'Données fictives de test uniquement'}]}
        # LIFO cleanup: finish workers before removing their Windows SQLite files.
        self.addCleanup(self.s.engine.pool.shutdown, wait=True)
    def project(self):return self.s.engine.create('Boutique test','Construire un prototype de boutique et vérifier le panier.','dropshipping')
    def test_schema(self):self.assertEqual(self.s.db.integrity(),'ok')
    def test_40_managers(self):self.assertEqual(len(ROLES),40)
    def test_privacy_officer(self):self.assertIn('RGPD',next(r['name'] for r in ROLES if r['id']=='compliance'))
    def test_unique_roles(self):self.assertEqual(len({a['id'] for a in ROLES}),40)
    def test_selected_team(self):self.assertIn('security',[a['id'] for a in team_for('dropshipping')])
    def test_skill_real(self):self.assertIn('ceo',skill_text(ROLES[0]).lower())
    def test_paused(self):
        pid=self.project()
        with self.assertRaisesRegex(ValueError,'pause'):self.s.engine.begin(pid)
    def test_database_close(self):
        with self.s.db.connect() as c:c.execute('SELECT 1')
        with self.assertRaises(sqlite3.ProgrammingError):c.execute('SELECT 1')
    def test_project_persists(self):
        pid=self.project();self.assertEqual(Service(self.home).project(pid)['name'],'Boutique test')
    def test_projects_reject_short(self):
        with self.assertRaises(ValueError):self.s.engine.create('x','a','general')
    def test_prototype(self):
        pid=self.project();result=self.s.engine.build_demo(pid)
        self.assertTrue(result['qa']['ok']);self.assertEqual(len(result['files']),3)
    def test_storefront_has_local_cart(self):
        pid=self.project();self.s.engine.build_demo(pid)
        self.assertIn(b'refreshCart()',read_preview(self.home,pid,'app.js'))
    def test_path_traversal(self):
        pid=self.project();self.s.engine.build_demo(pid)
        with self.assertRaises(ValueError):read_preview(self.home,pid,'../../evil')
    def test_webapp_template(self):
        pid=self.s.engine.create('Gestion tâches','Application locale pour tâches et priorités.','webapp')
        self.assertTrue(self.s.engine.build_demo(pid)['qa']['ok'])
        self.assertIn(b'renderTasks()',read_preview(self.home,pid,'app.js'))
    def test_content_template(self):
        pid=self.s.engine.create('Contenus test','Calendrier local pour organiser les publications.','content')
        self.assertTrue(self.s.engine.build_demo(pid)['qa']['ok'])
        self.assertIn(b'renderIdeas()',read_preview(self.home,pid,'app.js'))
    def test_html_escaped(self):
        pid=self.s.engine.create('<script>alert(1)</script>','Objectif sans collecte de données ni achats.','general')
        self.s.engine.build_demo(pid)
        html=read_preview(self.home,pid,'index.html').decode()
        self.assertNotIn('<script>alert(1)</script>',html)
        self.assertIn('&lt;script&gt;',html)
    def test_fixed_gate(self):
        pid=self.project();gate=require_gate(self.s.db,pid,'SPEND','Budget réclamé')
        self.assertEqual(gate['state'],'AWAITING_OWNER')
    def test_gate_approval_not_spend(self):
        pid=self.project();gate=require_gate(self.s.db,pid,'SPEND','Budget réclamé')
        self.assertEqual(decision(self.s.db,gate['id'],'APPROVED')['state'],'APPROVED')
        with self.assertRaises(PermissionError):block_external('SPEND')
    def test_reject_duplicate_gate(self):
        pid=self.project();gate=require_gate(self.s.db,pid,'SPEND','Budget réclamé')
        decision(self.s.db,gate['id'],'REJECTED')
        with self.assertRaises(ValueError):decision(self.s.db,gate['id'],'APPROVED')
    def test_paid_cannot_enable(self):
        with self.assertRaises(ValueError):self.s.db.set_setting('paid_enabled',True)
        self.assertFalse(self.s.db.setting('paid_enabled'))
    def test_model_urls(self):
        for url in ('https://127.0.0.1:1234/v1','http://openai.com/v1','http://127.0.0.1:8080/v1','http://user:pass@127.0.0.1:1234/v1'):
            with self.subTest(url=url),self.assertRaises(ValueError):local_endpoint(url)
    def test_model_no_network(self):
        with self.assertRaises(ModelUnavailable):LMStudio(url='http://127.0.0.1:1234/v1',timeout=.1).models()
    def test_metric_provenance(self):
        pid=self.project()
        with self.assertRaises(PermissionError):self.s.add_metric(pid,{'name':'ventes','value':10,'unit':'eur','provenance':'OBSERVED_VERIFIED','observed_at':'2026-10-15'})
    def test_manual_metric(self):
        pid=self.project();x=self.s.add_metric(pid,{'name':'ventes','value':10,'unit':'eur','provenance':'USER_REPORTED','observed_at':'2026-10-15'})
        self.assertFalse(x['verified'])
    def test_backup_restore(self):
        self.project();p=Path(self.tmp.name)/'backup.sqlite3'
        result=self.s.db.backup(p)
        self.assertTrue(result['sha256']);with_db=sqlite3.connect(p)
        try:self.assertEqual(with_db.execute('select count(*) from projects').fetchone()[0],1)
        finally:with_db.close()
    def test_candidate_disallows_external_network(self):
        with self.assertRaises(ValueError):validate_candidate({'index.html':'<html><script src="app.js"></script></html>','styles.css':'body{}','app.js':'fetch("https://bad.example/")'})
    def test_candidate_restore(self):
        """Test the filesystem rollback logic independently of an optional Node runtime.

        Node syntax checking is still mandatory in the production code; only its
        external subprocess is simulated here. Otherwise Windows machines without
        Node would be unable to INSTALL an application that can run without it.
        """
        from subprocess import CompletedProcess
        pid=self.project();self.s.engine.build_demo(pid)
        original={k:read_preview(self.home,pid,k).decode() for k in ('index.html','styles.css','app.js')}
        modified=dict(original);modified['styles.css']=original['styles.css']+'\nbody{border:0}'
        with patch('shutil.which',return_value='test-node'), patch('subprocess.run',return_value=CompletedProcess(['test-node','--check'],0,'','')) as run:
            outcome=apply_candidate(self.s.db,self.home,pid,modified)
            self.assertTrue(outcome['applied'])
            restore_checkpoint(self.s.db,self.home,pid,outcome['checkpoint'])
        self.assertEqual(run.call_count,2)
        self.assertEqual(read_preview(self.home,pid,'styles.css').decode(),original['styles.css'])

    def test_candidate_rejected_without_node_and_files_unchanged(self):
        """A missing optional Node installation must fail closed for AI code."""
        pid=self.project();self.s.engine.build_demo(pid)
        original={k:read_preview(self.home,pid,k) for k in ('index.html','styles.css','app.js')}
        modified={k:v.decode() for k,v in original.items()}
        modified['styles.css']+='\nbody{border:0}'
        with patch('shutil.which',return_value=None):
            with self.assertRaisesRegex(ValueError,'Node.js absent'):
                apply_candidate(self.s.db,self.home,pid,modified)
        for k,v in original.items():
            self.assertEqual(read_preview(self.home,pid,k),v)

    def test_candidate_rejected_if_js_check_fails(self):
        """A failing JavaScript parser must never result in an applied patch."""
        from subprocess import CompletedProcess
        pid=self.project();self.s.engine.build_demo(pid)
        original={k:read_preview(self.home,pid,k) for k in ('index.html','styles.css','app.js')}
        modified={k:v.decode() for k,v in original.items()}
        modified['styles.css']+='\nbody{border:0}'
        with patch('shutil.which',return_value='test-node'), patch('subprocess.run',return_value=CompletedProcess(['test-node','--check'],1,'','SyntaxError: test')):
            with self.assertRaisesRegex(ValueError,'Syntaxe JavaScript incorrecte'):
                apply_candidate(self.s.db,self.home,pid,modified)
        for k,v in original.items():
            self.assertEqual(read_preview(self.home,pid,k),v)

    def test_disallow_duplicate_process(self):
        pid=self.project();self.s.db.set_setting('paused',False)
        self.s.engine.active.add(pid)
        with self.assertRaisesRegex(ValueError,'déjà'):self.s.engine.begin(pid)
    def test_multiagent_reviews(self):
        pid=self.project();self.s.db.set_setting('paused',False);self.s.db.set_setting('model','qwen-test');self.s.engine.begin(pid)
        deadline=time.monotonic()+60
        while pid in self.s.engine.active and time.monotonic()<deadline:time.sleep(.04)
        self.assertNotIn(pid,self.s.engine.active,'Agents toujours actifs après 60 secondes')
        p=self.s.project(pid)
        self.assertEqual(p['state'],'AWAITING_OWNER',self.s.db.all('SELECT * FROM events'))
        self.assertGreaterEqual(len(p['decisions']),5)
        self.assertTrue((self.home/'projects'/str(pid)/'index.html').is_file())
    def test_model_missing_blocks(self):
        pid=self.project();self.s.db.set_setting('paused',False);self.s.engine.begin(pid)
        deadline=time.monotonic()+60
        while pid in self.s.engine.active and time.monotonic()<deadline:time.sleep(.04)
        self.assertEqual(self.s.project(pid)['state'],'BLOCKED')
    def test_crash_recovery(self):
        pid=self.project();self.s.db.write('UPDATE projects SET state=? WHERE id=?',('RUNNING',pid))
        s2=Service(self.home,FakeProvider())
        self.assertEqual(s2.project(pid)['state'],'BLOCKED')
    def test_audit(self):
        a=run_audit(self.s.db,self.home,FakeProvider())
        self.assertEqual(a['checks']['database_integrity'],'ok')
        self.assertEqual(a['checks']['agent_count'],40)
    def test_legacy_inspect_and_import(self):
        legacy=Path(self.tmp.name)/'legacy.sqlite3';c=sqlite3.connect(legacy)
        c.execute('CREATE TABLE projects(id integer primary key,name text,objective text)');c.execute("INSERT INTO projects VALUES(15,'Nature','Créer une chaîne YouTube locale')");c.execute('CREATE TABLE metrics(project_id integer,name text,value real,unit text,observed text)');c.execute("INSERT INTO metrics VALUES(15,'visites',50,'count','2026-10-12')");c.commit();c.close()
        self.assertEqual(len(inspect(legacy)['projects']),1)
        first=import_projects(self.s.db,legacy)
        self.assertEqual((first['imported'],first['metrics_imported']),(1,1))
        again=import_projects(self.s.db,legacy)
        self.assertEqual((again['imported'],again['metrics_imported']),(0,0))
        self.assertEqual(self.s.projects()[0]['state'],'IMPORTED_READ_ONLY')
        self.assertEqual(self.s.db.all('SELECT provenance FROM metrics')[0]['provenance'],'IMPORTED_UNVERIFIED')

class HTTPTests(unittest.TestCase):
    project=Tests.project
    def setUp(self):
        Tests.setUp(self)
        self.server=AppServer(('127.0.0.1',0),self.s)
        self.host=f'127.0.0.1:{self.server.server_port}'
        self.base='http://'+self.host
        self.thread=threading.Thread(target=self.server.serve_forever,daemon=True)
        self.thread.start()
        self.addCleanup(self.server.server_close)
        self.addCleanup(self.server.shutdown)
    def request(self,path,body=None,token=True,origin=True,host=None):
        headers={'Host':host or self.host}
        if token:headers['X-GDHQ-Token']=self.server.owner_token
        if origin:headers['Origin']=self.base
        data=json.dumps(body).encode() if body is not None else None
        if data is not None:headers['Content-Type']='application/json'
        req=Request(self.base+path,data=data,headers=headers)
        try:
            with urlopen(req,timeout=3) as r:return r.status,r.read()
        except HTTPError as e:return e.code,e.read()
    def test_http_health(self):self.assertEqual(self.request('/health')[0],200)
    def test_http_no_token(self):self.assertEqual(self.request('/api/dashboard',token=False)[0],401)
    def test_http_invalid_origin(self):self.assertEqual(self.request('/api/projects',{'name':'ab','brief':'1234567890','kind':'general'},origin=False)[0],403)
    def test_http_rejected_host(self):self.assertEqual(self.request('/api/dashboard',host='evil.example')[0],403)
    def test_http_project(self):
        status,data=self.request('/api/projects',{'name':'Nouveau site','brief':'Créer un panier original et local','kind':'webapp'})
        self.assertEqual(status,201);pid=json.loads(data)['project_id']
        self.assertEqual(self.request('/api/projects/'+str(pid))[0],200)
    def test_http_paid_setting_blocked(self):self.assertEqual(self.request('/api/settings',{'key':'paid_enabled','value':True})[0],409)
    def test_http_source_token_required(self):
        pid=self.project();self.s.engine.build_demo(pid)
        self.assertEqual(self.request(f'/api/projects/{pid}/source?file=app.js')[0],200)
        self.assertEqual(self.request(f'/api/projects/{pid}/source?file=app.js',token=False)[0],401)
        self.assertEqual(self.request(f'/api/projects/{pid}/source?file=secret.env')[0],400)
    def test_http_preview_only_known(self):
        pid=self.project();self.s.engine.build_demo(pid)
        self.assertEqual(self.request(f'/preview/{pid}/index.html')[0],200)
        self.assertEqual(self.request(f'/preview/{pid}/secret.env')[0],404)
    def test_http_live_routes_require_owner_and_origin(self):
        self.assertEqual(self.request('/api/live',token=False)[0],401)
        self.assertEqual(self.request('/api/live/import',{'connectors':[]},origin=False)[0],403)
        config={'name':'Test Public','kind':'API_GET','url':'https://example.org/api'}
        status,body=self.request('/api/live/import',{'connectors':config})
        self.assertEqual(status,200);cid=json.loads(body)['ids'][0]
        self.assertEqual(self.request('/api/live/approve',{'ids':[cid],'enabled':True})[0],200)
        self.assertTrue(json.loads(self.request('/api/live')[1])['connectors'][0]['approved'])
        pid=self.project()
        status,_=self.request('/api/live/plan',{'project_id':pid,'connector_ids':[cid],'query':'prix public','min_sources':1})
        self.assertEqual(status,200)
    def test_http_emergency(self):
        r=self.request('/api/settings',{'key':'emergency_stop','value':True})
        self.assertEqual(r[0],200);self.assertTrue(self.s.db.setting('emergency_stop'))

if __name__=='__main__':unittest.main()
