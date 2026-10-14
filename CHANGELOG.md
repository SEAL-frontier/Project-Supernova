# Changelog

Current public version: **2.0.5**. Architecture: **Supernova**.

2.0.1–2.0.3 were numbered retrospectively from private development sessions. They are change groups, not previously published GitHub tags. The first public repository is this release. Private deployment details and prompt/test contents are not published.

## 2.0.5 — 2026-10-15 — keys-keys goes public

- Public package/repository name keys-keys; MIT code license; bilingual English/Vietnamese README and Supernova architecture description.
- Small square Tendou Kei README avatar, attribution and separate artwork rights note.
- Blank persona/mode files, blank .env.example, empty tests placeholder; generic example configuration and local-fill instructions.
- Removed hardcoded private owner naming and private deployment notes from the exported source.
- Model ID optionally configurable with PROVIDER_MODEL; Gemini 3.8 Flash Medium via 9Router remains the default.
- Offline configuration checker; empty mode prompts fall back to the local base persona rather than silently erasing it.
- Docker/Compose and native Linux setup. Public packaging uses the production module only, not the old sandbox.
- Future build policy: work in this repository, update version/changelog, validate, commit and push authorized changes; keep runtime credentials and personalization local.

## 2.0.4 — 2026-10-15 — Status that fits on a phone

- Light red embed for objective/status/checklist; advanced keeps all minimal content and adds commands/output in a codeblock.
- Existing cards migrate by editing the same message. Long labels shorten cleanly; internal goal-update markers stay out of the visible objective.
- Runtime/package/presence version synchronized. Private verification: 49 regression checks and a live Discord embed readback.

## 2.0.3 — 2026-10-15 — Keep the old voice, choose the new one

- Preserved the previous personal prompt privately.
- /persona auto, soft and spicy; per-user persistent preference and changes between worker turns.
- Context-sensitive tone; gentler responses for emotional/serious conversations.

## 2.0.2 — 2026-10-15 — Show the work

- /debug off, minimal and advanced; one durable card per task, coalesced edits and first-run hint.
- Cooldown from Discord request completion; bounded real command/stdout/stderr previews, per-task stream isolation and secret redaction.
- Visible checklist updates do not count as completion evidence.
- Optional one-turn playful refusal: hold new nonurgent work unexecuted, resume the same goal after a polite request. Urgent/ongoing work and task controls bypass persona refusal.
- Live read-only stats job verified status edits and tool evidence in the private deployment.

## 2.0.1 — 2026-10-15 — Names are not topics

- Discord user ID joins username, account display name and per-guild nickname; equal names do not merge people.
- Removed nickname prefixes from message text; separate reply-author metadata.
- Merged system context for provider adapters so persona/identity/task updates stay together.
- More natural conversational style. Private old consumer retired after migration; private configuration/data not copied into the public source.

## 2.0.0 — 2026-10-15 — Production runtime

- Discord DM/guild conversation and memory; lightweight routing versus simple/deep copilot work.
- Assignment-controlled Wings/SSH/console/files/plugin/Spark operations.
- Durable plan/act/verify loop, cancellation/goal updates, checkpoints and reconciliation for uncertain mutations.
- File backups/readback, semantic remember/forget, conservative monitoring and requester confirmation for dangerous steps.

## Before 2.0

The earlier implementation was a private experimental sandbox. This repository exports the production v2 runtime. Historical private source, secrets, chat databases and personal prompts are not a public artifact.
