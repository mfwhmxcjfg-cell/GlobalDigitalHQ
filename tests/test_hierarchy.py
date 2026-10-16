"""Behavioral tests for the Jarvis/manager/employee delegation pattern from the supplied video."""
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase
from gdhq.service import Service
from gdhq.workforce import WORKFORCE, plan, run
from gdhq.roles import INDEX
from gdhq.providers import ModelUnavailable

class FakeLocalModel:
    def __init__(self): self.calls=[]
    def chat(self,system,user,model,max_tokens=300):
        self.calls.append((system,user,model))
        return ('Brouillon de travail non certifié. Source requise. '
                'Aucune vente, facture, réservation ou dépense réelle n’est confirmée. '
                'Vérifier avec le responsable avant diffusion. ')*2
    def models(self): return ['test-local-model']

class WorkforceTest(TestCase):
    def setUp(self):
        self.tmp=TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.model=FakeLocalModel()
        self.s=Service(Path(self.tmp.name),self.model)
    def create(self,kind='services'):
        return self.s.engine.create('Projet entreprise','Préparer les métiers et leurs opérations de façon sûre',kind)
    def prepare_model(self):
        self.s.db.set_setting('paused',False)
        self.s.db.set_setting('model','test-local-model')

    def test_40_managers_and_worker_plan_all_types(self):
        self.assertEqual(self.s.dashboard()['agents'],40)
        for typ,jobs in WORKFORCE.items():
            p=self.create(typ)
            team=self.s.project(p)['employees']
            self.assertEqual(len(team),len(jobs))
            self.assertEqual({x['employee_id'] for x in team},{j.employee for j in jobs})
            self.assertTrue(all(t['status']=='QUEUED' for t in team))
            self.assertTrue(all(t['manager_id'] in INDEX for t in team))
            self.assertEqual(len(self.s.project(p)['communications']),1)
    def test_delegation_graph_video(self):
        p=self.create()
        assignments={t['employee_id']:t for t in self.s.project(p)['employees']}
        self.assertEqual(assignments['devis']['manager_id'],'sales')
        self.assertEqual(assignments['mails']['manager_id'],'sales')
        self.assertEqual(assignments['factures']['manager_id'],'accounting')
        self.assertEqual(assignments['planning']['manager_id'],'operations')
        self.assertEqual(assignments['factures']['dependencies'],['devis'])
    def test_production_of_actual_drafts_and_manager_review(self):
        p=self.create();self.prepare_model()
        record=self.s.db.one('SELECT * FROM projects WHERE id=?',(p,))
        done=run(self.s.db,self.s.home,record,self.model,'test-local-model')
        self.assertEqual(len(done['processed']),5)
        team=self.s.project(p)['employees']
        self.assertTrue(all(t['status'] in ('REVIEWED_DRAFT','NEEDS_OWNER_REVIEW') for t in team))
        self.assertEqual(next(t for t in team if t['employee_id']=='factures')['status'],'NEEDS_OWNER_REVIEW')
        for t in team:
            self.assertTrue((Path(self.s.home)/'projects'/str(p)/'team'/(t['employee_id']+'.md')).is_file())
            self.assertGreater(len(t['review']),15)
        msgs=self.s.project(p)['communications']
        self.assertTrue(any(x['kind']=='MANAGER_REPORT' and x['recipient_id']=='ceo' for x in msgs))
        self.assertTrue(any(x['kind']=='DELIVERABLE' and x['recipient_id']=='accounting' for x in msgs))
        self.assertEqual(self.s.db.one("SELECT COUNT(*) AS n FROM artifacts WHERE project_id=? AND origin=?",(p,'LOCAL_MODEL_UNVERIFIED'))['n'],5)
    def test_idempotent_worker_execution(self):
        p=self.create();self.prepare_model()
        record=self.s.db.one('SELECT * FROM projects WHERE id=?',(p,))
        run(self.s.db,self.s.home,record,self.model,'test-local-model')
        old=len(self.model.calls)
        report=run(self.s.db,self.s.home,record,self.model,'test-local-model')
        self.assertEqual(report['processed'],[])
        self.assertEqual(len(self.model.calls),old)
    def test_no_model_or_pause_no_execution(self):
        p=self.create();record=self.s.db.one('SELECT * FROM projects WHERE id=?',(p,))
        with self.assertRaises(ModelUnavailable):run(self.s.db,self.s.home,record,self.model,'')
        self.assertEqual(len(self.model.calls),0)
        self.prepare_model();self.s.db.set_setting('paused',True)
        with self.assertRaises(PermissionError):run(self.s.db,self.s.home,record,self.model,'test-local-model')
        self.assertEqual(len(self.model.calls),0)
    def test_full_engine_run_with_workforce(self):
        p=self.create('services');self.prepare_model()
        self.s.engine._run(p)
        info=self.s.project(p)
        self.assertEqual(info['state'],'AWAITING_OWNER')
        self.assertEqual(next(x for x in info['tasks'] if x['instructions']=='WORKFORCE')['status'],'DONE')
        self.assertEqual(len([x for x in info['employees'] if x['status'] in ('REVIEWED_DRAFT','NEEDS_OWNER_REVIEW')]),5)
        self.assertTrue(any(g['action']=='SPEND' for g in info['gates']))
        self.assertEqual(self.s.db.setting('paid_enabled'),False)
    def test_blocked_without_local_model_is_honest(self):
        p=self.create();self.s.db.set_setting('paused',False)
        self.s.engine._run(p)
        info=self.s.project(p)
        self.assertEqual(info['state'],'BLOCKED')
        self.assertTrue(all(t['status']=='QUEUED' for t in info['employees']))
    def test_failsafe_on_provider_exception(self):
        class BrokenModel(FakeLocalModel):
            def chat(self,*args,**kwargs):raise ModelUnavailable('test fallback')
        p=self.create();self.prepare_model()
        with self.assertRaises(ModelUnavailable):
            run(self.s.db,self.s.home,self.s.db.one('SELECT * FROM projects WHERE id=?',(p,)),BrokenModel(),'test-local-model')
        self.assertEqual(self.s.project(p)['employees'][0]['status'],'BLOCKED')
        self.assertFalse((Path(self.s.home)/'projects'/str(p)/'team'/'devis.md').exists())
    def test_restart_keeps_messages_and_reports(self):
        p=self.create();self.prepare_model()
        run(self.s.db,self.s.home,self.s.db.one('SELECT * FROM projects WHERE id=?',(p,)),self.model,'test-local-model')
        fresh=Service(self.s.home,self.model)
        self.assertEqual(len(fresh.project(p)['employees']),5)
        self.assertGreater(len(fresh.project(p)['communications']),8)
    def test_never_calls_external_operations(self):
        p=self.create();self.prepare_model()
        run(self.s.db,self.s.home,self.s.db.one('SELECT * FROM projects WHERE id=?',(p,)),self.model,'test-local-model')
        self.assertEqual(self.s.db.all('SELECT * FROM gates WHERE project_id=?',(p,)),[])
        self.assertFalse(any('https://' in user for _,user,_ in self.model.calls))
