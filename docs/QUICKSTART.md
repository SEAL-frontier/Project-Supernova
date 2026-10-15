# Quick start / Cài nhanh

You need Docker Compose, a Discord bot token, and a provider with native tool calling.
You do **not** need SSH, a Wings token or a Minecraft server just to chat.

## 1. Discord, once / Tạo bot một lần

Create an application in the [Discord Developer Portal](https://discord.com/developers/applications).
Open **Bot**, copy its token privately and enable **Message Content Intent**.
Invite with **bot** and **applications.commands** scopes; allow View Channel, Send Messages,
Read Message History, Embed Links and Add Reactions in the channels you choose.

Tạo application, lấy bot token và bật Message Content Intent. Không paste token lên GitHub
hay nhắn vào channel. Wizard sẽ hỏi riêng trong terminal.

## 2. Clone and run the wizard / Clone rồi chạy wizard

```sh
git clone https://github.com/TonyBucket/keys-keys.git
cd keys-keys
docker compose run --build --rm keys-keys setup
docker compose run --rm keys-keys doctor
docker compose up -d
docker compose logs -f --tail=40
```

The wizard asks for language, timezone, Discord token, provider URL/key, model,
owner and one sentence of persona. Choose **chat** for the first connection.
For Vietnam use **Asia/Ho_Chi_Minh**; choose another IANA timezone if appropriate.

If you do not know your Discord user ID, leave owner blank. The terminal prints a
private claim code. Start the bot, then run `/setup code:THE_CODE` in Discord.
Keep the code private; it gives initial owner access and stops working after a claim.

Wizard hỏi từng bước, tự tạo file trong `data/`. Đừng tự tạo một đống file rỗng nữa.
Provider URL phải truy cập được **từ container**. `localhost` trong container là chính
container đó; dùng `host.docker.internal` nếu provider chạy trên Docker host.

Default model: `ag/gemini-3.8-flash-medium`, through an OpenAI-compatible 9Router `/v1`
endpoint. Other model IDs can be entered, but their actual tool/vision support must be checked.

## 3. Add Minecraft when ready / Thêm Minecraft sau

```sh
docker compose run --rm keys-keys server add
docker compose run --rm keys-keys doctor
docker compose restart keys-keys
```

Choose Panel, SSH or bridge. Each is optional. To add a second connector to an existing
server, use the **same server ID**. Back up `data/` before changing the deployment.

Owner can also use `/server connect` privately in Discord for a Panel API connection,
then `/server grant` to assign people. Regular players do not need a host account.

Details: [connectors](CONNECTORS.md), [Minecraft plugin](MINECRAFT.md),
[social and memory](SOCIAL.md), [updates](UPGRADING.md), [troubleshooting](TROUBLESHOOTING.md).

## Native Linux / Pelican Python slot

```sh
python3 -m venv .venv
. .venv/bin/activate
python -m pip install -e .
keys-keys setup
keys-keys doctor
keys-keys run
```

For a Python slot, install `-e .`, use `python bot.py` or `keys-keys run` as startup,
persist `data/`, and use the allocated TCP port when enabling the bridge.
Linux and Windows Docker/WSL are the recommended paths. Never run two consumers with
the same bot token just to find out whether Discord enjoys chaos.

## Files and unattended setup

New installs use `data/config.yaml`, `data/secrets.json`, `data/persona.md` and `data/kei.db`.
The public `.env.example`, persona files and test placeholder remain blank intentionally.
The wizard writes local private files, not those public placeholders.

Existing `kei.yaml`/`.env` installs remain supported. `setup --edit --config PATH` edits
an existing config with a backup. For unattended deployment use `setup --answers /private/answers.json`;
the answer file contains credentials and must stay private. Field names are documented in
[configuration](CONFIGURATION.md).
