<div align="center">

<img src="assets/kei.png" alt="Tendou Kei, adjusting her glasses and judging this repository" width="160" height="160" />

# keys-keys 🗝️🗝️

**An open-source Adaptive Hybrid Minecraft Server Copilot**

*Her server. Your problem.*

Actually, her problem. Your server. We got the custody arrangement wrong. 😭

![Version](https://img.shields.io/badge/version-2.0.7-EFA5A5?style=flat-square)
![Architecture](https://img.shields.io/badge/architecture-Supernova-aca9e8?style=flat-square)
![Python](https://img.shields.io/badge/Python-3.11%2B-3776ab?style=flat-square)
[![MIT](https://img.shields.io/badge/license-MIT-efa5a5?style=flat-square)](LICENSE)

[English](#english) · [Tiếng Việt](#tiếng-việt) · [Quick start](#get-her-online) · [Changelog](CHANGELOG.md)

</div>

---

## English

### So… why keys-keys?

Her name is **Kei**. Someone kept calling her **keys** to ragebait her. Now the typo owns a repository. Terrible naming process. Excellent commitment to the bit. 🥀

The experimental character/avatar is **Tendou Kei**. The code does the server work; the personality is yours to write. This is a fan experiment, not an official Blue Archive thing.

She has two jobs: hang out in Discord, and deal with the Minecraft server when an assigned person asks. A casual “yo” should not wake up a whole incident-response department. A request to inspect a config should not end with “I can help you with that” and absolutely nothing happening.

### What she actually does

| You ask | She does |
|---|---|
| Chat in DMs, mention/reply in a server | A light chat turn, with context and memory |
| “TPS? RAM? Why is it lagging?” | Reads real stats, logs and JVM info; can inspect Spark profiles |
| “Show/change this config” | Reads files; backs up changes and checks the result |
| “Find/install this plugin” | Finds releases, checks JAR metadata/dependencies, stages or installs |
| “Kick this player / restart the server” | Uses console/Wings for the assigned server; checks what happened |
| “What are you doing right now?” | An edited status card: objective, checklist, optional real commands/logs |

Server work is **assignment-only**. Chat is open. She knows people by Discord user ID, not by whichever cursed nickname they chose this week.

Ordinary authorized work runs directly. Destructive steps need the actual requester's confirmation. An accepted HTTP request is not a success certificate. “The button returned 200” is a very creative way to discover your server is still broken.

### Supernova, without the astronomy homework

**Supernova** is the name of this project's adaptive hybrid architecture:

```text
Discord message
  ├─ normal conversation → light chat
  ├─ small server job    → bounded direct tools
  └─ bigger server job   → inspect → plan → act → verify → adjust
                              ↕
                     SQLite checkpoints + memory
                              ↕
                   Wings / SSH / console / files / Spark
```

The router chooses a path from the request. Larger jobs keep their state, so cancel, updates and continuation have something real to operate on. This runtime is its own agent loop; OpenCode is not a dependency.

### Get her online

**Use Linux + Python 3.11+, or Docker.** The native runtime uses Linux file locking. On Windows, use Docker/WSL rather than arguing with `fcntl`.

**1. Clone and create your local files.**

```sh
git clone https://github.com/TonyBucket/keys-keys.git
cd keys-keys
cp .env.example .env
cp kei.example.yaml kei.yaml
mkdir -p data
touch known_hosts
```

**2. Fill `.env`.** The checked-in `.env.example` is genuinely empty. Paste these names into your local `.env`, then supply your own values:

```dotenv
DISCORD_BOT_TOKEN=
PROVIDER_API_KEY=
# Only needed when you add Minecraft server profiles:
WINGS_TOKEN=
MINECRAFT_SSH_PASSWORD=
# Optional; defaults shown here, not secrets:
PROVIDER_MODEL=ag/gemini-3.8-flash-medium
KEI_GATEWAY_ENABLED=1
```

The default model is **Gemini 3.8 Flash Medium through 9Router**. `provider_base` must be the provider's OpenAI-compatible **`/v1`** endpoint, with native function/tool calling. `PROVIDER_MODEL` lets you use a different compatible model; that is not a promise that every provider's tool adapter behaves identically.

**3. Fill `kei.yaml` and write `prompts/persona.md`.** For chat-only mode:

```yaml
provider_base: "http://YOUR_PROVIDER_HOST:20128/v1"
owner_id: "YOUR_DISCORD_USER_ID"
database: data/kei.db
persona_file: prompts/persona.md
assignments: {}
servers: []
```

The placeholders above are placeholders. Sadly, `YOUR_DISCORD_USER_ID` is not a real person.

The persona files are empty **on purpose**. Write how your bot speaks, addresses people, handles jokes/RP, and behaves when someone is having a bad day. Don't paste the maintainer's personal prompt and hope it becomes your personality. Optional mode files can stay empty; they fall back to the base persona. See [prompt setup](prompts/README.md).

**4. Create/invite your Discord bot.** In the [Developer Portal](https://discord.com/developers/applications), enable **Message Content Intent**. Invite it with `bot` and `applications.commands`, and channel permissions for viewing, sending, reading history and embeds. Application-command setup is covered in the [official Discord docs](https://docs.discord.com/developers/docs/interactions/slash-commands).

**5. Run a setup check, then start.**

<details>
<summary><strong>Docker — recommended if “Python environment” already ruined your afternoon</strong></summary>

```sh
docker compose build
docker compose run --rm keys-keys python -m minecraft_agent.v2.configure
# Once the checker says Setup OK:
docker compose up -d
docker compose logs -f --tail=40
```

This builds a local image using the [official Python image](https://hub.docker.com/_/python). Keep your provider/Wings endpoints reachable **from the container**. `127.0.0.1` inside a container points at that container, not your host.

</details>

<details>
<summary><strong>Native Linux / a Python Pelican slot</strong></summary>

```sh
python3 -m venv .venv
. .venv/bin/activate
python -m pip install -e .
python -m minecraft_agent.v2.configure
python bot.py
```

For a Python slot, upload the source plus your **local** config/persona/env, install `-e .`, and use `python bot.py` as the start command. Persist `data/`. Run one consumer per bot token, not two copies having a conversation with the same account.

</details>

The setup checker is offline. It catches blank settings and missing files; it does not pretend to have tested your SSH password, Discord token or server connection.

### Give her an actual Minecraft server

Start with **Pelican/Wings + SSH**. No Minecraft-side plugin is required for the current copilot. Spark is needed for Spark-specific profiling/TPS commands. Paper-family servers are the current target.

Replace every value in this example with yours, then put it in `kei.yaml`:

```yaml
assignments:
  "YOUR_DISCORD_USER_ID": [survival]
  "ANOTHER_AUTHORIZED_USER_ID": [survival]
servers:
  - id: survival
    name: Survival
    host: YOUR_SERVER_HOST
    ssh_user: YOUR_SSH_USER
    password_env: MINECRAFT_SSH_PASSWORD
    known_hosts: known_hosts
    uuid: YOUR_WINGS_SERVER_UUID
    wings_url: "https://YOUR_WINGS_HOST:YOUR_WINGS_PORT"
    wings_token_env: WINGS_TOKEN
    volume: "/YOUR/WINGS/VOLUMES/YOUR_WINGS_SERVER_UUID"
    file_owner: "YOUR_SERVER_UID:YOUR_SERVER_GID"
    minecraft_version: "YOUR_MINECRAFT_VERSION"
    notify_user: "YOUR_DISCORD_USER_ID"
```

| Field | Where it comes from |
|---|---|
| `uuid` | Full Minecraft server UUID from your panel/Wings configuration |
| `wings_url` / `WINGS_TOKEN` | Your Wings daemon endpoint and bearer token; not a Panel API key |
| `host` / `ssh_user` | The host holding the Minecraft volume; the account needs password-based sudo for these adapters |
| `volume` | The actual volume directory on that host |
| `file_owner` | The volume's numeric UID:GID; check with `stat -c '%u:%g' /your/volume` |
| `known_hosts` | A file with your verified SSH host key; the client rejects unknown keys |
| `assignments` | Who may ask for work on which server ID; even the owner needs an assignment |

Different nodes can name different password/token env variables. Don't force unrelated servers to share a secret because an example happened to use one.

### Daily use

```text
you: @Kei check TPS and RAM on Survival, read-only
you: show the anti-xray config
you: back up server.properties, then change the view distance to 8
you: find a compatible LuckPerms release; stage it first
you: cancel that job
you: remember this preference / forget that fact
```

| Command | What it changes |
|---|---|
| `/debug mode:off` | Hides the status card; the job keeps going |
| `/debug mode:minimal` | Light red embed: objective, status, checklist |
| `/debug mode:advanced` | Same objective/checklist, plus real commands/logs in a codeblock; default |
| `/persona mode:auto` | Your context-sensitive personality; default |
| `/persona mode:soft` / `spicy` | Your gentler / sharper local prompt |
| `kei!servers` / `kei!server use survival` | Lists/selects assigned servers |
| `kei!server assign @user survival` | Owner assigns a user |
| `kei!clear` / `kei!clearall` | Personal memory / owner-only full chat-memory clear |

Preferences stick to the user across DMs and guilds. Status edits are coalesced, at least five seconds apart after a request completes. You get a small first-run hint, not a new novella every time a command finishes.

Text fallbacks: `kei!debug <mode>` and `kei!persona <mode>`.

If your persona enables playful refusal, excessive teasing can make her hold **new, nonurgent** work without executing it. Ask nicely and she can resume the same request. This is optional personality behavior, not an authorization system. She does not sulk through an outage or abandon a running job. The server has enough problems already.

### What ships empty, and why

| Path | You provide |
|---|---|
| `.env.example` | Empty placeholder; put credentials in ignored `.env` |
| `prompts/persona*.md` | Your own voice and modes; all four public files are blank |
| `tests/.gitkeep` | Your deployment-specific tests; no fake “all tests passing” badge |
| `kei.example.yaml` | Minimal empty registry; fill a local `kei.yaml` |

Core agent/tool contracts remain in the implementation. Custom persona files are not where permission checks or “did that actually work?” live.

The original private runtime was checked against real server tools and a private regression suite. That suite is **not** in this repository. An empty `tests/` is not a passed test suite. To add yours:

```sh
python -m pip install -e '.[dev]'
# Write tests/test_*.py for your adapters/configuration first.
python -m pytest tests -q
```

The built-in UI/reply contract currently uses Vietnamese. Multi-server assignment is implemented, but the original live deployment validated one server. Profiler parsing has size limits, jobs have budgets/checkpoints, and a staged plugin still needs a real enable/restart check. She is a copilot, not a reason to stop reading the result.

### Contributing without leaking your entire afternoon

Work in this repository. Bump the patch version for fixes, update [CHANGELOG.md](CHANGELOG.md), validate, then commit. Keep prompts/env/config/test data local. `.gitignore` does not hide changes to files that are already tracked: see the prompt guide before pushing your filled placeholders.

---

## Tiếng Việt

### Tên repo từ đâu ra?

Tên ẻm là **Kei**. Bọn t cứ gọi thành **keys** để ragebait, xong đem luôn cái tên sai lên GitHub. Một quyết định thiếu tỉnh táo nhưng rất nhất quán. 🥀

**Tendou Kei** là character/avatar dùng cho thử nghiệm. Code lo server; tính cách thì m tự viết. Đây là fan project, không phải sản phẩm chính thức của Blue Archive.

Mục tiêu rất đời: chat thì chat cho giống đang nói chuyện, giao việc server thì làm thật. “Yo” không cần mở ban chuyên án. “Xem config hộ t” cũng không nên kết thúc bằng “mình có thể hỗ trợ bạn” rồi nằm im.

### Supernova làm gì?

**Supernova** là tên kiến trúc adaptive hybrid của project: chat dùng lượt nhẹ, việc nhỏ dùng tool trực tiếp, việc lớn đi qua xem → lên kế hoạch → làm → kiểm chứng → điều chỉnh. SQLite giữ memory và checkpoint. Wings/SSH/console/file/Spark là tay chân. Không cần OpenCode làm runtime.

Kei đọc TPS/RAM/JVM/log, xem và sửa config có backup, tìm/stage/cài plugin, chạy console, quản lý player và power server. Người chưa được assign vẫn chat được; **copilot chỉ dành cho user được assign server đó**. Nhận người bằng user ID, không phải nickname. Đặt tên “owner” không biến m thành owner đâu 🦭

### Deploy gọn

Chạy Linux + Python 3.11+, hoặc Docker/WSL nếu dùng Windows.

```sh
git clone https://github.com/TonyBucket/keys-keys.git
cd keys-keys
cp .env.example .env
cp kei.example.yaml kei.yaml
mkdir -p data
touch known_hosts
```

1. Điền `.env` theo block ở [Quick start](#get-her-online): token Discord và API key provider là bắt buộc; Wings token/SSH password cần khi bật copilot. File mẫu env cố ý để trống.
2. Điền `provider_base` là URL **`/v1`**, `owner_id` là Discord user ID của m. Mẫu `servers: []`, `assignments: {}` chạy chat-only sau khi các mục bắt buộc đã điền.
3. Tự viết `prompts/persona.md`. Muốn mode riêng thì viết thêm auto/soft/spicy; file mode trống sẽ dùng persona gốc. Bốn file public đều trống, không nhét prompt cá nhân của t vào project của m.
4. Tạo bot trong [Discord Developer Portal](https://discord.com/developers/applications), bật Message Content Intent, invite với bot + applications.commands, cho phép xem/gửi tin, đọc lịch sử và embed.
5. Check setup rồi chạy:

```sh
docker compose build
docker compose run --rm keys-keys python -m minecraft_agent.v2.configure
docker compose up -d
docker compose logs -f --tail=40
```

Checker chỉ kiểm cấu hình offline, không tự khẳng định token/SSH/server đã kết nối. Nhìn thấy `Setup OK` thì cấu hình đủ mục; nhìn thấy `KEI_READY` mới là bot đã vào Gateway. Nếu muốn chạy native/Python slot, dùng phần hướng dẫn Linux ở trên.

Provider mặc định là Gemini 3.8 Flash Medium qua 9Router. Có thể đổi `PROVIDER_MODEL` sang model tương thích tool calling. Trong Docker, localhost là chính container đó; đừng để Kei tìm 9Router trong phòng mình rồi hỏi sao không thấy.

### Cho quyền copilot

Điền server profile và `assignments` theo [ví dụ đầy đủ ở trên](#give-her-an-actual-minecraft-server). M cần Wings endpoint + daemon token, UUID server, SSH user có sudo bằng password, volume thật, UID:GID của file và verified known_hosts. Owner cũng cần assign. Chưa cần plugin bridge Minecraft; Spark dùng cho các thao tác Spark/profiler.

```text
@Kei xem TPS với RAM Survival, chỉ đọc thôi
cho t xem config anti-xray
backup server.properties rồi đổi view-distance thành 8
tìm LuckPerms đúng phiên bản, stage trước đã
hủy việc đó / tiếp tục / nhớ điều này / quên điều đó
```

### Chỉnh độ ồn, chỉnh độ dỗi

- `/debug mode:off`: tắt card, việc vẫn chạy.
- `/debug mode:minimal`: embed đỏ nhạt có objective, status và checklist.
- `/debug mode:advanced`: giữ đủ phần minimal, thêm lệnh/log thật trong codeblock. Mặc định.
- `/persona mode:auto`: linh hoạt theo mạch chat. Mặc định.
- `/persona mode:soft` hoặc `spicy`: dùng prompt nhẹ/đậm vị m tự viết.

Hai preference lưu theo user, chung DM và server. Có fallback `kei!debug <mode>` / `kei!persona <mode>`. Card được edit gọn, không spam một tin cho mỗi dòng log.

Nếu prompt của m bật dỗi: chọc quá trớn thì ẻm có thể giữ một việc mới không gấp, **chưa chạy tool**. Xin tử tế lại thì làm. Không dỗi trong lúc server đang cháy hoặc việc đã chạy. Muốn than thở thì cứ than thở, không cần mở performance profiler cho cảm xúc.

`kei!servers`, `kei!server use <id>` để chọn server; owner dùng `kei!server assign @user <id>`. `kei!clear` xóa memory cá nhân, `kei!clearall` dành cho owner.

### Phần trống là có chủ ý

Prompt/persona, env mẫu và thư mục test đều để trống cho m tự điền. Có hướng dẫn trong [prompts/README.md](prompts/README.md). Public repo không chứa token, cấu hình homelab, DB chat hay bộ test riêng của t. Đừng chạy pytest trên thư mục trống rồi khoe “test pass”. Nó chưa có gì để kiểm cả.

Built-in UI/contract trả lời hiện dùng tiếng Việt. Assignment multi-server có sẵn, nhưng nghiệm thu live ban đầu mới trên một server. Job có budget/checkpoint; plugin stage xong không đồng nghĩa plugin đã được bật; profiler có giới hạn size. Báo thành công phải có bằng chứng, không phải vì em nó nói nghe tự tin.

Lần build sau làm ngay trên repo này, bump version, ghi changelog rồi commit. Config/prompt/test riêng giữ local; kiểm staged files trước khi push. File đã track thì `.gitignore` không cứu m khỏi một cú `git add .` đáng nhớ.

---

### Credits & license

Code: **[MIT](LICENSE)**, © 2026 TonyBucket.

Experimental avatar: **Tendou Kei**. Art credit named in the supplied file: **Manic-san**; see [asset notes](assets/README.md). Character/artwork rights stay with their respective creators. MIT applies to the project code, not a surprise ownership claim over Kei.

<div align="center">

**Her server. Your problem.**

*Her problem. Your server. We'll get it right eventually.* 😭

</div>


### Eyes and receipts / Có mắt rồi, đỡ báo láo

Send a JPEG, PNG or WebP in a DM, or attach it when mentioning Kei in a server. You can also reply to your own image. Ask what you want her to read; an unexplained file is not permission to install anything. The provider must support OpenAI-compatible `image_url` content. The configured Gemini endpoint was tested with a real screenshot. Limits: four images, 8 MiB per image, 16 MiB total per turn. Images stay local for up to 24 hours; recent image context lasts ten minutes. Set `VISION_ENABLED=0` to disable.

Gửi ảnh trong DM hoặc tag Kei kèm ảnh ở server. Reply ảnh của chính m cũng được. Nói rõ muốn đọc gì; thả một file xuống không có nghĩa là “cài cái này dùm”. Endpoint phải hỗ trợ ảnh. Giới hạn như trên; `VISION_ENABLED=0` để tắt.

Search is selected by the model when a lookup, current facts or documentation is needed. No keyword bingo. Normal greetings and roleplay do not need a trip around the internet. Replies should cite the actual source URLs; if search fails, she says so.

Search do model quyết định khi cần dữ kiện mới hoặc tài liệu. “Yo” không cần tra Google giùm m 😭. Có nguồn thì dẫn link, search lỗi thì nói lỗi.

Optional local `.env` settings (keep your real values out of Git):

```dotenv
SEARCH_PROVIDER=auto
# Optional: EXA_API_KEY, FIRECRAWL_API_KEY, SEARXNG_BASE_URL
# Optional self-hosted Firecrawl: FIRECRAWL_BASE_URL
VISION_ENABLED=1
```

`auto` tries configured APIs, [Exa MCP](https://exa.ai/mcp), then keyless Bing RSS. You can select `exa`, `firecrawl`, `searxng`, `exa_mcp` or `bing_rss` explicitly. Public services can block requests; auto falls back, explicit selection reports the failure. [Exa API docs](https://exa.ai/docs/reference/search) and [Firecrawl search docs](https://docs.firecrawl.dev/api-reference/endpoint/search) explain their keys and limits. No paid account is required for the fallback; no paid quota is promised either.

A fresh server echo proves `say`/`msg` was emitted; a broadcast audit line proves the command was processed. Neither proves a human read it. Other changes still need a matching postcondition. If a check is missing, the worker checks again instead of declaring victory and then immediately saying “actually chưa xong”. ts pmo 🥀
