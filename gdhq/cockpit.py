"""Persistent owner-operated cockpit. No outbound connectors or fabricated telemetry."""
from .database import utc, dumps
from .roles import ROLES, INDEX

def init(db):
    with db.connect() as c:
        c.executescript("""
CREATE TABLE IF NOT EXISTS provider_configs(id INTEGER PRIMARY KEY, name TEXT NOT NULL, kind TEXT NOT NULL, endpoint TEXT NOT NULL, secret_env TEXT NOT NULL DEFAULT '', project_id INTEGER REFERENCES projects(id), notes TEXT NOT NULL DEFAULT '', updated_at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS cockpit_tasks(id INTEGER PRIMARY KEY, project_id INTEGER NOT NULL REFERENCES projects(id), agent_id TEXT NOT NULL, title TEXT NOT NULL, status TEXT NOT NULL DEFAULT 'TODO', evidence TEXT NOT NULL DEFAULT '', updated_at TEXT NOT NULL);
""")

def snapshot(s):
    db=s.db
    tasks=db.all('SELECT * FROM cockpit_tasks ORDER BY id DESC')
    agents=[]
    for r in ROLES:
        rows=db.all('SELECT status,updated_at FROM tasks WHERE agent_id=? UNION ALL SELECT status,updated_at FROM workforce_tasks WHERE manager_id=? ORDER BY updated_at DESC',(r['id'],r['id']))
        states=[x['status'] for x in rows]
        agents.append({'id':r['id'],'name':r['name'],'department':r['department'],'status':'RUNNING' if any(x in states for x in ('RUNNING','WORKING')) else 'BLOCKED' if 'BLOCKED' in states else 'QUEUED' if 'QUEUED' in states else 'IDLE','last_activity':rows[0]['updated_at'] if rows else None,'assignments':len(rows)})
    return {'observed_at':utc(),'agents':agents,'tasks':tasks,'memory':db.all('SELECT * FROM knowledge ORDER BY id DESC LIMIT 500'),'metrics':db.all('SELECT * FROM metrics ORDER BY id DESC LIMIT 500'),'connectors':[
        {'name':'LM Studio','status':'NOT_TESTED','mode':'Local, test explicite dans Réglages','manual':'Configurer le modèle puis tester le serveur local.'},
        {'name':'Apper.io','status':'NOT_CONNECTED','mode':'Option prévue, adaptateur absent','manual':'Copier le brief dans Apper après accord ; joindre le lien ou le résultat comme preuve de tâche. Aucun build automatique.'},
        {'name':'Creatikk.io','status':'NOT_CONNECTED','mode':'Option prévue, adaptateur absent','manual':'Préparer le script localement ; produire manuellement dans Creatikk après accord et enregistrer le livrable.'},
        {'name':'Shopify / Stripe / réseaux sociaux','status':'NOT_CONNECTED','mode':'Aucun accès depuis ce cockpit','manual':'Validation humaine et intégration technique distinctes nécessaires.'}
    ]}

def mutate(s,kind,d):
    db=s.db
    if kind=='task-status':
        with db.lock,db.connect() as c:
            row=c.execute('SELECT * FROM cockpit_tasks WHERE id=?',(d.get('id'),)).fetchone()
            if not row:raise ValueError('Tâche absente')
            allowed={'TODO':{'IN_PROGRESS','BLOCKED'},'IN_PROGRESS':{'REVIEW','BLOCKED'},'BLOCKED':{'TODO'},'REVIEW':{'DONE','IN_PROGRESS'},'DONE':set()}
            state=d.get('status'); evidence=str(d.get('evidence','')).strip()
            if state not in allowed[row['status']]:raise ValueError('Transition non autorisée')
            if state in ('REVIEW','DONE','BLOCKED') and len(evidence)<5:raise ValueError('Preuve, résultat ou motif requis (5 caractères minimum)')
            c.execute('UPDATE cockpit_tasks SET status=?,evidence=?,updated_at=? WHERE id=?',(state,evidence,utc(),row['id']))
            c.execute('INSERT INTO events(project_id,category,message,created_at) VALUES(?,?,?,?)',(row['project_id'],'OWNER_TASK',f"Tâche {row['id']} : {row['status']} → {state}; {evidence[:700]}",utc()))
        return {'ok':True}
    pid=int(d.get('project_id',0))
    if not db.one('SELECT id FROM projects WHERE id=?',(pid,)):raise ValueError('Sélectionne un projet existant')
    if kind=='task':
        title=str(d.get('title','')).strip(); agent=d.get('agent_id')
        if not 3<=len(title)<=200 or agent not in INDEX:raise ValueError('Titre ou responsable invalide')
        db.write('INSERT INTO cockpit_tasks(project_id,agent_id,title,updated_at) VALUES(?,?,?,?)',(pid,agent,title,utc()))
    elif kind=='memory':
        title=str(d.get('title','')).strip(); content=str(d.get('content','')).strip()
        if not 3<=len(title)<=160 or not 5<=len(content)<=8000:raise ValueError('Titre ou contenu invalide')
        db.write('INSERT INTO knowledge(project_id,agent_id,title,content,status,created_at) VALUES(?,?,?,?,?,?)',(pid,'owner',title,content,'USER_REPORTED',utc()))
    elif kind=='metric':
        if not str(d.get('name','')).strip() or not str(d.get('unit','')).strip():raise ValueError('Nom et unité requis')
        s.add_metric(pid,{**d,'provenance':'USER_REPORTED','observed_at':utc()})
    else:raise ValueError('Opération inconnue')
    db.event('OWNER_'+kind.upper(),'Ajout manuel : '+str(d.get('title',d.get('name','')))[:200],pid)
    return {'ok':True}

def providers(s):
    import os
    rows=s.db.all('SELECT * FROM provider_configs ORDER BY id DESC')
    for row in rows:
        row['credential_status']='PRESENT_IN_PROCESS' if row['secret_env'] and os.environ.get(row['secret_env']) else 'NOT_SET'
        row['connection_status']='NOT_CONNECTED'
        row['execution_status']='ADAPTER_REQUIRED'
    return rows

def save_provider(s,d):
    import re
    from urllib.parse import urlsplit
    name=str(d.get('name','')).strip();kind=d.get('kind');endpoint=str(d.get('endpoint','')).strip();env=str(d.get('secret_env','')).strip()
    if not 2<=len(name)<=100 or kind not in ('API','MCP'):raise ValueError('Nom ou type invalide')
    u=urlsplit(endpoint)
    if len(endpoint)>500 or not u.hostname or u.username or u.password or u.query or u.fragment or (u.scheme!='https' and not(u.scheme=='http' and u.hostname in ('127.0.0.1','localhost','::1'))):raise ValueError('URL HTTPS requise (HTTP local accepté), sans identifiants, paramètres ni fragment')
    if env and not re.fullmatch(r'[A-Z][A-Z0-9_]{2,79}',env):raise ValueError('Indiquer le NOM de variable, par exemple OPENAI_API_KEY, jamais la clé')
    pid=d.get('project_id') or None
    if pid is not None:
        pid=int(pid)
        if not s.db.one('SELECT id FROM projects WHERE id=?',(pid,)):raise ValueError('Projet absent')
    notes=str(d.get('notes','')).strip()
    if len(notes)>2000:raise ValueError('Notes trop longues')
    with s.db.lock,s.db.connect() as c:
        values=(name,kind,endpoint,env,pid,notes,utc())
        if d.get('id'):
            result=c.execute('UPDATE provider_configs SET name=?,kind=?,endpoint=?,secret_env=?,project_id=?,notes=?,updated_at=? WHERE id=?',values+(int(d['id']),))
            if result.rowcount!=1:raise ValueError('Configuration absente')
        else:c.execute('INSERT INTO provider_configs(name,kind,endpoint,secret_env,project_id,notes,updated_at) VALUES(?,?,?,?,?,?,?)',values)
        c.execute('INSERT INTO events(project_id,category,message,created_at) VALUES(?,?,?,?)',(pid,'PROVIDER_CONFIG','Configuration enregistrée localement ; aucune connexion effectuée',utc()))
    return {'ok':True,'connected':False}
