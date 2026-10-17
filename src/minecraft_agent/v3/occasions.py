"""Private social occasions; separate from user-assigned operational schedules."""
import hashlib,re,time,json
from datetime import datetime
from zoneinfo import ZoneInfo
from ..v2.store import dumps

def learn(db,person,scope,own,sources):
 if not db.one("SELECT name FROM sqlite_master WHERE name='kei_social_occasions'"):return
 words=' '.join(r['content'].split('[REPLIED MESSAGE',1)[0] for r in own)
 if not re.search(r'(?:sinh nhật|birthday).{0,15}(?:anh|em|tui|tao|tớ|mình|tôi)|(?:my|tui|tao|tớ|mình|tôi).{0,15}(?:sinh nhật|birthday)',words,re.I):return
 match=re.search(r'(?<!\d)(\d{1,2})\s*[/.-]\s*(\d{1,2})(?:\s*[/.-]\s*(\d{4}))?(?!\d)',words)
 if not match:return
 day,month=int(match[1]),int(match[2]);year=int(match[3]) if match[3] else None
 try:datetime(year or 2000,month,day)
 except ValueError:return
 ident=hashlib.sha256((person+'birthday').encode()).hexdigest()[:24]
 db.execute('INSERT OR REPLACE INTO kei_social_occasions VALUES (?,?,?,?,?,?,?,1)',(ident,person,'birthday',month,day,year,dumps(sources)))

async def tick(engine,now=None):
 now=time.time() if now is None else now;db=engine.db
 db.execute("UPDATE kei_occasion_deliveries SET status=(SELECT status FROM kei_outbox WHERE id=outbox) WHERE status='queued' AND outbox IS NOT NULL AND EXISTS(SELECT 1 FROM kei_outbox WHERE id=outbox AND status IN ('sent','failed','uncertain','cancelled'))")
 for occasion in db.rows('SELECT * FROM kei_social_occasions WHERE enabled=1'):
  person=occasion['person'];pref=engine.memory.preference(person)
  if not pref.get('dm_opt_in') or pref.get('muted') or db.tombstoned(json.loads(occasion['sources'])):continue
  user=engine.identity.discord(person)
  if not user:continue
  local=datetime.fromtimestamp(now,ZoneInfo(pref.get('timezone') or engine.cfg['timezone']))
  if occasion['kind']=='anniversary' and local.year<=occasion['year']:continue
  if engine.quiet.active('dm:'+user,person):continue
  if (local.month,local.day)!=(occasion['month'],occasion['day']) or not 8<=local.hour<22:continue
  if db.one('SELECT status FROM kei_occasion_deliveries WHERE occasion=? AND year=?',(occasion['id'],local.year)):continue
  # Durable claim precedes model/send. Uncertain crashes are not retried blindly.
  if db.execute("INSERT OR IGNORE INTO kei_occasion_deliveries VALUES (?,?,'preparing',NULL,?)",(occasion['id'],local.year,now)).rowcount!=1:continue
  try:
   from ..v2.persona import prompt
   result=await engine.social_model().chat([{'role':'system','content':prompt(engine.cfg,db,user)+'\nA sourced private occasion. Write a short natural Vietnamese greeting appropriate to this relationship. No mechanics, ages unless established, guilt, lists or claims of offscreen experiences. You may be sincerely warm.'},{'role':'user','content':dumps({'occasion':occasion['kind'],'local_date':local.date().isoformat(),'relationship':engine.memory.context(user,'dm:'+user)})}],max_tokens=300)
   text=(result.get('content') or '').strip()
   if not text:db.execute("UPDATE kei_occasion_deliveries SET status='failed' WHERE occasion=? AND year=?",(occasion['id'],local.year));continue
   with db.atomic():
    ids=db.queue(user,text[:1500]);outbox=ids[0] if isinstance(ids,list) and ids else None
    db.execute("UPDATE kei_occasion_deliveries SET status='queued',outbox=? WHERE occasion=? AND year=?",(outbox,occasion['id'],local.year))
  except Exception:
   db.execute("UPDATE kei_occasion_deliveries SET status='failed' WHERE occasion=? AND year=?",(occasion['id'],local.year))

def forget(db,person,scope=None,sources=()):
 for row in db.rows('SELECT * FROM kei_social_occasions WHERE person=?',(person,)):
  if not sources or set(sources)&set(json.loads(row['sources'])):
   db.execute('DELETE FROM kei_occasion_deliveries WHERE occasion=?',(row['id'],));db.execute('DELETE FROM kei_social_occasions WHERE id=?',(row['id'],))
