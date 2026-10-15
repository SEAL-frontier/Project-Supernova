"""Explicit server/host scope and per-action approval policy; never inferred from SSH presence."""
import time

LEVELS=('default','auto_review','read_only','full_access','custom')
EXTENTS=('minecraft','machine')

def install(db):
    db.execute('CREATE TABLE IF NOT EXISTS kei_execution_permissions(subject TEXT,server TEXT,extent TEXT,level TEXT,issuer TEXT,updated REAL,PRIMARY KEY(subject,server))')

def static_host(cfg,subject,server):
    profile=next((p for p in cfg['servers'] if p['id']==server),{})
    return str(subject)==str(cfg['owner_id']) or str(subject) in set(map(str,profile.get('host_admins',[])))

def policy(db,cfg,subject,server):
    install(db);row=db.one('SELECT * FROM kei_execution_permissions WHERE subject=? AND server=?',(str(subject),server))
    return row or {'subject':str(subject),'server':server,'extent':'machine' if static_host(cfg,subject,server) else 'minecraft','level':'default','issuer':'operator config','updated':None}

def save(db,cfg,issuer,subject,server,extent,level,has_ssh):
    if extent not in EXTENTS or level not in LEVELS:raise ValueError('Chọn phạm vi và mức quyền hợp lệ.')
    if extent=='machine' and (not has_ssh or not static_host(cfg,issuer,server)):
        raise PermissionError('Full Machine cần SSH và quyền cấp truy cập host từ chủ bot.')
    if level=='custom':
        profile=next((p for p in cfg['servers'] if p['id']==server),{})
        if not isinstance(profile.get('approval_rules'),dict):raise ValueError('Chủ bot chưa cấu hình approval_rules cho mức Custom.')
    install(db);db.execute('INSERT OR REPLACE INTO kei_execution_permissions VALUES (?,?,?,?,?,?)',(str(subject),server,extent,level,str(issuer),time.time()))
