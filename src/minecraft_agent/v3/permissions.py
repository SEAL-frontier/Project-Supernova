"""Explicit server/host scope and per-action approval policy; never inferred from SSH presence."""
import time

LEVELS=('default','auto_review','read_only','full_access','custom')
EXTENTS=('minecraft','host_user','machine')

def install(db):
    db.execute('CREATE TABLE IF NOT EXISTS kei_custom_permissions(subject TEXT,server TEXT,rules TEXT,PRIMARY KEY(subject,server))')
    db.execute('CREATE TABLE IF NOT EXISTS kei_execution_permissions(subject TEXT,server TEXT,extent TEXT,level TEXT,issuer TEXT,updated REAL,PRIMARY KEY(subject,server))')

def static_host(cfg,subject,server):
    profile=next((p for p in cfg['servers'] if p['id']==server),{})
    return str(subject)==str(cfg['owner_id']) or str(subject) in set(map(str,profile.get('host_admins',[])))

def policy(db,cfg,subject,server):
    install(db);row=db.one('SELECT * FROM kei_execution_permissions WHERE subject=? AND server=?',(str(subject),server))
    return row or {'subject':str(subject),'server':server,'extent':'machine' if static_host(cfg,subject,server) else 'minecraft','level':'default','issuer':'operator config','updated':None}

def save(db,cfg,issuer,subject,server,extent,level,has_ssh,rules=None):
    if extent not in EXTENTS or level not in LEVELS:raise ValueError('Chọn phạm vi và mức quyền hợp lệ.')
    existing=policy(db,cfg,subject,server)
    retained_self=str(issuer)==str(subject) and existing.get('updated') and {'minecraft':0,'host_user':1,'machine':2}.get(existing['extent'],0)>={'minecraft':0,'host_user':1,'machine':2}[extent]
    if extent in ('host_user','machine') and (not has_ssh or not (static_host(cfg,issuer,server) or retained_self)):
        raise PermissionError('Quyền host cần SSH và người được chủ bot cho phép cấp quyền máy chủ.')
    install(db)
    if level=='custom':
        import json
        configured=validate_custom(rules)
        if extent=='minecraft' and configured['tools'].get('remote_shell')=='allow':raise ValueError('Minecraft-only cannot grant host shell access.')
        db.execute('INSERT OR REPLACE INTO kei_custom_permissions VALUES (?,?,?)',(str(subject),server,json.dumps(configured)))
    install(db);db.execute('INSERT OR REPLACE INTO kei_execution_permissions VALUES (?,?,?,?,?,?)',(str(subject),server,extent,level,str(issuer),time.time()))


def custom_for(db,cfg,subject,server):
    import json
    install(db);row=db.one('SELECT rules FROM kei_custom_permissions WHERE subject=? AND server=?',(str(subject),server))
    raw=json.loads(row['rules']) if row else next((p for p in cfg['servers'] if p['id']==server),{}).get('approval_rules',{})
    return validate_custom(raw or {'*':'auto_review'})

def rules_for(db,cfg,subject,server):return custom_for(db,cfg,subject,server)['tools']

def validate_custom(value):
    import tomllib
    if isinstance(value,str):
        if len(value)>6000:raise ValueError('Custom config is limited to 6,000 characters.')
        try:value=tomllib.loads(value)
        except tomllib.TOMLDecodeError as exc:raise ValueError('Invalid TOML: '+str(exc)) from exc
    if not isinstance(value,dict) or not value:raise ValueError('Custom needs at least one explicit rule.')
    if 'tools' not in value:value={'tools':value}
    if set(value)-{'tools','paths','shell'}:raise ValueError('Supported Custom sections: tools, paths, shell.')
    tools=value.get('tools',{})
    names={'*','inspect','power','console','files','plugin_install','remote_shell','plugin_search','fetch_url','web_search','profiler','verify_action','find_server_files','task_evidence'}
    if not isinstance(tools,dict) or not tools or not set(tools)<=names or any(v not in ('allow','deny','auto_review','ask') for v in tools.values()):raise ValueError('Each tool rule must be allow, deny or auto_review.')
    out={'tools':{k:('auto_review' if v=='ask' else v) for k,v in tools.items()}}
    for section in ('paths','shell'):
        values=value.get(section,{})
        if not isinstance(values,dict) or set(values)-{'allow','deny'}:raise ValueError(section+' supports only allow and deny lists.')
        for key,patterns in values.items():
            if not isinstance(patterns,list) or len(patterns)>30 or any(not isinstance(v,str) or not 1<=len(v)<=220 or any(c in v for c in ('\n','\r','\x00')) for v in patterns):raise ValueError('Use a list of up to 30 short glob patterns.')
        out[section]=values
    return out

def custom_text(config):
    import json
    return '\n\n'.join('['+section+']\n'+'\n'.join(json.dumps(k)+' = '+json.dumps(v) for k,v in values.items()) for section,values in config.items() if values)

def custom_block(db,cfg,subject,server,name,args):
    import fnmatch
    config=custom_for(db,cfg,subject,server)
    for section,value in [('paths',str(args.get('path',''))),('shell',str(args.get('command','')) if name=='remote_shell' else '')]:
        if not value:continue
        rules=config.get(section,{})
        if any(fnmatch.fnmatchcase(value,p) for p in rules.get('deny',[])):return 'Custom '+section+' deny rule matched.'
        if rules.get('allow') and not any(fnmatch.fnmatchcase(value,p) for p in rules['allow']):return 'Outside the Custom '+section+' allow list.'
    return None
