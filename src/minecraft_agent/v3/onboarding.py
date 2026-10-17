"""Guided connector enrollment, shared by the small dashboard and headless tools."""
import asyncio,base64,copy,hashlib,json,os,re,secrets,socket,time
from pathlib import Path
from urllib.parse import urlsplit
import paramiko,yaml
from .config import Secrets,atomic
from .local import LocalAccess
from .connectors import HybridTools
from ..v2.store import dumps,uid

class Connections:
 def __init__(self,ux):self.ux=ux;self.pending={}
 def allowed(self,user,server=''):
  if server:
   if server not in self.ux.engine.servers or not self.ux.access.owner(user,server):raise PermissionError('Only this server’s owner can change its connections.')
  elif str(user)!=str(self.ux.cfg['owner_id']) and not self.ux.cfg.get('allow_self_service'):raise PermissionError('Ask the bot owner to enable server setup.')

 async def preview(self,user,body):
  user=str(user);server=str(body.get('server',''));self.allowed(user,server)
  kind=body.get('kind');name=str(body.get('name','')).strip()
  if not server and not 1<=len(name)<=80:raise ValueError('Give your server a name.')
  ident=uid();data={'user':user,'server':server,'name':name,'kind':kind,'expires':time.time()+600}
  if kind=='ssh':
   host=str(body.get('host','')).strip();account=str(body.get('user','')).strip();port=body.get('port',22)
   if not host or len(host)>253 or re.search(r'[\s/@\\]',host) or not re.fullmatch(r'[\w.@-]{1,80}',account):raise ValueError('Enter a host name/IP and an SSH account.')
   if type(port) is not int or not 1<=port<=65535:raise ValueError('SSH port must be between 1 and 65535.')
   volume=str(body.get('root','')).strip()
   if not volume or re.search(r'[\r\n\x00]',volume):raise ValueError('Enter the Minecraft folder as seen by the SSH account.')
   password=str(body.get('password',''));key=str(body.get('key',''));phrase=str(body.get('passphrase',''))
   if len(password)>1024 or len(key)>16384 or not(password or key):raise ValueError('Use an SSH password or a private key file under 16 KB.')
   ssh={'host':host,'port':port,'user':account,'volume':volume}
   def probe():
    sock=socket.create_connection((host,port),timeout=10);transport=paramiko.Transport(sock)
    try:
     transport.start_client(timeout=10);return transport.get_remote_server_key()
    finally:transport.close()
   hostkey=await asyncio.to_thread(probe)
   # Existing trusted host keys are never silently replaced by web onboarding.
   existing=self.ux.engine.servers.get(server,{}).get('connectors',{}).get('ssh',{})
   known=existing.get('known_hosts');hostid=host if port==22 else '['+host+']:'+str(port)
   if known and Path(known).exists():
    keys=paramiko.HostKeys(known)
    if keys.lookup(hostid) and not keys.check(hostid,hostkey):raise PermissionError('SSH host key changed. Verify the host identity with its operator before replacing the trusted key.')
   fingerprint='SHA256:'+base64.b64encode(hashlib.sha256(hostkey.asbytes()).digest()).decode().rstrip('=')
   data.update(ssh=ssh,password=password,key=key,passphrase=phrase,hostkey=hostkey,fingerprint=fingerprint)
   result={'fingerprint':fingerprint,'summary':'Verify this fingerprint with the server owner, then connect. No login or command has run yet.'}
  elif kind=='local':
   if user!=str(self.ux.cfg['owner_id']):raise PermissionError('Only the bot operator can attach folders visible on the bot host.')
   local={'root':str(body.get('root','')).strip(),'writable':body.get('writable') is True}
   state=LocalAccess(local).detect()
   if not state['root_visible']:raise ValueError('This folder is not visible to the bot. Check its path, permissions and container mount.')
   data['local']=local;result={'detection':state,'summary':'Folder access detected. Process control is separate and is not granted by this setup.'}
  elif kind=='bridge':
   endpoint=str(body.get('endpoint','')).strip();url=urlsplit(endpoint)
   if url.scheme not in ('ws','wss') or not url.hostname or url.path!='/v1/bridge' or url.username or url.password or url.query or url.fragment:raise ValueError('Use the bot bridge endpoint, for example wss://kei.example.com/v1/bridge.')
   if not self.ux.cfg.get('bridge',{}).get('enabled'):raise ValueError('The bot operator must enable the bridge listener first. Minecraft only needs an outbound connection to that listener.')
   data['endpoint']=endpoint;result={'summary':'The plugin will connect out to the bot. You do not need to open a new port on the Minecraft server.'}
  else:raise ValueError('Choose SSH, local folder, or Paper plugin.')
  self.pending={k:v for k,v in self.pending.items() if v['expires']>time.time()};self.pending[ident]=data
  return {'connection':ident,'kind':kind,**result}

 async def commit(self,user,ident,fingerprint='',guild=''):
  user=str(user);data=self.pending.get(str(ident))
  if not data or data['user']!=user or data['expires']<time.time():raise PermissionError('This connection preview expired. Test it again.')
  self.allowed(user,data['server'])
  profile=copy.deepcopy(self.ux.engine.servers[data['server']]) if data['server'] else {'id':(re.sub(r'[^a-z0-9-]','-',data['name'].casefold()).strip('-')[:30] or 'minecraft')+'-'+uid()[:8],'name':data['name'],'owners':[user],'connectors':{}}
  if data['name']:profile['name']=data['name']
  if guild:profile['guilds']=list(dict.fromkeys(profile.get('guilds',[])+[guild]))
  store=Secrets(self.ux.cfg.get('secrets_file','data/secrets.json'));kind=data['kind'];created=[];refs=[];plugin=None;folder_readable=True;persisted=False
  try:
   if kind=='ssh':
    if not secrets.compare_digest(str(fingerprint),data['fingerprint']):raise PermissionError('Confirm the exact SSH fingerprint shown in the test.')
    ssh=dict(data['ssh']);directory=Path('data/ssh-connections')/uid();directory.mkdir(parents=True,exist_ok=True);os.chmod(directory,0o700)
    known=directory/'known_hosts';keys=paramiko.HostKeys();host=ssh['host'] if ssh['port']==22 else '['+ssh['host']+']:'+str(ssh['port']);keys.add(host,data['hostkey'].get_name(),data['hostkey']);keys.save(str(known));os.chmod(known,0o600);created.append(known);ssh['known_hosts']=str(known)
    if data['key']:
     keypath=directory/'identity';atomic(keypath,data['key']);created.append(keypath);ssh['key_file']=str(keypath)
    for field,key in [('password','password'),('passphrase','key_password')]:
     if data[field]:ssh[key]=store.put('ssh-'+uid(),data[field]);refs.append(ssh[key])
    candidate=HybridTools({'id':profile['id'],'name':profile['name'],'connectors':{'ssh':ssh}},store)
    def verify():
     c=candidate.client()
     try:
      ftp=c.open_sftp()
      try:
       try:ftp.stat(ssh['volume'].rstrip('/\\')+'/server.properties');return True
       except PermissionError:return False
      finally:ftp.close()
     finally:c.close()
    folder_readable=await asyncio.to_thread(verify)
    profile['connectors']['ssh']=ssh
    # Supplying credentials grants server ownership, never implicit host/root
    # delegation to a non-operator account.
   elif kind=='local':profile['connectors']['local']=data['local']
   elif kind=='bridge':
    token=secrets.token_urlsafe(32);ref=store.put('bridge-'+uid(),token);refs.append(ref)
    profile['connectors']['bridge']={'token':ref}
    plugin=yaml.safe_dump({'server-id':profile['id'],'endpoint':data['endpoint'],'token':token,'triggers':self.ux.cfg['social']['triggers']},allow_unicode=True,sort_keys=False)
   existing=self.ux.db.one('SELECT owner FROM kei_registered_servers WHERE id=?',(profile['id'],))
   with self.ux.db.atomic():
    self.ux.db.execute('INSERT OR REPLACE INTO kei_registered_servers VALUES (?,?,?,?)',(profile['id'],dumps(profile),existing['owner'] if existing else user,time.time()))
    self.ux.db.execute('INSERT OR REPLACE INTO kei_grants VALUES (?,?,?,?)',(user,profile['id'],'copilot',user))
    self.ux.access.record(profile['id'],user,user,'connect',kind)
   persisted=True
   self.pending.pop(str(ident),None);self.ux.engine.refresh_servers()
   return {'id':profile['id'],'name':profile['name'],'saved':True,'plugin_config':plugin,'verified':kind!='bridge' and folder_readable,'message':('Connection verified.' if folder_readable else 'SSH login verified; folder access needs checking under People & permissions. No host/root access was automatically granted.') if kind!='bridge' else 'Config created. Install the plugin and use Test connection to verify the live bridge.'}
  except Exception:
   if not persisted:
    for path in created:path.unlink(missing_ok=True)
    for ref in refs:store.delete(ref.removeprefix('secret:'))
   raise
