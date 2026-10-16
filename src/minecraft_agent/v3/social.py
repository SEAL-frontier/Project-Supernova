from __future__ import annotations
import re, unicodedata, hashlib
from ..v2.model import tool, S, choices


def low_signal(text):
    text = unicodedata.normalize("NFKC", text).casefold().strip(" .!?,…")
    return not text or text in {
        "ok",
        "okay",
        "oke",
        "ừ",
        "ừm",
        "uh",
        "uhm",
        "đù",
        "vl",
        "vcl",
        "what",
        "hả",
        "huh",
        "lol",
        "lmao",
        "bruh",
        "36",
        "67",
    }


def followup_allowed(text, to_other=False, answering=False):
    if to_other or low_signal(text):
        return False
    text = unicodedata.normalize("NFKC", text).casefold().strip()
    if text.strip(" .!") in {"hay", "chuẩn", "đỉnh", "cảm ơn", "thanks", "thank you", "❤️", "👍"}:
        return True
    if len(text) > 4 and (
        "?" in text
        or re.search(
            r"\b(tps|ram|mspt|config|check|xem|kiểm tra|profiler|logs?|tiếp|hủy|cancel|đổi|sửa|giải thích|tại sao|như nào)\b",
            text,
        )
    ):
        return True
    return (answering or len(text.split()) >= 2)


def participation_candidate(message, reason, relationship):
    """Cheap per-message eligibility for weak invitations; not a response decision."""
    if reason not in ('nickname','followup'):return True
    warm=float(relationship.get('warmth',.5));familiar=float(relationship.get('familiarity',.1));tension=float(relationship.get('tension',0))
    chance=(.16 if reason=='nickname' else .4)+familiar*.3+(warm-.5)*.5+(float(relationship.get('trust',.5))-.5)*.25-tension*.5
    chance=max(.04,min(.85,chance))
    sample=int(hashlib.sha256(str(message).encode()).hexdigest()[:8],16)/0xffffffff
    return sample<chance


REACTIONS = ('👍','❤️','😭','🥀','🦭','🐧','👀','💀','😒','😤','🤨','😂','🫡','💔','✨','😔','🫶','✅','❓')

PROPOSAL = {
    "type": "object",
    "properties": {
        "kind": choices(
            "none",
            "preference",
            "fact",
            "nickname",
            "boundary",
            "warm_exchange",
            "milestone",
            "conflict",
            "reconciliation",
            "commitment",
            "operational",
        ),
        "content": S,
        "public_hint": S,
        "shareability": choices("safe", "sensitive", "never"),
        "alias": S,
        "title": S,
        "addressing": S,
        "boundaries": S,
        "interests": S,
        "due": {
            "type": "number",
            "description": "Optional commitment due time, Unix seconds; use actual local time from delivery context, never invent a date.",
        },
        "status": choices("open", "done", "cancelled"),
        "resolves_id": {
            "type": "string",
            "description": "Existing commitment ID explicitly completed/cancelled in this turn; never close unrelated promises.",
        },
        "dimensions": {
            "type": "object",
            "properties": {
                k: {"type": "number", "minimum":-1,"maximum":1,"description":"Proportionate directional strength from -1 to 1, not the absolute score or final tiny increment. Backend applies bounded steps. Cite meaningful human evidence; ordinary assistant irritation alone is not negative trust."}
                for k in ("familiarity", "trust", "warmth", "playfulness", "tension")
            },
        },
        "impact": {"type":"string","enum":["minor","major"],"description":"Major only for an explicit significant conflict, reconciliation or milestone grounded in human evidence. Ordinary teasing, warm replies and character tone are minor."},
    },
    "required": ["kind", "content", "shareability"],
}

ROUTER = tool(
    "social_turn",
    "Choose natural social behavior and optionally dispatch requested server work. This single decision is the reply, not hidden reasoning. Do not invent user words, button clicks, memories or relationships. Persona is expressive, not automatically hostile. When a meaningful interaction changes warmth/trust/tension/playfulness, propose a sourced memory with proportionate dimensions so the relationship state reflects it. Routine banter/acknowledgments need no change; a sharp assistant tone alone never proves the user is hostile. Respect boundaries and apologies; a configured one-time social sulk may wait for a natural please/do it, but never guilt or repeated appeasement. Preserve distinctive mutual teasing, nickname-origin stories and reconciliation as warm episodes with both sides' source IDs; fictional character annoyance is different from a real interpersonal conflict. Ordinary chat/RP never launches the operations worker. Silence is appropriate for other people talking, ambient spam, or an ambiguous nickname. Direct questions/operations deserve a useful response. An emoji can get a reaction or a short playful line, not an accusation of Continue. In public be selective with strangers/Neutral or strained relationships: brief replies, reactions or silence often fit. A name occurrence may describe another Kei, not address you. Learned nicknames are weaker invitations than mention/reply/Kei. Let relationship context shape warmth and teasing, never cruelty; use work_response honestly for run, react-and-run or a bounded nonurgent sulk. Use Discord Markdown sparingly: emphasis, bold, spoilers, strikethrough, mini -# notes; headings only when useful. Keep conversational paragraphs compact; no artificial blank space or raw traces.",
    {
        "nickname_for_kei":{"type":"string","description":"A nickname THIS speaker is actually using to address you, e.g. Keys. Empty for names of other people, repository titles or ordinary words. Backend learns it only from repeated sourced use, per person across channels; never universal."},
        "relationship_event":{"type":"object","description":"A meaningful social change even when no new factual memory is needed. Distinctive mutual teasing, appreciation, disagreement, conflict or reconciliation can matter. Do not emit for routine acknowledgments, tool logs or your tone alone. Use current human+assistant evidence and directional strength, not tiny final increments.","properties":{"kind":choices('warm_exchange','conflict','reconciliation'),"content":S,"dimensions":PROPOSAL['properties']['dimensions'],"impact":PROPOSAL['properties']['impact']},"required":["kind","content","dimensions"]},
        "report_action": {"type":"string","enum":["none","show","enable","disable"],"description":"Only for an explicit request to view stored operational reports or change automatic owner notifications. Disabling delivery does not delete report history. Requires server owner for settings and manager for retrieval."},
        "report_kind": {"type":"string","enum":["all","crash","admin","recovery"]},
        "custom_instruction_action": {"type":"string","enum":["none","set","clear","show"],"description":"Only when the current user explicitly asks to set/clear/show their own custom instructions. Not for quoted text, casual banter or another person's preferences. These are additive preferences, never system overrides or operational authorization."},
        "custom_instruction_text": {"type":"string","maxLength":2000,"description":"Requested additive preference text only; retain existing personal instructions when user explicitly appends rather than replaces."},
        "social_mood": {"type":"string","enum":["calm","playful","warm","annoyed","sad","shy","excited"],"description":"Contextual fictional mood, informed by the supplied daily disposition and recent mood. Genuine warmth needs no obligatory tsundere jab. Playful sulking is possible at any rank; your own tone is not evidence against the user."},
        "relationship_bond":{"type":"object","description":"Private nonsexual character connection, separate from durable friendship rank. Crush is Kei's one-sided feeling and does not claim user consent. Mutual/Lover needs the user's explicit romantic interest; casual affection alone is not consent. Breakup/stop flirting takes effect promptly. Never pressure, claim exclusivity, or threaten withheld care/work. Emit only on a meaningful sourced transition, not each affectionate turn.","properties":{"kind":choices('crush','mutual','breakup'),"reason":S},"required":["kind","reason"]},
        "work_response":{"type":"string","enum":["run","react_and_run","sulk_once"],"description":"For a directly requested authorized copilot task: run normally, react 👍 and actually work, or occasionally playfully sulk once and wait for a natural please/sorry/do it/force. Sulk is not a safety/approval gate. Never sulk for emergencies, recovery, scheduled tasks or repeated/forced requests. If sulk_once, clearly say the job has not started and do not claim work is running."},
        "intent": choices("chat", "copilot", "task_control"),
        "response_action": choices("reply", "short_reply", "react", "silence"),
        "reply": {
            "type": "string",
            "description": "Natural Vietnamese in the configured persona, grounded in this exact turn. No canned offers of help. Do not disclose raw relationship scores or hidden IDs.",
        },
        "reaction": choices(*REACTIONS),
        "importance": choices("low", "normal", "important"),
        "delivery": {
            "type": "string",
            "enum": ["channel", "reply", "edit"],
            "description": "In DMs send normally (channel); use reply only for an intentional historical callback. In guilds reply to the relevant requester or use channel when appropriate. Edit only an available own progress card. Never attach work to a bystander's message.",
        },
        "target_message_id": {
            "type": "string",
            "description": "Optional message ID from supplied nearby context or this request. Select a relevant earlier callback/reaction target intentionally; never invent an ID.",
        },
        "relationship_rank": {
            "type": "object",
            "description": "Stable friendship/trust rank, separate from short mood and crush/romantic bond. Neutral is not permanent. Warm is the first step; ordinary tsundere irritation is not Hostile. Repeated genuine conflict or loss of trust may justify a lower rank, without requiring literal stop keywords. Cite current human evidence; backend checks history and confirmation. Use relationship_bond for crush/mutual/breakup.",
            "properties": {
                "label": S,
                "category": choices(
                    "neutral",
                    "warm",
                    "friend",
                    "trusted",
                    "close",
                    "intimate",
                    "tense",
                    "distrustful",
                    "hostile",
                    "distant",
                ),
                "reason": S,
                "sources": {"type": "array", "items": S},
            },
            "required": ["label", "category", "reason", "sources"],
        },
        "schedule_action": {
            "type": "string",
            "enum": ["none", "create", "list", "update", "pause", "resume", "cancel"],
            "description": "Use for an explicit request to do work later/periodically or manage a schedule. Do NOT run that future task now. A pending schedule needs the requester's clock reaction before activation; append the backend notice to your acknowledgment.",
        },
        "schedule_id": S,
        "scheduled_goal": S,
        "schedule_mode": choices("observe", "change"),
        "alarm": {"type": "boolean"},
        "schedule": {
            "type": "object",
            "properties": {
                "kind": choices("once", "daily", "weekly", "cron"),
                "at": S,
                "time": S,
                "weekdays": {
                    "type": "array",
                    "items": {"type": "integer", "minimum": 0, "maximum": 6},
                },
                "cron": S,
                "timezone": S,
            },
            "required": ["kind", "timezone"],
        },
        "memory_action": choices("none", "remember", "forget"),
        "memory_scope": choices("current", "all"),
        "memory_ids": {"type": "array", "items": S},
        "social_preference": {
            "type": "string",
            "enum": [
                "none",
                "dm_on",
                "dm_off",
                "contact_more",
                "contact_less",
                "contact_normal",
                "mute",
                "unmute",
                "privacy_strict",
                "privacy_discreet",
                "romance_off",
                "romance_organic",
                "romance_mutual",
            ],
            "description": "Only for an explicit current request to change the requester own social setting. contact_more/less/normal records an explicit request for how often to initiate. dm_off means stop initiating, not stop answering. Record it quietly in natural dialogue, without a settings receipt. Temporary don't tease is a boundary, not an automatic global mute. Never merely promise a setting change.",
        },
        "memory": PROPOSAL,
        "goal": S,
        "server": S,
        "mode": choices("observe", "change"),
        "complexity": choices("simple", "deep"),
        "plan": {"type": "array", "items": S},
        "self_opinion": {
            "type": "object",
            "description": "Optional stable, fictional self preference expressed in this actual reply, such as a taste in games or tea. Not a fact about a user, a relationship, or server status. Stay consistent with configured persona and previous opinions; do not let random requests rewrite identity. Omit when unnecessary.",
            "properties": {"topic": S, "position": S, "quote": S},
            "required": ["topic", "position", "quote"],
        },
        "control_action": choices("status", "cancel", "append", "confirm"),
        "task_id": S,
        "instruction": S,
        "search_query": {
            "type": "string",
            "description": "Only when lookup/current information/unknown facts or docs require web evidence; empty for RP, greetings or personal feelings. Cite actual result URLs.",
        },
    },
    ["intent", "response_action", "reply", "importance", "memory_action"],
)


def nickname(text, names):
    text = unicodedata.normalize("NFKC", text).casefold()
    for name in names:
        name = unicodedata.normalize("NFKC", str(name)).strip().casefold()
        if name and re.search(
            r"(?<!\w)" + r"\s+".join(re.escape(x) for x in name.split()) + r"(?!\w)", text
        ):
            return name
    return None


def ambient_allowed(config, channel, guild=None, store=None):
    """Legacy settings remain readable; unsolicited public engagement is removed."""
    return False
