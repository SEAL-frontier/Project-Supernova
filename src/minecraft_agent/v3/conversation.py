"""Bounded Discord context and validated delivery targets, never guild-wide ingestion."""

from __future__ import annotations
import json, time, logging, contextvars
from pathlib import Path
from io import BytesIO
import discord
from ..v2.store import uid, dumps
from .formatting import chunks, chat_chunks

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
        self.math_render_root = (Path(config.get("database", "data/kei.db")).parent / "math-renders").resolve()
        store.db.executescript("""
        CREATE TABLE IF NOT EXISTS kei_conversation_parts(action TEXT PRIMARY KEY,parts TEXT);
        CREATE TABLE IF NOT EXISTS kei_conversation_sent(action TEXT,ordinal INTEGER,message TEXT,PRIMARY KEY(action,ordinal));
        CREATE TABLE IF NOT EXISTS kei_nearby(request TEXT PRIMARY KEY,scope TEXT,actor TEXT,channel TEXT,data TEXT,at REAL);
        CREATE TABLE IF NOT EXISTS kei_delivery_targets(action TEXT PRIMARY KEY,scope TEXT,actor TEXT,mode TEXT,target TEXT,at REAL);
        CREATE TABLE IF NOT EXISTS kei_task_origins(task TEXT PRIMARY KEY,scope TEXT,actor TEXT,channel TEXT,message TEXT,ack TEXT);
        CREATE TABLE IF NOT EXISTS kei_task_outbox(outbox TEXT PRIMARY KEY,task TEXT);
        CREATE TABLE IF NOT EXISTS kei_social_sent(action TEXT PRIMARY KEY,message TEXT);
        CREATE TABLE IF NOT EXISTS kei_search_cards(channel TEXT,request TEXT,message TEXT,header TEXT,receipts TEXT,at REAL,finished INTEGER DEFAULT 0,PRIMARY KEY(channel,request));
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
        parts = chunks(text) if confirm_task else chat_chunks(text)
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
        if not row and scope.startswith('dm:'):
            cutoff=self.db.one('SELECT at FROM kei_messages WHERE id=? AND scope=?',(str(request),scope))
            if cutoff:
                data['messages']=list(reversed(self.db.rows("SELECT id,user,role,content,at FROM kei_messages WHERE scope=? AND forgotten=0 AND at<=? AND (role='assistant' OR user=?) ORDER BY at DESC LIMIT 10",(scope,cutoff['at'],scope.split(':',1)[1]))))
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
        if scope.startswith("dm:") and mode == "reply" and target == str(request):
            mode = "channel"
        elif scope.startswith('guild:') and mode=='reply' and target==str(request):
            mode='channel' # Late interleaving is checked immediately before send.
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

    def render_path(self, value):
        return self._render_artifact(value)[0]

    def _render_artifact(self, value):
        """Only bounded, decoded backend PNGs; never arbitrary caller files."""
        from PIL import Image
        from .chat_math import MAX_IMAGE_WIDTH, MAX_IMAGE_HEIGHT, MAX_IMAGE_PIXELS, MAX_PNG_BYTES

        if not isinstance(value, str) or not value:
            raise ValueError("invalid_conversation_image")
        try:
            path = Path(value).resolve(strict=True)
            if (not path.is_relative_to(self.math_render_root)
                    or path.suffix.lower() != ".png" or not path.is_file()
                    or not 8 <= path.stat().st_size <= MAX_PNG_BYTES):
                raise ValueError("invalid_conversation_image")
            with path.open("rb") as stream:
                png = stream.read(MAX_PNG_BYTES + 1)
            if not 8 <= len(png) <= MAX_PNG_BYTES or not png.startswith(bytes.fromhex("89504e470d0a1a0a")):
                raise ValueError("invalid_conversation_image")
            with Image.open(BytesIO(png)) as image:
                width, height = image.size
                if (image.format != "PNG" or not 0 < width <= MAX_IMAGE_WIDTH
                        or not 0 < height <= MAX_IMAGE_HEIGHT or width * height > MAX_IMAGE_PIXELS
                        or getattr(image, "n_frames", 1) != 1):
                    raise ValueError("invalid_conversation_image")
                image.verify()
            # Header/CRC verification alone does not prove the pixel stream decodes.
            with Image.open(BytesIO(png)) as image:
                image.load()
        except (OSError, ValueError, SyntaxError, Image.DecompressionBombError):
            raise ValueError("invalid_conversation_image") from None
        return path, png

    def queue_parts(self, channel, request, parts, scope, actor, mode="channel", target=None):
        """Queue prevalidated text/renderer-image parts without changing string content."""
        if not isinstance(parts, list) or not 1 <= len(parts) <= 32:
            raise ValueError("invalid_conversation_parts")
        validated = []
        for part in parts:
            if not isinstance(part, dict):
                raise ValueError("invalid_conversation_parts")
            if part.get("type") == "text" and isinstance(part.get("text"), str):
                if not part["text"].strip():
                    raise ValueError("invalid_conversation_parts")
                validated.append({"type": "text", "text": part["text"]})
            elif part.get("type") == "image" and isinstance(part.get("alt", ""), str):
                validated.append({"type": "image", "path": str(self.render_path(part.get("path"))),
                                  "alt": part.get("alt", "")[:1024]})
            else:
                raise ValueError("invalid_conversation_parts")
        content = "\n".join(part["text"] for part in validated if part["type"] == "text")
        with self.db.atomic():
            action = self.queue(channel, request, "reply", content, scope, actor, mode, target)
            if action:
                self.db.execute("INSERT INTO kei_conversation_parts VALUES (?,?)",
                                (action, dumps(validated)))
        return action

    def sent_ids(self, action):
        """Exact confirmed bubble IDs, including partial deliveries, in send order."""
        return [row["message"] for row in self.db.rows(
            "SELECT message FROM kei_conversation_sent WHERE action=? ORDER BY ordinal",
            (str(action),),
        )]

    @staticmethod
    def latest_message_id(channel):
        """Gateway state only; DMs have a message cache but no last_message_id."""
        latest = getattr(channel, "last_message_id", None)
        latest = int(latest) if latest and str(latest).isdigit() else 0
        state = getattr(channel, "_state", None)
        for message in reversed(getattr(state, "_messages", None) or ()):
            if str(message.channel.id) == str(channel.id):
                latest = max(latest, int(message.id))
                break
        return latest

    def _delivery_started(self, action):
        return bool(self.sent_ids(action) or self.db.one(
            "SELECT id FROM kei_social_actions WHERE id=? AND status='uncertain'", (str(action),)))

    def _delivery_uncertain(self, action):
        if action:
            self.db.execute("UPDATE kei_social_actions SET status='uncertain' WHERE id=?", (str(action),))

    async def send_bubbles(self, channel, bubbles, *, reference=None, action=None, previous=None):
        """Delivery of a completed response, not provider streaming or another inference."""
        first = str(previous.id) if previous is not None else None
        own_ids = {previous.id} if previous is not None else set()
        observed = previous.id if previous is not None else self.latest_message_id(channel)
        for index, part in enumerate(bubbles, start=1 if previous is not None else 0):
            attachment = None
            if part["type"] == "image":
                _, png = self._render_artifact(part["path"])
                attachment = discord.File(BytesIO(png),
                                          filename="formula.png", description=part.get("alt") or None)
            if previous is not None:
                latest = self.latest_message_id(channel)
                reference = (
                    previous.to_reference(fail_if_not_exists=False)
                    if latest and latest != observed and latest not in own_ids else None
                )
                observed = latest
            try:
                sent = await channel.send(
                    part.get("text"),
                    reference=reference,
                    allowed_mentions=discord.AllowedMentions.none(),
                    **({"file": attachment} if attachment else {}),
                )
            except (discord.NotFound, discord.Forbidden, PermissionError):
                raise
            except BaseException:
                self._delivery_uncertain(action)
                raise
            finally:
                if attachment:
                    attachment.close()
                    attachment.fp.close()  # discord.File does not own caller-provided BytesIO.
            if action:
                self.db.execute(
                    "INSERT INTO kei_conversation_sent VALUES (?,?,?)",
                    (action, index, str(sent.id)),
                )
            if first is None:
                first = str(sent.id)
            previous = sent
            own_ids.add(sent.id)
        return first

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

    async def request_reference(self, channel, target, actor):
        if not target or not str(target).isdigit() or not str(actor).isdigit():
            return None
        if self.db.tombstoned([str(target)]):
            raise PermissionError('report_source_forgotten')
        try:
            message = await channel.fetch_message(int(target))
        except (discord.NotFound, discord.Forbidden, discord.HTTPException):
            return None
        if (str(message.id) != str(target) or str(message.channel.id) != str(channel.id)
                or str(message.author.id) != str(actor) or getattr(message.author, 'bot', False)):
            raise PermissionError('report_origin_mismatch')
        if self.db.tombstoned([str(target)]):
            raise PermissionError('report_source_forgotten')
        return message.to_reference(fail_if_not_exists=False)

    async def deliver(self, channel, row):
        if self._delivery_started(row["id"]):
            raise ValueError("conversation_delivery_already_started")
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
        search = self.db.one('SELECT * FROM kei_search_cards WHERE channel=? AND request=? AND finished=0 AND at>?', (row['channel'],row['message'],time.time()-3600))
        if search and not self.db.one('SELECT action FROM kei_conversation_parts WHERE action=?', (row['id'],)):
            first=await self.finish_search(channel,search,row['content'])
            if first:return first
        elif search:
            # Keep ordered attachments intact rather than flattening into an edit.
            self.db.execute('UPDATE kei_search_cards SET finished=1 WHERE channel=? AND request=?', (row['channel'], row['message']))
        mode = target["mode"] if target else "reply"
        if mode == "edit" and not self.db.one("SELECT action FROM kei_conversation_parts WHERE action=?", (row["id"],)):
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
        import asyncio
        if target and target['scope'].startswith('guild:') and mode=='channel':
            if hasattr(channel,'typing'):
                async with channel.typing():await asyncio.sleep(.35)
            last=getattr(channel,'last_message_id',None)
            if last and str(last)!=str(row['message']):mode='reply';ident=row['message']
            elif self.db.one("SELECT id FROM kei_social_actions WHERE channel=? AND id!=? AND at>=? AND status IN ('pending','sending')",(row['channel'],row['id'],row['at']-30)):mode='reply';ident=row['message']
        reference = await self.reference(channel, ident) if mode != "channel" else None
        ordered = self.db.one("SELECT parts FROM kei_conversation_parts WHERE action=?", (row["id"],))
        parts = json.loads(ordered["parts"]) if ordered else [{"type": "text", "text": row["content"]}]
        if ordered:
            original = "\n".join(p["text"] for p in parts if p["type"] == "text")
            if row["content"].startswith(original):
                suffix = row["content"][len(original):]
                if suffix.strip():
                    parts.append({"type": "text", "text": suffix})
            else:
                parts = [{"type": "text", "text": row["content"]}]
        bubbles = []
        for part in parts:
            if part["type"] == "text":
                bubbles.extend({"type": "text", "text": text} for text in chat_chunks(part["text"]))
            else:
                bubbles.append(part)
        return await self.send_bubbles(channel, bubbles, reference=reference, action=row["id"])

    async def finish_search(self, channel, card, content):
        """Reuse the progress message. Split safely instead of truncating the answer."""
        parts=chunks(card['header']+'\n'+content)
        try:
            message=await channel.fetch_message(int(card['message']))
            if message.author.id!=channel._state.user.id:return None
            await message.edit(content=parts[0],allowed_mentions=discord.AllowedMentions.none())
        except (discord.NotFound,discord.Forbidden,discord.HTTPException,ValueError,TypeError):
            self.db.execute('UPDATE kei_search_cards SET finished=1 WHERE channel=? AND request=?',(card['channel'],card['request']))
            return None
        # Claim the edit before sending continuation chunks. An uncertain send must
        # never replay the entire response on restart.
        self.db.execute('UPDATE kei_search_cards SET finished=1 WHERE channel=? AND request=?',(card['channel'],card['request']))
        for part in parts[1:]:await channel.send(part,allowed_mentions=discord.AllowedMentions.none())
        return str(message.id)
