from __future__ import annotations
import json, time
from ..v2.store import Store as LegacyStore, dumps, uid


class Store(LegacyStore):
    def __init__(self, path):
        super().__init__(path)
        self.memory_service = None
        self.db.executescript("""
  CREATE TABLE IF NOT EXISTS kei_schema(version INTEGER PRIMARY KEY,applied REAL);
  CREATE TABLE IF NOT EXISTS kei_people(id TEXT PRIMARY KEY,created REAL);
  CREATE TABLE IF NOT EXISTS kei_accounts(platform TEXT,account TEXT,server TEXT DEFAULT '',person TEXT,verified INTEGER DEFAULT 0,PRIMARY KEY(platform,account,server));
  CREATE TABLE IF NOT EXISTS kei_social_events(id TEXT PRIMARY KEY,person TEXT,scope TEXT,kind TEXT,content TEXT,sources TEXT,visibility TEXT,shareability TEXT,at REAL);
  CREATE INDEX IF NOT EXISTS kei_events_person ON kei_social_events(person,at);
  CREATE TABLE IF NOT EXISTS kei_relationships(person TEXT,scope TEXT,profile TEXT,updated REAL,PRIMARY KEY(person,scope));
  CREATE TABLE IF NOT EXISTS kei_episodes(id TEXT PRIMARY KEY,person TEXT,scope TEXT,title TEXT,summary TEXT,quotes TEXT,sources TEXT,visibility TEXT,shareability TEXT,importance REAL,at REAL);
  CREATE TABLE IF NOT EXISTS kei_memories(id TEXT PRIMARY KEY,person TEXT,scope TEXT,kind TEXT,content TEXT,sources TEXT,visibility TEXT,shareability TEXT,active INTEGER DEFAULT 1,at REAL);
  CREATE INDEX IF NOT EXISTS kei_memory_person ON kei_memories(person,active,at);
  CREATE TABLE IF NOT EXISTS kei_commitments(id TEXT PRIMARY KEY,person TEXT,scope TEXT,content TEXT,due REAL,status TEXT,sources TEXT);
  CREATE TABLE IF NOT EXISTS kei_group_profiles(scope TEXT PRIMARY KEY,profile TEXT,updated REAL);
  CREATE TABLE IF NOT EXISTS kei_social_preferences(person TEXT PRIMARY KEY,dm_opt_in INTEGER DEFAULT 0,timezone TEXT,sharing TEXT,muted INTEGER DEFAULT 0);
  CREATE TABLE IF NOT EXISTS kei_social_deliveries(id TEXT PRIMARY KEY,person TEXT,channel TEXT,reason TEXT,at REAL,answered INTEGER DEFAULT 0);
  CREATE TABLE IF NOT EXISTS kei_aliases(alias TEXT,person TEXT,scope TEXT,sources TEXT,PRIMARY KEY(alias,person,scope));
  CREATE TABLE IF NOT EXISTS kei_link_codes(code_hash TEXT PRIMARY KEY,discord TEXT,server TEXT,expires REAL);
  CREATE TABLE IF NOT EXISTS kei_event_meta(message TEXT PRIMARY KEY,platform TEXT,person TEXT,actor TEXT,server TEXT,scope TEXT,channel TEXT,addressed INTEGER,at REAL);
  CREATE TABLE IF NOT EXISTS kei_task_context(task TEXT PRIMARY KEY,platform TEXT,actor TEXT,server TEXT,person TEXT);
  CREATE TABLE IF NOT EXISTS kei_social_actions(id TEXT PRIMARY KEY,channel TEXT,message TEXT,kind TEXT,content TEXT,status TEXT,at REAL);
  CREATE TABLE IF NOT EXISTS kei_forget_tombstones(source TEXT PRIMARY KEY,at REAL);
  CREATE TABLE IF NOT EXISTS kei_jobs(key TEXT PRIMARY KEY,cursor REAL DEFAULT 0,last_run REAL DEFAULT 0,state TEXT DEFAULT '{}');
  CREATE TABLE IF NOT EXISTS kei_registered_servers(id TEXT PRIMARY KEY,profile TEXT,owner TEXT,updated REAL);
  CREATE TABLE IF NOT EXISTS kei_grants(subject TEXT,server TEXT,level TEXT,issuer TEXT,PRIMARY KEY(subject,server));
  CREATE TABLE IF NOT EXISTS kei_bridge_requests(id TEXT PRIMARY KEY,server TEXT,method TEXT,effect TEXT,status TEXT,result TEXT,at REAL);
  CREATE TABLE IF NOT EXISTS kei_self_opinions(id TEXT PRIMARY KEY,persona TEXT,topic TEXT,position TEXT,source TEXT,at REAL,active INTEGER DEFAULT 1);
  CREATE TABLE IF NOT EXISTS kei_mc_debug_messages(id TEXT PRIMARY KEY,server TEXT,uuid TEXT,dm_channel TEXT,dm_message TEXT,dm_blocked INTEGER DEFAULT 0,updated REAL);
  """)
        try:
            self.db.execute(
                "CREATE VIRTUAL TABLE IF NOT EXISTS kei_memory_search USING fts5(id UNINDEXED,content)"
            )
            self.fts = True
        except Exception:
            self.fts = False
        self.execute("INSERT OR IGNORE INTO kei_schema VALUES (?,?)", (3, time.time()))

    def context(self, scope, user, server=None, **kwargs):
        text, history = super().context(scope, user, server, **kwargs)
        if self.memory_service:
            text += "\n" + self.memory_service.context(user, scope, kwargs.get("through"))
        return text, history

    def social_action(self, channel, message, kind, content=""):
        if kind not in ("reply", "short_reply", "react", "silence"):
            raise ValueError("Unknown social action")
        if kind != "silence":
            self.execute(
                "INSERT INTO kei_social_actions VALUES (?,?,?,?,?,?,?)",
                (uid(), str(channel), str(message or ""), kind, content, "pending", time.time()),
            )

    def tombstoned(self, ids):
        return any(
            self.one("SELECT source FROM kei_forget_tombstones WHERE source=?", (str(x),))
            for x in ids
        )

    def recover(self):
        super().recover()
        self.execute("UPDATE kei_social_actions SET status='uncertain' WHERE status='sending'")
