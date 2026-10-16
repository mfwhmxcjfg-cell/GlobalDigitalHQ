import json,os,tempfile,unittest,socket
from pathlib import Path
from unittest.mock import patch,MagicMock
from concurrent.futures import ThreadPoolExecutor
from gdhq.service import Service
from gdhq import live
from gdhq.public_http import endpoint,public_addresses,ConnectorError
from gdhq.workforce import run

TEXT='Le prix public affiché est de 25 EUR par unité, relevé pour cet exemple de test uniquement.'

class EvidenceModel:
 def chat(self,system,user,model,max_tokens=1000):
  if '"verdict":"ACCEPT"' in system:return '{"verdict":"ACCEPT","reason":"Livrable de test correctement limité"}'
  if '"evidence_id":1' in system:
   import re
   match=re.search(r'\[E(\d+)\]',user);eid=int(match.group(1)) if match else 1
   return json.dumps({'verdict':'SUPPORTED','claims':[{'statement':'Prix affiché dans la source de test','evidence_id':eid,'quote':TEXT,'kpi':'prix'}],'missing':[],'recommendation':'Comparer les conditions exactes avant décision.'})
  return 'Document de test qui cite les données et demande une validation humaine.'
 def models(self):return ['test-model']

class LiveTests(unittest.TestCase):
 def setUp(self):
  self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
  self.s=Service(Path(self.temp.name),EvidenceModel());self.addCleanup(self.s.engine.pool.shutdown,wait=True)
  self.db=self.s.db;self.pid=self.s.engine.create('Projet recherche','Comparer les prix publics de produits disponibles','general')
  self.db.set_setting('paused',False);self.db.set_setting('model','test-model')
 def connector(self,**extra):
  config={'name':'Public source','kind':'API_GET','url':'https://example.org/data?q={query}',**extra}
  cid=live.import_connectors(self.db,config)['ids'][0];live.approve_connectors(self.db,[cid],True)
  return self.db.one('SELECT * FROM live_connectors WHERE id=?',(cid,))
 def plan(self,row,**extra):return live.save_plan(self.db,self.pid,{'connector_ids':[row['id']],'query':'prix produit','min_sources':1,**extra})
 def response(self,*args,**kwargs):return json.dumps({'price':TEXT}).encode(),{'content-type':'application/json'}
 def test_bulk_atomic_and_reimport_revokes_only_changes(self):
  with self.assertRaises(ValueError):live.import_connectors(self.db,[{'name':'Valid','kind':'API_GET','url':'https://example.org/data'},{'name':'Bad','kind':'API_GET','url':'http://example.org'}])
  self.assertEqual(live.connector_rows(self.db),[])
  row=self.connector();live.import_connectors(self.db,json.loads(row['config']))
  self.assertTrue(live.connector_rows(self.db)[0]['approved'])
  changed=json.loads(row['config']);changed['url']='https://other.example/data'
  live.import_connectors(self.db,changed);self.assertFalse(live.connector_rows(self.db)[0]['approved'])
 def test_no_unapproved_or_paused_network(self):
  row=self.connector();live.approve_connectors(self.db,[row['id']],False)
  with patch('gdhq.live.fetch') as fetch:
   with self.assertRaises(ConnectorError):live.collect_one(self.db,self.s.home,self.pid,row,'test')
   fetch.assert_not_called()
  live.approve_connectors(self.db,[row['id']],True);self.db.set_setting('emergency_stop',True)
  with patch('gdhq.live.fetch') as fetch:
   with self.assertRaises(PermissionError):live.collect_one(self.db,self.s.home,self.pid,row,'test')
   fetch.assert_not_called()
 def test_observed_content_hash_and_secret_redaction(self):
  row=self.connector(secret_env='TEST_API_KEY')
  with patch.dict(os.environ,{'TEST_API_KEY':'never-store-this-key'}),patch('gdhq.live.fetch',return_value=(json.dumps({'value':TEXT,'echo':'never-store-this-key'}).encode(),{})):
   result=live.collect_one(self.db,self.s.home,self.pid,row,'test')
  self.assertNotIn('never-store-this-key',result['content']);self.assertIn('[SECRET MASQUÉ]',result['content'])
  self.assertEqual((self.s.home/result['artifact']).read_text(encoding='utf-8'),result['content'])
  self.assertEqual(len(result['sha256']),64)
 def test_call_limit_is_atomic(self):
  row=self.connector(daily_calls=1)
  def attempt():
   try:live.reserve(self.db,row,self.pid);return True
   except ConnectorError:return False
  with ThreadPoolExecutor(max_workers=4) as pool:results=list(pool.map(lambda _:attempt(),range(4)))
  self.assertEqual(sum(results),1)
 def test_failed_call_still_consumes_budget(self):
  row=self.connector(daily_calls=2,max_cost_usd=.5,daily_budget_usd=.5)
  with patch('gdhq.live.fetch',side_effect=ConnectorError('HTTP 503')):
   with self.assertRaises(ConnectorError):live.collect_one(self.db,self.s.home,self.pid,row,'test')
  with self.assertRaisesRegex(ConnectorError,'budget'):live.reserve(self.db,row,self.pid)
 def test_citations_and_kpi_require_real_excerpt(self):
  rows=[{'id':1,'content':TEXT}]
  valid={'verdict':'SUPPORTED','claims':[{'statement':'Prix public','evidence_id':1,'quote':TEXT,'kpi':'prix'}],'missing':[],'recommendation':'Comparer'}
  self.assertEqual(live.validate_decision(json.dumps(valid),rows,['prix']),valid)
  for key,value in [('evidence_id',999),('quote','Une citation inventée contenant un prix de 100 EUR')]:
   bad=json.loads(json.dumps(valid));bad['claims'][0][key]=value
   with self.assertRaises(live.MissingResource):live.validate_decision(json.dumps(bad),rows,[])
  with self.assertRaises(live.MissingResource):live.validate_decision(json.dumps(valid),rows,['ventes'])
 def test_no_source_creates_one_idempotent_resource_request(self):
  p=self.s.project(self.pid)
  for _ in range(2):
   with self.assertRaises(live.MissingResource):live.discover(self.db,self.s.home,p,self.s.provider,'test-model')
  self.assertEqual(len(live.snapshot(self.db)['requests']),1)
 def test_discovery_passes_real_collected_data_to_analysis(self):
  row=self.connector();self.plan(row,required_kpis=['prix'])
  with patch('gdhq.live.fetch',side_effect=self.response):d=live.discover(self.db,self.s.home,self.s.project(self.pid),self.s.provider,'test-model')
  self.assertIn(TEXT,d['context']);self.assertEqual(d['reports'][0]['report']['verdict'],'SUPPORTED')
 def test_engine_blocks_then_resource_approval_resumes(self):
  self.s.engine._run(self.pid)
  self.assertEqual(self.s.project(self.pid)['state'],'BLOCKED')
  request=live.snapshot(self.db,self.pid)['requests'][0]
  row=self.connector();self.plan(row)
  with patch('gdhq.live.fetch',side_effect=self.response):
   self.assertTrue(live.approve_request(self.s,request['id'])['resumed'])
   self.s.engine.pool.shutdown(wait=True)
  self.assertEqual(self.s.project(self.pid)['state'],'AWAITING_OWNER')
  self.assertEqual(live.snapshot(self.db,self.pid)['requests'][0]['status'],'RESOLVED')
 def test_resolve_does_not_resume_while_paused(self):
  try:live.require_resource(self.db,self.pid,'model','Model required')
  except live.MissingResource:pass
  req=live.snapshot(self.db)['requests'][0];self.db.set_setting('paused',True)
  with self.assertRaises(PermissionError):live.approve_request(self.s,req['id'])
  self.assertEqual(live.snapshot(self.db)['requests'][0]['status'],'OPEN')
 def test_search_follow_never_forwards_key_and_rejects_private_target(self):
  row=self.connector(secret_env='SEARCH_API_KEY',follow_links=True);self.plan(row)
  calls=[]
  def transport(url,headers=None,*args,**kwargs):
   calls.append((url,headers))
   if 'example.org' in url:return json.dumps({'web':{'results':[{'url':'https://public.example/page'},{'url':'http://127.0.0.1:8824/'}]}}).encode(),{}
   return TEXT.encode(),{'content-type':'text/plain'}
  with patch.dict(os.environ,{'SEARCH_API_KEY':'my-secret'}),patch('gdhq.live.fetch',side_effect=transport):
   try:live.discover(self.db,self.s.home,self.s.project(self.pid),self.s.provider,'test-model')
   except live.MissingResource:pass
  self.assertEqual(len(calls),2);self.assertEqual(calls[1][1],{})
 def test_rejected_review_blocks_dependents(self):
  class Refusing(EvidenceModel):
   def chat(self,system,user,model,max_tokens=300):
    if '"verdict":"ACCEPT"' in system:return '{"verdict":"REVISE","reason":"Les preuves sont insuffisantes"}'
    return super().chat(system,user,model,max_tokens)
  report=run(self.db,self.s.home,self.s.project(self.pid),Refusing(),'test-model')
  self.assertIn('NEEDS_REVISION',report['statuses'].values());self.assertIn('WAITING_DEPENDENCY',report['statuses'].values())
  self.assertFalse(report['processed'])
 def test_dependency_content_and_entire_skill_reach_next_agent(self):
  class Recording(EvidenceModel):
   def __init__(self):self.calls=[]
   def chat(self,system,user,model,max_tokens=300):self.calls.append((system,user));return super().chat(system,user,model,max_tokens)
  model=Recording();run(self.db,self.s.home,self.s.project(self.pid),model,'test-model')
  self.assertTrue(any('Document de test qui cite' in user and 'LIVRABLES PRÉCÉDENTS' in user for _,user in model.calls))
  from gdhq.roles import INDEX,skill_text
  self.assertTrue(any(skill_text(INDEX['qa']) in system for system,_ in model.calls))
 def test_invalid_model_reply_never_reaches_build(self):
  row=self.connector();self.plan(row)
  self.s.engine.ai=MagicMock();self.s.engine.ai.chat.return_value='Tout est certain, ventes 100000.'
  with patch('gdhq.live.fetch',side_effect=self.response):self.s.engine._run(self.pid)
  self.assertEqual(self.s.project(self.pid)['state'],'BLOCKED')
  self.assertFalse((self.s.home/'projects'/str(self.pid)/'index.html').exists())

class NetworkPolicyTests(unittest.TestCase):
 def test_private_ipv4_ipv6_and_mixed_dns_denied(self):
  for addresses in [('127.0.0.1',),('::1',),('10.0.0.1',),('169.254.169.254',),('8.8.8.8','192.168.0.1')]:
   answers=[(socket.AF_INET,socket.SOCK_STREAM,6,'',(a,443)) for a in addresses]
   with patch('gdhq.public_http.socket.getaddrinfo',return_value=answers):
    with self.assertRaises(ConnectorError):public_addresses('example.org')
 def test_url_and_credentials_validation(self):
  for url in ['file:///etc/passwd','http://example.org','https://user:secret@example.org','https://example.org:8080','https://example.org/#key']:
   with self.assertRaises(ValueError):endpoint(url)
  with self.assertRaises(ValueError):live.clean_config({'name':'Test','kind':'API_GET','url':'https://example.org?api_key=abc'})
  with self.assertRaises(ValueError):live.clean_config({'name':'Test','kind':'MCP','url':'https://example.org','tool':'read','command':'npx something'})
 def test_remote_model_requires_cost_reservation(self):
  with self.assertRaises(ValueError):live.clean_config({'name':'Cloud','kind':'MODEL','url':'https://api.example/chat','model':'test'})

class MCPTests(unittest.TestCase):
 def config(self):return live.clean_config({'name':'Read MCP','kind':'MCP','url':'https://mcp.example/mcp','tool':'search','arguments':{'query':'{query}'}})
 def test_handshake_session_and_exact_read_tool(self):
  seen=[]
  def transport(url,headers,payload,**kwargs):
   seen.append((dict(headers),payload));method=payload['method']
   if method=='initialize':result={'protocolVersion':'2025-11-25'}
   elif method=='notifications/initialized':return b'',{}
   elif method=='tools/list':result={'tools':[{'name':'search','annotations':{'readOnlyHint':True}}]}
   else:result={'content':[{'type':'text','text':TEXT}]}
   return json.dumps({'jsonrpc':'2.0','id':payload['id'],'result':result}).encode(),{'mcp-session-id':'session'}
  with patch('gdhq.live.fetch',side_effect=transport):self.assertIn(TEXT,live.mcp_read(self.config(),'public query'))
  self.assertEqual(seen[-1][1]['params'],{'name':'search','arguments':{'query':'public query'}})
  self.assertEqual(seen[-1][0]['MCP-Session-Id'],'session');self.assertEqual(seen[-1][0]['MCP-Protocol-Version'],'2025-11-25')
 def test_tools_without_readonly_annotation_never_called(self):
  seen=[]
  def transport(url,headers,payload,**kwargs):
   seen.append(payload['method'])
   result={'protocolVersion':'2025-11-25'} if payload['method']=='initialize' else {'tools':[{'name':'search'}]}
   return json.dumps({'id':payload.get('id'),'result':result}).encode(),{}
  with patch('gdhq.live.fetch',side_effect=transport):
   with self.assertRaises(ConnectorError):live.mcp_read(self.config(),'query')
  self.assertNotIn('tools/call',seen)

class ModelAndMetricsTests(unittest.TestCase):
 setUp=LiveTests.setUp
 connector=LiveTests.connector
 def test_model_protocol_budget_and_key_handling(self):
  from gdhq.model_council import RemoteModel
  row=self.connector(kind='MODEL',url='https://api.example/v1/chat/completions',model='test-model',secret_env='TEST_API_KEY',max_cost_usd=.1,daily_budget_usd=.2,output_limit_field='max_completion_tokens')
  with patch.dict(os.environ,{'TEST_API_KEY':'private-key'}),patch('gdhq.model_council.fetch',return_value=(b'{"choices":[{"message":{"content":"Answer private-key"}}]}',{})) as transport:
   answer=RemoteModel(self.db,self.pid,row).chat('system','public source',max_tokens=100)
  self.assertNotIn('private-key',answer)
  payload=transport.call_args.args[2]
  self.assertEqual(payload['max_completion_tokens'],100);self.assertNotIn('tools',payload)
  self.assertEqual(self.db.one('SELECT count(*) AS n FROM connector_calls')['n'],1)
 def test_anthropic_response_blocks(self):
  from gdhq.model_council import RemoteModel
  row=self.connector(kind='MODEL',url='https://api.example/v1/messages',model='test-model',protocol='anthropic',max_cost_usd=.1,daily_budget_usd=.2)
  with patch('gdhq.model_council.fetch',return_value=(b'{"content":[{"type":"text","text":"Source-grounded answer"}]}',{})) as transport:
   self.assertEqual(RemoteModel(self.db,self.pid,row).chat('system','sources'),'Source-grounded answer')
  self.assertEqual(transport.call_args.args[1]['anthropic-version'],'2023-06-01')
 def test_metrics_exact_path_and_null_fail_closed(self):
  row=self.connector(metrics=[{'name':'prix','path':'product.price','unit':'EUR'}])
  with patch('gdhq.live.fetch',return_value=(json.dumps({'product':{'price':25},'description':TEXT}).encode(),{})):
   r=live.collect_one(self.db,self.s.home,self.pid,row,'query')
  metric=live.snapshot(self.db,self.pid)['measurements'][0]
  self.assertEqual(metric['value'],25);self.assertEqual(metric['evidence_id'],r['id'])
  with patch('gdhq.live.fetch',return_value=(json.dumps({'product':{'price':None}}).encode(),{})):
   with self.assertRaisesRegex(ConnectorError,'KPI'):live.collect_one(self.db,self.s.home,self.pid,row,'query')
 def test_conflicting_model_council_blocks(self):
  from gdhq.model_council import compare
  row=self.connector(kind='MODEL',url='https://api.example/v1/chat/completions',model='test-model',max_cost_usd=.1,daily_budget_usd=1)
  other=self.connector(name='Other model',kind='MODEL',url='https://api.example/v1/chat/completions',model='other-model',max_cost_usd=.1,daily_budget_usd=1)
  report=json.dumps({'verdict':'SUPPORTED','claims':[{'statement':'Prix public','evidence_id':1,'quote':TEXT,'kpi':''}],'missing':[],'recommendation':'Compare'})
  with patch('gdhq.model_council.RemoteModel.chat',side_effect=[report,report,'{"agreement":"DISAGREEMENT","reason":"contradiction"}']):
   with self.assertRaises(live.MissingResource):compare(self.db,self.pid,{'model_ids':[row['id'],other['id']],'required_kpis':[]},[{'id':1,'content':TEXT}],'sources')
  self.assertEqual(len(live.snapshot(self.db,self.pid)['decisions']),2)

class WindowsSecretTests(unittest.TestCase):
 @unittest.skipUnless(os.name=='nt','DPAPI requires Windows')
 def test_encrypted_roundtrip_does_not_persist_plaintext(self):
  from gdhq.secret_store import save,load
  with tempfile.TemporaryDirectory() as tmp,patch.dict(os.environ,{},clear=False):
   result=save(Path(tmp),'GDHQ_UNIT_TEST_KEY','unit-test-only-not-a-real-credential')
   self.assertNotIn('unit-test-only',json.dumps(result))
   self.assertNotIn(b'unit-test-only',(Path(tmp)/'credentials.dpapi').read_bytes())
   self.assertEqual(load(tmp)['GDHQ_UNIT_TEST_KEY'],'unit-test-only-not-a-real-credential')
