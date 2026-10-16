# Changelog

Current public version: **3.4.0-rc.2**. Architecture: **Supernova**.

2.0.1–2.0.3 were numbered retrospectively from private development sessions. They are change groups, not previously published GitHub tags. The first public repository is this release. Private deployment details and prompt/test contents are not published.

## 3.4.0-rc.2 — Stop investigating the same evidence forever

- Confirmed a real configuration job spent over an hour repeating successful file reads and near-identical documentation searches. Add durable per-task evidence fingerprints: repeated successful reads receive a strategy warning, then a concrete freeze if the same evidence is requested again. This is a no-progress check, not an overall job timeout. Explicit live monitoring can still collect unchanged samples.
- Preserve completed mutation receipts during history compaction, even after newer read-only noise pushes them outside the most recent receipt window. Repeated rejected completion claims now surface their exact missing verification.
- Add literal plugin filters to log inspection. Reading `logs/latest.log` now returns the latest window rather than an obsolete file prefix; matching log inspection can read plugin-specific lines past high-volume world-generation chatter.
- Reject unsafe hot plugin lifecycle operations through PlugMan, which produced observed classloader errors in the incident. Recognize its info/status/test commands as reads, including old saved actions during completion checks. Do not claim plugin enablement from an accepted command.
- Enforce explicit `site:` search restrictions before fetching fallback results. Unrelated fallback pages become an empty search instead of useful-looking evidence.
- Show a concrete paused/failure reason on the existing progress card. Preserve task history and backups when interrupting a confirmed loop.

Validation: real 173-action incident replay warns at call 16 and identifies stagnation at call 24 (278 seconds); actual filtered production plugin logs expose the classloader failure. No Minecraft restart or plugin reinstall was performed solely for this hotfix. Relationship/rank behavior is unchanged.

## 3.4.0-rc.1 — A mood that carries into the next conversation

- Add persistent daily character disposition and sourced, decaying personal mood. Feed both into actual chat context while preserving the configured core persona. Warmth can be sincere; playful sulking remains contextual at any rank. Daily variation never invents offscreen experiences or changes server rights.
- Keep friendship/trust rank separate from transient mood and romantic connection. A sourced one-sided Crush can develop organically; Lover needs explicit human romantic interest and meaningful history, without a fourteen-day ladder. Breakup/stop-flirting is respected and blocks unsolicited rekindling. Personal platonic/invited-only/organic controls are available in chat, Discord and Web settings.
- Fix the confirmed delayed Warm notification: rank changes bind to the current relevant answer, use double arrows, and are acknowledged after delivery. Remove the five-minute background standalone rank DMs. Small sourced point changes can retain the current rank with a single arrow; significant deltas use two.
- Relax negative-rank evidence away from literal stop keywords and two-calendar-day conflict requirements. Require sourced repeated conflict/loss of trust, independent confirmation and stable-change cooldowns. Major conflict/reconciliation/milestone events may apply proportionate larger steps; ordinary teasing stays minor.
- Expand typed OpenAI Decisions / Jev judgments to eligible short/direct acknowledgments, personal nickname and follow-up participation, proposed rank/bond transitions and opted-in initiative. Full conversational requests keep the direct generator path. Uncertain/refused/failed decisions fall back; all permission checks remain deterministic.
- Add configurable, durable one-turn social work holds for nonurgent directly assigned jobs. A natural please/do it/force resumes the original scoped job with permission revalidation. Emergencies, forced/repeated requests and scheduled workflows cannot be stalled this way. A thumbs-up acknowledgment can launch real work without a conversational paragraph.
- Add global mood/bond/work-sulk controls and personal romance preferences. New relationship profiles explain uncalibrated defaults instead of displaying neutral priors as established judgments. Preserve original profiles, private persona, scoped excerpts and forgetting boundaries.

Validation: 296 private and 70 stripped-public regression checks, local browser controls, isolated production-snapshot migration, actual OpenAI Decisions + existing chat model replay, and live deployment with authenticated owner refresh/session persistence; detailed evidence is recorded in FEATURE_MATRIX.md. This remains a prerelease: simulated cycles and API-backed replay do not establish sustained live social quality.

## 3.3.0-rc.1 — One person, one relationship

- Unify numeric relationship state, frequency and durable rank across a linked person's DMs, guilds and Minecraft identity. Migrate existing profiles once without adding repeated channel baselines; keep contextual addressing, private excerpts and original evidence scoped. Forgotten contributions cannot reappear through a global aggregate.
- Rebuild Global Overview around ranked Discord guilds and DMs. Aggregate channels into their guild, show delivery-aware recent DM activity, per-person top guilds and DM counts, and collapsible large sections. Move global relationships into a separate searchable, paginated screen with compact/expanded dimensions.
- Expand owner settings with separate chat/agent model IDs, configurable trigger/follow-up behavior, memory/reflection limits, quiet hours, proactive caps and relationship-notice sensitivity. Settings persist in this deployment and apply to new work without a restart.
- Default Gemini 3.8 chat to low and agent/tool work to high. Model selection is request-scoped, so concurrent chat cannot change a worker's model. Non-Gemini configurations retain the chosen provider model unless role models are explicitly set.
- Preserve the addressed person's follow-up when bystanders interleave. Use a configurable window after actual replies and a bounded candidate count; unrelated users still do not inherit participation. A contextual challenge/correction can receive a natural counter or reaction.
- Learn model-identified nicknames from repeated retained messages of the actual speaker, across that person's permitted contexts. Nicknames never become universal triggers.
- Accept raw-newline/fenced social JSON safely in the social parser, increase response/repair budgets, and log safe parser offsets. Operational tool arguments remain strict. Confirmed production failures were JSON parse errors; the rejected payloads were not retained, so the exact malformed bytes are unknown.
- Let a later substantive exchange confirm an already-proposed stable rank using global history. Default confirmation is six hours; rank notices have a six-hour cooldown. Meaningful social events can update dimensions without inventing a new fact, with source dedupe and bounded credits. Minor/major notices retain the current-label arrow format.

Validation: 284 private regressions and 58 checks against the stripped public source passed, including custom-provider setup round trips. Local owner UI save/pagination/collapse, actual low/high model probes, real read-only connector status, and isolated production-snapshot migration were checked. Production now runs this version with a fresh ready marker, database integrity OK, unchanged protected configuration/persona/secret hashes, no channel-specific rank rows and an existing web session retained through restart. A real-model replay of the reported counter/reconciliation exchange produced replies and a sourced relationship signal in an isolated snapshot; sustained conversation quality and natural rank progression still require real use. Interactive production-owner and mobile browser acceptance remain open. This is a prerelease.

## 3.2.0-rc.4 — Owner controls and a dashboard that stays signed in

- Remove the retired **Read only** execution mode entirely. There are four choices: **Custom**, **Approve for me**, **Ask for approval**, and **Full access**. Existing legacy `read_only` rows migrate to the safer task-starter approval mode; owners never need approval from themselves.
- Keep Discord sign-in across browser visits and service restarts with durable server-side sessions, rotating OAuth refresh tokens, rolling expiry, CSRF checks, and permission revalidation. OAuth tokens stay in the server secret store.
- Add an owner-only **Global Overview** with aggregate interaction counts, active DM/channel sessions, most active conversations and servers, server/player status, and per-context relationship rank and dimensions. It never returns raw message text.
- Add owner-only global defaults for timezone, self-service server linking, and the default approval mode for new grants. Existing per-server grants and personal preferences remain independent.
- Move crash, moderator/admin, recovery, and relationship-rank notices into personal notification settings. Each user can choose their own notices; server reports remain saved and retrievable when DM notifications are muted.
- Add endpoint regressions for owner-only global routes, aggregate-only overview data, persistent sessions, token refresh, and the four supported execution modes.

This remains a prerelease. Production is running rc.4 with the SQLite database intact, the startup marker verified, and production config/persona/secret hashes unchanged. Live `/` and `/login` return HTTP 200/302, and an unauthenticated `/api/state` returns 401. Existing rc.3 browser sessions were memory-only, so users may need to sign in once after this upgrade; actual interactive re-login and refresh across a later restart still need browser acceptance.

## 3.2.0-rc.3 — Permissions people can actually understand

- Align approval routing with the picker: Ask for approval asks the task starter before every change; Approve for me asks that person only for changes flagged by deterministic risk checks.
- Rename the scope selector to Access level and show Sandbox (Minecraft server only), Host (SSH user permissions, no automatic sudo) and Root (full machine control).
- Replace TOML-only Custom configuration with an interactive permission form: per-tool switches, per-tool decision menus, fallback behavior, file path rules, SSH command blocks and lower-priority guidance. The backend still validates and enforces every rule.
- Clarify Admin access: it applies to the Admin role and controls server view/operation access; owner and host authority stay separate.
- Make run-mode, access, role and report pickers compact, expandable and animated, with reduced-motion support.

## 3.2.0-rc.2 — Work until done, keep the owner inbox quiet

- Keep the previous internal policy values behind the updated labels for stored-data compatibility. New saves and action dispatch now apply the rc.3 approval destinations above. Reports never grant authority or imply an approval requirement.
- Replace the run-mode dropdown with clear selectable cards. Custom now edits and validates tool/path/command rules in the dashboard form, including allow, deny, ask and auto-review. Scope grants remain separate from run modes.
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
