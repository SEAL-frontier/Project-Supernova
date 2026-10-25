from __future__ import annotations
import asyncio, hashlib, json, logging, re, time, uuid, os, copy
from pathlib import Path
from contextlib import asynccontextmanager
import discord
from discord import app_commands
from ..v2.application import Kei as LegacyKei
from ..v2.identity import sync_identity
from ..v2.progress import Reporter
from ..v2.store import dumps, uid
from . import VERSION
from .engine import Engine
from .bridge import Bridge
from .config import Secrets, normalize_profile, save_config
from .social import nickname, ambient_allowed, low_signal, followup_allowed, participation_candidate
from .panel import Panel
from .ux import UserExperience
from .social_policy import asks_quiet, operation
LOG = logging.getLogger('kei')

class MinecraftMessage:

    def __init__(self, destination, ident):
        self.destination = destination
        self.id = ident

    async def edit(self, content=None, embed=None, view=None, **kwargs):
        await self.destination.update_debug(str(self.id), content, embed)
        return self

    async def delete(self):
        row = self.destination.bot.store.one('SELECT * FROM kei_mc_debug_messages WHERE id=?', (str(self.id),))
        if row and row['dm_message']:
            try:
                channel = await self.destination.bot.destination(row['dm_channel'])
                await channel.get_partial_message(int(row['dm_message'])).delete()
            except discord.HTTPException:
                pass
        await self.destination.bot.bridge.progress(self.destination.server, self.destination.uuid, '')

class MinecraftDestination:

    def __init__(self, bot, channel):
        self.bot = bot
        self.id = channel
        _, self.server, self.uuid, self.visibility = channel.split(':', 3)

    async def send(self, content=None, embed=None, view=None, allowed_mentions=None, **kwargs):
        text = content or ''
        if embed:
            ident = str(int(uid(), 16))
            await self.update_debug(ident, content, embed)
            return MinecraftMessage(self, ident)
        if view and getattr(view, 'children', None):
            ident = view.children[0].custom_id.split(':')[-1]
            text += '\n/kei confirm ' + ident
        if text:
            result = await self.bot.bridge.send(self.server, self.uuid, text, self.visibility == 'public' and (not view))
            if result.get('delivered') is False:
                person = self.bot.engine.identity.resolve('minecraft', self.uuid, self.server)
                discord_id = self.bot.engine.identity.discord(person)
                if not discord_id:
                    raise ConnectionError('Minecraft player offline; reply was not delivered')
                destination = await self.bot.destination(discord_id)
                await destination.send(text, allowed_mentions=discord.AllowedMentions.none(), view=view)
        return MinecraftMessage(self, str(int(uid(), 16)))

    async def fetch_message(self, ident):
        return MinecraftMessage(self, ident)

    def get_partial_message(self, ident):
        return MinecraftMessage(self, str(ident))

    async def update_debug(self, ident, content, embed):
        description = embed.description if embed else content or ''
        brief = re.sub('```[\\s\\S]*?```', '', description).strip()[:220]
        await self.bot.bridge.progress(self.server, self.uuid, brief)
        row = self.bot.store.one('SELECT * FROM kei_mc_debug_messages WHERE id=?', (ident,))
        if not row:
            self.bot.store.execute('INSERT INTO kei_mc_debug_messages VALUES (?,?,?,?,?,?,?)', (ident, self.server, self.uuid, '', '', 0, time.time()))
            row = self.bot.store.one('SELECT * FROM kei_mc_debug_messages WHERE id=?', (ident,))
        person = self.bot.engine.identity.resolve('minecraft', self.uuid, self.server)
        discord_id = self.bot.engine.identity.discord(person)
        advanced = '```' in description
        emitted = False
        if discord_id and (advanced or row['dm_message']) and (not row['dm_blocked']):
            try:
                target = await self.bot.destination(discord_id)
                if row['dm_message']:
                    await target.get_partial_message(int(row['dm_message'])).edit(content=content or None, embed=embed, allowed_mentions=discord.AllowedMentions.none())
                else:
                    message = await target.send(content or None, embed=embed, allowed_mentions=discord.AllowedMentions.none())
                    self.bot.store.execute('UPDATE kei_mc_debug_messages SET dm_channel=?,dm_message=? WHERE id=?', (discord_id, str(message.id), ident))
            except (discord.Forbidden, discord.NotFound):
                self.bot.store.execute('UPDATE kei_mc_debug_messages SET dm_blocked=1 WHERE id=?', (ident,))
        elif advanced and time.time() - row['updated'] >= 15:
            blocks = re.findall('```(?:text)?\\n([\\s\\S]*?)```', description)
            if blocks:
                await self.bot.bridge.send(self.server, self.uuid, '\n'.join(blocks[-1].splitlines()[-2:])[-350:])
                emitted = True
        if emitted:
            self.bot.store.execute('UPDATE kei_mc_debug_messages SET updated=? WHERE id=?', (time.time(), ident))

class Kei(LegacyKei):

    def __init__(self, cfg, store, model):
        super().__init__(cfg, store, model)
        self.bridge = Bridge(store, cfg, Secrets(cfg.get('secrets_file', 'data/secrets.json')))
        self.engine = Engine(cfg, store, model, self.bridge)
        self.engine.search_observer = self.search_status
        self.ux = UserExperience(self)
        self.bridge.handler = self.minecraft_event
        self.reporter = Reporter(store, self.destination, self.engine.progress.secrets, reference_for_task=self.task_reference, can_report=self.can_report)
        self._register_commands()
        self.ux.register()
        self.ambient_last = {}
        self.direct_windows = {}
        self.followup_turns = {}
        self.channel_speakers = {}
        self.search_cards = {}
        self.typing_leases = {}
        self.engine.typing_observer = self.begin_typing
        self.engine.typing_end_observer = self.end_typing
        from .presence import DailyPresence
        self.daily_presence = DailyPresence(store, cfg, model)
        self.engine.memory.on_forget = self.invalidate_presence

    def invalidate_presence(self):
        text = getattr(self, 'last_presence_thought', None)
        if text and (not self.store.one('SELECT day FROM kei_presence_thoughts WHERE text=?', (text,))):
            self.last_presence_thought = None
            asyncio.create_task(self.change_presence(activity=discord.Game(name='Kei ' + VERSION + ' · Supernova')))

    async def configure_social_intents(self):
        try:
            info = await self.application_info()
            enabled = bool(info.flags.gateway_presence or info.flags.gateway_presence_limited)
            self._connection._intents.presences = enabled
            if enabled:
                self._connection._intents.members = bool(info.flags.gateway_guild_members or info.flags.gateway_guild_members_limited)
            self._connection.member_cache_flags = discord.MemberCacheFlags.from_intents(self._connection._intents)
            self._connection._chunk_guilds = bool(self._connection._intents.members)
        except discord.HTTPException:
            LOG.info('Presence metadata unavailable')

    async def on_presence_update(self, before, after):
        person = self.store.one("SELECT person FROM kei_accounts WHERE platform='discord' AND account=?", (str(after.id),))
        if not person:
            return
        person = person['person']
        pref = self.engine.memory.preference(person)
        if pref.get('muted'):
            return
        for row in self.store.rows('SELECT scope,data,at FROM kei_social_context WHERE person=?', (person,)):
            if time.time() - row['at'] > 1800 and (not (pref.get('dm_opt_in') and row['scope'].startswith('dm:'))):
                continue
            if not (row['scope'].startswith('dm:') or row['scope'].startswith('guild:' + str(after.guild.id) + ':')):
                continue
            data = json.loads(row['data'])
            data.update(presence=str(after.status), status_available=True, custom_status=None, observed_at=time.time())
            for activity in after.activities:
                if isinstance(activity, discord.CustomActivity):
                    data['custom_status'] = str(activity.name or activity.state or '')[:200]
            self.store.execute('UPDATE kei_social_context SET data=?,at=? WHERE person=? AND scope=?', (json.dumps(data), time.time(), person, row['scope']))

    async def monitor_loop(self):
        await self.wait_until_ready()
        consecutive = {}
        while not self.is_closed():
            for server, executor in list(self.engine.tools.items()):
                try:
                    result = await asyncio.to_thread(executor.do_inspect, 'status')
                    data = result['data']
                    resources = data.get('resources', {})
                    limit = resources.get('memory_limit_bytes', data.get('limits', {}).get('memory_limit', 0) * 1024 * 1024)
                    event = self.engine.reports.monitor_sample(server, data.get('state', 'unknown'), resources, limit)
                    consecutive[server] = 0
                    if not event:
                        continue
                    notify = str(executor.p.get('notify_user', self.cfg['owner_id']))
                    k = self.store.create_task(server, 'dm:' + notify, notify, notify, 'Kiểm tra trạng thái ' + executor.p['name'] + ' và xác định có lỗi bất thường không. Chỉ đọc; không sửa hay bật/tắt server. Kết luận bằng monitor_verdict normal/issue/unknown cùng bằng chứng.', 'observe', ['Đọc trạng thái và log mới', 'Phân biệt khởi động, dừng chủ động và lỗi thật', 'Lưu kết luận cùng bằng chứng'])
                    self.store.execute('INSERT INTO kei_report_tasks VALUES (?,?,?)', (k, 'monitor', event['key']))
                    self.engine.launch(k)
                except asyncio.CancelledError:
                    raise
                except Exception as exc:
                    consecutive[server] = consecutive.get(server, 0) + 1
                    if consecutive[server] == 2:
                        self.engine.reports.record(server, 'crash', 'monitor', 'Chưa đọc được trạng thái server (' + type(exc).__name__ + '). Chưa đủ dữ kiện để kết luận crash.', dedupe='monitor-read:' + server + ':' + str(int(time.time() // 3600)))
                    LOG.warning('Monitor sample deferred server=%s type=%s', server, type(exc).__name__)
            await asyncio.sleep(30)

    def can_report(self, task):
        if self.store.one('SELECT task FROM kei_report_tasks WHERE task=?', (task['id'],)):
            return False
        origin = self.store.one('SELECT ack FROM kei_task_origins WHERE task=?', (task['id'],))
        if not origin or not origin['ack']:
            return True
        ack = self.store.one('SELECT status FROM kei_social_actions WHERE id=?', (origin['ack'],))
        return not ack or ack['status'] not in ('pending', 'sending')

    async def task_reference(self, task, channel):
        if str(task['channel']).startswith('mc:'):
            return None
        origin = self.store.one('SELECT message FROM kei_task_origins WHERE task=?', (task['id'],))
        return await self.engine.conversation.reference(channel, origin['message']) if origin else None

    async def search_status(self, channel, request, phase, **data):
        if str(channel).startswith('mc:'):
            return
        channel, request = (str(channel), str(request))
        card = self.store.one('SELECT * FROM kei_search_cards WHERE channel=? AND request=?', (channel, request))
        if card and card['finished']:
            return
        receipts = json.loads(card['receipts']) if card else []
        for receipt in data.get('receipts', []):
            if receipt.get('url') and receipt.get('domain') and (not any((p['url'] == receipt['url'] for p in receipts))):
                receipts.append(receipt)
        if phase == 'done':
            sites = len({r['domain'] for r in receipts})
            text = '-# Searched ' + str(sites) + (' site' if sites == 1 else ' sites') if sites else '-# Search unavailable' if data.get('status') == 'error' or data.get('errors') else '-# No matching sources' if data.get('status') == 'empty' else '-# Results found · source pages unavailable'
        elif phase == 'searching':
            text = '-# Searching…'
        else:
            text = '-# Searching… ' + str(data.get('pages', 0)) + ' pages · ' + str(data.get('domain', ''))[:80]
        now = time.time()
        if card and phase not in ('done', 'searching') and (now - card['at'] < 2):
            return
        try:
            target = await self.destination(channel)
            if card:
                try:
                    await target.get_partial_message(int(card['message'])).edit(content=text, allowed_mentions=discord.AllowedMentions.none())
                except discord.NotFound:
                    card = None
            if not card:
                reference_target = request
                if request.startswith('task:'):
                    origin = self.store.one('SELECT message FROM kei_task_origins WHERE task=?', (request[5:],))
                    reference_target = origin['message'] if origin else None
                reference = await self.engine.conversation.reference(target, reference_target)
                message = await target.send(text, reference=reference, allowed_mentions=discord.AllowedMentions.none())
                card = {'message': str(message.id)}
            self.store.execute('INSERT OR REPLACE INTO kei_search_cards VALUES (?,?,?,?,?,?,0)', (channel, request, card['message'], text, json.dumps(receipts), now))
        except discord.HTTPException as exc:
            LOG.warning('Search status deferred (%s)', type(exc).__name__)

    def _register_commands(self):
        social = app_commands.Group(name='social', description='Cách Kei tương tác với bạn và channel')

        @social.command(name='dm', description='Bật/tắt Kei chủ động nhắn riêng; tối đa 3 lần/ngày, có giờ yên lặng')
        @app_commands.choices(mode=[app_commands.Choice(name='on', value='on'), app_commands.Choice(name='off', value='off')])
        async def social_dm(interaction: discord.Interaction, mode: app_commands.Choice[str]):
            person = self.engine.identity.resolve('discord', interaction.user.id)
            self.engine.memory.set_preference(person, dm_opt_in=mode.value == 'on')
            await interaction.response.send_message('DM chủ động: **' + mode.value + '**. Không trả lời thì Kei sẽ không gửi đuổi.', ephemeral=True)

        @social.command(name='timezone', description='Đặt timezone IANA của bạn cho giờ yên lặng')
        async def timezone_command(interaction: discord.Interaction, timezone: str):
            try:
                self.engine.memory.set_preference(self.engine.identity.resolve('discord', interaction.user.id), timezone=timezone)
                text = 'Đã lưu timezone ' + timezone + '.'
            except Exception:
                text = 'Timezone không hợp lệ. Ví dụ: Asia/Ho_Chi_Minh.'
            await interaction.response.send_message(text, ephemeral=True)
        self.tree.add_command(social)

        @app_commands.command(name='privacy', description='Chọn strict hoặc cho Kei gợi nhắc kín đáo giữa các ngữ cảnh')
        @app_commands.choices(mode=[app_commands.Choice(name=x, value=x) for x in ('strict', 'discreet')])
        async def privacy_command(interaction: discord.Interaction, mode: app_commands.Choice[str]):
            self.engine.memory.set_preference(self.engine.identity.resolve('discord', interaction.user.id), sharing=mode.value)
            await interaction.response.send_message('Chia sẻ ngữ cảnh: **' + mode.value + '**. Không quote DM hay tiết lộ chuyện nhạy cảm.', ephemeral=True)
        self.tree.add_command(privacy_command)

        @app_commands.command(name='link', description='Lấy mã nối Discord với Minecraft; mã chỉ hiện riêng cho bạn')
        async def link(interaction: discord.Interaction, server: str=''):
            code = self.engine.identity.issue(interaction.user.id, server)
            await interaction.response.send_message('Login Minecraft rồi nhập `/kei link ' + code + '`. Mã dùng một lần, hết hạn sau 10 phút. Link không tự cấp quyền server mới.', ephemeral=True)
        self.tree.add_command(link)

        @app_commands.command(name='unlink', description='Gỡ link Minecraft và quyền copilot kế thừa từ Discord')
        async def unlink(interaction: discord.Interaction, server: str=''):
            count = self.engine.identity.unlink(interaction.user.id, server or None)
            await interaction.response.send_message('Đã gỡ ' + str(count) + ' liên kết Minecraft.', ephemeral=True)
        self.tree.add_command(unlink)
        memory = app_commands.Group(name='memory', description='Xem hoặc quên memory của chính bạn')

        @memory.command(name='show', description='Xem memory đã lưu, chỉ hiện riêng cho bạn')
        async def memory_show(interaction: discord.Interaction):
            person = self.engine.identity.resolve('discord', interaction.user.id)
            rows = self.store.rows('SELECT id,kind,content FROM kei_memories WHERE person=? AND active=1 ORDER BY at DESC LIMIT 20', (person,))
            self.store.execute('INSERT OR REPLACE INTO kei_meta VALUES (?,?)', ('memory-view:' + str(interaction.user.id), dumps([r['id'] for r in rows])))
            from .memory import unpack
            text = '\n'.join((str(i + 1) + '. ' + r['kind'] + ': ' + unpack(r['content'])['text'][:180] for i, r in enumerate(rows))) or 'Chưa có memory cá nhân đã chọn lưu.'
            await interaction.response.send_message(text[:1900] + '\nDùng `/memory forget` để quên một mục hoặc cả phạm vi.', ephemeral=True)

        @memory.command(name='forget', description='Quên mục đã xem, hoặc toàn bộ memory trong scope/all')
        @app_commands.choices(scope=[app_commands.Choice(name=x, value=x) for x in ('current', 'all')])
        async def memory_forget(interaction: discord.Interaction, scope: app_commands.Choice[str], index: int=0):
            selected = None
            if index:
                saved = self.store.one('SELECT value FROM kei_meta WHERE key=?', ('memory-view:' + str(interaction.user.id),))
                ids = json.loads(saved['value']) if saved else []
                if index < 1 or index > len(ids):
                    await interaction.response.send_message('Dùng /memory show rồi chọn số mục hợp lệ.', ephemeral=True)
                    return
                selected = [ids[index - 1]]
            current = 'dm:' + str(interaction.user.id) if not interaction.guild_id else 'guild:' + str(interaction.guild_id) + ':' + str(interaction.channel_id)
            self.engine.memory.forget(str(interaction.user.id), None if scope.value == 'all' else current, selected)
            await interaction.response.send_message('Đã quên dữ liệu và phần dẫn xuất liên quan.', ephemeral=True)
        self.tree.add_command(memory)
        servers = app_commands.Group(name='server', description='Xem, kết nối và cấp quyền Minecraft server')

        @servers.command(name='list', description='Xem server và capability bạn được sử dụng')
        async def server_list(interaction: discord.Interaction):
            ids = self.engine.assigned(str(interaction.user.id))
            text = '\n'.join((self.engine.servers[s]['name'] + ' (`' + s + '`): ' + ', '.join(self.engine.tools[s].capabilities()) for s in ids))
            await interaction.response.send_message(text[:1800] or 'Chưa được assign server; bạn vẫn chat bình thường được.', ephemeral=True)

        @servers.command(name='grant', description='Owner server: cấp chat, observe hoặc copilot cho một người')
        @app_commands.choices(level=[app_commands.Choice(name=x, value=x) for x in ('chat', 'observe', 'copilot')])
        async def server_grant(interaction: discord.Interaction, server: str, user: discord.User, level: app_commands.Choice[str]):
            try:
                self.engine.grant(str(interaction.user.id), str(user.id), server, level.value)
                text = 'Đã lưu quyền ' + level.value + ' trên ' + server + '.'
            except Exception as exc:
                text = str(exc)
            await interaction.response.send_message(text, ephemeral=True)

        @servers.command(name='connect', description='Owner: kết nối Panel bằng wizard riêng tư')
        async def server_connect(interaction: discord.Interaction):
            if str(interaction.user.id) != self.cfg['owner_id'] and (not self.cfg.get('allow_self_service', False)):
                await interaction.response.send_message('Operator cần bật self-service hoặc thêm server bằng keys-keys server add.', ephemeral=True)
                return
            await interaction.response.send_modal(PanelConnect(self))
        self.tree.add_command(servers)

        @app_commands.command(name='setup', description='Claim owner bằng mã một lần từ terminal khi cài mới')
        async def claim(interaction: discord.Interaction, code: str):
            expected = self.cfg.get('owner_claim_hash')
            valid = expected and hashlib.sha256(code.strip().encode()).hexdigest() == expected and (self.cfg['owner_id'] == '0')
            if valid:
                owner = str(interaction.user.id)
                self.cfg['owner_id'] = owner
                self.cfg.pop('owner_claim_hash', None)
                for p in self.cfg['servers']:
                    if p.get('owners') == ['0']:
                        p['owners'] = [owner]
                        self.cfg['assignments'].setdefault(owner, [])
                        if p['id'] not in self.cfg['assignments'][owner]:
                            self.cfg['assignments'][owner].append(p['id'])
                        self.store.execute('INSERT OR IGNORE INTO kei_assignments VALUES (?,?)', (owner, p['id']))
                save_config(self.cfg, self.cfg['_path'])
                self.engine.refresh_servers()
            await interaction.response.send_message('Đã nhận owner. Dùng /server connect để thêm server.' if valid else 'Mã sai, hết hiệu lực hoặc bot đã có owner.', ephemeral=True)
        self.tree.add_command(claim)

    async def on_interaction(self, interaction):
        if interaction.type == discord.InteractionType.application_command:
            name = (interaction.data or {}).get('name', 'unknown')
            if name not in {c.name for c in self.tree.get_commands()}:
                name = 'unknown'
            LOG.info('SLASH_RECEIVED command=%s', name)
        await super().on_interaction(interaction)

    async def setup_hook(self):
        await self.configure_social_intents()
        for task in self.store.rows("SELECT * FROM kei_tasks WHERE status='waiting' AND pending IS NOT NULL"):
            try:
                pending = json.loads(task['pending'])
            except (TypeError, ValueError):
                continue
            if pending.get('approval_for') == 'owner':
                pending.pop('approval_for', None)
                pending.pop('approved_by', None)
                pending['confirmed'] = False
                self.store.update_task(task['id'], pending=dumps(pending))
                self.store.queue(task['channel'], '**Approval needed**\n-# This pending change now needs confirmation from the person who started the task.', confirm_task=task['id'])
        await super().setup_hook()
        await self.bridge.start()
        await self.ux.start()
        self.bg.extend([asyncio.create_task(self.sync_commands()), asyncio.create_task(self.social_outbox()), asyncio.create_task(self.social_background()), asyncio.create_task(self.scheduler_loop())])

    async def sync_commands(self):
        await self.wait_until_ready()
        try:
            for command in self.tree.get_commands():
                await self.http.upsert_global_command(self.application_id, command.to_dict(self.tree))
            LOG.info('SLASH_REGISTRATION_COMPLETE count=%s', len(self.tree.get_commands()))
        except discord.HTTPException as exc:
            LOG.warning('Command registration deferred: %s', type(exc).__name__)

    async def on_ready(self):
        await super().on_ready()
        await self.change_presence(activity=discord.Game(name='Kei ' + VERSION + ' · Supernova'))
        LOG.info('KEI_READY version=%s bot_id=%s model=%s servers=%s presence=%s member_cache=%s cached_members=%s', VERSION, self.user.id, self.engine.model.model, ','.join(self.engine.servers), self.intents.presences, self._connection.member_cache_flags.joined, sum((len(g.members) for g in self.guilds)))

    def mark_exchange(self, channel, actor, message=None):
        key = (str(channel), str(actor))
        now = time.time()
        meta = self.store.one('SELECT addressed FROM kei_event_meta WHERE message=?', (str(message),)) if message else None
        if self.direct_windows.get(key, 0) <= now or (meta and meta['addressed'] == 1):
            self.followup_turns[key] = 0
        self.direct_windows[key] = now + int(self.cfg['social'].get('followup_seconds', 90))

    async def on_message(self, message):
        if message.author.bot or message.webhook_id:
            return
        channel = str(message.channel.id)
        user = str(message.author.id)
        guild = message.guild
        scope = 'dm:' + user if guild is None else 'guild:' + str(guild.id) + ':' + channel
        person = self.engine.identity.resolve('discord', user)
        aliases = self.cfg['social'].get('triggers', ['kei']) + [r['alias'] for r in self.store.rows("SELECT alias FROM kei_aliases WHERE person=? AND (?='discreet' OR scope=?) AND NOT EXISTS (SELECT 1 FROM json_each(kei_aliases.sources) s JOIN kei_forget_tombstones f ON f.source=s.value)", (person, self.engine.memory.preference(person)['sharing'], scope))]
        from .social_runtime import names as call_names, capture as capture_environment
        manual_names = call_names(self.store, person)
        aliases += manual_names
        named = bool(nickname(message.content, self.cfg['social'].get('triggers', ['kei'])))
        learned = bool(nickname(message.content, [a for a in aliases if a not in self.cfg['social'].get('triggers', ['kei'])]))
        strong = guild is None or self.user in message.mentions or named or bool(nickname(message.content, manual_names)) or message.content.startswith('kei!')
        direct = guild is None or self.user in message.mentions or bool(nickname(message.content, aliases)) or message.content.startswith('kei!')
        to_other = False
        if message.reference:
            ref = message.reference.resolved
            if not isinstance(ref, discord.Message):
                try:
                    ref = await message.channel.fetch_message(message.reference.message_id)
                except discord.HTTPException:
                    ref = None
            strong = strong or bool(ref and ref.author.id == self.user.id)
            direct = direct or bool(ref and ref.author.id == self.user.id)
            to_other = bool(ref and ref.author.id != self.user.id)
        now = time.time()
        previous_speaker = self.channel_speakers.get(channel)
        self.channel_speakers[channel] = user
        if strong:
            self.direct_windows[channel, user] = now + self.cfg['social'].get('followup_seconds', 90)
            self.followup_turns[channel, user] = 0
        last = self.store.one("SELECT content FROM kei_messages WHERE scope=? AND user=? AND role='assistant' AND forgotten=0 ORDER BY at DESC LIMIT 1", (scope, user))
        turn_limit = int(self.cfg['social'].get('followup_turn_limit', 4))
        recent_exchange = self.followup_turns.get((channel, user), 0) < turn_limit and self.direct_windows.get((channel, user), 0) > now and (not to_other)
        if not direct and recent_exchange and low_signal(message.content) and (not self.engine.quiet.active(scope, person)):
            if self.store.seen(message.id):
                return
            self.store.add_message(scope, user, 'user', message.content, str(message.id))
            self.engine.conversation.queue(channel, str(message.id), 'react', '👍' if message.content.casefold().strip(' .!') in ('ok', 'okay', 'oke', 'ừ', 'yes') else '👀', scope, user, 'reply')
            self.followup_turns[channel, user] = self.followup_turns.get((channel, user), 0) + 1
            return
        following = self.followup_turns.get((channel, user), 0) < turn_limit and self.direct_windows.get((channel, user), 0) > now and followup_allowed(message.content, to_other=to_other, answering=bool(last and '?' in last['content']))
        if not direct and (not to_other) and (message.content.lower().strip(' .!') in ('ừ', 'ừ làm đi', 'ok', 'okay', 'yes', 'làm đi', 'xác nhận', 'đồng ý')):
            following = following or len(self.store.rows("SELECT id FROM kei_tasks WHERE requester=? AND scope=? AND status='waiting'", (user, scope))) == 1
        if not (direct or following):
            return
        weak_reason = 'nickname' if learned and (not strong) else 'followup' if following and (not strong) else 'direct'
        if not strong and weak_reason == 'nickname' and (not operation(message.content)) and (not participation_candidate(message.id, weak_reason, self.engine.memory.relationship(person, scope))):
            return
        if following and (not direct):
            self.followup_turns[channel, user] = self.followup_turns.get((channel, user), 0) + 1
        member = message.author
        if guild is None:
            member = next((g.get_member(message.author.id) for g in self.guilds if g.get_member(message.author.id)), message.author)
        capture_environment(self.store, person, scope, member, message.channel, available=bool(self.intents.presences))
        if guild:
            restricted = not message.channel.permissions_for(guild.default_role).view_channel
            self.store.execute('INSERT OR REPLACE INTO kei_meta VALUES (?,?)', ('scope-visibility:' + scope, 'restricted' if restricted else 'group'))
        self.following[channel, user] = time.time() + 90
        await super().on_message(message)
        if self.store.one('SELECT id FROM kei_messages WHERE id=?', (str(message.id),)):
            self.store.execute('INSERT OR REPLACE INTO kei_event_meta VALUES (?,?,?,?,?,?,?,?,?)', (str(message.id), 'discord', person, user, '', scope, channel, 1 if strong else 3 if learned else 2 if following else 0, time.time()))

    async def begin_typing(self, channel, request):
        if str(channel).startswith('mc:'):
            return
        key = (str(channel), str(request))
        if key in self.typing_leases:
            return

        async def pulse():
            try:
                await asyncio.sleep(0.9)
                while True:
                    await self.http.send_typing(int(channel))
                    await asyncio.sleep(7)
            except asyncio.CancelledError:
                raise
            except discord.HTTPException:
                pass
        self.typing_leases[key] = asyncio.create_task(pulse())

    def end_typing(self, channel, request):
        job = self.typing_leases.pop((str(channel), str(request)), None)
        if job:
            job.cancel()

    @asynccontextmanager
    async def conversation_typing(self, channel, scope, user):
        yield

    async def flush(self, key):
        while key in self.buffers:
            batch = self.buffers[key]
            text = ' '.join((t for _, t in batch['messages'])).strip()
            unfinished = bool(re.search('(?:\\.\\.\\.|…|nên là|của|nó học|học cách|vì|because|so|and|but)\\s*$', text, re.I))
            remaining = min((2.8 if unfinished else 1.6) - (time.monotonic() - batch['last']), 8 - (time.monotonic() - batch['first']))
            if remaining > 0:
                await asyncio.sleep(min(remaining, 0.2))
                continue
            self.buffers.pop(key)
            channel = batch['channel']
            ids = [i for i, _ in batch['messages']]
            try:
                await self.engine.conversation.capture(channel, key[0], batch['user'], ids)
                async with self.conversation_typing(channel, key[0], batch['user']):
                    await self.engine.converse(batch['user'], key[0], str(channel.id), '\n'.join((t for _, t in batch['messages'])), ids)
                if not self.store.one("SELECT id FROM kei_social_actions WHERE channel=? AND message=? AND kind IN ('reply','short_reply') AND status IN ('pending','sending')", (str(channel.id), ids[-1])):
                    self.end_typing(str(channel.id), ids[-1])
            except Exception as exc:
                # The public conversation schema already persists exact delivery
                # provenance. Pending/uncertain replies must not be replayed, and
                # only a real social_sent receipt counts as confirmed delivery.
                reply = self.store.one(
                    "SELECT a.id,a.status FROM kei_social_actions a "
                    "JOIN kei_delivery_targets t ON t.action=a.id "
                    "WHERE a.channel=? AND a.message IN (" + ','.join('?' for _ in ids) + ") "
                    "AND t.scope=? AND t.actor=? AND a.kind IN ('reply','short_reply') "
                    "AND (a.status IN ('pending','sending','uncertain') "
                    "OR EXISTS (SELECT 1 FROM kei_social_sent s WHERE s.action=a.id)) "
                    "ORDER BY a.at DESC LIMIT 1",
                    (str(channel.id), *map(str, ids), key[0], str(batch['user'])),
                )
                if reply:
                    LOG.warning('CONVERSATION_POSTPROCESSING_FAILED error=%s action=%s delivery=%s',
                                type(exc).__name__, reply['id'], reply['status'])
                    if reply['status'] not in ('pending', 'sending'):
                        self.end_typing(str(channel.id), ids[-1])
                    continue
                LOG.warning('CONVERSATION_FAILED error=%s', type(exc).__name__)
                self.end_typing(str(channel.id), ids[-1])
                self.engine.conversation.queue(str(channel.id), ids[-1], 'reply', 'Kei bị lỗi xử lý lượt này rồi. Nhắn lại giúp em một lần nhé.', key[0], batch['user'])

    async def command(self, message, scope, text):
        if text.split()[0] in ('kei!clear', 'kei!clearall'):
            if text.startswith('kei!clearall'):
                if str(message.author.id) != self.cfg['owner_id']:
                    self.store.queue(message.channel.id, 'Chỉ owner dùng clearall.')
                    return True
                for row in self.store.rows('SELECT account FROM kei_accounts WHERE platform=?', ('discord',)):
                    self.engine.memory.forget(row['account'])
            else:
                self.engine.memory.forget(str(message.author.id), scope)
            self.store.queue(message.channel.id, 'Đã quên memory và ngữ cảnh dẫn xuất.')
            return True
        return await super().command(message, scope, text)

    async def destination(self, channel):
        if str(channel).startswith('mc:'):
            return MinecraftDestination(self, str(channel))
        return await super().destination(channel)

    async def task_typing_loop(self):
        await self.wait_until_ready()
        while not self.is_closed():
            for row in self.store.rows("SELECT DISTINCT channel FROM kei_tasks WHERE status='running'"):
                if row['channel'].startswith('mc:'):
                    continue
                try:
                    await self.http.send_typing(int(row['channel']))
                except Exception:
                    pass
            await asyncio.sleep(7)

    async def maintenance(self):
        await self.wait_until_ready()
        while not self.is_closed():
            for p in self.attachment_dir.iterdir():
                if p.is_file() and time.time() - p.stat().st_mtime > 86400:
                    p.unlink()
            self.store.execute('DELETE FROM kei_inbox WHERE at<?', (time.time() - 7 * 86400,))
            await asyncio.sleep(300)

    async def update_daily_presence(self):
        thought = await self.daily_presence.choose()
        if thought and thought != getattr(self, 'last_presence_thought', None):
            await self.change_presence(activity=discord.CustomActivity(name=thought))
            self.last_presence_thought = thought
            self.store.execute('UPDATE kei_presence_thoughts SET delivered=? WHERE text=?', (time.time(), thought))
        elif not thought and getattr(self, 'last_presence_thought', None):
            await self.change_presence(activity=discord.Game(name='Kei ' + VERSION + ' · Supernova'))
            self.last_presence_thought = None

    async def social_background(self):
        await self.wait_until_ready()
        await asyncio.sleep(20)
        while not self.is_closed():
            for job in (self.update_daily_presence, self.engine.proactive, self.engine.social_maintenance):
                try:
                    await job()
                except asyncio.CancelledError:
                    raise
                except Exception as exc:
                    LOG.warning('Social background deferred job=%s type=%s', job.__name__, type(exc).__name__)
            await asyncio.sleep(300)

    async def rank_notifications(self):
        return

    async def outbox_loop(self):
        await self.wait_until_ready()
        while not self.is_closed():
            rows = self.store.rows("SELECT * FROM kei_outbox WHERE status='pending' ORDER BY at,rowid LIMIT 15")
            for row in rows:
                origin = self.store.one('SELECT o.ack FROM kei_task_outbox m JOIN kei_task_origins o ON o.task=m.task WHERE m.outbox=?', (row['id'],))
                if origin and origin['ack']:
                    ack = self.store.one('SELECT status FROM kei_social_actions WHERE id=?', (origin['ack'],))
                    if ack and ack['status'] in ('pending', 'sending'):
                        continue
                self.store.execute("UPDATE kei_outbox SET status='sending',attempts=attempts+1 WHERE id=? AND status='pending'", (row['id'],))
                try:
                    channel = await self.destination(row['channel'])
                    view = None
                    reference = None
                    if row.get('confirm_task'):
                        view = discord.ui.View(timeout=None)
                        view.add_item(discord.ui.Button(label='Xác nhận bước này', style=discord.ButtonStyle.danger, custom_id='kei-confirm:' + row['confirm_task']))
                    task = self.store.one('SELECT o.* FROM kei_task_outbox m JOIN kei_task_origins o ON o.task=m.task WHERE m.outbox=?', (row['id'],))
                    if task:
                        self.mark_exchange(row['channel'], task['actor'])
                    if task and (not row['channel'].startswith('mc:')):
                        reference = await self.engine.conversation.request_reference(channel, task['message'], task['actor'])
                        if self.store.tombstoned([task['message']]):
                            raise PermissionError('report_source_forgotten')
                    if task:
                        current = self.store.one('SELECT status FROM kei_tasks WHERE id=?', (task['task'],))
                        gate = getattr(self.engine, 'service_authorize', None)
                        permitted = bool(await gate(task['actor'], task['scope'], 'report')) if gate else True
                        current = self.store.one('SELECT status FROM kei_tasks WHERE id=?', (task['task'],))
                        if not permitted or not current or current['status'] == 'cancelled' or self.store.tombstoned([task['message']]):
                            raise PermissionError('report_context_unavailable')
                    prior_sent = self.store.one("SELECT b.id FROM kei_task_outbox m JOIN kei_outbox b ON b.id=m.outbox WHERE m.task=? AND b.status='sent' LIMIT 1", (task['task'],)) if task else None
                    extra = {'reference': reference, 'mention_author': not bool(prior_sent)} if reference else {}
                    search = self.store.one("SELECT c.* FROM kei_search_cards c JOIN kei_task_outbox o ON c.request='task:'||o.task WHERE o.outbox=? AND c.finished=0 AND c.at>?", (row['id'], time.time() - 3600)) if not view else None
                    edited = await self.engine.conversation.finish_search(channel, search, row['content']) if search and not reference else None
                    if edited:
                        sent = type('EditedSearch', (), {'id': edited})()
                    else:
                        sent = await channel.send(row['content'], allowed_mentions=discord.AllowedMentions.none(), view=view, **extra)
                    self.store.execute("UPDATE kei_outbox SET status='sent',message=? WHERE id=?", (str(sent.id), row['id']))
                except (discord.Forbidden, discord.NotFound, PermissionError):
                    self.store.execute("UPDATE kei_outbox SET status='failed' WHERE id=?", (row['id'],))
                except Exception as exc:
                    self.store.execute("UPDATE kei_outbox SET status='uncertain' WHERE id=?", (row['id'],))
                    LOG.warning('Outbox delivery uncertain (%s)', type(exc).__name__)
            await asyncio.sleep(0.5 if rows else 1)

    async def social_outbox(self):
        await self.wait_until_ready()
        while not self.is_closed():
            for row in self.store.rows("SELECT * FROM kei_social_actions WHERE status='pending' ORDER BY at LIMIT 10"):
                self.store.execute("UPDATE kei_social_actions SET status='sending' WHERE id=?", (row['id'],))
                try:
                    channel = await self.destination(row['channel'])
                    if not row['channel'].startswith('mc:'):
                        if row['kind'] in ('reply', 'short_reply'):
                            try:
                                await self.http.send_typing(int(row['channel']))
                            except discord.HTTPException:
                                pass
                        try:
                            sent = await self.engine.conversation.deliver(channel, row)
                        finally:
                            self.end_typing(row['channel'], row['message'])
                        if sent and row['kind'] in ('reply', 'short_reply'):
                            recipient = self.store.one('SELECT actor FROM kei_delivery_targets WHERE action=?', (row['id'],))
                            if recipient:
                                self.mark_exchange(row['channel'], recipient['actor'], row['message'])
                        if sent:
                            self.store.execute('INSERT OR REPLACE INTO kei_social_sent VALUES (?,?)', (row['id'], str(sent)))
                            schedules = self.store.rows("SELECT id,owner FROM kei_schedules WHERE status='pending' AND request_message=?", (row['message'],))
                            for scheduled in schedules:
                                self.engine.scheduler.bind_confirmation(scheduled['owner'], scheduled['id'], str(sent))
                            if schedules:
                                try:
                                    await channel.get_partial_message(int(sent)).add_reaction('🕒')
                                except discord.HTTPException:
                                    pass
                    else:
                        await channel.send(row['content'], allowed_mentions=discord.AllowedMentions.none())
                    self.store.execute("UPDATE kei_social_actions SET status='sent' WHERE id=?", (row['id'],))
                    for notice in self.store.rows('SELECT notice FROM kei_rank_actions WHERE action=?', (row['id'],)):
                        self.engine.memory.relationships.delivered(notice['notice'])
                except (discord.Forbidden, discord.NotFound):
                    self.store.execute("UPDATE kei_social_actions SET status='failed' WHERE id=?", (row['id'],))
                except Exception as exc:
                    self.store.execute("UPDATE kei_social_actions SET status='uncertain' WHERE id=?", (row['id'],))
                    LOG.warning('Social delivery uncertain (%s)', type(exc).__name__)
                state = self.store.one('SELECT status FROM kei_social_actions WHERE id=?', (row['id'],))
            await asyncio.sleep(1)

    async def scheduler_loop(self):
        await self.wait_until_ready()
        while not self.is_closed():
            try:
                await self.engine.scheduler.tick()
            except Exception as exc:
                LOG.warning('Scheduler tick deferred (%s)', type(exc).__name__)
            await asyncio.sleep(15)

    async def on_raw_reaction_add(self, payload):
        if self.user and payload.user_id == self.user.id:
            return
        if str(payload.emoji) not in ('🕒', '⏰'):
            return
        try:
            schedules = self.engine.scheduler.confirm_message(str(payload.user_id), str(payload.message_id))
            if not schedules:
                return
            channel = await self.destination(str(payload.channel_id))
            for scheduled in schedules:
                target = scheduled.get('ack_message')
                if target:
                    try:
                        message = await channel.fetch_message(int(target))
                        if message.author.id == self.user.id:
                            base = '\n'.join((line for line in message.content.splitlines() if not line.startswith('-#')))
                            await message.edit(content=(base + '\n\n-# ✓ Đã tạo lịch · ' + scheduled['timezone']).strip(), allowed_mentions=discord.AllowedMentions.none())
                    except discord.HTTPException:
                        pass
                try:
                    await channel.get_partial_message(payload.message_id).add_reaction('✅')
                except discord.HTTPException:
                    pass
        except (ValueError, PermissionError) as exc:
            LOG.info('Schedule confirmation rejected (%s)', type(exc).__name__)

    async def minecraft_event(self, data):
        server = data['server']
        actor = str(uuid.UUID(data['uuid']))
        user = 'mc:' + server + ':' + actor
        person = self.engine.identity.resolve('minecraft', actor, server)
        authenticated = bool(data.get('authenticated'))
        channel = 'mc:' + server + ':' + actor + (':public' if data.get('public') else ':private')
        if authenticated:
            self.store.execute('INSERT OR REPLACE INTO kei_meta VALUES (?,?)', ('mc-auth:' + server + ':' + actor, str(time.time())))
        if authenticated and data.get('discord_id') and str(data['discord_id']).isdigit():
            existing = self.engine.identity.discord(person)
            if existing in (None, str(data['discord_id'])):
                code = self.engine.identity.issue(str(data['discord_id']), server)
                person = self.engine.identity.redeem(code, server, actor, True)
        command = data.get('command', 'chat')
        text = str(data.get('message', ''))[:12000]
        if command == 'link':
            try:
                self.engine.identity.redeem(text, server, actor, authenticated)
                reply = 'Đã link Discord. Quyền server được kế thừa đúng assignment.'
            except Exception as exc:
                reply = str(exc)
            await self.bridge.send(server, actor, reply)
            return
        if command == 'confirm':
            try:
                if not authenticated:
                    raise PermissionError('Login trước khi xác nhận.')
                task = self.store.one('SELECT server FROM kei_tasks WHERE id=?', (text.strip(),))
                if not task or task['server'] != server:
                    raise PermissionError('Task không thuộc server Minecraft hiện tại.')
                await self.engine.control(self.engine.subject(user), {'action': 'confirm', 'task_id': text.strip()})
                reply = 'Đã nhận xác nhận đúng bước.'
            except Exception as exc:
                reply = str(exc)
            await self.bridge.send(server, actor, reply)
            return
        if command == 'debug':
            try:
                if not authenticated:
                    raise PermissionError('Login trước khi đổi debug.')
                self.engine.progress.set_mode(self.engine.subject(user), text.strip())
                reply = 'Debug: ' + text.strip()
            except Exception as exc:
                reply = str(exc)
            await self.bridge.send(server, actor, reply)
            return
        if command in ('privacy', 'persona', 'dm', 'unlink'):
            try:
                if not authenticated:
                    raise PermissionError('Login Minecraft/AuthMe trước khi đổi thiết lập.')
                if command == 'privacy':
                    self.engine.memory.set_preference(person, sharing=text.strip())
                    reply = 'Privacy: ' + text.strip()
                elif command == 'persona':
                    from ..v2.persona import set_mode
                    set_mode(self.store, self.engine.subject(user), text.strip())
                    reply = 'Persona: ' + text.strip()
                elif command == 'dm':
                    if not self.engine.identity.discord(person):
                        raise ValueError('Link Discord trước để bật DM chủ động.')
                    if text.strip() not in ('on', 'off'):
                        raise ValueError('/kei dm on|off')
                    self.engine.memory.set_preference(person, dm_opt_in=text.strip() == 'on')
                    reply = 'DM chủ động: ' + text.strip()
                else:
                    discord = self.engine.identity.discord(person)
                    if not discord:
                        raise ValueError('Chưa link Discord.')
                    self.engine.identity.unlink(discord, server)
                    reply = 'Đã gỡ link Minecraft trên server này.'
            except Exception as exc:
                reply = str(exc)
            await self.bridge.send(server, actor, reply)
            return
        ident = 'mc-' + server + '-' + str(data.get('id') or uid())
        if self.store.seen(ident):
            return
        scope = 'mc:' + server if data.get('public') else 'mc-private:' + server + ':' + actor
        self.store.execute('INSERT OR REPLACE INTO kei_users VALUES (?,?,?,?,?)', (user, str(data.get('name', 'player')), None, str(data.get('name', 'player')), 0))
        self.store.add_message(scope, user, 'user', text, ident)
        self.store.execute('INSERT OR REPLACE INTO kei_event_meta VALUES (?,?,?,?,?,?,?,?,?)', (ident, 'minecraft', person, actor, server, scope, channel, 1, time.time()))
        try:
            await self.engine.converse(user, scope, channel, text, [ident])
        except Exception as exc:
            await self.bridge.send(server, actor, 'Kei chưa xử lý được (' + type(exc).__name__ + '); chưa xác nhận thao tác nào hoàn tất.')
            LOG.warning('Minecraft turn failed (%s)', type(exc).__name__)

    async def close(self):
        leases = list(self.typing_leases.values())
        for lease in leases:
            lease.cancel()
        if leases:
            await asyncio.gather(*leases, return_exceptions=True)
        self.typing_leases.clear()
        await self.ux.close()
        await self.bridge.close()
        await super().close()

class PanelConnect(discord.ui.Modal, title='Kết nối Minecraft Panel'):
    url = discord.ui.TextInput(label='Panel URL', placeholder='https://panel.example.com', max_length=300)
    token = discord.ui.TextInput(label='Client API key (không phải Wings token)', min_length=10, max_length=300)

    def __init__(self, bot):
        super().__init__()
        self.bot = bot

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True, thinking=True)
        try:
            if str(interaction.user.id) != self.bot.cfg['owner_id'] and (not self.bot.cfg.get('allow_self_service', False)):
                raise PermissionError('Server registration permission changed.')
            secrets = Secrets(self.bot.cfg.get('secrets_file', 'data/secrets.json'))
            ref = secrets.put('panel-' + uid(), str(self.token))
            profile = {'url': str(self.url).rstrip('/'), 'token': ref}
            panel = Panel(profile, secrets)
            try:
                rows = await asyncio.to_thread(panel.servers)
            finally:
                panel.close()
            if not rows:
                raise ValueError('Account chưa truy cập server nào.')
            view = discord.ui.View(timeout=180)
            select = discord.ui.Select(placeholder='Chọn server để kết nối', options=[discord.SelectOption(label=str(r['name'])[:100], value=str(i)) for i, r in enumerate(rows[:25])])

            async def picked(event):
                if event.user.id != interaction.user.id:
                    await event.response.send_message('Wizard này của người khác.', ephemeral=True)
                    return
                r = rows[int(select.values[0])]
                matched = next((p for p in self.bot.engine.servers.values() if p.get('uuid') == r['uuid'] or p.get('connectors', {}).get('panel', {}).get('server') == r['uuid']), None)
                sid = matched['id'] if matched else re.sub('[^a-z0-9-]', '-', str(r['name']).casefold()).strip('-')[:30] + '-' + r['uuid'][:8]
                p = copy.deepcopy(matched) if matched else {'id': sid, 'name': r['name'], 'uuid': r['uuid'], 'connectors': {}, 'owners': [str(event.user.id)]}
                p.setdefault('connectors', {})['panel'] = {**profile, 'server': r['uuid']}
                existing = self.bot.store.one('SELECT owner FROM kei_registered_servers WHERE id=?', (sid,))
                if existing and existing['owner'] != str(event.user.id) and (str(event.user.id) != self.bot.cfg['owner_id']):
                    raise PermissionError('Server đã có owner trong registry.')
                self.bot.store.execute('INSERT OR REPLACE INTO kei_registered_servers VALUES (?,?,?,?)', (sid, dumps(p), str(event.user.id), time.time()))
                self.bot.store.execute('INSERT OR REPLACE INTO kei_grants VALUES (?,?,?,?)', (str(event.user.id), sid, 'copilot', str(event.user.id)))
                self.bot.engine.refresh_servers()
                await event.response.edit_message(content='Đã kết nối **' + r['name'] + '**. Dùng /server list hoặc nhờ Kei kiểm tra server.', view=None)
            select.callback = picked
            view.add_item(select)
            await interaction.followup.send('Key chỉ lưu riêng trên host. Chọn một server:', view=view, ephemeral=True)
        except Exception as exc:
            await interaction.followup.send('Kết nối chưa xong: ' + type(exc).__name__ + '. Dùng keys-keys doctor để xem hướng sửa; không gửi key vào chat.', ephemeral=True)
