"""Real public command payload and ephemeral-menu regressions; no network."""
import asyncio
import copy
from types import SimpleNamespace
from unittest.mock import AsyncMock

import discord
import pytest

from minecraft_agent.v3.application import Kei
from minecraft_agent.v3.config import DEFAULTS
from minecraft_agent.v3.store import Store


@pytest.fixture
def bot(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    cfg = copy.deepcopy(DEFAULTS)
    cfg.update(owner_id='200', persona='Synthetic character.', provider_key='',
               discord_token='', timezone='UTC', _path=str(tmp_path / 'kei.yaml'),
               secrets_file=str(tmp_path / 'secrets.json'))
    db = Store(':memory:')
    app = Kei(cfg, db, SimpleNamespace(model='offline'))
    yield app
    db.db.close()


def payloads(bot):
    return [command.to_dict(bot.tree) for command in bot.tree.get_commands()]


def assert_compact(rows):
    assert sorted((row['name'], row.get('options', [])) for row in rows) == [('server', []), ('settings', [])]


def test_actual_public_tree_publishes_only_two_optionless_commands(bot):
    assert_compact(payloads(bot))


def test_startup_and_ready_registration_preserve_other_integrations(bot):
    async def exercise():
        sent, removed = [], []
        class HTTP:
            async def upsert_global_command(self, app, payload): sent.append(payload)
            async def get_global_commands(self, app):
                return [{'name': 'debug', 'id': '11'}, {'name': 'plugin', 'id': '12'}, {'name': 'server', 'id': '13'}]
            async def delete_global_command(self, app, ident): removed.append(('global', ident))
            async def get_guild_commands(self, app, guild):
                return [{'name': 'server', 'id': '21'}, {'name': 'setup', 'id': '22'}, {'name': 'bridge', 'id': '23'}]
            async def delete_guild_command(self, app, guild, ident): removed.append((guild, ident))
        bot.http = HTTP()
        bot._connection.application_id = 123
        bot._connection._guilds = {456: SimpleNamespace(id=456)}
        bot.configure_social_intents = AsyncMock()
        bot.bridge.start = AsyncMock()
        bot.ux.start = AsyncMock()
        bot.wait_until_ready = AsyncMock()
        parked = asyncio.Event()
        async def idle(): await parked.wait()
        for name in ('outbox_loop', 'monitor_loop', 'maintenance', 'task_typing_loop', 'progress_loop',
                     'social_outbox', 'social_background', 'scheduler_loop'):
            setattr(bot, name, idle)
        try:
            await bot.setup_hook()
            for task in bot.bg:
                if task.get_coro().__name__ == 'sync_commands':
                    await task
            assert_compact(sent[:2])
            assert_compact(sent[-2:])
            assert all(row['name'] in {'settings', 'server'} for row in sent)
            assert ('global', '11') in removed
            assert (456, '21') in removed and (456, '22') in removed
            assert not any(ident in {'12', '13', '23'} for _, ident in removed)
        finally:
            for task in bot.bg: task.cancel()
            await asyncio.gather(*bot.bg, return_exceptions=True)
    asyncio.run(exercise())


def test_settings_preserves_setup_wizard_and_one_time_owner_claim(bot):
    from minecraft_agent.v3.ux import SettingsView, SetupView
    async def exercise():
        bot.cfg['owner_id'] = '0'
        import hashlib
        bot.cfg['owner_claim_hash'] = hashlib.sha256(b'synthetic-code').hexdigest()
        view = SettingsView(bot.ux, '200', 'dm:200')
        labels = {getattr(child, 'label', '') for child in view.children}
        assert 'Bắt đầu thiết lập' in labels and 'Nhận quyền owner' in labels
        interaction = SimpleNamespace(user=SimpleNamespace(id=200), guild_id=None,
            channel_id=300, response=SimpleNamespace(send_modal=AsyncMock(), edit_message=AsyncMock(), send_message=AsyncMock()))
        await next(child for child in view.children if getattr(child, 'label', '') == 'Bắt đầu thiết lập').callback(interaction)
        assert isinstance(interaction.response.edit_message.call_args.kwargs['view'], SetupView)
        await next(child for child in view.children if getattr(child, 'label', '') == 'Nhận quyền owner').callback(interaction)
        modal = interaction.response.send_modal.call_args.args[0]
        modal.code._value = 'synthetic-code'
        await modal.on_submit(interaction)
        assert bot.cfg['owner_id'] == '200' and 'owner_claim_hash' not in bot.cfg
        with pytest.raises(PermissionError): bot.ux.claim('201', 'synthetic-code')
    asyncio.run(exercise())


def test_server_command_opens_visible_paginated_overview_and_bound_details(bot):
    async def exercise():
        from minecraft_agent.v3.server_ui import ServerView
        bot.cfg['servers'] = [{'id': f's{i}', 'name': f'Server {i:02}', 'owners': ['999'],
            'guilds': ['456'] if i == 26 else [], 'connectors': {}} for i in range(27)]
        bot.cfg['assignments'] = {'201': [f's{i}' for i in range(27)]}
        for sid in bot.cfg['assignments']['201']:
            bot.store.execute('INSERT INTO kei_assignments VALUES (?,?)', ('201', sid))
        bot.engine.refresh_servers()
        interaction = SimpleNamespace(user=SimpleNamespace(id=201), guild_id=None,
            channel_id=300, response=SimpleNamespace(defer=AsyncMock(), edit_message=AsyncMock(), send_message=AsyncMock()),
            followup=SimpleNamespace(send=AsyncMock()))
        await bot.tree.get_command('server').callback(interaction)
        sent = interaction.followup.send.call_args.kwargs
        assert sent['ephemeral'] is True and isinstance(sent['view'], ServerView)
        view = sent['view']
        assert len(view.rows()) == 27 and len(view.page_rows()) == 10
        stranger = SimpleNamespace(user=SimpleNamespace(id=202), response=SimpleNamespace(send_message=AsyncMock()))
        assert await view.interaction_check(stranger) is False
        await next(c for c in view.children if getattr(c, 'label', '') == 'Next').callback(interaction)
        next_view = interaction.response.edit_message.call_args.kwargs['view']
        assert next_view.page == 1
        picker = next(c for c in next_view.children if isinstance(c, discord.ui.Select) and c.placeholder == 'Choose a Minecraft server')
        picker._values = ['s10']
        await picker.callback(interaction)
        detail = interaction.response.edit_message.call_args.kwargs['view']
        assert detail.selected == 's10'
        assert 's10' in str(interaction.response.edit_message.call_args.kwargs['embed'].to_dict())
        bot.store.execute('DELETE FROM kei_assignments WHERE user=? AND server=?', ('201', 's10'))
        bot.ux.connection_test = AsyncMock()
        await next(c for c in detail.children if getattr(c, 'label', '') == 'Test connection').callback(interaction)
        bot.ux.connection_test.assert_not_awaited()
        assert interaction.response.send_message.call_args.kwargs['ephemeral'] is True
        scoped = ServerView(bot.ux, '201', 'guild:789:300')
        assert 's26' not in {row['id'] for row in scoped.rows()}
    asyncio.run(exercise())


def test_settings_keeps_retired_alias_features_reachable(bot):
    from minecraft_agent.v3.ux import SettingsView
    async def exercise():
        pages = {page: SettingsView(bot.ux, '200', 'dm:200', page) for page in
                 ('persona', 'participation', 'privacy', 'memory', 'accounts', 'servers', 'admins', 'diagnostics')}
        labels = lambda page: {getattr(c, 'label', '') for c in pages[page].children}
        assert 'Public participation' in labels('participation')
        assert 'Forget one saved memory' in labels('memory')
        assert 'Bật đăng nhập Web' in labels('diagnostics')
        assert 'Tạo mã link Minecraft' in labels('accounts')
        assert 'Kết nối Panel' in labels('servers')
        menu = next(c for c in pages['persona'].children if isinstance(c, discord.ui.Select))
        assert {'tasks', 'privacy', 'memory', 'admins', 'servers'} <= {o.value for o in menu.options}
    asyncio.run(exercise())


def test_server_rechecks_access_after_interaction_defer(bot):
    from minecraft_agent.v3.server_ui import ServerView
    async def exercise():
        bot.cfg['servers'] = [{'id': 'one', 'name': 'One', 'owners': ['200'], 'connectors': {}}]
        bot.engine.refresh_servers()
        bot.store.execute('INSERT INTO kei_assignments VALUES (?,?)', ('201', 'one'))
        view = ServerView(bot.ux, '201', 'dm:201', selected='one')
        async def revoke(**kwargs):
            bot.store.execute('DELETE FROM kei_assignments WHERE user=?', ('201',))
        interaction = SimpleNamespace(user=SimpleNamespace(id=201),
            response=SimpleNamespace(defer=AsyncMock(side_effect=revoke), send_message=AsyncMock()),
            followup=SimpleNamespace(send=AsyncMock()))
        bot.ux.connection_test = AsyncMock()
        await next(c for c in view.children if getattr(c, 'label', '') == 'Test connection').callback(interaction)
        bot.ux.connection_test.assert_not_awaited()
        assert 'no successful status confirmed' in interaction.followup.send.call_args.args[0]
    asyncio.run(exercise())


def test_settings_command_opens_private_home(bot):
    async def exercise():
        interaction = SimpleNamespace(user=SimpleNamespace(id=200), guild_id=None,
            channel_id=300, response=SimpleNamespace(defer=AsyncMock()),
            followup=SimpleNamespace(send=AsyncMock()))
        await bot.tree.get_command('settings').callback(interaction)
        interaction.response.defer.assert_awaited_once_with(ephemeral=True, thinking=True)
        sent = interaction.followup.send.call_args.kwargs
        assert sent['ephemeral'] is True
        assert isinstance(sent['view'], discord.ui.View)
    asyncio.run(exercise())
