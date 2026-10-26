"""Self-hosted Minecraft connection overview; no hosted admission policy."""
from __future__ import annotations

import discord

PAGE_SIZE = 10


async def open_server_menu(ux, interaction):
    await interaction.response.defer(ephemeral=True, thinking=True)
    user = str(interaction.user.id)
    scope = f'guild:{interaction.guild_id}:{interaction.channel_id}' if interaction.guild_id else 'dm:' + user
    view = ServerView(ux, user, scope)
    await interaction.followup.send(embed=view.embed(), view=view, ephemeral=True,
                                    allowed_mentions=discord.AllowedMentions.none())


class ServerView(discord.ui.View):
    def __init__(self, ux, user, scope, page=0, selected=None, filter_by='all'):
        super().__init__(timeout=600)
        self.ux, self.user, self.scope = ux, str(user), scope
        self.page, self.selected, self.filter_by = max(0, page), selected, filter_by
        rows = self.rows()
        self.page = min(self.page, max(0, (len(rows) - 1) // PAGE_SIZE))
        if selected:
            self.button('Back to list', lambda i: self.show(i))
            self.button('Test connection', self.test)
            self.button('Use in DM', self.use_default)
            row = next((r for r in rows if r['id'] == selected), None)
            if row and row['manage_access']:
                self.button('People & permissions', self.permissions)
        else:
            filters = discord.ui.Select(placeholder='Filter connections', options=[
                discord.SelectOption(label=label, value=value, default=value == filter_by)
                for value, label in [('all', 'All visible'), ('managed', 'I manage'), ('connected', 'Has connectors')]])
            async def filtered(i):
                if await self.interaction_check(i):
                    await self.show(i, page=0, filter_by=filters.values[0])
            filters.callback = filtered
            self.add_item(filters)
            if rows:
                picker = discord.ui.Select(placeholder='Choose a Minecraft server', options=[
                    discord.SelectOption(label=r['name'][:100], value=r['id'], description=r['level'][:100])
                    for r in self.page_rows()])
                async def picked(i):
                    if await self.interaction_check(i):
                        await self.show(i, selected=picker.values[0])
                picker.callback = picked
                self.add_item(picker)
            self.button('Previous', lambda i: self.show(i, page=self.page - 1), disabled=self.page == 0)
            self.button('Next', lambda i: self.show(i, page=self.page + 1), disabled=(self.page + 1) * PAGE_SIZE >= len(rows))
        if ux.state(self.user, self.scope)['can_connect']:
            self.button('Connect Panel', self.connect)
        self.button('Settings', self.settings)

    def rows(self):
        rows = self.ux.state(self.user, self.scope)['servers']
        if self.filter_by == 'managed': rows = [r for r in rows if r['manage_access']]
        elif self.filter_by == 'connected': rows = [r for r in rows if r['connections']]
        return sorted(rows, key=lambda r: (r['name'].casefold(), r['id']))

    def page_rows(self):
        return self.rows()[self.page * PAGE_SIZE:(self.page + 1) * PAGE_SIZE]

    async def interaction_check(self, interaction):
        if str(interaction.user.id) == self.user:
            return True
        await interaction.response.send_message('Open /server to view your own connections.', ephemeral=True)
        return False

    async def allowed(self, interaction, server=None):
        if not await self.interaction_check(interaction): return False
        if server and server not in self.ux.access.visible(self.user, self.scope):
            await interaction.response.send_message('This connection is no longer available to you. Open /server again.', ephemeral=True)
            return False
        return True

    def button(self, label, action, disabled=False):
        button = discord.ui.Button(label=label, disabled=disabled, style=discord.ButtonStyle.secondary)
        async def clicked(i):
            if await self.allowed(i, self.selected): await action(i)
        button.callback = clicked
        self.add_item(button)

    def embed(self):
        rows = self.rows()
        if self.selected:
            row = next((r for r in rows if r['id'] == self.selected), None)
            if not row:
                return discord.Embed(title='Connection unavailable', description='Access changed; return to the list.')
            embed = discord.Embed(title=row['name'][:256], description='Minecraft connection · `' + row['id'] + '`', color=0xEFA5A5)
            embed.add_field(name='Your access', value=row['level'] + (' · manages access' if row['manage_access'] else ''), inline=False)
            embed.add_field(name='Connectors', value=', '.join(row['connections']) or 'None configured', inline=False)
            embed.add_field(name='Available capabilities', value=(', '.join(row['capabilities']) or 'None')[:1024], inline=False)
            embed.set_footer(text='Configuration is not a live status check. Use Test connection for a fresh read.')
            return embed
        configured = sum(bool(r['connections']) for r in rows)
        pages = max(1, (len(rows) + PAGE_SIZE - 1) // PAGE_SIZE)
        lines = [f"**{r['name']}** · {r['level']} · {', '.join(r['connections']) or 'no connector'}" for r in self.page_rows()]
        embed = discord.Embed(title='Your Minecraft servers', color=0xEFA5A5,
            description=('\n'.join(lines)[:3800] or 'No visible Minecraft connections. Ask an owner for access or connect your own Panel if enabled.'))
        embed.set_footer(text=f'{len(rows)} visible · {configured} with connectors · page {self.page + 1}/{pages} · live status not checked')
        return embed

    async def show(self, interaction, page=None, selected=None, filter_by=None):
        if not await self.allowed(interaction, selected): return
        view = ServerView(self.ux, self.user, self.scope, self.page if page is None else page,
                          selected, self.filter_by if filter_by is None else filter_by)
        await interaction.response.edit_message(content=None, embed=view.embed(), view=view,
                                                allowed_mentions=discord.AllowedMentions.none())

    async def test(self, interaction):
        await interaction.response.defer(ephemeral=True, thinking=True)
        try:
            if self.selected not in self.ux.access.visible(self.user, self.scope):
                raise PermissionError('Connection access changed')
            result = await self.ux.connection_test(self.user, self.selected)
            # A revoked scope must not receive a completed read after its await.
            if self.selected not in self.ux.access.visible(self.user, self.scope):
                text = 'Access changed while testing. Open /server again.'
            else:
                text = result['message'] + '\nCapabilities: ' + ', '.join(result['capabilities'])
        except Exception as exc:
            text = 'Connection check unavailable (' + type(exc).__name__ + '); no successful status confirmed.'
        await interaction.followup.send(text[:1900], ephemeral=True, allowed_mentions=discord.AllowedMentions.none())

    async def use_default(self, interaction):
        self.ux.update(self.user, {'default_server': self.selected})
        await interaction.response.send_message('Default Minecraft server saved for your DMs.', ephemeral=True)

    async def permissions(self, interaction):
        from .ux import AccessModal
        if not self.ux.access.manager(self.user, self.selected):
            await interaction.response.send_message('Only this server\'s managers can change access.', ephemeral=True)
            return
        modal = AccessModal(self.ux, self.user)
        modal.server.default = self.selected
        await interaction.response.send_modal(modal)

    async def connect(self, interaction):
        from .ux import ConnectModal
        if not self.ux.state(self.user, self.scope)['can_connect']:
            await interaction.response.send_message('Self-service connections are disabled.', ephemeral=True)
            return
        await interaction.response.send_modal(ConnectModal(self.ux, self.user))

    async def settings(self, interaction):
        from .ux import SettingsView
        await interaction.response.edit_message(content=None, embed=self.ux.embed(self.user, self.scope),
            view=SettingsView(self.ux, self.user, self.scope), allowed_mentions=discord.AllowedMentions.none())
