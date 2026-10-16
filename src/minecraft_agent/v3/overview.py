"""Owner-only aggregates. Guild activity is not a Minecraft-server/channel ranking."""
import time

def aggregates(ux,now=None):
 now=time.time() if now is None else now;cutoff=now-900
 guild_names={str(g.id):getattr(g,'name','Discord server '+str(g.id)) for g in getattr(ux.bot,'guilds',[])}
 users={};guilds={};dms={}
 rows=ux.db.rows("SELECT user,scope,role,count(*) n,max(at) latest FROM kei_messages WHERE forgotten=0 AND role IN ('user','assistant') GROUP BY user,scope,role")
 human_actors={str(r['user']) for r in rows if r['role']=='user'}
 identities={str(r['user_id']):r for r in ux.db.rows('SELECT user_id,username,global_name,account_display FROM kei_users')}
 for row in rows:
  actor=str(row['user']);scope=row['scope'];parts=scope.split(':')
  if actor not in human_actors:continue
  person=ux.engine.identity.person_for_user(actor)
  discord=ux.engine.identity.discord(person) or actor
  name=identities.get(discord,{})
  user=users.setdefault(person,{'person':person,'id':discord,'display_name':name.get('global_name') or name.get('account_display') or name.get('username') or discord,'username':name.get('username') or '', 'message_count':0,'reply_count':0,'last_at':0,'dm_messages':0,'dm_replies':0,'guild_counts':{}})
  user['last_at']=max(user['last_at'],row['latest']);key='message_count' if row['role']=='user' else 'reply_count';user[key]+=row['n']
  if parts[0]=='dm':
   dm=dms.setdefault(person,{'id':discord,'display_name':user['display_name'],'messages':0,'replies':0,'last_user_at':0,'last_kei_at':0,'last_at':0})
   dm['messages' if row['role']=='user' else 'replies']+=row['n'];dm['last_user_at' if row['role']=='user' else 'last_kei_at']=max(dm['last_user_at' if row['role']=='user' else 'last_kei_at'],row['latest']);dm['last_at']=max(dm['last_at'],row['latest'])
   user['dm_messages' if row['role']=='user' else 'dm_replies']+=row['n']
  elif parts[0]=='guild' and len(parts)>=3 and row['role']=='user':
   gid=parts[1];entry=guilds.setdefault(gid,{'id':gid,'name':guild_names.get(gid,'Discord server '+gid),'messages':0,'last_at':0,'people':set()})
   entry['messages']+=row['n'];entry['last_at']=max(entry['last_at'],row['latest']);entry['people'].add(person)
   user['guild_counts'][gid]=user['guild_counts'].get(gid,0)+row['n']
 for user in users.values():
  account=getattr(ux.bot,'get_user',lambda _:None)(int(user['id'])) if user['id'].isdigit() else None
  user['avatar_url']=str(account.display_avatar.url) if account else None
  user['active']=user['last_at']>=cutoff
  user['top_guilds']=[{'id':gid,'name':guild_names.get(gid,'Discord server '+gid),'messages':n} for gid,n in sorted(user.pop('guild_counts').items(),key=lambda item:item[1],reverse=True)[:3]]
 for entry in guilds.values():entry['people']=len(entry['people'])
 for dm in dms.values():
  dm['active']=dm['last_at']>=cutoff
  dm['status']='No reply yet' if dm['last_user_at']>dm['last_kei_at'] else 'Kei replied'
  action=ux.db.one("SELECT a.kind,a.status,a.at FROM kei_social_actions a JOIN kei_delivery_targets t ON t.action=a.id WHERE t.actor=? AND t.scope LIKE 'dm:%' ORDER BY a.at DESC LIMIT 1",(dm['id'],))
  if action and action['at']>=dm['last_user_at']:
   dm['status']='Kei is responding' if action['status'] in ('pending','sending') else 'Kei reacted' if action['status']=='sent' and action['kind']=='react' else 'Kei replied' if action['status']=='sent' else 'Last response failed' if action['status']=='failed' else 'Delivery unconfirmed'
 return sorted(users.values(),key=lambda u:u['message_count'],reverse=True),sorted(guilds.values(),key=lambda g:g['messages'],reverse=True),sorted(dms.values(),key=lambda d:d['messages'],reverse=True)

def page(request,rows):
 query=request.query.get('search','').strip().casefold()
 if query:rows=[r for r in rows if query in (r.get('display_name','')+' '+r.get('username','')+' '+r['id']).casefold()]
 try:offset=max(0,int(request.query.get('offset',0)))
 except (TypeError,ValueError):offset=0
 return rows[offset:offset+25],offset+25 if offset+25<len(rows) else None

async def overview(dashboard,request):
 now=dashboard.clock();users,guilds,dms=aggregates(dashboard.ux,now);selected,next_offset=page(request,users)
 active_dms=sorted([d for d in dms if d['active']],key=lambda d:d['last_at'],reverse=True)
 active_guilds=[g for g in guilds if g['last_at']>=now-900]
 return {'totals':{'people':len(users),'messages':sum(u['message_count'] for u in users),'active_dms':len(active_dms),'active_guilds':len(active_guilds),'active_channels':len(active_guilds),'guilds_joined':len(getattr(dashboard.ux.bot,'guilds',[]))},
  'active_dms':active_dms[:25],'guild_rankings':guilds[:50],'dm_rankings':dms[:50],
  'joined_guilds':[{'id':str(g.id),'name':getattr(g,'name','Discord server '+str(g.id)),'members':getattr(g,'member_count',None)} for g in getattr(dashboard.ux.bot,'guilds',[])],
  'servers':await dashboard._global_live_servers(),'users':selected,'next_offset':next_offset,'active_window_minutes':15}

def relationships(dashboard,request):
 ux=dashboard.ux;users,_,_=aggregates(ux,dashboard.clock());rows=[]
 for user in users:
  profile=ux.engine.memory.relationship(user['person'],'global');rank=profile['rank'];aliases=ux.db.rows('SELECT DISTINCT alias FROM kei_aliases WHERE person=?',(user['person'],))
  rows.append({**{k:user[k] for k in ('id','display_name','username','avatar_url','message_count','last_at')},'rank':{k:rank.get(k) for k in ('label','category','changed')},'dimensions':{k:profile.get(k,0) for k in ('familiarity','trust','warmth','playfulness','tension','confidence','interaction_frequency')},'aliases':[r['alias'] for r in aliases],
   'calibrated':profile['frequency']['meaningful_sessions_30']>=3,'bond':{k:v for k,v in ux.engine.memory.affect.bond(user['person']).items() if k in ('kind','label','changed')},'mood':ux.engine.memory.affect.context(user['person'],'global'),
   'changes':ux.db.rows('SELECT label,at FROM kei_relationship_changes WHERE person=? ORDER BY at DESC LIMIT 8',(user['person'],))})
 sort=request.query.get('sort','familiarity')
 rows.sort(key=lambda r:r['dimensions'].get(sort,0) if sort in ('familiarity','trust','warmth','tension') else r['message_count'],reverse=True)
 selected,next_offset=page(request,rows)
 return {'users':selected,'total':len(rows),'next_offset':next_offset}
