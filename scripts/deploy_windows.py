"""Manual local deployment for an owner-controlled Windows runner. Never starts a server."""
from pathlib import Path
from contextlib import closing
import os,shutil,socket,sqlite3,datetime,json,tempfile,hashlib
ROOT=Path(__file__).resolve().parent.parent

def backup_database(source, destination):
    # A sqlite3 connection context commits/rolls back; it does not close handles.
    with closing(sqlite3.connect(Path(source).resolve().as_uri()+'?mode=ro', uri=True)) as src:
        with closing(sqlite3.connect(destination)) as dst:
            src.backup(dst)


def snapshot_database(source, destination):
    """Offline migration: recover a stable copy on the destination drive only.

    All writers must be stopped. Keep WAL and rollback journal; rebuild SHM on D:.
    Never use immutable=1, which could hide committed WAL transactions.
    """
    source=Path(source);destination=Path(destination)
    files=[source,Path(str(source)+'-wal'),Path(str(source)+'-journal')]
    def fingerprints():
        result={}
        for path in files:
            if path.is_symlink():raise ValueError('Lien SQLite refusé')
            if path.exists():
                with path.open('rb') as stream:
                    result[path.name]=hashlib.file_digest(stream,'sha256').hexdigest()
        return result
    before=fingerprints()
    with tempfile.TemporaryDirectory(prefix='sqlite-migrate-',dir=destination.parent) as temp:
        copied=Path(temp)/source.name
        for path in files:
            if path.name in before:shutil.copyfile(path,Path(temp)/path.name)
        if fingerprints()!=before:
            raise RuntimeError('Base modifiée pendant la copie : fermer toutes les instances de Global et réessayer')
        for name,digest in before.items():
            with (Path(temp)/name).open('rb') as stream:
                if hashlib.file_digest(stream,'sha256').hexdigest()!=digest:
                    raise RuntimeError('Copie SQLite incohérente : fermer toutes les instances de Global et réessayer')
        # Open the writable copy so SQLite can recover journals without touching C:.
        with closing(sqlite3.connect(copied)) as src:
            src.execute('PRAGMA temp_store=MEMORY')
            if src.execute('PRAGMA quick_check').fetchall()!=[('ok',)]:
                raise RuntimeError('Ancienne base SQLite invalide : migration arrêtée, original conservé')
            with closing(sqlite3.connect(destination)) as dst:
                src.backup(dst)
                if dst.execute('PRAGMA quick_check').fetchall()!=[('ok',)]:
                    raise RuntimeError('Sauvegarde SQLite invalide : migration arrêtée')


def migrate_data(previous, destination):
    """Copy existing owner data locally once, preserving the original."""
    previous=Path(previous);destination=Path(destination)
    if not previous.is_dir() or (destination.exists() and any(destination.iterdir())):return False
    if previous.is_symlink() or any(p.is_symlink() for p in previous.rglob('*')):raise ValueError('Lien dans les données : migration manuelle requise')
    stage=destination.parent/('data-copy-'+datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%S%f'))
    shutil.copytree(previous,stage,ignore=shutil.ignore_patterns('*.sqlite3','*.sqlite3-wal','*.sqlite3-shm','*.sqlite3-journal'))
    try:
        for db in previous.rglob('*.sqlite3'):
            target=stage/db.relative_to(previous);target.parent.mkdir(parents=True,exist_ok=True)
            snapshot_database(db, target)
        if destination.exists():destination.rmdir()
        stage.rename(destination)
    except Exception:
        shutil.rmtree(stage,ignore_errors=True)
        raise
    return True

def deploy(home, source=ROOT, previous_data=None):
    home=Path(home).resolve();source=Path(source).resolve()
    if home==source or home.is_relative_to(source) or source.is_relative_to(home):raise ValueError('Source et installation doivent être distinctes')
    if home.exists() and any(p.is_symlink() for p in [home,*home.parents]):raise ValueError('Chemin lié refusé')
    with socket.socket() as sock:
        if sock.connect_ex(('127.0.0.1',8824))==0:raise RuntimeError('Fermer Global sur le port 8824 avant déploiement')
    stamp=datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%S%f')
    home.mkdir(parents=True,exist_ok=True)
    migrated=migrate_data(previous_data,home/'data') if previous_data else False
    staged=home/('staging-'+stamp);old=home/('app-before-'+stamp);app=home/'app'
    if app.is_symlink() or (home/'data').is_symlink():raise ValueError('Chemin lié refusé')
    # Backup each database without changing the original. Runtime data never enters the source package.
    backup=home/'backups'/stamp
    for db in (home/'data').glob('*.sqlite3'):
        backup.mkdir(parents=True,exist_ok=True)
        backup_database(db, backup/db.name)
    shutil.copytree(source,staged,ignore=shutil.ignore_patterns('.git','__pycache__','*.pyc','.env','.env.*','dist','data','backups','logs','.venv','node_modules'))
    try:
        if app.exists():app.rename(old)
        staged.rename(app)
    except Exception:
        if old.exists() and not app.exists():old.rename(app)
        raise
    launcher=home/'LANCER_GLOBAL.cmd'
    launcher.write_text('@echo off\nsetlocal\ncd /d "%~dp0app"\nset "GDHQ_DATA_DIR=%~dp0data"\nset "TEMP=%~dp0temp"\nset "TMP=%~dp0temp"\nif not exist "%TEMP%" mkdir "%TEMP%"\nset "PYTHONUTF8=1"\nset "PLAYWRIGHT_BROWSERS_PATH=%~dp0browsers"\nif exist "%~dp0venv\\Scripts\\python.exe" (\n  "%~dp0venv\\Scripts\\python.exe" -m gdhq.cli serve --port 8824\n) else (\n  python -m gdhq.cli serve --port 8824\n)\nif errorlevel 1 pause\n',encoding='utf-8')
    state={'data_migrated':migrated,'launcher':str(launcher),'installed_app':str(app),'previous_app':str(old) if old.exists() else None,'database_backup':str(backup) if backup.exists() else None,'started':False,'deployed_at':stamp}
    (home/'last-deployment.json').write_text(json.dumps(state,indent=2))
    return state

if __name__=='__main__':
    import argparse
    ap=argparse.ArgumentParser();ap.add_argument('--confirm',required=True,choices=['DEPLOY_LOCAL']);ap.add_argument('--install-root',required=True);a=ap.parse_args()
    if os.name!='nt':raise SystemExit('Windows required for real deployment')
    if os.environ.get('GDHQ_DATA_DIR'):raise SystemExit('GDHQ_DATA_DIR personnalisé : sauvegarder et déployer manuellement après vérification')
    target=Path(a.install_root)
    if not target.is_absolute() or target.drive.upper()!='D:':raise SystemExit('Installation prévue uniquement sur D:')
    previous=Path(os.environ['LOCALAPPDATA'])/'GlobalDigitalHQ_Next_1_1_Desktop'/'data'
    print(json.dumps(deploy(target,previous_data=previous),indent=2))
