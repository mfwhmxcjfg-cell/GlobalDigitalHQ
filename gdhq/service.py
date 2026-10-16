"""Use cases and API view models; single source of truth for observed state."""
from .roles import ROLES,team_for
from .settings import data_dir
from .database import Database
from .engine import Engine
from .providers import LMStudio
from .auditing import run_audit
from .governance import decision
from .builder import check_project
from .workforce import workforce_for

class Service:
    def __init__(self,home=None,provider=None):
        self.home=home or data_dir()
        self.db=Database(self.home)
        from .cockpit import init
        init(self.db)
        from .live import init as live_init
        live_init(self.db)
        from .secret_store import load as load_secrets
        import os
        try:os.environ.update(load_secrets(self.home))
        except Exception:self.db.event("CREDENTIALS", "Coffre Windows indisponible : réenregistrer les clés avec le compte actuel")
        if provider is not None:
            self.provider=provider
        elif self.db.setting('provider')=='ollama':
            from .providers import Ollama
            self.provider=Ollama()
        elif self.db.setting('provider')=='agents_sdk_local':
            from .sdk_provider import AgentsSDKLocal
            self.provider=AgentsSDKLocal()
        else:
            self.provider=LMStudio()
        self.engine=Engine(self.db,self.home,self.provider)
        # Non-destructive migration: previous Next projects receive employee plans,
        # but no old task is marked complete or run automatically.
        from .workforce import plan as plan_workforce
        for project in self.db.all('SELECT id,kind FROM projects'):
            if not self.db.one('SELECT id FROM workforce_tasks WHERE project_id=?',(project['id'],)):
                plan_workforce(self.db,project['id'],project['kind'])
        # Interrupted jobs are not silently resumed. Crash recovery is visible.
        for p in self.db.all("SELECT id FROM projects WHERE state='RUNNING'"):
            self.db.write('UPDATE projects SET state=? WHERE id=?',('BLOCKED',p['id']))
            self.db.write("UPDATE tasks SET status='BLOCKED',error='Processus interrompu avant la fin' WHERE project_id=? AND status='RUNNING'",(p['id'],))
            self.db.write("UPDATE workforce_tasks SET status='BLOCKED',review='Processus interrompu ; reprise manuelle requise' WHERE project_id=? AND status IN ('RUNNING','WORKING')",(p['id'],))
            self.db.event('RECOVERY','Processus précédent interrompu, reprise manuelle requise',p['id'])
    def dashboard(self):
        db=self.db
        return {'version':'1.5.0','agents':len(ROLES),'projects':db.one('SELECT count(*) AS n FROM projects')['n'],'tasks':db.one("SELECT count(*) AS n FROM tasks WHERE status='DONE'")['n'],'blocked':db.one("SELECT count(*) AS n FROM tasks WHERE status='BLOCKED'")['n'],'gates':db.one("SELECT count(*) AS n FROM gates WHERE state='AWAITING_OWNER'")['n'],'events':db.all('SELECT * FROM events ORDER BY id DESC LIMIT 20'),'settings':{k:db.setting(k) for k in ('paused','emergency_stop','model','provider','autonomous_mode')},'employees':db.one('SELECT count(*) AS n FROM workforce_tasks')['n'],'employee_drafts':db.one("SELECT count(*) AS n FROM workforce_tasks WHERE status IN ('REVIEWED_DRAFT','NEEDS_OWNER_REVIEW')")['n'],'integrations':{'LM Studio':'NON CERTIFIÉ','MCP':'CATALOGUE','Shopify':'NON CONNECTÉ','Paiement':'INACTIF','Recherche live':str(db.one('SELECT count(*) AS n FROM live_connectors WHERE approved=1')["n"])+ ' connecteur(s) autorisé(s)' }}
    def projects(self):return self.db.all('SELECT * FROM projects ORDER BY id DESC LIMIT 100')
    def project(self,pid):
        p=self.db.one('SELECT * FROM projects WHERE id=?',(pid,))
        if not p:raise ValueError('Projet absent')
        return {**p,'tasks':self.db.all('SELECT * FROM tasks WHERE project_id=? ORDER BY id',(pid,)),'decisions':self.db.all('SELECT * FROM decisions WHERE project_id=? ORDER BY id DESC',(pid,)),'artifacts':self.db.all('SELECT * FROM artifacts WHERE project_id=?',(pid,)),'gates':self.db.all('SELECT * FROM gates WHERE project_id=?',(pid,)),'metrics':self.db.all('SELECT * FROM metrics WHERE project_id=?',(pid,)),'employees':workforce_for(self.db,pid),'communications':self.db.all('SELECT * FROM agent_messages WHERE project_id=? ORDER BY id DESC LIMIT 100',(pid,)),'team':[{'id':a['id'],'name':a['name'],'department':a['department']} for a in team_for(p['kind'])]}
    def add_metric(self,pid,data):
        if not self.db.one('SELECT id FROM projects WHERE id=?',(pid,)):raise ValueError('Projet absent')
        if data.get('provenance') not in ('USER_REPORTED','IMPORTED_UNVERIFIED','OBSERVED_VERIFIED'):raise ValueError('Source non qualifiée')
        if data.get('provenance')=='OBSERVED_VERIFIED':raise PermissionError('Une donnée vérifiée exige un connecteur certifié; impossible en saisie manuelle.')
        from datetime import datetime
        datetime.fromisoformat(str(data.get('observed_at','')))
        val=float(data['value'])
        if not __import__('math').isfinite(val):raise ValueError('Valeur numérique incorrecte')
        self.db.write('INSERT INTO metrics(project_id,name,value,unit,provenance,observed_at) VALUES(?,?,?,?,?,?)',(pid,str(data['name'])[:120],val,str(data['unit'])[:30],data['provenance'],data['observed_at']))
        return {'recorded':True,'verified':False}
