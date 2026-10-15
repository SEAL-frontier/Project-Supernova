# Supernova 3.1.0-rc.1 — feature matrix

Implemented = a code path with evidence. Partial = an important acceptance gap remains. This is a prerelease; transport mocks are not production proof.

| Feature | Status | Code and evidence | Remaining boundary |
| --- | --- | --- | --- |
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
| Custom stable ranks and private profiles | Implemented | Multi-day thresholds, 24h hysteresis, infrequent -# notices, self-only UI | Starts Neutral; intimacy requires opt-in and evidence; no privilege coupling |
| Episodic memory, reflection, forgetting | Implemented | Source excerpts, origin/resolution, FTS, atomic cursor, tombstones | Multi-day tests pass; multi-week field evidence remains open |
| Group intelligence | Partial | Observed participants/activity and sourced social observations | Not a complete social graph; no inferred motives as facts |
| Proactive conversation | Partial | Opt-in DMs, quiet hours, caps and unanswered suppression | Reasons mainly commitments/episodes; general public initiative deferred |
| /setup and /settings | Implemented | Guided private UI, CLI retained; real HTTP integration tests | Independent novice installation still needed |
| Delegated administrators | Implemented | Owner-issued revocable server scopes, grantor/history, backend checks | Guild/relationship ranks do not grant host access |
| Responsive OAuth dashboard | Partial | aiohttp, server-side identity/CSRF/access; HTTP fixture OAuth + real Panel-client integration | Real production Discord login needs client secret and authorized callback |
| Scheduled agent tasks | Implemented | Chat, /tasks and UI; once/daily/weekly/cron, timezone, clock confirmation | Permission rechecked at execution; sensitive steps still require approval |
| Durable scheduling | Implemented | Unique occurrences, recovery, bounded read retries, no blind mutation replay | Actual confirmed scheduled agent read ran in isolated staging; alarm receipt proves sending only |
| Panel User API + SSH | Implemented | Real status/console/file reads and task history | Password/challenge fallback varies by deployment |
| Local access without SSH | Partial | Real Windows FS/process and Linux-container FS/process checks; explicit roots/argv | Native non-container Linux and full mixed-OS networking not separately exercised |
| Paper/Leaf plugin artifact | Implemented | Packaged JAR3.1.0-rc.1; real Leaf/AuthMe/Minecraft-client/TPS/files checks | Protocol1 compatible; existing production rc.1 JAR retained without unnecessary restart |
| Multi-server foundations | Implemented | IDs/names/aliases, guild mappings/defaults, scoped permission, ambiguity asks | Advanced fleet orchestration deferred |
| Search UX and source counts | Implemented | Edited -# status; actual 3 page fetches across 2 sites | Failed fetches/results-only URLs do not increase fetched-site count |
| Agent/approval/audit/verification | Implemented | Existing workflow retained; actual scheduled read and fresh TPS receipt | Not every arbitrary plugin/profiler workflow is accepted yet |
| Broad proactive repairs | Partial | Existing offline/high-memory investigation retained | Wider TPS/disk/plugin diagnosis and repair policy deferred |
| Stable release | Partial | Plugin/connector and technical setup evidence exist | Social, long-term memory and independent novice acceptance still open |

## Evidence and privacy

Actual recent Discord DM/public/reply/webhook messages, five feedback entries, task/action history and application measurements were inspected first. The private corpus contains 48 sanitized excerpts in ten cases; originals and fixtures are not published. Historical search per-fetch traces were incomplete, so not every old failure can be attributed precisely.

The plugin was verified by matching the built/installed SHA256 and live connection logs, then the new distributable was tested independently on real Leaf. A scheduled agent read the actual server, reached the existing completion path and reopened without duplicate task/occurrence. Search counters and structured TPS fallback were checked against real responses. Slow tick maxima remain visible.

OAuth integration uses real HTTP with a fixture issuer; it is not a production Discord-login claim. Private acceptance measurements stays outside the public distribution; ordinary copilot action audit remains included.
