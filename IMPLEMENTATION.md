# Supernova 3.0 implementation and acceptance

Status: **3.0.0-rc.1. Not stable.**

## Release gates

- [ ] Natural social decisions and durable memory, including restart/consolidation/forgetting.
- [x] Plugin and connectors exercised on a real Minecraft server.
- [ ] A clean clone completes setup using documentation, without asking the developer.

Every gate needs recorded evidence. Passing imports or an accepted HTTP request is not a gate pass.

## Baseline

2.0.7 at `33a5ad3` already provides Discord identity, persona modes, scoped memory review,
task persistence, approval, monitoring, vision, search and live debug. These are retained.

## Work log

- Added additive schema 3, identity linking, provenance-backed relationship events and episodes.
- Added one-call social router; operations retain the existing copilot loop.
- Added optional connector registry, Panel session support and protocol-v1 outbound bridge.
- Added setup/doctor CLI and private Discord settings flows. Clean-room acceptance pending.
- Default timezone: `Asia/Ho_Chi_Minh`, configurable by wizard and user preference.
- Ambient public participation disabled by default; enabled modes are free and whitelist.
- Social DMs require opt-in; limits are three/day, four hours apart, quiet 22:00–08:00.
- Raw chat retention is 90 days; selected episode excerpts remain until forgotten.

## Recorded acceptance evidence

- 117 private regression checks pass: legacy behavior, social choices, grants, linking,
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

These are targeted technical checks, not a claim of long-term naturalness or a novice
human field trial. The rc label remains until the release gates have sufficient evidence.

## Delivery rules

No second Discord consumer. Back up the production DB and private configuration before cutover.
Keep public personalization/env/test placeholders blank. Publish an rc until all three gates pass.
