"""Optional aiohttp dashboard. OAuth credentials and session authority stay server-side."""

from __future__ import annotations

import asyncio
import base64
import hashlib
import json
import logging
import secrets
import time
from urllib.parse import urlencode, urlsplit

import aiohttp
from aiohttp import web

from .config import Secrets
from .web_ui import branding, render_home

LOG = logging.getLogger("kei.web")
DISCORD = "https://discord.com/api/v10"


def web_error(error,path=''):
    text=str(error).strip()
    if text and all(ord(c)<128 for c in text):return text
    if isinstance(error,PermissionError):
        if path.startswith('/api/access'):return 'Permission denied. Server owners manage admins, co-owners and run modes; host access also needs an operator grant.'
        return 'You do not have permission for this server or operation. Sign in again if your access recently changed.'
    if path.startswith('/api/tasks'):return 'Check the task, future date/time, timezone and selected server. A changed schedule needs confirmation again.'
    if path.startswith('/api/connect'):return 'Connection failed. Check your Panel URL, Client API key and access to the selected server.'
    if path.startswith('/api/settings'):return 'Check your settings. Use a valid timezone such as Asia/Ho_Chi_Minh and an assigned default server.'
    if path.startswith('/oauth'):return 'This sign-in request expired or is invalid. Please sign in with Discord again.'
    if path.startswith('/api/access'):return 'Check the Discord user ID, selected role, scope and Custom config. Unsupported rules are rejected.'
    return 'The request could not be completed. Check your input or sign in again.'


class OAuthClient:
    def __init__(self, client_id, client_secret, redirect_uri):
        self.client_id, self.client_secret, self.redirect_uri = (
            client_id,
            client_secret,
            redirect_uri,
        )
        self.http = None

    async def client(self):
        if self.http is None:
            self.http = aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=20))
        return self.http

    async def identity(self, token):
        http = await self.client()
        headers = {"Authorization": "Bearer " + token}
        async with http.get(DISCORD + "/users/@me", headers=headers) as response:
            if response.status != 200:
                raise PermissionError("Discord session đã hết hạn; đăng nhập lại nhé.")
            user = await response.json()
        async with http.get(DISCORD + "/users/@me/guilds", headers=headers) as response:
            if response.status != 200:
                raise PermissionError("Không xác minh được quyền Discord; đăng nhập lại nhé.")
            guilds = await response.json()
        if not str(user.get("id", "")).isdigit() or not isinstance(guilds, list):
            raise PermissionError("Discord trả về danh tính chưa hợp lệ.")
        return user, guilds

    async def exchange(self, code, verifier):
        http = await self.client()
        async with http.post(
            DISCORD + "/oauth2/token",
            data={
                "client_id": self.client_id,
                "client_secret": self.client_secret,
                "grant_type": "authorization_code",
                "code": code,
                "redirect_uri": self.redirect_uri,
                "code_verifier": verifier,
            },
        ) as response:
            if response.status != 200:
                raise PermissionError(
                    "Discord chưa xác thực được lượt đăng nhập. Thử lại từ đầu nhé."
                )
            result = await response.json()
        token = result.get("access_token")
        refresh = result.get("refresh_token")
        if not token or not refresh:
            raise PermissionError("Discord không cấp session đăng nhập.")
        user, guilds = await self.identity(token)
        return user, guilds, {
            "access_token": token,
            "refresh_token": refresh,
            "expires_at": time.time() + max(60, int(result.get("expires_in", 3600))),
        }

    async def refresh(self, refresh_token):
        http = await self.client()
        async with http.post(
            DISCORD + "/oauth2/token",
            data={
                "client_id": self.client_id,
                "client_secret": self.client_secret,
                "grant_type": "refresh_token",
                "refresh_token": refresh_token,
            },
        ) as response:
            if response.status != 200:
                raise PermissionError("Discord session expired; sign in again.")
            result = await response.json()
        access = result.get("access_token")
        rotated = result.get("refresh_token") or refresh_token
        if not access:
            raise PermissionError("Discord did not renew the session.")
        return {
            "access_token": access,
            "refresh_token": rotated,
            "expires_at": time.time() + max(60, int(result.get("expires_in", 3600))),
        }

    async def close(self):
        if self.http is not None:
            await self.http.close()


class Dashboard:
    def __init__(self, ux, oauth=None, clock=time.time):
        self.ux, self.cfg, self.clock = ux, ux.cfg.get("web", {}), clock
        self.oauth = oauth
        self.db = ux.db
        self.runner = None
        self.site = None
        self.states = {}
        self.origin = ""
        self.secure = True
        self.status = "disabled"
        self.auth_ready = False
        self.setup_message = "Web login is not ready: the operator must configure Discord OAuth. You can still use /settings in Discord."
        self.branding = None
        self.global_live_cache = (0, [])

    def configure(self):
        url = str(self.cfg.get("public_url", "")).rstrip("/")
        parsed = urlsplit(url)
        redirect = str(self.cfg.get("redirect_uri", url + "/oauth/callback"))
        callback = urlsplit(redirect)
        local = parsed.hostname in ("localhost", "127.0.0.1", "::1")
        if (
            parsed.scheme not in ("http", "https")
            or not parsed.netloc
            or parsed.path not in ("", "/")
            or parsed.query
            or parsed.fragment
            or parsed.username
            or parsed.password
            or (parsed.scheme != "https" and not local)
        ):
            raise ValueError("web.public_url cần HTTPS, hoặc http://127.0.0.1:PORT cho local.")
        if (
            (callback.scheme, callback.netloc, callback.path)
            != (parsed.scheme, parsed.netloc, "/oauth/callback")
            or callback.query
            or callback.fragment
        ):
            raise ValueError("OAuth redirect_uri phải đúng PUBLIC_URL/oauth/callback.")
        client_id = str(
            self.cfg.get("client_id") or getattr(self.ux.bot, "application_id", "") or ""
        )
        secret = Secrets(self.ux.cfg.get("secrets_file", "data/secrets.json")).get(
            self.cfg.get("client_secret_ref")
            or self.cfg.get("client_secret", "env:DISCORD_CLIENT_SECRET")
        )
        self.origin, self.secure = url, parsed.scheme == "https"
        if self.oauth is None and client_id.isdigit() and secret:
            self.oauth = OAuthClient(client_id, secret, redirect)
        self.auth_ready = bool(self.oauth and client_id.isdigit())
        self.branding = branding(self.cfg.get("branding"))
        return client_id, redirect

    def app(self):
        client_id, redirect = self.configure()
        self.client_id, self.redirect_uri = client_id, redirect

        @web.middleware
        async def errors(request, handler):
            try:
                response = await handler(request)
            except (PermissionError, ValueError) as exc:
                response = web.json_response(
                    {"error": web_error(exc,request.path)}, status=403 if isinstance(exc, PermissionError) else 400
                )
            except web.HTTPException as exc:
                response = web.json_response(
                    {"error": ("Sign in with Discord first." if exc.status==401 else web_error(exc.text,request.path))},
                    status=exc.status,
                    headers={k: v for k, v in exc.headers.items() if k.lower() != "content-type"},
                )
            except Exception as exc:
                # Never relay upstream bodies, URL credentials or stack traces to the browser.
                LOG.warning(
                    "DASHBOARD_REQUEST_FAILED path=%s type=%s", request.path, type(exc).__name__
                )
                response = web.json_response(
                    {"error": "The request failed. Please try again or check local diagnostics."}, status=502
                )
            response.headers["Cache-Control"] = "public, max-age=86400" if request.path.startswith('/assets/') and response.status==200 else "no-store"
            response.headers["X-Content-Type-Options"] = "nosniff"
            response.headers["Referrer-Policy"] = "no-referrer"
            response.headers["X-Frame-Options"] = "DENY"
            return response

        app = web.Application(middlewares=[errors], client_max_size=65536)
        app.router.add_get("/", self.home)
        app.router.add_get("/login", self.login)
        app.router.add_get("/oauth/callback", self.callback)
        app.router.add_get("/api/session", self.session_hint)
        app.router.add_get("/api/state", self.state)
        app.router.add_get("/api/global/overview", self.global_overview)
        app.router.add_get("/api/global/occasions",self.global_occasions)
        app.router.add_get("/api/global/relationships", self.global_relationships)
        app.router.add_get("/api/global/settings", self.global_settings)
        app.router.add_post("/api/global/settings", self.update_global_settings)
        app.router.add_get("/api/profile", self.profile)
        app.router.add_get("/api/memories", self.memories)
        app.router.add_get("/api/reports", self.reports)
        app.router.add_post("/api/access/preview", self.access_preview)
        app.router.add_post("/api/settings", self.settings)
        app.router.add_post("/api/link", self.link)
        app.router.add_post("/api/unlink", self.unlink)
        app.router.add_post("/api/forget", self.forget)
        app.router.add_post("/api/access", self.access)
        app.router.add_post("/api/connect/preview", self.connect_preview)
        app.router.add_post("/api/connect/commit", self.connect_commit)
        app.router.add_post("/api/server/test", self.server_test)
        app.router.add_post("/api/connect/service/preview",self.service_preview)
        app.router.add_post("/api/connect/service/commit",self.service_commit)
        app.router.add_get("/api/tasks", self.tasks)
        app.router.add_post("/api/tasks/propose", self.task_propose)
        app.router.add_post("/api/tasks/action", self.task_action)
        app.router.add_post("/logout", self.logout)
        return app

    async def start(self):
        if not self.cfg.get("enabled", False):
            return
        try:
            app = self.app()
            self.runner = web.AppRunner(app, access_log=None)
            await self.runner.setup()
            self.site = web.TCPSite(
                self.runner, self.cfg.get("host", "127.0.0.1"), int(self.cfg.get("port", 8768))
            )
            await self.site.start()
            self.status = "listening" if self.auth_ready else "listening:setup_required"
            LOG.info("DASHBOARD_LISTENING oauth_ready=%s", self.auth_ready)
        except Exception as exc:
            self.status = "unavailable:" + type(exc).__name__
            LOG.warning(
                "Dashboard unavailable (%s); /settings remain available",
                type(exc).__name__,
            )
            if self.runner:
                await self.runner.cleanup()
                self.runner = None

    async def close(self):
        if self.runner:
            await self.runner.cleanup()
        if self.oauth:
            await self.oauth.close()
        self.states.clear()

    def prune(self):
        now = self.clock()
        self.states = {k: v for k, v in self.states.items() if v["expires"] > now}
        while len(self.states) >= 128:
            self.states.pop(next(iter(self.states)))
        expired = self.db.rows("SELECT session_hash,token_ref FROM kei_web_sessions WHERE expires<=?", (now,))
        for row in expired:
            self._drop_session(row["session_hash"], row["token_ref"])

    def _secrets(self):
        return Secrets(self.ux.cfg.get("secrets_file", "data/secrets.json"))

    def _drop_session(self, key, token_ref=None):
        row = self.db.one("SELECT token_ref FROM kei_web_sessions WHERE session_hash=?", (key,))
        self.db.execute("DELETE FROM kei_web_sessions WHERE session_hash=?", (key,))
        token_ref = token_ref or (row or {}).get("token_ref")
        if token_ref and str(token_ref).startswith("secret:"):
            self._secrets().delete(str(token_ref)[7:])

    def _store_session(self, sid, session):
        key = hashlib.sha256(sid.encode()).hexdigest()
        self.db.execute(
            "INSERT OR REPLACE INTO kei_web_sessions VALUES (?,?,?,?,?,?,?,?,?)",
            (key, session["user"], session["name"], session["csrf"], session["token_ref"],
             json.dumps(session["guilds"], separators=(",", ":")), session["expires"],
             session["checked"], session.get("touched", self.clock())),
        )
        return key

    async def login(self, request):
        if not self.auth_ready:
            raise web.HTTPServiceUnavailable(text=self.setup_message)
        self.prune()
        state, binding, verifier = (
            secrets.token_urlsafe(32),
            secrets.token_urlsafe(32),
            secrets.token_urlsafe(48),
        )
        self.states[hashlib.sha256(state.encode()).hexdigest()] = {
            "binding": hashlib.sha256(binding.encode()).hexdigest(),
            "verifier": verifier,
            "expires": self.clock() + 300,
        }
        challenge = (
            base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest())
            .decode()
            .rstrip("=")
        )
        response = web.Response(
            status=302,
            headers={
                "Location": "https://discord.com/oauth2/authorize?"
                + urlencode(
                    {
                        "client_id": self.client_id,
                        "redirect_uri": self.redirect_uri,
                        "response_type": "code",
                        "scope": "identify guilds",
                        "state": state,
                        "code_challenge": challenge,
                        "code_challenge_method": "S256",
                    }
                )
            },
        )
        response.set_cookie(
            "kei_oauth",
            binding,
            max_age=300,
            httponly=True,
            secure=self.secure,
            samesite="Lax",
            path="/",
        )
        return response

    async def callback(self, request):
        if not self.auth_ready:
            raise web.HTTPServiceUnavailable(text=self.setup_message)
        self.prune()
        state, code = request.query.get("state", ""), request.query.get("code", "")
        saved = self.states.pop(hashlib.sha256(state.encode()).hexdigest(), None)
        binding = hashlib.sha256(request.cookies.get("kei_oauth", "").encode()).hexdigest()
        if not saved or not code or not secrets.compare_digest(saved["binding"], binding):
            raise PermissionError("Lượt đăng nhập hết hạn hoặc không hợp lệ; mở /login lại nhé.")
        user, guilds, tokens = await self.oauth.exchange(code, saved["verifier"])
        sid = secrets.token_urlsafe(32)
        token_ref = self._secrets().put("web_session_" + secrets.token_hex(20), json.dumps(tokens))
        self._store_session(sid, {
            "user": str(user["id"]),
            "name": str(user.get("global_name") or user.get("username") or user["id"]),
            "guilds": guilds,
            "token_ref": token_ref,
            "csrf": secrets.token_urlsafe(32),
            "expires": self.clock() + 90 * 86400,
            "checked": self.clock(),
            "touched": self.clock(),
        })
        response = web.Response(status=302, headers={"Location": "/"})
        response.del_cookie("kei_oauth", path="/")
        response.set_cookie(
            "kei_session",
            sid,
            max_age=365 * 86400,
            httponly=True,
            secure=self.secure,
            samesite="Lax",
            path="/",
        )
        return response

    async def session(self, request, write=False):
        if not self.auth_ready:
            raise web.HTTPServiceUnavailable(text=self.setup_message)
        self.prune()
        sid = hashlib.sha256(request.cookies.get("kei_session", "").encode()).hexdigest()
        row = self.db.one("SELECT * FROM kei_web_sessions WHERE session_hash=? AND expires>?", (sid, self.clock()))
        if not row:
            raise web.HTTPUnauthorized(text="Đăng nhập Discord trước nhé.")
        session = {**row, "guilds": json.loads(row["guilds"])}
        if write:
            if request.headers.get("Origin") != self.origin or not secrets.compare_digest(
                session["csrf"], request.headers.get("X-CSRF-Token", "")
            ):
                raise PermissionError("Phiên thao tác chưa hợp lệ. Tải lại trang rồi thử lại.")
            if request.content_type != "application/json":
                raise ValueError("Gửi JSON hợp lệ.")
        # Keep sign-in across app restarts. Refresh the server-side OAuth grant when
        # needed and re-check Discord identity/permissions before privileged writes.
        tokens = json.loads(self._secrets().get(session["token_ref"], "{}"))
        if not tokens.get("access_token") or not tokens.get("refresh_token"):
            self._drop_session(sid, session["token_ref"])
            raise web.HTTPUnauthorized(text="Discord session expired; sign in again.")
        if float(tokens.get("expires_at", 0)) <= self.clock() + 300:
            try:
                tokens = await self.oauth.refresh(tokens["refresh_token"])
            except PermissionError:
                self._drop_session(sid, session["token_ref"])
                raise web.HTTPUnauthorized(text="Discord session expired; sign in again.")
            self._secrets().put(session["token_ref"][7:], json.dumps(tokens))
        if write or self.clock() - session["checked"] > 300:
            user, guilds = await self.oauth.identity(tokens["access_token"])
            if str(user["id"]) != session["user"]:
                self._drop_session(sid, session["token_ref"])
                raise PermissionError("Danh tính Discord đã thay đổi; đăng nhập lại.")
            session.update(guilds=guilds, checked=self.clock())
        if self.clock() - float(session.get("touched", 0)) > 86400:
            session.update(expires=self.clock() + 90 * 86400, touched=self.clock())
        self._store_session(request.cookies.get("kei_session", ""), session)
        return session

    def guilds(self, session):
        connected = {str(g.id) for g in getattr(self.ux.bot, "guilds", [])}
        visible = set(self.ux.access.visible(session["user"]))
        mapped = {str(g) for sid in visible for g in self.ux.engine.servers[sid].get("guilds", [])}
        result = []
        for guild in session["guilds"]:
            gid = str(guild.get("id", ""))
            manage = bool(guild.get("owner")) or bool(int(guild.get("permissions", "0")) & (8 | 32))
            if gid in connected and (manage or gid in mapped):
                result.append(
                    {"id": gid, "name": str(guild.get("name", gid)), "manage_guild": manage}
                )
        return result

    async def home(self, request):
        nonce = secrets.token_urlsafe(20)
        html = render_home(nonce, self.branding, self.auth_ready)
        notice=str(self.cfg.get('credential_notice',''))
        if not notice and self.ux.cfg.get('social',{}).get('hosted_credential_notice'):
            notice='Hosted service: the operator stores these credentials on the bot host. If that host is compromised, connected servers may be affected too. This experimental service is provided as-is; keep your own backups and use an account with limited access.'
        html=html.replace('__CREDENTIAL_NOTICE__',__import__('html').escape(notice))
        response = web.Response(text=html, content_type="text/html")
        response.headers["Content-Security-Policy"] = (
            "default-src 'none'; script-src 'nonce-"
            + nonce
            + "'; style-src 'nonce-"
            + nonce
            + "'; connect-src 'self'; img-src 'self' data: https://cdn.discordapp.com; frame-ancestors 'none'; base-uri 'none'; form-action 'self'"
        )
        return response

    async def session_hint(self,request):
        # Presentation only; no authority, tokens or CSRF. Every real operation
        # still uses session() and fresh Discord checks where required.
        key=hashlib.sha256(request.cookies.get('kei_session','').encode()).hexdigest()
        row=self.db.one('SELECT user,name FROM kei_web_sessions WHERE session_hash=? AND expires>?',(key,self.clock()))
        return web.json_response({'signed_in':bool(row),'name':row['name'] if row else None})

    async def state(self, request):
        session = await self.session(request)
        result = self.ux.state(session["user"])
        for server in result["servers"]:
            if server["manage_access"]:
                server["grants"] = self.ux.access.entries(session["user"], server["id"])
                for grant in server['grants'][:50]:
                    grant['person']=await self.ux.public_person(grant['subject'],server['id'],cached_only=True)
                    if grant.get('issuer') and str(grant['issuer']).isdigit():grant['grantor']=await self.ux.public_person(grant['issuer'],server['id'],cached_only=True)
        result.update(name=session["name"], csrf=session["csrf"], guilds=self.guilds(session))
        return web.json_response(result)

    def require_bot_owner(self, session):
        if str(session.get('user')) != str(self.ux.cfg.get('owner_id')):
            raise PermissionError('This page is available to the configured bot owner only.')

    async def global_occasions(self,request):
        session=await self.session(request);self.require_bot_owner(session)
        items=[]
        for row in self.db.rows('SELECT * FROM kei_social_occasions ORDER BY month,day LIMIT 200'):
            if self.db.tombstoned(json.loads(row['sources'])):continue
            user=self.ux.engine.identity.discord(row['person'])
            account=await self.ux.public_person(user,cached_only=True) if user else {'display_name':'Linked player'}
            delivery=self.db.one('SELECT status,at FROM kei_occasion_deliveries WHERE occasion=? ORDER BY year DESC LIMIT 1',(row['id'],))
            items.append({'person':account['display_name'],'kind':row['kind'],'month':row['month'],'day':row['day'],'enabled':bool(row['enabled']),'last_delivery':delivery})
        return web.json_response({'items':items,'note':'Private internal social occasions; actual delivery still requires DM opt-in and a relevant date.'})

    async def global_settings(self,request):
        session=await self.session(request)
        self.require_bot_owner(session)
        return web.json_response(self.ux.global_settings(session['user']))

    async def update_global_settings(self,request):
        session=await self.session(request,True)
        self.require_bot_owner(session)
        return web.json_response(self.ux.update_global_settings(session['user'],await request.json()))

    async def _global_live_servers(self):
        now=self.clock()
        cached_at,cached=self.global_live_cache
        if now-cached_at<30:return cached
        servers=list(self.ux.engine.servers.items())[:20]
        async def inspect(sid,profile):
            executor=self.ux.engine.tools.get(sid)
            result={'id':sid,'name':profile.get('name',sid),'state':'Not checked','players':None,
                    'connectors':sorted(k for k,v in getattr(executor,'cs',{}).items() if v) if executor else []}
            try:caps=executor.capabilities() if executor else []
            except Exception:caps=[]
            if not executor or 'status' not in caps:return result
            try:
                receipt=await asyncio.wait_for(asyncio.to_thread(executor.do_inspect,'status'),timeout=5)
                data=(receipt or {}).get('data') or {}
                result['state']=str(data.get('state') or 'Status returned without a state')[:80]
                players=data.get('players',data.get('players_online'))
                if isinstance(players,list):result['players']=len(players)
                if isinstance(players,list):result['player_names']=[str(p.get('name') or p.get('username')) if isinstance(p,dict) else str(p) for p in players[:30]]
                elif isinstance(players,dict):
                    online=players.get('online',players.get('count'))
                    if isinstance(online,int):result['players']=max(0,online)
                    names=players.get('sample') or players.get('list') or []
                    if isinstance(names,list):result['player_names']=[str(p.get('name') or p.get('username')) if isinstance(p,dict) else str(p) for p in names[:30]]
                elif isinstance(players,int):result['players']=max(0,players)
                if result['players'] is None and 'players' in caps and result['state'].casefold() in ('running','online','active'):
                    player_receipt=await asyncio.wait_for(asyncio.to_thread(executor.do_inspect,'players'),timeout=4)
                    output=str((player_receipt or {}).get('stdout') or (player_receipt or {}).get('console_output') or '')
                    match=__import__('re').search(r'(?:there are\s+)?(\d+)\s+(?:of\s+a\s+max\s+\d+\s+)?players? online\s*:?[ ]*(.*)',output,__import__('re').I)
                    if match:
                        result['players']=int(match.group(1));result['player_names']=[name.strip() for name in match.group(2).split(',') if name.strip()][:30]
            except asyncio.TimeoutError:result['state']='Check timed out'
            except Exception as exc:result['state']='Check failed · '+type(exc).__name__
            return result
        results=await asyncio.gather(*(inspect(sid,profile) for sid,profile in servers))
        self.global_live_cache=(now,results)
        return results

    async def global_overview(self,request):
        session=await self.session(request)
        self.require_bot_owner(session)
        from .overview import overview
        return web.json_response(await overview(self,request))

    async def global_relationships(self,request):
        session=await self.session(request)
        self.require_bot_owner(session)
        from .overview import relationships
        return web.json_response(relationships(self,request))

    async def profile(self, request):
        session = await self.session(request)
        # Personal web profile uses only the authenticated user's own DM context.
        profile=self.ux.profile(session["user"],"dm:"+session["user"])
        profile.pop("bond",None)
        return web.json_response(profile)

    async def memories(self,request):
        session=await self.session(request)
        return web.json_response(self.ux.engine.memory.episodes_page(session['user'],request.query.get('offset',0),request.query.get('limit',12),request.query.get('q','')))

    async def reports(self,request):
        session=await self.session(request)
        return web.json_response({'items':self.ux.engine.reports.recent(session['user'],request.query.get('server',''),20)})

    async def access_preview(self,request):
        session=await self.session(request,True);body=await request.json()
        return web.json_response(await self.ux.access_preview(session['user'],str(body.get('server','')),str(body.get('subject',''))))

    async def settings(self, request):
        session = await self.session(request, True)
        return web.json_response(self.ux.update(session["user"], await request.json()))

    async def link(self, request):
        session = await self.session(request, True)
        body = await request.json()
        server = str(body.get("server", ""))
        if server and server not in self.ux.access.visible(session["user"]):
            raise PermissionError("Bạn chưa có quyền server này.")
        code = self.ux.engine.identity.issue(session["user"], server)
        return web.json_response(
            {
                "command": "/kei link " + code,
                "expires_in": 600,
                "note": "Login Minecraft trước. Cần plugin Kei đang kết nối.",
            }
        )

    async def unlink(self, request):
        session = await self.session(request, True)
        body = await request.json()
        count = self.ux.engine.identity.unlink(session["user"], str(body.get("server", "")) or None)
        return web.json_response({"unlinked": count})

    async def forget(self, request):
        session = await self.session(request, True)
        body = await request.json()
        if body.get("confirm") is not True:
            raise ValueError("Xác nhận quên dữ liệu trước.")
        self.ux.engine.memory.forget(
            session["user"], None if body.get("all") is True else "dm:" + session["user"]
        )
        return web.json_response({"forgotten": True})

    async def access(self, request):
        session = await self.session(request, True)
        body = await request.json()
        server, subject, action = (
            str(body.get("server", "")),
            str(body.get("subject", "")),
            body.get("action", ""),
        )
        level = body.get("level", "observe")
        if not subject.isdigit():
            raise ValueError("Discord user ID cần dạng số.")
        if action=='save_member':
            self.ux.access.configure_member(session['user'],subject,server,body.get('role'),level,body.get('execution'))
            return web.json_response({'ok':True})
        # Validate and persist the effective policy with the grant in one transaction.
        if body.get('execution'):
            selected=body['execution']
            if not isinstance(selected,dict):raise ValueError('Mức quyền chưa hợp lệ.')
            with self.ux.db.atomic():
                self.ux.access.set_policy(session['user'],subject,server,selected.get('extent'),selected.get('level'),selected.get('config',selected.get('rules')))
                original=dict(body);original.pop('execution')
                if action=='policy':return web.json_response({'ok':True})
                # Remaining grant paths are simple local DB operations; validate action first.
                if action=='grant':self.ux.access.grant(session['user'],subject,server,level)
                elif action in ('admin','unadmin'):self.ux.access.delegate(session['user'],subject,server,action=='admin',level)
                elif action=='revoke':self.ux.access.revoke(session['user'],subject,server)
                elif action in ('owner','unowner'):self.ux.access.coowner(session['user'],subject,server,action=='owner')
                else:raise ValueError('Thao tác chưa hợp lệ.')
            return web.json_response({'ok':True})
        if action == 'reports':
            if subject!=session['user']:raise PermissionError('Chỉ sửa thông báo của chính bạn.')
            return web.json_response(self.ux.engine.reports.update(session['user'],server,body.get('preferences',{})))
        if action in ('owner','unowner'):
            self.ux.access.coowner(session['user'],subject,server,action=='owner')
        elif action == "grant":
            self.ux.access.grant(session["user"], subject, server, level)
        elif action == "revoke":
            self.ux.access.revoke(session["user"], subject, server)
        elif action in ("admin", "unadmin"):
            self.ux.access.delegate(session["user"], subject, server, action == "admin", level)
        else:
            raise ValueError("Chọn grant, revoke, admin hoặc unadmin.")
        return web.json_response(
            {"ok": True, "server": server, "subject": subject, "action": action}
        )

    async def connect_preview(self, request):
        session = await self.session(request, True)
        body = await request.json()
        result = await self.ux.connection_preview(
            session["user"], body.get("url", ""), body.get("token", "")
        )
        return web.json_response(result)

    async def connect_commit(self, request):
        session = await self.session(request, True)
        body = await request.json()
        guild = str(body.get("guild", ""))
        if guild and guild not in {g["id"] for g in self.guilds(session) if g["manage_guild"]}:
            raise PermissionError("Bạn chưa được quản lý guild này.")
        return web.json_response(
            self.ux.connection_commit(
                session["user"], body.get("connection", ""), body.get("index"), guild
            )
        )

    def connections(self):
        if not hasattr(self,'_connections'):
            from .onboarding import Connections
            self._connections=Connections(self.ux)
        return self._connections

    async def service_preview(self,request):
        session=await self.session(request,True)
        return web.json_response(await self.connections().preview(session['user'],await request.json()))

    async def service_commit(self,request):
        session=await self.session(request,True);body=await request.json();guild=str(body.get('guild',''))
        if guild and guild not in {g['id'] for g in self.guilds(session) if g['manage_guild']}:raise PermissionError('You do not manage this Discord server.')
        return web.json_response(await self.connections().commit(session['user'],str(body.get('connection','')),str(body.get('fingerprint','')),guild))

    async def server_test(self, request):
        session = await self.session(request, True)
        body = await request.json()
        return web.json_response(
            await self.ux.connection_test(session["user"], str(body.get("server", "")))
        )

    def scheduler(self):
        scheduler = getattr(self.ux.engine, "scheduler", None)
        if scheduler is None:
            raise ValueError("Bộ lịch chưa sẵn sàng.")
        return scheduler

    def bind_schedule_ack(self, session, task):
        if task.get("status") == "pending":
            source = "web:" + secrets.token_urlsafe(24)
            self.scheduler().bind_confirmation(session["user"], task["id"], source)
            session.setdefault("schedule_confirmations", {})[task["id"]] = source

    def public_task(self, task):
        return {
            k: task.get(k)
            for k in (
                "id",
                "goal",
                "status",
                "next_run",
                "timezone",
                "server",
                "mode",
                "alarm",
                "schedule",
            )
        }

    async def tasks(self, request):
        session = await self.session(request)
        scheduler = getattr(self.ux.engine, "scheduler", None)
        return web.json_response(
            {
                "available": scheduler is not None,
                "items": (
                    [self.public_task(t) for t in scheduler.list(session["user"])]
                    if scheduler
                    else []
                ),
            }
        )

    async def task_propose(self, request):
        session = await self.session(request, True)
        body = await request.json()
        scheduler = self.scheduler()
        from .scheduler import parse_schedule_text

        zone = str(
            body.get("timezone")
            or self.ux.engine.memory.preference(self.ux.person(session["user"])).get("timezone")
            or self.ux.cfg["timezone"]
        )
        mode = str(body.get("mode", "alarm"))
        if mode not in ("alarm", "observe", "change"):
            raise ValueError("Chọn alarm, observe hoặc change.")
        values = {
            "goal": str(body.get("goal", "")),
            "schedule": parse_schedule_text(body.get("when", ""), zone) if str(body.get("when", "")).strip() or not body.get("id") else scheduler.get(session["user"],str(body["id"]))["schedule"],
            "server": str(body.get("server", "")).strip() or None,
            "mode": "observe" if mode == "alarm" else mode,
            "alarm": mode == "alarm",
        }
        if body.get("id"):
            task = scheduler.change(session["user"], str(body["id"]), **values)
        else:
            # Web-created personal schedules deliver in the user's Discord DM.
            task = scheduler.propose(
                session["user"], "dm:" + session["user"], session["user"], **values
            )
        self.bind_schedule_ack(session, task)
        return web.json_response(
            {"task": self.public_task(task), "needs_confirmation": task.get("status") == "pending"}
        )

    async def task_action(self, request):
        session = await self.session(request, True)
        body = await request.json()
        scheduler = self.scheduler()
        ident, action = str(body.get("id", "")), str(body.get("action", ""))
        task = scheduler.get(session["user"], ident)
        if action == "confirm":
            confirmations = session.setdefault("schedule_confirmations", {})
            if ident not in confirmations:
                self.bind_schedule_ack(session, task)
            task = scheduler.confirm(session["user"], ident, confirmations.pop(ident, ""))
        elif action in ("pause", "resume", "cancel"):
            task = getattr(scheduler, action)(session["user"], ident)
            self.bind_schedule_ack(session, task)
        else:
            raise ValueError("Chọn confirm, pause, resume hoặc cancel.")
        return web.json_response(
            {"task": self.public_task(task), "needs_confirmation": task.get("status") == "pending"}
        )

    async def logout(self, request):
        session = await self.session(request, True)
        key = hashlib.sha256(request.cookies.get("kei_session", "").encode()).hexdigest()
        self._drop_session(key, session["token_ref"])
        response = web.json_response({"ok": True})
        response.del_cookie("kei_session", path="/")
        return response
