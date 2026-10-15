"""Bounded Discord context and validated delivery targets, never guild-wide ingestion."""

from __future__ import annotations
import json, time, logging, contextvars
import discord
from ..v2.store import uid, dumps
from .formatting import chunks

LOG = logging.getLogger("kei.conversation")
CURRENT_TASK = contextvars.ContextVar("kei_delivery_task", default=None)


def message_record(message):
    ref = getattr(message, "reference", None)
    author = message.author
    return {
        "id": str(message.id),
        "author_id": str(author.id),
        "display_name": str(getattr(author, "display_name", getattr(author, "name", ""))),
        "username": str(getattr(author, "name", "")),
        "global_name": getattr(author, "global_name", None),
        "bot": bool(author.bot),
        "webhook": bool(getattr(message, "webhook_id", None)),
        "content": str(message.content)[:3000],
        "at": message.created_at.timestamp(),
        "reply_to": str(ref.message_id) if ref else None,
        "mentions": [str(u.id) for u in getattr(message, "mentions", [])],
        "attachments": [
            {"filename": a.filename, "content_type": a.content_type}
            for a in getattr(message, "attachments", [])
        ][:4],
        "embeds": [
            {
                "title": e.title,
                "description": str(e.description or "")[:1200],
                "author": getattr(e.author, "name", None),
                "fields": [{"name": f.name, "value": str(f.value)[:600]} for f in e.fields[:5]],
            }
            for e in getattr(message, "embeds", [])
        ][:3],
        "reactions": [
            {"emoji": str(r.emoji), "count": r.count} for r in getattr(message, "reactions", [])
        ][:6],
    }


class Conversation:
    def __init__(self, store, config):
        self.db = store
        self.cfg = config
        store.db.executescript("""
        CREATE TABLE IF NOT EXISTS kei_nearby(request TEXT PRIMARY KEY,scope TEXT,actor TEXT,channel TEXT,data TEXT,at REAL);
        CREATE TABLE IF NOT EXISTS kei_delivery_targets(action TEXT PRIMARY KEY,scope TEXT,actor TEXT,mode TEXT,target TEXT,at REAL);
        CREATE TABLE IF NOT EXISTS kei_task_origins(task TEXT PRIMARY KEY,scope TEXT,actor TEXT,channel TEXT,message TEXT,ack TEXT);
        CREATE TABLE IF NOT EXISTS kei_task_outbox(outbox TEXT PRIMARY KEY,task TEXT);
        CREATE TABLE IF NOT EXISTS kei_social_sent(action TEXT PRIMARY KEY,message TEXT);
        """)
        if not hasattr(store, "delivery_queue_original"):
            store.delivery_queue_original = store.queue
            store.queue = self.legacy_queue

    def legacy_queue(self, channel, text, confirm_task=None):
        task = CURRENT_TASK.get() or confirm_task
        if task and self.db.one("SELECT name FROM sqlite_master WHERE type='table' AND name='kei_schedule_runs'"):
            scheduled=self.db.one('SELECT task FROM kei_schedule_runs WHERE task=?',(task,))
            status=self.db.one('SELECT status FROM kei_tasks WHERE id=?',(task,))
            if scheduled and status and status['status'] in ('succeeded','failed'):
                text=str(text)+'\n\n-# '+('✓ Task hoàn tất' if status['status']=='succeeded' else '✕ Task chưa hoàn tất')
        parts = chunks(text)
        ids = []
        for index, part in enumerate(parts):
            ident = uid()
            ids.append(ident)
            self.db.execute(
                "INSERT INTO kei_outbox(id,channel,content,status,message,at,attempts,confirm_task) VALUES (?,?,?,'pending',NULL,?,0,?)",
                (
                    ident,
                    str(channel),
                    part,
                    time.time(),
                    confirm_task if index == len(parts) - 1 else None,
                ),
            )
            if task:
                self.db.execute("INSERT INTO kei_task_outbox VALUES (?,?)", (ident, task))
        return ids

    def task_origin(self, task, scope, actor, channel, message, ack=""):
        self.db.execute(
            "INSERT OR REPLACE INTO kei_task_origins VALUES (?,?,?,?,?,?)",
            (task, scope, str(actor), str(channel), str(message), ack),
        )

    async def capture(self, channel, scope, actor, ids):
        if not scope.startswith("guild:") or not ids:
            return
        limit = max(1, min(30, int(self.cfg.get("social", {}).get("context_messages", 10))))
        records = {}
        status = "ok"
        try:
            async for message in channel.history(
                limit=limit, around=discord.Object(id=int(ids[-1]))
            ):
                records[str(message.id)] = message_record(message)
            # Reply chains can point beyond the immediate ten-message window; bounded depth.
            pending = list(ids)
            for _ in range(3):
                following = []
                for ident in pending[-3:]:
                    row = records.get(str(ident))
                    if not row:
                        try:
                            row = message_record(await channel.fetch_message(int(ident)))
                            records[str(ident)] = row
                        except (discord.NotFound, discord.Forbidden):
                            continue
                    target = row.get("reply_to")
                    if target and target not in records:
                        try:
                            ref = await channel.fetch_message(int(target))
                            if str(ref.channel.id) == str(channel.id):
                                records[target] = message_record(ref)
                        except (discord.NotFound, discord.Forbidden):
                            pass
                    if target and target in records:
                        following.append(target)
                pending = following
                if not pending:
                    break
        except discord.HTTPException as exc:
            status = type(exc).__name__
        payload = {
            "status": status,
            "channel": str(channel.id),
            "guild": scope.split(":")[1],
            "request_ids": list(map(str, ids)),
            "messages": sorted(records.values(), key=lambda r: (r["at"], r["id"])),
        }
        self.db.execute(
            "INSERT OR REPLACE INTO kei_nearby VALUES (?,?,?,?,?,?)",
            (str(ids[-1]), scope, str(actor), str(channel.id), dumps(payload), time.time()),
        )
        self.db.execute("DELETE FROM kei_nearby WHERE at<?", (time.time() - 3600,))

    def context(self, scope, request):
        row = self.db.one(
            "SELECT data FROM kei_nearby WHERE request=? AND scope=? AND at>?",
            (str(request), scope, time.time() - 3600),
        )
        data = json.loads(row["data"]) if row else {"messages": []}
        forgotten = {r["source"] for r in self.db.rows("SELECT source FROM kei_forget_tombstones")}
        data["messages"] = [m for m in data["messages"] if m["id"] not in forgotten]
        return data

    def queue(self, channel, request, kind, content, scope, actor, mode="reply", target=None):
        if kind == "silence":
            return None
        allowed = {m["id"]: m for m in self.context(scope, request)["messages"]}
        allowed[str(request)] = {"id": str(request)}
        target = str(target or request)
        if mode not in ("channel", "reply", "edit") or target not in allowed:
            mode = "reply"
            target = str(request)
        if mode == "edit":
            card = self.db.one(
                "SELECT c.message FROM kei_debug_cards c JOIN kei_tasks t ON t.id=c.task WHERE c.message=? AND t.scope=? AND t.requester=?",
                (target, scope, str(actor)),
            )
            if not card:
                mode = "reply"
                target = str(request)
        ident = uid()
        self.db.execute(
            "INSERT INTO kei_social_actions VALUES (?,?,?,?,?,?,?)",
            (ident, str(channel), str(request), kind, content, "pending", time.time()),
        )
        self.db.execute(
            "INSERT INTO kei_delivery_targets VALUES (?,?,?,?,?,?)",
            (ident, scope, str(actor), mode, target, time.time()),
        )
        return ident

    async def reference(self, channel, target):
        if not target or not str(target).isdigit():
            return None
        try:
            message = await channel.fetch_message(int(target))
            if str(message.channel.id) != str(channel.id):
                return None
            if time.time() - message.created_at.timestamp() > 7 * 86400:
                return None
            return message.to_reference(fail_if_not_exists=False)
        except (discord.NotFound, discord.Forbidden, discord.HTTPException):
            return None

    async def deliver(self, channel, row):
        target = self.db.one("SELECT * FROM kei_delivery_targets WHERE action=?", (row["id"],))
        ident = target["target"] if target else row["message"]
        if row["kind"] == "react":
            try:
                message = await channel.fetch_message(int(ident))
                if str(message.channel.id) != str(channel.id):
                    return None
                if time.time() - message.created_at.timestamp() > 7 * 86400:
                    return None
                await message.add_reaction(row["content"])
            except (
                discord.NotFound,
                discord.Forbidden,
                discord.HTTPException,
                ValueError,
                TypeError,
            ):
                LOG.info("REACTION_TARGET_UNAVAILABLE")
            return
        mode = target["mode"] if target else "reply"
        if mode == "edit":
            try:
                message = await channel.fetch_message(int(ident))
                if message.author.id == channel._state.user.id:
                    await message.edit(
                        content=row["content"][:2000],
                        allowed_mentions=discord.AllowedMentions.none(),
                    )
                    return str(message.id)
            except (discord.NotFound, discord.Forbidden, discord.HTTPException):
                pass
        reference = await self.reference(channel, ident) if mode != "channel" else None
        first = None
        for index, chunk in enumerate(chunks(row["content"])):
            sent = await channel.send(
                chunk,
                reference=reference if index == 0 else None,
                allowed_mentions=discord.AllowedMentions.none(),
            )
            if first is None:
                first = str(sent.id)
        return first
