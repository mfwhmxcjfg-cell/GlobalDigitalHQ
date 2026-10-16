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
        self.guard=threading.Lock();self.active=set()
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
    def _run(self,pid):
        try:
            p=self.db.one('SELECT * FROM projects WHERE id=?',(pid,))
            self.db.write('UPDATE projects SET state=?,updated_at=? WHERE id=?',('RUNNING',utc(),pid))
            self._set(pid,'DISCOVERY','RUNNING')
            self.db.event('EVIDENCE','Recherche live non connectée : seules des hypothèses seront proposées.',pid)
            self._set(pid,'DISCOVERY','DONE','Sources externes : NON VERIFIÉES. Aucune donnée de tendance ou vente importée.')
            self._set(pid,'STRATEGY','RUNNING')
            selected=team_for(p['kind'])
            # Managers directly accountable for this project's employee tasks vote first.
            managers=[t['manager_id'] for t in self.db.all('SELECT manager_id FROM workforce_tasks WHERE project_id=? ORDER BY id',(pid,))]
            ids=list(dict.fromkeys(['ceo']+managers+['security','qa','compliance']))
            selected=[INDEX[i] for i in ids if i in INDEX][:7]
            model=self.db.setting('model')
            if not model:
                raise ModelUnavailable('Aucun modèle LM Studio sélectionné. Ouvre Moteur & réglages.')
            # Two rounds: managers propose, peer reviewers challenge, CEO consolidates.
            proposals=[]
            for role in selected:
                if self.db.setting('emergency_stop'):raise RuntimeError('Arrêt d’urgence.')
                instructions=('Tu es le responsable métier '+role['name']+'. Tu dois distinguer faits vérifiés, hypothèses et inconnues. '
                  'Aucun paiement, publication, donnée client, navigation externe ou action irréversible. '
                  'Réponds en français en 150 mots maximum.\n'+skill_text(role)[:1600]+'\n'+ecosystem_context(role['id']))
                answer=self.ai.chat(instructions,'Projet: '+p['name']+'\nObjectif: '+p['brief']+'\nDonne ta stratégie et trois risques. ',model,max_tokens=300)
                self.db.write('INSERT INTO decisions(project_id,agent_id,phase,opinion,verified,created_at) VALUES(?,?,?,?,?,?)',(pid,role['id'],'PROPOSITION',answer,0,utc()))
                proposals.append(role['name']+': '+answer)
            reviews=[]
            for review_id in ('qa','security','compliance'):
                role=INDEX[review_id]
                answer=self.ai.chat('Tu es '+role['name']+'. Tu remets en question les hypothèses non prouvées. Ne certifie aucune conformité ni résultat non vérifié.','Critique ces propositions et identifie les risques prioritaires :\n'+'\n'.join(proposals)[:12000],model,max_tokens=400)
                self.db.write('INSERT INTO decisions(project_id,agent_id,phase,opinion,verified,created_at) VALUES(?,?,?,?,?,?)',(pid,role['id'],'REVIEW',answer,0,utc()))
                reviews.append(answer)
            summary=self.ai.chat('Tu es CEO. Synthétise les désaccords sans inventer les preuves manquantes. Propose une stratégie testable, pas une validation commerciale.', 'Mission : '+p['brief']+'\nPropositions:\n'+'\n'.join(proposals)[:10000]+'\nContre-expertises:\n'+'\n'.join(reviews)[:6000],model,max_tokens=650)
            self.db.write('INSERT INTO decisions(project_id,agent_id,phase,opinion,verified,created_at) VALUES(?,?,?,?,?,?)',(pid,'ceo','SYNTHESIS',summary,0,utc()))
            self._set(pid,'STRATEGY','DONE',summary)
            self._set(pid,'WORKFORCE','RUNNING')
            report=workforce_run(self.db,self.home,p,self.ai,model)
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
            self.db.event('COMPLETE','Proposition et prototype terminés ; décisions commerciales en attente.',pid)
        except Exception as e:
            error=str(e)[:500]
            waiting=self.db.one('SELECT instructions FROM tasks WHERE project_id=? AND status=? ORDER BY id LIMIT 1',(pid,'RUNNING'))
            if waiting:self._set(pid,waiting['instructions'],'BLOCKED',error=error)
            self.db.write('UPDATE projects SET state=?,updated_at=? WHERE id=?',('BLOCKED',utc(),pid))
            self.db.event('BLOCKED',error,pid)
        finally:
            with self.guard:self.active.discard(pid)
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
