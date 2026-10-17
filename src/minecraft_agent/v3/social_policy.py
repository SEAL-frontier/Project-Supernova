"""Small observable boundaries; no personality score can veto an assigned operation."""
import re,time,json
from .social import low_signal

def operation(text):
    return bool(re.search(r'\b(tps|mspt|ram|cpu|server|profiler|plugin|config|logs?|kick|ban|restart|backup)\b',text,re.I))

def asks_quiet(text):
    return bool(re.search(r'\b(ignore me|leave me alone|don.?t.{0,18}reply|forbidden.{0,30}chat|stop.{0,20}(?:chat|talk|reply)|im(?: lặng)?(?=\s*(?:đi|coi|nào|ở|tại|giùm|hộ|$))|nín|dừng chat|ngừng chat|đừng.{0,18}(?:chat|nói|trả lời|reply)|bơ (?:anh|tao|tôi|tớ))\b',text,re.I))

def work_safe_reply(reply):
    if re.search(r'(?:server|crash).{0,160}(?:tự.{0,20}gõ lệnh|đừng.{0,40}(?:réo|nhờ)|khỏi.{0,30}(?:giúp|quản))',reply,re.I|re.S):
        return 'Thích chọc thì cứ chọc. Việc server em vẫn xử lý đàng hoàng.'
    return reply

class QuietPolicy:
    def __init__(self,db):
        self.db=db;self.owner=None
        db.execute('CREATE TABLE IF NOT EXISTS kei_quiet_rules(scope TEXT,person TEXT,issuer TEXT,expires REAL,reason TEXT,PRIMARY KEY(scope,person))')
    def key(self,scope,person):return 'social-quiet:'+person+':'+scope
    def active(self,scope,person):
        if self.db.one('SELECT scope FROM kei_quiet_rules WHERE scope=? AND person IN (?,?) AND (expires=0 OR expires>?)',(scope,person,'*',time.time())):return True
        row=self.db.one('SELECT value FROM kei_meta WHERE key=?',(self.key(scope,person),))
        return bool(row and float(row['value'])>time.time())
    def choose_silence(self,scope,person,text):
        metadata=self.db.one('SELECT data FROM kei_social_context WHERE person=? AND scope=?',(person,scope)) if self.db.one("SELECT name FROM sqlite_master WHERE name='kei_social_context'") else None
        rights=json.loads(metadata['data']) if metadata else {}
        manager=rights.get('guild_owner') or rights.get('channel_manager') or person=='discord:'+str(self.owner)
        channel_request=bool(re.search(r'(?:here|channel|kênh|ở đây|tại đây)',text,re.I))
        target='*' if scope.startswith('guild:') and channel_request and manager else person
        release=bool(re.search(r'(?:được|cho phép).{0,15}(?:nói|chat|trả lời).{0,8}lại|(?:can|may).{0,12}(?:chat|talk).{0,12}again|unmute|nói chuyện.{0,15}tiếp|chat.{0,8}again',text,re.I))
        if release:
            if manager and self.db.one("SELECT issuer FROM kei_quiet_rules WHERE scope=? AND person='*'",(scope,)):target='*'
            self.db.execute('DELETE FROM kei_quiet_rules WHERE scope=? AND person=?',(scope,target));self.db.execute('DELETE FROM kei_meta WHERE key=?',(self.key(scope,person),));return False
        if asks_quiet(text):
            duration=re.search(r'(\d+)\s*(phút|minutes?|mins?|giờ|hours?)',text,re.I)
            seconds=min(30*86400,int(duration[1])*(3600 if duration[2].casefold() in ('giờ','hour','hours') else 60)) if duration else 1800
            indefinite=bool(re.search(r'until|tới khi|đến khi|from now on',text,re.I))
            self.db.execute('INSERT OR REPLACE INTO kei_quiet_rules VALUES (?,?,?,?,?)',(scope,target,person,0 if indefinite else time.time()+seconds,text[:250]))
            return not operation(text)
        # One necessary response never silently removes a persistent quiet rule.
        if self.active(scope,person):return not (operation(text) or re.search(r'\b(help|giúp|cứu|khẩn|cần|urgent)\b|\?',text,re.I))
        if scope.startswith('dm:') and low_signal(text):
            previous=self.db.one("SELECT content FROM kei_messages WHERE scope=? AND role='assistant' AND forgotten=0 ORDER BY at DESC LIMIT 1",(scope,))
            if previous and re.search(r'(?:em |đang |sẽ )(?:bơ|ignore)|không trả lời',previous['content'],re.I):return True
        key=self.key(scope,person)
        return False
