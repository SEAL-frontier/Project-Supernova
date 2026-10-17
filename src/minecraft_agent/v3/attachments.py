"""Explicit task-owned attachment transfer, with backup and byte readback."""
import hashlib,io,json,pathlib,re,time,zipfile
import yaml
from contextvars import ContextVar
from ..v2.model import tool,S

DEFINITION=tool('attachment_install','Copy an actual user attachment to an explicitly requested relative server path. Requires authorized change work. Keeps a backup and verifies the bytes; copying a plugin does not prove it is enabled. Never execute the uploaded contents or extract archives automatically.',{'attachment_id':S,'path':S},['attachment_id','path'])
CONTEXT=ContextVar('kei_attachment_task',default=None)

def install(db):
 db.execute('CREATE TABLE IF NOT EXISTS kei_attachments(id TEXT PRIMARY KEY,message TEXT,actor TEXT,scope TEXT,path TEXT,filename TEXT,sha256 TEXT,bytes INTEGER,at REAL)')

def record(db,message,actor,scope,path,filename):
 install(db);raw=pathlib.Path(path).read_bytes();digest=hashlib.sha256(raw).hexdigest();ident=hashlib.sha256((str(message)+filename).encode()).hexdigest()[:24]
 db.execute('INSERT OR REPLACE INTO kei_attachments VALUES (?,?,?,?,?,?,?,?,?)',(ident,str(message),str(actor),scope,str(path),filename,digest,len(raw),time.time()))
 return ident

def transfer(db,task,args,executor):
 row=db.one('SELECT * FROM kei_attachments WHERE id=?',(args.get('attachment_id'),))
 if not row or row['actor']!=task['requester'] or row['scope']!=task['scope'] or db.tombstoned([row['message']]):raise PermissionError('This attachment does not belong to this task requester and conversation.')
 if row['at']<time.time()-86400:raise ValueError('The attachment expired. Please attach it again.')
 source=pathlib.Path(row['path']).resolve();root=pathlib.Path('data/attachments').resolve()
 if not source.is_relative_to(root) or not source.is_file():raise ValueError('The original attachment is unavailable.')
 raw=source.read_bytes();digest=hashlib.sha256(raw).hexdigest()
 if digest!=row['sha256'] or len(raw)>64*1024*1024:raise ValueError('Attachment checksum/size does not match the saved upload.')
 relative=executor._path(str(args.get('path','')))
 if relative.endswith(('.jar','.zip')):
  with zipfile.ZipFile(io.BytesIO(raw)) as archive:
   if len(archive.infolist())>10000 or sum(i.file_size for i in archive.infolist())>512*1024*1024:raise ValueError('Archive expands beyond the inspection limit.')
   if any(i.filename.startswith(('/','\\')) or '..' in i.filename.replace('\\','/').split('/') for i in archive.infolist()):raise ValueError('Archive contains unsafe paths.')
   if relative.endswith('.jar'):
    descriptor=next((yaml.safe_load(archive.read(n)) for n in ('paper-plugin.yml','plugin.yml') if n in archive.namelist()),None)
    if not isinstance(descriptor,dict) or not descriptor.get('name'):raise ValueError('JAR has no valid Paper/Bukkit plugin descriptor.')
    if not relative.startswith('plugins/'):raise ValueError('Install plugins under plugins/.')
 if executor.local:return executor.local.write_binary(relative,raw)
 backup='.kei-backups/'+str(time.time_ns())+'/'+relative
 if executor.connected_bridge('files'):
  import base64
  result=executor.bridge.rpc_sync(task['server'],'files',{'action':'write_binary','path':relative,'base64':base64.b64encode(raw).decode()},'change',timeout=90)
  return {**result,'verified':result.get('verified') is True,'path':relative,'sha256':digest,'note':'Copied file only; runtime activation is separate.'}
 if executor.panel:
  folder=str(pathlib.PurePosixPath(relative).parent);filename=pathlib.PurePosixPath(relative).name;executor._mkdir_panel(folder)
  listing=executor.do_files('list',folder)['stdout'].splitlines()
  existed=filename in listing
  if existed:
   previous=executor.read_binary(relative);backupfolder=str(pathlib.PurePosixPath(backup).parent);executor._mkdir_panel(backupfolder);executor.panel.upload(backupfolder,previous,filename)
  executor.panel.upload(folder,raw,filename)
  verified=hashlib.sha256(executor.read_binary(relative)).hexdigest()==digest
  return {'verified':verified,'sha256':digest,'path':relative,'backup_path':backup if existed else None,'note':'Copied file only; runtime activation is separate.'}
 if executor.cs.get('ssh',{}).get('volume'):
  # Use the existing scoped text-safe installer for textual files. Binary SFTP
  # keeps a sibling backup without requiring a general host shell permission.
  client=executor.client();ftp=client.open_sftp();target=executor.absolute(relative);backup_target=executor.absolute(backup);temporary=target+'.kei-'+str(time.time_ns());existed=False
  def mkdirs(path):
   parts=pathlib.PurePosixPath(path).parts;current='/' if path.startswith('/') else ''
   for part in parts:
    if part=='/':continue
    current=current.rstrip('/')+'/'+part
    try:ftp.stat(current)
    except FileNotFoundError:ftp.mkdir(current)
  try:
   mkdirs(str(pathlib.PurePosixPath(target).parent))
   try:
    old=ftp.open(target,'rb');existed=True
    try:previous=old.read(64*1024*1024+1)
    finally:old.close()
    if len(previous)>64*1024*1024:raise ValueError('Existing destination is too large for a safe backup.')
    mkdirs(str(pathlib.PurePosixPath(backup_target).parent))
    with ftp.open(backup_target,'wb') as f:f.write(previous)
   except FileNotFoundError:pass
   with ftp.open(temporary,'wb') as f:f.write(raw)
   ftp.posix_rename(temporary,target)
   with ftp.open(target,'rb') as f:actual=hashlib.sha256(f.read(64*1024*1024+1)).hexdigest()
   return {'verified':actual==digest,'sha256':digest,'path':relative,'backup_path':backup if existed else None,'note':'Copied file only; runtime activation is separate.'}
  finally:
   try:ftp.remove(temporary)
   except OSError:pass
   ftp.close();client.close()
 raise ValueError('No file transfer connector is available.')
