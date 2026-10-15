from __future__ import annotations
import json, time
from contextlib import contextmanager
from ..v2.store import Store as LegacyStore, dumps, uid

class Store(LegacyStore):

    def __init__(self, path):
        self._atomic_depth = 0
        super().__init__(path)
        self.memory_service = None
        self.db.executescript("\n  CREATE TABLE IF NOT EXISTS kei_schema(version INTEGER PRIMARY KEY,applied REAL);\n  CREATE TABLE IF NOT EXISTS kei_people(id TEXT PRIMARY KEY,created REAL);\n  CREATE TABLE IF NOT EXISTS kei_accounts(platform TEXT,account TEXT,server TEXT DEFAULT '',person TEXT,verified INTEGER DEFAULT 0,PRIMARY KEY(platform,account,server));\n  CREATE TABLE IF NOT EXISTS kei_social_events(id TEXT PRIMARY KEY,person TEXT,scope TEXT,kind TEXT,content TEXT,sources TEXT,visibility TEXT,shareability TEXT,at REAL);\n  CREATE INDEX IF NOT EXISTS kei_events_person ON kei_social_events(person,at);\n  CREATE TABLE IF NOT EXISTS kei_relationships(person TEXT,scope TEXT,profile TEXT,updated REAL,PRIMARY KEY(person,scope));\n  CREATE TABLE IF NOT EXISTS kei_episodes(id TEXT PRIMARY KEY,person TEXT,scope TEXT,title TEXT,summary TEXT,quotes TEXT,sources TEXT,visibility TEXT,shareability TEXT,importance REAL,at REAL);\n  CREATE TABLE IF NOT EXISTS kei_memories(id TEXT PRIMARY KEY,person TEXT,scope TEXT,kind TEXT,content TEXT,sources TEXT,visibility TEXT,shareability TEXT,active INTEGER DEFAULT 1,at REAL);\n  CREATE INDEX IF NOT EXISTS kei_memory_person ON kei_memories(person,active,at);\n  CREATE TABLE IF NOT EXISTS kei_commitments(id TEXT PRIMARY KEY,person TEXT,scope TEXT,content TEXT,due REAL,status TEXT,sources TEXT);\n  CREATE TABLE IF NOT EXISTS kei_group_profiles(scope TEXT PRIMARY KEY,profile TEXT,updated REAL);\n  CREATE TABLE IF NOT EXISTS kei_social_preferences(person TEXT PRIMARY KEY,dm_opt_in INTEGER DEFAULT 0,timezone TEXT,sharing TEXT,muted INTEGER DEFAULT 0);\n  CREATE TABLE IF NOT EXISTS kei_social_deliveries(id TEXT PRIMARY KEY,person TEXT,channel TEXT,reason TEXT,at REAL,answered INTEGER DEFAULT 0);\n  CREATE TABLE IF NOT EXISTS kei_aliases(alias TEXT,person TEXT,scope TEXT,sources TEXT,PRIMARY KEY(alias,person,scope));\n  CREATE TABLE IF NOT EXISTS kei_link_codes(code_hash TEXT PRIMARY KEY,discord TEXT,server TEXT,expires REAL);\n  CREATE TABLE IF NOT EXISTS kei_event_meta(message TEXT PRIMARY KEY,platform TEXT,person TEXT,actor TEXT,server TEXT,scope TEXT,channel TEXT,addressed INTEGER,at REAL);\n  CREATE TABLE IF NOT EXISTS kei_task_context(task TEXT PRIMARY KEY,platform TEXT,actor TEXT,server TEXT,person TEXT);\n  CREATE TABLE IF NOT EXISTS kei_social_actions(id TEXT PRIMARY KEY,channel TEXT,message TEXT,kind TEXT,content TEXT,status TEXT,at REAL);\n  CREATE TABLE IF NOT EXISTS kei_forget_tombstones(source TEXT PRIMARY KEY,at REAL);\n  CREATE TABLE IF NOT EXISTS kei_jobs(key TEXT PRIMARY KEY,cursor REAL DEFAULT 0,last_run REAL DEFAULT 0,state TEXT DEFAULT '{}');\n  CREATE TABLE IF NOT EXISTS kei_registered_servers(id TEXT PRIMARY KEY,profile TEXT,owner TEXT,updated REAL);\n  CREATE TABLE IF NOT EXISTS kei_grants(subject TEXT,server TEXT,level TEXT,issuer TEXT,PRIMARY KEY(subject,server));\n  CREATE TABLE IF NOT EXISTS kei_bridge_requests(id TEXT PRIMARY KEY,server TEXT,method TEXT,effect TEXT,status TEXT,result TEXT,at REAL);\n  CREATE TABLE IF NOT EXISTS kei_self_opinions(id TEXT PRIMARY KEY,persona TEXT,topic TEXT,position TEXT,source TEXT,at REAL,active INTEGER DEFAULT 1);\n  CREATE TABLE IF NOT EXISTS kei_mc_debug_messages(id TEXT PRIMARY KEY,server TEXT,uuid TEXT,dm_channel TEXT,dm_message TEXT,dm_blocked INTEGER DEFAULT 0,updated REAL);\n  ")
        try:
            self.db.execute('CREATE VIRTUAL TABLE IF NOT EXISTS kei_memory_search USING fts5(id UNINDEXED,content)')
            self.fts = True
        except Exception:
            self.fts = False
        self.execute('INSERT OR IGNORE INTO kei_schema VALUES (?,?)', (3, time.time()))
        from .relationships import install
        install(self)

    def execute(self, sql, args=()):
        with self.lock:
            if self._atomic_depth:
                return self.db.execute(sql, args)
            return super().execute(sql, args)

    @contextmanager
    def atomic(self):
        """Savepoints keep multi-record reflection and its cursor crash-safe together."""
        with self.lock:
            name = 'kei_atomic_' + str(self._atomic_depth)
            self.db.execute('SAVEPOINT ' + name)
            self._atomic_depth += 1
            try:
                yield
                self.db.execute('RELEASE SAVEPOINT ' + name)
            except BaseException:
                self.db.execute('ROLLBACK TO SAVEPOINT ' + name)
                self.db.execute('RELEASE SAVEPOINT ' + name)
                raise
            finally:
                self._atomic_depth -= 1

    def context(self, scope, user, server=None, **kwargs):
        text, history = super().context(scope, user, server, **kwargs)
        summary = self.one('SELECT through FROM kei_summaries WHERE scope=?', (scope,))
        if summary and kwargs.get('through') is not None and (summary['through'] > kwargs['through']):
            text = text.split('\nCONVERSATION SUMMARY:', 1)[0]
        if self.memory_service:
            cfg = self.memory_service.cfg['memory']
            rows = self.rows('SELECT * FROM kei_messages WHERE scope=? AND forgotten=0 AND at<=? ORDER BY at DESC,rowid DESC LIMIT ?', (scope, kwargs.get('through') or time.time(), cfg.get('recent_turns', 96)))
            excluded = set(map(str, kwargs.get('exclude_ids', ())))
            budget = cfg.get('context_chars', 120000)
            recent = []
            for row in rows:
                if row['id'] in excluded:
                    continue
                if budget <= 0:
                    break
                content = row['content'][-min(budget, 12000):]
                content += '\n[source_message_id: ' + row['id'] + ']'
                if row['role'] == 'user':
                    content += '\n[source_user_id: ' + row['user'] + ']'
                recent.append({'role': row['role'], 'content': content})
                budget -= len(content)
            history = list(reversed(recent))
        if self.memory_service:
            text += '\n' + self.memory_service.context(user, scope, kwargs.get('through'))
        return (text, history)

    def social_action(self, channel, message, kind, content=''):
        if kind not in ('reply', 'short_reply', 'react', 'silence'):
            raise ValueError('Unknown social action')
        if kind != 'silence':
            self.execute('INSERT INTO kei_social_actions VALUES (?,?,?,?,?,?,?)', (uid(), str(channel), str(message or ''), kind, content, 'pending', time.time()))

    def tombstoned(self, ids):
        return any((self.one('SELECT source FROM kei_forget_tombstones WHERE source=?', (str(x),)) for x in ids))

    def recover(self):
        super().recover()
        self.execute("UPDATE kei_social_actions SET status='uncertain' WHERE status='sending'")
