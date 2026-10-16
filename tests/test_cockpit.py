import tempfile, unittest
from pathlib import Path
from gdhq.service import Service
from gdhq.cockpit import snapshot,mutate
class CockpitTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.s=Service(Path(self.tmp.name));self.pid=self.s.engine.create('Cockpit test','Validation locale sans appel externe','general')
 def tearDown(self):
  self.s.engine.pool.shutdown(wait=True);self.tmp.cleanup()
 def test_persistent_task_validation(self):
  mutate(self.s,'task',{'project_id':self.pid,'title':'Vérifier le résultat','agent_id':'qa'});t=snapshot(self.s)['tasks'][0]
  with self.assertRaises(ValueError):mutate(self.s,'task-status',{'id':t['id'],'status':'DONE','evidence':'preuve'})
  for state in ['IN_PROGRESS','REVIEW','DONE']:mutate(self.s,'task-status',{'id':t['id'],'status':state,'evidence':'Rapport relu par le propriétaire'})
  self.assertEqual(snapshot(self.s)['tasks'][0]['status'],'DONE')
  self.assertEqual(self.s.db.one("SELECT count(*) n FROM events WHERE category='OWNER_TASK'")['n'],4)
 def test_memory_and_kpi(self):
  mutate(self.s,'memory',{'project_id':self.pid,'title':'Hypothèse','content':'À confirmer par une source'})
  mutate(self.s,'metric',{'project_id':self.pid,'name':'Clients','value':0,'unit':'clients'})
  d=snapshot(self.s);self.assertEqual(d['metrics'][0]['value'],0);self.assertEqual(d['memory'][0]['status'],'USER_REPORTED')
  with self.assertRaises(ValueError):mutate(self.s,'metric',{'project_id':self.pid,'name':'CA','value':float('nan'),'unit':'EUR'})
 def test_missing_project_and_agent(self):
  for pid,agent in [(999,'qa'),(self.pid,'invented')]:
   with self.assertRaises(ValueError):mutate(self.s,'task',{'project_id':pid,'title':'Test','agent_id':agent})
 def test_no_claimed_connections(self):
  d=snapshot(self.s);self.assertEqual(len(d['agents']),40)
  self.assertTrue(all(c['status']=='NOT_CONNECTED' for c in d['connectors'][1:]))
