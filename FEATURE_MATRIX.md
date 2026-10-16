# Supernova 3.3.0-rc.1 — feature matrix

Implemented = a code path with evidence. Partial = an important acceptance gap remains. This is a prerelease; transport mocks are not production proof.

| Feature | Status | Code and evidence | Remaining boundary |
| --- | --- | --- | --- |
| Global per-person relationship and linked-account continuity | Implemented | Global profile/rank migration, cross-context frequency, scoped raw evidence and forgetting regressions; isolated snapshot checked 15 profiles; live deployment has no channel-specific rank rows and database integrity OK | No invented affection/rank changes during migration; field progression remains under observation |
| Ranked owner overview and separate Global relationships | Implemented | Guild aggregation across channels, ranked DMs, delivery-aware active-DM labels; owner-only API tests; local UI tested with 39 synthetic people | Retained interaction counts are not lifetime totals or Discord online presence |
| Chat low / agent high, configurable | Implemented | Request-local model views; concurrent transport regression; actual Gemini 3.8 low social response + high native tool call | Custom providers need their own valid model IDs |
| Natural counters after interleaving | Implemented; field acceptance partial | Same-person bounded follow-up survives bystanders; real-model isolated replay of the reported correction/reconciliation produced replies and a sourced relationship signal | Semantic response quality still depends on the chat model; sustained live acceptance remains open |
| Personal learned nickname continuity | Implemented | Repeated sourced model-selected aliases; identity/privacy/tombstone checks; retained-owner snapshot supports keys and keys keys | Not a universal trigger; learning requires evidence |
| Four execution modes; no owner Read only option | Implemented | `permissions.py` exposes only Ask for approval, Approve for me, Full access and Custom; old rows migrate to Ask for approval; dashboard/API regressions; retained in this live version | Existing legacy rows are normalized on first policy read |
| Durable Discord dashboard login | Implemented | SQLite session records + server-side rotating OAuth refresh tokens; restart/refresh and CSRF tests; an existing production session survived this restart; `/login` redirects to OAuth | Actual browser revisit/refresh acceptance after this deployment remains unverified |
| Owner Global Overview | Implemented | Owner-only guild/DM rankings and recent DM delivery state; relationship profiles live on a separate page; raw message text is never returned and non-owner API calls get 403 | Retained counts and a recent activity window, not online presence |
| Owner Global settings | Implemented | Validated persisted role models, social/memory/reflection defaults, server-linking and new-grant settings; local browser save verified | Existing scoped grants remain unchanged |
| Personal notification controls | Implemented | Users set their own crash, moderator/admin, recovery and relationship notices; reports remain queryable when DMs are muted | Discord delivery is confirmed by outbox, not guaranteed if the recipient blocks the bot |
| DM, nickname/direct addressing | Implemented | application.py/social.py; actual Discord conversations inspected | Naturalness needs ongoing feedback |
| Nearby context, reply ancestry, webhooks | Implemented | conversation.py; default 10 messages, three ancestry steps; real multi-user corpus | Requires history permission; no guild-wide collection |
| Historical reply/react/status targets | Implemented | Existence/channel/age/own-progress validation, task source retained | Deleted targets degrade gracefully |
| Paragraphs and ack/progress ordering | Implemented | formatting.py, delivery origins and acknowledgment gates | Uncertain network sends are not blindly replayed |
| Social selection | Partial | One-pass Gemini plus optional fast decisions; real API replay | Actual replay exposed mistakes; quiet/work backend policies added, sustained acceptance open |
| Irritation never vetoes authorized work | Implemented | Separate lifecycle and permissions, work-safe reply policy | Natural-language ambiguity can still need clarification |
| OpenAI Decisions | Implemented | Official /v1/decisions, gpt-6-luna; actual API calls | Used for ambiguous participation, not every DM |
| Jev compatibility | Partial | Official System One adapter and schema-contract tests | No live Jev key/probe |
| 9router token-saver header | Implemented | Chat client sends x-9router-token-saver: off; operator OpenCode provider configured | Existing OpenCode sessions may need config reload |
| Frequency and relationship dimensions | Implemented | relationships.py; sourced sessions, separate update-credit ledger | Scores are contextual parameters, not measured feelings |
| Custom stable ranks and private profiles | Implemented | Multi-day evidence, configurable six-hour confirmation, stable-change cooldown, infrequent -# notices, self-only UI | Starts Neutral; intimacy requires opt-in and evidence; no privilege coupling |
| Episodic memory, reflection, forgetting | Implemented | Source excerpts, origin/resolution, FTS, atomic cursor, tombstones | Multi-day tests pass; multi-week field evidence remains open |
| Group intelligence | Partial | Observed participants/activity and sourced social observations | Not a complete social graph; no inferred motives as facts |
| Proactive conversation | Partial | Opt-in, relationship-adaptive caps, actual topics and contact-more/less preferences; bounded gentle followup | Field acceptance pending; unsolicited public participation removed |
| /setup and /settings | Implemented | Guided private UI, early private acknowledgments, safe error replies; CLI and real HTTP integration | Independent novice installation and another human slash-command check still needed |
| Delegated administrators | Implemented | Owner-issued revocable server scopes, grantor/history; host-shell gate also covers verification | General SSH requires operator or static host_admins; server/rank/UI profiles cannot grant it |
| Responsive OAuth dashboard | Implemented | Real Discord OAuth login on production, configured operator identity, assigned server and self profile; desktop/mobile UI | Independent novice installation remains a separate gate |
| Scheduled agent tasks | Implemented | Chat, /tasks and UI; once/daily/weekly/cron, timezone, clock confirmation | Permission rechecked at execution; sensitive steps still require approval |
| Durable scheduling | Implemented | Unique occurrences, recovery, bounded read retries, no blind mutation replay | Actual confirmed scheduled agent read ran in isolated staging; alarm receipt proves sending only |
| Panel User API + SSH | Implemented | Real status/console/file reads and task history | Password/challenge fallback varies by deployment |
| Local access without SSH | Partial | Real Windows FS/process and Linux-container FS/process checks; explicit roots/argv | Native non-container Linux and full mixed-OS networking not separately exercised |
| Paper/Leaf plugin artifact | Implemented | Packaged JAR3.1.0-rc.1; real Leaf/AuthMe/Minecraft-client/TPS/files checks | Backend rc.2 keeps protocol1; existing production rc.1 JAR retained without unnecessary restart |
| Multi-server foundations | Implemented | IDs/names/aliases, guild mappings/defaults, scoped permission, ambiguity asks | Advanced fleet orchestration deferred |
| Search UX and source counts | Implemented | Edited -# status; actual 3 page fetches across 2 sites | Failed fetches/results-only URLs do not increase fetched-site count |
| Agent/approval/audit/verification | Implemented | Existing workflow retained; actual scheduled read and fresh TPS receipt | Not every arbitrary plugin/profiler workflow is accepted yet |
| Broad proactive repairs | Partial | Existing offline/high-memory investigation retained | Wider TPS/disk/plugin diagnosis and repair policy deferred |
| Stable release | Partial | Plugin/connector and technical setup evidence exist | Social, long-term memory and independent novice acceptance still open |

## Evidence and privacy

Actual recent Discord DM/public/reply/webhook messages, five feedback entries, task/action history and application measurements were inspected first. The private corpus contains 48 sanitized excerpts in ten cases; originals and fixtures are not published. Historical search per-fetch traces were incomplete, so not every old failure can be attributed precisely.

The plugin was verified by matching the built/installed SHA256 and live connection logs, then the new distributable was tested independently on real Leaf. A scheduled agent read the actual server, reached the existing completion path and reopened without duplicate task/occurrence. Search counters and structured TPS fallback were checked against real responses. Slow tick maxima remain visible.

OAuth contract tests use a fixture issuer. Production acceptance additionally completed real Discord consent, callback and authenticated dashboard reads for the configured operator; the assigned server and private profile loaded without changing settings. This is not an independent novice trial. Private acceptance measurements stays outside the public distribution; ordinary copilot action audit remains included.

## rc.3 feedback delta

| Improvement | Status | Evidence and boundary |
| --- | --- | --- |
| Current-state minor/major notices | Implemented | Sourced dimension deltas, label-preserving category hysteresis, private regressions; no fabricated retroactive rank or Discord test spam |
| Additive custom instructions | Implemented | Chat + private modal + Web, user-level prompt context, self-only storage and forgetting; cannot authorize tools |
| DM sends and line-break bubbles | Implemented | Bounded DM historical targets, normal sends by default, compact Markdown and mini notes |
| Searchable memory library | Implemented | Self-only paginated endpoint, original excerpts, tombstone filtering and local HTTP/UI checks |
| Accessible setup/access dashboard | Implemented | Three-step setup, roster with effective permissions, display identities, mobile navigation; independent novice usability remains to be observed |
| Long-term natural social behavior | Partial | Actual conversations inspected; further real daily use required, not established by one release |

| 16 October delta | Status | Evidence / limitation |
| --- | --- | --- |
| Public trigger/followup isolation | Implemented | Per-person aliases, bystander invalidation, two-candidate cap, no ambient entry path; redacted multi-user regressions |
| Host scope and approval profiles | Implemented | Atomic owner-issued policy, scoped host checks, runtime rechecks, logged auto-review and revoke regressions; Minecraft-only is a typed tool boundary, not a kernel sandbox |
| Panel power signal translation | Implemented | Confirmed wrong payload in source and real failed action history; transport regression validates exact schema; real offline-to-running Panel start and bridge reconnection observed; fresh startup marker handles noisy logs |

Actual Panel validation probe returned HTTP 422 with `The signal field is required.` without issuing a valid power command. Current server state read back as running. Social credit regressions cover operational-noise starvation and distinct same-session apology/conflict updates.

rc.4 adds a regression for a single opted-in gentle followup about an existing retained topic, then stops after two unanswered messages. No live unsolicited DM was sent merely to test it.


## 3.2.0-rc.1 feedback delta

| Capability | Status | Evidence / boundary |
|---|---|---|
| Restart notification dedupe + grouped recovery | Implemented | Durable report keys, legacy-notice migration, restart replay regression |
| Human approval summaries + progress labels | Implemented | Raw action stays in pending/audit; public summary + exact-step button |
| Owner report archive + per-category DM preferences | Implemented | Shared Reports service; permission checks; Web and single-pass chat controls |
| Scoped co-owner and self policy editing | Implemented | Shared Access service; atomic grants; original owner protected; no implicit host escalation |
| Editable Custom per-tool rules | Implemented | Persisted per subject/server; checked at approval and dispatch |
| Minecraft connection inventory | Implemented | Configured transport names only; no credential exposure |
| Active-only schedule UI, pending edit/cancel | Implemented | Existing scheduler/history preserved; empty edited time retains old schedule |
| Line-separated conversation delivery | Implemented | Fenced code/list regression; Aris reference inspected read-only |
| Sourced event-time social delta notices | Implemented; field acceptance partial | Bounded emotional credits + cumulative net delta; stable ranks still require evidence and time |
| Stable production acceptance | Partial | Real deployment/connector checks recorded in release report; longitudinal social/novice acceptance remain open |

| Host User versus Full Machine · Root | Implemented; platform evidence scoped | Per-task identity context, sudo/direct-root UID check; Linux production sudo probe. Optional su fallback is not claimed live-accepted; Windows Administrator elevation unchanged. |


## 3.2.0-rc.2 corrective feedback delta

| Requirement | Status | Evidence / limit |
|---|---|---|
| Codex-inspired run-mode cards | Implemented | Ask for approval, Approve for me, Full access, interactive Custom; backend contract tested |
| Legacy Read only mode | Removed | Existing policy rows migrate to Ask for approval; the mode is absent from current controls and cannot be saved |
| Custom tool/path/command policies | Implemented | Strict TOML validation, actual dispatch enforcement, no scope expansion |
| Long-running jobs without overall budget pauses | Implemented | Regression exceeds former simple-turn limit; durable cycle state, real freeze reasons; I/O hangs still bounded |
| Resume same task / preserve receipts | Implemented | Explicit continuation reuses existing task; duplicate-mutation and compaction regressions |
| Missing datapack-source investigation | Implemented; user file may remain unavailable | Bounded filename search returns actual matches or a concrete missing-source question; no fabricated install |
| Follow-up replies/reactions | Implemented; field feedback ongoing | Same-person recent reply window; cheap acknowledgments; bystander and quiet boundaries retained |
| English Web UI | Implemented | Real local browser flow plus production delivery checked in operator acceptance report |
| Production/Minecraft acceptance | Scoped | Real SSH identities, live Panel/bridge/model checks; no destructive admin action run solely as a test |


## 3.2.0-rc.3 permissions UX and routing

| Requirement | Status | Evidence / limit |
|---|---|---|
| Ask for approval routes to task starter for every write | Implemented | V3 approval gate and requester-only confirm path; regression test added. |
| Approve for me routes flagged-risk writes to task starter | Implemented | Deterministic `dangerous()` gate; ordinary writes continue without a prompt. |
| Read only routes writes to eligible owner | Implemented | Owner authority checked at confirm; requester cannot self-approve. |
| Sandbox / Host / Root scope labels | Implemented | Dashboard labels retain existing backend extent values and connector checks. |
| Custom permission form without TOML | Implemented | Per-tool switches/menus, path and command patterns, guidance; backend validates before storage/dispatch. |
| Animated compact dropdowns and collapsible run mode | Implemented | Dashboard HTML/CSS/JS with keyboard controls and reduced-motion fallback. |
| Browser/device visual acceptance | Pending | Source checks and local browser pass remain required before release. |
