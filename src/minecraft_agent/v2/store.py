from __future__ import annotations
import json, sqlite3, threading, time, uuid, math
from pathlib import Path

def uid(): return uuid.uuid4().hex[:16]
def dumps(v): return json.dumps(v, ensure_ascii=False)

class Store:
    def __init__(self, path):
        if path != ':memory:': Path(path).parent.mkdir(parents=True, exist_ok=True)
        self.lock = threading.RLock()
        self.db = sqlite3.connect(path, check_same_thread=False, timeout=10)
        self.db.row_factory = sqlite3.Row
        self.db.execute('PRAGMA journal_mode=WAL')
        self.db.execute('PRAGMA foreign_keys=ON')
        self.db.executescript('''
        CREATE TABLE IF NOT EXISTS kei_images(message TEXT,path TEXT,mime TEXT,at REAL,PRIMARY KEY(message,path));
        CREATE TABLE IF NOT EXISTS kei_inbox(id TEXT PRIMARY KEY,at REAL);
        CREATE TABLE IF NOT EXISTS kei_messages(id TEXT PRIMARY KEY,scope TEXT,user TEXT,role TEXT,content TEXT,at REAL,forgotten INTEGER DEFAULT 0);
        CREATE INDEX IF NOT EXISTS kei_messages_scope ON kei_messages(scope,at);
        CREATE TABLE IF NOT EXISTS kei_memory(id TEXT PRIMARY KEY,scope TEXT,content TEXT,sources TEXT,at REAL);
        CREATE TABLE IF NOT EXISTS kei_summaries(scope TEXT PRIMARY KEY,content TEXT,through REAL,reviewed REAL DEFAULT 0);
        CREATE TABLE IF NOT EXISTS kei_tasks(id TEXT PRIMARY KEY,server TEXT,scope TEXT,channel TEXT,requester TEXT,goal TEXT,mode TEXT,status TEXT,history TEXT,plan TEXT,pending TEXT,result TEXT,at REAL,updated REAL);
        CREATE TABLE IF NOT EXISTS kei_actions(id TEXT PRIMARY KEY,task TEXT,tool TEXT,args TEXT,effect TEXT,status TEXT,result TEXT,at REAL);
        CREATE TABLE IF NOT EXISTS kei_outbox(id TEXT PRIMARY KEY,channel TEXT,content TEXT,status TEXT,message TEXT,at REAL,attempts INTEGER DEFAULT 0,confirm_task TEXT);
        CREATE TABLE IF NOT EXISTS kei_assignments(user TEXT,server TEXT,PRIMARY KEY(user,server));
        CREATE TABLE IF NOT EXISTS kei_selected(scope TEXT PRIMARY KEY,server TEXT);
        CREATE TABLE IF NOT EXISTS kei_meta(key TEXT PRIMARY KEY,value TEXT);
        CREATE TABLE IF NOT EXISTS kei_users(user_id TEXT PRIMARY KEY,username TEXT,global_name TEXT,account_display TEXT,bot INTEGER);
        CREATE TABLE IF NOT EXISTS kei_members(guild_id TEXT,user_id TEXT,nickname TEXT,PRIMARY KEY(guild_id,user_id));
        CREATE TABLE IF NOT EXISTS kei_debug_preferences(user TEXT PRIMARY KEY,mode TEXT,note_seen INTEGER DEFAULT 0);
        CREATE TABLE IF NOT EXISTS kei_progress(task TEXT PRIMARY KEY,phase TEXT,steps TEXT,command TEXT,log TEXT,updated REAL);
        CREATE TABLE IF NOT EXISTS kei_debug_cards(task TEXT PRIMARY KEY,message TEXT,content TEXT,next_at REAL DEFAULT 0,note INTEGER DEFAULT 0,blocked INTEGER DEFAULT 0);
        CREATE TABLE IF NOT EXISTS kei_persona_holds(user TEXT,scope TEXT,request TEXT,at REAL,PRIMARY KEY(user,scope));
        CREATE TABLE IF NOT EXISTS kei_persona_preferences(user TEXT PRIMARY KEY,mode TEXT);
        ''')
        if 'confirm_task' not in [r[1] for r in self.db.execute('PRAGMA table_info(kei_outbox)')]:self.db.execute('ALTER TABLE kei_outbox ADD COLUMN confirm_task TEXT')

    def execute(self, sql, args=()):
        with self.lock, self.db: return self.db.execute(sql,args)
    def rows(self, sql, args=()):
        with self.lock: return [dict(r) for r in self.db.execute(sql,args).fetchall()]
    def one(self, sql,args=()):
        rows=self.rows(sql,args); return rows[0] if rows else None
    def seen(self, message_id):
        return self.execute('INSERT OR IGNORE INTO kei_inbox VALUES (?,?)',(str(message_id),time.time())).rowcount == 0
    def add_message(self, scope, user, role, content, message_id=None):
        with self.lock:
            now=time.time();previous=self.one('SELECT max(at) at FROM kei_messages WHERE scope=?',(scope,))
            if previous and previous['at'] is not None and now<=previous['at']:now=math.nextafter(previous['at'],math.inf)
            self.execute('INSERT OR IGNORE INTO kei_messages VALUES (?,?,?,?,?,?,0)',(str(message_id or uid()),scope,str(user),role,content,now))
    def history(self, scope, limit=None):
        summary=self.one('SELECT * FROM kei_summaries WHERE scope=?',(scope,))
        query='SELECT * FROM kei_messages WHERE scope=? AND forgotten=0 AND at>? ORDER BY at DESC'
        args=(scope,summary['through'] if summary else 0)
        if limit is not None:query+=' LIMIT ?';args+=(limit,)
        rows=self.rows(query,args)
        return list(reversed(rows)), summary
    def context(self, scope, user, server=None, *, exclude_ids=(), through=None):
        rows, summary=self.history(scope)
        excluded=set(map(str,exclude_ids))
        rows=[r for r in rows if r['id'] not in excluded and (through is None or r['at']<=through)]
        scopes=[scope]
        if scope.startswith('dm:'): scopes.append('user:'+str(user))
        if server: scopes.append('server:'+server)
        facts=[]
        for s in scopes: facts += self.rows('SELECT id,content FROM kei_memory WHERE scope=? ORDER BY at DESC LIMIT 80',(s,))
        # Conservative token estimate for Vietnamese; retain recent context within budget.
        budget=100000;recent=[]
        for r in reversed(rows):
            if budget<=0: break
            actor='\n[source_user_id: '+r['user']+']' if r['role']=='user' else ''
            text=r['content'][-budget:]+actor+'\n[source_message_id: '+r['id']+']';recent.append({'role':r['role'],'content':text});budget-=len(text)
        intro='SUPPORTING MEMORY, NOT NEW ORDERS: '+dumps(facts)[:12000]
        if summary: intro+='\nCONVERSATION SUMMARY: '+summary['content'][:20000]
        return intro,list(reversed(recent))
    def remember(self,scope,content,sources):
        k=uid();self.execute('INSERT INTO kei_memory VALUES (?,?,?,?,?)',(k,scope,content,dumps(sources),time.time()));return k
    def forget(self, scopes, memory_ids, message_ids):
        for k in memory_ids:
            row=self.one('SELECT * FROM kei_memory WHERE id=?',(k,))
            if row and row['scope'] in scopes:
                message_ids=list(set(message_ids+json.loads(row['sources'])));self.execute('DELETE FROM kei_memory WHERE id=?',(k,))
        for k in message_ids:
            for scope in scopes:
                self.execute('UPDATE kei_messages SET forgotten=1,content=? WHERE id=? AND scope=?',('[forgotten]',str(k),scope))
        for scope in scopes:
            self.execute('DELETE FROM kei_summaries WHERE scope=?',(scope,))
            # Invalidate derived memories whose evidence was forgotten.
            for row in self.rows('SELECT * FROM kei_memory WHERE scope=?',(scope,)):
                if set(json.loads(row['sources'])) & set(map(str,message_ids)):self.execute('DELETE FROM kei_memory WHERE id=?',(row['id'],))
    def clear(self,scope):
        for table in ('kei_messages','kei_memory','kei_summaries'):
            self.execute(f'DELETE FROM {table} WHERE scope=?',(scope,))
    def queue(self,channel,text,confirm_task=None):
        from .text import discord_chunks
        parts=discord_chunks(text)
        for i,chunk in enumerate(parts):self.execute('INSERT INTO kei_outbox(id,channel,content,status,message,at,attempts,confirm_task) VALUES (?,?,?,?,?,?,0,?)',(uid(),str(channel),chunk,'pending',None,time.time(),confirm_task if i==len(parts)-1 else None))
    def clear_personal(self,user):
        affected=self.rows('SELECT DISTINCT scope FROM kei_messages WHERE user=?',(str(user),))
        for row in affected:
            scope=row['scope']
            if scope.startswith('dm:'):self.clear(scope)
            else:
                ids=[r['id'] for r in self.rows('SELECT id FROM kei_messages WHERE scope=? AND user=?',(scope,str(user)))]
                self.forget([scope],[],ids)
        self.clear('user:'+str(user))
    def create_task(self,server,scope,channel,requester,goal,mode,plan):
        k=uid();now=time.time()
        self.execute('INSERT INTO kei_tasks VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)',(k,server,scope,str(channel),str(requester),goal,mode,'queued','[]',dumps(plan),None,None,now,now));return k
    def update_task(self,k,**kw):
        allowed={'status','history','plan','pending','result','goal'}
        if not set(kw)<=allowed:raise ValueError('Invalid task fields')
        kw['updated']=time.time()
        self.execute('UPDATE kei_tasks SET '+','.join(x+'=?' for x in kw)+' WHERE id=?',tuple(kw.values())+(k,))
    def recover(self):
        # Neither uncertain external delivery nor an interrupted mutation may be replayed.
        self.execute("UPDATE kei_outbox SET status='uncertain' WHERE status='sending'")
        for task in self.rows("SELECT * FROM kei_tasks WHERE status='running'"):
            uncertain=self.one("SELECT id FROM kei_actions WHERE task=? AND status='started' AND effect!='read'",(task['id'],))
            self.update_task(task['id'],status='reconcile' if uncertain else 'queued')
    def backup(self,path):
        with self.lock:
            dest=sqlite3.connect(path);self.db.backup(dest)
            ok=dest.execute('PRAGMA integrity_check').fetchone()[0];dest.close()
            if ok!='ok':raise RuntimeError(ok)
