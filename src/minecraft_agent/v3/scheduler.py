"""Durable, explicitly confirmed agent schedules; existing task execution stays authoritative."""

from __future__ import annotations

import asyncio
from datetime import datetime, timedelta, timezone
import json
import re
import sqlite3
import time
from zoneinfo import ZoneInfo

from ..v2.store import dumps, uid

UTC = timezone.utc
TERMINAL = {"succeeded", "failed", "cancelled", "timed_out", "skipped", "blocked", "uncertain"}


def _zone(name):
    try:
        return ZoneInfo(str(name))
    except Exception as exc:
        raise ValueError("Timezone không hợp lệ; ví dụ Asia/Ho_Chi_Minh.") from exc


def _clock(value):
    if not re.fullmatch(r"\d{2}:\d{2}", str(value)):
        raise ValueError("Giờ cần dạng HH:MM, ví dụ 07:00.")
    hour, minute = map(int, value.split(":"))
    if hour > 23 or minute > 59:
        raise ValueError("Giờ không hợp lệ.")
    return hour, minute


def _cron_field(text, low, high, sunday=False):
    values = set()
    for part in str(text).split(","):
        if not part:
            raise ValueError("Cron có field trống.")
        base, *step = part.split("/")
        if len(step) > 1 or (
            step and (not step[0].isdigit() or not 1 <= int(step[0]) <= high - low + 1)
        ):
            raise ValueError("Cron step không hợp lệ.")
        stride = int(step[0]) if step else 1
        if base == "*":
            start, stop = low, high
        elif re.fullmatch(r"\d+-\d+", base):
            start, stop = map(int, base.split("-"))
        elif base.isdigit():
            start = int(base)
            stop = high if step else start
        else:
            raise ValueError(
                "Cron hỗ trợ số, *, ranges, lists và /step; không dùng shell expressions."
            )
        if start < low or stop > high or start > stop:
            raise ValueError("Cron field ngoài khoảng cho phép.")
        values.update(range(start, stop + 1, stride))
    return {0 if sunday and n == 7 else n for n in values}


def validate_schedule(schedule, default_timezone="Asia/Ho_Chi_Minh"):
    if not isinstance(schedule, dict):
        raise ValueError("Cần thời gian cụ thể cho lịch hẹn.")
    kind = str(schedule.get("kind", "once"))
    if kind not in ("once", "daily", "weekly", "cron"):
        raise ValueError("Lịch hỗ trợ once, daily, weekly hoặc cron.")
    name = str(schedule.get("timezone") or default_timezone)
    zone = _zone(name)
    out = {"kind": kind, "timezone": name}
    if kind == "once":
        try:
            at = datetime.fromisoformat(str(schedule["at"]).replace("Z", "+00:00"))
            if at.tzinfo is None:
                at = at.replace(tzinfo=zone)
                back = datetime.fromtimestamp(at.timestamp(), zone)
                if back.replace(tzinfo=None) != at.replace(tzinfo=None):
                    raise ValueError("Local time does not exist on this DST date")
            out["at"] = at.astimezone(UTC).isoformat()
        except (ValueError, KeyError) as exc:
            raise ValueError(
                "Lịch một lần cần ngày giờ ISO, ví dụ 2026-10-17T07:00:00+07:00."
            ) from exc
    elif kind in ("daily", "weekly"):
        _clock(schedule.get("time", ""))
        out["time"] = str(schedule["time"])
        if kind == "weekly":
            days = schedule.get("weekdays")
            if (
                not isinstance(days, list)
                or not days
                or any(type(d) is not int or not 0 <= d <= 6 for d in days)
            ):
                raise ValueError("Ngày trong tuần dùng 0=thứ Hai đến 6=Chủ nhật.")
            out["weekdays"] = sorted(set(days))
    else:
        expression = str(schedule.get("cron", "")).strip()
        fields = expression.split()
        if len(fields) != 5:
            raise ValueError("Cron cần 5 field: phút giờ ngày-tháng tháng thứ-tuần.")
        for value, low, high in zip(fields, (0, 0, 1, 1, 0), (59, 23, 31, 12, 7)):
            _cron_field(value, low, high)
        out["cron"] = expression
    return out


def next_run(schedule, after=None):
    """Return the next UTC timestamp strictly after `after`; wall times fire once on DST folds."""
    schedule = validate_schedule(schedule)
    after = time.time() if after is None else float(after)
    zone = _zone(schedule["timezone"])
    if schedule["kind"] == "once":
        value = datetime.fromisoformat(schedule["at"]).timestamp()
        return value if value > after else None
    local = datetime.fromtimestamp(after, zone)
    if schedule["kind"] == "cron":
        raw = schedule["cron"].split()
        minute, hour, monthday, month, weekday = [
            _cron_field(v, lo, hi, i == 4)
            for i, (v, lo, hi) in enumerate(zip(raw, (0, 0, 1, 1, 0), (59, 23, 31, 12, 7)))
        ]
    else:
        h, m = _clock(schedule["time"])
        minute, hour, monthday, month, weekday = {m}, {h}, None, None, None
    for offset in range(366 * 5):
        date = local.date() + timedelta(days=offset)
        if schedule["kind"] == "weekly" and date.weekday() not in schedule["weekdays"]:
            continue
        if schedule["kind"] == "cron":
            if date.month not in month:
                continue
            dom, dow = date.day in monthday, (date.weekday() + 1) % 7 in weekday
            # Standard cron: restricted day-of-month and day-of-week use OR.
            allowed = (dom or dow) if raw[2] != "*" and raw[4] != "*" else (dom and dow)
            if not allowed:
                continue
        for h in sorted(hour):
            for m in sorted(minute):
                candidate = datetime(date.year, date.month, date.day, h, m, tzinfo=zone, fold=0)
                stamp = candidate.timestamp()
                # Missing DST wall times are skipped, rather than silently moved an hour.
                returned = datetime.fromtimestamp(stamp, zone)
                if returned.hour != h or returned.minute != m or returned.date() != date:
                    continue
                if stamp > after:
                    return stamp
    raise ValueError("Không tìm được thời điểm cron hợp lệ trong 5 năm tới.")


def parse_schedule_text(text, timezone="Asia/Ho_Chi_Minh", now=None):
    value = str(text).strip().casefold()
    value = re.sub(r'(?<!\d)(\d):(\d{2})(?=\s|$)',r'0\1:\2',value)
    zone = _zone(timezone)
    now = time.time() if now is None else float(now)
    local = datetime.fromtimestamp(now, zone)
    for prefix in ("mỗi ngày ", "hằng ngày ", "hàng ngày ", "daily "):
        if value.startswith(prefix):
            return validate_schedule(
                {"kind": "daily", "time": value[len(prefix) :].strip(), "timezone": timezone}
            )
    for prefix in ("hàng tuần ", "hằng tuần ", "mỗi tuần ", "weekly "):
        if value.startswith(prefix):
            rest = value[len(prefix) :].strip()
            days, clock = rest.rsplit(" ", 1)
            names = {
                "mon": 0,
                "tue": 1,
                "wed": 2,
                "thu": 3,
                "fri": 4,
                "sat": 5,
                "sun": 6,
                "t2": 0,
                "t3": 1,
                "t4": 2,
                "t5": 3,
                "t6": 4,
                "t7": 5,
                "cn": 6,
            }
            try:
                indices = [names[d.strip()] for d in days.split(",")]
            except KeyError as exc:
                raise ValueError(
                    "Ví dụ tuần: weekly mon,wed 07:00 hoặc hàng tuần t2,t4 07:00."
                ) from exc
            return validate_schedule(
                {"kind": "weekly", "weekdays": indices, "time": clock, "timezone": timezone}
            )
    if value.startswith("cron "):
        return validate_schedule({"kind": "cron", "cron": value[5:], "timezone": timezone})
    tomorrow = False
    for prefix in ("ngày mai ", "mai ", "tomorrow "):
        if value.startswith(prefix):
            tomorrow = True
            value = value[len(prefix) :].strip()
            break
    if re.fullmatch(r"\d{2}:\d{2}", value):
        h, m = _clock(value)
        date = local.date() + timedelta(days=1 if tomorrow else 0)
        at = datetime(date.year, date.month, date.day, h, m, tzinfo=zone)
        if at.timestamp() <= now:
            at += timedelta(days=1)
        return validate_schedule({"kind": "once", "at": at.isoformat(), "timezone": timezone})
    # Accept ISO dates without requiring a technical form field.
    return validate_schedule({"kind": "once", "at": value, "timezone": timezone})


class Scheduler:
    def __init__(self, store, engine, cfg):
        self.db, self.engine, self.cfg = store, engine, cfg
        self.lock = asyncio.Lock()
        with store.lock:
            store.db.executescript("""
            CREATE TABLE IF NOT EXISTS kei_schedules(
              id TEXT PRIMARY KEY,owner TEXT NOT NULL,scope TEXT NOT NULL,channel TEXT NOT NULL,
              goal TEXT NOT NULL,server TEXT,mode TEXT NOT NULL,alarm INTEGER NOT NULL DEFAULT 0,
              schedule TEXT NOT NULL,status TEXT NOT NULL,next_run REAL,request_message TEXT,
              ack_message TEXT,created REAL NOT NULL,updated REAL NOT NULL,confirmed REAL,revision INTEGER NOT NULL DEFAULT 1);
            CREATE INDEX IF NOT EXISTS kei_schedule_due ON kei_schedules(status,next_run);
            CREATE TABLE IF NOT EXISTS kei_schedule_runs(
              id TEXT PRIMARY KEY,schedule TEXT NOT NULL,scheduled_for REAL NOT NULL,status TEXT NOT NULL,
              task TEXT,outbox TEXT,attempt INTEGER NOT NULL DEFAULT 0,retry_at REAL,lease_until REAL,
              result TEXT,created REAL NOT NULL,updated REAL NOT NULL,UNIQUE(schedule,scheduled_for));
            CREATE TABLE IF NOT EXISTS kei_schedule_history(
              id TEXT PRIMARY KEY,schedule TEXT NOT NULL,actor TEXT NOT NULL,event TEXT NOT NULL,data TEXT NOT NULL,at REAL NOT NULL);
            """)

    def _event(self, sid, actor, event, data=None):
        self.db.execute(
            "INSERT INTO kei_schedule_history VALUES (?,?,?,?,?,?)",
            (uid(), sid, str(actor), event, dumps(data or {}), time.time()),
        )

    def _public(self, row):
        value = dict(row)
        value["schedule"] = json.loads(value["schedule"])
        value["timezone"] = value["schedule"]["timezone"]
        value["alarm"] = bool(value["alarm"])
        return value

    def get(self, owner, schedule_id):
        row = self.db.one(
            "SELECT * FROM kei_schedules WHERE id=? AND owner=?", (str(schedule_id), str(owner))
        )
        if not row:
            raise PermissionError("Không thấy lịch hẹn thuộc account của m.")
        return self._public(row)

    def list(self, owner):
        return [
            self._public(r)
            for r in self.db.rows(
                "SELECT * FROM kei_schedules WHERE owner=? ORDER BY CASE WHEN status IN ('completed','cancelled') THEN 1 ELSE 0 END,created DESC LIMIT 100",
                (str(owner),),
            )
        ]

    def history(self, owner, schedule_id):
        self.get(owner, schedule_id)
        return self.db.rows(
            "SELECT * FROM kei_schedule_runs WHERE schedule=? ORDER BY scheduled_for DESC LIMIT 30",
            (schedule_id,),
        )

    def _authorize(self, owner, scope, server, mode, alarm=False):
        if mode not in ("observe", "change"):
            raise ValueError(
                "Mode dùng observe hoặc change; dangerous actions vẫn cần xác nhận riêng."
            )
        if alarm:
            if not str(owner).isdigit():
                raise ValueError("Báo thức cần Discord account đã xác thực.")
            return None
        target = self.engine.select(str(owner), scope, server)
        if mode == "change" and self.engine.permission(str(owner), target) != "copilot":
            raise PermissionError("Lịch sửa server cần quyền copilot của đúng server đó.")
        return target

    def propose(
        self,
        owner,
        scope,
        channel,
        goal,
        schedule,
        server=None,
        mode="observe",
        message_id=None,
        alarm=False,
    ):
        goal = str(goal).strip()
        if not goal or len(goal) > 4000:
            raise ValueError("Mục tiêu cần ngắn gọn, tối đa 4000 ký tự.")
        active = self.db.one(
            "SELECT count(*) n FROM kei_schedules WHERE owner=? AND status NOT IN ('cancelled','completed')",
            (str(owner),),
        )["n"]
        if active >= 50:
            raise ValueError("Tối đa 50 lịch chưa kết thúc mỗi người; hủy lịch cũ trong /settings.")
        schedule = validate_schedule(schedule, self.cfg.get("timezone", "Asia/Ho_Chi_Minh"))
        now = time.time()
        due = next_run(schedule, now)
        if due is None:
            raise ValueError("Giờ hẹn đã qua; chọn thời gian mới nhé.")
        target = self._authorize(owner, scope, server, mode, alarm)
        sid = uid()
        self.db.execute(
            """INSERT INTO kei_schedules(id,owner,scope,channel,goal,server,mode,alarm,schedule,status,next_run,request_message,created,updated)
                           VALUES (?,?,?,?,?,?,?,?,?,'pending',?,?,?,?)""",
            (
                sid,
                str(owner),
                scope,
                str(channel),
                goal,
                target,
                mode,
                int(alarm),
                dumps(schedule),
                due,
                str(message_id) if message_id else None,
                now,
                now,
            ),
        )
        self._event(
            sid, owner, "proposed", {"due": due, "server": target, "mode": mode, "alarm": alarm}
        )
        return self.get(owner, sid)

    def bind_confirmation(self, owner, schedule_id, message_id):
        row = self.get(owner, schedule_id)
        if row["status"] != "pending" or not str(message_id).strip():
            raise ValueError("Chỉ gắn xác nhận cho lịch đang chờ.")
        self.db.execute(
            "UPDATE kei_schedules SET ack_message=?,updated=? WHERE id=?",
            (str(message_id), time.time(), schedule_id),
        )
        return self.get(owner, schedule_id)

    def confirm(self, owner, schedule_id, source_message_id=None):
        row = self.get(owner, schedule_id)
        if row["status"] == "active":
            return row
        if row["status"] != "pending":
            raise ValueError("Lịch này không chờ xác nhận; mở /settings để xem.")
        if source_message_id is None or str(source_message_id) not in {
            row["request_message"],
            row["ack_message"],
        }:
            raise PermissionError("Xác nhận bằng 🕒 ở đúng yêu cầu gốc hoặc tin xác nhận của Kei.")
        self._authorize(owner, row["scope"], row["server"], row["mode"], row["alarm"])
        now = time.time()
        due = next_run(row["schedule"], now)
        if due is None:
            raise ValueError("Giờ hẹn đã qua trước lúc xác nhận; đổi giờ rồi xác nhận lại nhé.")
        self.db.execute(
            "UPDATE kei_schedules SET status='active',next_run=?,confirmed=?,updated=? WHERE id=? AND status='pending'",
            (due, now, now, schedule_id),
        )
        self._event(
            schedule_id,
            owner,
            "confirmed",
            {"source": str(source_message_id), "revision": row["revision"]},
        )
        return self.get(owner, schedule_id)

    def confirm_for_message(self, owner, message_id):
        rows = self.db.rows(
            "SELECT id FROM kei_schedules WHERE owner=? AND status='pending' AND (request_message=? OR ack_message=?)",
            (str(owner), str(message_id), str(message_id)),
        )
        return [self.confirm(owner, r["id"], str(message_id)) for r in rows]

    confirm_message = confirm_for_message

    def change(self, owner, schedule_id, **patch):
        row = self.get(owner, schedule_id)
        allowed = {"goal", "schedule", "server", "mode", "alarm", "message_id"}
        if not patch or set(patch) - allowed:
            raise ValueError("Chỉ sửa mục tiêu, thời gian, server hoặc mode của lịch hẹn.")
        if row["status"] in ("cancelled", "completed"):
            raise ValueError("Tạo lịch mới cho lịch đã kết thúc.")
        merged = {**row, **patch}
        schedule = validate_schedule(
            merged["schedule"], self.cfg.get("timezone", "Asia/Ho_Chi_Minh")
        )
        if not str(merged["goal"]).strip() or len(str(merged["goal"])) > 4000:
            raise ValueError("Mục tiêu cần 1–4000 ký tự.")
        due = next_run(schedule)
        if due is None:
            raise ValueError("Giờ mới đã qua.")
        server = self._authorize(
            owner, row["scope"], merged["server"], merged["mode"], merged["alarm"]
        )
        # Old clock reactions must not confirm a newly edited goal/time.
        self.db.execute(
            """UPDATE kei_schedules SET goal=?,schedule=?,server=?,mode=?,alarm=?,status='pending',next_run=?,
                           request_message=?,ack_message=NULL,confirmed=NULL,revision=revision+1,updated=? WHERE id=?""",
            (
                str(merged["goal"]).strip(),
                dumps(schedule),
                server,
                merged["mode"],
                int(bool(merged["alarm"])),
                due,
                str(patch["message_id"]) if patch.get("message_id") else None,
                time.time(),
                schedule_id,
            ),
        )
        self._event(
            schedule_id, owner, "edited_pending_confirmation", {"revision": row["revision"] + 1}
        )
        self._cancel_retries(schedule_id, "Schedule changed; old retry invalidated")
        return self.get(owner, schedule_id)

    update = change

    def _cancel_retries(self, schedule_id, reason):
        self.db.execute(
            "UPDATE kei_schedule_runs SET status='cancelled',retry_at=NULL,result=?,updated=? WHERE schedule=? AND status='retry'",
            (dumps({"note": reason}), time.time(), schedule_id),
        )

    def pause(self, owner, schedule_id):
        row = self.get(owner, schedule_id)
        if row["status"] not in ("active", "pending", "paused"):
            raise ValueError("Lịch đã kết thúc.")
        self.db.execute(
            "UPDATE kei_schedules SET status='paused',updated=? WHERE id=?",
            (time.time(), schedule_id),
        )
        self._event(schedule_id, owner, "paused")
        self._cancel_retries(schedule_id, "Schedule paused; pending retry cancelled")
        return self.get(owner, schedule_id)

    def resume(self, owner, schedule_id, message_id=None):
        row = self.get(owner, schedule_id)
        if row["status"] != "paused":
            raise ValueError("Chỉ tiếp tục lịch đang tạm dừng.")
        due = next_run(row["schedule"])
        if due is None:
            raise ValueError("Giờ hẹn đã qua; đổi giờ rồi bật lại nhé.")
        self.db.execute(
            "UPDATE kei_schedules SET status='pending',next_run=?,request_message=?,ack_message=NULL,confirmed=NULL,updated=? WHERE id=?",
            (due, str(message_id) if message_id else None, time.time(), schedule_id),
        )
        self._event(schedule_id, owner, "resumed_pending_confirmation")
        return self.get(owner, schedule_id)

    def cancel(self, owner, schedule_id):
        self.get(owner, schedule_id)
        self.db.execute(
            "UPDATE kei_schedules SET status='cancelled',updated=? WHERE id=?",
            (time.time(), schedule_id),
        )
        self._event(
            schedule_id,
            owner,
            "cancelled",
            {"note": "Future runs cancelled; an already dispatched task is separate"},
        )
        self._cancel_retries(schedule_id, "Schedule cancelled; pending retry cancelled")
        return self.get(owner, schedule_id)

    def _create_task(self, row, occurrence, now):
        target = self._authorize(row["owner"], row["scope"], row["server"], row["mode"], False)
        task = self.db.create_task(
            target,
            row["scope"],
            row["channel"],
            row["owner"],
            row["goal"],
            row["mode"],
            {
                "complexity": "deep",
                "steps": [
                    "Kiểm tra trạng thái và quyền hiện tại",
                    "Thực hiện đúng yêu cầu đã hẹn",
                    "Xác minh kết quả và báo lại",
                ],
            },
        )
        if hasattr(self.engine, "conversation"):
            self.engine.conversation.task_origin(
                task,
                row["scope"],
                row["owner"],
                row["channel"],
                row.get("request_message") or "",
                row.get("ack_message") or "",
            )
        self.db.execute(
            "UPDATE kei_schedule_runs SET task=?,status='running',attempt=attempt+1,retry_at=NULL,lease_until=?,updated=? WHERE id=?",
            (task, now + 120, now, occurrence),
        )
        self._event(row["id"], row["owner"], "dispatched", {"task": task, "occurrence": occurrence})
        return task

    async def _reconcile(self, now):
        launched = []
        timeout = max(60, int(self.cfg.get("scheduler", {}).get("task_timeout_seconds", 1800)))
        for run in self.db.rows(
            "SELECT * FROM kei_schedule_runs WHERE status IN ('claimed','running','waiting','retry','reconcile','delivering') ORDER BY created LIMIT 100"
        ):
            row = self.db.one("SELECT * FROM kei_schedules WHERE id=?", (run["schedule"],))
            if not row:
                continue
            row = self._public(row)
            if run["status"] == "retry":
                if (run["retry_at"] or 0) <= now and row["status"] == "active":
                    try:
                        with self.db.atomic():
                            current = self.db.one(
                                "SELECT * FROM kei_schedule_runs WHERE id=?", (run["id"],)
                            )
                            if current["status"] != "retry":
                                continue
                            task_id = self._create_task(row, run["id"], now)
                        self.engine.launch(task_id)
                        launched.append(task_id)
                    except (ValueError, PermissionError) as exc:
                        self.db.execute(
                            "UPDATE kei_schedule_runs SET status='blocked',result=?,updated=? WHERE id=?",
                            (dumps({"error": str(exc)}), now, run["id"]),
                        )
                continue
            if run["outbox"]:
                delivery = self.db.one(
                    "SELECT status,message FROM kei_outbox WHERE id=?", (run["outbox"],)
                )
                if delivery and delivery["status"] in ("sent", "failed", "uncertain"):
                    outcome = (
                        "succeeded"
                        if delivery["status"] == "sent"
                        else ("uncertain" if delivery["status"] == "uncertain" else "failed")
                    )
                    self.db.execute(
                        "UPDATE kei_schedule_runs SET status=?,result=?,updated=? WHERE id=?",
                        (
                            outcome,
                            dumps(
                                {
                                    "delivery": delivery["status"],
                                    "message": delivery["message"],
                                    "scope": "Discord send receipt; does not prove user awoke",
                                }
                            ),
                            now,
                            run["id"],
                        ),
                    )
                continue
            task = (
                self.db.one("SELECT * FROM kei_tasks WHERE id=?", (run["task"],))
                if run["task"]
                else None
            )
            if task:
                status = task["status"]
                if status == "succeeded":
                    self.db.execute(
                        "UPDATE kei_schedule_runs SET status='succeeded',result=?,updated=? WHERE id=?",
                        (
                            dumps(
                                {
                                    "task": task["id"],
                                    "summary": task["result"],
                                    "scope": "Existing agent verified completion",
                                }
                            ),
                            now,
                            run["id"],
                        ),
                    )
                elif status in ("waiting", "paused", "reconcile"):
                    self.db.execute(
                        "UPDATE kei_schedule_runs SET status=?,result=?,updated=? WHERE id=?",
                        (
                            "reconcile" if status == "reconcile" else "waiting",
                            dumps(
                                {
                                    "task": task["id"],
                                    "status": status,
                                    "note": "Needs requester/verification; not completed",
                                }
                            ),
                            now,
                            run["id"],
                        ),
                    )
                elif status in ("failed", "cancelled"):
                    changed = self.db.one(
                        "SELECT id FROM kei_actions WHERE task=? AND effect!='read' AND status IN ('started','done','failed') LIMIT 1",
                        (task["id"],),
                    )
                    retry = (
                        row["status"] == "active"
                        and row["mode"] == "observe"
                        and status == "failed"
                        and not changed
                        and run["attempt"] < 2
                    )
                    self.db.execute(
                        "UPDATE kei_schedule_runs SET status=?,retry_at=?,result=?,updated=? WHERE id=?",
                        (
                            "retry" if retry else status,
                            now + 60 if retry else None,
                            dumps(
                                {
                                    "task": task["id"],
                                    "summary": task["result"],
                                    "automatic_retry": bool(retry),
                                }
                            ),
                            now,
                            run["id"],
                        ),
                    )
                elif status in ("queued", "running") and now - run["created"] > timeout:
                    self.db.update_task(
                        task["id"],
                        status="cancelled",
                        result="Scheduled task timeout; already dispatched effects may be uncertain. Inspect before retry.",
                    )
                    self.db.execute(
                        "UPDATE kei_schedule_runs SET status='timed_out',result=?,updated=? WHERE id=?",
                        (
                            dumps(
                                {
                                    "task": task["id"],
                                    "verified": False,
                                    "note": "No success inferred; running external actions are not forcibly replayed/killed",
                                }
                            ),
                            now,
                            run["id"],
                        ),
                    )
                    self.db.queue(
                        row["channel"],
                        "-# Lịch hẹn quá thời gian chờ; chưa xác nhận hoàn tất. Mở /settings để kiểm tra.",
                    )
                elif status == "queued" and (run["lease_until"] or 0) <= now:
                    # Existing task ID is reused; never create a second mutation after a crash.
                    self.engine.launch(task["id"])
                    self.db.execute(
                        "UPDATE kei_schedule_runs SET lease_until=?,updated=? WHERE id=?",
                        (now + 120, now, run["id"]),
                    )
            elif run["status"] in ("claimed", "running", "reconcile"):
                self.db.execute(
                    "UPDATE kei_schedule_runs SET status='uncertain',result=?,updated=? WHERE id=?",
                    (
                        dumps({"note": "Dispatch record lacks its task; no blind replay"}),
                        now,
                        run["id"],
                    ),
                )
        self.db.execute(
            """UPDATE kei_schedules SET status='completed',updated=? WHERE status='active' AND next_run IS NULL
                           AND EXISTS (SELECT 1 FROM kei_schedule_runs r WHERE r.schedule=kei_schedules.id)
                           AND NOT EXISTS (SELECT 1 FROM kei_schedule_runs r WHERE r.schedule=kei_schedules.id
                                           AND r.status IN ('claimed','running','waiting','retry','reconcile','delivering'))""",
            (now,),
        )
        return launched

    async def tick(self, now=None):
        now = time.time() if now is None else float(now)
        launched = []
        async with self.lock:
            launched += await self._reconcile(now)
            for original in self.db.rows(
                "SELECT * FROM kei_schedules WHERE status='active' AND next_run<=? ORDER BY next_run LIMIT 20",
                (now,),
            ):
                task_id = None
                try:
                    with self.db.atomic():
                        current = self.db.one(
                            "SELECT * FROM kei_schedules WHERE id=?", (original["id"],)
                        )
                        if (
                            not current
                            or current["status"] != "active"
                            or current["next_run"] is None
                            or current["next_run"] > now
                        ):
                            continue
                        row = self._public(current)
                        run_id = uid()
                        due = row["next_run"]
                        inserted = self.db.execute(
                            "INSERT OR IGNORE INTO kei_schedule_runs(id,schedule,scheduled_for,status,created,updated) VALUES (?,?,?,'claimed',?,?)",
                            (run_id, row["id"], due, now, now),
                        ).rowcount
                        future = next_run(row["schedule"], now)
                        self.db.execute(
                            "UPDATE kei_schedules SET next_run=?,updated=? WHERE id=?",
                            (future, now, row["id"]),
                        )
                        if not inserted:
                            continue
                        previous = self.db.one(
                            "SELECT id FROM kei_schedule_runs WHERE schedule=? AND id!=? AND status IN ('claimed','running','waiting','retry','reconcile','delivering') LIMIT 1",
                            (row["id"], run_id),
                        )
                        if previous:
                            self.db.execute(
                                "UPDATE kei_schedule_runs SET status='skipped',result=? WHERE id=?",
                                (
                                    dumps(
                                        {
                                            "reason": "Previous occurrence still active; overlap skipped"
                                        }
                                    ),
                                    run_id,
                                ),
                            )
                            continue
                        lateness = now - due
                        limit = int(
                            self.cfg.get("scheduler", {}).get(
                                (
                                    "alarm_max_lateness_seconds"
                                    if row["alarm"]
                                    else "task_max_lateness_seconds"
                                ),
                                3600 if row["alarm"] else 86400,
                            )
                        )
                        if lateness > limit:
                            self.db.execute(
                                "UPDATE kei_schedule_runs SET status='skipped',result=? WHERE id=?",
                                (
                                    dumps(
                                        {
                                            "reason": "Missed while offline; outside configured lateness window",
                                            "late_seconds": lateness,
                                        }
                                    ),
                                    run_id,
                                ),
                            )
                            continue
                        try:
                            self._authorize(
                                row["owner"], row["scope"], row["server"], row["mode"], row["alarm"]
                            )
                            if row["alarm"]:
                                outbox = uid()
                                text = "Tới giờ rồi này. " + row["goal"][:1600]
                                self.db.execute(
                                    "INSERT INTO kei_outbox(id,channel,content,status,message,at,attempts) VALUES (?,?,?,'pending',NULL,?,0)",
                                    (outbox, row["owner"], text, now),
                                )
                                self.db.execute(
                                    "UPDATE kei_schedule_runs SET status='delivering',outbox=?,attempt=1,updated=? WHERE id=?",
                                    (outbox, now, run_id),
                                )
                            else:
                                task_id = self._create_task(row, run_id, now)
                        except (ValueError, PermissionError) as exc:
                            self.db.execute(
                                "UPDATE kei_schedule_runs SET status='blocked',result=?,updated=? WHERE id=?",
                                (dumps({"error": str(exc), "verified": False}), now, run_id),
                            )
                            self.db.queue(row["channel"], "-# Lịch hẹn chưa chạy: " + str(exc))
                    if task_id:
                        self.engine.launch(task_id)
                        launched.append(task_id)
                except sqlite3.IntegrityError:
                    # Another timer won the durable occurrence claim.
                    continue
            return launched

    def chat(self, owner, scope, channel, request_id, decision):
        action = decision.get("schedule_action")
        sid = decision.get("schedule_id")
        if action == "create":
            row = self.propose(
                owner,
                scope,
                channel,
                decision.get("scheduled_goal") or decision.get("goal") or "",
                decision.get("schedule"),
                decision.get("server") or None,
                decision.get("schedule_mode") or "observe",
                request_id,
                bool(decision.get("alarm", False)),
            )
        elif action == "list":
            rows = self.list(owner)
            lines = [r["id"] + " · " + r["status"] + " · " + r["goal"][:90] for r in rows[:12]]
            return {
                "notice": "-# " + ("\n-# ".join(lines) if lines else "Chưa có lịch hẹn."),
                "schedules": rows,
            }
        elif action in ("update", "pause", "resume", "cancel"):
            if not sid:
                raise ValueError("Chọn lịch trong /settings hoặc nêu đúng ID lịch cần sửa.")
            if action == "update":
                patch = {"message_id": request_id}
                for src, dst in [
                    ("scheduled_goal", "goal"),
                    ("schedule", "schedule"),
                    ("server", "server"),
                    ("schedule_mode", "mode"),
                ]:
                    if decision.get(src):
                        patch[dst] = decision[src]
                row = self.change(owner, sid, **patch)
            elif action == "resume":
                row = self.resume(owner, sid, request_id)
            else:
                row = getattr(self, action)(owner, sid)
        else:
            raise ValueError("Không hiểu thao tác lịch hẹn.")
        if row["status"] == "pending":
            dt = datetime.fromtimestamp(row["next_run"], _zone(row["timezone"]))
            notice = (
                "-# "
                + dt.strftime("%d/%m %H:%M")
                + " · "
                + row["timezone"]
                + " · Thả 🕒 vào tin này hoặc yêu cầu gốc để bật lịch."
            )
        else:
            notice = "-# Lịch " + row["id"] + ": " + row["status"] + "."
        return {
            "notice": notice,
            "schedule": row,
            "schedule_id": row["id"],
            "confirmation_required": row["status"] == "pending",
        }
