# Supernova 3.0 implementation and acceptance

Status: **3.0.0-rc.2. Not stable.**

## Release gates

- [ ] Natural social decisions and durable memory, including restart/consolidation/forgetting.
- [x] Plugin and connectors exercised on a real Minecraft server.
- [x] Automated clean-clone setup completes through the documented interactive wizard and doctor.

Every gate needs recorded evidence. Passing imports or an accepted HTTP request is not a gate pass.

## Baseline

2.0.7 at `33a5ad3` already provides Discord identity, persona modes, scoped memory review,
task persistence, approval, monitoring, vision, search and live debug. These are retained.

## Work log

- Added additive schema 3, identity linking, provenance-backed relationship events and episodes.
- Added one-call social router; operations retain the existing copilot loop.
- Added optional connector registry, Panel session support and protocol-v1 outbound bridge.
- Added setup/doctor CLI and private Discord settings flows. Clean-room wizard and live doctor verified.
- Default timezone: `Asia/Ho_Chi_Minh`, configurable by wizard and user preference.
- Ambient public participation disabled by default; enabled modes are free and whitelist.
- Social DMs require opt-in; limits are three/day, four hours apart, quiet 22:00–08:00.
- Raw chat retention is 90 days; selected episode excerpts remain until forgotten.

## Recorded acceptance evidence

- 121 private regression checks pass: legacy behavior, social choices, grants, linking,
  episodes, privacy, retention, forgetting, proactive gates, exact-source verification,
  setup/claim and durable Minecraft progress.
- Real-model replay preserves a nickname-origin episode after database reopen and deep
  consolidation; an explicit request not to tease changes the response appropriately.
- A real isolated Leaf 1.21.11 server loads the bridge with AuthMe. A Minecraft protocol
  client registers, logs in, links Discord, chats, requests TPS/JVM memory and completes
  a staged YAML write/readback. Both copilot jobs finish with actual server evidence.
- Real Panel client API discovers servers, reads running resources, writes/reads/removes
  a staging file and executes a read-only console command. Existing Wings+SSH reads pass.
- The Java bridge builds successfully with Maven/Java 21. Source/model input contains
  no deployed credentials. Provider reasoning is stripped from history/debug.

- A fresh GitHub clone builds its Docker image, completes interactive English chat setup
  and Panel discovery without copying UUIDs, then passes live Discord/provider/Panel doctor.
  Public templates and the tracked checkout remain unchanged. No second Gateway consumer runs.
- Production cutover preserves the previous persona/config/database backup. The Discord
  Gateway starts on 3.0.0-rc.1; the production Leaf server loads the plugin after a normal
  restart and returns fresh TPS/JVM metrics through the authenticated bridge.
- Memory jobs keep bounded resumable batches, including equal-time messages; backlog
  continues on maintenance ticks instead of waiting another six hours. Earlier summaries
  accompany the next batch. An offline Minecraft reply can fall back to its linked DM.

These are targeted technical checks, not a claim of long-term naturalness or a novice
human field trial. The social gate remains open for sustained real-user acceptance;
therefore this release stays rc. A fully independent human setup trial is also welcome.

## rc.2 backend patch

Concurrent scoped forgetting invalidates a pending model consolidation before any
summary, group profile or memory update is persisted. A deferred-response regression
covers the race. The rc.1 bridge stays protocol-compatible and needs no server restart.
The clean-clone acceptance was run on rc.1; rc.2 leaves that CLI flow unchanged.

## Delivery rules

No second Discord consumer. Back up the production DB and private configuration before cutover.
Keep public personalization/env/test placeholders blank. Publish an rc until all three gates pass.
