# Supernova 3.4.0-rc.3 — feature matrix

## 3.4.0-rc.3 task execution follow-up

- **Implemented, regression-tested:** repeated console/verification/rejected-action guards, canonical evidence comparison, no-op mutation cycles, live goal updates and checklist-only stagnation detection. Explicit monitoring and 30 distinct successful reads complete without a total turn/time limit.
- **Confirmed from real receipts:** a config reload was incorrectly certified using generic server health despite an explicit `accepted: false`. Deterministic validation now rejects that certificate before model judgment or dispatch and during completion checks. Completed historical records are not rewritten.
- **Live audit:** zero running/queued tasks at inspection; the previously interrupted task stayed paused at 173 actions. The newest diagnostic completed in 53 seconds with four real reads. Old paused/reconcile records are not currently executing.
- **Evidence:** 318 private and 68 stripped-public tests, a 12-task/468-action retained-incident replay, isolated host validation and post-deploy readiness/action-count checks. These do not establish that every future model strategy can never stall.
- **Still blocked:** original plugin runtime enablement/config application needs plugin-error repair and an authorized clean restart. No Minecraft restart was performed for this release.


## Agent-loop hotfix evidence

An actual user-requested configuration job ran 173 actions over 64 minutes. Its successful but unchanged reads bypassed the previous error-only loop guard. The new durable watchdog, replayed against the original receipts in isolation, warned at action 16 and froze unchanged evidence at action 24, 278 seconds after the first action. A real filtered log read exposed a disabled plugin and repeated classloader/zip failures; config-on-disk is not runtime enablement. Hot plugin-manager lifecycle commands are blocked, while read-only info/status commands remain available. No rank/mood policy was changed in this hotfix.

The existing task was interrupted with its complete history and a database backup preserved. Production plugin repair/restart is separate from this agent-loop fix; no successful gameplay verification is claimed.

Implemented = a code path with evidence. Partial = an important acceptance gap remains. This is a prerelease; transport mocks are not production proof.

| Feature | Status | Code and evidence | Remaining boundary |
| --- | --- | --- | --- |
| Persistent daily + personal affect | Implemented; field acceptance partial | Stored bounded daily disposition; sourced personal events decay, survive restart and enter real chat context; privacy/forgetting tests | No claims of actual sentience or offscreen experiences; multi-day field acceptance remains open |
| Immediate DBH-style rank delivery | Implemented; field acceptance partial | Confirmed old Warm event changed at 18:33 but was sent separately at 18:37; new regression binds double-arrow rank notice into the same answer, no standalone outbox | Uncertain sends are not blindly retried; background reflection changes accompany the next relevant answer |
| Crush / mutual bond / breakup | Implemented; field acceptance partial | Separate nonsexual bond axis, source/intent checks, personal opt-out, prompt breakup and no unsolicited rekindling | One-sided Crush does not claim a mutual relationship; real user acceptance pending |
| Broader typed decision routing | Implemented; field acceptance partial | Real OpenAI decisions: participation react 0.99, rank supported 0.94, unsupported mutual bond 0.80; initiative 0.64 correctly fell back; Jev contract tests | A classification call is not automatically a latency improvement; measurements required |
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
| Configurable one-turn nonurgent social holds | Implemented; field acceptance partial | Durable original goal/server, natural force/please resume, deterministic permission revalidation; urgent and scheduled work bypass holds | Social waiting is separate from operational approval; live acceptance pending |
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


## 3.4.0-rc.1 acceptance evidence

- Private regressions cover daily persistence and bounded day transitions, sourced personal affect, privacy and forgetting, one-sided crush versus explicit mutual intent, breakup/platonic boundaries, inline double-arrow rank delivery, force-resumed original work, real task launch with reaction-only acknowledgment, urgent-work bypass, and both decision-provider contracts.
- An isolated production SQLite snapshot migrated with integrity OK and the existing Warm rank intact. Actual OpenAI Decisions requests ran for participation, rank, bond and initiative. A DM thumbs-up chose react with confidence 0.99 and zero generator calls; the full turn took about 1.57 s in this probe. A normal affectionate chat replay replied through the existing chat model in about 5.46 s. These are individual measurements, not a throughput or latency guarantee.
- The initiative probe was below confidence threshold and conservatively fell back; it was not counted as an accurate decisive classification. Casual affection did not create a mutual romantic relationship. No Discord messages were sent by the isolated replay and production memories were not changed.
- Local owner UI exposed the mood/bond/work-hold controls and personal connection picker without console errors. Long-term naturalness, real-user romantic progression and mobile browser acceptance remain open. The unchanged Minecraft bridge protocol/artifact does not require a server restart for this update.


Production deployment of 3.4.0-rc.1 was verified with a fresh ready marker, database integrity OK, six required schema tables present, existing rank labels preserved, and unchanged protected config/persona/secret hashes. Existing web session records survived restart; a real authenticated owner browser refresh loaded the current version and correct profile without another login. Local application HTTP returned 200 for the landing page and 401 for unauthenticated state/global routes. The public site also loaded in the real browser. No fresh conversation failure was observed during the smoke window. This is operational verification, not multi-day social acceptance.

Regression results: **296 private checks** and **70 checks against the stripped public source** passed; JavaScript syntax and Python compilation checks also passed. The runtime and public source preserve the existing bridge protocol; no Minecraft restart was needed.
