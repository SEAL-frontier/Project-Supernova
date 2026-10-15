"""Optional aiohttp dashboard. OAuth credentials and session authority stay server-side."""

from __future__ import annotations

import asyncio
import base64
import hashlib
import logging
import secrets
import time
from urllib.parse import urlencode, urlsplit

import aiohttp
from aiohttp import web

from .config import Secrets

LOG = logging.getLogger("kei.web")
DISCORD = "https://discord.com/api/v10"


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
        if not token:
            raise PermissionError("Discord không cấp session đăng nhập.")
        user, guilds = await self.identity(token)
        return user, guilds, token

    async def close(self):
        if self.http is not None:
            await self.http.close()


class Dashboard:
    def __init__(self, ux, oauth=None, clock=time.time):
        self.ux, self.cfg, self.clock = ux, ux.cfg.get("web", {}), clock
        self.oauth = oauth
        self.runner = None
        self.site = None
        self.sessions = {}
        self.states = {}
        self.origin = ""
        self.secure = True
        self.status = "disabled"
        self.auth_ready = False
        self.setup_message = "Đăng nhập web chưa sẵn sàng: operator cần cấu hình Discord OAuth. Bạn vẫn dùng /setup và /settings trong Discord bình thường."

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
                    {"error": str(exc)}, status=403 if isinstance(exc, PermissionError) else 400
                )
            except web.HTTPException as exc:
                response = web.json_response(
                    {"error": exc.text},
                    status=exc.status,
                    headers={k: v for k, v in exc.headers.items() if k.lower() != "content-type"},
                )
            except Exception as exc:
                # Never relay upstream bodies, URL credentials or stack traces to the browser.
                LOG.warning(
                    "DASHBOARD_REQUEST_FAILED path=%s type=%s", request.path, type(exc).__name__
                )
                response = web.json_response(
                    {"error": "Chưa xử lý được. Thử lại hoặc xem diagnostics local."}, status=502
                )
            response.headers["Cache-Control"] = "no-store"
            response.headers["X-Content-Type-Options"] = "nosniff"
            response.headers["Referrer-Policy"] = "no-referrer"
            response.headers["X-Frame-Options"] = "DENY"
            return response

        app = web.Application(middlewares=[errors], client_max_size=16384)
        app.router.add_get("/", self.home)
        app.router.add_get("/login", self.login)
        app.router.add_get("/oauth/callback", self.callback)
        app.router.add_get("/api/state", self.state)
        app.router.add_get("/api/profile", self.profile)
        app.router.add_post("/api/settings", self.settings)
        app.router.add_post("/api/link", self.link)
        app.router.add_post("/api/unlink", self.unlink)
        app.router.add_post("/api/forget", self.forget)
        app.router.add_post("/api/access", self.access)
        app.router.add_post("/api/connect/preview", self.connect_preview)
        app.router.add_post("/api/connect/commit", self.connect_commit)
        app.router.add_post("/api/server/test", self.server_test)
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
                "Dashboard unavailable (%s); /setup and /settings remain available",
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
        self.sessions.clear()

    def prune(self):
        now = self.clock()
        self.states = {k: v for k, v in self.states.items() if v["expires"] > now}
        self.sessions = {k: v for k, v in self.sessions.items() if v["expires"] > now}
        while len(self.states) >= 128:
            self.states.pop(next(iter(self.states)))
        while len(self.sessions) >= 256:
            self.sessions.pop(next(iter(self.sessions)))

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
        user, guilds, token = await self.oauth.exchange(code, saved["verifier"])
        sid = secrets.token_urlsafe(32)
        self.sessions[hashlib.sha256(sid.encode()).hexdigest()] = {
            "user": str(user["id"]),
            "name": str(user.get("global_name") or user.get("username") or user["id"]),
            "guilds": guilds,
            "token": token,
            "csrf": secrets.token_urlsafe(32),
            "expires": self.clock() + 3600,
            "checked": self.clock(),
        }
        response = web.Response(status=302, headers={"Location": "/"})
        response.del_cookie("kei_oauth", path="/")
        response.set_cookie(
            "kei_session",
            sid,
            max_age=3600,
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
        session = self.sessions.get(sid)
        if not session:
            raise web.HTTPUnauthorized(text="Đăng nhập Discord trước nhé.")
        if write:
            if request.headers.get("Origin") != self.origin or not secrets.compare_digest(
                session["csrf"], request.headers.get("X-CSRF-Token", "")
            ):
                raise PermissionError("Phiên thao tác chưa hợp lệ. Tải lại trang rồi thử lại.")
            if request.content_type != "application/json":
                raise ValueError("Gửi JSON hợp lệ.")
        # Discord permissions are refreshed before every privileged write, not browser-supplied.
        if write or self.clock() - session["checked"] > 300:
            user, guilds = await self.oauth.identity(session["token"])
            if str(user["id"]) != session["user"]:
                self.sessions.pop(sid, None)
                raise PermissionError("Danh tính Discord đã thay đổi; đăng nhập lại.")
            session.update(guilds=guilds, checked=self.clock())
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
        html = HTML.replace("__NONCE__", nonce)
        if not self.auth_ready:
            html = html.replace(
                '<a id="login" href="/login">Đăng nhập Discord</a>',
                '<span id="login" class="muted">Discord login chưa sẵn sàng</span>',
            )
        response = web.Response(text=html, content_type="text/html")
        response.headers["Content-Security-Policy"] = (
            "default-src 'none'; script-src 'nonce-"
            + nonce
            + "'; style-src 'nonce-"
            + nonce
            + "'; connect-src 'self'; img-src 'self' data:; frame-ancestors 'none'; base-uri 'none'; form-action 'self'"
        )
        return response

    async def state(self, request):
        session = await self.session(request)
        result = self.ux.state(session["user"])
        for server in result["servers"]:
            if server["manage_access"]:
                server["grants"] = self.ux.access.entries(session["user"], server["id"])
        result.update(name=session["name"], csrf=session["csrf"], guilds=self.guilds(session))
        return web.json_response(result)

    async def profile(self, request):
        session = await self.session(request)
        # Personal web profile uses only the authenticated user's own DM context.
        return web.json_response(self.ux.profile(session["user"], "dm:" + session["user"]))

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
        if action == "grant":
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
            "schedule": parse_schedule_text(body.get("when", ""), zone),
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
        await self.session(request, True)
        key = hashlib.sha256(request.cookies.get("kei_session", "").encode()).hexdigest()
        self.sessions.pop(key, None)
        response = web.json_response({"ok": True})
        response.del_cookie("kei_session", path="/")
        return response


HTML = r"""<!doctype html>
<html lang="vi"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Keys Keys · Your settings</title>
<style nonce="__NONCE__">
:root{color-scheme:dark;--bg:#15151b;--card:#202028;--line:#35343f;--muted:#bab5c0;--pink:#efa5a5}*{box-sizing:border-box}body{margin:0;background:var(--bg);color:#f5eff2;font:16px/1.6 system-ui,sans-serif}main{max-width:1000px;margin:auto;padding:24px}header{display:flex;justify-content:space-between;align-items:center;border-bottom:1px solid var(--line);padding-bottom:20px}h1{font-size:32px;margin:0}h2{font-size:21px;margin:0 0 12px}p{margin:8px 0}small,.muted{color:var(--muted)}a{color:var(--pink)}.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(300px,1fr));gap:16px;margin-top:20px}.card{background:var(--card);border:1px solid var(--line);border-radius:18px;padding:22px}.wide{grid-column:1/-1}label{display:block;margin:12px 0 4px;font-size:14px;color:var(--muted)}input,select,button{font:inherit;border-radius:9px;border:1px solid #504651;background:#18181f;color:inherit;padding:10px 12px;max-width:100%}input,select{width:100%}button{cursor:pointer;margin:12px 8px 0 0}button.primary{background:var(--pink);color:#251a20;border-color:var(--pink)}button.danger{border-color:#c97883;color:#ffb1bd}.hidden{display:none!important}#status{position:sticky;top:0;background:#33252d;padding:10px 16px;border-radius:10px;margin:16px 0;white-space:pre-line}.item{padding:12px 0;border-bottom:1px solid var(--line);overflow-wrap:anywhere}code{background:#14141a;padding:2px 5px;border-radius:4px;overflow-wrap:anywhere}pre{white-space:pre-wrap;overflow-wrap:anywhere;font:inherit}.stats{display:flex;flex-wrap:wrap;gap:8px}.pill{background:#302833;border-radius:20px;padding:3px 10px;font-size:14px}@media(max-width:420px){main{padding:16px}.grid{grid-template-columns:1fr}.card{padding:17px}h1{font-size:27px}header{align-items:flex-start;gap:12px}}
</style>
<main><header><div><h1>keys keys</h1><small>Her problem. Your server.</small></div><a id="login" href="/login">Đăng nhập Discord</a><button id="logout" class="hidden">Đăng xuất</button></header>
<div id="status" role="status" class="hidden"></div>
<section id="welcome" class="card" style="margin-top:20px"><h2>Kei, dễ thiết lập hơn một chút.</h2><p>Chat, giữ những chuyện đáng nhớ, và nhờ quản lý Minecraft khi bạn có quyền. Không cần có server để nói chuyện.</p><p>Đăng nhập Discord hoặc dùng <code>/setup</code> và <code>/settings</code> ngay trong Discord.</p><small>Chat, memories and Minecraft. Your account only; server access is checked by the bot.</small></section>
<div id="settings" class="grid hidden">
<section class="card"><h2>Xin chào, <span id="name"></span></h2><label>Tính cách / Personality</label><select id="persona"><option value="auto">Linh hoạt / Adaptive</option><option value="soft">Dịu hơn / Gentle</option><option value="spicy">Đậm vị / Sharp</option></select><label>Tiến độ công việc / Task status</label><select id="debug"><option value="off">Ẩn / Off</option><option value="minimal">Checklist</option><option value="advanced">Checklist + lệnh/log</option></select><label>Múi giờ / Timezone</label><input id="timezone" value="Asia/Ho_Chi_Minh"><button id="save" class="primary">Lưu thiết lập</button></section>
<section class="card"><h2>Tham gia & quyền riêng tư</h2><label>Chủ động nhắn DM / Proactive DMs</label><select id="dm"><option value="false">Tắt</option><option value="true">Cho phép, theo giờ yên lặng</option></select><label>Kei có thể trả lời bạn</label><select id="muted"><option value="false">Bình thường</option><option value="true">Để mình yên</option></select><label>Memory giữa các ngữ cảnh</label><select id="sharing"><option value="strict">Chỉ nơi đã nói / Strict</option><option value="discreet">Gợi nhắc kín đáo / Discreet</option></select><label>Thông báo thay đổi rank</label><select id="rank"><option value="true">Bật</option><option value="false">Tắt</option></select><small>Không quote DM ra public. Rank không cấp quyền quản trị.</small></section>
<section class="card"><h2>Kei ↔ Bạn</h2><p id="relationship">Đang đọc profile…</p><div id="dimensions" class="stats"></div><div id="memories"></div><button id="forget" class="danger">Quên memory trong DM</button><button id="forget-all" class="danger">Quên dữ liệu của mình</button></section>
<section class="card"><h2>Tài khoản Minecraft</h2><div id="accounts"></div><button id="link">Tạo mã link</button><button id="unlink" class="danger">Gỡ link</button><p id="link-code"></p><small>Nhập mã trong Minecraft sau khi login. Cần plugin Kei đang kết nối. Link không tự cấp thêm quyền server.</small></section>
<section class="card wide"><h2>Minecraft của bạn</h2><p class="muted">Chỉ hiện server bạn được phép dùng. Capability là kết nối hiện có; không tự khẳng định plugin đã cài.</p><label>Server mặc định cho DM</label><select id="default-server"></select><button id="default-save">Lưu server mặc định</button><div id="servers"></div></section>
<section id="tasks-card" class="card wide hidden"><h2>Lịch hẹn & công việc định kỳ</h2><p class="muted">Nhắc việc hoặc nhờ Kei kiểm tra server sau. Lịch mới/sửa lịch cần bấm 🕒 xác nhận; chưa xác nhận thì chưa chạy. Kết quả gửi về DM của bạn.</p><div id="tasks-list"></div><label>Việc hoặc lời nhắc</label><input id="task-goal" maxlength="1000" placeholder="Nhắc mình đi ngủ / kiểm tra TPS server"><label>Khi nào?</label><input id="task-when" placeholder="ngày mai 07:00 / mỗi ngày 07:00"><label>Loại việc</label><select id="task-mode"><option value="alarm">Lời nhắc</option><option value="observe">Kiểm tra server (chỉ xem)</option><option value="change">Làm việc được phép trên server</option></select><label>Server ID (bỏ trống nếu chỉ nhắc việc)</label><input id="task-server" placeholder="sarisu"><button id="task-save" class="primary">Đề xuất lịch</button><button id="task-reset">Tạo lịch mới</button><small>Lịch dùng múi giờ cá nhân phía trên. Mọi lần chạy vẫn kiểm quyền server; quan hệ thân thiết không thay thế quyền.</small></section>
<section id="connect-card" class="card hidden"><h2>Kết nối server</h2><p class="muted">Panel → Account → API Credentials → tạo Client API key. Dùng key của account thật sự có quyền server.</p><label>Panel URL</label><input id="panel-url" placeholder="https://panel.example.com"><label>Client API key</label><input id="panel-key" type="password" autocomplete="off"><button id="preview">Kiểm tra kết nối</button><div id="candidate" class="hidden"><label>Server từ Panel</label><select id="candidate-server"></select><label>Guild (tùy chọn)</label><select id="candidate-guild"><option value="">Chưa gắn guild</option></select><button id="commit" class="primary">Kết nối server đã chọn</button></div><small>Credential giữ ở bot, không đưa cho model. SSH/local setup vẫn có trong CLI cho operator.</small></section>
<section id="access-card" class="card hidden"><h2>Quyền server</h2><label>Server</label><select id="access-server"></select><label>Discord user ID</label><input id="subject" inputmode="numeric"><label>Thao tác</label><select id="action"><option value="grant">Cấp quyền</option><option value="revoke">Thu hồi quyền</option><option value="admin">Bổ nhiệm admin (owner)</option><option value="unadmin">Gỡ admin (owner)</option></select><label>Phạm vi</label><select id="level"><option value="observe">observe · chỉ xem</option><option value="copilot">copilot · thao tác được phép</option><option value="chat">chat · chỉ trò chuyện</option></select><button id="access-save">Lưu phân quyền</button><small>Admin chỉ quản lý đúng server được giao. Người cấp và phạm vi được ghi lại; owner có thể thu hồi.</small></section>
</div><p class="muted"><small>Headless / recovery: <code>keys-keys setup --edit</code> · <code>keys-keys doctor</code></small></p></main>
<script nonce="__NONCE__">
let state=null,candidate=null;const $=id=>document.getElementById(id);function note(text){$('status').textContent=text;$('status').classList.remove('hidden')}async function api(path,data){const opts=data===undefined?{}:{method:'POST',headers:{'Content-Type':'application/json','X-CSRF-Token':state?.csrf||''},body:JSON.stringify(data)};const r=await fetch(path,opts);let value;try{value=await r.json()}catch{throw Error(r.status===401?'Đăng nhập Discord trước nhé.':'Chưa nhận được phản hồi hợp lệ.')}if(!r.ok)throw Error(value.error||'Thao tác chưa thành công.');return value}function option(select,value,label){const o=document.createElement('option');o.value=value;o.textContent=label;select.append(o)}function line(parent,text){const p=document.createElement('div');p.className='item';p.textContent=text;parent.append(p);return p}function run(fn){return async()=>{try{await fn()}catch(e){note(e.message)}}}async function load(){state=await api('/api/state');$('name').textContent=state.name;$('login').classList.add('hidden');$('logout').classList.remove('hidden');$('welcome').classList.add('hidden');$('settings').classList.remove('hidden');for(const key of ['persona','debug'])$(key).value=state[key];$('timezone').value=state.preferences.timezone||'Asia/Ho_Chi_Minh';$('dm').value=String(Boolean(state.preferences.dm_opt_in));$('muted').value=String(Boolean(state.preferences.muted));$('sharing').value=state.preferences.sharing||'strict';$('rank').value=String(state.preferences.rank_notifications!==false);$('accounts').replaceChildren();for(const a of state.linked_accounts)line($('accounts'),a.account+' · '+a.server);if(!state.linked_accounts.length)$('accounts').textContent='Chưa link tài khoản.';$('servers').replaceChildren();$('default-server').replaceChildren();$('access-server').replaceChildren();for(const s of state.servers){option($('default-server'),s.id,s.name);const row=line($('servers'),s.name+' · '+s.level+'\nCó thể dùng: '+s.capabilities.join(', '));const b=document.createElement('button');b.textContent='Kiểm tra kết nối';b.onclick=run(async()=>{note('Đang kiểm tra '+s.name+'…');const r=await api('/api/server/test',{server:s.id});note(r.message)});row.append(b);if(s.manage_access){option($('access-server'),s.id,s.name);for(const g of s.grants||[])line(row,g.subject+' · '+g.level+(g.admin?' + admin':'')+' · cấp bởi '+g.issuer)}}if(!state.servers.length)$('servers').textContent='Chưa được assign server; bạn vẫn chat bình thường được.';if(state.default_server)$('default-server').value=state.default_server;$('connect-card').classList.toggle('hidden',!state.can_connect);$('access-card').classList.toggle('hidden',!state.servers.some(s=>s.manage_access));$('candidate-guild').replaceChildren();option($('candidate-guild'),'','Chưa gắn guild');for(const g of state.guilds.filter(g=>g.manage_guild))option($('candidate-guild'),g.id,g.name);const p=await api('/api/profile');$('relationship').textContent=(p.rank?.label||'Neutral')+' · '+(p.rank?.reason||'Chưa có thay đổi đáng kể.');$('dimensions').replaceChildren();for(const [k,v]of Object.entries(p.dimensions||{})){if(typeof v!=='number')continue;const el=document.createElement('span');el.className='pill';el.textContent=k+': '+Math.round(v*100)+'%';$('dimensions').append(el)}$('memories').replaceChildren();for(const m of (p.memories||[]).slice(0,5))line($('memories'),m.title||m.summary||'')}
let editingTask=null;
async function loadTasks(){
 const data=await api('/api/tasks');$('tasks-card').classList.toggle('hidden',!data.available);$('tasks-list').replaceChildren();
 const names={pending:'Chờ xác nhận',active:'Đã hẹn',paused:'Tạm dừng',completed:'Hoàn tất',cancelled:'Đã hủy'};
 for(const task of data.items){
  const row=line($('tasks-list'),task.goal+' · '+(names[task.status]||task.status)+(task.next_run?' · '+new Date(task.next_run*1000).toLocaleString():''));
  for(const[action,label]of [['confirm','🕒 Xác nhận'],['pause','Tạm dừng'],['resume','Tiếp tục'],['cancel','Hủy']]){
   if(action==='confirm'&&task.status!=='pending')continue;
   const b=document.createElement('button');b.textContent=label;b.onclick=run(async()=>{await api('/api/tasks/action',{id:task.id,action});await loadTasks();note(action==='confirm'?'Đã xác nhận lịch.':'Đã cập nhật lịch; lịch tiếp tục cần xác nhận lại.');});row.append(b);
  }
  const edit=document.createElement('button');edit.textContent='Sửa';edit.onclick=()=>{editingTask=task.id;$('task-goal').value=task.goal;$('task-server').value=task.server||'';$('task-mode').value=task.alarm?'alarm':task.mode;$('task-when').value='';$('task-save').textContent='Đề xuất sửa lịch';$('task-when').focus();};row.append(edit);
 }
}
const loadSettings=load;load=async()=>{await loadSettings();await loadTasks();};
$('task-save').onclick=run(async()=>{await api('/api/tasks/propose',{id:editingTask,goal:$('task-goal').value,when:$('task-when').value,server:$('task-server').value,mode:$('task-mode').value,timezone:$('timezone').value});editingTask=null;$('task-save').textContent='Đề xuất lịch';await loadTasks();note('Lịch đang chờ. Bấm 🕒 Xác nhận nếu đúng thời gian và công việc.');});
$('task-reset').onclick=()=>{editingTask=null;$('task-goal').value='';$('task-when').value='';$('task-server').value='';$('task-save').textContent='Đề xuất lịch';};
$('save').onclick=run(async()=>{await api('/api/settings',{persona:$('persona').value,debug:$('debug').value,timezone:$('timezone').value,dm_opt_in:$('dm').value==='true',muted:$('muted').value==='true',sharing:$('sharing').value,rank_notifications:$('rank').value==='true'});note('Đã lưu thiết lập.');await load()});$('default-save').onclick=run(async()=>{await api('/api/settings',{default_server:$('default-server').value});note('Đã lưu server mặc định cho DM.')});$('link').onclick=run(async()=>{const r=await api('/api/link',{});$('link-code').textContent=r.command+' · hết hạn sau 10 phút.'});$('unlink').onclick=run(async()=>{if(confirm('Gỡ các liên kết Minecraft của bạn?')){await api('/api/unlink',{});await load();note('Đã gỡ link.')}});for(const [id,all]of [['forget',false],['forget-all',true]])$(id).onclick=run(async()=>{if(confirm(all?'Quên toàn bộ dữ liệu của bạn?':'Quên memory của bạn trong DM?')){await api('/api/forget',{confirm:true,all});await load();note('Đã quên dữ liệu và phần dẫn xuất liên quan.')}});$('preview').onclick=run(async()=>{note('Đang kiểm tra Panel…');candidate=await api('/api/connect/preview',{url:$('panel-url').value,token:$('panel-key').value});$('panel-key').value='';$('candidate-server').replaceChildren();for(const s of candidate.servers)option($('candidate-server'),String(s.index),s.name);$('candidate').classList.remove('hidden');note('Đã đọc danh sách từ Panel. Chọn đúng server để kết nối.')});$('commit').onclick=run(async()=>{const r=await api('/api/connect/commit',{connection:candidate.connection,index:Number($('candidate-server').value),guild:$('candidate-guild').value});candidate=null;$('candidate').classList.add('hidden');await load();note('Đã kết nối '+r.name+'.')});$('access-save').onclick=run(async()=>{await api('/api/access',{server:$('access-server').value,subject:$('subject').value,action:$('action').value,level:$('level').value});await load();note('Đã lưu phân quyền.')});$('logout').onclick=run(async()=>{await api('/logout',{});location.reload()});load().catch(e=>{if(!String(e.message).includes('Đăng nhập'))note(e.message)});
</script></html>"""
