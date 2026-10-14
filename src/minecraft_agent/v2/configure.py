"""Offline setup check. Reports missing keys/paths, never credential values."""
import os,json,sys
from pathlib import Path
from urllib.parse import urlparse
import yaml
from dotenv import load_dotenv

def load_config():
    load_dotenv()
    path=Path(os.environ.get('KEI_CONFIG','kei.yaml'))
    if not path.is_file():raise RuntimeError('Missing kei.yaml. Copy kei.example.yaml and fill it first.')
    cfg=yaml.safe_load(path.read_text(encoding='utf-8'))
    if not isinstance(cfg,dict):raise RuntimeError('kei.yaml must contain a YAML mapping.')
    problems=[]
    for key in ('DISCORD_BOT_TOKEN','PROVIDER_API_KEY'):
        if not os.environ.get(key,'').strip():problems.append('Fill '+key+' in .env')
    owner=str(cfg.get('owner_id',''))
    if not owner.isdigit() or int(owner)==0:problems.append('Fill owner_id with your Discord user ID')
    base=urlparse(str(cfg.get('provider_base','')))
    if base.scheme not in ('http','https') or not base.netloc:problems.append('Fill provider_base with the /v1 URL of your tool-calling provider')
    prompt=Path(cfg.get('persona_file') or 'prompts/persona.md')
    if not prompt.is_file() or not prompt.read_text(encoding='utf-8').strip():problems.append('Write your own persona in '+str(prompt))
    profiles=cfg.get('servers',[]);assignments=cfg.get('assignments',{})
    if not isinstance(profiles,list):problems.append('servers must be a list');profiles=[]
    if not isinstance(assignments,dict):problems.append('assignments must be a mapping');assignments={}
    ids=[]
    for profile in profiles:
        if not isinstance(profile,dict):problems.append('Every server must be a mapping');continue
        name=str(profile.get('id') or '<unnamed>');ids.append(name)
        for key in ('id','name','host','ssh_user','password_env','known_hosts','uuid','wings_url','wings_token_env','volume','file_owner','minecraft_version'):
            if not profile.get(key):problems.append(name+': fill '+key)
        for key in ('password_env','wings_token_env'):
            if profile.get(key) and not os.environ.get(profile[key]):problems.append(name+': fill the env variable named by '+key)
        if profile.get('known_hosts') and not Path(profile['known_hosts']).is_file():problems.append(name+': add the verified host key to '+profile['known_hosts'])
    if len(set(ids))!=len(ids):problems.append('Server IDs must be unique')
    for user,servers in assignments.items():
        if not str(user).isdigit() or not isinstance(servers,list) or any(s not in ids for s in servers):problems.append('Fix assignment for user '+str(user))
    if problems:raise RuntimeError('\n'.join(problems))
    cfg['owner_id']=owner;cfg['servers']=profiles;cfg['assignments']=assignments
    cfg['persona']=prompt.read_text(encoding='utf-8')
    cfg['persona_variants']={}
    for mode in ('auto','soft','spicy'):
        variant=prompt.parent/('persona-'+mode+'.md')
        if variant.is_file() and variant.read_text(encoding='utf-8').strip():cfg['persona_variants'][mode]=variant.read_text(encoding='utf-8')
    return cfg

def main():
    try:
        cfg=load_config()
        print('Setup OK. '+str(len(cfg['servers']))+' server profile(s). No network requests were made.')
        return 0
    except (RuntimeError,OSError,yaml.YAMLError) as exc:
        print('Setup needs a few things:\n'+str(exc),file=sys.stderr);return 1

if __name__=='__main__':raise SystemExit(main())
