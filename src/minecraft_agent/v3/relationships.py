"""Sourced relationship state. These labels never grant operational permissions."""

from __future__ import annotations

import hashlib
import json
import re
import time

from ..v2.store import dumps


def install(store):
    store.db.executescript("""
    CREATE TABLE IF NOT EXISTS kei_relationship_activity(
      person TEXT,scope TEXT,session INTEGER,source TEXT,event TEXT,kind TEXT,at REAL,
      PRIMARY KEY(person,scope,source));
    CREATE INDEX IF NOT EXISTS kei_relationship_active ON kei_relationship_activity(person,scope,at);
    CREATE TABLE IF NOT EXISTS kei_relationship_credits(
      person TEXT,scope TEXT,session INTEGER,event TEXT,at REAL,PRIMARY KEY(person,scope,session));
    CREATE TABLE IF NOT EXISTS kei_relationship_ranks(
      person TEXT,scope TEXT,state TEXT,updated REAL,PRIMARY KEY(person,scope));
    CREATE TABLE IF NOT EXISTS kei_relationship_changes(
      id TEXT PRIMARY KEY,person TEXT,scope TEXT,old_label TEXT,label TEXT,category TEXT,
      reason TEXT,sources TEXT,at REAL,notification TEXT DEFAULT 'pending');
    CREATE TABLE IF NOT EXISTS kei_relationship_preferences(person TEXT PRIMARY KEY,settings TEXT);
    CREATE TABLE IF NOT EXISTS kei_social_moods(person TEXT,scope TEXT,tone TEXT,source TEXT,at REAL,PRIMARY KEY(person,scope));
    CREATE TABLE IF NOT EXISTS kei_relationship_signals(id TEXT PRIMARY KEY,person TEXT,scope TEXT,direction TEXT,dimension TEXT,delta REAL,sources TEXT,action TEXT,at REAL);
    CREATE TABLE IF NOT EXISTS kei_relationship_delta_events(id TEXT PRIMARY KEY,person TEXT,scope TEXT,delta REAL,sources TEXT,at REAL);
    CREATE TABLE IF NOT EXISTS kei_emotion_credits(person TEXT,scope TEXT,source TEXT,kind TEXT,at REAL,PRIMARY KEY(person,scope,source));
    CREATE TABLE IF NOT EXISTS kei_relationship_change_directions(id TEXT PRIMARY KEY,direction TEXT);
    CREATE TABLE IF NOT EXISTS kei_group_observations(
      id TEXT PRIMARY KEY,scope TEXT,kind TEXT,content TEXT,people TEXT,sources TEXT,at REAL);
    CREATE INDEX IF NOT EXISTS kei_group_observed ON kei_group_observations(scope,at);
    """)


RANKS = {
    "neutral": ("Neutral", 0, 0, 0),
    "warm": ("Warm", 1, 3, 2),
    "friend": ("Friend", 2, 8, 3),
    "trusted": ("Trusted", 3, 15, 5),
    "close": ("Close", 4, 25, 8),
    "intimate": ("Lover", 5, 40, 14),
    "tense": ("Tense", -1, 3, 2),
    "distrustful": ("Distrustful", -2, 5, 3),
    "hostile": ("Hostile", -3, 8, 4),
    "distant": ("Distant", 0, 3, 2),
}
INTIMATE = re.compile(
    r"lover|romantic|soulmate|girlfriend|boyfriend|wife|husband|người yêu|vợ|chồng", re.I
)
BOUNDARY = re.compile(
    r"\b(stop|don't|do not|leave me|ignore me|im lặng|đừng|không muốn|không thích|để .{0,12}yên|ngừng)\b",
    re.I,
)


def direct_words(row):
    """Do not attribute a quoted reply or JSON author envelope to its current speaker."""
    return str(row.get("content", "")).split("[REPLIED MESSAGE", 1)[0].split("[REPLY CONTEXT", 1)[0]


class Relationships:
    def __init__(self, store, identity):
        self.db = store
        self.identity = identity

    def backfill(self):
        """Index existing sourced events without changing any relationship scores."""
        for event in self.db.rows(
            "SELECT id,person,scope,kind,sources FROM kei_social_events ORDER BY at DESC LIMIT 5000"
        ):
            sources = json.loads(event["sources"])
            if self.db.tombstoned(sources):
                continue
            rows = [
                self.db.one(
                    "SELECT * FROM kei_messages WHERE id=? AND scope=? AND forgotten=0",
                    (s, event["scope"]),
                )
                for s in sources
            ]
            self.observe(
                event["person"], event["scope"], event["id"], event["kind"], [r for r in rows if r]
            )
            self.credit(event["person"], event["scope"], event["id"], [r for r in rows if r])

    def credit(self, person, scope, event, rows):
        """Curated updates are idempotent independently of raw observed activity."""
        own = [
            r
            for r in rows
            if r["role"] == "user" and self.identity.person_for_user(r["user"]) == person
        ]
        if not own:
            return False
        observed = max(r["at"] for r in own)
        return (
            self.db.execute(
                "INSERT OR IGNORE INTO kei_relationship_credits VALUES (?,?,?,?,?)",
                (person, scope, int(observed // 1800), event, observed),
            ).rowcount
            == 1
        )

    def preferences(self, person):
        row = self.db.one(
            "SELECT settings FROM kei_relationship_preferences WHERE person=?", (person,)
        )
        return {
            "rank_notifications": True,
            "romantic_opt_in": False,
            **(json.loads(row["settings"]) if row else {}),
        }

    def emotion_credit(self,person,scope,kind,rows):
        """A distinct real apology/conflict can matter inside a conversation session."""
        if kind not in ('conflict','reconciliation','warm_exchange','milestone'):return False
        own=[r for r in rows if r['role']=='user' and self.identity.person_for_user(r['user'])==person]
        text=' '.join(direct_words(r) for r in own)
        if kind=='reconciliation' and not re.search(r'xin lỗi|sorry|soww?y|sowwy|làm hòa|thôi mà',text,re.I):return False
        if not own:return False
        if kind in ('warm_exchange','milestone') and not any(r['role']=='assistant' for r in rows):return False
        if kind=='warm_exchange' and not any(len(direct_words(r).strip())>=18 for r in own):return False
        now=max(r['at'] for r in own)
        if self.db.one('SELECT source FROM kei_emotion_credits WHERE person=? AND scope=? AND kind=? AND at>?',(person,scope,kind,now-(900 if kind=='warm_exchange' else 3600))):return False
        if self.db.one('SELECT count(*) n FROM kei_emotion_credits WHERE person=? AND at>?',(person,now-86400))['n']>=4:return False
        # An existing credit for the same human message cannot change kind and count twice.
        if any(self.db.one('SELECT source FROM kei_emotion_credits WHERE person=? AND scope=? AND source=?',(person,scope,r['id'])) for r in own):return False
        for row in own:self.db.execute('INSERT OR IGNORE INTO kei_emotion_credits VALUES (?,?,?,?,?)',(person,scope,row['id'],kind,now))
        return True

    def set_preferences(self, person, **values):
        if not set(values) <= {"rank_notifications", "romantic_opt_in"}:
            raise ValueError("Unknown relationship preference")
        if not all(isinstance(v, bool) for v in values.values()):
            raise ValueError("Relationship preferences must be boolean")
        self.db.execute(
            "INSERT OR REPLACE INTO kei_relationship_preferences VALUES (?,?)",
            (person, dumps({**self.preferences(person), **values})),
        )

    def observe(self, person, scope, event, kind, rows):
        """One observed half-hour session, regardless of message or proposal spam."""
        new_session = False
        for row in rows:
            if row["role"] != "user" or self.identity.person_for_user(row["user"]) != person:
                continue
            if not self.db.one(
                "SELECT source FROM kei_relationship_activity WHERE person=? AND scope=? AND session=? LIMIT 1",
                (person, scope, int(row["at"] // 1800)),
            ):
                new_session = True
            self.db.execute(
                "INSERT OR IGNORE INTO kei_relationship_activity VALUES (?,?,?,?,?,?,?)",
                (person, scope, int(row["at"] // 1800), row["id"], event, kind, row["at"]),
            )
        return new_session

    def frequency(self, person, scope, now=None):
        now = time.time() if now is None else now
        rows = self.db.rows(
            "SELECT session,max(at) at FROM kei_relationship_activity WHERE person=? AND scope=? AND at<=? AND at>? GROUP BY session",
            (person, scope, now, now - 30 * 86400),
        )
        by_day = {}
        for row in rows:
            day = int(row["at"] // 86400)
            by_day[day] = min(6, by_day.get(day, 0) + 1)
        last = self.db.one(
            "SELECT max(at) at FROM kei_relationship_activity WHERE person=? AND scope=? AND at<=?",
            (person, scope, now),
        )
        return {
            "active_days_30": len(by_day),
            "meaningful_sessions_30": sum(by_day.values()),
            "last_seen": (last or {}).get("at"),
            "score": round(min(1, len(by_day) / 15) * min(1, sum(by_day.values()) / 20), 4),
        }

    def rank(self, person, scope):
        row = self.db.one(
            "SELECT state FROM kei_relationship_ranks WHERE person=? AND scope=?", (person, scope)
        )
        return (
            json.loads(row["state"])
            if row
            else {
                "label": "Neutral",
                "category": "neutral",
                "reason": "No established rank change yet.",
                "changed": None,
            }
        )

    def _evidence(self, person, scope, sources):
        if not isinstance(sources, list) or not sources or len(sources) > 24:
            return None
        sources = list(dict.fromkeys(str(s) for s in sources))
        if self.db.tombstoned(sources):
            return None
        rows = [
            self.db.one(
                "SELECT * FROM kei_messages WHERE id=? AND scope=? AND forgotten=0", (s, scope)
            )
            for s in sources
        ]
        if not all(rows):
            return None
        if not any(
            r["role"] == "user" and self.identity.person_for_user(r["user"]) == person for r in rows
        ):
            return None
        return rows

    def propose(self, person, scope, proposal, profile, now=None):
        """Hysteresis + evidence, not a model-controlled affection scoreboard."""
        now = time.time() if now is None else now
        if not isinstance(proposal, dict):
            return False
        category = str(proposal.get("category", "")).casefold()
        if category not in RANKS:
            return False
        label = str(proposal.get("label", "")).strip()
        reason = str(proposal.get("reason", "")).strip()
        if not 2 <= len(label) <= 32 or not 8 <= len(reason) <= 350:
            return False
        if re.search(r"[\n\r<>@`]|https?://", label + reason):
            return False
        if INTIMATE.search(label) and category != "intimate":
            return False
        sources = proposal.get("sources", [])
        rows = self._evidence(person, scope, sources)
        if rows is None:
            return False
        history = self.db.rows(
            "SELECT session,max(at) at FROM kei_relationship_activity WHERE person=? AND scope=? AND at<=? GROUP BY session",
            (person, scope, now),
        )
        sessions = len(history)
        days = len({int(r["at"] // 86400) for r in history})
        _, stage, minimum, minimum_days = RANKS[category]
        if sessions < minimum or days < minimum_days:
            return False
        if stage > 0 and (profile.get("trust", 0.5) < 0.45 or profile.get("warmth", 0.5) < 0.45):
            return False
        if stage >= 2 and (
            profile.get("familiarity", 0.1) < 0.2 or profile.get("trust", 0.5) < 0.53
        ):
            return False
        if stage >= 3 and profile.get("trust", 0.5) < 0.65:
            return False
        if stage >= 4 and profile.get("warmth", 0.5) < 0.65:
            return False
        own = [
            direct_words(r)
            for r in rows
            if r["role"] == "user" and self.identity.person_for_user(r["user"]) == person
        ]
        if category == "intimate":
            if not self.preferences(person)["romantic_opt_in"] or not any(
                INTIMATE.search(s) for s in own
            ):
                return False
        if stage < 0:
            # Character banter or assistant demands are not evidence that the user is hostile.
            if profile.get("tension", 0) < 0.35 or not any(BOUNDARY.search(s) for s in own):
                return False
            conflict = self.db.one(
                "SELECT count(DISTINCT CAST(at/86400 AS INTEGER)) n FROM kei_relationship_activity WHERE person=? AND scope=? AND kind='conflict' AND at>?",
                (person, scope, now - 30 * 86400),
            )
            if not conflict or conflict["n"] < 2:
                return False
        current = self.rank(person, scope)
        if current["label"] == label and current["category"] == category:
            return False
        old_stage = RANKS.get(current["category"], RANKS["neutral"])[1]
        if abs(stage - old_stage) > 1:
            return False
        # A new independent session and a full day must confirm a proposed change.
        pending = current.get("pending", {})
        independent = set(sources) - set(pending.get("sources", []))
        if pending.get("category") != category:
            current["pending"] = {
                "label": label,
                "category": category,
                "reason": reason,
                "sources": sources,
                "since": now,
            }
            self._save(person, scope, current, now)
            return False
        # Wording may vary between turns; a rename must not restart the clock.
        label = pending.get('label') or label
        if (
            now - pending["since"] < 86400
            or not independent
            or (current.get("changed") and now - current["changed"] < 86400)
        ):
            return False
        previous_sources = pending.get("sources", [])
        # Never confirm a candidate after its older evidence was forgotten.
        if self._evidence(person, scope, previous_sources) is None:
            current.pop("pending", None)
            self._save(person, scope, current, now)
            return False
        changed_sources = list(dict.fromkeys(previous_sources + sources))
        change = hashlib.sha256(
            (person + scope + label + dumps(changed_sources)).encode()
        ).hexdigest()[:24]
        with self.db.atomic():
            self.db.execute(
                "INSERT OR IGNORE INTO kei_relationship_changes VALUES (?,?,?,?,?,?,?,?,?,?)",
                (
                    change,
                    person,
                    scope,
                    current["label"],
                    label,
                    category,
                    reason,
                    dumps(changed_sources),
                    now,
                    "pending" if self.preferences(person)["rank_notifications"] else "disabled",
                ),
            )
            self.db.execute(
                "INSERT OR REPLACE INTO kei_relationship_change_directions VALUES (?,?)",
                (change, "Down" if stage < old_stage else "Up"),
            )
            self._save(
                person,
                scope,
                {"label": label, "category": category, "reason": reason, "changed": now},
                now,
            )
        return True

    def _save(self, person, scope, state, now):
        self.db.execute(
            "INSERT OR REPLACE INTO kei_relationship_ranks VALUES (?,?,?,?)",
            (person, scope, dumps(state), now),
        )

    def notification(self, person, scope, now=None):
        """Pull one short self-only notice. Caller marks it after delivery; no channel spam."""
        now = time.time() if now is None else now
        if not self.preferences(person)["rank_notifications"]:
            return None
        # Only the latest still-pending change; historical catch-up isn't useful.
        row = self.db.one(
            "SELECT * FROM kei_relationship_changes WHERE person=? AND scope=? AND notification='pending' AND at>? ORDER BY at DESC LIMIT 1",
            (person, scope, now - 7 * 86400),
        )
        if not row or self.db.tombstoned(json.loads(row["sources"])):
            return None
        old = self.db.one(
            "SELECT at FROM kei_relationship_changes WHERE person=? AND notification='sent' ORDER BY at DESC LIMIT 1",
            (person,),
        )
        if old and now - old["at"] < 3 * 86400:
            return None
        known_direction = self.db.one(
            "SELECT direction FROM kei_relationship_change_directions WHERE id=?", (row["id"],)
        )
        old_stage = next((v[1] for v in RANKS.values() if v[0] == row["old_label"]), 0)
        direction = (
            known_direction["direction"]
            if known_direction
            else ("Down" if RANKS.get(row["category"], RANKS["neutral"])[1] < old_stage else "Up")
        )
        arrow = '↓' if direction == 'Down' else '↑'
        return {"id": row["id"], "content": f"-# {row['label']} {arrow}"}

    def delivered(self, notification_id):
        self.db.execute(
            "UPDATE kei_relationship_changes SET notification='sent' WHERE id=? AND notification='pending'",
            (notification_id,),
        )

    def mood(self,person,scope,tone=None,source=None):
        if tone in ('calm','playful','warm','annoyed') and source and self._evidence(person,scope,[source]):
            self.db.execute('INSERT OR REPLACE INTO kei_social_moods VALUES (?,?,?,?,?)',(person,scope,tone,source,time.time()))
        row=self.db.one('SELECT tone,source,at FROM kei_social_moods WHERE person=? AND scope=? AND at>?',(person,scope,time.time()-7200))
        return {'tone':row['tone'],'at':row['at']} if row and not self.db.tombstoned([row['source']]) else None

    def delta_notice(self,person,scope,before,after,sources,action,threshold=0.012,now=None):
        now=time.time() if now is None else now
        if not action or not self.preferences(person)['rank_notifications'] or self._evidence(person,scope,sources) is None:return None
        # Real sourced dimension updates only. Character tone alone is insufficient.
        deltas={k:(float(after.get(k,0))-float(before.get(k,0)))*(-1 if k=='tension' else 1) for k in ('trust','warmth','playfulness','tension')}
        key=max(deltas,key=lambda k:abs(deltas[k]))
        delta=deltas['trust']*1.4+deltas['warmth']+deltas['playfulness']*.45+deltas['tension']*.8
        ident=hashlib.sha256((person+scope+dumps(sources)).encode()).hexdigest()[:24]
        if abs(delta)<.000001:return None
        self.db.execute('INSERT OR IGNORE INTO kei_relationship_delta_events VALUES (?,?,?,?,?,?)',(ident,person,scope,delta,dumps(sources),now))
        last=self.db.one("SELECT max(s.at) at FROM kei_relationship_signals s JOIN kei_social_actions a ON a.id=s.action WHERE s.person=? AND s.scope=? AND a.status IN ('pending','sending','sent','uncertain')",(person,scope))
        through=max(now-1800,(last or {}).get('at') or 0)
        delta=self.db.one('SELECT coalesce(sum(delta),0) n FROM kei_relationship_delta_events WHERE person=? AND scope=? AND at>?',(person,scope,through))['n']
        if abs(delta)<max(.005,float(threshold)):return None
        interval=45 if abs(delta)>=.035 else 180
        previous=self.db.one("SELECT s.at FROM kei_relationship_signals s JOIN kei_social_actions a ON a.id=s.action WHERE s.person=? AND s.scope=? AND s.at>? AND a.status IN ('pending','sending','sent') ORDER BY s.at DESC LIMIT 1",(person,scope,now-interval))
        if previous:return None
        ident=hashlib.sha256((person+scope+dumps(sources)).encode()).hexdigest()[:24]
        if self.db.one('SELECT id FROM kei_relationship_signals WHERE id=?',(ident,)):return None
        direction='up' if delta>0 else 'down'
        self.db.execute('INSERT INTO kei_relationship_signals VALUES (?,?,?,?,?,?,?,?,?)',(ident,person,scope,direction,key,delta,dumps(sources),action,now))
        arrow='↑' if direction=='up' else '↓'
        if abs(delta)>=.035:arrow*=2
        return '-# '+self.rank(person,scope)['label']+' '+arrow

    def forget(self, person, scope=None, sources=()):
        sources = set(sources)
        if scope:self.db.execute('DELETE FROM kei_social_moods WHERE person=? AND scope=?',(person,scope))
        else:self.db.execute('DELETE FROM kei_social_moods WHERE person=?',(person,))
        self.db.execute('DELETE FROM kei_relationship_delta_events WHERE person=?'+(' AND scope=?' if scope else ''),(person,scope) if scope else (person,))
        self.db.execute('DELETE FROM kei_emotion_credits WHERE person=?'+(' AND scope=?' if scope else ''),(person,scope) if scope else (person,))
        for signal in self.db.rows('SELECT * FROM kei_relationship_signals WHERE person=?',(person,)):
            if (not scope or signal['scope']==scope) and (not sources or sources.intersection(json.loads(signal['sources']))):self.db.execute('DELETE FROM kei_relationship_signals WHERE id=?',(signal['id'],))
        for table in ("kei_relationship_changes", "kei_group_observations"):
            for row in self.db.rows("SELECT * FROM " + table):
                owned = row.get("person") == person and (not scope or row.get("scope") == scope)
                if owned or sources.intersection(json.loads(row["sources"])):
                    self.db.execute("DELETE FROM " + table + " WHERE id=?", (row["id"],))
                    if table == "kei_relationship_changes":
                        self.db.execute(
                            "DELETE FROM kei_relationship_change_directions WHERE id=?",
                            (row["id"],),
                        )
        query = "DELETE FROM kei_relationship_activity WHERE person=?"
        args = (person,)
        if scope:
            query += " AND scope=?"
            args += (scope,)
        self.db.execute(query, args)
        query = "DELETE FROM kei_relationship_credits WHERE person=?"
        self.db.execute(
            query + (" AND scope=?" if scope else ""), (person, scope) if scope else (person,)
        )
        query = "DELETE FROM kei_relationship_ranks WHERE person=?"
        self.db.execute(
            query + (" AND scope=?" if scope else ""), (person, scope) if scope else (person,)
        )

    def group_observe(self, scope, proposal, visible_rows):
        """Persist bounded observations, not unsourced claims about a group's motives."""
        if scope.startswith(("dm:", "mc-private:")) or not isinstance(proposal, dict):
            return
        visible = {r["id"]: r for r in visible_rows}
        for item in proposal.get("observations", [])[:20]:
            if not isinstance(item, dict) or item.get("kind") not in {
                "topic",
                "joke",
                "nickname",
                "pattern",
                "relationship",
                "boundary",
            }:
                continue
            sources = list(dict.fromkeys(map(str, item.get("sources", []))))
            text = str(item.get("content", "")).strip()[:400]
            if (
                not sources
                or not text
                or not set(sources) <= visible.keys()
                or self.db.tombstoned(sources)
            ):
                continue
            humans = [visible[s] for s in sources if visible[s]["role"] == "user"]
            if not humans:
                continue
            people = sorted({self.identity.person_for_user(r["user"]) for r in humans})
            if item["kind"] == "relationship" and len(people) < 2:
                continue
            if item["kind"] == "boundary" and not any(
                BOUNDARY.search(direct_words(r)) for r in humans
            ):
                continue
            duplicate = False
            for old in self.db.rows(
                "SELECT sources FROM kei_group_observations WHERE scope=? AND kind=? ORDER BY at DESC LIMIT 200",
                (scope, item["kind"]),
            ):
                previous = set(json.loads(old["sources"]))
                if len(previous & set(sources)) >= min(len(previous), len(sources)) * 0.6:
                    duplicate = True
                    break
            if duplicate:
                continue
            ident = hashlib.sha256(
                (scope + item["kind"] + text + dumps(sources)).encode()
            ).hexdigest()[:24]
            self.db.execute(
                "INSERT OR IGNORE INTO kei_group_observations VALUES (?,?,?,?,?,?,?)",
                (
                    ident,
                    scope,
                    item["kind"],
                    text,
                    dumps(people),
                    dumps(sources),
                    max(visible[s]["at"] for s in sources),
                ),
            )

    def group(self, scope, through=None):
        if scope.startswith(("dm:", "mc-private:")):
            return {}
        now = time.time() if through is None else through
        people = {}
        recent = self.db.rows(
            "SELECT id,user,at FROM kei_messages WHERE scope=? AND role='user' AND forgotten=0 AND at>? AND at<=? ORDER BY at DESC LIMIT 500",
            (scope, now - 30 * 86400, now),
        )
        hourly = {}
        for row in recent:
            if self.db.tombstoned([row["id"]]):
                continue
            person = self.identity.person_for_user(row["user"])
            item = people.setdefault(
                person,
                {
                    "person": person,
                    "observed_messages": 0,
                    "active_days": set(),
                    "last_seen": row["at"],
                },
            )
            item["observed_messages"] += 1
            item["active_days"].add(int(row["at"] // 86400))
            hour = int(row["at"] // 3600) % 24
            hourly[hour] = hourly.get(hour, 0) + 1
        participants = []
        for item in sorted(people.values(), key=lambda p: p["observed_messages"], reverse=True)[
            :12
        ]:
            participants.append({**item, "active_days": len(item["active_days"])})
        observations = []
        for row in self.db.rows(
            "SELECT * FROM kei_group_observations WHERE scope=? AND at<=? ORDER BY at DESC LIMIT 100",
            (scope, now),
        ):
            if self.db.tombstoned(json.loads(row["sources"])):
                continue
            observations.append(
                {
                    "kind": row["kind"],
                    "content": row["content"],
                    "people": json.loads(row["people"]),
                    "sources": json.loads(row["sources"]),
                    "at": row["at"],
                }
            )
            if len(observations) >= 12:
                break
        return {
            "basis": "Observed permitted messages only; not a complete guild history or inferred motives.",
            "participants": participants,
            "observed_hour_utc_counts": hourly,
            "observations": observations,
        }
