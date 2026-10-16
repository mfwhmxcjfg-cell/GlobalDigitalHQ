"""Read-only import of safe fields from a legacy SQLite, never secrets or credentials."""
from pathlib import Path
import sqlite3, hashlib
from .database import utc

def inspect(source):
    p=Path(source).expanduser().resolve()
    if not p.is_file():raise ValueError('Base source introuvable.')
    db=sqlite3.connect(f'file:{p.as_posix()}?mode=ro',uri=True)
    db.row_factory=sqlite3.Row
    try:
        tabs={x[0] for x in db.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        result={'source':str(p),'tables':sorted(tabs),'projects':[], 'metrics':[], 'warnings':['Aucun secret, connecteur, token, mot de passe ni base cliente importé.']} 
        if 'projects' in tabs:
            fields={x[1] for x in db.execute('PRAGMA table_info(projects)')}
            if {'name','objective'}.issubset(fields):
                result['projects']=[{'legacy_id':x['id'] if 'id' in fields else x['rowid'],'name':str(x['name'])[:120],'brief':str(x['objective'] or '')[:2500]} for x in db.execute('SELECT rowid,* FROM projects LIMIT 100')]
            elif {'name','brief'}.issubset(fields):
                result['projects']=[{'legacy_id':x['id'] if 'id' in fields else x['rowid'],'name':str(x['name'])[:120],'brief':str(x['brief'] or '')[:2500]} for x in db.execute('SELECT rowid,* FROM projects LIMIT 100')]
        if 'metrics' in tabs:
            fields={x[1] for x in db.execute('PRAGMA table_info(metrics)')}
            if {'project_id','name','value','unit'}.issubset(fields):
                query='SELECT rowid,* FROM metrics ORDER BY rowid LIMIT 1000'
                for x in db.execute(query):
                    try:
                        value=float(x['value'])
                        if not __import__('math').isfinite(value):continue
                        result['metrics'].append({'legacy_id':str(x['rowid']),'project_id':int(x['project_id']),'name':str(x['name'])[:120],'value':value,'unit':str(x['unit'])[:30],'observed_at':str(x['observed'] if 'observed' in fields else x['observed_at'] if 'observed_at' in fields else utc())})
                    except (ValueError,TypeError,KeyError):continue
        return result
    finally:db.close()

def import_projects(db,source):
    report=inspect(source)
    inserted=0
    imported_metrics=0
    source_id=hashlib.sha256(Path(source).expanduser().resolve().as_posix().encode()).hexdigest()
    # Dedupe name+brief makes repeat safe, no overwrite.
    for project in report['projects']:
        if not project['name'] or not project['brief']:continue
        found=db.one('SELECT id FROM projects WHERE name=? AND brief=?',(project['name'],project['brief']))
        if found:continue
        db.write('INSERT INTO projects(name,brief,kind,state,created_at,updated_at) VALUES(?,?,?,?,?,?)',(project['name'],project['brief'],'general','IMPORTED_READ_ONLY',utc(),utc()))
        inserted+=1
    # Import metrics only when project row ordering maps securely to legacy id and with UNVERIFIED provenance.
    project_map={}
    for proj in report['projects']:
        match=db.one('SELECT id FROM projects WHERE name=? AND brief=?',(proj['name'],proj['brief']))
        if match:project_map[proj['legacy_id']]=match['id']
    for metric in report['metrics']:
        new_pid=project_map.get(metric['project_id'])
        if not new_pid:continue
        with db.lock,db.connect() as c:
            existing=c.execute('SELECT 1 FROM legacy_imports WHERE source_id=? AND table_name=? AND legacy_id=?',(source_id,'metrics',metric['legacy_id'])).fetchone()
            if existing:continue
            c.execute('INSERT INTO metrics(project_id,name,value,unit,provenance,observed_at) VALUES(?,?,?,?,?,?)',(new_pid,metric['name'],metric['value'],metric['unit'],'IMPORTED_UNVERIFIED',metric['observed_at']))
            c.execute('INSERT INTO legacy_imports(source_id,table_name,legacy_id) VALUES(?,?,?)',(source_id,'metrics',metric['legacy_id']))
            imported_metrics+=1
    db.event('MIGRATION',f'{inserted} projet(s) et {imported_metrics} mesures non vérifiées importés')
    return {'imported':inserted,'metrics_imported':imported_metrics,'candidates':len(report['projects']),'warnings':report['warnings']}
