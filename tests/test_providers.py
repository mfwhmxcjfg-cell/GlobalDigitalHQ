import unittest,tempfile,os
from pathlib import Path
from gdhq.service import Service
from gdhq.cockpit import save_provider,providers
class ProviderTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.s=Service(Path(self.tmp.name))
 def tearDown(self):self.s.engine.pool.shutdown();self.tmp.cleanup()
 def test_save_update_secret_not_exposed(self):
  d=dict(name='Example',kind='API',endpoint='https://example.com/v1',secret_env='GDHQ_TEST_KEY')
  os.environ['GDHQ_TEST_KEY']='secret-test-value'
  try:
   save_provider(self.s,d);r=providers(self.s)[0];self.assertEqual(r['credential_status'],'PRESENT_IN_PROCESS');self.assertNotIn('secret-test-value',str(r));self.assertEqual(r['connection_status'],'NOT_CONNECTED')
   save_provider(self.s,{**d,'id':r['id'],'name':'Edited'});self.assertEqual(len(providers(self.s)),1)
  finally:os.environ.pop('GDHQ_TEST_KEY',None)
 def test_invalid_urls(self):
  for u in ['https://user:pass@example.com','https://example.com?key=secret','file:///tmp/file','http://example.com','https://example.com#secret']:
   with self.assertRaises(ValueError):save_provider(self.s,dict(name='Example',kind='MCP',endpoint=u))
 def test_invalid_reference(self):
  with self.assertRaises(ValueError):save_provider(self.s,dict(name='Example',kind='API',endpoint='https://example.com',secret_env='sk-secret'))
  with self.assertRaises(ValueError):save_provider(self.s,dict(name='Example',kind='API',endpoint='https://example.com',project_id=999))
