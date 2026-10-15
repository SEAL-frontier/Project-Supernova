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

New schedules stay pending until you press **🕒 Xác nhận lịch** on the private acknowledgement. Discord ephemeral messages cannot receive reactions, so this private button provides the explicit clock confirmation. Editing or resuming a schedule requires confirmation again. You can inspect, edit, pause, resume and cancel only your own schedules. Permissions are checked again when a server task runs; a schedule does not bypass normal dangerous-action approval.

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
