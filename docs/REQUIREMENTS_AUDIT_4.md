# Approved feedback audit — 4.0.0-rc.2

This reconstructs 35 acceptance checkpoints from the approved conversation. These
numbers are audit identifiers, not a claim to recover the exact numbering of an
earlier chat list. A code path is not proof of natural behavior in daily use.
The current table overrides broad completion wording in earlier release notes.

Before changing code, the operator reviewed the latest 180 retained messages.
There were 87 assistant replies, including 16 using lists. The reported casual
work recap was present verbatim. Several other lists were genuine command guides
or task reports; deleting every list would damage working behavior.
Private conversations, test fixtures and acceptance measurements are not included
in the public distribution.

| # | Requested behavior | Actual implementation and remaining acceptance |
|---|---|---|
| 1 | Casual chat, including retelling work, must not become an AI report | **Corrected this round.** `voice.py`, social schema and Engine distinguish ordinary check-ins from requested reports. An exceptional outline-shaped reply gets at most one formatting repair; good replies add no model call. Failed/invalid repair keeps the original facts rather than blindly stripping Markdown. Field quality remains partial. |
| 2 | Mood-aware slang, lowercase, abbreviations and text emoticons | **Partial.** Additive character guidance and reply instructions, not a forced slang dictionary. Real model replay is a sample, not broad language-quality acceptance. |
| 3 | Preserve base character; no exclusive ownership of anh/em | Code guidance present in Engine; private persona is preserved. Consistent tone across all users remains a field gate. |
| 4 | Understand fragmented messages | Debounce/coalescing and ordered context exist. **Partial:** no complete semantic conversation-thread model. |
| 5 | Natural follow-up without replying to every bystander | Per-person bounded continuation and relevance decisions exist. **Partial:** concurrent public exchanges need sustained field acceptance. |
| 6 | Plain DM/channel send; reply when interleaved, historical or reporting a job | Late target validation and task origins exist in Conversation. Regression-tested; full multi-user live acceptance remains partial. |
| 7 | Typing through generation and delivery, without inappropriate flashes | Delayed typing leases exist. **Partial:** an eventual model-selected silence can still briefly type; zero flashes is not established. |
| 8 | Larger contextual reaction bank | Expanded choices in `social.py`; model selects reply/react/silence. Selection quality remains a field concern. |
| 9 | Default Kei plus per-person configured/learned call names | Implemented in social runtime and routing. **Corrected this round:** names created before Minecraft linking now merge into the linked person, with the existing limit and no global aliases. |
| 10 | Contextual silence with expiry and genuinely needed-help exceptions | Durable scoped QuietPolicy exists. **Partial:** keyword-based boundaries/exceptions do not establish complete semantic understanding. |
| 11 | Irritation never blocks assigned authorized work | Work decisions run/react-and-run; old social holds retire. Operational permissions remain separate. Regression-tested; no new Minecraft writes performed. |
| 12 | Channel name, guild owner and top two roles inform etiquette | Observed metadata is supplied without granting authority. Intents/cache were verified in the prior runtime check; etiquette needs field acceptance. |
| 13 | Global mood affected by interactions with several people | Persisted daily disposition plus bounded recent sourced affect exists. **Partial:** not a rich evolving narrative of every memorable story. |
| 14 | Immediate minor/major changes in both directions, separate from ranks | Event updates and current-label arrows exist; six-hour confirmation removed. Cooldowns/evidence still apply. Frequency/naturalness needs field acceptance. |
| 15 | Custom ranks grounded in history | Validated model label proposals exist. **Partial:** category thresholds/hysteresis still constrain transitions; labels are not arbitrary unrestricted state. |
| 16 | Neutral/Warm must not speak as established intimate partners | Prompt guidance and score checks exist. **Partial:** no complete independent tone-stage controller or broad behavioral calibration. |
| 17 | Character connections develop naturally and stay hidden as a mechanic | User-facing connection controls removed; sourced two-sided conversational acceptance exists. **Partial:** intent recognition uses limited patterns and currently forms mutual bonds only in private contexts. |
| 18 | Multiple ambiguous connections, fewer crushes | Separate states exist. **Partial:** crush has stronger evidence requirements, but no calibrated frequency/cap proving it is substantially rarer. |
| 19 | One established partner; stop other pursuits | Unique mutual-partner constraint, clearing active ambiguous/crush states and shared partner context exist. History is retained; romantic state grants no permissions. |
| 20 | Acceptance may be uncertain without suddenly high trust/closeness | Uncertain-love label and no automatic trust inflation exist. Multi-day behavioral quality is not yet accepted. |
| 21 | Gradual lover-specific behavior and anniversaries | Internal anniversary scheduling exists. **Partial:** richer gradual affection/conflict behavior is primarily model context, not a complete separately tested progression system. |
| 22 | Breakup, prolonged absence and return without coercion | Explicit breakup and fixed dormant/former thresholds exist. **Partial:** nuanced reunion/planned-absence interpretation and adaptive decay remain limited. |
| 23 | Know the partner globally; public mention only within privacy boundaries | Shared exclusivity context and sourced public permission exist. **Corrected this round:** forgetting the public-permission source revokes disclosure without deleting the relationship. Broader public behavior remains a field gate. |
| 24 | Contextual initiative, closeness/trust/rank budget and justified exceptions | Relationship-adaptive soft caps and sourced exceptions exist. Opt-in, quiet and unanswered-send boundaries remain. **Partial:** long-term frequency calibration is not accepted. |
| 25 | Presence plus custom text status, used subtly | Current-person metadata enters context; idle weight is higher, DND lower, offline/invisible share the normal weight. Status is not a diagnosis. Behavioral acceptance remains partial. |
| 26 | Learn schedules, weekday/time, activities and explicit plans | Thirty-day activity bins and recent plans are supplied to initiative selection. **Partial:** no complete persistent semantic routine model or deterministic adaptive scheduling from those bins. |
| 27 | Birthday/anniversary, silent internal schedules, owner diagnostics | Separate durable social occasions exist. **Partial:** birthday extraction is limited to explicit date patterns; broad natural-language date interpretation is absent. |
| 28 | Warm memory, original excerpts, better context/compaction and recall | Scoped episodes, source excerpts, lexical/FTS retrieval and query expansion exist. **Partial:** no new embedding index, comprehensive old-memory repair or proof of multi-week preservation quality. |
| 29 | Forgetting must invalidate derived records | Tombstones, source-aware derivatives and regressions exist, including the public-permission fix. Every future derived feature still needs its own forgetting coverage. |
| 30 | Useful Hermes-inspired reusable knowledge | Receipt-backed scoped procedures and original-history search exist. **Corrected this round:** worker planning now receives relevant procedures directly under unchanged permissions. **Partial:** no full Hermes migration or on-demand skill-file/registry system. |
| 31 | Avoid login confusion and repeated login on access/reload | Early restoring state, cached identity rendering and durable sessions exist; existing real operator browser session was verified previously. Fresh independent-user setup remains unaccepted. |
| 32 | Clear Add Minecraft flow, panel compatibility, SSH credentials/key, plugin pairing, local topology, test | Guided connections/list/tests exist. **Partial:** plugin uses a private config/token download, not a short pairing-code UX; full connection edit/remove and remote novice acceptance remain incomplete. Hosted credential notice is operator-configured, not public self-host default. |
| 33 | Receive uploaded files and use authorized installation workflow | Scoped expiring attachment IDs, checksums, approval checks, backups/readback exist. **Partial:** full SSH/Panel/bridge file-install acceptance and plugin compatibility acceptance are not complete. |
| 34 | Search when needed without spam; status becomes the answer | Durable search cards, deduplicated successful-fetch counts, bounded repeated searches and answer editing exist. **Partial:** automatic search calibration and real Discord UX need broader acceptance. |
| 35 | Kei chooses a sourced public status about the day or character tastes | Public-only same-day candidates, privacy filtering, validation and bounded update rate exist; a status was submitted through the live Gateway previously. **Partial:** quality/truthfulness of every generated characterization is not established. |

## Paused and separate gates

Minecraft copilot/plugin end-to-end operation acceptance remains paused by the
operator. Do not resume old jobs or restart/change Minecraft to satisfy this audit.
The existing plugin artifact and connectors remain available. Read-only transport
checks do not count as successful gameplay or a verified repair.

Stable release still requires natural sustained social/memory behavior, actual
Minecraft operation acceptance, and independent fresh-user setup. This remains RC.

The previously requested external-app Vietnamese rewrite was not completed through
that app; no supported automation path was available. The dashboard subsequently
switched to English at the operator's request. Additive voice work does not mean
the private persona was replaced or every Vietnamese string was rewritten.
