"""SQLite 中的馆藏、账号、学习记录与重建任务。"""
import json
import os
import sqlite3
import threading
import time
from contextlib import contextmanager
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parents[1] / 'data'
DATA_DIR.mkdir(exist_ok=True)
DB_PATH = os.environ.get('QJQN_DB_PATH', str(DATA_DIR / 'app.sqlite3'))
_init_lock = threading.Lock()
_initialized = None


@contextmanager
def connect():
    db = sqlite3.connect(DB_PATH, timeout=20)
    db.row_factory = sqlite3.Row
    db.execute('PRAGMA foreign_keys=ON')
    try:
        with db:
            yield db
    finally:
        db.close()


def initialize():
    global _initialized
    seed = DATA_DIR / 'artifacts.json'
    stamp = (DB_PATH, seed.stat().st_mtime_ns if seed.exists() else 0)
    with _init_lock, connect() as db:
        if _initialized == stamp:
            return
        db.executescript('''
        CREATE TABLE IF NOT EXISTS users(id TEXT PRIMARY KEY, username TEXT UNIQUE NOT NULL, password TEXT NOT NULL, created REAL NOT NULL);
        CREATE TABLE IF NOT EXISTS sessions(token TEXT PRIMARY KEY, user_id TEXT REFERENCES users(id) ON DELETE CASCADE, expires REAL NOT NULL);
        CREATE TABLE IF NOT EXISTS artifacts(id TEXT PRIMARY KEY, data TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS events(id INTEGER PRIMARY KEY, user_id TEXT REFERENCES users(id), artifact_id TEXT, kind TEXT, duration INTEGER DEFAULT 0, created REAL);
        CREATE TABLE IF NOT EXISTS favorites(user_id TEXT REFERENCES users(id), artifact_id TEXT REFERENCES artifacts(id), created REAL, PRIMARY KEY(user_id,artifact_id));
        CREATE TABLE IF NOT EXISTS attempts(id INTEGER PRIMARY KEY, user_id TEXT REFERENCES users(id), task_id TEXT, answer TEXT, correct INTEGER, feedback TEXT, created REAL);
        CREATE TABLE IF NOT EXISTS reconstructions(id TEXT PRIMARY KEY, owner_id TEXT REFERENCES users(id), data TEXT NOT NULL, created REAL NOT NULL);
        CREATE TABLE IF NOT EXISTS saved_models(user_id TEXT REFERENCES users(id), task_id TEXT REFERENCES reconstructions(id), created REAL, PRIMARY KEY(user_id,task_id));
        ''')
        if seed.exists():
            for artifact in json.loads(seed.read_text(encoding='utf-8')):
                db.execute('INSERT INTO artifacts(id,data) VALUES(?,?) ON CONFLICT(id) DO UPDATE SET data=excluded.data',
                           (artifact['id'], json.dumps(artifact, ensure_ascii=False)))
        _initialized = stamp


def artifacts():
    initialize()
    with connect() as db:
        return [json.loads(row['data']) for row in db.execute('SELECT data FROM artifacts ORDER BY id')]


def artifact_by_id(artifact_id):
    initialize()
    with connect() as db:
        row = db.execute('SELECT data FROM artifacts WHERE id=?', (artifact_id,)).fetchone()
    return json.loads(row['data']) if row else None


def save_reconstruction(task_id, data, owner=None):
    initialize()
    with connect() as db:
        db.execute('INSERT INTO reconstructions VALUES(?,?,?,?) ON CONFLICT(id) DO UPDATE SET data=excluded.data',
                   (task_id, owner, json.dumps(data, ensure_ascii=False), time.time()))


def reconstruction(task_id):
    initialize()
    with connect() as db:
        row = db.execute('SELECT * FROM reconstructions WHERE id=?', (task_id,)).fetchone()
    return {'owner_id': row['owner_id'], **json.loads(row['data'])} if row else None
