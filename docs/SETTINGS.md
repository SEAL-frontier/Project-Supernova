# Set up Kei without learning twelve commands

Kei chats, remembers selected moments, and helps operate Minecraft servers **you are actually assigned to**. You do not need a Minecraft server to talk to her.

## In Discord: two places to start

1. Run **`/setup`**. The screen is private. Choose how Kei talks, then link Minecraft or connect a server if you need either.
2. Later, run **`/settings`**. Everything is there: personality, task progress, participation, proactive DMs, privacy, timezone, memories, relationship profile, linked accounts and Minecraft access.

Existing commands still work. An operator can still claim a fresh installation with `/setup code:ONE_TIME_CODE`; no code is required for ordinary personal setup.

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

Open `/settings` → **Lịch hẹn & công việc định kỳ**, or use **`/tasks`**. Enter what to do, a time such as `ngày mai 07:00` or `mỗi ngày 07:00`, and your timezone. Choose **alarm** for a reminder, **observe** for server checks or **change** for authorized server work. Server work needs an assigned server; reminders do not.

New schedules stay pending until you press **🕒 Xác nhận lịch** on the private acknowledgement. Discord ephemeral messages cannot receive reactions, so this private button provides the explicit clock confirmation. Editing or resuming a schedule requires confirmation again. You can inspect, edit, pause, resume and cancel only your own schedules. Permissions are checked again when a server task runs; a schedule uses the same current run mode and assignment checks.

The web screen has the same controls. Web-created schedules deliver in your Discord DM. A web confirmation is recorded as a web acknowledgement, never as a fabricated Discord reaction. An alarm being delivered does not prove that you woke up or read it.

## Optional Web UI

The web screen uses the same preferences and access checks as Discord. It is optional; `/setup`, `/settings` and the CLI work while it is disabled or misconfigured.

Configure the same Discord application that owns the bot:

1. In the Discord Developer Portal, open **OAuth2** and add the exact callback URL, for example `https://kei.example.com/oauth/callback`.
2. Add the web configuration below and restart Kei once. The landing page works before OAuth is ready.
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

Login requests only Discord **identify** and **guilds**. OAuth tokens and credentials stay server-side. Sessions expire after an hour and after a restart. Writes require a session-bound CSRF token and the configured origin; Discord identity is checked again before writes. A guild administrator role does **not** automatically grant Minecraft access. The dashboard shows only bot-connected guilds the person manages or that map to their explicitly assigned servers.

OAuth reference: [Discord OAuth2 documentation](https://discord.com/developers/docs/topics/oauth2).

### Make this deployment yours

The silver, soft pink and crimson web theme ships with a small local Kei illustration. It does not fetch an avatar, font or UI library from somebody else's server. The public project defaults are reusable; deployment names and community invites belong in your own private config:

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

The landing page explains what the project is and why it exists before setup. Its conversation examples run locally in the browser; they send no messages or model requests. Once signed in, the same screen opens personal settings, relationship/memory, Minecraft and schedules. Tabs support keyboard navigation, and animation respects reduced-motion preferences.

For custom deployments that copy the Python source directly, include `minecraft_agent/v3/web_assets/kei.png` along with the Python modules. Wheels and the supplied Dockerfile package this asset automatically. The image is the existing project artwork; the code's MIT license does not relicense it.

When the OAuth app secret or client ID is missing, the landing page remains readable and explains that Discord login is not ready. Login, callbacks and private APIs return 503; there is no anonymous setup or settings access. An invalid public URL or callback prevents the listener starting. Slash-command setup continues working in either case. A successful local HTTP test is not proof that your production Discord OAuth callback has been configured.

## Tiếng Việt: dùng nhanh

**`/setup` để bắt đầu, `/settings` để chỉnh lại.** Không phải học kiến trúc mới nói chuyện được. Chọn tính cách, bật/tắt DM chủ động, đặt `Asia/Ho_Chi_Minh`, xem hoặc quên memory, link Minecraft nếu muốn.

Muốn Kei quản lý server: owner nối Panel rồi cấp quyền cho từng người. Có nhiều server thì chọn mặc định hoặc gọi rõ tên; Kei không được tự bốc đại server. Rank thân thiết chỉ là ngữ cảnh nói chuyện, không phải vé vào console.

Web là đường dễ nhìn hơn trên điện thoại. Chưa cấu hình OAuth thì cứ dùng hai lệnh trong Discord. CLI vẫn còn cho cài mới, SSH và cứu hộ:

```sh
keys-keys setup --edit
keys-keys server add
keys-keys doctor
```

## Fewer commands, more ordinary words (rc.3)

`/setup` opens three short private steps, with Back/Next and optional Minecraft linking. `/settings` opens direct category buttons plus a selector; each page can return home. The Web dashboard has the same personal controls, a three-step guide and an always-available **Về Kei** / **Góc của bạn** switch.

Say “Kei, từ giờ gọi mình là anh” or add text in **Trò chuyện → Lời dặn riêng** (also `/settings → Tính cách & tiến độ → Lời dặn riêng`). Clear the field to remove it. Personal instructions are limited to 2,000 characters and are inserted as lower-authority user preferences, never as a system replacement. Operators may set optional `custom_instructions: "..."` in kei.yaml (up to 4,000 characters used). Neither option grants permissions.

**Người có quyền** shows the selected server's owners, delegated admins and configured assignments. Check a Discord User ID before adding it; the roster shows display name, username, avatar when available, grantor and effective rights. Use **Sửa quyền**, **Thu hồi** or the action selector. Only server owners appoint administrators. Source configuration assignments can be overridden to conversation-only through the normal revoke operation; owner roles cannot be removed here.

**Chuyện hai người** contains a searchable library: load more, open a story, read retained original excerpts. It is scoped to your authenticated DM identity, not other users' conversations. Recent conversational mood and durable rank are separate. Small Discord notices use `-# Companion ↑` or `-# Companion ↓↓` with the actual current label. Single arrows are minor changes; doubled arrows indicate larger changes. A short cooldown (3 minutes for minor shifts, 45 seconds for major shifts) and opt-out keep them quiet. A snarky assistant response alone does not lower relationship scores.

The new banner is user-supplied Tendou Kei / Blue Archive fan art credited to kita (kitairoha); artwork and characters retain their creators' rights. The MIT license covers project code, not third-party artwork.

## Execution permissions (rc.3)

In **Người có quyền**, select a server and person. Owners can set two separate controls:

| Scope | Meaning |
| --- | --- |
| Minecraft-only | Server-scoped files/console/power tools. No general host shell; not an OS sandbox. |
| Full Machine | Host commands over configured SSH. Only the operator or operator-configured host administrator can issue this scope. |

| Level | Behavior |
| --- | --- |
| Default | Routine work runs in scope; risky steps receive internal review. |
| Auto-review | Changes are reviewed automatically; denied steps return to the worker for replanning, without an owner ticket. |
| Read only | Diagnostics run; writes need an eligible server or host owner approval. Observation-only tasks still cannot mutate. |
| Full access | Executes within the explicitly granted scope without per-step approval. Assignment, target validation, backups and verification still apply. |
| Custom | Editable TOML tool/path/command rules (`allow`, `deny`, `auto_review`), enforced before dispatch. Scope is never expanded. |

Custom can be edited directly in the Web config.toml editor; a separate operator-only setup step is no longer required. Legacy ask rules become auto_review. Admin delegation alone cannot issue host scope or bypass the owner's execution profile. Revocation sets conversation-only plus Minecraft/read-only to remove previously granted host execution.

Unsolicited public participation is removed. Old ambient settings are ignored. `kei` is the default configurable trigger; learned aliases only apply to the person who established them. The public followup window is at most two candidates, expires after 45 seconds by default, and closes when another person speaks. A candidate still may be ignored or receive only a reaction. Direct mentions, replies and actual work are stronger signals.

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

**Custom** opens a validated TOML editor for allow, deny and auto_review rules. Deny blocks the selected tool, including reads; automatic review applies to changes. Choosing Allow never expands the selected server/host scope or an observation-only task. Revocation, grants and policy changes share the same access audit as Discord.

Under the same server, choose which crash, delegated-admin/moderator and recovery reports should arrive in your own DM. Turn delivery off to keep the history without notifications. Ask “Kei, tắt thông báo thao tác admin cho server A” or “Kei, xem báo cáo server A gần đây”. Report retrieval requires management access. New co-owners have independent notification preferences.

Completed/cancelled schedules leave the active Web list automatically; execution history remains in storage. Edit a pending/active/paused schedule to change its job or time; leave time blank while editing to retain the previous schedule. Changes require confirmation again.


### Minecraft-only / Host User / Full Machine · Root

- **Minecraft-only** keeps general host shell unavailable; typed server tools remain scoped to the selected server.
- **Host User** executes as the configured ordinary SSH account (for example `wrc`). It disables automatic sudo and rejects explicit elevation commands. It is an execution policy, not an OS sandbox. Use a non-root SSH account; root/Administrator credentials cannot be relabeled as an ordinary user.
- **Full Machine · Root** uses the configured account's real OS elevation. Linux SSH verifies UID 0 before commands. With sudo enabled (the default), stored SSH credentials go over stdin to `sudo -S`; NOPASSWD is not mandatory. An SSH root account runs directly. Commands run separately; there is no persistent interactive `sudo -s` session.

For Linux hosts that require `su`, an operator may set `connectors.ssh.elevation: su` and `root_password: secret:root-password` in private configuration. The helper uses a non-echoing PTY and `su -c` with a bounded command. This fallback requires its own host acceptance; binary reads over that PTY are refused to avoid corrupting files. Current production acceptance covers Linux sudo. Windows local/companion connectors retain their existing OS identity; this Linux root control does not claim Windows Administrator elevation.

Legacy explicit `machine` grants retain their Root meaning. New Host User grants never acquire root simply because the connected account could use sudo.

Host User / Root chooses the identity of SSH commands. Panel, Wings and plugin actions keep their own scoped connector permissions. General shell accepts an optional absolute `cwd`; read-only host inspection can fall back to SSH home if the Minecraft directory is inaccessible, while mutations never silently move to a different directory.


## Current run modes (3.2.0-rc.2)

Access scope answers **where**; run mode answers **how work is reviewed**. Select the person, then a mode card:

| Mode | Behavior |
|---|---|
| Default permissions | Ordinary authorized work runs in scope. Risky steps receive an internal review. |
| Auto-review | Changes and elevated steps receive an automatic allow/deny decision. A denial returns to the worker to replan; it does not send an owner approval ticket. |
| Read only | Diagnostics remain available. Changes wait for an eligible server owner, or host owner when host scope is involved. The original requester cannot approve someone else's authority. |
| Full access | Authorized changes execute without per-step approval/review; assignments, selected scope, backups and verification still apply. |
| Custom (config.toml) | Uses validated `[tools]`, `[paths]` and `[shell]` rules. Each tool can allow, deny or auto_review. Path/command glob lists narrow the existing scope. Unsupported fields fail visibly. |

Custom is an application policy, not an OS sandbox. Old `ask` rules migrate to `auto_review`; choose Read only for manual escalation. Existing explicit host grants keep their identity. A co-owner may adjust their own already-granted host policy without gaining permission to grant host access to others.

Routine admin activity DMs default to **Save only**. Each owner can opt in independently. Read-only approval requests are a separate workflow and remain visible when an actual approval is required.

The dashboard is now English. Discord conversation/persona language is unchanged. The run-mode cards and Custom editor replace the former ambiguous action/policy dropdown UX.
