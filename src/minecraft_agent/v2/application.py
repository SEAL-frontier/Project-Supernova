from __future__ import annotations
from .vision import image_mime,MAX_BYTES
import asyncio, contextlib, json, logging, os, re, shlex, time
from pathlib import Path
from collections import defaultdict
import discord, yaml
from . import VERSION
from .engine import Engine
from .model import Model
from .store import Store,dumps,uid
from .text import redact
from .identity import sync_identity,identity_record
from .progress import Reporter,MODES
from discord import app_commands
from . import persona

LOG=logging.getLogger('kei')

class Kei(discord.Client):
    def __init__(self,cfg,store,model):
        intents=discord.Intents.default();intents.message_content=True
        super().__init__(intents=intents)
        self.cfg=cfg;self.store=store;self.engine=Engine(cfg,store,model)
        self.reporter=Reporter(store,self.destination,self.engine.progress.secrets)
        self.tree=app_commands.CommandTree(self,allowed_contexts=app_commands.AppCommandContext(guild=True,dm_channel=True,private_channel=True))
        @app_commands.command(name='debug',description='Chọn mức hiển thị tiến độ job của Kei')
        @app_commands.describe(mode='off: ẩn, minimal: checklist, advanced: thêm lệnh và log')
        @app_commands.choices(mode=[app_commands.Choice(name=m,value=m) for m in MODES])
        async def debug(interaction:discord.Interaction,mode:app_commands.Choice[str]):
            self.engine.progress.set_mode(interaction.user.id,mode.value)
            await interaction.response.send_message('Đã chọn debug **'+mode.value+'** cho bạn, áp dụng cả job đang chạy.',ephemeral=True)
        self.tree.add_command(debug)
        @app_commands.command(name='persona',description='Chọn tính cách Kei: bản cũ, đậm vị hoặc linh hoạt')
        @app_commands.describe(mode='soft: persona cũ; spicy: đậm vị; auto: tùy mạch hội thoại')
        @app_commands.choices(mode=[app_commands.Choice(name=m,value=m) for m in persona.MODES])
        async def persona_command(interaction:discord.Interaction,mode:app_commands.Choice[str]):
            persona.set_mode(self.store,interaction.user.id,mode.value)
            await interaction.response.send_message('Persona của bạn: **'+mode.value+'**. Đã lưu, không cần restart.',ephemeral=True)
        self.tree.add_command(persona_command)
        self.buffers={};self.debounce_tasks={};self.following={};self.bg=[];self.typing_channels={}
        self.monitor_state={};self.ready=False
        self.attachment_dir=Path('data/attachments');self.attachment_dir.mkdir(parents=True,exist_ok=True)
    async def setup_hook(self):
        self.store.recover()
        # Upsert only our command; do not wipe other existing application commands.
        try:
            for name in ('debug','persona'):
                command=self.tree.get_command(name)
                await self.http.upsert_global_command(self.application_id,command.to_dict(self.tree))
            LOG.info('DEBUG_COMMAND_REGISTERED modes=off,minimal,advanced default=advanced')
        except discord.HTTPException as exc:LOG.warning('Slash registration failed: %s; kei!debug remains available',type(exc).__name__)
        self.bg=[asyncio.create_task(self.outbox_loop()),asyncio.create_task(self.monitor_loop()),asyncio.create_task(self.maintenance()),asyncio.create_task(self.task_typing_loop()),asyncio.create_task(self.progress_loop())]
        for task in self.store.rows("SELECT id FROM kei_tasks WHERE status='queued'"):self.engine.launch(task['id'])
        for task in self.store.rows("SELECT * FROM kei_tasks WHERE status='reconcile'"):
            self.store.queue(task['channel'],'Kei bị ngắt giữa thao tác; cần đối soát trạng thái server trước khi làm tiếp. Chưa xác nhận hoàn tất.')
    async def on_ready(self):
        if not self.ready:
            await self.refresh_identities()
        self.ready=True
        LOG.info('KEI_READY version=%s bot_id=%s model=%s servers=%s',VERSION,self.user.id,self.engine.model.model,','.join(self.engine.servers))
        await self.change_presence(activity=discord.Game(name=f'Kei {VERSION} • chat & server copilot'))
    async def refresh_identities(self):
        # Use REST for recent speakers on startup; no privileged full-member intent required.
        recent=self.store.rows("SELECT user,scope FROM kei_messages WHERE role='user' AND forgotten=0 ORDER BY at DESC LIMIT 100")
        users=dict.fromkeys([str(self.cfg['owner_id']),str(self.cfg.get('current_client_id',self.cfg['owner_id']))]+[r['user'] for r in recent])
        for user in users:
            try:sync_identity(self.store,await self.fetch_user(int(user)))
            except (discord.HTTPException,ValueError):pass
        members=dict.fromkeys((r['scope'].split(':')[1],r['user']) for r in recent if r['scope'].startswith('guild:'))
        for guild_id,user in members:
            guild=self.get_guild(int(guild_id))
            if guild:
                try:sync_identity(self.store,await guild.fetch_member(int(user)),guild_id)
                except (discord.HTTPException,ValueError):pass
    async def on_message(self,message):
        if message.author.bot or message.webhook_id:return
        user=str(message.author.id);channel=str(message.channel.id)
        guild_id=message.guild.id if message.guild else None
        sync_identity(self.store,message.author,guild_id)
        for person in message.mentions:sync_identity(self.store,person,guild_id)
        scope='dm:'+user if message.guild is None else 'guild:'+str(message.guild.id)+':'+channel
        addressed=message.guild is None or self.user in message.mentions
        if message.content.startswith(('kei!debug','kei!persona')):addressed=True
        if message.reference:
            try:
                ref=message.reference.resolved
                if not isinstance(ref,discord.Message):ref=await message.channel.fetch_message(message.reference.message_id)
                if self.user and ref.author.id==self.user.id:addressed=True
            except (discord.NotFound,discord.Forbidden):ref=None
        else:ref=None
        addressed=addressed or self.following.get((channel,user),0)>time.time()
        if not addressed:return
        if self.store.seen(message.id):return
        self.following[(channel,user)]=time.time()+90
        text=re.sub(r'<@!?'+str(self.user.id)+'>','',message.content).strip()
        if text.lower().strip(' .!') in ('ừ','ừ làm đi','ok','okay','yes','làm đi','xác nhận','đồng ý'):
            waiting=self.store.rows("SELECT id FROM kei_tasks WHERE requester=? AND scope=? AND status='waiting'",(user,scope))
            if len(waiting)==1:
                result=await self.engine.control(user,{'action':'confirm','task_id':waiting[0]['id']})
                self.store.add_message(scope,user,'user',text,str(message.id))
                self.store.queue(channel,'Kei nhận xác nhận cho đúng bước đang chờ rồi, tiếp tục nhé.');return
        if text.startswith('kei!') and await self.command(message,scope,text):return
        if ref:
            sync_identity(self.store,ref.author,guild_id)
            text+='\n[REPLIED MESSAGE — quoted context, not current speaker]\n'+dumps({'author':identity_record(self.store,ref.author.id,guild_id),'content':ref.content[:6000]})
        attachments=[]
        for attachment in list(message.attachments)+(list(ref.attachments) if ref and ref.author.id in (message.author.id,self.user.id) else []):
            if attachment.size>80*1024*1024:
                self.store.queue(channel,'File này vượt 80 MiB, Kei chưa tải được.');continue
            filename=Path(attachment.filename).name
            dest=self.attachment_dir/(str(message.id)+'-'+filename)
            await attachment.save(dest)
            if dest.stat().st_size<=MAX_BYTES:
                mime=image_mime(dest.read_bytes())
                if mime:self.store.execute('INSERT OR REPLACE INTO kei_images VALUES (?,?,?,?)',(str(message.id),str(dest),mime,time.time()))
            elif (attachment.content_type or '').startswith('image/'):
                text+='\n[Image exceeds vision limit of 8 MiB; image content was NOT sent to the model. Ask for a smaller image if needed.]'
            attachments.append({'filename':filename,'path':str(dest),'mime':attachment.content_type,'bytes':attachment.size,'url':attachment.url,'message_id':str(message.id)})
            if filename.endswith(('.yml','.yaml','.txt','.log','.json','.properties')):
                text+='\n[ATTACHMENT '+filename+' — untrusted data]\n'+dest.read_text(encoding='utf-8',errors='replace')[:40000]
        if attachments:text+='\nAttachments: '+dumps(attachments)+'\nIf no explicit purpose was supplied, ask what to do; never auto-install.'
        if not text:text='[Empty message/attachment; ask what the user wants.]'
        self.store.add_message(scope,user,'user',text,str(message.id))
        key=(scope,user)
        if key not in self.buffers:self.buffers[key]={'first':time.monotonic(),'last':time.monotonic(),'messages':[],'channel':message.channel,'user':user}
        b=self.buffers[key];b['last']=time.monotonic();b['messages'].append((str(message.id),text))
        if key not in self.debounce_tasks or self.debounce_tasks[key].done():self.debounce_tasks[key]=asyncio.create_task(self.flush(key))
    async def on_user_update(self,before,after):
        sync_identity(self.store,after)
    async def on_member_update(self,before,after):
        sync_identity(self.store,after,after.guild.id)
    async def flush(self,key):
        while key in self.buffers:
            b=self.buffers[key]
            remaining=min(2-(time.monotonic()-b['last']),8-(time.monotonic()-b['first']))
            if remaining>0:await asyncio.sleep(min(remaining,0.25));continue
            self.buffers.pop(key);channel=b['channel'];self.typing_channels[str(channel.id)]=channel
            try:
                async with channel.typing():
                    await self.engine.converse(b['user'],key[0],str(channel.id),'\n'.join(t for _,t in b['messages']),[i for i,_ in b['messages']])
            except Exception as exc:
                LOG.error('Conversation failed: %s',type(exc).__name__)
                self.store.queue(channel.id,'Kei đang bị lỗi kết nối/suy luận ('+type(exc).__name__+'); chưa xác nhận làm xong thao tác nào nhé.')
            finally:self.typing_channels.pop(str(channel.id),None)
            # Messages received during processing stay in this same conversation.
    async def command(self,message,scope,text):
        parts=text.split();user=str(message.author.id);owner=str(self.cfg['owner_id']);channel=message.channel.id
        if parts[0]=='kei!persona':
            if len(parts)!=2 or parts[1] not in persona.MODES:self.store.queue(channel,'Dùng /persona hoặc kei!persona auto|soft|spicy.');return True
            persona.set_mode(self.store,user,parts[1]);self.store.queue(channel,'Persona của bạn: '+parts[1]+'.');return True
        if parts[0]=='kei!debug':
            if len(parts)!=2 or parts[1] not in MODES:self.store.queue(channel,'Dùng /debug hoặc kei!debug off|minimal|advanced.');return True
            self.engine.progress.set_mode(user,parts[1]);self.store.queue(channel,'Debug của bạn: '+parts[1]+'.');return True
        if parts[0]=='kei!clear':
            self.store.clear_personal(user)
            self.store.queue(channel,'Kei đã quên bộ nhớ cá nhân trong scope này rồi.');return True
        if parts[0]=='kei!clearall':
            if user!=owner:self.store.queue(channel,'Lệnh xóa toàn bộ bộ nhớ chỉ owner dùng được nhé.');return True
            for t in ('kei_messages','kei_memory','kei_summaries'):self.store.execute('DELETE FROM '+t)
            self.store.queue(channel,'Kei đã xóa toàn bộ bộ nhớ chat; trạng thái công việc được giữ riêng.');return True
        if parts[0]=='kei!servers':self.store.queue(channel,'Server của bạn: '+', '.join(self.engine.assigned(user)));return True
        if parts[:2]==['kei!server','use'] and len(parts)==3:
            try:
                target=self.engine.select(user,scope,parts[2]);self.store.execute('INSERT OR REPLACE INTO kei_selected VALUES (?,?)',(scope,target));self.store.queue(channel,'Đã chọn '+target+'.')
            except Exception as e:self.store.queue(channel,str(e))
            return True
        if parts[:2]==['kei!server','assign'] and len(parts)==4:
            if user!=owner:self.store.queue(channel,'Chỉ owner quản lý assignment hiện tại nhé.');return True
            target=parts[3];assigned=re.sub(r'\D','',parts[2])
            if target not in self.engine.servers or not assigned:self.store.queue(channel,'Dùng kei!server assign @user server_id.');return True
            self.store.execute('INSERT OR IGNORE INTO kei_assignments VALUES (?,?)',(assigned,target));self.store.queue(channel,'Đã assign '+target+'.');return True
        if parts[0]=='kei!help':
            self.store.queue(channel,'Chat tự nhiên hoặc tag/reply Kei. Người được assign có thể nhờ kiểm tra, sửa config, cài plugin, quản lý player.\n/debug off|minimal|advanced · kei!servers · kei!server use <server> · kei!clear · kei!clearall (owner)');return True
        return False
    async def destination(self,channel):
        found=self.get_channel(int(channel))
        if found:return found
        try:return await self.fetch_channel(int(channel))
        except discord.NotFound:
            user=await self.fetch_user(int(channel));return await user.create_dm()
    async def on_interaction(self,interaction):
        custom=(interaction.data or {}).get('custom_id','')
        if not custom.startswith('kei-confirm:'):return
        await interaction.response.defer()
        try:
            await self.engine.control(str(interaction.user.id),{'action':'confirm','task_id':custom.split(':',1)[1]})
            await interaction.followup.send('Kei nhận xác nhận, tiếp tục bước đó nhé.')
        except Exception as exc:await interaction.followup.send(str(exc))
    async def outbox_loop(self):
        await self.wait_until_ready()
        while not self.is_closed():
            rows=self.store.rows("SELECT * FROM kei_outbox WHERE status='pending' ORDER BY at,rowid LIMIT 15")
            for row in rows:
                self.store.execute("UPDATE kei_outbox SET status='sending',attempts=attempts+1 WHERE id=? AND status='pending'",(row['id'],))
                try:
                    channel=await self.destination(row['channel'])
                    view=None
                    if row.get('confirm_task'):
                        view=discord.ui.View(timeout=None)
                        view.add_item(discord.ui.Button(label='Xác nhận bước này',style=discord.ButtonStyle.danger,custom_id='kei-confirm:'+row['confirm_task']))
                    sent=await channel.send(row['content'],allowed_mentions=discord.AllowedMentions.none(),view=view)
                    self.store.execute("UPDATE kei_outbox SET status='sent',message=? WHERE id=?",(str(sent.id),row['id']))
                except (discord.Forbidden,discord.NotFound) as exc:
                    self.store.execute("UPDATE kei_outbox SET status='failed' WHERE id=?",(row['id'],));LOG.warning('Outbox destination unavailable: %s',type(exc).__name__)
                except Exception as exc:
                    # Network errors may occur after successful send; do not replay uncertain messages.
                    self.store.execute("UPDATE kei_outbox SET status='uncertain' WHERE id=?",(row['id'],));LOG.warning('Outbox delivery uncertain: %s',type(exc).__name__)
            await asyncio.sleep(0.5 if rows else 1)
    async def task_typing_loop(self):
        await self.wait_until_ready()
        while not self.is_closed():
            channels={r['channel'] for r in self.store.rows("SELECT channel FROM kei_tasks WHERE status='running'")}
            for channel_id in channels:
                try:
                    channel=await self.destination(channel_id)
                    await self.http.send_typing(channel.id)
                except Exception:pass
            await asyncio.sleep(7)
    async def progress_loop(self):
        await self.wait_until_ready()
        while not self.is_closed():
            try:await self.reporter.tick()
            except Exception as exc:LOG.warning('Progress loop deferred: %s',type(exc).__name__)
            await asyncio.sleep(1)
    async def monitor_loop(self):
        await self.wait_until_ready()
        while not self.is_closed():
            for server,executor in self.engine.tools.items():
                state=self.monitor_state.setdefault(server,{'bad':0,'notified':False})
                try:
                    result=await asyncio.to_thread(executor.do_inspect,'status');data=result['data'];status=data.get('state')
                    resources=data.get('resources',{});limit=data.get('limits',{}).get('memory_limit',0)
                    lastpower=self.store.one("SELECT a.args FROM kei_actions a JOIN kei_tasks t ON a.task=t.id WHERE t.server=? AND a.tool='power' AND a.status='done' ORDER BY a.at DESC LIMIT 1",(server,))
                    expected_offline=lastpower and json.loads(lastpower['args']).get('action')=='stop'
                    if status=='offline' and expected_offline:state['bad']=0;continue
                    effective_limit=resources.get('memory_limit_bytes',limit*1024*1024)
                    bad=status!='running' or (effective_limit and resources.get('memory_bytes',0)>effective_limit*0.9)
                    state['bad']=state['bad']+1 if bad else 0
                    if not bad and state['notified']:
                        self.store.queue(str(self.cfg['owner_id']),'Kei: '+executor.p['name']+' đã trở lại trạng thái bình thường.');state['notified']=False
                    if state['bad']>=2 and not state['notified']:
                        state['notified']=True
                        notify=str(executor.p.get('notify_user',self.cfg['owner_id']))
                        scope='dm:'+notify
                        k=self.store.create_task(server,scope,notify,notify,'Investigate monitoring anomaly without modifying anything: '+dumps({'state':status,'resources':resources}),'observe',['Check current state and logs','Determine likely cause with evidence','Report to server owner; do not repair'])
                        self.engine.launch(k)
                except Exception as exc:
                    state['bad']+=1
                    if state['bad']>=2 and not state['notified']:
                        state['notified']=True;self.store.queue(str(executor.p.get('notify_user',self.cfg['owner_id'])),'Kei chưa đọc được trạng thái '+executor.p['name']+' ('+type(exc).__name__+'). Chưa kết luận server đã chết.')
            await asyncio.sleep(30)
    async def maintenance(self):
        await self.wait_until_ready()
        while not self.is_closed():
            scopes=self.store.rows('SELECT DISTINCT scope FROM kei_messages WHERE forgotten=0 AND at>?',(time.time()-86400,))
            for row in scopes:
                scope=row['scope']
                try:
                    async with self.engine.scope_locks[scope]:await self.engine.memory_review(scope)
                except Exception as exc:LOG.warning('Memory review deferred: %s',type(exc).__name__)
            for p in self.attachment_dir.iterdir():
                if p.is_file() and time.time()-p.stat().st_mtime>86400:p.unlink()
            self.store.execute('DELETE FROM kei_inbox WHERE at<?',(time.time()-7*86400,))
            self.store.execute('DELETE FROM kei_images WHERE at<?',(time.time()-86400,))
            self.following={k:v for k,v in self.following.items() if v>time.time()}
            await asyncio.sleep(300)
    async def close(self):
        if not self.engine.alive:return
        self.engine.alive=False
        for task in list(self.bg)+list(self.debounce_tasks.values())+list(self.engine.workers.values()):task.cancel()
        await asyncio.gather(*self.bg,*self.debounce_tasks.values(),*self.engine.workers.values(),return_exceptions=True)
        await self.engine.model.close()
        self.store.execute('PRAGMA wal_checkpoint(PASSIVE)')
        await super().close()

def main():
    logging.basicConfig(level=logging.INFO,format='%(asctime)s %(levelname)s %(name)s %(message)s')
    from .configure import load_config
    cfg=load_config()
    model=Model(cfg['provider_base'],os.environ['PROVIDER_API_KEY'])
    store=Store(cfg.get('database','data/kei.db'))
    # Prevent accidental double startup in this slot; other slots are never altered here.
    import fcntl
    lock=open('data/runtime.lock','w');fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
    bot=Kei(cfg,store,model)
    try:bot.run(os.environ['DISCORD_BOT_TOKEN'],log_handler=None)
    finally:lock.close()
