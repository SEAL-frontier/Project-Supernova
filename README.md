<div align="center">

<img src="assets/kei.png" alt="Tendou Kei, adjusting her glasses and judging this repository" width="160" height="160" />

# keys-keys 🗝️🗝️

**An open-source Adaptive Hybrid Minecraft Server Copilot**

*Her server. Your problem.*

Actually, her problem. Your server. We got the custody arrangement wrong. 😭

![Version](https://img.shields.io/badge/version-4.0.0--rc.2-EFA5A5?style=flat-square)
![Architecture](https://img.shields.io/badge/architecture-Supernova-aca9e8?style=flat-square)
![Python](https://img.shields.io/badge/Python-3.11%2B-3776ab?style=flat-square)
[![MIT](https://img.shields.io/badge/license-MIT-efa5a5?style=flat-square)](LICENSE)

[English](README.md) · [Tiếng Việt](README.vi.md) · [Setup](docs/QUICKSTART.md) · [Changelog](CHANGELOG.md)

</div>

## What is this project?

**keys-keys is a self-hosted AI bot that lives in Discord and Minecraft.** People can
chat with her in DMs, server channels or in-game. Assigned admins can also ask her to
operate their Minecraft server: check TPS/RAM, investigate lag, read or change configs,
manage plugins and run server commands. She uses real tools and checks the result.

The Python bot runs the conversation, memory and agent. It connects through your Panel,
SSH or the optional Minecraft plugin, using what you have available. One bot can serve
multiple people and assigned servers. You bring a Discord token, a model endpoint and
your own persona; start chat-only and add Minecraft when ready.

## Why does this project exist?

Because running a Minecraft server turns “let me play for a bit” into opening a panel,
SSH, three logs, a config file and a plugin release page. Someone says “server lag”
and suddenly you have a second job. Unpaid, naturally. 🥀

We wanted one character who could hang out with the group **and do that server work
when asked**, in the same conversation. Casual chat should feel like chat. A server
request should lead to an investigation, actions and a result backed by evidence.

That is why **Supernova** separates ordinary conversation from the copilot agent,
and keeps memory, task progress and server access together. “Adaptive” means choosing
the right kind of work; “hybrid” means using the connections available on that server.
The open-source goal is to let other people run that setup with their own servers,
models and characters. The original experiment happened to hand the job to Tendou Kei.
She received a Minecraft server instead of a peaceful afternoon. 😭

> **4.0.0-rc.2 is a release candidate.** Stable requires three things: natural social behavior
> with durable memory, plugin/connectors verified on a real server, and a clean-clone
> setup that does not require finding the developer. Evidence lives in
> [the implementation log](IMPLEMENTATION.md) and [feature matrix](FEATURE_MATRIX.md).

### Why the name keys-keys?

Her name is **Kei**. Someone kept calling her **keys** to annoy her. Now the typo owns
a repository. Terrible naming process. Excellent commitment to the bit. 🥀

The experimental character/avatar is **Tendou Kei**. Your persona is yours to write.
This is a fan experiment, not an official Blue Archive product.

[New in 4.0: conversations, relationships and guided server setup](docs/RELEASE_4.md)

### Start here

Use **`/setup`** once and **`/settings`** later. Personal preferences, privacy,
relationship profile, linked accounts and assigned servers live there.
[Discord + optional Web UI](docs/SETTINGS.md) · [Local files without SSH](docs/LOCAL_ACCESS.md)
· [Install the Minecraft plugin](docs/BRIDGE_INSTALL.md).

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
| `/social dm`, `/social timezone` | Decide how much she appears in your life |
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

## License and avatar

Code: [MIT](LICENSE). Character/avatar: Tendou Kei, experimental fan use.
The supplied art filename credits Manic-san; see [asset notes](assets/README.md).
The code license does not relicense the character or artwork.
