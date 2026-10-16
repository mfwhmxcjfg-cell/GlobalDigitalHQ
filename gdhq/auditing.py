"""Non-invasive controls; audit reports only what was actually checked."""
from pathlib import Path
import hashlib,json,sqlite3
from .database import utc,dumps
from .roles import ROLES
from .settings import ROOT

IGNORES={'MANIFEST.sha256'}
def file_digests():
    for area in ('gdhq','seed','web','scripts','tests','docs'):
        for p in sorted((ROOT/area).rglob('*')):
            if p.is_file() and '__pycache__' not in p.parts and p.suffix!='.pyc':
                yield p.relative_to(ROOT).as_posix(),hashlib.sha256(p.read_bytes()).hexdigest()
    for name in ('README.md','INSTALLER_WINDOWS.cmd','INSTALLER_SUR_BUREAU.cmd','LANCER.cmd','LANCER_BUREAU.cmd','VERIFIER.cmd','DIAGNOSTIC_BUREAU.cmd','GUIDE_INSTALLATION_BUREAU.md','requirements-sdk.txt'):
        file=ROOT/name
        if file.is_file():yield name,hashlib.sha256(file.read_bytes()).hexdigest()

def manifest_generate():
    (ROOT/'MANIFEST.sha256').write_text(''.join(f'{digest}  {rel}\n' for rel,digest in file_digests()),encoding='utf-8')

def run_audit(db,home,provider=None):
    issues=[];checks={}
    checks['database_integrity']=db.integrity()
    if checks['database_integrity']!='ok':issues.append({'level':'CRITICAL','message':'SQLite integrity_check KO'})
    checks['agent_count']=len(ROLES)
    if len(ROLES)!=40:issues.append({'level':'HIGH','message':'Catalogue des responsables incohérent'})
    expected={}
    manifest=ROOT/'MANIFEST.sha256'
    if manifest.exists():
        for line in manifest.read_text(encoding='utf-8').splitlines():
            if '  ' in line:
                digest,name=line.split('  ',1)
                expected[name]=digest
        actual=dict(file_digests())
        modified=sorted(set(actual)^set(expected) | {name for name in actual.keys()&expected.keys() if actual[name]!=expected[name]})
        checks['package_files']=len(actual)
        checks['package_mismatch']=modified[:15]
        if modified:issues.append({'level':'HIGH','message':f'Fichiers du paquet modifiés ou manquants : {len(modified)}'})
    else:
        checks['package_mismatch']=['MANIFEST.sha256 absent']
        issues.append({'level':'HIGH','message':'Manifeste d’intégrité absent'})
    checks['payment_capability']='NOT_IMPLEMENTED'
    checks['deployment_capability']='NOT_IMPLEMENTED'
    checks['local_model']='NOT_TESTED'
    if provider:
        try:
            checks['local_model']='REACHABLE' if provider.models() else 'NO_MODEL_LOADED'
        except Exception:
            checks['local_model']='UNAVAILABLE'
    checks['workforce_assignments']=db.one('SELECT count(*) AS n FROM workforce_tasks')['n']
    checks['workforce_drafts']=db.one("SELECT count(*) AS n FROM workforce_tasks WHERE status IN ('REVIEWED_DRAFT','NEEDS_OWNER_REVIEW')")['n']
    checks['workforce_blocked']=db.one("SELECT count(*) AS n FROM workforce_tasks WHERE status='BLOCKED'")['n']
    # High-risk employee output must never be reported as automatically validated.
    wrongly_approved=db.all("SELECT id FROM workforce_tasks WHERE risk='HIGH' AND status='REVIEWED_DRAFT'")
    if wrongly_approved:issues.append({'level':'HIGH','message':'Livrables sensibles sans revue propriétaire'})
    checks['open_owner_gates']=db.one("SELECT count(*) AS n FROM gates WHERE state='AWAITING_OWNER'")['n']
    checks['blocked_projects']=db.one("SELECT count(*) AS n FROM projects WHERE state='BLOCKED'")['n']
    # Safe repair: after crash, do not restart external work; flag orphan RUNNING projects for owner.
    stagnant=db.all("SELECT id FROM projects WHERE state='RUNNING'")
    checks['possibly_interrupted_projects']=[x['id'] for x in stagnant]
    if stagnant:issues.append({'level':'WARNING','message':'Projets RUNNING : vérifier si une exécution est réellement active avant reprise'})
    severity='CRITICAL' if any(i['level']=='CRITICAL' for i in issues) else 'HIGH' if any(i['level']=='HIGH' for i in issues) else 'WARNING' if issues else 'OK'
    report={'timestamp':utc(),'severity':severity,'checks':checks,'issues':issues,'limitations':['Pas de test d’intrusion réseau','Pas d’audit de dépendances tierces','Pas de certificat RGPD','Pas de vérification des ventes ou fournisseurs','Aucune modification automatique du code de production']}
    db.write('INSERT INTO audits(severity,result_json,created_at) VALUES(?,?,?)',(severity,dumps(report),utc()))
    db.event('AUDIT','Audit local : '+severity)
    return report
