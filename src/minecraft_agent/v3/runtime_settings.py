"""Validated bot defaults shared by the owner dashboard and headless config."""
import re

DEFAULTS={
 'chat_model':'ag/gemini-3.8-flash-low','agent_model':'ag/gemini-3.8-flash-high',
 'trigger_name':'kei','followup_seconds':90,'followup_turn_limit':4,'context_messages':10,
 'relationship_notice_min_delta':.006,'rank_confirmation_hours':6,'rank_notice_hours':6,'rank_notice_minutes':10,
 'dynamic_status':True,'operator_public_name':'','hosted_credential_notice':False,'dynamic_mood':True,'romantic_bonds':True,'work_sulking':True,
 'proactive_enabled':True,'dm_daily_limit':3,'quiet_start':22,'quiet_end':8,
 'recent_turns':96,'memory_context_chars':32000,'retention_days':90,'incremental_hours':6,'daily_hour':4,
}
SOCIAL=set(DEFAULTS)-{'chat_model','agent_model','recent_turns','memory_context_chars','retention_days','incremental_hours','daily_hour'}
MEMORY={'recent_turns','memory_context_chars','retention_days','incremental_hours','daily_hour'}
BOUNDS={'followup_seconds':(15,600),'followup_turn_limit':(1,12),'context_messages':(3,30),
 'relationship_notice_min_delta':(.003,.1),'rank_confirmation_hours':(1,72),'rank_notice_hours':(1,168),'rank_notice_minutes':(0,1440),
 'dm_daily_limit':(0,12),'quiet_start':(0,23),'quiet_end':(0,23),'recent_turns':(12,200),
 'memory_context_chars':(4000,96000),'retention_days':(7,730),'incremental_hours':(1,24),'daily_hour':(0,23)}

def read(cfg):
 out={**DEFAULTS}
 for key in out:
  section=cfg.get('social',{}) if key in SOCIAL else cfg.get('memory',{}) if key in MEMORY else cfg
  out[key]=section.get(key,out[key])
 out['trigger_name']=(cfg.get('social',{}).get('triggers') or ['kei'])[0]
 return out

def validate(key,value):
 if key in ('chat_model','agent_model'):
  if not isinstance(value,str) or value.startswith(('http:','https:','sk-')) or not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_./:-]{0,119}',value):raise ValueError('Enter a model ID, not a URL or provider secret.')
 elif key=='trigger_name':
  if not isinstance(value,str) or not 2<=len(value.strip())<=24 or not re.fullmatch(r'[\w -]+',value):raise ValueError('Use a short name without mentions or punctuation.')
  value=value.strip().casefold()
 elif key=='operator_public_name':
  if not isinstance(value,str) or len(value)>40 or re.search(r'[@<>\r\n]',value):raise ValueError('Use a short public name without mentions.')
  value=value.strip()
 elif key in ('proactive_enabled','hosted_credential_notice','dynamic_status','dynamic_mood','romantic_bonds','work_sulking'):
  if type(value) is not bool:raise ValueError('Proactive messages must be on or off.')
 elif key in BOUNDS:
  low,high=BOUNDS[key]
  if type(value) not in (int,float) or not low<=value<=high or (key!='relationship_notice_min_delta' and int(value)!=value):raise ValueError(f'{key} must be between {low} and {high}.')
  value=float(value) if key=='relationship_notice_min_delta' else int(value)
 else:raise ValueError('Unknown bot setting.')
 return value

def apply(cfg,values):
 for key,value in values.items():
  if key not in DEFAULTS:continue
  target=cfg.setdefault('social',{}) if key in SOCIAL else cfg.setdefault('memory',{}) if key in MEMORY else cfg
  target[key]=value
  if key=='trigger_name':target['triggers']=[value]
