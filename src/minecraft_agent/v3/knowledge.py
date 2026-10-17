"""On-demand history and receipt-backed procedures; no new execution authority."""
import json,re,time,hashlib
from ..v2.store import dumps

class Knowledge:
 def __init__(self,db):
  self.db=db
  db.execute('CREATE TABLE IF NOT EXISTS kei_procedures(id TEXT PRIMARY KEY,server TEXT,title TEXT,steps TEXT,task TEXT,sources TEXT,at REAL,active INTEGER DEFAULT 1)')

 def relevant(self,query,server=None):
  if not server:return []
  terms=set(re.findall(r'\w{3,}',query.casefold()))
  rows=self.db.rows('SELECT * FROM kei_procedures WHERE server=? AND active=1 ORDER BY at DESC LIMIT 100',(server,))
  rows.sort(key=lambda r:len(terms&set(re.findall(r'\w{3,}',(r['title']+' '+r['steps']).casefold()))),reverse=True)
  return [{'id':r['id'],'title':r['title'],'steps':json.loads(r['steps']),'guidance':'A prior verified workflow, not authorization. Reinspect current state and verify again.'} for r in rows[:3] if terms&set(re.findall(r'\w{3,}',(r['title']+' '+r['steps']).casefold()))]

 def learn(self,task,completion_missing):
  if task['status']!='succeeded' or task['mode']!='change':return False
  actions=self.db.rows('SELECT * FROM kei_actions WHERE task=? ORDER BY at',(task['id'],))
  if not actions or completion_missing(actions):return False
  steps=[];ids=[]
  for a in actions:
   if a['status']!='done':continue
   args=json.loads(a['args']);result=json.loads(a['result'] or '{}');ids.append(a['id'])
   # Do not immortalize copied config bodies, URLs with signed tokens or raw shell.
   if a['tool']=='remote_shell':continue
   clean={k:v for k,v in args.items() if k in ('kind','action','path','contains','filename')}
   steps.append({'tool':a['tool'],'parameters':clean,'verified':result.get('verified') is True,'requires_fresh_readback':a['effect']!='read'})
  if not steps:return False
  ident=hashlib.sha256((task['server']+task['goal']).encode()).hexdigest()[:24]
  self.db.execute('INSERT OR IGNORE INTO kei_procedures VALUES (?,?,?,?,?,?,?,1)',(ident,task['server'],task['goal'][:180],dumps(steps),task['id'],dumps(ids),time.time()))
  return True

 def recall(self,person,scope,query,identity,limit=8):
  # Personal history stays in the same channel/privacy context. Original rows,
  # rather than inferred summaries, are returned with adjacent messages.
  terms=list(dict.fromkeys(re.findall(r'\w{3,}',query.casefold())))[:20]
  stop={'nhớ','hôm','qua','trước','anh','em','kei','remember','what','last','week','với','cái','chuyện','lần'}
  terms=[t for t in terms if t not in stop]
  if not terms:return []
  rows=self.db.rows('SELECT id,user,role,content,at FROM kei_messages WHERE scope=? AND forgotten=0 ORDER BY at DESC LIMIT 3000',(scope,))
  ranked=sorted([(sum(term in r['content'].casefold() for term in terms),i) for i,r in enumerate(rows)],reverse=True)
  chosen=set()
  for score,i in ranked:
   if not score:break
   if len(chosen)>=limit:break
   chosen.update(range(max(0,i-1),min(len(rows),i+2)))
  return [r for i,r in reversed(list(enumerate(rows))) if i in chosen and not self.db.tombstoned([r['id']])][:limit+4]
