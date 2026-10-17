"""Small, private Discord setup/settings flows and shared server-side access checks.

The dashboard uses exactly the same service as Discord. Neither UI supplies authority.
"""

from __future__ import annotations

import asyncio
import copy
import hashlib
import json
import logging
import re
import time
from urllib.parse import urlsplit

import discord
from discord import app_commands

from ..v2 import persona
from ..v2.store import dumps, uid
from .config import Secrets, save_config
from .panel import Panel
from .instructions import get as personal_instructions

LOG = logging.getLogger("kei.commands")


class Access:
    """Additive delegated administration; relationship state is never consulted."""

    def __init__(self, engine):
        self.engine = engine
        self.db = engine.db
        self.db.db.executescript("""
          CREATE TABLE IF NOT EXISTS kei_server_admins(
            server TEXT,user TEXT,issuer TEXT,created REAL,revoked REAL,
            PRIMARY KEY(server,user));
          CREATE TABLE IF NOT EXISTS kei_access_history(
            id TEXT PRIMARY KEY,server TEXT,subject TEXT,issuer TEXT,
            action TEXT,level TEXT,at REAL);
        """)
        self.db.db.commit()

    def owner(self, user, server):
        user = str(user)
        if server not in self.engine.servers:
            return False
        row = self.db.one("SELECT owner FROM kei_registered_servers WHERE id=?", (server,))
        return (
            user == str(self.engine.cfg["owner_id"])
            or user in list(map(str, self.engine.servers[server].get("owners", [])))
            or bool(row and row["owner"] == user)
            or bool(self.db.one("SELECT user FROM kei_server_owners WHERE server=? AND user=? AND revoked IS NULL",(server,user)))
        )

    def manager(self, user, server):
        return self.owner(user, server) or bool(
            self.db.one(
                "SELECT user FROM kei_server_admins WHERE server=? AND user=? AND revoked IS NULL",
                (server, str(user)),
            )
        )

    def record(self, server, subject, issuer, action, level=""):
        self.db.execute(
            "INSERT INTO kei_access_history VALUES (?,?,?,?,?,?,?)",
            (uid(), server, str(subject), str(issuer), action, level, time.time()),
        )

        if action in ('grant','member_saved') and hasattr(self.engine,'reports') and not self.owner(issuer,server):
            actor=self.db.one('SELECT global_name,account_display,username FROM kei_users WHERE user_id=?',(str(issuer),)) or {}
            display=actor.get('global_name') or actor.get('account_display') or actor.get('username') or str(issuer)
            labels={'observe':'chỉ xem','copilot':'thao tác Minecraft','chat':'chỉ trò chuyện','observer':'người xem','moderator':'moderator','admin':'admin','owner':'đồng sở hữu'}
            self.engine.reports.record(server,'admin',issuer,display+' đã đổi quyền tài khoản '+str(subject)+' thành '+labels.get(level,level)+'.',dedupe='access:'+server+':'+str(issuer)+':'+str(subject)+':'+action+':'+level+':'+str(int(time.time()//15)))

    def grant(self, issuer, subject, server, level):
        issuer, subject = str(issuer), str(subject)
        if not self.manager(issuer, server):
            raise PermissionError("Bạn chưa được owner cho quản lý quyền server này.")
        if level not in ("chat", "observe", "copilot"):
            raise ValueError("Chọn chat, observe hoặc copilot.")
        if self.owner(subject, server) and not self.owner(issuer, server):
            raise PermissionError("Admin không thể sửa quyền của owner.")
        with self.db.atomic():
            self.db.execute(
                "INSERT OR REPLACE INTO kei_grants VALUES (?,?,?,?)",
                (subject, server, level, issuer),
            )
            if level == "chat":
                self.db.execute(
                    "DELETE FROM kei_assignments WHERE user=? AND server=?", (subject, server)
                )
            self.record(server, subject, issuer, "grant", level)

    def delegate(self, issuer, subject, server, enabled=True, level="observe"):
        issuer, subject = str(issuer), str(subject)
        if not self.owner(issuer, server):
            raise PermissionError("Chỉ owner server được bổ nhiệm hoặc gỡ admin.")
        if self.owner(subject, server):
            raise ValueError("Owner đã có quyền quản lý server.")
        with self.db.atomic():
            if enabled:
                if level not in ("observe", "copilot"):
                    raise ValueError("Quyền admin cần observe hoặc copilot.")
                self.db.execute(
                    "INSERT OR REPLACE INTO kei_server_admins VALUES (?,?,?,?,NULL)",
                    (server, subject, issuer, time.time()),
                )
                self.grant(issuer, subject, server, level)
                self.record(server, subject, issuer, "admin_grant", level)
            else:
                self.db.execute(
                    "UPDATE kei_server_admins SET revoked=? WHERE server=? AND user=?",
                    (time.time(), server, subject),
                )
                # Explicit chat shadows old config assignments as well as current DB grants.
                self.grant(issuer, subject, server, "chat")
                self.clear_policy(subject,server)
                self.record(server, subject, issuer, "admin_revoke", "chat")

    def revoke(self, issuer, subject, server):
        if self.owner(subject, server):
            raise PermissionError("Không gỡ owner qua màn hình phân quyền.")
        if self.db.one(
            "SELECT user FROM kei_server_admins WHERE server=? AND user=? AND revoked IS NULL",
            (server, str(subject)),
        ):
            self.delegate(issuer, subject, server, False)
            return
        self.grant(issuer, subject, server, "chat")
        self.clear_policy(subject,server)
        self.record(server, subject, issuer, "revoke", "chat")

    def coowner(self,issuer,subject,server,enabled=True):
        if not self.owner(issuer,server):raise PermissionError('Chỉ chủ server được thêm hoặc gỡ đồng sở hữu.')
        fixed={str(self.engine.cfg['owner_id']),*map(str,self.engine.servers[server].get('owners',[]))}
        registered=self.db.one('SELECT owner FROM kei_registered_servers WHERE id=?',(server,))
        if registered:fixed.add(registered['owner'])
        if str(subject) in fixed:raise ValueError('Chủ gốc được giữ trong cấu hình triển khai; bạn vẫn có thể sửa mức thực thi của mình.')
        with self.db.atomic():
            if enabled:
                self.db.execute('INSERT OR REPLACE INTO kei_server_owners VALUES (?,?,?,?,NULL)',(server,str(subject),str(issuer),time.time()))
                self.grant(issuer,subject,server,'copilot')
            else:
                self.db.execute('UPDATE kei_server_owners SET revoked=? WHERE server=? AND user=?',(time.time(),server,str(subject)))
                self.db.execute('UPDATE kei_server_admins SET revoked=? WHERE server=? AND user=?',(time.time(),server,str(subject)))
                self.db.execute('INSERT OR REPLACE INTO kei_grants VALUES (?,?,?,?)',(str(subject),server,'chat',str(issuer)))
                self.clear_policy(subject,server)
            self.record(server,subject,issuer,'owner_grant' if enabled else 'owner_revoke')

    def configure_member(self,issuer,subject,server,role,level='copilot',execution=None):
        issuer,subject=str(issuer),str(subject)
        if not self.manager(issuer,server):raise PermissionError('Bạn chưa quản lý server này.')
        if role not in ('observer','moderator','admin','owner'):raise ValueError('Chọn vai trò hợp lệ.')
        if level not in ('observe','copilot'):raise ValueError('Chọn quyền xem hoặc thao tác server.')
        is_owner=self.owner(subject,server)
        current_admin=bool(self.db.one('SELECT user FROM kei_server_admins WHERE server=? AND user=? AND revoked IS NULL',(server,subject)))
        if (role in ('admin','owner') or current_admin or is_owner) and not self.owner(issuer,server):raise PermissionError('Chỉ chủ server được sửa owner hoặc admin.')
        if is_owner and role!='owner' and not self.db.one('SELECT user FROM kei_server_owners WHERE server=? AND user=? AND revoked IS NULL',(server,subject)):
            raise ValueError('Chủ gốc được giữ trong cấu hình triển khai; bạn vẫn có thể sửa mức thực thi của mình.')
        with self.db.atomic():
            # Validate/save execution before a co-owner voluntarily gives up authority.
            if execution:
                if not isinstance(execution,dict):raise ValueError('Mức thực thi chưa hợp lệ.')
                self.set_policy(issuer,subject,server,execution.get('extent'),execution.get('level'),execution.get('config',execution.get('rules')))
            if role=='owner':
                if not is_owner:self.coowner(issuer,subject,server,True)
            else:
                if is_owner:self.db.execute('UPDATE kei_server_owners SET revoked=? WHERE server=? AND user=?',(time.time(),server,subject))
                if role=='admin':self.db.execute('INSERT OR REPLACE INTO kei_server_admins VALUES (?,?,?,?,NULL)',(server,subject,issuer,time.time()))
                else:self.db.execute('UPDATE kei_server_admins SET revoked=? WHERE server=? AND user=?',(time.time(),server,subject))
                assigned='observe' if role=='observer' else level if role=='admin' else 'copilot'
                self.db.execute('INSERT OR REPLACE INTO kei_grants VALUES (?,?,?,?)',(subject,server,assigned,issuer))
            self.record(server,subject,issuer,'member_saved',role)

    def set_policy(self,issuer,subject,server,extent,level,rules=None):
        if not self.owner(issuer,server):raise PermissionError('Chỉ chủ server được đổi phạm vi và mức thực thi.')
        from .permissions import save
        tool=self.engine.tools.get(server);has_ssh=bool(getattr(tool,'cs',{}).get('ssh'))
        save(self.db,self.engine.cfg,issuer,subject,server,extent,level,has_ssh,rules)
        self.record(server,str(subject),str(issuer),'execution_policy',extent+':'+level)

    def clear_policy(self,subject,server):
        from .permissions import install
        install(self.db)
        self.db.execute('DELETE FROM kei_execution_permissions WHERE subject=? AND server=?',(str(subject),server))
        self.db.execute('DELETE FROM kei_custom_permissions WHERE subject=? AND server=?',(str(subject),server))

    def visible(self, user, scope=None):
        assigned = set(self.engine.assigned(str(user)))
        parts = str(scope or "").split(":")
        guild = parts[1] if len(parts) > 1 and parts[0] == "guild" else None
        return [
            s
            for s, p in self.engine.servers.items()
            if (s in assigned or self.manager(user, s))
            and (not guild or not p.get("guilds") or guild in set(map(str, p["guilds"])))
        ]

    def entries(self, user, server):
        if not self.manager(user, server):
            raise PermissionError("Bạn chưa được xem phân quyền server này.")
        grants = self.db.rows("SELECT * FROM kei_grants WHERE server=?", (server,))
        admins = {
            r["user"]: r
            for r in self.db.rows(
                "SELECT * FROM kei_server_admins WHERE server=? AND revoked IS NULL", (server,)
            )
        }
        entries = [
            {
                **g,
                "admin": g["subject"] in admins,
                "admin_issuer": admins.get(g["subject"], {}).get("issuer"),
            }
            for g in grants
        ]
        profile=self.engine.servers[server]
        people={entry['subject']:entry for entry in entries}
        registered=self.db.one('SELECT owner FROM kei_registered_servers WHERE id=?',(server,))
        owners=set(map(str,profile.get('owners',[])))|{str(self.engine.cfg['owner_id'])}
        if registered:owners.add(registered['owner'])
        coowners={r['user']:r for r in self.db.rows('SELECT * FROM kei_server_owners WHERE server=? AND revoked IS NULL',(server,))}
        owners.update(coowners)
        for subject in owners:
            people[subject]={**people.get(subject,{}),'subject':subject,'level':self.engine.permission(subject,server),'issuer':'','owner':True,'admin':True,'coowner':subject in coowners,'issuer':coowners.get(subject,{}).get('issuer','')}
        for subject, assigned in self.engine.cfg.get('assignments',{}).items():
            if server in assigned and str(subject) not in people:
                people[str(subject)]={'subject':str(subject),'level':self.engine.permission(str(subject),server),'issuer':'','configured':True,'admin':str(subject) in admins}
        for subject in admins:
            people.setdefault(subject,{'subject':subject,'level':self.engine.permission(subject,server),'issuer':admins[subject]['issuer'],'admin':True})
        for entry in people.values():
            from .permissions import policy
            entry['execution']=policy(self.db,self.engine.cfg,entry['subject'],server)
            from .permissions import rules_for,custom_for,custom_text
            saved=custom_for(self.db,self.engine.cfg,entry['subject'],server)
            entry['execution']['rules']=rules_for(self.db,self.engine.cfg,entry['subject'],server)
            entry['execution']['custom']={key:saved[key] for key in ('paths','shell','instructions')}
            entry['execution']['config']=custom_text(saved)
            entry['role']='owner' if entry.get('owner') else 'admin' if entry.get('admin') else entry['level']
            entry['permissions']=['View status, performance and logs'] if entry['level'] in ('observe','copilot') else ['Trò chuyện với Kei']
            if entry['level']=='copilot':entry['permissions'].append('Ask Kei to operate this server within the assigned access level and run mode')
            if entry.get('admin'):entry['permissions'].append('Manage members assigned to this server')
        return sorted(people.values(),key=lambda e:(not e.get('owner'),e['subject']))


class UserExperience:
    def __init__(self, bot):
        self.bot = bot
        self.db = bot.store
        self.engine = bot.engine
        self.cfg = bot.cfg
        self.access = Access(self.engine)
        self.engine.access = self.access
        self._load_global_defaults()
        self.pending_connections = {}
        self.dashboard = None
        self.people_cache = {}

    def _load_global_defaults(self):
        """Apply the owner's persisted bot-wide defaults before commands start."""
        rows=self.db.rows('SELECT key,value FROM kei_global_settings')
        saved={row['key']:json.loads(row['value']) for row in rows}
        from .runtime_settings import apply
        apply(self.cfg,saved)
        if 'timezone' in saved:self.cfg['timezone']=saved['timezone']
        if 'allow_self_service' in saved:self.cfg['allow_self_service']=bool(saved['allow_self_service'])
        if 'default_run_mode' in saved:self.cfg['default_execution_mode']=saved['default_run_mode']
        self.engine.cfg.update(self.cfg)
        if hasattr(self.engine.model,'for_model'):self.engine.model.model=self.cfg.get('agent_model','ag/gemini-3.8-flash-high')

    def global_settings(self,user):
        if str(user)!=str(self.cfg['owner_id']):raise PermissionError('Chỉ main owner mới chỉnh được bot-wide settings.')
        saved={row['key']:json.loads(row['value']) for row in self.db.rows('SELECT key,value FROM kei_global_settings')}
        from .runtime_settings import read
        return {**read(self.cfg),'timezone':str(self.cfg.get('timezone','Asia/Ho_Chi_Minh')),
                'allow_self_service':bool(self.cfg.get('allow_self_service',False)),
                'default_run_mode':self.cfg.get('default_execution_mode','default')}

    def update_global_settings(self,user,values):
        if str(user)!=str(self.cfg['owner_id']):raise PermissionError('Chỉ main owner mới chỉnh được bot-wide settings.')
        from .runtime_settings import DEFAULTS, validate
        if not isinstance(values,dict) or not values or not set(values)<= set(DEFAULTS)|{'timezone','allow_self_service','default_run_mode'}:
            raise ValueError('Chọn timezone, self-service hoặc default approval mode hợp lệ.')
        updated=self.global_settings(user)
        for key,value in values.items():
            if key in DEFAULTS:updated[key]=validate(key,value)
        if 'timezone' in values:
            try:
                from zoneinfo import ZoneInfo
                if not isinstance(values['timezone'],str) or not values['timezone'].strip():raise ValueError()
                ZoneInfo(values['timezone'].strip())
            except Exception as exc:raise ValueError('Use a valid IANA time zone, for example Asia/Ho_Chi_Minh.') from exc
            updated['timezone']=values['timezone'].strip()
        if 'allow_self_service' in values:
            if type(values['allow_self_service']) is not bool:raise ValueError('Self-service must be on or off.')
            updated['allow_self_service']=values['allow_self_service']
        if 'default_run_mode' in values:
            if values['default_run_mode'] not in ('default','auto_review'):raise ValueError('New grants can default to Ask for approval or Approve for me.')
            updated['default_run_mode']=values['default_run_mode']
        with self.db.atomic():
            for key,value in updated.items():
                self.db.execute('INSERT OR REPLACE INTO kei_global_settings VALUES (?,?,?,?)',(key,json.dumps(value),time.time(),str(user)))
        self.cfg['timezone']=updated['timezone'];self.engine.cfg['timezone']=updated['timezone']
        self.cfg['allow_self_service']=updated['allow_self_service'];self.engine.cfg['allow_self_service']=updated['allow_self_service']
        self.cfg['default_execution_mode']=updated['default_run_mode'];self.engine.cfg['default_execution_mode']=updated['default_run_mode']
        self._load_global_defaults()
        if getattr(self.engine,'bridge',None):self.engine.bridge.refresh_aliases()
        return updated

    def person(self, user):
        return self.engine.identity.resolve("discord", str(user))

    async def public_person(self, user, server=None, cached_only=False):
        user=str(user);cached=self.people_cache.get(user)
        if cached and cached[0]>time.time() and (cached_only or cached[1].get('avatar_url')):return cached[1]
        from ..v2.identity import identity_record, sync_identity
        record=identity_record(self.db,user)
        result={'id':user,'display_name':record.get('display_name') or 'Tài khoản Discord','username':record.get('username') or '', 'avatar_url':None}
        account=getattr(self.bot,'get_user',lambda _:None)(int(user))
        if account is None and not cached_only and hasattr(self.bot,'fetch_user'):
            try:account=await self.bot.fetch_user(int(user))
            except discord.HTTPException:pass
        if account:
            sync_identity(self.db,account)
            result.update(display_name=str(getattr(account,'global_name',None) or account.display_name),username=str(account.name))
            avatar=str(account.display_avatar.url)
            if urlsplit(avatar).scheme=='https' and urlsplit(avatar).hostname=='cdn.discordapp.com':result['avatar_url']=avatar
        self.people_cache[user]=(time.time()+300,result)
        return result

    async def access_preview(self,user,server,subject):
        if not self.access.manager(str(user),server):raise PermissionError('Bạn chưa được quản lý quyền trên server này.')
        if not str(subject).isdigit() or len(str(subject))>22:raise ValueError('Nhập Discord ID hoặc dán mention của người muốn thêm.')
        account=await self.public_person(str(subject),server)
        existing=next((g for g in self.access.entries(str(user),server) if g['subject']==str(subject)),None)
        return {'person':account,'existing':existing}

    def state(self, user, scope=None):
        user = str(user)
        scope = scope or "dm:" + user
        pref = self.engine.memory.preference(self.person(user))
        linked = self.db.rows(
            "SELECT account,server,verified FROM kei_accounts WHERE person=? AND platform='minecraft'",
            (self.person(user),),
        )
        selected = self.db.one("SELECT server FROM kei_selected WHERE scope=?", ("dm:" + user,))
        servers = []
        for sid in self.access.visible(user, scope):
            p = self.engine.servers[sid]
            servers.append(
                {
                    "id": sid,
                    "name": p.get("name", sid),
                    "level": self.engine.permission(user, sid),
                    "owner": self.access.owner(user, sid),
                    "ssh_user": str(getattr(self.engine.tools.get(sid),'cs',{}).get('ssh',{}).get('user','')) if self.access.manager(user,sid) else "",
                    "host_available": bool(getattr(self.engine.tools.get(sid),'cs',{}).get('ssh')),
                    "can_grant_host": __import__('minecraft_agent.v3.permissions',fromlist=['static_host']).static_host(self.cfg,user,sid),
                    "manage_access": self.access.manager(user, sid),
                    "capabilities": self.engine.tools[sid].capabilities(),
                    "connections": [k for k,v in getattr(self.engine.tools[sid],'cs',{}).items() if v],
                    "report_preferences": self.engine.reports.settings(user,sid),
                }
            )
        return {
            "user": user,
            "is_bot_owner": user == str(self.cfg["owner_id"]),
            "custom_instructions": personal_instructions(self.db,self.person(user)),
            "call_names": __import__("minecraft_agent.v3.social_runtime",fromlist=["names"]).names(self.db,self.person(user)),
            "persona": persona.mode(self.db, user),
            "debug": self.engine.progress.mode(user),
            "preferences": {k: v for k, v in pref.items() if k != "person"},
            "linked_accounts": linked,
            "servers": servers,
            "default_server": selected["server"] if selected else None,
            "can_connect": user == str(self.cfg["owner_id"])
            or bool(self.cfg.get("allow_self_service")),
            "web_url": (
                self.cfg.get("web", {}).get("public_url", "")
                if self.cfg.get("web", {}).get("enabled")
                else ""
            ),
        }

    def update(self, user, values):
        user = str(user)
        allowed = {
            "persona",
            "debug",
            "dm_opt_in",
            "sharing",
            "muted",
            "timezone",
            "default_server",
            "rank_notifications",
            "romantic_opt_in",
            "romance_mode",
            "custom_instructions",
            "call_names",
        }
        if not isinstance(values, dict) or not set(values) <= allowed:
            raise ValueError("Thiết lập không hợp lệ.")
        pref = {k: v for k, v in values.items() if k not in {"persona", "debug", "default_server", "custom_instructions", "call_names"}}
        if 'custom_instructions' in values and (not isinstance(values['custom_instructions'],str) or len(values['custom_instructions'])>2000):
            raise ValueError('Lời dặn riêng tối đa 2.000 ký tự.')
        for key in ("dm_opt_in", "muted", "rank_notifications", "romantic_opt_in"):
            if key in pref and type(pref[key]) is not bool:
                raise ValueError(key + " cần true hoặc false.")
        if "romance_mode" in pref and pref["romance_mode"] not in ("off","organic","mutual"):raise ValueError("Choose off, organic or mutual.")
        if "persona" in values and values["persona"] not in persona.MODES:
            raise ValueError("Chọn auto, soft hoặc spicy.")
        if "debug" in values and values["debug"] not in ("off", "minimal", "advanced"):
            raise ValueError("Chọn off, minimal hoặc advanced.")
        if "default_server" in values and values["default_server"] not in self.access.visible(user):
            raise PermissionError("Bạn chưa được dùng server này.")
        if "timezone" in pref:
            try:
                from zoneinfo import ZoneInfo

                if not isinstance(pref["timezone"], str):
                    raise ValueError()
                ZoneInfo(pref["timezone"])
            except Exception as exc:
                raise ValueError("Múi giờ chưa hợp lệ. Ví dụ: Asia/Ho_Chi_Minh.") from exc
        # Validate everything before changing multiple personal preferences.
        with self.db.atomic():
            if 'call_names' in values:
                from .social_runtime import set_names
                set_names(self.db,self.person(user),values['call_names'])
                if self.engine.bridge:self.engine.bridge.refresh_aliases()
            if 'custom_instructions' in values:
                from .instructions import set as save_instructions
                save_instructions(self.db,self.person(user),values['custom_instructions'])
            if pref:
                self.engine.memory.set_preference(self.person(user), **pref)
            if "persona" in values:
                persona.set_mode(self.db, user, values["persona"])
            if "debug" in values:
                self.engine.progress.set_mode(user, values["debug"])
            if "default_server" in values:
                self.db.execute(
                    "INSERT OR REPLACE INTO kei_selected VALUES (?,?)",
                    ("dm:" + user, values["default_server"]),
                )
        return self.state(user)

    def claim(self, user, code):
        expected = self.cfg.get("owner_claim_hash")
        if not expected or str(self.cfg["owner_id"]) != "0" or not isinstance(code, str):
            raise PermissionError("Bot đã có owner hoặc mã không còn hiệu lực.")
        import secrets

        actual = hashlib.sha256(code.strip().encode()).hexdigest()
        if not secrets.compare_digest(actual, expected):
            raise PermissionError("Mã owner chưa đúng.")
        user = str(user)
        self.cfg["owner_id"] = user
        self.cfg.pop("owner_claim_hash", None)
        for p in self.cfg["servers"]:
            if p.get("owners") == ["0"]:
                p["owners"] = [user]
                assignments = self.cfg.setdefault("assignments", {}).setdefault(user, [])
                if p["id"] not in assignments:
                    assignments.append(p["id"])
                self.db.execute(
                    "INSERT OR IGNORE INTO kei_assignments VALUES (?,?)", (user, p["id"])
                )
        save_config(self.cfg, self.cfg["_path"])
        self.engine.refresh_servers()

    def profile(self, user, scope):
        if hasattr(self.engine.memory, "profile"):
            return self.engine.memory.profile(str(user), scope, viewer=str(user))
        return {
            "dimensions": self.engine.memory.relationship(self.person(user), scope),
            "rank": {"label": "Neutral"},
            "memories": [],
            "changes": [],
        }

    def set_ambient(self, user, guild, mode, channel="", can_manage=False):
        if not guild or (str(user) != str(self.cfg["owner_id"]) and not can_manage):
            raise PermissionError("Cần quyền quản lý guild Discord để đổi mục này.")
        if mode not in ("off", "whitelist", "free"):
            raise ValueError("Chọn off, whitelist hoặc free.")
        key = "ambient:guild:" + str(guild)
        row = self.db.one("SELECT value FROM kei_meta WHERE key=?", (key,))
        previous = (
            json.loads(row["value"])
            if row
            else {"enabled": False, "mode": "whitelist", "channels": []}
        )
        previous.update(enabled=mode != "off", mode=mode if mode != "off" else previous["mode"])
        if mode == "whitelist":
            if not str(channel).isdigit():
                raise ValueError("Chọn kênh Discord hợp lệ.")
            previous["channels"] = list(dict.fromkeys(previous["channels"] + [str(channel)]))
        self.db.execute("INSERT OR REPLACE INTO kei_meta VALUES (?,?)", (key, dumps(previous)))
        return previous

    async def activate_web(self, user, client_id, client_secret):
        if str(user) != str(self.cfg["owner_id"]):
            raise PermissionError("Chỉ operator của bot được cấu hình Discord OAuth.")
        client_id, client_secret = str(client_id).strip(), str(client_secret).strip()
        if not client_id.isdigit() or not 16 <= len(client_secret) <= 512:
            raise ValueError("Client ID cần dạng số; kiểm tra lại Discord OAuth client secret.")
        webcfg = copy.deepcopy(self.cfg.get("web", {}))
        if not webcfg.get("public_url"):
            raise ValueError(
                "Đặt web.public_url và HTTPS cho deployment trước; xem docs/SETTINGS.md."
            )
        from .dashboard import Dashboard

        # Validate callback configuration before persisting a credential.
        checked = Dashboard(self)
        checked.configure()
        ref = Secrets(self.cfg.get("secrets_file", "data/secrets.json")).put(
            "discord-oauth-client-secret", client_secret
        )
        webcfg.update(enabled=True, client_id=client_id, client_secret_ref=ref)
        webcfg.pop("client_secret", None)
        self.cfg["web"] = webcfg
        save_config(self.cfg, self.cfg["_path"])
        if self.dashboard:
            await self.dashboard.close()
        self.dashboard = Dashboard(self)
        await self.dashboard.start()
        return {
            "ready": bool(self.dashboard.auth_ready and self.dashboard.runner),
            "url": str(webcfg["public_url"]),
            "callback": str(
                webcfg.get("redirect_uri")
                or str(webcfg["public_url"]).rstrip("/") + "/oauth/callback"
            ),
        }

    async def connection_preview(self, user, url, token):
        user = str(user)
        if user != str(self.cfg["owner_id"]) and not self.cfg.get("allow_self_service", False):
            raise PermissionError("Operator chưa mở tự kết nối server. Nhờ owner cấp quyền trước.")
        parsed = urlsplit(str(url))
        if (
            parsed.scheme not in ("http", "https")
            or not parsed.netloc
            or parsed.username
            or parsed.password
            or parsed.query
            or parsed.fragment
        ):
            raise ValueError("Nhập Panel URL dạng https://panel.example.com, không kèm mật khẩu.")
        if not isinstance(token, str) or len(token.strip()) < 10 or len(token) > 512:
            raise ValueError("Nhập Client API key từ trang Account của Panel.")
        # The credential exists only server-side; preview does not persist a failed key.
        secret_store = Secrets(self.cfg.get("secrets_file", "data/secrets.json"))

        class CandidateSecrets:
            def get(self, ref, default=""):
                return token if ref == "candidate" else secret_store.get(ref, default)

        panel = Panel({"url": str(url).rstrip("/"), "token": "candidate"}, CandidateSecrets())
        try:
            rows = await asyncio.to_thread(panel.servers)
        finally:
            panel.close()
        if not rows:
            raise ValueError("Panel account này chưa truy cập được server nào.")
        self.pending_connections = {
            k: v for k, v in self.pending_connections.items() if v["expires"] > time.time()
        }
        ident = uid()
        self.pending_connections[ident] = {
            "user": user,
            "url": str(url).rstrip("/"),
            "token": token,
            "rows": rows,
            "expires": time.time() + 600,
        }
        return {
            "connection": ident,
            "servers": [
                {"index": i, "name": str(r["name"]), "uuid": str(r["uuid"])}
                for i, r in enumerate(rows[:100])
            ],
        }

    def connection_commit(self, user, connection, index, guild=""):
        user = str(user)
        candidate = self.pending_connections.get(str(connection))
        if not candidate or candidate["user"] != user or candidate["expires"] < time.time():
            raise PermissionError("Lượt kết nối đã hết hạn hoặc thuộc người khác. Thử lại nhé.")
        if user != str(self.cfg["owner_id"]) and not self.cfg.get("allow_self_service", False):
            raise PermissionError("Quyền kết nối server đã thay đổi.")
        if type(index) is not int or index < 0 or index >= len(candidate["rows"]):
            raise ValueError("Chọn server trong danh sách vừa kiểm tra.")
        row = candidate["rows"][index]
        matched = next(
            (
                p
                for p in self.engine.servers.values()
                if p.get("uuid") == row["uuid"]
                or p.get("connectors", {}).get("panel", {}).get("server") == row["uuid"]
            ),
            None,
        )
        if matched and not self.access.owner(user, matched["id"]):
            raise PermissionError("Server này đã có owner trong Kei; không thay kết nối của họ.")
        p = (
            copy.deepcopy(matched)
            if matched
            else {
                "id": (
                    re.sub(r"[^a-z0-9-]", "-", str(row["name"]).casefold()).strip("-")[:30]
                    or "server"
                )
                + "-"
                + str(row["uuid"])[:8],
                "name": str(row["name"]),
                "uuid": row["uuid"],
                "owners": [user],
                "connectors": {},
            }
        )
        if guild:
            p["guilds"] = list(dict.fromkeys(list(map(str, p.get("guilds", []))) + [str(guild)]))
        secrets = Secrets(self.cfg.get("secrets_file", "data/secrets.json"))
        ref = secrets.put("panel-" + uid(), candidate["token"])
        p.setdefault("connectors", {})["panel"] = {
            "url": candidate["url"],
            "token": ref,
            "server": row["uuid"],
        }
        existing = self.db.one("SELECT owner FROM kei_registered_servers WHERE id=?", (p["id"],))
        registry_owner = existing["owner"] if existing else str((p.get("owners") or [user])[0])
        self.db.execute(
            "INSERT OR REPLACE INTO kei_registered_servers VALUES (?,?,?,?)",
            (p["id"], dumps(p), registry_owner, time.time()),
        )
        self.access.record(p["id"], user, user, "connect", "copilot")
        self.db.execute(
            "INSERT OR REPLACE INTO kei_grants VALUES (?,?,?,?)", (user, p["id"], "copilot", user)
        )
        self.pending_connections.pop(str(connection), None)
        self.engine.refresh_servers()
        return {
            "id": p["id"],
            "name": p["name"],
            "connected": True,
            "capabilities": self.engine.tools[p["id"]].capabilities(),
        }

    async def connection_test(self, user, server):
        if server not in self.access.visible(user):
            raise PermissionError("Bạn chưa được xem server này.")
        tool = self.engine.tools[server]
        if tool.cs.get('ssh'):
            from .execution import SHELL_IDENTITY
            from .permissions import policy
            import shlex
            selected=policy(self.db,self.cfg,user,server)['extent']
            def test_ssh():
                client=tool.client();client.close() # Authentication is independently verified.
                directory=tool.cs['ssh'].get('volume')
                if not directory:return True
                token=SHELL_IDENTITY.set(selected if selected in ('machine','host_user') else None)
                try:
                    result=tool.shell('test -r '+shlex.quote(directory.rstrip('/\\')+'/server.properties'),timeout=15)
                    return result.get('exit_code')==0
                finally:SHELL_IDENTITY.reset(token)
            folder_ok=await asyncio.to_thread(test_ssh)
            return {'ok':folder_ok,'ssh_authenticated':True,'server':server,'message':'SSH and Minecraft folder verified with your selected access level.' if folder_ok else 'SSH login works, but the Minecraft folder is not readable with your current access level. Check its path, permissions or connect a Panel.','capabilities':tool.capabilities()}
        if tool.cs.get('bridge') and self.engine.bridge and self.engine.bridge.online(server):
            return {'ok':True,'server':server,'message':'Paper bridge is online.','capabilities':tool.capabilities()}
        if tool.local:
            state=tool.local.detect()
            return {'ok':state['root_visible'],'server':server,'message':'Folder access verified; process control is separate.','capabilities':tool.capabilities()}
        if "status" not in tool.capabilities():
            return {
                "ok": False,
                "server": server,
                "message": "Chưa có kết nối đọc trạng thái.",
                "capabilities": tool.capabilities(),
            }
        result = await asyncio.to_thread(tool.execute, "inspect", {"kind": "status"}, "observe")
        # Do not expose connector configuration or exception bodies containing credentials.
        return {
            "ok": bool(result.get("verified", False)),
            "server": server,
            "message": (
                "Đã nhận trạng thái server."
                if result.get("verified")
                else "Có phản hồi nhưng chưa xác minh trạng thái."
            ),
            "capabilities": tool.capabilities(),
        }

    def embed(self, user, scope, page="home"):
        state = self.state(user, scope)
        embed = discord.Embed(color=0xEFA5A5)
        if page == "profile":
            p = self.profile(user, scope)
            rank = p.get("rank", {}).get("label", "Neutral")
            embed.title = "Kei ↔ Bạn · " + rank
            embed.description = (
                p.get("rank", {}).get("reason")
                or "Quan hệ thay đổi theo những cuộc trò chuyện có ý nghĩa."
            )
            if embed.description == "No established rank change yet.":
                embed.description = "Chưa có thay đổi quan hệ đủ rõ để đổi rank."
            dims = p.get("dimensions", {})
            labels = {
                "familiarity": "Quen thuộc",
                "trust": "Tin cậy",
                "warmth": "Ấm áp",
                "playfulness": "Trêu đùa",
                "tension": "Căng thẳng",
                "confidence": "Độ chắc chắn",
            }
            embed.add_field(
                name="Hiện tại",
                value=" · ".join(
                    f"{label}: {float(dims.get(k, 0)):.0%}" for k, label in labels.items()
                )[:1024],
                inline=False,
            )
            frequency = p.get("frequency", {})
            if frequency:
                embed.add_field(
                    name="Tương tác trong 30 ngày",
                    value=str(frequency.get("active_days_30", 0))
                    + " ngày · "
                    + str(frequency.get("meaningful_sessions_30", 0))
                    + " lượt có ý nghĩa",
                    inline=False,
                )
            episodes = p.get("memories", [])[:4]
            episode_labels = {
                "warm_exchange": "Một chuyện đáng nhớ", "nickname": "Chuyện biệt danh",
                "milestone": "Một dấu mốc", "conflict": "Lúc không vui",
                "reconciliation": "Chuyện làm hòa", "commitment": "Điều đã hứa",
                "inside_joke": "Chuyện đùa của hai người",
            }
            embed.add_field(
                name="Chuyện chung",
                value="\n".join(
                    "• " + episode_labels.get(str(r.get("title")), str(r.get("title") or r.get("summary", "")))[:160] for r in episodes
                )
                or "Chưa có episode đã chọn lưu trong cuộc trò chuyện này.",
                inline=False,
            )
            aliases = p.get("aliases", [])
            if aliases:
                embed.add_field(
                    name="Biệt danh",
                    value=", ".join(
                        str(a.get("alias", "")) if isinstance(a, dict) else str(a) for a in aliases
                    )[:1024],
                    inline=False,
                )
            changes = p.get("changes", [])[:3]
            if changes:
                embed.add_field(
                    name="Thay đổi gần đây",
                    value="\n".join(
                        str(r.get("old_label", "")) + " → " + str(r.get("label", ""))
                        for r in changes
                    )[:1024],
                    inline=False,
                )
            embed.set_footer(text="Chỉ bạn thấy. Rank không cấp quyền quản trị server.")
        elif page == "memory":
            embed.title = "Memory của bạn"
            rows = self.db.rows(
                "SELECT kind,content FROM kei_memories WHERE person=? AND scope=? AND active=1 ORDER BY at DESC LIMIT 8",
                (self.person(user), scope),
            )
            from .memory import unpack

            embed.description = (
                "\n".join("• " + unpack(r["content"])["text"][:180] for r in rows)
                or "Chưa có memory đã chọn lưu ở đây."
            )
            embed.set_footer(
                text="Quên dữ liệu cũng xóa phần dẫn xuất; không dựng lại từ summary cũ."
            )
        elif page == "servers":
            embed.title = "Minecraft của bạn"
            embed.description = (
                "\n\n".join(
                    "**"
                    + s["name"]
                    + "** (`"
                    + s["id"]
                    + "`) · "
                    + s["level"]
                    + "\nCó thể dùng: "
                    + ", ".join(s["capabilities"])
                    for s in state["servers"]
                )[:3800]
                or "Chưa được nối server. Bạn vẫn có thể nói chuyện với Kei. Owner có thể kết nối Panel hoặc cấp quyền cho bạn."
            )
            embed.set_footer(
                text="Chỉ hiện khả năng thực có. Có kết nối không có nghĩa plugin đã cài."
            )
        elif page == "admins":
            embed.title = "Ai được làm gì?"
            lines = []
            for s in state["servers"]:
                if not s["manage_access"]:
                    continue
                lines.append("**" + s["name"] + "** (`" + s["id"] + "`)")
                for grant in self.access.entries(user, s["id"])[:12]:
                    lines.append(
                        "• `"
                        + grant["subject"]
                        + "`: "
                        + grant["level"]
                        + (" + admin" if grant["admin"] else "")
                        + "; cấp bởi `"
                        + grant["issuer"]
                        + "`"
                    )
            embed.description = (
                "\n".join(lines)[:3600]
                or "Chỉ owner hoặc admin được ủy quyền mới quản lý quyền server."
            )
            embed.add_field(
                name="Phạm vi",
                value="observe: xem · copilot: thực hiện việc được phép · admin: quản lý cấp quyền của đúng server. Chỉ owner bổ nhiệm admin. Thu hồi ở nút bên dưới.",
                inline=False,
            )
        elif page == "accounts":
            embed.title = "Tài khoản Minecraft"
            embed.description = (
                "\n".join(
                    "• `"
                    + a["account"]
                    + "` · "
                    + a["server"]
                    + (" · đã xác thực" if a["verified"] else " · chưa xác thực")
                    for a in state["linked_accounts"]
                )
                or "Chưa link. Tạo mã rồi nhập `/kei link MÃ` trong Minecraft sau khi login. Mã không cấp thêm quyền server."
            )
        elif page == "diagnostics":
            embed.title = "Kết nối & chẩn đoán"
            dashboard = self.dashboard
            embed.description = (
                (
                    "Web: "
                    + (
                        "đã bật đăng nhập Discord"
                        if dashboard and dashboard.auth_ready
                        else "đăng nhập Discord chưa sẵn sàng"
                    )
                )
                + "\n"
                + (state["web_url"] or "Chưa đặt Web URL.")
            )
            if str(user) == str(self.cfg["owner_id"]):
                callback = (
                    self.cfg.get("web", {}).get("redirect_uri")
                    or str(self.cfg.get("web", {}).get("public_url", "")).rstrip("/")
                    + "/oauth/callback"
                )
                embed.add_field(
                    name="Bật Web login",
                    value="Discord Developer Portal → ứng dụng của bot → OAuth2 → Redirects: thêm đúng `"
                    + callback
                    + "`. Sau đó dùng nút bên dưới để nhập Client Secret riêng tư.",
                    inline=False,
                )
            for s in state["servers"][:8]:
                embed.add_field(
                    name=s["name"],
                    value=", ".join(s["capabilities"])[:1024] or "Chưa có kết nối.",
                    inline=False,
                )
            embed.set_footer(
                text="Không hiện key hay cấu hình SSH. Danh sách capability không thay cho nghiệm thu plugin trên server."
            )
        else:
            pref = state["preferences"]
            embed.title = "Kei · Thiết lập của bạn"
            embed.description = "Chat với Kei, nhớ chuyện đáng nhớ, và nhờ quản lý Minecraft khi bạn có quyền. Chọn một mục bên dưới; mọi thiết lập ở đây chỉ hiện riêng cho bạn."
            embed.add_field(name="Tính cách / Personality", value=state["persona"], inline=True)
            embed.add_field(name="Tiến độ công việc", value=state["debug"], inline=True)
            embed.add_field(
                name="Chủ động nhắn DM",
                value="Bật" if pref.get("dm_opt_in") else "Tắt",
                inline=True,
            )
            embed.add_field(
                name="Quyền riêng tư",
                value=(
                    "Chỉ ngữ cảnh hiện tại"
                    if pref.get("sharing") == "strict"
                    else "Gợi nhắc kín đáo; không quote DM ra public"
                ),
                inline=False,
            )
            embed.add_field(
                name="Múi giờ", value=str(pref.get("timezone") or self.cfg["timezone"]), inline=True
            )
            embed.add_field(
                name="Minecraft",
                value=str(len(state["servers"])) + " server có quyền truy cập",
                inline=True,
            )
            if page == "participation":
                embed.add_field(
                    name="Tham gia trò chuyện",
                    value=(
                        "Kei đang để bạn yên"
                        if pref.get("muted")
                        else "Có thể trả lời khi được gọi hoặc cuộc trò chuyện phù hợp. Public ambient mặc định tắt."
                    ),
                    inline=False,
                )
            if state["web_url"]:
                embed.add_field(name="Web", value=state["web_url"], inline=False)
        return embed

    def register(self):
        self.bot.tree.remove_command("setup")
        self.bot.tree.error(self.command_error)

        @app_commands.command(
            name="setup",
            description="Bắt đầu: thiết lập riêng tư, link tài khoản và kết nối Minecraft",
        )
        async def setup(interaction: discord.Interaction, code: str = ""):
            if code:
                try:
                    self.claim(interaction.user.id, code)
                except (ValueError, PermissionError) as exc:
                    await interaction.response.send_message(str(exc), ephemeral=True)
                    return
            await self.home(interaction, setup=True)

        @app_commands.command(
            name="settings", description="Tính cách, memory, quyền riêng tư và Minecraft của bạn"
        )
        async def settings(interaction: discord.Interaction):
            await self.home(interaction)

        @app_commands.command(
            name="tasks", description="Xem, tạo hoặc tạm dừng lịch hẹn của riêng bạn"
        )
        async def tasks(interaction: discord.Interaction):
            await interaction.response.defer(ephemeral=True, thinking=True)
            user = str(interaction.user.id)
            scope = (
                "dm:" + user
                if not interaction.guild_id
                else f"guild:{interaction.guild_id}:{interaction.channel_id}"
            )
            await interaction.followup.send(
                embed=tasks_embed(self, user),
                view=TasksView(self, user, scope, str(interaction.channel_id)),
                ephemeral=True,
                allowed_mentions=discord.AllowedMentions.none(),
            )

        self.bot.tree.add_command(setup)
        self.bot.tree.add_command(settings)
        self.bot.tree.add_command(tasks)

    async def home(self, interaction, setup=False):
        # Acknowledge before loading identity/profile/server data. An unavailable
        # backend should result in a private error, not an expired interaction.
        await interaction.response.defer(ephemeral=True, thinking=True)
        user = str(interaction.user.id)
        scope = (
            "dm:" + user
            if not interaction.guild_id
            else f"guild:{interaction.guild_id}:{interaction.channel_id}"
        )
        view = SetupView(self, user, scope) if setup else SettingsView(self, user, scope)
        text = (
            "Ba bước là đủ: chọn cách nói chuyện → link Minecraft nếu muốn → chọn hoặc nối server. Không cần có server để chat."
            if setup
            else None
        )
        await interaction.followup.send(
            text,
            embed=view.intro() if setup else self.embed(user, scope),
            view=view,
            ephemeral=True,
            allowed_mentions=discord.AllowedMentions.none(),
        )

    async def command_error(self, interaction, error):
        original = getattr(error, "original", error)
        command = getattr(getattr(interaction, "command", None), "qualified_name", "unknown")
        LOG.warning("COMMAND_FAILED command=%s type=%s", command, type(original).__name__)
        text = "Kei chưa mở được mục này. Thử lại bằng /settings; nếu vẫn lỗi, báo operator kiểm tra log nhé."
        try:
            if interaction.response.is_done():
                await interaction.followup.send(text, ephemeral=True)
            else:
                await interaction.response.send_message(text, ephemeral=True)
        except discord.HTTPException as exc:
            LOG.warning("COMMAND_ERROR_REPLY_FAILED type=%s", type(exc).__name__)

    async def start(self):
        from .dashboard import Dashboard

        self.dashboard = Dashboard(self)
        await self.dashboard.start()

    async def close(self):
        if self.dashboard:
            await self.dashboard.close()
        self.pending_connections.clear()


class SettingsView(discord.ui.View):
    def __init__(self, ux, user, scope, page="home"):
        super().__init__(timeout=600)
        self.ux, self.user, self.scope = ux, str(user), scope
        section = discord.ui.Select(
            placeholder="Bạn muốn chỉnh gì?",
            options=[
                discord.SelectOption(label=label, value=value, default=value == page)
                for value, label in (
                    ("home", "Tổng quan"),
                    ("persona", "Tính cách & tiến độ"),
                    ("participation", "Tham gia & thông báo"),
                    ("privacy", "Quyền riêng tư"),
                    ("memory", "Những chuyện đã nhớ"),
                    ("profile", "Quan hệ với Kei"),
                    ("accounts", "Tài khoản Minecraft"),
                    ("servers", "Server & kiểm tra kết nối"),
                    ("admins", "Cấp / thu hồi quyền"),
                    ("tasks", "Lịch hẹn & công việc định kỳ"),
                    ("diagnostics", "Kết nối & chẩn đoán"),
                )
            ],
        )

        async def choose(interaction):
            await self.show(interaction, section.values[0])

        section.callback = choose
        self.add_item(section)
        if page == 'home':
            for target,label in (('persona','Cách nói chuyện'),('profile','Chuyện hai người'),('servers','Minecraft'),('admins','Người có quyền'),('tasks','Lịch hẹn')):
                async def open_page(interaction, target=target):await self.show(interaction,target)
                self.button(label,open_page)
            self.web_button()
        else:
            async def back(interaction):await self.show(interaction,'home')
            self.button('← Các mục khác',back)
        if page == "persona":
            self.choice(
                "Cách nói chuyện",
                "persona",
                [("auto", "Linh hoạt"), ("soft", "Dịu hơn"), ("spicy", "Đậm vị")],
            )
            self.choice(
                "Tiến độ công việc",
                "debug",
                [("off", "Ẩn"), ("minimal", "Chỉ checklist"), ("advanced", "Checklist + lệnh/log")],
            )
            self.button('Lời dặn riêng',lambda i:i.response.send_modal(InstructionsModal(ux,user)))
        elif page == "participation":
            self.choice("Chủ động nhắn DM", "dm_opt_in", [(True, "Cho phép"), (False, "Tắt")])
            self.choice(
                "Cho Kei trả lời bạn", "muted", [(False, "Bình thường"), (True, "Để mình yên")]
            )
            self.choice("Chuyển biến quan hệ ↑ / ↓", "rank_notifications", [(True, "Hiện dòng nhỏ"), (False, "Tắt")])
            self.button("Múi giờ", lambda i: i.response.send_modal(TimezoneModal(ux, user)))

        elif page == "privacy":
            # Connection state grows in conversation; it is not a settings game.
            self.choice(
                "Dùng memory giữa các ngữ cảnh",
                "sharing",
                [("strict", "Chỉ nơi đã nói"), ("discreet", "Gợi nhắc kín đáo")],
            )
        elif page == "memory":
            self.button(
                "Quên cuộc trò chuyện này", lambda i: self.confirm_forget(i, False), danger=True
            )
            self.button(
                "Quên toàn bộ dữ liệu của mình", lambda i: self.confirm_forget(i, True), danger=True
            )
        elif page == "accounts":
            self.button("Tạo mã link Minecraft", self.link)
            self.button("Gỡ các link Minecraft", self.unlink, danger=True)
        elif page == "servers":
            servers = ux.state(user, scope)["servers"]
            if servers:
                self.choice(
                    "Server mặc định cho DM",
                    "default_server",
                    [(s["id"], s["name"]) for s in servers[:25]],
                )
                self.button("Kiểm tra server mặc định", self.test)
            if ux.state(user)["can_connect"]:
                self.button(
                    "Kết nối Panel", lambda i: i.response.send_modal(ConnectModal(ux, user))
                )
        elif page == "admins" and any(s["manage_access"] for s in ux.state(user, scope)["servers"]):
            self.button("Cấp hoặc thu hồi", lambda i: i.response.send_modal(AccessModal(ux, user)))
            self.web_button()
        elif page == "diagnostics" and str(user) == str(ux.cfg["owner_id"]):
            self.button("Bật đăng nhập Web", self.oauth)

    async def interaction_check(self, interaction):
        if str(interaction.user.id) == self.user:
            return True
        await interaction.response.send_message(
            "Thiết lập này của người khác. Mở /settings của bạn nhé.", ephemeral=True
        )
        return False

    def button(self, label, callback, danger=False):
        button = discord.ui.Button(
            label=label,
            style=discord.ButtonStyle.danger if danger else discord.ButtonStyle.secondary,
        )
        button.callback = callback
        self.add_item(button)

    def web_button(self):
        url=self.ux.cfg.get('web',{}).get('public_url','')
        if url.startswith('https://'):
            self.add_item(discord.ui.Button(label='Mở trang thiết lập',url=url))

    def choice(self, placeholder, key, options):
        choice = discord.ui.Select(
            placeholder=placeholder,
            options=[
                discord.SelectOption(label=str(label)[:100], value=str(index))
                for index, (value, label) in enumerate(options)
            ],
        )

        async def changed(interaction):
            try:
                selected = int(choice.values[0])
                if not 0 <= selected < len(options):
                    raise ValueError("Lựa chọn đã hết hiệu lực.")
                self.ux.update(self.user, {key: options[selected][0]})
                await interaction.response.edit_message(
                    content="Đã lưu.",
                    embed=self.ux.embed(self.user, self.scope),
                    allowed_mentions=discord.AllowedMentions.none(),
                )
            except (ValueError, PermissionError) as exc:
                await interaction.response.send_message(str(exc), ephemeral=True)

        choice.callback = changed
        self.add_item(choice)

    async def oauth(self, interaction):
        if str(interaction.user.id) != self.user or self.user != str(self.ux.cfg["owner_id"]):
            await interaction.response.send_message(
                "Chỉ operator của bot được cấu hình Web login.", ephemeral=True
            )
            return
        await interaction.response.send_modal(OAuthSecretModal(self.ux, self.user))

    async def show(self, interaction, page):
        if page == "tasks":
            await interaction.response.edit_message(
                content=None,
                embed=tasks_embed(self.ux, self.user),
                view=TasksView(self.ux, self.user, self.scope, str(interaction.channel_id)),
                allowed_mentions=discord.AllowedMentions.none(),
            )
            return
        await interaction.response.edit_message(
            content=None,
            embed=self.ux.embed(self.user, self.scope, page),
            view=SettingsView(self.ux, self.user, self.scope, page),
            allowed_mentions=discord.AllowedMentions.none(),
        )

    async def link(self, interaction):
        code = self.ux.engine.identity.issue(self.user)
        await interaction.response.send_message(
            "Trong Minecraft, login rồi nhập `/kei link "
            + code
            + "`. Mã riêng của bạn, một lần, hết hạn sau 10 phút. Cần plugin Kei đang kết nối; chưa có plugin thì tải/cài theo hướng dẫn của operator.",
            ephemeral=True,
        )

    async def ambient(self, interaction):
        if not interaction.guild_id or not (
            interaction.permissions.manage_guild
            or str(interaction.user.id) == str(self.ux.cfg["owner_id"])
        ):
            await interaction.response.send_message(
                "Cần quyền quản lý guild Discord để đổi mức tham gia public.", ephemeral=True
            )
            return
        view = discord.ui.View(timeout=180)
        select = discord.ui.Select(
            placeholder="Mức tham gia public của Kei",
            options=[
                discord.SelectOption(label="Chỉ khi được gọi (mặc định)", value="off"),
                discord.SelectOption(label="Tự tham gia ở kênh hiện tại", value="whitelist"),
                discord.SelectOption(label="Tự tham gia các kênh được phép xem", value="free"),
            ],
        )

        async def selected(event):
            try:
                if str(event.user.id) != self.user or event.guild_id != interaction.guild_id:
                    raise PermissionError("Phiên này không thuộc bạn.")
                self.ux.set_ambient(
                    self.user,
                    event.guild_id,
                    select.values[0],
                    event.channel_id,
                    event.permissions.manage_guild,
                )
                await event.response.edit_message(
                    content="Đã lưu mức tham gia public: "
                    + select.values[0]
                    + ". Gọi tên/tag/reply vẫn dùng được khi off.",
                    view=None,
                )
            except (ValueError, PermissionError) as exc:
                await event.response.send_message(str(exc), ephemeral=True)

        select.callback = selected
        view.add_item(select)
        await interaction.response.send_message(
            "Thay đổi áp dụng cho guild này; mặc định Kei chỉ tham gia khi được gọi.",
            view=view,
            ephemeral=True,
        )

    async def unlink(self, interaction):
        count = self.ux.engine.identity.unlink(self.user)
        await interaction.response.send_message(
            f"Đã gỡ {count} link Minecraft. Quyền Discord được giữ theo phân công của owner.",
            ephemeral=True,
        )

    async def test(self, interaction):
        state = self.ux.state(self.user)
        server = state["default_server"] or (
            state["servers"][0]["id"] if len(state["servers"]) == 1 else None
        )
        if not server:
            await interaction.response.send_message(
                "Chọn server mặc định trước nhé; không tự đoán khi có nhiều server.", ephemeral=True
            )
            return
        await interaction.response.defer(ephemeral=True, thinking=True)
        try:
            result = await self.ux.connection_test(self.user, server)
            text = result["message"] + "\nCó thể dùng: " + ", ".join(result["capabilities"])
        except Exception as exc:
            text = (
                "Chưa kiểm tra được kết nối ("
                + type(exc).__name__
                + "). Xem diagnostics local; chưa xác nhận server hoạt động."
            )
        await interaction.followup.send(text, ephemeral=True)

    async def confirm_forget(self, interaction, all_scopes):
        view = discord.ui.View(timeout=60)
        button = discord.ui.Button(label="Xác nhận quên", style=discord.ButtonStyle.danger)

        async def confirmed(event):
            if str(event.user.id) != self.user:
                await event.response.send_message("Đây không phải dữ liệu của bạn.", ephemeral=True)
                return
            self.ux.engine.memory.forget(self.user, None if all_scopes else self.scope)
            await event.response.edit_message(
                content="Đã quên dữ liệu và phần dẫn xuất liên quan.", view=None
            )

        button.callback = confirmed
        view.add_item(button)
        await interaction.response.send_message(
            (
                "Quên toàn bộ dữ liệu của bạn ở mọi ngữ cảnh?"
                if all_scopes
                else "Quên dữ liệu của bạn ở cuộc trò chuyện hiện tại?"
            ),
            view=view,
            ephemeral=True,
        )


class SetupView(SettingsView):
    def __init__(self,ux,user,scope,step=0):
        self.step=step
        super().__init__(ux,user,scope,('persona','accounts','servers')[step])
        if step:
            async def previous(i):await self.move(i,self.step-1)
            self.button('← Bước trước',previous)
        async def advance(i):
            if self.step<2:await self.move(i,self.step+1)
            else:await self.show(i,'home')
        self.button('Tiếp theo →' if step<2 else 'Xong rồi',advance)
        self.web_button()

    def intro(self):
        titles=('1/3 · Nói chuyện cho hợp ý','2/3 · Liên kết Minecraft nếu bạn chơi','3/3 · Chọn server nếu cần')
        copies=('Chọn cách Kei trả lời và hiện tiến độ ở bên dưới. Bạn cũng có thể nói thẳng “gọi mình là anh” hoặc “trả lời ngắn thôi” trong chat. Giữ mặc định cũng được.',
                'Tạo mã rồi nhập lệnh đó trong Minecraft sau khi đăng nhập. Server cần plugin Kei. Chưa chơi hoặc chưa cài plugin? Bấm Tiếp theo để bỏ qua.',
                'Chọn server đã được cấp quyền hoặc kết nối Panel nếu bạn là chủ. Chưa có server vẫn chat được bình thường. Xong rồi, thử nhắn “Kei ơi” nhé.')
        return discord.Embed(title=titles[self.step],description=copies[self.step],color=0xEFA5A5)

    async def move(self,interaction,step):
        view=SetupView(self.ux,self.user,self.scope,step)
        await interaction.response.edit_message(content=None,embed=view.intro(),view=view,allowed_mentions=discord.AllowedMentions.none())


class InstructionsModal(discord.ui.Modal,title='Lời dặn riêng cho Kei'):
    def __init__(self,ux,user):
        super().__init__();self.ux,self.user=ux,str(user)
        self.text=discord.ui.TextInput(label='Muốn Kei lưu ý điều gì khi nói chuyện?',style=discord.TextStyle.paragraph,required=False,max_length=2000,default=personal_instructions(ux.db,ux.person(user)),placeholder='Ví dụ: gọi mình là anh; trả lời ngắn khi mình đi học.')
        self.add_item(self.text)
        from .social_runtime import names
        self.names=discord.ui.TextInput(label='Tên riêng bạn sẽ gọi Kei · cách nhau dấu phẩy',required=False,max_length=330,default=', '.join(names(ux.db,ux.person(user))),placeholder='keys, cây, kei-kei')
        self.add_item(self.names)

    async def on_submit(self,interaction):
        if str(interaction.user.id)!=self.user:
            await interaction.response.send_message('Lời dặn này không thuộc tài khoản của bạn.',ephemeral=True);return
        self.ux.update(self.user,{'custom_instructions':str(self.text),'call_names':[s.strip() for s in str(self.names).split(',') if s.strip()]})
        await interaction.response.send_message('Đã lưu lời dặn riêng. Để trống rồi lưu nếu muốn xóa; lời dặn không thay quyền server hoặc tính cách gốc.',ephemeral=True)


class OAuthSecretModal(discord.ui.Modal, title="Bật Discord login cho Web"):
    client_id = discord.ui.TextInput(label="Discord application / client ID", max_length=24)
    client_secret = discord.ui.TextInput(
        label="Discord OAuth Client Secret (chỉ hiện riêng)", min_length=16, max_length=512
    )

    def __init__(self, ux, user):
        super().__init__()
        self.ux, self.user = ux, str(user)
        self.client_id.default = str(
            ux.cfg.get("web", {}).get("client_id") or getattr(ux.bot, "application_id", "") or ""
        )

    async def on_submit(self, interaction):
        if str(interaction.user.id) != self.user or self.user != str(self.ux.cfg["owner_id"]):
            await interaction.response.send_message(
                "Chỉ operator của bot được cấu hình Web login.", ephemeral=True
            )
            return
        await interaction.response.defer(ephemeral=True, thinking=True)
        try:
            result = await self.ux.activate_web(
                self.user, str(self.client_id), str(self.client_secret)
            )
            text = (
                (
                    "Đã lưu riêng tư và bật lại Web listener. "
                    if result["ready"]
                    else "Đã lưu riêng tư; Web listener chưa sẵn sàng, xem log local. "
                )
                + "Thêm đúng callback `"
                + result["callback"]
                + "` trong Discord Developer Portal → OAuth2 → Redirects, rồi mở "
                + result["url"]
                + " để thử đăng nhập. Bot Discord không cần restart."
            )
        except (ValueError, PermissionError) as exc:
            text = str(exc)
        except Exception as exc:
            text = (
                "Chưa bật được Web login ("
                + type(exc).__name__
                + "). Không xác nhận đăng nhập thành công; kiểm tra cấu hình local."
            )
        # Never return entered credentials, OAuth responses or exception bodies.
        await interaction.followup.send(
            text, ephemeral=True, allowed_mentions=discord.AllowedMentions.none()
        )


class TimezoneModal(discord.ui.Modal, title="Múi giờ của bạn"):
    timezone = discord.ui.TextInput(label="Timezone", default="Asia/Ho_Chi_Minh", max_length=80)

    def __init__(self, ux, user):
        super().__init__()
        self.ux, self.user = ux, str(user)

    async def on_submit(self, interaction):
        try:
            if str(interaction.user.id) != self.user:
                raise PermissionError("Thiết lập này không thuộc bạn.")
            self.ux.update(self.user, {"timezone": str(self.timezone).strip()})
            text = "Đã lưu múi giờ. Giờ yên lặng và nhắc việc sẽ theo múi giờ này."
        except Exception:
            text = "Múi giờ chưa hợp lệ. Ví dụ: Asia/Ho_Chi_Minh."
        await interaction.response.send_message(text, ephemeral=True)


class AccessModal(discord.ui.Modal, title="Quyền của đúng một server"):
    server = discord.ui.TextInput(label="Server ID (trong danh sách vừa xem)", max_length=100)
    subject = discord.ui.TextInput(label="Discord user ID", min_length=1, max_length=24)
    action = discord.ui.TextInput(
        label="grant / revoke / admin / unadmin", default="grant", max_length=20
    )
    level = discord.ui.TextInput(label="chat / observe / copilot", default="observe", max_length=20)

    def __init__(self, ux, user):
        super().__init__()
        self.ux, self.user = ux, str(user)

    async def on_submit(self, interaction):
        try:
            if str(interaction.user.id) != self.user:
                raise PermissionError("Phiên này không thuộc bạn.")
            subject, action, sid, level = (
                str(self.subject).strip(),
                str(self.action).strip(),
                str(self.server).strip(),
                str(self.level).strip(),
            )
            if not subject.isdigit():
                raise ValueError("Nhập Discord user ID dạng số.")
            if action == "grant":
                self.ux.access.grant(self.user, subject, sid, level)
            elif action == "revoke":
                self.ux.access.revoke(self.user, subject, sid)
            elif action in ("admin", "unadmin"):
                self.ux.access.delegate(self.user, subject, sid, action == "admin", level)
            else:
                raise ValueError("Chọn grant, revoke, admin hoặc unadmin.")
            text = (
                "Đã lưu: "
                + action
                + " · "
                + sid
                + " · user "
                + subject
                + ". Có ghi lại người cấp và phạm vi."
            )
        except (PermissionError, ValueError) as exc:
            text = str(exc)
        await interaction.response.send_message(
            text, ephemeral=True, allowed_mentions=discord.AllowedMentions.none()
        )


class ConnectModal(discord.ui.Modal, title="Kết nối Panel riêng tư"):
    url = discord.ui.TextInput(
        label="Panel URL", placeholder="https://panel.example.com", max_length=300
    )
    token = discord.ui.TextInput(
        label="Client API key (Account → API Credentials)", min_length=10, max_length=512
    )

    def __init__(self, ux, user):
        super().__init__()
        self.ux, self.user = ux, str(user)

    async def on_submit(self, interaction):
        await interaction.response.defer(ephemeral=True, thinking=True)
        try:
            if str(interaction.user.id) != self.user:
                raise PermissionError("Phiên này không thuộc bạn.")
            result = await self.ux.connection_preview(self.user, str(self.url), str(self.token))
            view = discord.ui.View(timeout=600)
            select = discord.ui.Select(
                placeholder="Chọn server thật từ Panel",
                options=[
                    discord.SelectOption(label=r["name"][:100], value=str(r["index"]))
                    for r in result["servers"][:25]
                ],
            )

            async def chosen(event):
                if str(event.user.id) != self.user:
                    await event.response.send_message("Phiên này không thuộc bạn.", ephemeral=True)
                    return
                try:
                    connected = self.ux.connection_commit(
                        self.user, result["connection"], int(select.values[0])
                    )
                    await event.response.edit_message(
                        content="Đã kết nối **"
                        + connected["name"]
                        + "**. Chọn server trong /settings để kiểm tra trạng thái.",
                        view=None,
                        allowed_mentions=discord.AllowedMentions.none(),
                    )
                except (PermissionError, ValueError) as exc:
                    await event.response.send_message(str(exc), ephemeral=True)

            select.callback = chosen
            view.add_item(select)
            await interaction.followup.send(
                "Chọn một server. Key được giữ ở phía bot; không đưa vào câu trả lời hay model.",
                view=view,
                ephemeral=True,
            )
        except (PermissionError, ValueError) as exc:
            await interaction.followup.send(str(exc), ephemeral=True)
        except Exception as exc:
            await interaction.followup.send(
                "Chưa kết nối được Panel ("
                + type(exc).__name__
                + "). Kiểm tra URL, Client API key và quyền của account.",
                ephemeral=True,
            )


def tasks_embed(ux, user, task=None):
    embed = discord.Embed(title="Lịch hẹn của bạn", color=0xEFA5A5)
    scheduler = getattr(ux.engine, "scheduler", None)
    if scheduler is None:
        embed.description = "Bộ lịch chưa sẵn sàng. Những công việc đang chạy vẫn được giữ nguyên."
        return embed
    rows = [task] if task else scheduler.list(str(user))[:15]
    states = {
        "pending": "Chờ bạn xác nhận 🕒",
        "active": "Đã hẹn",
        "paused": "Tạm dừng",
        "cancelled": "Đã hủy",
        "completed": "Đã xong",
        "done": "Đã xong",
    }
    embed.description = (
        "\n\n".join(
            "**"
            + str(r.get("goal", "Lịch hẹn"))[:180]
            + "**\n"
            + states.get(r.get("status"), str(r.get("status", "")))
            + (" · <t:" + str(int(r["next_run"])) + ":f>" if r.get("next_run") else "")
            + (" · " + str(r["server"]) if r.get("server") else "")
            for r in rows
        )[:3800]
        or "Chưa có lịch hẹn. Tạo một lời nhắc hoặc việc kiểm tra server nhé."
    )
    embed.set_footer(
        text="Lịch mới hoặc sửa lịch cần bạn bấm 🕒 xác nhận. Mỗi người chỉ thấy lịch của mình."
    )
    return embed


class TasksView(discord.ui.View):
    def __init__(self, ux, user, scope, channel, task=None, confirmation_source=None):
        super().__init__(timeout=600)
        self.ux, self.user, self.scope, self.channel = ux, str(user), scope, str(channel)
        self.task, self.confirmation_source = task, confirmation_source
        scheduler = getattr(ux.engine, "scheduler", None)
        if not scheduler:
            return
        create = discord.ui.Button(label="Tạo lịch hẹn", style=discord.ButtonStyle.secondary)

        async def create_clicked(interaction):
            await interaction.response.send_modal(TaskModal(ux, user, scope, channel))

        create.callback = create_clicked
        self.add_item(create)
        rows = scheduler.list(self.user)
        if rows:
            select = discord.ui.Select(
                placeholder="Chọn một lịch hẹn",
                options=[
                    discord.SelectOption(
                        label=str(r.get("goal", r["id"]))[:100], value=str(r["id"])
                    )
                    for r in rows[:25]
                ],
            )

            async def selected(interaction):
                try:
                    selected_task = scheduler.get(self.user, select.values[0])
                    await interaction.response.edit_message(
                        embed=tasks_embed(ux, self.user, selected_task),
                        view=TasksView(ux, self.user, scope, channel, selected_task),
                        allowed_mentions=discord.AllowedMentions.none(),
                    )
                except (ValueError, PermissionError) as exc:
                    await interaction.response.send_message(str(exc), ephemeral=True)

            select.callback = selected
            self.add_item(select)
        if task:
            for action, label in (
                ("pause", "Tạm dừng"),
                ("resume", "Tiếp tục"),
                ("cancel", "Hủy lịch"),
            ):
                button = discord.ui.Button(
                    label=label,
                    style=(
                        discord.ButtonStyle.danger
                        if action == "cancel"
                        else discord.ButtonStyle.secondary
                    ),
                )

                async def act(interaction, action=action):
                    try:
                        result = getattr(scheduler, action)(self.user, task["id"])
                        await self.ack(interaction, result)
                    except (ValueError, PermissionError) as exc:
                        await interaction.response.send_message(str(exc), ephemeral=True)

                button.callback = act
                self.add_item(button)
            edit = discord.ui.Button(label="Sửa lịch", style=discord.ButtonStyle.secondary)

            async def edited(interaction):
                await interaction.response.send_modal(TaskModal(ux, user, scope, channel, task))

            edit.callback = edited
            self.add_item(edit)
            if task.get("status") == "pending":
                confirm = discord.ui.Button(
                    label="🕒 Xác nhận lịch", style=discord.ButtonStyle.primary
                )

                async def confirmed(interaction):
                    try:
                        source = self.confirmation_source or str(interaction.message.id)
                        # The UI click itself supplies a new, visible owner-bound acknowledgement.
                        scheduler.bind_confirmation(self.user, task["id"], source)
                        result = scheduler.confirm(self.user, task["id"], source)
                        await interaction.response.edit_message(
                            content="Đã xác nhận lịch.",
                            embed=tasks_embed(ux, self.user, result),
                            view=TasksView(ux, self.user, scope, channel, result),
                            allowed_mentions=discord.AllowedMentions.none(),
                        )
                    except (ValueError, PermissionError) as exc:
                        await interaction.response.send_message(str(exc), ephemeral=True)

                confirm.callback = confirmed
                self.add_item(confirm)

    async def interaction_check(self, interaction):
        if str(interaction.user.id) == self.user:
            return True
        await interaction.response.send_message(
            "Lịch này của người khác. Mở /tasks của bạn nhé.", ephemeral=True
        )
        return False

    async def ack(self, interaction, result):
        view = TasksView(self.ux, self.user, self.scope, self.channel, result)
        await interaction.response.edit_message(
            content=None,
            embed=tasks_embed(self.ux, self.user, result),
            view=view,
            allowed_mentions=discord.AllowedMentions.none(),
        )
        if result.get("status") == "pending":
            message = await interaction.original_response()
            self.ux.engine.scheduler.bind_confirmation(self.user, result["id"], str(message.id))
            view.confirmation_source = str(message.id)


class TaskModal(discord.ui.Modal, title="Hẹn Kei làm gì?"):
    goal = discord.ui.TextInput(
        label="Việc hoặc lời nhắc", style=discord.TextStyle.paragraph, max_length=1000
    )
    when = discord.ui.TextInput(
        label="Khi nào? VD: ngày mai 07:00 / mỗi ngày 07:00", max_length=120
    )
    server = discord.ui.TextInput(
        label="Server ID (bỏ trống nếu chỉ nhắc việc)", required=False, max_length=100
    )
    mode = discord.ui.TextInput(
        label="alarm: lời nhắc · observe: xem · change: làm", default="alarm", max_length=10
    )
    timezone = discord.ui.TextInput(label="Múi giờ", default="Asia/Ho_Chi_Minh", max_length=80)

    def __init__(self, ux, user, scope, channel, task=None):
        super().__init__()
        self.ux, self.user, self.scope, self.channel = ux, str(user), scope, str(channel)
        self.task = task
        self.timezone.default = (
            ux.engine.memory.preference(ux.person(user)).get("timezone") or ux.cfg["timezone"]
        )
        if task:
            self.goal.default = str(task.get("goal", ""))
            self.server.default = str(task.get("server") or "")
            self.mode.default = "alarm" if task.get("alarm") else str(task.get("mode", "observe"))

    async def on_submit(self, interaction):
        try:
            if str(interaction.user.id) != self.user:
                raise PermissionError("Lịch này không thuộc bạn.")
            scheduler = getattr(self.ux.engine, "scheduler", None)
            if scheduler is None:
                raise ValueError("Bộ lịch chưa sẵn sàng.")
            from .scheduler import parse_schedule_text

            schedule = parse_schedule_text(str(self.when), str(self.timezone).strip())
            mode = str(self.mode).strip()
            if mode not in ("alarm", "observe", "change"):
                raise ValueError("Chọn alarm, observe hoặc change.")
            values = {
                "goal": str(self.goal),
                "schedule": schedule,
                "server": str(self.server).strip() or None,
                "mode": "observe" if mode == "alarm" else mode,
                "alarm": mode == "alarm",
            }
            if self.task:
                result = scheduler.change(self.user, self.task["id"], **values)
            else:
                result = scheduler.propose(self.user, self.scope, self.channel, **values)
            view = TasksView(self.ux, self.user, self.scope, self.channel, result)
            await interaction.response.send_message(
                "-# Bấm 🕒 để xác nhận lịch này; Kei chưa bật chạy trước khi bạn xác nhận.",
                embed=tasks_embed(self.ux, self.user, result),
                view=view,
                ephemeral=True,
                allowed_mentions=discord.AllowedMentions.none(),
            )
            ack = await interaction.original_response()
            scheduler.bind_confirmation(self.user, result["id"], str(ack.id))
            view.confirmation_source = str(ack.id)
        except (PermissionError, ValueError) as exc:
            await interaction.response.send_message(str(exc), ephemeral=True)
