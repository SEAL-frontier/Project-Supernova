# keys-keys (Project Supernova)

[![Release Candidate](https://img.shields.io/badge/release-v4.6.0--rc.2-orange)](https://github.com/SEAL-frontier/Project-Supernova/releases) [![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)

> **Note**: `v4.6.0-rc.2` is a self-hosted pre-release candidate, not an officially finalized stable release. It does not claim behavioral parity with private or community-hosted deployments.

`keys-keys` is a self-hosted Discord companion and Minecraft server copilot built on the Supernova architecture. You run it on your own hardware using your own LLM API keys. It handles normal conversation, checks server health via Pterodactyl/Wings or SSH, safely surfaces command receipts, and keeps track of basic context without acting like an enterprise ticket bot.

[Vietnamese README (README.vi.md)](README.vi.md) | [Quickstart Guide](docs/QUICKSTART.md) | [Changelog](CHANGELOG.md)

<p align="center">
  <img src="assets/kei.png" alt="Tendou Kei fan tribute" width="280" />
</p>

*Character inspiration: Tendou Kei from Blue Archive. This is an independent open-source fan work under the MIT License; it is not affiliated with or endorsed by Nexon, Yostar, or the official Blue Archive project team.*

---

## Why this exists

Running a Minecraft server usually starts with wanting to build stuff with friends and inevitably turns into SSHing from your phone, parsing crash logs, and answering "is the server down?" every forty minutes.

`keys-keys` unifies chat and server utilities into one process:
- **Separation of roles**: Uses an everyday conversational model (`ag/gemini-3.8-flash-low` by default) for routine chat, while delegating command execution and server investigations to an agent model (`ag/gemini-3.8-flash-high` by default). Both endpoints are fully configurable.
- **Operational boundaries**: Routine authorized changes execute directly, but dangerous operations require explicit requester confirmation. Host-level SSH access requires dedicated permissions; being friends with the bot never grants admin rights over your machine.
- **Calculator receipts**: Restricted calculator evaluation that can render ordered formula PNGs directly to Discord for complex outputs. Native audio/video processing is not supported.
- **Self-hosted dashboard**: Contains a minimal Discord OAuth shell for server operators to manage configuration.

## Recent Changes in v4.6.0-rc.2

- **Ephemeral worker source handoff**: Passes transient source references into fresh worker inferences bounded strictly to the same actor and same scope (within a six-hour window); durable handoff states store source IDs and hashes instead of raw transcripts, and workers checkpoint for session cancellation or forgotten sources.
- **Direct message continuity boundaries**: DM continuity is strictly isolated per user; there is no automatic continuity across different scopes (including no public-to-DM transfer), and raw cross-scope transcripts are never exported.
- **Progress live-output cleanup**: When a running task initiates a new command, only the previous live command output text is cleared to prevent channel clutter, while cards, receipts, and bounded final summaries remain intact.
- **Actual completion summaries**: Saved task cards display bounded actual summaries rather than automatically assuming unchecked checklist steps are done.
- **Anchored reply notification**: Task completion notifications explicitly target the original request in the same origin channel using Discord reference semantics (`parse=[]`, `replied_user=True`) on the first segment only, avoiding duplicate pings on subsequent segments.

---

## Prerequisites

- Python `>= 3.11`
- A Discord Bot application with **Message Content Intent** enabled
- An OpenAI-compatible `/v1` endpoint supporting native function calling
- Discord OAuth credentials (only if using the self-hosted operator dashboard)

> Prompt templates, system personas, and `.env.example` placeholders are shipped empty by default. Usable system defaults are provided in the runtime configuration, and running interactive setup writes a local `data/persona.md` file using the user's provided persona choices rather than claiming an automatic persona identity.

---

## Quickstart

```bash
# 1. Clone repository
git clone https://github.com/SEAL-frontier/Project-Supernova.git
cd Project-Supernova

# 2. Virtual environment setup
python -m venv .venv
# Linux/macOS:
source .venv/bin/activate
# Windows PowerShell:
# .venv\Scripts\Activate.ps1

# 3. Install dependencies
python -m pip install -e ".[dev]"

# 4. Interactive configuration setup
keys-keys setup --config data/config.yaml

# 5. Add a target server (interactive prompt)
keys-keys server add --kind panel --config data/config.yaml

# 6. Verify configuration without spending tokens
keys-keys doctor --config data/config.yaml --offline

# 7. Start the bot
keys-keys run --config data/config.yaml
```

Running `keys-keys doctor` without the `--offline` flag makes a live health check to your configured model endpoint and will incur actual token costs.

### Running via Docker

Docker Compose files are provided in the repository as templates:

```bash
docker compose run --build --rm keys-keys setup
docker compose run --rm keys-keys doctor
docker compose up -d
```
*Note: Docker Compose definitions have been checked for file structure only; container build and runtime operations have not been validated for this release candidate.*

---

## Discord Slash Commands

The public branch provides the following slash command groups:

- `/setup` - Guided private setup and optional initial bot ownership claim.
- `/tasks` - Inspect your task history and progress.
- `/settings` - Manage server-level preferences.
- `/server connect`, `/server list`, `/server grant` - Connector bindings and access delegation.
- `/social dm`, `/social timezone` - Optional proactive messaging and local timezone configuration.
- `/privacy`, `/memory show`, `/memory forget` - Inspect and delete stored interaction history.
- `/link`, `/unlink` - Account bridge bindings.
- `/persona`, `/debug` - Bot operational inspect utilities.

---

## Privacy & Default Rules

- **Passive listening**: Ambient participation defaults to off. When enabled, channel filtering modes are configurable.
- **Proactive DMs are opt-in**: Proactive check-ins default to disabled. When enabled, baseline targets (defaulting to up to 3 messages per day and a minimum 4-hour interval) scale dynamically with context and relationship level. Quiet windows are configurable (defaulting to 22:00 to 08:00 in `Asia/Ho_Chi_Minh`).
- **Retention**: Raw transcript logs expire after 90 days by default, while curated episodic memory is retained until explicitly cleared using `/memory forget`.

---

## Test Boundaries & Verification

### Public Release Limitations & Deferred Features

- **No automatic cross-scope continuity**: Bounded continuity is strictly restricted to the same actor and same scope; public-to-DM transfer and lexical cross-scope handoffs are not supported.


Public verification runs against configured local test fixtures and mock responses, testing internal logic without requiring live Discord bots or external Minecraft servers:

```bash
python -m pytest tests -q --tb=short
```

External API errors (such as HTTP 400 responses from upstream model providers, sudden rate limits, or HTTP 200 responses returning unusable payloads) cannot be resolved automatically by local retry loops. Diagnostic utilities log sanitized error details without printing secret credentials.

---

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details. Built by NeuralSeal & TonyBucket.
