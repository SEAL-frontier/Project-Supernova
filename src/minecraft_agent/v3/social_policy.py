"""Small observable boundaries; no personality score can veto an assigned operation."""
import re,time,json
from .social import low_signal

def operation(text):
    return bool(re.search(r'\b(tps|mspt|ram|cpu|server|profiler|plugin|config|logs?|kick|ban|restart|backup)\b',text,re.I))

def asks_quiet(text):
    return bool(re.search(r'\b(ignore me|leave me alone|don.?t.{0,18}reply.{0,15}me|đừng.{0,12}(?:trả lời|reply).{0,12}(?:anh|tao|tôi|tớ)|bơ (?:anh|tao|tôi|tớ))\b',text,re.I))

def work_safe_reply(reply):
    if re.search(r'(?:server|crash).{0,160}(?:tự.{0,20}gõ lệnh|đừng.{0,40}(?:réo|nhờ)|khỏi.{0,30}(?:giúp|quản))',reply,re.I|re.S):
        return 'Thích chọc thì cứ chọc. Việc server em vẫn xử lý đàng hoàng.'
    return reply

class QuietPolicy:
    def __init__(self,db):self.db=db
    def key(self,scope,person):return 'social-quiet:'+person+':'+scope
    def active(self,scope,person):
        row=self.db.one('SELECT value FROM kei_meta WHERE key=?',(self.key(scope,person),))
        return bool(row and float(row['value'])>time.time())
    def choose_silence(self,scope,person,text):
        if operation(text):return False
        if scope.startswith('dm:') and low_signal(text):
            previous=self.db.one("SELECT content FROM kei_messages WHERE scope=? AND role='assistant' AND forgotten=0 ORDER BY at DESC LIMIT 1",(scope,))
            if previous and re.search(r'(?:em |đang |sẽ )(?:bơ|ignore)|không trả lời',previous['content'],re.I):return True
        key=self.key(scope,person)
        if asks_quiet(text):
            self.db.execute('INSERT OR REPLACE INTO kei_meta VALUES (?,?)',(key,str(time.time()+1800)))
            return True
        if self.active(scope,person):
            if low_signal(text) or not text.strip():return True
            # A meaningful new message resumes conversation naturally, without appeasement.
            self.db.execute('DELETE FROM kei_meta WHERE key=?',(key,))
        return False
