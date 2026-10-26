# Set up Kei without learning twelve commands

Kei chats, remembers selected moments, and helps operate Minecraft servers **you are actually assigned to**. You do not need a Minecraft server to talk to her.

## In Discord: two places to start

1. Run **`/settings`** and choose **Bắt đầu thiết lập** for the optional three-step guide. The screen is private. Choose how Kei talks, then link Minecraft or connect a server if you need either.
2. Run **`/server`** for a private, paginated overview of Minecraft connections you can actually access. Filter, select a connection, inspect its capabilities, test it, choose your DM default, connect a Panel or open permissions. `/settings` keeps personality, task progress, participation, proactive DMs, privacy, timezone, memories, relationship profile, linked accounts and schedules.

These are the only two slash entry points, both without arguments or subcommands. Old slash aliases are retired, not hidden duplicates. To claim a fresh installation, open `/settings` → **Nhận quyền owner** and enter the one-time code printed in your private terminal. No code is needed for ordinary personal setup. The self-hosted server menu does not implement hosted-service verification or community approval.

### Connect a Minecraft server

Open `/settings` → **Server & kiểm tra kết nối** → **Kết nối Panel**. In your Pterodactyl/Pelican account, open **Account → API Credentials** and create a **Client API key**. Enter the Panel URL and that key in the private form. Kei reads the servers the Panel account can actually access; choose one, then test the connection.

The operator controls whether other users may connect their own servers (`allow_self_service: true`). This does not grant permission to replace somebody else's registered connection. SSH, bind-mounted files and other connectors remain available through `keys-keys server add` for terminal administrators.

### Link Minecraft

Open `/settings` → **Tài khoản Minecraft** → **Tạo mã link**. Log in on the Minecraft server, then type the generated `/kei link CODE`. Codes expire after ten minutes and work once. **The Kei plugin must be installed and connected**; producing a code does not prove it is installed. A link joins identities, not privileges.

### Give someone server access

Server owners use `/settings` → **Cấp / thu hồi quyền**. The screen shows the server, Discord user ID, permission and who granted it.

- **chat**: conversation only; explicitly removes inherited operational access.
- **observe**: inspect the assigned server.
- **copilot**: request operations subject to the normal authorization/approval checks.
- **admin**: manage assignments for that one server. Only its owner can appoint or remove an admin. An admin cannot appoint another admin or change the owner's permissions.

Use **revoke** to remove operational access or **unadmin** to remove delegated administration and operational access. Relationship ranks never grant permissions. Access changes are recorded in `kei_access_history`.

### Schedule a reminder or a real task

Open `/settings` → **Lịch hẹn & công việc định kỳ**. Enter what to do, a time such as `ngày mai 07:00` or `mỗi ngày 07:00`, and your timezone. Choose **alarm** for a reminder, **observe** for server checks or **change** for authorized server work. Server work needs an assigned server; reminders do not.

New schedules stay pending until you press **🕒 Xác nhận lịch** on the private acknowledgement. Discord ephemeral messages cannot receive reactions, so this private button provides the explicit clock confirmation. Editing or resuming a schedule requires confirmation again. You can inspect, edit, pause, resume and cancel only your own schedules. Permissions are checked again when a server task runs; a schedule uses the same current run mode and assignment checks.

The web screen has the same controls. Web-created schedules deliver in your Discord DM. A web confirmation is recorded as a web acknowledgement, never as a fabricated Discord reaction. An alarm being delivered does not prove that you woke up or read it.

## Optional Web UI

The web screen uses the same preferences and access checks as Discord. It is optional; `/settings`, `/server` and the CLI work while it is disabled or misconfigured.

Configure the same Discord application that owns the bot:

1. In the Discord Developer Portal, open **OAuth2** and add the exact callback URL, for example `https://kei.example.com/oauth/callback`.
2. Add the web configuration below and restart Kei once. The dashboard shell loads before OAuth is ready; private settings still require sign-in.
3. As the bot operator, open **`/settings` → Kết nối & chẩn đoán → Bật đăng nhập Web**. Enter the application's Client ID and **OAuth client secret** in the private modal. Kei stores the secret in its private secrets file and restarts only the web listener. The bot remains connected. Then open `https://kei.example.com` and test Discord login.

The OAuth client secret is different from the bot token. The button appears only for the operator, and its authority is checked again on submission. The secret is never returned in a message or a dashboard API response. For terminal deployment instead, put it in the private environment as `DISCORD_CLIENT_SECRET` and use this example:

```yaml
web:
  enabled: true
  host: 127.0.0.1
  port: 8768
  public_url: https://kei.example.com
  redirect_uri: https://kei.example.com/oauth/callback
  client_id: "YOUR_DISCORD_APPLICATION_ID"
  client_secret_ref: env:DISCORD_CLIENT_SECRET
```

Use a reverse proxy with HTTPS for a public deployment. Only the web port needs proxying; do not expose credentials or the secrets file. Keep the listener on loopback when the proxy shares its network namespace. In separate containers, use a private container network and explicitly choose the web bind address instead of assuming that host loopback is reachable.

For a local test, set both URLs to `http://127.0.0.1:8768` and `http://127.0.0.1:8768/oauth/callback`. HTTP is accepted only for loopback URLs. The callback must match exactly. There is no arbitrary redirect parameter.

Login requests only Discord **identify** and **guilds**. OAuth tokens and credentials stay server-side. Sessions survive service restarts and renew with OAuth refresh tokens; inactive sessions expire after 90 days. Writes require a session-bound CSRF token and the configured origin; Discord identity is checked again before writes. A guild administrator role does **not** automatically grant Minecraft access. The dashboard shows only bot-connected guilds the person manages or that map to their explicitly assigned servers.

### Owner controls

The configured bot owner gets **Global Overview**, **Global relationships** and **Global settings**. A server co-owner does not get these bot-wide pages.

- **Global Overview** ranks Discord guilds (all their channels combined) and DM conversations. It shows recent DM activity, delivery state, joined guilds, Minecraft status, and each person's DM/top-guild interaction counts. Large lists collapse and the people directory loads in pages. Counts describe retained history, not online presence or lifetime statistics.
- **Global relationships** gives each linked person one numeric relationship and one durable rank across DM, guilds and Minecraft. Use **Show dimensions** for details. Private messages, source excerpts, contextual boundaries and memories keep their privacy rules.
- **Global settings** controls role models, trigger name, follow-up window/count, context size, relationship notices, memory/reflection, quiet hours and proactive caps. Personal opt-outs and server permissions still apply. Settings persist locally and apply to new turns without restarting.

For Gemini 3.8 on a compatible provider, chat defaults to low and agent/tool work to high. Both can be edited independently in Global settings, or in headless configuration:

```yaml
chat_model: ag/gemini-3.8-flash-low
agent_model: ag/gemini-3.8-flash-high
social:
  triggers: [kei]
  followup_seconds: 90
  followup_turn_limit: 4
  relationship_notice_min_delta: 0.006
  rank_confirmation_hours: 6
  rank_notice_hours: 6
```

Use model IDs supported by your endpoint. Other providers retain their selected `provider_model` unless you explicitly set role overrides. No provider key is sent to the browser. Saved dashboard overrides take priority over these initial defaults.

OAuth reference: [Discord OAuth2 documentation](https://discord.com/developers/docs/topics/oauth2).

### Make this deployment yours

The public dashboard ships its HTML, CSS and JavaScript locally, without promotional artwork. It does not fetch fonts or a UI library from somebody else's server. The public project defaults are reusable; deployment names and community invites belong in your own private config:

```yaml
web:
  # Keep the OAuth/listener settings above.
  branding:
    name: keys keys
    bot_name: Kei
    deployment_label: My Minecraft copilot
    tagline: Her problem. Your server.
    repo_url: https://github.com/TonyBucket/keys-keys
    community_url: ""
```

Optional `intro` replaces the short introduction. Names and copy are escaped as text. Repository links require HTTPS; `community_url` accepts a real `https://discord.gg/...` or `https://discord.com/invite/...` invite. Leave it empty to hide the community link. There is no default invite to somebody else's server.

The public Web UI is a dashboard, not a promotional landing page or conversation demo. Once signed in, it opens personal settings, relationship/memory, Minecraft and schedules. Tabs support keyboard navigation, and animation respects reduced-motion preferences.

For source deployments, include the exported `minecraft_agent/v3/web_assets/` dashboard HTML, CSS and JavaScript alongside the Python modules. The public dashboard does not include promotional artwork. Wheels package the exported dashboard assets; the code's MIT license does not relicense character artwork.

When the OAuth app secret or client ID is missing, the dashboard shell explains that Discord login is not ready. Login, callbacks and private APIs return 503; there is no anonymous setup or settings access. An invalid public URL or callback prevents the listener starting. Slash-command setup continues working in either case. A successful local HTTP test is not proof that your production Discord OAuth callback has been configured.

## Tiếng Việt: dùng nhanh

**`/settings` để bắt đầu hoặc chỉnh lại; `/server` để xem kết nối Minecraft.** Không phải học kiến trúc mới nói chuyện được. Chọn tính cách, bật/tắt DM chủ động, đặt `Asia/Ho_Chi_Minh`, xem hoặc quên memory, link Minecraft nếu muốn.

Muốn Kei quản lý server: owner nối Panel rồi cấp quyền cho từng người. Có nhiều server thì chọn mặc định hoặc gọi rõ tên; Kei không được tự bốc đại server. Rank thân thiết chỉ là ngữ cảnh nói chuyện, không phải vé vào console.

Web là đường dễ nhìn hơn trên điện thoại. Chưa cấu hình OAuth thì cứ dùng hai lệnh trong Discord. CLI vẫn còn cho cài mới, SSH và cứu hộ:

```sh
keys-keys setup --edit
keys-keys server add
keys-keys doctor
```

## Fewer commands, more ordinary words (rc.3)

`/settings` → **Bắt đầu thiết lập** opens three short private steps, with Back/Next and optional Minecraft linking. `/settings` opens direct category buttons plus a selector; each page can return home. The Web dashboard retains personal controls and a three-step guide, without the old promotional landing-page switch.

Say “Kei, từ giờ gọi mình là anh” or add text in **Trò chuyện → Lời dặn riêng** (also `/settings → Tính cách & tiến độ → Lời dặn riêng`). Clear the field to remove it. Personal instructions are limited to 2,000 characters and are inserted as lower-authority user preferences, never as a system replacement. Operators may set optional `custom_instructions: "..."` in kei.yaml (up to 4,000 characters used). Neither option grants permissions.

**Người có quyền** shows the selected server's owners, delegated admins and configured assignments. Check a Discord User ID before adding it; the roster shows display name, username, avatar when available, grantor and effective rights. Use **Sửa quyền**, **Thu hồi** or the action selector. Only server owners appoint administrators. Source configuration assignments can be overridden to conversation-only through the normal revoke operation; owner roles cannot be removed here.

**Chuyện hai người** contains a searchable library: load more, open a story, read retained original excerpts. It is scoped to your authenticated DM identity, not other users' conversations. Recent conversational mood and durable rank are separate. Small Discord notices use `-# Companion ↑` or `-# Companion ↓↓` with the actual current label. Single arrows are minor changes; doubled arrows indicate larger changes. A short cooldown (3 minutes for minor shifts, 45 seconds for major shifts) and opt-out keep them quiet. A snarky assistant response alone does not lower relationship scores.

The new banner is user-supplied Tendou Kei / Blue Archive fan art credited to kita (kitairoha); artwork and characters retain their creators' rights. The MIT license covers project code, not third-party artwork.

## Server access and run modes (3.2.0-rc.3)

The **People & permissions** screen separates three decisions: a person's server role, the access level Kei may use, and when Kei needs approval. An Admin role controls server membership only; its separate **Admin access** choice says whether that admin can view the server or ask Kei to operate it. Relationship rank never grants permissions.

**Access level** chooses the real connector boundary:

| Mode | Actual permission scope |
| --- | --- |
| Sandbox | Minecraft server only; no general host shell. |
| Host | The configured SSH user's permissions; Kei does not automatically use sudo. |
| Root | Full machine control through the configured root/elevation path. |

**Mode** chooses who approves changes:

| Mode | What happens |
| --- | --- |
| Ask for approval | Ask the person who started the task before every change. |
| Approve for me | Routine changes proceed; changes the risk rules flag are sent to that same task starter. |
| Full access | No per-step prompt inside the selected access level. Server assignment, target checks, backups and verification still apply. |
| Custom rules | Configure tool switches, per-tool behavior, file path allow/deny patterns, blocked SSH command patterns and extra guidance in the dashboard. No TOML editing is required. |

In **Custom rules**, switch each tool on or off, then choose whether Kei asks the task starter, reviews the change, or allows it within the saved scope. Unlisted tools have their own default. File and command rules only narrow access. Extra guidance is lower priority than system policy, the task, permissions and approval requirements; it cannot grant new authority.

Only a server owner can change another person's access level or run mode. Admin membership permissions and host access are separate. A co-owner can manage this server but does not gain the bot operator account or SSH rights unless an owner separately grants them.

Unsolicited public participation is removed. Old ambient settings are ignored. `kei` is the default configurable trigger; learned aliases only apply to the person who established them. Follow-ups default to four candidates within 90 seconds of Kei's actual reply. Another speaker does not erase that person's exchange or acquire their eligibility. An explicit reply, mention or name starts a fresh window. The model still distinguishes a direct counter from unrelated chatter and may answer briefly, react, or stay silent when appropriate. Strict context-sharing preferences keep learned aliases within their original context.

For opt-in private conversation, say “nhắn mình nhiều hơn”, “ít lại” or “đừng chủ động nhắn nữa”. Kei records the preference and adjusts future initiative using relationship/context. This is not a fixed-time reminder; use scheduled tasks for exact times. Quiet hours remain a boundary, not a send schedule.


## People, roles and reports

Open **People with access** / **Người có quyền**, choose a server, then find a Discord user ID. The roster shows display names, avatars when Discord provides them, who granted access and the effective execution policy. Use **Edit my permissions** on your own card to change your execution policy.

| Role | What it allows |
|---|---|
| Viewer | Read status, metrics and logs |
| Moderator | Request Minecraft operations |
| Admin | Manage viewer/moderator grants, plus the selected read/operation access |
| Co-owner | Equal management authority for this server, including admins and other co-owners |

The original configured owner stays protected. Co-ownership does not grant the bot operator account or host SSH authority. Full Machine needs an existing SSH connector and an explicit host grant. Relationship rank grants no access.

**Custom rules** are edited with switches and pickers in the dashboard. A blocked tool cannot run; allowing a tool never expands the selected server/host scope or an observation-only task. Grants and policy changes share the access audit with Discord.

Under the same server, choose which crash, delegated-admin/moderator and recovery reports should arrive in your own DM. Turn delivery off to keep the history without notifications. Ask “Kei, tắt thông báo thao tác admin cho server A” or “Kei, xem báo cáo server A gần đây”. Report retrieval requires management access. New co-owners have independent notification preferences.

Completed/cancelled schedules leave the active Web list automatically; execution history remains in storage. Edit a pending/active/paused schedule to change its job or time; leave time blank while editing to retain the previous schedule. Changes require confirmation again.


### Minecraft-only / Host User / Full Machine · Root

- **Minecraft-only** keeps general host shell unavailable; typed server tools remain scoped to the selected server.
- **Host User** executes as the configured ordinary SSH account (for example `wrc`). It disables automatic sudo and rejects explicit elevation commands. It is an execution policy, not an OS sandbox. Use a non-root SSH account; root/Administrator credentials cannot be relabeled as an ordinary user.
- **Full Machine · Root** uses the configured account's real OS elevation. Linux SSH verifies UID 0 before commands. With sudo enabled (the default), stored SSH credentials go over stdin to `sudo -S`; NOPASSWD is not mandatory. An SSH root account runs directly. Commands run separately; there is no persistent interactive `sudo -s` session.

For Linux hosts that require `su`, an operator may set `connectors.ssh.elevation: su` and `root_password: secret:root-password` in private configuration. The helper uses a non-echoing PTY and `su -c` with a bounded command. This fallback requires its own host acceptance; binary reads over that PTY are refused to avoid corrupting files. Current production acceptance covers Linux sudo. Windows local/companion connectors retain their existing OS identity; this Linux root control does not claim Windows Administrator elevation.

Legacy explicit `machine` grants retain their Root meaning. New Host User grants never acquire root simply because the connected account could use sudo.

Host User / Root chooses the identity of SSH commands. Panel, Wings and plugin actions keep their own scoped connector permissions. General shell accepts an optional absolute `cwd`; read-only host inspection can fall back to SSH home if the Minecraft directory is inaccessible, while mutations never silently move to a different directory.


## Approval behavior

Ask for approval and Read only both pause before a write, but they ask different people: Ask for approval goes to the task starter; Read only goes to the server/host owner. Approve for me asks the task starter only when deterministic risk checks flag a step. Routine admin activity reports are optional FYI notifications and never serve as approval cards. The dashboard is English; Discord conversation/persona language is unchanged.


## Mood, feelings and work

Global settings includes **Dynamic mood**, **Character romantic bonds** and **One-turn social sulking**. Core persona remains your own; a low-energy day changes delivery rather than rewriting identity or server permissions.

Each person chooses **Keep things platonic**, **Only romance I explicitly invite**, or **Let feelings develop naturally** in Chat settings or Discord Privacy settings. Natural development can mean a one-sided character crush; it never declares the human is in a relationship. Mutual romance needs an explicit invitation and shared history. Saying stop flirting or breaking up ends that direction without bargaining. These are fictional, nonsexual character states.

Single arrows show meaningful point movement while keeping the current rank. Double arrows show a major movement or confirmed rank/bond change. Notices accompany a relevant answer instead of arriving as unrelated DMs minutes later. New users see that relationship defaults are uncalibrated; 50% is a neutral prior, not proof of affection or trust.

When social sulking is enabled, a directly assigned nonurgent job may occasionally wait one turn. The bot says it has **not started**. Say **do it**, **force**, **please**, **làm đi**, or **thôi mà** to resume the original job; say **cancel** to drop it. A hold never grants access, replaces risk approval, stalls scheduled jobs or blocks emergency recovery. Disable it globally for strictly operational deployments.
