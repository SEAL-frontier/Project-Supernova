"""Local acceptance measurements. No transcripts, external collector or model calls."""

from __future__ import annotations

import hashlib
import hmac

import math
import secrets
import time

from . import VERSION
from ..v2.store import uid, dumps


class Telemetry:
    def __init__(self, store, config):
        self.db = store
        self.cfg = config
        self.db.telemetry = self
        install(self.db)
        salt = self.db.one("SELECT value FROM kei_meta WHERE key='telemetry-salt'")
        if not salt:
            self.db.execute(
                "INSERT OR IGNORE INTO kei_meta VALUES (?,?)",
                ("telemetry-salt", secrets.token_hex(32)),
            )
            salt = self.db.one("SELECT value FROM kei_meta WHERE key='telemetry-salt'")
        self.salt = salt["value"].encode()
        if self.enabled:
            self._start()

    @property
    def enabled(self):
        return bool(self.cfg.get("telemetry", {}).get("enabled", False))

    def _start(self):
        self.db.execute(
            "INSERT OR IGNORE INTO kei_meta VALUES (?,?)", ("telemetry-started", str(time.time()))
        )

    def reference(self, value):
        return (
            hmac.new(self.salt, str(value).encode(), hashlib.sha256).hexdigest()[:32]
            if value
            else ""
        )

    def generation(self):
        return self.db.one("SELECT value FROM kei_meta WHERE key='memory-forget-generation'")

    def record(self, kind, user="", scope="", trace="", duration_ms=None, outcome="ok", **data):
        if not self.enabled:
            return None
        allowed = {
            "conversation": {"intent", "action", "reason", "received_at", "queue_ms", "route_calls", "parse_repairs", "context_chars", "model_ms", "style_ms"},
            "social_state": {"stage", "validation"},
            "bridge_sample": set(),
        }
        if kind not in allowed or set(data) - allowed[kind]:
            raise ValueError("Unsupported telemetry fields")
        enums = {
            "intent": {"chat", "copilot", "task_control", "unknown"},
            "action": {"reply", "short_reply", "react", "silence", "task_queued", "unknown"},
            "reason": {"direct", "ambient", "followup", "nickname", "unknown"},
            "stage": {"event", "rank"},
            "validation": {"nonliteral_event", "missing_human_choice", "misattributed_quote", "accepted", "no_evidence", "invalid_event", "duplicate_source", "duplicate_event", "ungrounded_impact", "no_delta", "invalid_rank", "unchanged_rank", "missing_bond", "missing_current_event", "insufficient_history", "insufficient_negative_evidence", "reused_rank_sources"},
        }
        for key, value in data.items():
            if key in enums and (not isinstance(value, str) or value not in enums[key]):
                raise ValueError("Invalid telemetry tag")
            if key not in enums and (
                not isinstance(value, (int, float)) or not math.isfinite(value)
            ):
                raise ValueError("Telemetry measurements must be finite numbers")
        if outcome not in ("ok", "error", "up", "down"):
            raise ValueError("Invalid telemetry outcome")
        if duration_ms is not None and (not math.isfinite(duration_ms) or duration_ms < 0):
            raise ValueError("Invalid telemetry duration")
        self._start()
        ident = uid()
        self.db.execute(
            "INSERT INTO kei_telemetry_events VALUES (?,?,?,?,?,?,?,?,?,?)",
            (
                ident,
                kind,
                self.reference(user),
                self.reference(scope),
                self.reference(trace),
                duration_ms,
                outcome,
                dumps(data),
                VERSION,
                time.time(),
            ),
        )
        return ident


def install(store):
    """Idempotent public-clone schema installation; no private store dependency."""
    store.execute("CREATE TABLE IF NOT EXISTS kei_meta(key TEXT PRIMARY KEY,value TEXT)")
    store.execute("CREATE TABLE IF NOT EXISTS kei_telemetry_events(id TEXT PRIMARY KEY,kind TEXT,actor TEXT,scope TEXT,trace TEXT,duration_ms REAL,outcome TEXT,data TEXT,version TEXT,at REAL)")
