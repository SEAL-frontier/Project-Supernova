from __future__ import annotations
import json,time,re,logging
import discord
from .store import dumps
from .text import redact

LOG=logging.getLogger('kei.progress')
MODES=('off','minimal','advanced')
LABELS={'queued':'Chờ chạy','running':'Đang làm','succeeded':'Hoàn tất','failed':'Chưa hoàn tất',
        'cancelled':'Đã hủy','waiting':'Chờ xác nhận','paused':'Đang chờ','reconcile':'Cần đối soát'}


class Progress:
    def __init__(self,store,secrets=()):self.db=store;self.secrets=secrets
    def clean(self,text,limit=1000):
        text=redact(text,self.secrets).replace('```',"'''")
        text=re.sub(r'\x1b\[[0-?]*[ -/]*[@-~]','',text)
        return ''.join(c for c in text if ord(c)>=32 or c in '\n\t')[-limit:]
    def mode(self,user):
        row=self.db.one('SELECT mode FROM kei_debug_preferences WHERE user=?',(str(user),))
        return row['mode'] if row else 'advanced'
    def set_mode(self,user,mode):
        if mode not in MODES:raise ValueError('Chọn off, minimal hoặc advanced.')
        self.db.execute('INSERT INTO kei_debug_preferences(user,mode) VALUES (?,?) ON CONFLICT(user) DO UPDATE SET mode=excluded.mode',(str(user),mode))
    def start(self,k):
        task=self.db.one('SELECT plan FROM kei_tasks WHERE id=?',(k,))
        plan=json.loads(task['plan']);labels=plan.get('steps',[]) if isinstance(plan,dict) else plan
        self.db.execute('INSERT OR IGNORE INTO kei_progress VALUES (?,?,?,?,?,?)',(k,'Chuẩn bị',dumps([{'label':self.clean(s,100),'state':'pending'} for s in labels]),'','',time.time()))
    def phase(self,k,text):
        self.db.execute('UPDATE kei_progress SET phase=?,updated=? WHERE task=?',(self.clean(text,160),time.time(),k))
    def plan(self,k,labels):
        row=self.db.one('SELECT steps FROM kei_progress WHERE task=?',(k,))
        previous={s['label']:s['state'] for s in json.loads(row['steps'])} if row else {}
        self.db.execute('UPDATE kei_progress SET steps=?,updated=? WHERE task=?',
                        (dumps([{'label':self.clean(s,100),'state':previous.get(self.clean(s,100),'pending')} for s in labels]),time.time(),k))
    def step(self,k,index,state,note=''):
        row=self.db.one('SELECT steps FROM kei_progress WHERE task=?',(k,));steps=json.loads(row['steps'])
        if not isinstance(index,int) or index<0 or index>=len(steps) or state not in ('running','done','skipped'):raise ValueError('Invalid progress step')
        steps[index]['state']=state
        self.db.execute('UPDATE kei_progress SET steps=?,phase=?,updated=? WHERE task=?',(dumps(steps),self.clean(note or steps[index]['label'],160),time.time(),k))
    def event(self,k,kind,text):
        if kind not in ('command','log'):return
        # Store only the recent tail, already redacted; never entire files or credentials.
        if kind=='command':
            self.db.execute('UPDATE kei_progress SET command=?,log=?,updated=? WHERE task=?',(self.clean(text,500),'',time.time(),k))
            return
        if kind=='log':
            row=self.db.one('SELECT log FROM kei_progress WHERE task=?',(k,))
            text=(row['log'] if row else '')+text
        self.db.execute('UPDATE kei_progress SET '+kind+'=?,updated=? WHERE task=?',(self.clean(text,1100 if kind=='log' else 500),time.time(),k))
    def complete(self,k):
        self.phase(k,'Đã có kết quả')


def render(task,progress,mode,note=False):
    if mode=='off':return None
    def clean(text,n):
        text=re.sub(r'[\r\n]+',' ',str(text)).replace('```',"'''")
        return text if len(text)<=n else text[:n-1].rstrip()+'…'
    objective=task['goal'].split('\nAdditional requester instruction:',1)[0]
    lines=[clean(objective,110)]
    if task['status']=='running':lines+=['','**Đang:** '+clean(re.sub(r'^(?:Đang[ :]+)+','',progress['phase'],flags=re.I),100)]
    elif task['status']=='succeeded' and task.get('result'):lines+=['','**Tóm tắt kết quả xử lý:** '+clean(task['result'],600)]
    elif task['status'] in ('paused','failed','reconcile') and task.get('result'):lines+=['','**Chưa xong:** '+clean(task['result'],280)]
    icons={'pending':'☐','running':'◉','done':'☑','skipped':'—'}
    steps=json.loads(progress['steps'])
    if steps:lines.append('')
    for s in steps[:7]:
        icon=icons.get(s['state'],'☐')
        if s['state']=='running' and task['status'] in ('paused','failed','cancelled','reconcile'):icon='!'
        lines.append(icon+' '+clean(s['label'],80))
    if len(steps)>7:lines.append(f'… còn {len(steps)-7} bước')
    if mode=='advanced':
        logs=[]
        if progress['command']:logs.append('> '+clean(progress['command'],300))
        if progress['log']:
            logs += ['— output gần nhất —']+[clean(s,140) for s in progress['log'].splitlines()[-5:]]
        if logs:lines+=['','-# Bước gần nhất · chi tiết thao tác, không phải kết luận.','```text\n'+'\n'.join(logs)[:1050]+'\n```']
    embed={'title':f"Kei · {clean(task['server'],40)} · {LABELS.get(task['status'],task['status'])}",
           'description':'\n'.join(lines),'color':0xEFA5A5}
    hint='-# `/debug mode:off` để ẩn; `minimal` chỉ checklist, `advanced` thêm lệnh/log. Lưu riêng cho bạn.' if note else ''
    return {'content':hint,'embed':embed}


class Reporter:
    """One durable card per task, coalesced updates; discord.py handles route 429s."""
    def __init__(self,store,destination,secrets=(),clock=time.time,interval=5,reference_for_task=None,can_report=None):
        self.db=store;self.destination=destination;self.progress=Progress(store,secrets)
        self.clock=clock;self.interval=interval;self.channel_next={};self.global_next=0
        self.reference_for_task=reference_for_task;self.can_report=can_report
    async def tick(self):
        tasks=self.db.rows('SELECT t.* FROM kei_tasks t JOIN kei_progress p ON p.task=t.id ORDER BY p.updated DESC LIMIT 100')
        for task in tasks:
            if self.can_report and not self.can_report(task):continue
            now=self.clock();k=task['id'];user=task['requester'];channel=task['channel'];mode=self.progress.mode(user)
            card=self.db.one('SELECT * FROM kei_debug_cards WHERE task=?',(k,))
            if card and (card['blocked'] or card['next_at']>now):continue
            # Do not replay ancient historical tasks after enabling debug.
            if not card and (mode=='off' or task['updated']<now-86400):continue
            if now<self.global_next or now<self.channel_next.get(channel,0):continue
            row=self.db.one('SELECT * FROM kei_progress WHERE task=?',(k,))
            pref=self.db.one('SELECT * FROM kei_debug_preferences WHERE user=?',(user,))
            note=bool(card['note']) if card else not(pref and pref['note_seen'])
            safe_task={**task,'goal':self.progress.clean(task['goal'].split('\nAdditional requester instruction:',1)[0],2000),'result':redact(str(task.get('result') or ''),self.progress.secrets)}
            payload=render(safe_task,row,mode,note)
            content=dumps(payload) if payload is not None else None
            if card and content==card['content']:continue
            if not card:self.db.execute('INSERT INTO kei_debug_cards(task) VALUES (?)',(k,));card=self.db.one('SELECT * FROM kei_debug_cards WHERE task=?',(k,))
            try:
                target=await self.destination(channel)
                if self.can_report and not self.can_report(task):continue
                if content is None:
                    if card['message']:await target.get_partial_message(int(card['message'])).delete()
                    message=None
                elif card['message']:
                    message=card['message']
                    await target.get_partial_message(int(message)).edit(content=payload['content'] or None,embed=discord.Embed.from_dict(payload['embed']),allowed_mentions=discord.AllowedMentions.none())
                else:
                    # Mark creation uncertain before network I/O: restart must not duplicate a card.
                    self.db.execute('UPDATE kei_debug_cards SET blocked=1 WHERE task=?',(k,))
                    extra={}
                    if self.reference_for_task:
                        reference=await self.reference_for_task(task,target)
                        if reference:extra['reference']=reference
                    if self.can_report and not self.can_report(task):continue
                    sent=await target.send(payload['content'] or None,embed=discord.Embed.from_dict(payload['embed']),allowed_mentions=discord.AllowedMentions.none(),**extra);message=str(sent.id)
                completed=self.clock()
                self.db.execute('UPDATE kei_debug_cards SET message=?,content=?,next_at=?,note=?,blocked=0 WHERE task=?',
                                (message,content,completed+self.interval,int(note and content is not None),k))
                if note and content is not None:
                    self.db.execute("INSERT INTO kei_debug_preferences(user,mode,note_seen) VALUES (?,'advanced',1) ON CONFLICT(user) DO UPDATE SET note_seen=1",(user,))
                self.channel_next[channel]=completed+1;self.global_next=completed+0.5
                LOG.info('PROGRESS_CARD_UPDATED task=%s mode=%s status=%s',k,mode,task['status'])
            except discord.NotFound:
                # A deleted message is not recreated repeatedly.
                self.db.execute('UPDATE kei_debug_cards SET blocked=1 WHERE task=?',(k,))
            except discord.Forbidden:
                self.db.execute('UPDATE kei_debug_cards SET blocked=1 WHERE task=?',(k,))
                LOG.warning('No permission for task progress card')
            except Exception as exc:
                self.db.execute('UPDATE kei_debug_cards SET next_at=? WHERE task=?',(now+30,k))
                LOG.warning('Progress update deferred: %s',type(exc).__name__)
