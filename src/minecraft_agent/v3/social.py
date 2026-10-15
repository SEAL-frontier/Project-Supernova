from __future__ import annotations
import re, unicodedata
from ..v2.model import tool, S, choices

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
                k: {"type": "number"}
                for k in ("familiarity", "trust", "warmth", "playfulness", "tension")
            },
        },
    },
    "required": ["kind", "content", "shareability"],
}

ROUTER = tool(
    "social_turn",
    "Choose natural social behavior and optionally dispatch requested server work. This single decision is the reply, not hidden reasoning. Do not invent user words, button clicks, memories or relationships. Persona is expressive, not automatically hostile. Respect boundaries and apologies; never require appeasement before doing work. Ordinary chat/RP never launches the operations worker. Silence is appropriate for other people talking, ambient spam, or an ambiguous nickname. Direct questions/operations deserve a useful response. An emoji can get a reaction or a short playful line, not an accusation of Continue.",
    {
        "intent": choices("chat", "copilot", "task_control"),
        "response_action": choices("reply", "short_reply", "react", "silence"),
        "reply": {
            "type": "string",
            "description": "Natural Vietnamese in the configured persona, grounded in this exact turn. No canned offers of help. Do not disclose raw relationship scores or hidden IDs.",
        },
        "reaction": choices("👍", "❤️"),
        "importance": choices("low", "normal", "important"),
        "memory_action": choices("none", "remember", "forget"),
        "memory_scope": choices("current", "all"),
        "memory_ids": {"type": "array", "items": S},
        "social_preference": {
            "type": "string",
            "enum": [
                "none",
                "dm_on",
                "dm_off",
                "mute",
                "unmute",
                "privacy_strict",
                "privacy_discreet",
            ],
            "description": "Only for an explicit current request to change the requester own social setting. Temporary don't tease is a boundary, not an automatic global mute. Never merely promise a setting change.",
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
    settings = config["social"]["ambient"]
    if guild and store:
        import json

        row = store.one("SELECT value FROM kei_meta WHERE key=?", ("ambient:guild:" + str(guild),))
        if row:
            settings = json.loads(row["value"])
    return settings["enabled"] and (
        settings["mode"] == "free" or str(channel) in list(map(str, settings["channels"]))
    )
