from .ecosystem import context as ecosystem_context
"""Coordinated manager reviews; honest BLOCKED status if local inference is absent."""
from concurrent.futures import ThreadPoolExecutor
import threading
from .database import utc
from .roles import team_for,INDEX,skill_text
from .providers import LMStudio,ModelUnavailable
from .builder import scaffold,check_project
from .governance import require_gate
from .workforce import plan as workforce_plan,run as workforce_run

STEPS=[('DISCOVERY','Étudier le marché et la demande'),('STRATEGY','Débattre des stratégies'),('WORKFORCE','Managers et employés IA'),('BUILD','Construire un prototype local'),('QUALITY','Tester le prototype'),('GOVERNANCE','Évaluer RGPD, coûts, publication')]

class Engine:
    def __init__(self,db,home,provider=None):
        self.db=db;self.home=home;self.ai=provider or LMStudio()
        self.pool=ThreadPoolExecutor(max_workers=1,thread_name_prefix='gdhq')
        self.guard=threading.Lock();self.active=set();self.pending_resume=set()
        from .live import discover
        self.research=discover
    def create(self,name,brief,kind):
        name=name.strip();brief=brief.strip()
        if not 3<=len(name)<=120 or not 10<=len(brief)<=2500:raise ValueError('Nom ou objectif invalide.')
        if kind not in ('dropshipping','webapp','content','general','services'):raise ValueError('Type de projet invalide.')
        with self.db.lock,self.db.connect() as c:
            pid=c.execute("INSERT INTO projects(name,brief,kind,state,created_at,updated_at) VALUES(?,?,?,'DRAFT',?,?)",(name,brief,kind,utc(),utc())).lastrowid
            for code,title in STEPS:
                c.execute("INSERT INTO tasks(project_id,agent_id,title,instructions,status,created_at,updated_at) VALUES(?,?,?,?,?,?,?)",(pid,'ceo' if code in ('STRATEGY','GOVERNANCE') else 'chief_of_staff',title,code,'QUEUED',utc(),utc()))
        workforce_plan(self.db,pid,kind)
        self.db.event('PROJECT','Projet créé, aucune recherche prétendument réalisée',pid)
        return pid
    def _set(self,pid,step,status,result='',error=''):
        self.db.write('UPDATE tasks SET status=?,result=?,error=?,updated_at=? WHERE project_id=? AND instructions=?',(status,result[:12000],error[:2000],utc(),pid,step))
    def begin(self,pid):
        row=self.db.one('SELECT * FROM projects WHERE id=?',(pid,))
        if not row:raise ValueError('Projet introuvable')
        if self.db.setting('emergency_stop') or self.db.setting('paused'):raise ValueError('Système en pause. Réactive le moteur après vérification.')
        with self.guard:
            if pid in self.active:raise ValueError('Ce projet est déjà en exécution.')
            self.active.add(pid)
        self.pool.submit(self._run,pid)
        return {'started':True}
    def resume_after_resource(self,pid):
        with self.guard:
            if pid in self.active:
                self.pending_resume.add(pid)
                return {'queued':True}
        return self.begin(pid)
    def _run(self,pid):
        try:
            p=self.db.one('SELECT * FROM projects WHERE id=?',(pid,))
            self.db.write('UPDATE projects SET state=?,updated_at=? WHERE id=?',('RUNNING',utc(),pid))
            self._set(pid,'DISCOVERY','RUNNING')
            from .live import check_running,MissingResource,require_resource,DECISION_SYSTEM,validate_decision
            check_running(self.db)
            model=self.db.setting('model')
            dossier=self.research(self.db,self.home,p,self.ai,model)
            evidence=dossier['context']
            ai=self.ai
            if dossier.get('reports') and dossier['reports'][0].get('connector_id'):
                from .model_council import RemoteModel
                cid=dossier['reports'][0]['connector_id']
                ai=RemoteModel(self.db,pid,self.db.one('SELECT * FROM live_connectors WHERE id=?',(cid,)))
                model=ai.config['model']
            if not model:require_resource(self.db,pid,'model','Configurer un modèle local ou un modèle API approuvé')
            self._set(pid,'DISCOVERY','DONE','Sources collectées et citations contrôlées. Vérité et adéquation commerciale à examiner.\n'+evidence)
            self._set(pid,'STRATEGY','RUNNING')
            selected=team_for(p['kind'])
            # Managers directly accountable for this project's employee tasks vote first.
            managers=[t['manager_id'] for t in self.db.all('SELECT manager_id FROM workforce_tasks WHERE project_id=? ORDER BY id',(pid,))]
            ids=list(dict.fromkeys(['ceo']+managers+['security','qa','compliance']))
            selected=[INDEX[i] for i in ids if i in INDEX][:7]
            # Two rounds: managers propose, peer reviewers challenge, CEO consolidates.
            proposals=[]
            for role in selected:
                check_running(self.db)
                instructions=(DECISION_SYSTEM+'\nTu es le responsable métier '+role['name']+'. Utilise uniquement les faits cités ; signale ce qui manque. '
                  'Aucun paiement, publication, donnée client, navigation externe ou action irréversible. '
                  'Réponds en français en 150 mots maximum.\n'+skill_text(role)+'\n'+ecosystem_context(role['id']))
                answer=ai.chat(instructions,'SOURCES :\n'+evidence+'\nProjet: '+p['name']+'\nObjectif: '+p['brief']+'\nDonne ta stratégie et trois risques. ',model,max_tokens=1000)
                try:validate_decision(answer,dossier['evidence'],[])
                except MissingResource:require_resource(self.db,pid,'analysis','Proposition de '+role['name']+' sans preuves suffisantes : compléter les sources ou choisir un modèle apte au JSON')
                self.db.write('INSERT INTO decisions(project_id,agent_id,phase,opinion,verified,created_at) VALUES(?,?,?,?,?,?)',(pid,role['id'],'PROPOSITION',answer,0,utc()))
                proposals.append(role['name']+': '+answer)
            reviews=[]
            for review_id in ('qa','security','compliance'):
                role=INDEX[review_id]
                check_running(self.db)
                answer=ai.chat('Tu es '+role['name']+'. Tu remets en question les hypothèses non prouvées. Ne certifie aucune conformité ni résultat non vérifié.','SOURCES :\n'+evidence+'\nCritique ces propositions et identifie les risques prioritaires :\n'+'\n'.join(proposals)[:12000],model,max_tokens=400)
                self.db.write('INSERT INTO decisions(project_id,agent_id,phase,opinion,verified,created_at) VALUES(?,?,?,?,?,?)',(pid,role['id'],'REVIEW',answer,0,utc()))
                reviews.append(answer)
            check_running(self.db)
            summary=ai.chat(DECISION_SYSTEM+' Tu es CEO. Synthétise les désaccords. Une contradiction matérielle impose INSUFFICIENT.', 'SOURCES :\n'+evidence+'\nMission : '+p['brief']+'\nPropositions:\n'+'\n'.join(proposals)[:10000]+'\nContre-expertises:\n'+'\n'.join(reviews)[:6000],model,max_tokens=1400)
            try:validate_decision(summary,dossier['evidence'],dossier.get('plan',{}).get('required_kpis',[]))
            except MissingResource:require_resource(self.db,pid,'decision','Synthèse CEO insuffisamment étayée ou contradictoire : compléter les preuves puis valider la reprise')
            self.db.write('INSERT INTO decisions(project_id,agent_id,phase,opinion,verified,created_at) VALUES(?,?,?,?,?,?)',(pid,'ceo','SYNTHESIS',summary,0,utc()))
            self._set(pid,'STRATEGY','DONE',summary)
            self._set(pid,'WORKFORCE','RUNNING')
            # A new evidence run must not reuse employee drafts from an older dossier.
            self.db.write("UPDATE workforce_tasks SET status='QUEUED',updated_at=? WHERE project_id=?",(utc(),pid))
            report=workforce_run(self.db,self.home,p,ai,model,evidence=evidence)
            if any(v not in ('REVIEWED_DRAFT','NEEDS_OWNER_REVIEW') for v in report['statuses'].values()):
                require_resource(self.db,pid,'deliverables','Livrables refusés ou dépendances incomplètes : examiner les revues, corriger les sources/consignes puis valider pour réessayer')
            check_running(self.db)
            self._set(pid,'WORKFORCE','DONE',str(report)[:12000])
            self._set(pid,'BUILD','RUNNING')
            scaffold(self.db,self.home,p)
            self._set(pid,'BUILD','DONE','Prototype de commerce local, sans vente ni paiement.')
            self._set(pid,'QUALITY','RUNNING')
            result=check_project(self.home,pid)
            if not result['ok']:raise RuntimeError('QA: '+'; '.join(result['issues']))
            self._set(pid,'QUALITY','DONE','Validation structurelle du prototype uniquement ; navigateurs externes non testés.')
            self._set(pid,'GOVERNANCE','RUNNING')
            for action in ('SPEND','PUBLISH','COLLECT_PERSONAL_DATA'):
                require_gate(self.db,pid,action,'Action future nécessitant validation explicite et intégration autorisée.')
            self._set(pid,'GOVERNANCE','DONE','Gates créés, aucune dépense ni publication possible.')
            self.db.write('UPDATE projects SET state=?,updated_at=? WHERE id=?',('AWAITING_OWNER',utc(),pid))
            self.db.write("UPDATE resource_requests SET status='RESOLVED',updated_at=? WHERE project_id=? AND status='APPROVED'",(utc(),pid))
            self.db.event('COMPLETE','Proposition et prototype terminés ; décisions commerciales en attente.',pid)
        except Exception as e:
            from .public_http import ConnectorError
            error=str(e)[:500]
            waiting=self.db.one('SELECT instructions FROM tasks WHERE project_id=? AND status=? ORDER BY id LIMIT 1',(pid,'RUNNING'))
            if waiting:self._set(pid,waiting['instructions'],'BLOCKED',error=error)
            self.db.write('UPDATE projects SET state=?,updated_at=? WHERE id=?',('BLOCKED',utc(),pid))
            self.db.event('BLOCKED',error,pid)
            from .live import MissingResource,require_resource
            if isinstance(e,(ModelUnavailable,ConnectorError)):
                try:require_resource(self.db,pid,'model','Moteur IA inaccessible : vérifier le modèle et sa connexion dans Réglages')
                except MissingResource:pass
        finally:
            with self.guard:
                self.active.discard(pid)
                resume=pid in self.pending_resume
                self.pending_resume.discard(pid)
            if resume and not self.db.setting('paused') and not self.db.setting('emergency_stop'):
                self.begin(pid)
    def build_demo(self,pid):
        p=self.db.one('SELECT * FROM projects WHERE id=?',(pid,))
        if not p:raise ValueError('Projet absent')
        files=scaffold(self.db,self.home,p)
        result=check_project(self.home,pid)
        self._set(pid,'BUILD','DONE','Prototype local généré sans modèle IA')
        self._set(pid,'QUALITY','DONE' if result['ok'] else 'BLOCKED',str(result))
        return {'files':list(files),'qa':result,'status':'DEMO_ONLY'}
    def improve(self,pid,request):
        request=str(request).strip()
        if len(request)<10 or len(request)>1200:raise ValueError('Instruction attendue entre 10 et 1200 caractères.')
        if self.db.setting('paused') or self.db.setting('emergency_stop'):raise ValueError('Moteur en pause ou arrêté.')
        p=self.db.one('SELECT * FROM projects WHERE id=?',(pid,))
        if not p:raise ValueError('Projet inconnu')
        from .builder import read_preview
        originals={f:read_preview(self.home,pid,f).decode('utf-8') for f in ('index.html','styles.css','app.js')}
        with self.guard:
            if pid in self.active:raise ValueError('Une intervention est déjà en cours sur ce projet.')
            self.active.add(pid)
        self.pool.submit(self._improve_run,pid,request,originals)
        self.db.event('IMPROVE_REQUEST','Demande d’amélioration en cours : '+request[:200],pid)
        return {'started':True,'status':'RUNNING'}
    def _improve_run(self,pid,request,originals):
        import json
        try:
            model=self.db.setting('model')
            system=('Tu es Senior Software Engineer. Tu dois améliorer un prototype LOCAL existant en conservant toutes ses fonctionnalités. '
            'Renvoie uniquement un objet JSON strict contenant exactement les clés "index.html", "styles.css", "app.js" et des contenus chaînes UTF-8 complets. '
            'Ne crée aucun fetch, URL externe, tracking, paiement, iframe, stockage local, import dynamique ni collecte de données personnelles. '
            'Préserve data-template, les identifiants DOM existants et la référence <script src="app.js"></script>. '
            'Préserve dans app.js refreshCart() ou renderIdeas() ou renderTasks() selon le projet. Pas de Markdown.')
            answer=self.ai.chat(system,'Demande utilisateur : '+request+'\nFichiers actuels:\n'+json.dumps(originals,ensure_ascii=False)[:18000],model,max_tokens=5000)
            if answer.startswith('```'):
                answer=answer.split('\n',1)[-1].rsplit('```',1)[0].strip()
            patch=json.loads(answer)
            from .builder import apply_candidate
            outcome=apply_candidate(self.db,self.home,pid,patch)
            self.db.event('IMPROVE_DONE','Modification vérifiée, checkpoint '+outcome['checkpoint'],pid)
        except Exception as e:
            self.db.event('IMPROVE_FAILED',str(e)[:700],pid)
        finally:
            with self.guard:self.active.discard(pid)
