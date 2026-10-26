<div align="center">

<img src="assets/kei.png" alt="Tendou Kei, adjusting her glasses and judging this repository" width="160" height="160" />

# keys-keys 🗝️🗝️

**An open-source Adaptive Hybrid Minecraft Server Copilot**

*Her server. Your problem.*

Actually, her problem. Your server. We got the custody arrangement wrong. 😭

![Version](https://img.shields.io/badge/version-4.6.1-EFA5A5?style=flat-square)
![Architecture](https://img.shields.io/badge/architecture-Supernova-aca9e8?style=flat-square)
![Python](https://img.shields.io/badge/Python-3.11%2B-3776ab?style=flat-square)
[![MIT](https://img.shields.io/badge/license-MIT-efa5a5?style=flat-square)](LICENSE)

[English](README.md) · [Tiếng Việt](README.vi.md) · [Setup](docs/QUICKSTART.md) · [Changelog](CHANGELOG.md)

</div>

## What is this project?

**keys-keys is a self-hosted AI companion for Discord and a copilot for Minecraft servers.**
People can talk to her in DMs, server channels or through the optional Minecraft bridge.
Assigned admins can ask her to check TPS/RAM, investigate lag, inspect configs, manage
plugins and run server commands. Conversations use a chat model; server work uses a
separate tool loop with saved progress and execution evidence.

You supply a Discord token, an OpenAI-compatible model endpoint and a persona. The bot
runs on your machine or VPS. Start with chat only, then connect a Panel, SSH, a local
server directory or the Minecraft bridge when you need it. One instance can serve
several people and separately assigned servers.

## Why does this project exist?

Because “let me play for a bit” somehow turns into opening a panel, SSH, three logs,
a config file and a plugin release page. Someone says “server lag” and suddenly you
have a second job. Unpaid, naturally. 🥀

We wanted one character who could hang out with the group **and do that server work
when asked**, in the same conversation. Casual chat should feel like chat. A server
request should lead to an investigation, permitted actions and a useful result—not a
promise to help followed by an impressive amount of nothing.

**Supernova** separates those paths while keeping identity, memory and server access
connected. “Adaptive” means choosing the appropriate kind of work; “hybrid” means using
the connections the server actually has. The point of opening the source is that you
can run it with your own servers, models and character. We gave Tendou Kei a Minecraft
server instead of a peaceful afternoon. This may explain a few things.

> **4.6.1 is the stable public release.** Self-hosted behavior still depends on your
> model, connector permissions and configuration. This repository is not a copy of a
> private hosted bot's deployment or community rules. Version-specific changes belong
> in the [changelog](CHANGELOG.md), not in the middle of your setup instructions.

### Why the name keys-keys?

Her name is **Kei**. Someone kept calling her **keys** to annoy her. Now the typo owns a
repository. Terrible naming process. Excellent commitment to the bit. 🥀

The experimental character/avatar is **Tendou Kei**. Your persona is yours to write;
the shipped persona files are intentionally empty. This is a fan project, not an
official Blue Archive product.

## What she does

| Conversation | Minecraft copilot |
|---|---|
| Names, nicknames, scoped history and relationship context | Inspect TPS/MSPT, JVM memory, players, logs and plugins |
| Reply, short reply, reaction or silence | Inspect → plan → act → verify → adjust |
| Selective memories and original episodes, not every greeting forever | Persistent tasks, saved actions and compact progress |
| Opt-in proactive DMs with configurable quiet hours | Config backups/readback, plugin staging and profiler analysis |
| Verified Discord/Minecraft account linking | Per-person server assignments and dangerous-step confirmation |
| Images, source-linked web lookup and restricted calculation helpers | Panel/Wings compatibility, SSH, local files or bridge capabilities |

Recent conversational choices can follow the same requester into a worker rather than
making it hunt for a “template” you just discussed. The handoff is bounded and
source-checked; it does not grant permission to operate a server. Task cards show the
saved result, and starting another command clears the previous command's live output—not
the evidence that an action happened.

Nearby conversation evidence stays in the current channel or DM and carries explicit
partial-coverage metadata; omitted messages are unknown. Direct names and current dialogue
use the main response pass. Repeated acknowledgment suppression requires a previously
accepted observation in the same bounded run, not just a short message. The public build
retains its existing daily presence behavior; the private full status controller and
scheduled-data integration are not included.

Math stays in the chat path. A restricted calculator supplies numerical results, and
local formula rendering can send an actual PNG between text messages. It is not an image
model, a general-purpose code sandbox or proof the Minecraft bridge supports images.

```text
Discord / Minecraft
        ↓
identity + permitted context + relevant memories
        ↓
conversation ─── reply / reaction / silence
        ↓ requested server work only
copilot ─── inspect → plan → act → verify
        ↓
configured connectors + saved execution evidence
```

Relationship state changes how she speaks, never which server she can touch.
No affection grinding your way into SSH access. Nice try.

### Ask her to pass something on

Use ordinary chat to send a selected point, link or indexed attachment to a named person,
ask them a question and bring back their answer, or deliver your own report/reminder by DM.
Mentions, user IDs, usernames and available server nicknames can identify a recipient; an
ambiguous name needs clarification, not a guessed DM.

You can choose a time, an existing job's completion or the next time that person actually
talks to Kei. This is not an online-status watcher. Unsent messages can be changed or
cancelled; recipients can postpone or decline. Replies return privately by default, and
selecting a destination never grants access to unrelated private history. There are no
ticket cards or mandatory delivery announcements for these exchanges.

## Start here

**Two Discord entry points. Not a wall of slash commands.**

- **`/settings`** opens your private controls: setup, persona, memory/privacy, relationship
  profile, account linking, schedules, progress preferences and Minecraft connections.
- **`/server`** opens the Minecraft connection menu. Inspect assigned/visible servers and use the
  relevant management controls; buttons remain bound to the person who opened them.

Use normal conversation for questions and requests. You do not need to memorize the old
`/social`, `/memory`, `/link`, `/debug` or `/server connect` command families; their
supported controls live in the menus instead. Minecraft's optional `/kei <message>`
bridge command is a different interface.

Examples:

> “Show the current anti-xray config.”
>
> “Find why TPS dropped. Don't change anything yet.”
>
> “Stage this plugin, but leave the restart for later.”
>
> “Remember why keys keys became a joke.”

[Discord + Web UI](docs/SETTINGS.md) · [Schedules](docs/SCHEDULED_TASKS.md) ·
[Local files without SSH](docs/LOCAL_ACCESS.md) · [Bridge installation](docs/BRIDGE_INSTALL.md)

## Get her online

You need Python **3.11+**, a Discord application/token with **Message Content Intent**
enabled, and a model endpoint that supports native function calling. For Discord, grant
access to the intended channels and the permissions needed to send messages, read their
history, embed links, attach files and react. Connector permissions are configured
separately; a Discord role name is not a server credential.

```sh
git clone https://github.com/SEAL-frontier/Project-Supernova.git
cd Project-Supernova
python -m venv .venv

# Linux / macOS
source .venv/bin/activate
# Windows PowerShell: .venv\Scripts\Activate.ps1

python -m pip install -e ".[dev]"
keys-keys setup --config data/config.yaml
keys-keys doctor --config data/config.yaml --offline
keys-keys run --config data/config.yaml
```

The wizard asks for language, timezone, token, provider and persona, then lets you start
chat-only or configure a server connector. For Vietnam, choose **Asia/Ho_Chi_Minh**.
An online `doctor` check—without `--offline`—contacts configured services and may spend
model tokens. An offline check validates local setup; it does not prove connectivity.

The provider base is the endpoint's **`/v1`** URL, not a website login page. Chat and
agent model IDs are configurable. The supplied defaults use Gemini Flash Low for chat
and Flash High for work; you can set both roles to the same suitable model. Optional
decision support is off by default. Those are self-hosted defaults, not a promise that
every provider accepts the same schemas or model IDs.

Secrets, generated persona, config and memory stay in your local `data/` directory.
Keep it private and back it up before updating. The public `.env.example` and persona
placeholders are empty on purpose; they are not a character or a set of credentials to
copy from someone else's installation.

### Prefer Docker?

The repository also includes a Compose setup:

```sh
docker compose run --build --rm keys-keys setup
docker compose run --rm keys-keys doctor
docker compose up -d
```

Your provider URL must be reachable **from the container**. `localhost` inside the bot
container is the bot container, not your host's model service. Compose files are supplied;
container build/runtime acceptance is separate from the offline Python tests.

[Full quick start](docs/QUICKSTART.md) · [Connector choices](docs/CONNECTORS.md) ·
[Configuration](docs/CONFIGURATION.md) · [Upgrade and recovery](docs/UPGRADING.md)

## Defaults worth knowing

- Public ambient participation is off by default; direct invitations and permitted
  follow-ups are distinct from listening to an entire channel.
- The default call name is `kei`. Mentions/replies and configured names also work.
- Proactive DMs are opt-in. Daily and interval settings are contextual controls, not a
  requirement to produce a message; quiet hours and unanswered-contact checks still matter.
- Raw chat has a default 90-day retention window. Selected episodes have their own
  retention rules; privacy controls can explicitly forget their supported sources.
- `strict` keeps memory scoped; `discreet` can carry permitted low-risk hints. Neither
  means publishing someone's raw private conversation in another audience.
- Server work needs a real assignment/capability. Observe mode cannot modify a server;
  ordinary authorized changes can run, while dangerous steps require confirmation.
- A Minecraft plugin cannot start its own stopped server. A staged JAR is not an enabled
  plugin. An accepted command is not automatically a verified outcome.

## Web dashboard

The optional web interface is an authenticated dashboard with a minimal Discord OAuth
login shell—not the project's private introduction website. Configure OAuth before
expecting sign-in to work. UI visibility does not replace the backend's permission checks.

## Development and limits

```sh
python -m pytest tests -q
python -m pip wheel . --no-deps --wheel-dir dist
```

Public tests use synthetic model/Discord boundaries, disposable data and real local PNGs.
They are not live Minecraft, Discord-client notification or Docker acceptance. Native
video/audio understanding is not implemented. Local error handling cannot universally fix
upstream HTTP errors, provider safety blocks or an HTTP 200 with no usable model output.

For installation problems, start with [Troubleshooting](docs/TROUBLESHOOTING.md). See
[Social/memory/privacy](docs/SOCIAL.md) and [Minecraft](docs/MINECRAFT.md) for behavior and
connector details. Submit a focused issue or PR with reproducible steps, but remove
credentials, persona, private conversations and server addresses from logs first.

## License and avatar

Code: [MIT](LICENSE), developed by **TonyBucket / NeuralSeal**. Character/avatar:
Tendou Kei, experimental fan use. The supplied art filename credits Manic-san; see
[asset notes](assets/README.md). The code license does not relicense the character or
artwork, and this project is not affiliated with the original rights holders.
