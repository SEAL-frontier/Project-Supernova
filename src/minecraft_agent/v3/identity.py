from __future__ import annotations
import hashlib, secrets, time, json
from ..v2.store import dumps


class Identity:
    def __init__(self, store):
        self.db = store

    def resolve(self, platform, account, server=""):
        account = str(account)
        server = str(server or "") if platform == "minecraft" else ""
        row = self.db.one(
            "SELECT * FROM kei_accounts WHERE platform=? AND account=? AND server=?",
            (platform, account, server),
        )
        if row:
            return row["person"]
        person = (
            ("discord:" + account)
            if platform == "discord"
            else "minecraft:" + server + ":" + account
        )
        self.db.execute("INSERT OR IGNORE INTO kei_people VALUES (?,?)", (person, time.time()))
        self.db.execute(
            "INSERT INTO kei_accounts VALUES (?,?,?,?,?)",
            (platform, account, server, person, int(platform == "discord")),
        )
        return person

    def person_for_user(self, user):
        if str(user).startswith("mc:"):
            _, server, account = str(user).split(":", 2)
            return self.resolve("minecraft", account, server)
        return self.resolve("discord", str(user))

    def discord(self, person):
        row = self.db.one(
            "SELECT account FROM kei_accounts WHERE person=? AND platform='discord' AND verified=1",
            (person,),
        )
        return row["account"] if row else None

    def issue(self, discord_id, server=""):
        code = secrets.token_hex(4).upper()
        hashed = hashlib.sha256(code.encode()).hexdigest()
        self.db.execute("DELETE FROM kei_link_codes WHERE expires<?", (time.time(),))
        self.db.execute(
            "INSERT INTO kei_link_codes VALUES (?,?,?,?)",
            (hashed, str(discord_id), str(server or ""), time.time() + 600),
        )
        return code

    def redeem(self, code, server, uuid, authenticated):
        if not authenticated:
            raise PermissionError("Login Minecraft/AuthMe trước khi link.")
        hashed = hashlib.sha256(code.strip().upper().encode()).hexdigest()
        row = self.db.one(
            "SELECT * FROM kei_link_codes WHERE code_hash=? AND expires>?", (hashed, time.time())
        )
        if not row or (row["server"] and row["server"] != server):
            raise ValueError("Mã link hết hạn hoặc sai server.")
        existing = self.resolve("minecraft", uuid, server)
        target = self.resolve("discord", row["discord"])
        if self.discord(existing) not in (None, row["discord"]):
            raise PermissionError("UUID đã link người khác; unlink trước.")
        if existing!=target:
            from .relationships import Relationships
            relationship=Relationships(self.db,self)
            profiles=[json.loads(relationship.profile_row(p)['profile']) for p in (target,existing)]
            base={'familiarity':.1,'trust':.5,'warmth':.5,'playfulness':.5,'tension':0,'confidence':.2}
            merged={k:max((float(p.get(k,v)) for p in profiles),key=lambda x:abs(x-v)) for k,v in base.items()}
            self.db.execute('INSERT OR REPLACE INTO kei_relationships VALUES (?,?,?,?)',(target,'global',dumps(merged),time.time()))
            for table in ('kei_relationships','kei_relationship_ranks','kei_relationship_activity','kei_relationship_credits','kei_relationship_changes','kei_relationship_signals','kei_relationship_delta_events','kei_emotion_credits','kei_social_moods','kei_aliases'):
                self.db.execute('UPDATE OR IGNORE '+table+' SET person=? WHERE person=?',(target,existing))
                self.db.execute('DELETE FROM '+table+' WHERE person=?',(existing,))
            for table in ('kei_affect_events','kei_bonds','kei_bond_events'):
                if self.db.one("SELECT name FROM sqlite_master WHERE type='table' AND name=?",(table,)):
                    self.db.execute('UPDATE OR IGNORE '+table+' SET person=? WHERE person=?',(target,existing))
                    self.db.execute('DELETE FROM '+table+' WHERE person=?',(existing,))
        self.db.execute(
            "UPDATE kei_accounts SET person=?,verified=1 WHERE platform=? AND account=? AND server=?",
            (target, "minecraft", uuid, server),
        )
        for table in (
            "kei_social_events",
            "kei_episodes",
            "kei_memories",
            "kei_commitments",
            "kei_event_meta",
        ):
            self.db.execute("UPDATE " + table + " SET person=? WHERE person=?", (target, existing))
        self.db.execute("DELETE FROM kei_link_codes WHERE code_hash=?", (hashed,))
        return target

    def unlink(self, discord_id, server=None):
        person = self.resolve("discord", discord_id)
        rows = self.db.rows(
            "SELECT * FROM kei_accounts WHERE platform='minecraft' AND person=?", (person,)
        )
        for row in rows:
            if server and row["server"] != server:
                continue
            separate = "minecraft:" + row["server"] + ":" + row["account"]
            self.db.execute(
                "INSERT OR IGNORE INTO kei_people VALUES (?,?)", (separate, time.time())
            )
            self.db.execute(
                "UPDATE kei_accounts SET person=?,verified=0 WHERE platform='minecraft' AND account=? AND server=?",
                (separate, row["account"], row["server"]),
            )
        return len([r for r in rows if not server or r["server"] == server])
