from __future__ import annotations
import asyncio, json, secrets, time
from aiohttp import web, WSMsgType
from ..v2.store import uid, dumps


class Bridge:
    def __init__(self, store, config, secret_store):
        self.db = store
        self.cfg = config
        self.secrets = secret_store
        self.peers = {}
        self.pending = {}
        self.loop = None
        self.handler = None
        self.runner = None

    def profile(self, server):
        return self._registered(server) or next(
            (p for p in self.cfg["servers"] if p["id"] == server), None
        )

    def _registered(self, server):
        row = self.db.one("SELECT profile FROM kei_registered_servers WHERE id=?", (server,))
        return json.loads(row["profile"]) if row else None

    async def start(self):
        if not self.cfg["bridge"]["enabled"]:
            return
        self.loop = asyncio.get_running_loop()
        app = web.Application(client_max_size=70 * 1024 * 1024)
        app.router.add_get("/v1/bridge", self.connect)
        app.router.add_get(
            "/health",
            lambda _: web.json_response({"ok": True, "protocol": 1, "connected": len(self.peers)}),
        )
        self.runner = web.AppRunner(app)
        await self.runner.setup()
        await web.TCPSite(
            self.runner, self.cfg["bridge"]["host"], int(self.cfg["bridge"]["port"])
        ).start()

    async def close(self):
        for peer in list(self.peers.values()):
            await peer["ws"].close()
        if self.runner:
            await self.runner.cleanup()

    def online(self, server):
        return server in self.peers and not self.peers[server]["ws"].closed

    def capabilities(self, server):
        return self.peers.get(server, {}).get("capabilities", [])

    def social_config(self, server):
        by_uuid = {}
        for account in self.db.rows(
            "SELECT * FROM kei_accounts WHERE platform='minecraft' AND server=?", (server,)
        ):
            pref = self.db.one(
                "SELECT sharing FROM kei_social_preferences WHERE person=?", (account["person"],)
            )
            sharing = (pref or {}).get("sharing") or self.cfg["memory"]["cross_context"]
            aliases = []
            for row in self.db.rows(
                "SELECT * FROM kei_aliases WHERE person=?", (account["person"],)
            ):
                same = (
                    row["scope"] == "mc:" + server
                    or row["scope"] == "mc-private:" + server + ":" + account["account"]
                )
                source = self.db.one(
                    "SELECT shareability,visibility FROM kei_social_events WHERE person=? AND scope=? AND kind='nickname' ORDER BY at DESC LIMIT 1",
                    (account["person"], row["scope"]),
                )
                if (same or sharing=='discreet') and not self.db.tombstoned(json.loads(row['sources'])):
                    aliases.append(row["alias"])
            if aliases:
                by_uuid[account["account"]] = list(dict.fromkeys(aliases))[:20]
        return {
            "type": "config",
            "triggers": self.cfg["social"]["triggers"],
            "aliases_by_uuid": by_uuid,
        }

    def refresh_aliases(self):
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            return
        for server, peer in list(self.peers.items()):
            if not peer["ws"].closed:
                loop.create_task(peer["ws"].send_json(self.social_config(server)))

    async def connect(self, request):
        server = request.query.get("server", "")
        p = self.profile(server)
        ref = (p or {}).get("connectors", {}).get("bridge", {}).get("token")
        expected = self.secrets.get(ref)
        actual = request.headers.get("Authorization", "").removeprefix("Bearer ")
        if not p or not expected or not secrets.compare_digest(expected, actual):
            raise web.HTTPUnauthorized()
        ws = web.WebSocketResponse(heartbeat=25, max_msg_size=70 * 1024 * 1024)
        await ws.prepare(request)
        if server in self.peers:
            await self.peers[server]["ws"].close(code=1008, message=b"replaced connection")
        peer = {"ws": ws, "capabilities": [], "at": time.time()}
        self.peers[server] = peer
        try:
            async for msg in ws:
                if msg.type != WSMsgType.TEXT:
                    continue
                try:
                    data = json.loads(msg.data)
                except ValueError:
                    continue
                kind = data.get("type")
                if kind == "hello":
                    if data.get("protocol") != 1:
                        await ws.close(code=1008, message=b"unsupported protocol")
                        break
                    peer.update(
                        capabilities=data.get("capabilities", []),
                        authenticated=bool(data.get("authenticated_sessions")),
                        version=data.get("version"),
                    )
                    await ws.send_json({"type": "hello", "protocol": 1, "server": server})
                    await ws.send_json(self.social_config(server))
                elif kind == "rpc.result":
                    ident = data.get("id")
                    future = self.pending.get((server, ident))
                    result = data.get("result", {})
                    if future and not future.done():
                        future.set_result(result)
                    self.db.execute(
                        "UPDATE kei_bridge_requests SET status='answered',result=? WHERE id=? AND server=?",
                        (dumps(result), ident, server),
                    )
                elif kind == "chat" and self.handler:
                    if not peer.get("capabilities"):
                        continue
                    # Server identity is bound by credential, never accepted from the payload.
                    data["server"] = server
                    asyncio.create_task(self.handler(data))
                elif kind == "ping":
                    await ws.send_json({"type": "pong"})
        finally:
            if self.peers.get(server) is peer:
                self.peers.pop(server, None)
            for (sid, _), future in list(self.pending.items()):
                if sid == server and not future.done():
                    future.set_exception(
                        ConnectionError(
                            "Bridge disconnected after dispatch; reconcile before retry"
                        )
                    )
        return ws

    async def rpc(self, server, method, args=None, effect="read", timeout=35, request_id=None):
        if not self.online(server):
            raise ConnectionError("Minecraft bridge chưa online")
        ident = request_id or uid()
        prior = self.db.one("SELECT * FROM kei_bridge_requests WHERE id=?", (ident,))
        if prior and prior["status"] == "answered":
            return json.loads(prior["result"])
        if prior and effect != "read":
            raise RuntimeError("Outcome uncertain; reconcile before retry")
        future = asyncio.get_running_loop().create_future()
        self.pending[(server, ident)] = future
        self.db.execute(
            "INSERT OR REPLACE INTO kei_bridge_requests VALUES (?,?,?,?,?,?,?)",
            (ident, server, method, effect, "dispatched", None, time.time()),
        )
        try:
            await self.peers[server]["ws"].send_json(
                {
                    "type": "rpc.request",
                    "id": ident,
                    "method": method,
                    "args": args or {},
                    "effect": effect,
                }
            )
            return await asyncio.wait_for(future, timeout)
        finally:
            self.pending.pop((server, ident), None)

    def rpc_sync(self, server, method, args=None, effect="read", timeout=35):
        if not self.loop:
            raise ConnectionError("Bridge service not started")
        return asyncio.run_coroutine_threadsafe(
            self.rpc(server, method, args, effect, timeout), self.loop
        ).result(timeout + 3)

    async def send(self, server, uuid, text, public=False):
        return await self.rpc(
            server, "chat.send", {"uuid": uuid, "text": text, "public": public}, "read"
        )

    async def progress(self, server, uuid, text):
        return await self.rpc(server, "chat.progress", {"uuid": uuid, "text": text}, "read")
