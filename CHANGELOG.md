# Changelog

Current public version: **3.2.0-rc.2**. Architecture: **Supernova**.

2.0.1–2.0.3 were numbered retrospectively from private development sessions. They are change groups, not previously published GitHub tags. The first public repository is this release. Private deployment details and prompt/test contents are not published.

## 3.2.0-rc.2 — Work until done, keep the owner inbox quiet

- Correct the run-mode contract: Default checks risky work internally; Auto-review reviews changes automatically; Full access executes authorized work without per-step prompts. Only Read only forwards a write approval to an eligible server/host owner. Reports never grant authority or imply an approval requirement.
- Replace the run-mode dropdown with clear selectable cards. Custom now edits and validates actual TOML tool/path/command rules, including allow, deny and auto_review. Scope grants remain separate from run modes.
- Remove overall job time/turn/call-budget cutoffs and the repeated “saved progress; say continue” message. Persist each cycle, retry transient model failures, and report a concrete freeze/blocker instead. Preserve I/O deadlines for hung external calls and uncertain-mutation recovery.
- Resume the same task for an explicit “continue”. Preserve completed mutation receipts across restarts/compaction and avoid executing an identical completed mutation again.
- Add bounded server filename search and persisted task-evidence retrieval. Missing source files require an upload/exact path, rather than repeatedly searching unrelated plugin folders. Compact operational noise while retaining receipts, goals and recent turns.
- Make routine delegated-admin reports opt-in. Keep report history queryable when notifications are off. Show actual current access/run-mode facts to the social router.
- Relax same-person conversation follow-ups after a real reply. Short acknowledgments can get a cheap reaction, and a legitimate continued conversation no longer fails a random participation gate. Other speakers still break the window; ambient auto-engagement stays off.
- Switch the entire Web interface to English, including dashboard, setup guidance, permission descriptions and actionable Web API errors. Personal names, memories and user-authored task/report content retain their own language.
- Fix the Web schedule example “mai 7:00” and preserve existing time when editing only a job. Completed/cancelled schedules stay out of the active list.

rc.1 snapshots were operator deployments used for feedback, not a separate public release. This prerelease includes those changes plus the corrections above; longitudinal social and independent novice acceptance remain open.

## 3.2.0-rc.1 — Less noise, actual controls

- Fix repeated restart/reconcile notices with durable per-task deduplication and grouped delivery. Import old operational results without sending them again.
- Monitor normal startup/shutdown as lifecycle states; allow ten minutes for boot. Store investigations privately, show Vietnamese summaries, suppress healthy conclusions, and use structured normal/issue/unknown outcomes.
- Store owner-scoped reports separately from DM preferences. Crash, delegated-administration and recovery notifications can each be disabled in the access UI or through explicit chat requests; saved reports remain retrievable.
- Replace the access action dropdown with named roles: viewer, moderator, admin and server co-owner. Add self policy editing, scoped co-ownership, atomic changes and a working per-tool Custom policy editor.
- Show configured connection types in the Minecraft list. Hide finished/cancelled schedules from the active list; pending schedules can be edited/cancelled, and editing only the job preserves its time.
- Split normal conversational lines into Discord messages while keeping fenced code/structured lists intact. Keep approval text with its button; approval summaries do not dump shell JSON. Remove duplicated progress prefixes and unnecessary DM task references.
- Split host scope into **Host User** (the connected SSH user, no automatic sudo) and **Full Machine · Root** (verified UID 0, configured sudo/direct-root; optional Linux su fallback). Preserve existing machine grants; isolate identities between concurrent tasks.
- Fix host inspection failing before execution when an ordinary SSH account cannot enter the Minecraft volume. Read-only inspection may use SSH home; writes require the original or explicitly selected absolute directory.
- Give the social router current execution policy and adapter capabilities. Configured SSH sudo may use stored credentials; do not claim NOPASSWD is required without checking.
- Permit bounded meaningful warm exchanges within a session. Accumulate small sourced relationship deltas over thirty minutes for DBH-style current-state arrows; retain anti-spam, cooldown, privacy/forgetting and stable-rank hysteresis.

Still a prerelease: long-term social behavior and independent fresh-user acceptance need real field feedback. Public source excludes private persona, credentials, production memories and local instrumentation.

## 3.1.0-rc.4 — One more message, when you asked for it

- Fix the gentle-followup gate: a close user who explicitly opted into more contact may receive one model-selected followup about a retained sourced topic, even if that topic initiated the first DM.
- Keep deduplication, quiet hours, relationship/cadence checks and the two-unanswered-message stop. Forgotten topics are not recreated.
- Includes the full rc.3 social, setup, dashboard, permissions and Panel/startup verification changes. Still a prerelease; long-term social and independent novice acceptance remain open.

## 3.1.0-rc.3 — A place for the conversation

- Material-inspired responsive dashboard, Kei artwork, reusable public branding, plain Vietnamese, reduced-motion support and interactive examples. Project information stays accessible after sign-in.
- Three-step private /setup, direct settings buttons, additive personal instructions through chat, Discord and Web; optional operator-wide custom_instructions. Persona and permission rules stay authoritative.
- Server access roster includes effective roles, display names, usernames, avatars where Discord supplies them, grantor and scoped capabilities. Account preview and explicit confirmation before changes.
- Searchable paginated DM memory library with original excerpts; profile preview now shows up to 12 selected memories rather than five.
- DMs send ordinary messages by default; validated intentional callbacks remain supported. Conversational line breaks stay in one message; lists, fenced code and attached mini notices stay together.
- DBH-style current-state notices: Label ↑ / ↓ for minor sourced changes, ↑↑ / ↓↓ for larger changes. Notifications respect opt-out, deduplication and a short cooldown (3 minutes for minor shifts, 45 seconds for major shifts). Long-term rank changes remain stable and evidence-based; label rewording no longer resets a pending category.
- Separate recent conversational mood from durable relationship rank; forgetting removes derived mood/signals and all-person forgetting also clears personal instructions.
- Actual DM audit informed regressions. Fixture tests do not prove sustained social naturalness; prerelease acceptance remains open.


### Additional feedback from 16 October

- Removed unsolicited public engagement, including legacy free/whitelist overrides. Public candidates now require a strong trigger, the same person's learned alias, or a bounded recent followup. Followups stop after two candidates, expire after 45 seconds by default, and end when a bystander speaks. They do not renew themselves.
- Learned aliases are scoped to person + context instead of all guild members. Weak alias/followup eligibility is deterministic per message and weighted by relationship; it only determines whether to evaluate, never grants operational authority. Configurable default trigger stays `kei`. Semantic routing can still react/silence when a name is about another Kei.
- Expanded validated reaction bank and Discord-native compact formatting. Normal chat is not split at spaces/newlines. Code fences keep their content; only Discord length limits cause splitting. DM reply references remain deliberate historical callbacks. Public typing is emitted after a reply decision, avoiding typing on ignored noise.
- Fixed the confirmed Pterodactyl/Pelican payload mismatch: `/power` needs `signal`, while Wings needs `action`. Panel failures return a short description instead of an internal URL/HTTP documentation dump. Real offline-to-running Panel start and bridge reconnection observed; startup verification uses a fresh Done marker even under log spam.
- Added two independent execution settings: Minecraft-only / Full Machine and Default / Auto-review / Read only / Full access / Custom. Host scope requires an operator-issued SSH grant; Full access alone cannot escape Minecraft scope. Auto-review uses a real model review for eligible elevated steps, preserves manual approval for destructive shell/forced kill/deletion, and logs its decision. Read only gates writes; custom tool rules are supplied in operator config. Typed Minecraft tools are not an OS sandbox.
- Opt-in proactive DMs use relationship state, meaningful topics and more/less contact preferences, not a fixed send time. Quiet hours and caps remain; one gentle unanswered followup is possible only for close users explicitly asking for more contact. Stop requests remain durable. These preferences are recorded without a technical settings receipt in conversation.
- Hero title: “Server của bạn? Để mình lo.” with “(GGEZ) 🥀”. Vietnamese copy and setup navigation rewritten in the maintained app.


- Corrected social update budgeting: operational/fact noise no longer consumes social credits. A sourced conflict followed by a real apology can update state inside the same conversation, with per-event deduplication, hourly and daily caps. This does not mint affection from repeated messages.

## 3.1.0-rc.2 — Web you can actually read

- Responsive silver, pink and crimson dashboard with plain-language setup, local avatar and accessible interaction.
- Reusable public branding; production names, community links and credentials stay in private configuration. Known profile labels are localized; custom memories remain intact.
- Private early acknowledgments and graceful command failures; refresh slash commands after Gateway connects.
- Host shell requires operator-issued host access, separately from server-scoped delegation.
- Clean-clone Docker/setup/Discord/model/Panel read integration and real production Discord OAuth verified.
- Keeps the protocol-1 bridge artifact from 3.1.0-rc.1; backend update needs no Minecraft restart.
- Still a release candidate; see FEATURE_MATRIX.md for verified and partial scope.

## 3.1.0-rc.1 — Follow the conversation, not the last message

- Guided `/setup` and `/settings`, optional Discord OAuth dashboard, revocable server access.
- Bounded Discord reply-chain context, validated historical response targets and native formatting.
- Sourced relationship frequency/ranks, private profiles and crash-safe nightly reflection.
- Local file/process connectors and a packaged Paper/Leaf bridge.
- Persistent scheduled agent tasks, timezone-aware confirmations and execution-time permission checks.
- Optional OpenAI Decision API/Jev social decisions; normal generation remains separate.
- Search progress uses fetched evidence and compact status updates.
- Explicit quiet requests and social roleplay cannot cancel legitimate assigned work.
- 9router chat requests disable provider token-saver context rewriting.
- Remains a release candidate; see FEATURE_MATRIX.md for verified and partial scope.

## Unreleased

### Documentation

- Put the project definition and reason for existing first, in both languages.
- Add a full Vietnamese README; language links open the selected file directly instead of relying on fragment scrolling in mobile clients.

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
