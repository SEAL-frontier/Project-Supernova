# Changelog

Current public version: **3.0.0-rc.2**. Architecture: **Supernova**.

2.0.1–2.0.3 were numbered retrospectively from private development sessions. They are change groups, not previously published GitHub tags. The first public repository is this release. Private deployment details and prompt/test contents are not published.

## 3.0.0-rc.2 — Forget means forget, even mid-consolidation

- A user forgetting a source invalidates in-flight consolidation before it can write an old summary or group profile back into memory.
- Adds a concurrent-forgetting regression; 121 private checks pass.
- Backend-only patch. The compatible protocol-v1 bridge stays at 3.0.0-rc.1; no Minecraft restart is needed.
- The clean-clone wizard/doctor flow and release gates from rc.1 remain applicable. Sustained social acceptance is still open.

VI: Bấm quên giữa lúc Kei đang tổng hợp thì kết quả cũ bị bỏ, không được nhớ lại từ cửa sau.

## 3.0.0-rc.1 — Supernova social intelligence

Release candidate. Stable is gated on natural durable social behavior, live Minecraft/plugin/connectors, and clean-clone onboarding.

- Retains the verified 2.x copilot, task ledger, monitoring, vision, search and compact debug.
- Adds social reply/short reply/reaction/silence, configured and learned aliases, opt-in initiative and group/relationship context. Ambient public participation is disabled by default.
- Adds additive schema 3, cross-platform identity, provenance-backed episodes/events, six-hour and daily consolidation, 90-day raw retention and scoped forgetting.
- Adds independent Panel API/session, Wings, SSH/SFTP and Paper bridge capability adapters. Unknown mutations require action-specific postcondition verification.
- Adds Java 21 / Paper 1.21.11 bridge, authenticated linking, DiscordSRV/AuthMe hooks, native metrics, console/files, receipts and reconnect handling.
- Adds setup/doctor/server/migrate CLI, private Discord controls, data-only Docker deployment and optional browser image.
- Default Vietnam timezone is Asia/Ho_Chi_Minh; wizard/user preferences can change it.
- Bounded memory batches resume backlog without losing same-time messages; offline Minecraft replies fall back to a linked DM.
- Acceptance: 120 private regression checks, real-model memory replay, live Minecraft/Panel checks and automated interactive clean-clone setup. Sustained social acceptance remains open, so this is a prerelease.
- Rewrites bilingual setup/docs; local personalization and credentials are generated under data/, while public placeholders remain blank.

VI: Đây là nâng cấp cả social, memory, connector và Minecraft, không chỉ thêm mắm vào persona. Chưa đủ ba cửa nghiệm thu thì giữ rc.

## 2.0.7 — The user did not press Continue

- Fixed queued Discord chat turns ending on an earlier assistant reply. Current input is now a real final `user` message, once, with its source IDs; it is no longer duplicated inside a system instruction.
- Conversation snapshots exclude later queued messages and later assistant replies, preventing one batch from consuming another user's future input.
- Images and the actual current text share the final user message, preserving the intent behind emoji-only and image turns.
- Earlier assistant claims are not evidence of user words or UI actions. Preserve ordinary emoji reactions instead of inventing continuation requests.
- 61 private regression checks, including delayed turns, interleaved speakers and multimodal message ordering.

VI: Sửa lỗi Kei tự bảo người dùng bấm Continue khi họ chỉ gửi emoji. Tin thật luôn nằm cuối đúng vai user; tin đang chờ không bị lẫn qua lượt khác. Không đổi persona.

## 2.0.6 — Receipts, eyes, and a search bar

- Fixed successful `say`, `msg` and `broadcast` being reported unfinished: fresh server log receipts now count for their actual scope. Sending a message does not mean a player read it.
- Missing readback now sends the worker back to verify, without repeating completed actions or posting a contradictory success/failure reply.
- Progress/checklist calls no longer consume the operational tool budget. Reserved finalization permits readback, never extra mutations.
- Discord image attachments and eligible replied images reach the model as native image inputs. JPEG/PNG/WebP, at most four images per turn, 8 MiB each / 16 MiB total; recent scoped context only, forgotten messages excluded. Provider rejection is explicit.
- Added semantic automatic search to chat and native `web_search` to the copilot. Auto tries configured Exa/Firecrawl/SearxNG, free Exa MCP, then Bing RSS; results are cached for five minutes and include source URLs.
- Verified the configured Gemini 3.8 Flash Medium endpoint actually read a Discord screenshot. Keyless search works on the deployed host; provider availability varies.
- Private regression checks: 58 passing. Public prompt, persona, environment and test placeholders remain blank.

VI: Lệnh đã chạy có log xác nhận thì báo đúng là xong. Thiếu hậu kiểm thì tự kiểm tra tiếp. Kei đọc được ảnh và tự tra web khi cần; chat bình thường vẫn đi đường chat.

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
