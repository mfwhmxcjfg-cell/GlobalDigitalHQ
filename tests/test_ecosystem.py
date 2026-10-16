import unittest,tempfile,json,threading,sqlite3
from pathlib import Path
from contextlib import closing
from http.server import BaseHTTPRequestHandler,HTTPServer
from unittest.mock import patch
from gdhq.ecosystem import catalog,context,prepare_workflow,verify_sources
from gdhq.providers import Ollama,ModelUnavailable
from gdhq.service import Service
from gdhq.roles import INDEX
from scripts.deploy_windows import deploy

class EcosystemTests(unittest.TestCase):
 def test_eligible_pinned_sources(self):
  d=catalog();self.assertEqual(len(d['repositories']),19)
  for r in d['repositories']:
   self.assertGreaterEqual(r['stargazers_count'],50000);self.assertFalse(r['archived']);self.assertEqual(len(r['commit_sha']),40)
  self.assertEqual(verify_sources(),[])
 def test_every_agent_has_bounded_context(self):
  for role in INDEX:
   text=context(role);self.assertIn('DONNÉES INSUFFISANTES',text);self.assertLess(len(text),1200)
 def test_workflow_preparation_is_idempotent_and_stopped(self):
  with tempfile.TemporaryDirectory() as t:
   s=Service(Path(t))
   try:
    pid=s.engine.create('App test','Une application locale de gestion des tâches','webapp')
    self.assertEqual(prepare_workflow(s,pid,'factory')['created_tasks'],4)
    self.assertEqual(prepare_workflow(s,pid,'factory')['created_tasks'],0)
    rows=s.db.all('SELECT * FROM cockpit_tasks');self.assertTrue(all(r['status']=='TODO' and r['agent_id'] in INDEX for r in rows))
    s.db.set_setting('emergency_stop',True)
    with self.assertRaises(PermissionError):prepare_workflow(s,pid,'operations')
   finally:s.engine.pool.shutdown()
 def test_bad_workflow_and_project(self):
  with tempfile.TemporaryDirectory() as t:
   s=Service(Path(t))
   try:
    with self.assertRaises(ValueError):prepare_workflow(s,999,'factory')
   finally:s.engine.pool.shutdown()
 def test_ollama_rejects_remote_and_cloud(self):
  with self.assertRaises(ValueError):Ollama('https://example.com/v1')
  for name in ['model:cloud','provider/model','https://model']:
   with self.assertRaises(ModelUnavailable):Ollama().chat('system','user',name)
 def test_ollama_protocol(self):
  seen=[]
  class Handler(BaseHTTPRequestHandler):
   def log_message(self,*args):pass
   def do_GET(self):
    seen.append(self.path);raw=json.dumps({'data':[{'id':'qwen-local'},{'id':'qwen:cloud'}]}).encode();self.send_response(200);self.end_headers();self.wfile.write(raw)
   def do_POST(self):
    seen.append(json.loads(self.rfile.read(int(self.headers['Content-Length']))));self.send_response(200);self.end_headers();self.wfile.write(b'{"choices":[{"message":{"content":"Brouillon local valide"}}]}')
  server=HTTPServer(('127.0.0.1',0),Handler);thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
  try:
   with patch('gdhq.providers.local_endpoint',lambda u:u):
    client=Ollama('http://127.0.0.1:'+str(server.server_port)+'/v1')
   self.assertEqual(client.models(),['qwen-local']);self.assertEqual(client.chat('sys','usr','qwen-local'),'Brouillon local valide')
   self.assertEqual(seen[-1]['model'],'qwen-local');self.assertFalse(seen[-1]['stream'])
  finally:server.shutdown();server.server_close();thread.join()
 def test_deploy_preserves_database_and_previous_app(self):
  with tempfile.TemporaryDirectory() as t:
   home=Path(t)/'install';source=Path(t)/'source';source.mkdir();(source/'README.md').write_text('new');(source/'.env').write_text('private')
   (home/'app').mkdir(parents=True);(home/'app/README.md').write_text('old');(home/'data').mkdir()
   with closing(sqlite3.connect(home/'data/agency.sqlite3')) as c, c:c.execute('CREATE TABLE evidence(value TEXT)');c.execute("INSERT INTO evidence VALUES ('keep')")
   with patch('scripts.deploy_windows.socket.socket') as sock:
    sock.return_value.__enter__.return_value.connect_ex.return_value=1
    r=deploy(home,source)
   self.assertFalse(r['started']);self.assertEqual((home/'app/README.md').read_text(),'new');self.assertFalse((home/'app/.env').exists());self.assertEqual((Path(r['previous_app'])/'README.md').read_text(),'old')
   with closing(sqlite3.connect(Path(r['database_backup'])/'agency.sqlite3')) as c, c:self.assertEqual(c.execute('SELECT value FROM evidence').fetchone()[0],'keep')
 def test_deploy_refuses_running_server(self):
  with tempfile.TemporaryDirectory() as t:
   with patch('scripts.deploy_windows.socket.socket') as sock:
    sock.return_value.__enter__.return_value.connect_ex.return_value=0
    with self.assertRaises(RuntimeError):deploy(Path(t)/'install',Path(t)/'source')

class AgentWorkflowTests(unittest.TestCase):
 def test_local_draft_contains_result_and_review_marker(self):
  from scripts.run_agent_workflow import run
  class Local:
   def models(self):return ['test-model']
   def chat(self,*args,**kwargs):return 'Résultat de test local sans aucune preuve commerciale.'
  with tempfile.TemporaryDirectory() as t:
   rows=run(Local(),'test-model','qa,qa,security','Vérifier le parcours de création du projet',t)
   self.assertEqual(len(rows),2)
   self.assertTrue(all(not r['external_action'] for r in rows))
   self.assertIn('BROUILLON NON VÉRIFIÉ',(Path(t)/'qa.md').read_text())
 def test_unknown_agent_and_missing_model_are_rejected(self):
  from scripts.run_agent_workflow import run
  class Local:
   def models(self):return []
  with tempfile.TemporaryDirectory() as t:
   for role in ['not-an-agent','qa']:
    with self.assertRaises(ValueError):run(Local(),'missing',role,'Une demande assez détaillée',t)
   self.assertEqual(list(Path(t).iterdir()),[])

class DataMigrationTests(unittest.TestCase):
 def test_copy_database_and_assets_without_overwriting_original(self):
  from scripts.deploy_windows import migrate_data
  with tempfile.TemporaryDirectory() as t:
   previous=Path(t)/'previous';previous.mkdir();(previous/'note.txt').write_text('keep')
   with closing(sqlite3.connect(previous/'global.sqlite3')) as c, c:c.execute('CREATE TABLE notes(value TEXT)');c.execute("INSERT INTO notes VALUES ('original')")
   target=Path(t)/'newdata'
   self.assertTrue(migrate_data(previous,target));self.assertEqual((target/'note.txt').read_text(),'keep')
   with closing(sqlite3.connect(target/'global.sqlite3')) as c, c:self.assertEqual(c.execute('SELECT value FROM notes').fetchone()[0],'original')
   self.assertTrue((previous/'global.sqlite3').exists());self.assertFalse(migrate_data(previous,target))
 def test_launcher_uses_target_data_and_temp(self):
  with tempfile.TemporaryDirectory() as t:
   source=Path(t)/'source';source.mkdir();(source/'README.md').write_text('new');home=Path(t)/'target'
   with patch('scripts.deploy_windows.socket.socket') as sock:
    sock.return_value.__enter__.return_value.connect_ex.return_value=1
    r=deploy(home,source)
   text=Path(r['launcher']).read_text();self.assertIn('GDHQ_DATA_DIR=%~dp0data',text);self.assertIn('TEMP=%~dp0temp',text)

class WorkflowContextRegressionTests(unittest.TestCase):
 def test_runner_context_is_never_used_in_job_env(self):
  from gdhq.settings import ROOT
  for path in (ROOT/'.github/workflows').glob('*.yml'):
   job_env=False
   for line in path.read_text().splitlines():
    if line.startswith('    env:'):job_env=True
    elif line.strip() and not line.startswith('      '):job_env=False
    if job_env:self.assertNotIn('runner.',line,str(path))

class WindowsWorkflowRegressionTests(unittest.TestCase):
 def test_windows_actions_do_not_require_powershell_scripts(self):
  from gdhq.settings import ROOT
  for name in ['deploy-windows.yml','agent-drafts.yml']:
   text=(ROOT/'.github/workflows'/name).read_text(encoding='utf-8')
   self.assertNotIn('shell: powershell',text);self.assertNotIn('shell: pwsh',text)
   self.assertIn('shell: cmd',text);self.assertIn('PYTHONUTF8: "1"',text)

class BackupHandleTests(unittest.TestCase):
 def test_connections_closed_on_success_and_failure(self):
  from scripts.deploy_windows import backup_database
  from unittest.mock import MagicMock
  for fail in [False, True]:
   with self.subTest(fail=fail):
    src=MagicMock();dst=MagicMock()
    if fail:src.backup.side_effect=RuntimeError('backup failed')
    with patch('scripts.deploy_windows.sqlite3.connect',side_effect=[src,dst]):
     if fail:
      with self.assertRaises(RuntimeError):backup_database(Path('source.sqlite3'),Path('target.sqlite3'))
     else:backup_database(Path('source.sqlite3'),Path('target.sqlite3'))
    src.close.assert_called_once_with();dst.close.assert_called_once_with()
 def test_source_closed_when_destination_cannot_open(self):
  from scripts.deploy_windows import backup_database
  from unittest.mock import MagicMock
  src=MagicMock()
  with patch('scripts.deploy_windows.sqlite3.connect',side_effect=[src,OSError('cannot open')]):
   with self.assertRaises(OSError):backup_database(Path('source.sqlite3'),Path('target.sqlite3'))
  src.close.assert_called_once_with()
