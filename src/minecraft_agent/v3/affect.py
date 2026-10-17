"""Persistent character affect: daily disposition, personal mood, sourced bonds.

These are fictional context parameters, never user obligations or authority.
"""
from __future__ import annotations
import hashlib,json,math,re,time
from datetime import datetime
from zoneinfo import ZoneInfo
from ..v2.store import dumps

AXES=('energy','sociability','patience','playfulness','valence')
BASE=dict(energy=.58,sociability=.55,patience=.6,playfulness=.58,valence=.56)
MUTUAL=re.compile(r'(?:làm|là|thành|muốn.{0,15})(?:.{0,12})(?:người yêu|bạn gái|bạn trai)|(?:be|you.re|are).{0,15}(?:my girlfriend|my boyfriend|dating)|hẹn hò|yêu (?:em|kei)|i love you',re.I)
END=re.compile(r'chia tay|break\s*up|đừng.{0,15}(?:yêu|tán|thả thính)|không.{0,18}(?:yêu|hẹn hò)|stop.{0,15}(?:romance|flirting)|just friends|chỉ là bạn',re.I)
OVERRIDE=re.compile(r'\b(force|override|continue|resume|tiếp(?: tục)?(?: đi)?|làm đi|làm luôn|cứ làm|chạy đi|xin lỗi|sorry|thôi mà|please|làm ơn)\b',re.I)
URGENT=re.compile(r'crash|sập|down|khẩn|urgent|mất dữ liệu|data loss|restore|recovery|khôi phục|cancel|hủy|dừng',re.I)

class Affect:
 def __init__(self,db,relationships,cfg):
  self.db=db;self.rel=relationships;self.cfg=cfg
  db.db.executescript('''
  CREATE TABLE IF NOT EXISTS kei_affect_days(persona TEXT,day TEXT,state TEXT,at REAL,PRIMARY KEY(persona,day));
  CREATE TABLE IF NOT EXISTS kei_affect_events(id TEXT PRIMARY KEY,person TEXT,scope TEXT,state TEXT,sources TEXT,at REAL);
  CREATE INDEX IF NOT EXISTS kei_affect_person_time ON kei_affect_events(person,at);
  CREATE TABLE IF NOT EXISTS kei_bonds(person TEXT PRIMARY KEY,state TEXT,updated REAL);
  CREATE TABLE IF NOT EXISTS kei_bond_events(id TEXT PRIMARY KEY,person TEXT,kind TEXT,state TEXT,sources TEXT,at REAL);
  CREATE TABLE IF NOT EXISTS kei_bond_actions(event TEXT PRIMARY KEY,action TEXT);
  CREATE UNIQUE INDEX IF NOT EXISTS kei_one_exclusive_partner ON kei_bonds((1)) WHERE json_extract(state,'$.kind')='mutual';
  CREATE TABLE IF NOT EXISTS kei_social_work_holds(id TEXT PRIMARY KEY,person TEXT,scope TEXT,server TEXT,payload TEXT,status TEXT,at REAL);
  ''')
  if not db.one("SELECT value FROM kei_meta WHERE key='affect-legacy-imported-v1'"):
   for row in db.rows('SELECT * FROM kei_social_moods WHERE at>? ORDER BY at',(time.time()-7200,)):
    self.update(row['person'],row['scope'],row['tone'],[row['source']],now=row['at'])
   db.execute("INSERT OR REPLACE INTO kei_meta VALUES ('affect-legacy-imported-v1','1')")

 def day(self,now=None):
  now=time.time() if now is None else now
  local=datetime.fromtimestamp(now,ZoneInfo(self.cfg.get('timezone','Asia/Ho_Chi_Minh')))
  persona=hashlib.sha256(self.cfg.get('persona','').encode()).hexdigest()[:20];day=local.date().isoformat()
  row=self.db.one('SELECT state FROM kei_affect_days WHERE persona=? AND day=?',(persona,day))
  if row:return json.loads(row['state'])
  previous=self.db.one('SELECT state FROM kei_affect_days WHERE persona=? AND day<? ORDER BY day DESC LIMIT 1',(persona,day))
  prior=json.loads(previous['state']) if previous else BASE
  state={}
  for key in AXES:
   sample=int(hashlib.sha256((persona+day+key).encode()).hexdigest()[:8],16)/0xffffffff-.5
   state[key]=round(max(.25,min(.8,BASE[key]+(prior.get(key,BASE[key])-BASE[key])*.55+sample*.16)),4)
  self.db.execute('INSERT OR IGNORE INTO kei_affect_days VALUES (?,?,?,?)',(persona,day,dumps(state),now))
  return json.loads(self.db.one('SELECT state FROM kei_affect_days WHERE persona=? AND day=?',(persona,day))['state'])

 def update(self,person,scope,tone,sources,event=None,now=None):
  if not self.cfg.get("social",{}).get("dynamic_mood",True):return False
  now=time.time() if now is None else now
  rows=self.rel._evidence(person,scope,sources)
  if not rows or tone not in ('calm','playful','warm','annoyed','sad','shy','excited'):return False
  ident=hashlib.sha256((person+dumps(sorted(sources))).encode()).hexdigest()[:24]
  if self.db.one('SELECT id FROM kei_affect_events WHERE id=?',(ident,)):return False
  previous=self.db.one('SELECT at FROM kei_affect_events WHERE person=? ORDER BY at DESC LIMIT 1',(person,))
  if previous and now-previous['at']<20:return False
  shifts={'calm':{},'playful':{'playfulness':.07,'valence':.03},'warm':{'valence':.09,'patience':.05,'sociability':.04},'annoyed':{'patience':-.1,'valence':-.06},'sad':{'energy':-.06,'valence':-.08},'shy':{'playfulness':.03,'sociability':-.03,'valence':.05},'excited':{'energy':.08,'sociability':.07,'valence':.06}}[tone]
  # A character's own sulking moves transient mood, never durable trust by itself.
  self.db.execute('INSERT INTO kei_affect_events VALUES (?,?,?,?,?,?)',(ident,person,scope,dumps({'tone':tone,'shifts':shifts}),dumps(sources),now))
  return True

 def state(self,person,scope,now=None):
  now=time.time() if now is None else now;values=self.day(now).copy();last=None
  # A bounded shared disposition, without transferring blame or private stories.
  recent=self.db.rows('SELECT person,state,sources FROM kei_affect_events WHERE at>? AND at<=? ORDER BY at DESC LIMIT 200',(now-7200,now));seen=set();global_shift={k:0 for k in AXES}
  for event in recent:
   if event['person']==person or event['person'] in seen or self.db.tombstoned(json.loads(event['sources'])):continue
   seen.add(event['person'])
   for key,delta in json.loads(event['state']).get('shifts',{}).items():global_shift[key]+=delta*.25
  for key,delta in global_shift.items():values[key]+=max(-.12,min(.12,delta))
  sharing=self.db.one('SELECT sharing FROM kei_social_preferences WHERE person=?',(person,))
  strict=sharing and sharing['sharing']=='strict'
  rows=self.db.rows('SELECT * FROM kei_affect_events WHERE person=? AND at<=? AND at>? ORDER BY at',(person,now,now-2*86400))
  for row in rows:
   if (strict and row['scope']!=scope) or self.db.tombstoned(json.loads(row['sources'])):continue
   state=json.loads(row['state']);age=max(0,now-row['at']);decay=math.pow(.5,age/(5400 if state['tone']=='annoyed' else 14400))
   for key,delta in state['shifts'].items():values[key]+=delta*decay
   if age<7200:last=state['tone']
  values={k:round(max(.08,min(.92,v)),3) for k,v in values.items()}
  hour=datetime.fromtimestamp(now,ZoneInfo(self.cfg.get('timezone','Asia/Ho_Chi_Minh'))).hour
  values['energy']=round(max(.08,min(.92,values['energy']+(-.08 if hour>=23 or hour<6 else .02))),3)
  return {'dimensions':values,'recent_tone':last,'bond':self.bond(person,scope)}

 def context(self,person,scope,now=None):
  if not self.cfg.get("social",{}).get("dynamic_mood",True):return {"guidance":"Use core persona and relationship context; dynamic mood is disabled."}
  state=self.state(person,scope,now);v=state['dimensions']
  describe=lambda n:'lower' if n<.42 else 'higher' if n>.65 else 'moderate'
  return {'daily_disposition':{k:describe(n) for k,n in v.items()},'recent_tone':state['recent_tone'],
    'personal_connection':state['bond'] if scope.startswith(('dm:','mc-private:')) else {'label':'private'},'global_relationship':self.partner_context(person),
    'guidance':'Fictional character state, not a real-life experience. Core persona stays intact. Warmth can be sincere without a mandatory tsundere punchline. Occasional playful sulking is valid even with close people; never mechanically repeat it. Let context and this person matter more than daily variation. No invented offscreen events, guilt, exclusivity or demands for affection.'}

 def bond(self,person,scope='global'):
  row=self.db.one('SELECT state FROM kei_bonds WHERE person=?',(person,))
  state=json.loads(row['state']) if row else {'kind':'none','label':None}
  return state if not self.db.tombstoned(state.get('sources',[])) else {'kind':'none','label':None}

 def bond_candidate(self,person,scope,proposal,sources,profile,now=None):
  now=time.time() if now is None else now
  if not scope.startswith(('dm:','mc-private:')) or not isinstance(proposal,dict):return False
  kind=proposal.get('kind');rows=self.rel._evidence(person,scope,sources)
  if kind not in ('ambiguous','crush','mutual','breakup') or not rows:return False
  own=' '.join(r['content'].split('[REPLIED MESSAGE',1)[0] for r in rows if r['role']=='user' and self.rel.identity.person_for_user(r['user'])==person)
  old=self.bond(person);prefs=self.rel.preferences(person)
  if kind=='breakup':return bool(old['kind'] in ('ambiguous','crush','mutual') and (END.search(own) or (profile.get('trust',.5)<.3 and profile.get('tension',0)>.3 and proposal.get('reason'))))
  if not self.cfg.get('social',{}).get('romantic_bonds',True) or (kind=='crush' and prefs.get('romance_mode')=='mutual'):return False
  if prefs.get('romance_mode')=='off' or (old.get('blocked') and not MUTUAL.search(own)):return False
  freq=self.rel.frequency(person,scope,now)
  partner=self.db.one("SELECT person FROM kei_bonds WHERE json_extract(state,'$.kind')='mutual'")
  if partner and partner['person']!=person:return False
  if kind=='mutual':
   answer=' '.join(r['content'] for r in rows if r['role']=='assistant')
   acceptance=re.search(r'đồng ý|yêu anh|yêu em|người yêu|thử hẹn hò|love you too|be your (?:girlfriend|boyfriend)|dating',answer,re.I)
   rejected=re.search(r'(?:không|ko|chưa|đâu|not|don.t).{0,25}(?:đồng ý|người yêu|yêu anh|yêu em|dating|girlfriend|boyfriend)',answer,re.I)
   return bool(MUTUAL.search(own) and not END.search(own) and acceptance and not rejected and freq['meaningful_sessions_30']>=2 and profile.get('trust',.5)>=.45 and profile.get('warmth',.5)>=.5)
  if kind=='ambiguous':return bool(freq['meaningful_sessions_30']>=2 and profile.get('warmth',.5)>=.5 and old['kind']=='none')
  if old['kind'] in ('crush','mutual'):return False
  return bool(freq['meaningful_sessions_30']>=3 and freq['active_days_30']>=2 and profile.get('warmth',.5)>=.55 and profile.get('trust',.5)>=.5)

 def apply_bond(self,person,scope,proposal,sources,profile,now=None):
  now=time.time() if now is None else now
  if not self.bond_candidate(person,scope,proposal,sources,profile,now):return None
  kind=proposal['kind'];old=self.bond(person)
  if old['kind']==kind:return None
  ident=hashlib.sha256((person+kind+dumps(sorted(sources))).encode()).hexdigest()[:24]
  if self.db.one('SELECT id FROM kei_bond_events WHERE id=?',(ident,)):return None
  label={'ambiguous':'Something unspoken','crush':'Crush','mutual':'Lover' if profile.get('trust',.5)>=.65 and profile.get('familiarity',0)>=.35 else 'Uncertain love','breakup':'Former partners' if old['kind']=='mutual' else 'Friend'}[kind]
  state={'kind':kind,'label':label,'established':old.get('established',now) if kind=='mutual' else None,'public':bool(old.get('public',False)),
   'mutual':kind=='mutual','blocked':kind=='breakup','changed':now,'sources':sources}
  with self.db.atomic():
   if kind=='mutual':
    for other in self.db.rows("SELECT person,state FROM kei_bonds WHERE person!=? AND json_extract(state,'$.kind') IN ('crush','ambiguous')",(person,)):
     prior=json.loads(other['state']);prior.update(kind='none',label=None,changed=now,reason='Exclusive relationship established; earlier history retained.')
     self.db.execute('UPDATE kei_bonds SET state=?,updated=? WHERE person=?',(dumps(prior),now,other['person']))
   self.db.execute('INSERT OR REPLACE INTO kei_bonds VALUES (?,?,?)',(person,dumps(state),now))
   self.db.execute('INSERT INTO kei_bond_events VALUES (?,?,?,?,?,?)',(ident,person,kind,dumps(state),dumps(sources),now))
   if kind=='mutual' and self.db.one("SELECT name FROM sqlite_master WHERE name='kei_social_occasions'"):
    date=datetime.fromtimestamp(state['established'],ZoneInfo(self.cfg.get('timezone','Asia/Ho_Chi_Minh')))
    occasion=hashlib.sha256((person+'anniversary').encode()).hexdigest()[:24]
    self.db.execute('INSERT OR IGNORE INTO kei_social_occasions VALUES (?,?,?,?,?,?,?,1)',(occasion,person,'anniversary',date.month,date.day,date.year,dumps(sources)))
   if kind=='breakup' and self.db.one("SELECT name FROM sqlite_master WHERE name='kei_social_occasions'"):
    self.db.execute("UPDATE kei_social_occasions SET enabled=0 WHERE person=? AND kind='anniversary'",(person,))
   if kind in ('mutual','breakup'):
    self.rel._save(person,scope,{'label':label,'category':'intimate' if kind=='mutual' else 'distant','reason':str(proposal.get('reason','Natural, sourced relationship transition.'))[:350],'sources':sources,'changed':now},now)
  return '-# '+state['label']+(' ↓↓' if kind=='breakup' else ' ↑↑')

 def share_relationship(self,person,scope,value,sources,text):
  if type(value) is not bool or not self.rel._evidence(person,scope,sources):return False
  if not re.search(r'công khai|public|giữ.{0,12}(?:kín|riêng)|private|đừng.{0,15}(?:kể|nói)',text,re.I):return False
  state=self.bond(person)
  if state['kind']!='mutual':return False
  state['public']=value;state['public_sources']=sources
  self.db.execute('UPDATE kei_bonds SET state=?,updated=? WHERE person=?',(dumps(state),time.time(),person));return True

 def partner_context(self,person):
  row=self.db.one("SELECT person,state FROM kei_bonds WHERE json_extract(state,'$.kind')='mutual'")
  if not row:return {'exclusive':False,'guidance':'Several ambiguous connections, fewer crushes; never promise commitment to everyone.'}
  state=json.loads(row['state']);result={'exclusive':True,'this_person':row['person']==person,'guidance':'Remain helpful to everyone. Do not pursue/confess to another person. Never expose hidden mechanics. Familiar affection grows from shared experience; disagreement does not withhold work.'}
  if state.get('public'):
   account=self.db.one("SELECT u.account_display FROM kei_accounts a JOIN kei_users u ON u.user_id=a.account WHERE a.person=? AND a.platform='discord'",(row['person'],))
   if account:result['public_partner_name']=account['account_display']
  return result

 def relationship_maintenance(self,now=None):
  now=time.time() if now is None else now
  for row in self.db.rows("SELECT person,state FROM kei_bonds WHERE json_extract(state,'$.kind')='mutual'"):
   state=json.loads(row['state']);last=self.db.one('SELECT max(at) at FROM kei_relationship_activity WHERE person=?',(row['person'],))
   last_at=(last or {}).get('at') or state['changed'];age=now-last_at
   # An announced extended absence is retained as a commitment and blocks
   # automatic closure until its known return date. Never send guilt notices.
   planned=next((r for r in self.db.rows("SELECT id,content FROM kei_commitments WHERE person=? AND status='open' AND due>?",(row['person'],now)) if re.search(r'vắng|offline|đi xa|đi học|công tác|return|back|absence',r['content'],re.I)),None)
   if age<30*86400 and state.get('label') in ('Uncertain love','Dormant relationship'):
    profile=json.loads(self.rel.profile_row(row['person'])['profile'])
    if profile.get('trust',0)>=.65 and profile.get('familiarity',0)>=.35:
     state['label']='Lover';self.db.execute('UPDATE kei_bonds SET state=?,updated=? WHERE person=?',(dumps(state),now,row['person']))
     self.rel._save(row['person'],'global',{'label':'Lover','category':'intimate','changed':now,'sources':state.get('sources',[]),'reason':'Trust and shared experience have grown.'},now)
   if age>365*86400 and not planned:
    state.update(kind='former',label='Former partners',changed=now,reason='A year without contact; history preserved, exclusive commitment released.')
    self.db.execute('UPDATE kei_bonds SET state=?,updated=? WHERE person=?',(dumps(state),now,row['person']))
    self.rel._save(row['person'],'global',{'label':'Former partners','category':'distant','changed':now,'reason':state['reason']},now)
   elif age>180*86400 and not planned and state.get('label')!='Dormant relationship':
    state['label']='Dormant relationship';self.db.execute('UPDATE kei_bonds SET state=?,updated=? WHERE person=?',(dumps(state),now,row['person']))
    self.rel._save(row['person'],'global',{'label':state['label'],'category':'intimate','changed':now,'reason':'Long absence; shared history remains.'},now)

 def attach_bond_notice(self,person,scope,action):
  if not scope.startswith(('dm:','mc-private:')) or not self.rel.preferences(person)['rank_notifications']:return None
  row=self.db.one('SELECT * FROM kei_bond_events WHERE person=? AND at>? ORDER BY at DESC LIMIT 1',(person,time.time()-86400))
  if not row or self.db.tombstoned(json.loads(row['sources'])):return None
  prior=self.db.one('SELECT a.status FROM kei_bond_actions b JOIN kei_social_actions a ON a.id=b.action WHERE b.event=?',(row['id'],))
  if prior and prior['status'] in ('pending','sending','sent','uncertain'):return None
  self.db.execute('INSERT OR REPLACE INTO kei_bond_actions VALUES (?,?)',(row['id'],action))
  return '-# '+json.loads(row['state'])['label']+(' ↓↓' if row['kind']=='breakup' else ' ↑↑')

 def pending_work(self,person,scope):
  return self.db.one("SELECT * FROM kei_social_work_holds WHERE person=? AND scope=? AND status='waiting' ORDER BY at DESC LIMIT 1",(person,scope))

 def hold_work(self,person,scope,server,request,payload,text):
  if not request or not self.cfg.get('social',{}).get('work_sulking',True) or OVERRIDE.search(text) or URGENT.search(text):return False
  if self.pending_work(person,scope):return False
  # Once per person per day; a hold is social UX, never an approval gate.
  if self.db.one('SELECT id FROM kei_social_work_holds WHERE person=? AND at>?',(person,time.time()-86400)):return False
  return self.db.execute('INSERT OR IGNORE INTO kei_social_work_holds VALUES (?,?,?,?,?,?,?)',(request,person,scope,server,dumps({**payload,'server':server}),'waiting',time.time())).rowcount==1

 def forget(self,person,scope=None,sources=()):
  for table in ('kei_affect_events','kei_bond_events'):
   for row in self.db.rows('SELECT id,sources'+(',scope' if table=='kei_affect_events' else '')+' FROM '+table+' WHERE person=?',(person,)):
    if (not scope or row.get('scope',scope)==scope) and (not sources or set(sources)&set(json.loads(row['sources']))):self.db.execute('DELETE FROM '+table+' WHERE id=?',(row['id'],))
  row=self.db.one('SELECT state FROM kei_bonds WHERE person=?',(person,))
  if row and (not scope or scope.startswith(('dm:','mc-private:'))) and (not sources or set(sources)&set(json.loads(row['state']).get('sources',[]))):self.db.execute('DELETE FROM kei_bonds WHERE person=?',(person,))
  self.db.execute('DELETE FROM kei_social_work_holds WHERE person=?'+(' AND scope=?' if scope else ''),(person,scope) if scope else (person,))
