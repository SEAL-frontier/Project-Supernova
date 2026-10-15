<div align="center">

<img src="assets/kei.png" alt="Tendou Kei, adjusting her glasses and judging this repository" width="160" height="160" />

# keys-keys 🗝️🗝️

**An open-source Adaptive Hybrid Minecraft Server Copilot**

*Her server. Your problem.*

Actually, her problem. Your server. We got the custody arrangement wrong. 😭

![Version](https://img.shields.io/badge/version-3.0.0--rc.1-EFA5A5?style=flat-square)
![Architecture](https://img.shields.io/badge/architecture-Supernova-aca9e8?style=flat-square)
![Python](https://img.shields.io/badge/Python-3.11%2B-3776ab?style=flat-square)
[![MIT](https://img.shields.io/badge/license-MIT-efa5a5?style=flat-square)](LICENSE)

[English](#english) · [Tiếng Việt](#tiếng-việt) · [Setup](docs/QUICKSTART.md) · [Changelog](CHANGELOG.md)

</div>

---

> **3.0 is a release candidate.** Stable requires three things: natural social behavior
> with durable memory, plugin/connectors verified on a real server, and a clean-clone
> setup that does not require finding the developer. Evidence lives in
> [the implementation log](IMPLEMENTATION.md) and [feature matrix](FEATURE_MATRIX.md).

## English

### Why keys-keys?

Her name is **Kei**. Someone kept calling her **keys** to annoy her. Now the typo owns
a repository. Terrible naming process. Excellent commitment to the bit. 🥀

The experimental character/avatar is **Tendou Kei**. Your persona is yours to write.
This is a fan experiment, not an official Blue Archive product.

She has two jobs: hang out, and operate an assigned Minecraft server when asked.
“Yo” does not need an incident-response department. “Check TPS” should produce actual
TPS instead of a paragraph about how happy she would be to help someday.

### What she does

| Conversation | Minecraft copilot |
|---|---|
| Names, nicknames, group context and relationship history | Inspect TPS/MSPT, JVM memory, players, logs and plugins |
| Reply, brief reply, reaction or silence | Plan → execute → verify → adjust |
| Meaningful original episodes, not just a bag of facts | Persistent jobs, real evidence, compact live progress |
| Opt-in social initiative with quiet hours | Config backup/readback, plugin staging/install and profiler analysis |
| Discord/Minecraft continuity after verified linking | Scoped assignments, dangerous-step confirmation and recovery |
| Images and source-linked web search | Use available Panel, Wings, SSH or bridge capabilities |

**Supernova** is the architecture. The Aurora-inspired part is the social design from
the feature checklist; this does not import or depend on an Aurora repository.

```text
Discord / Minecraft
        ↓
identity + context + relevant memories
        ↓
social decision ─── ordinary chat / reaction / silence
        ↓ requested work only
copilot ─── inspect → plan → act → verify
        ↓
available connectors + persistent receipts
```

The operations worker is an agent loop. Ordinary conversation does not launch one.
Relationship state changes how she speaks, never which server she is allowed to touch.
No affection grinding your way into SSH access. Nice try.

### Get her online

Create a Discord application/token, enable **Message Content Intent**, and get a
provider key for an OpenAI-compatible endpoint with native tool calling.

```sh
git clone https://github.com/TonyBucket/keys-keys.git
cd keys-keys
docker compose run --build --rm keys-keys setup
docker compose run --rm keys-keys doctor
docker compose up -d
```

The wizard asks for language, timezone, token, provider and persona, then offers
**chat-only**, Panel, SSH or plugin bridge. You can start with chat and add a server later.
It discovers Panel servers and common SSH volumes instead of making you copy UUIDs
from three tabs and pray.

For Vietnam, choose **Asia/Ho_Chi_Minh**. Provider default:
`ag/gemini-3.8-flash-medium` through 9Router. Model ID is configurable; `doctor` checks
an actual tool call instead of trusting a model name.

If you leave owner ID blank, claim the bot using the private terminal code and `/setup`.
The token, persona, config and memory are local under `data/`, which survives updates.
Public prompt/persona/env/test files stay blank on purpose. The wizard fills **your
local files**, not GitHub's placeholders.

[Full quick start](docs/QUICKSTART.md) · [Connector choices](docs/CONNECTORS.md) ·
[Install the plugin](docs/MINECRAFT.md) · [Upgrade from 2.x](docs/UPGRADING.md)

### Defaults that matter

- Ambient public participation is **off**. Admin can enable free or whitelisted channels.
- The default trigger is `kei`; direct mentions/replies work too. Names are configurable.
- Social DMs require opt-in, at most three/day, four hours apart, with quiet hours.
- Raw conversation lasts 90 days; selected warm episodes keep useful original excerpts until forgotten.
- `discreet` can carry a low-risk hint across contexts; it does not publish DMs or private stories.
- Chat is open. Server work requires assignment. Ordinary authorized work runs; dangerous steps need confirmation.
- A plugin cannot start its own stopped server. A staged JAR is not an enabled plugin.

### The commands you will actually use

| Command | Job |
|---|---|
| `/server connect`, `/server list`, `/server grant` | Connect a Panel privately and manage access |
| `/link`, `/unlink` | Connect or separate Minecraft identity |
| `/social dm`, `/social ambient`, `/social timezone` | Decide how much she appears in your life |
| `/privacy`, `/memory show`, `/memory forget` | Inspect and control memory |
| `/persona auto/soft/spicy` | Choose the old, stronger or adaptive style |
| `/debug off/minimal/advanced` | Choose job progress detail |
| `/kei <message>` in Minecraft | A private ingame conversation |

Examples: “Show the current anti-xray config”; “Find why TPS dropped, do not change anything”;
“Stage this compatible plugin, leave restart for later”; “Remember why keys keys became a joke.”

### Documentation

[Setup](docs/QUICKSTART.md) · [Configuration](docs/CONFIGURATION.md) ·
[Connections](docs/CONNECTORS.md) · [Minecraft](docs/MINECRAFT.md) ·
[Social/memory/privacy](docs/SOCIAL.md) · [Updates/recovery](docs/UPGRADING.md) ·
[Troubleshooting](docs/TROUBLESHOOTING.md)

## Tiếng Việt

Kei vừa chat vừa làm Minecraft copilot. Chat thường đi đường nhẹ; nhờ việc thì mới
chạy agent có plan, tool, hậu kiểm và tiến độ. Không phải cứ nhắc Minecraft là em nó
phi vào SSH như đi đánh trận.

3.0 thêm relationship theo người/ngữ cảnh, kỷ niệm có đoạn hội thoại gốc, react/im lặng,
nhắn chủ động có opt-in và chatbot ingame. Giữ agent, vision, search và debug từ 2.x.
Điểm thân thiết là ngữ cảnh cho nhân vật, không phải cảm xúc thật hay thẻ admin.

### Cài đỡ khổ

Chạy các lệnh ở phần English, chọn tiếng Việt trong wizard. Nó tự tạo file riêng trong
`data/`; không cần sửa YAML trước. Chưa có server thì chọn `chat`. Có Panel thì đưa URL
và Client API key rồi chọn server. Có SSH thì dò thư mục. Có plugin thì nhận pairing
config được tạo sẵn. Có gì dùng nấy, không bắt đủ nguyên bộ.

Tạo bot trên [Discord Developer Portal](https://discord.com/developers/applications),
bật Message Content Intent và invite đủ quyền. Hướng dẫn từng bước ở
[QUICKSTART](docs/QUICKSTART.md). Windows dùng Docker/WSL; Linux hoặc Pelican Python slot
có hướng dẫn native trong cùng tài liệu.

Mặc định timezone Việt Nam là **Asia/Ho_Chi_Minh**, wizard cho đổi. Đừng dùng localhost
của container để gọi provider trên host rồi đổ tại em nó 🦭

### Nói chuyện và giao việc

- Public tự xen tắt mặc định. Bật thì chọn `free` hoặc `whitelist`.
- Mặc định gọi `kei`; deployment riêng có thể thêm Keys Keys, Cây hoặc nickname đã học.
- Có thể đáp một câu, một câu ngắn, react hoặc im. Không phải tin nào cũng cần tranh micro.
- DM chủ động phải opt-in; tối đa 3 lần/ngày và không đuổi theo khi m không trả lời.
- Chat thô 90 ngày; episode quan trọng giữ đoạn gốc cần thiết. Quên thì xóa cả phần dẫn xuất.
- Người thường chat được. Copilot cần assign đúng server; link Discord/UUID không tự cấp quyền mới.
- Plugin chạy network nền; phần cần Bukkit API về scheduler. Model không ngồi trên tick thread.

`/debug minimal` hiện objective/checklist trong embed hồng nhạt; `advanced` thêm codeblock
lệnh/log thật. Persona cũ vẫn có ở `soft`; không cần dỗ mới chịu làm việc nữa.

“Check TPS với RAM Java server này”; “Đọc anti-xray hiện tại”; “Tìm nguyên nhân lag,
chưa sửa gì”; “Stage plugin tương thích rồi báo lại.” Đã làm thì phải có bằng chứng,
không có chuyện 200 OK xong tự phong chiến thắng.

### Version và giới hạn

**3.0.0-rc.1 chưa phải stable.** Ba cửa nghiệm thu ở đầu README phải có bằng chứng.
Xem [feature matrix](FEATURE_MATRIX.md), [implementation log](IMPLEMENTATION.md) và
[changelog](CHANGELOG.md); không lấy một bài test mock làm bằng chứng server thật.

Mỗi connector có giới hạn. Plugin-only không bật lại server đã tắt; login Panel có thể
cần browser tùy chọn hoặc session đã xác thực. Không hot reload plugin. Một bot token,
một consumer, không phải hai chị em cùng trả lời một tin rồi hỏi sao nó lắm mồm.

## License and avatar

Code: [MIT](LICENSE). Character/avatar: Tendou Kei, experimental fan use.
The supplied art filename credits Manic-san; see [asset notes](assets/README.md).
The code license does not relicense the character or artwork.
