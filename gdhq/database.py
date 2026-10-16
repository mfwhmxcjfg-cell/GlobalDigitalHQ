"""SQLite DAL: explicit close, WAL, schema migration with non-destructive CREATE IF NOT EXISTS."""
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
import hashlib, json, sqlite3, threading

def utc():
    return datetime.now(timezone.utc).isoformat(timespec='seconds')

def dumps(value):
    return json.dumps(value, ensure_ascii=False, separators=(',', ':'))

SCHEMA = '''
CREATE TABLE IF NOT EXISTS legacy_imports(source_id TEXT NOT NULL,table_name TEXT NOT NULL,legacy_id TEXT NOT NULL,PRIMARY KEY(source_id,table_name,legacy_id));
CREATE TABLE IF NOT EXISTS schema_version(version INTEGER PRIMARY KEY, applied_at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS projects(id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT NOT NULL, brief TEXT NOT NULL, kind TEXT NOT NULL, state TEXT NOT NULL DEFAULT 'DRAFT', created_at TEXT NOT NULL, updated_at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS tasks(id INTEGER PRIMARY KEY AUTOINCREMENT, project_id INTEGER NOT NULL REFERENCES projects(id), agent_id TEXT NOT NULL, title TEXT NOT NULL, instructions TEXT NOT NULL, status TEXT NOT NULL DEFAULT 'QUEUED', result TEXT NOT NULL DEFAULT '', error TEXT NOT NULL DEFAULT '', created_at TEXT NOT NULL, updated_at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS events(id INTEGER PRIMARY KEY AUTOINCREMENT, project_id INTEGER, category TEXT NOT NULL, message TEXT NOT NULL, created_at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS decisions(id INTEGER PRIMARY KEY AUTOINCREMENT, project_id INTEGER NOT NULL REFERENCES projects(id), agent_id TEXT NOT NULL, phase TEXT NOT NULL, opinion TEXT NOT NULL, verified INTEGER NOT NULL DEFAULT 0, created_at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS gates(id INTEGER PRIMARY KEY AUTOINCREMENT, project_id INTEGER NOT NULL REFERENCES projects(id), action TEXT NOT NULL, state TEXT NOT NULL DEFAULT 'AWAITING_OWNER', justification TEXT NOT NULL DEFAULT '', created_at TEXT NOT NULL, decided_at TEXT, UNIQUE(project_id,action));
CREATE TABLE IF NOT EXISTS artifacts(id INTEGER PRIMARY KEY AUTOINCREMENT, project_id INTEGER NOT NULL REFERENCES projects(id), relative_path TEXT NOT NULL, sha256 TEXT NOT NULL, origin TEXT NOT NULL, created_at TEXT NOT NULL, UNIQUE(project_id,relative_path));
CREATE TABLE IF NOT EXISTS metrics(id INTEGER PRIMARY KEY AUTOINCREMENT, project_id INTEGER NOT NULL REFERENCES projects(id), name TEXT NOT NULL, value REAL NOT NULL, unit TEXT NOT NULL, provenance TEXT NOT NULL, observed_at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS knowledge(id INTEGER PRIMARY KEY AUTOINCREMENT, project_id INTEGER NOT NULL REFERENCES projects(id), agent_id TEXT NOT NULL, title TEXT NOT NULL, content TEXT NOT NULL, status TEXT NOT NULL DEFAULT 'UNVERIFIED', created_at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS audits(id INTEGER PRIMARY KEY AUTOINCREMENT, severity TEXT NOT NULL, result_json TEXT NOT NULL, created_at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS settings(key TEXT PRIMARY KEY, value_json TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS workforce_tasks(
 id INTEGER PRIMARY KEY AUTOINCREMENT,
 project_id INTEGER NOT NULL REFERENCES projects(id),
 manager_id TEXT NOT NULL, employee_id TEXT NOT NULL,
 title TEXT NOT NULL, deliverable TEXT NOT NULL,
 dependencies TEXT NOT NULL, risk TEXT NOT NULL DEFAULT 'NORMAL',
 status TEXT NOT NULL DEFAULT 'QUEUED', result TEXT NOT NULL DEFAULT '',
 review TEXT NOT NULL DEFAULT '', updated_at TEXT NOT NULL,
 UNIQUE(project_id, employee_id));
CREATE TABLE IF NOT EXISTS agent_messages(
 id INTEGER PRIMARY KEY AUTOINCREMENT,
 project_id INTEGER NOT NULL REFERENCES projects(id),
 sender_id TEXT NOT NULL, recipient_id TEXT NOT NULL,
 kind TEXT NOT NULL, body TEXT NOT NULL, created_at TEXT NOT NULL);
CREATE INDEX IF NOT EXISTS idx_workforce_project ON workforce_tasks(project_id,status);
CREATE INDEX IF NOT EXISTS idx_messages_project ON agent_messages(project_id,id);
CREATE INDEX IF NOT EXISTS idx_tasks_project ON tasks(project_id,status);
CREATE INDEX IF NOT EXISTS idx_events_project ON events(project_id,id);
CREATE INDEX IF NOT EXISTS idx_metrics_project ON metrics(project_id);
'''

class Database:
    def __init__(self, home):
        self.home = Path(home)
        self.home.mkdir(parents=True, exist_ok=True)
        self.path = self.home / 'global.sqlite3'
        self.lock = threading.RLock()
        with self.connect() as conn:
            conn.executescript(SCHEMA)
            conn.execute('INSERT OR IGNORE INTO schema_version VALUES (?,?)',(1,utc()))
            for key,value in {'paused':True,'emergency_stop':False,'provider':'lmstudio','model':'','audit_hours':2,'paid_enabled':False,'autonomous_mode':'DRAFT_ONLY','privacy_gate':True}.items():
                conn.execute('INSERT OR IGNORE INTO settings VALUES (?,?)',(key,dumps(value)))
    @contextmanager
    def connect(self):
        conn = sqlite3.connect(self.path, timeout=15, isolation_level='DEFERRED')
        conn.row_factory = sqlite3.Row
        try:
            conn.execute('PRAGMA foreign_keys=ON')
            conn.execute('PRAGMA busy_timeout=15000')
            conn.execute('PRAGMA journal_mode=WAL')
            with conn:
                yield conn
        finally:
            conn.close()
    def all(self,sql,params=()):
        with self.connect() as c:
            return [dict(x) for x in c.execute(sql,params)]
    def one(self,sql,params=()):
        with self.connect() as c:
            row=c.execute(sql,params).fetchone()
            return dict(row) if row else None
    def write(self,sql,params=()):
        with self.lock,self.connect() as c:
            result=c.execute(sql,params)
            return result.lastrowid
    def setting(self,key):
        result=self.one('SELECT value_json FROM settings WHERE key=?',(key,))
        if result is None:raise KeyError(key)
        return json.loads(result['value_json'])
    def set_setting(self,key,value):
        if key not in {'paused','emergency_stop','model','provider','audit_hours','autonomous_mode','privacy_gate'}:
            raise ValueError('Ce paramètre ne peut pas être modifié depuis l’application.')
        self.write('UPDATE settings SET value_json=? WHERE key=?',(dumps(value),key))
    def event(self,category,message,project_id=None):
        self.write('INSERT INTO events(project_id,category,message,created_at) VALUES(?,?,?,?)',(project_id,category,str(message)[:1200],utc()))
    def integrity(self):
        with self.connect() as c:
            return c.execute('PRAGMA integrity_check').fetchone()[0]
    def backup(self, destination):
        dest=Path(destination).resolve()
        if dest == self.path.resolve():raise ValueError('Destination identique à la base active.')
        dest.parent.mkdir(parents=True,exist_ok=True)
        with self.lock, self.connect() as origin:
            dst = sqlite3.connect(dest)
            try:origin.backup(dst)
            finally:dst.close()
        probe=sqlite3.connect(dest)
        try:
            if probe.execute('PRAGMA integrity_check').fetchone()[0]!='ok':raise RuntimeError('Sauvegarde corrompue')
        finally:probe.close()
        return {'path':str(dest),'sha256':hashlib.sha256(dest.read_bytes()).hexdigest()}
