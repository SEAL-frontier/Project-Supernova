# Lịch hẹn / Scheduled tasks

Ask Kei in normal chat, or use **`/tasks`** from the settings home screen:

```text
Kei, mỗi ngày 07:00 kiểm tra TPS server survival, chỉ đọc thôi.
Kei, ngày mai 06:30 gọi anh dậy đi học.
Kei, tạm dừng lịch kiểm tra TPS.
```

Kei adds one small `-#` line to her acknowledgment. **Click the clock confirmation
or react with 🕒 to the original request / Kei's linked acknowledgment** before
the schedule activates. Other people's reactions cannot confirm your schedule.
Changing the time, target or goal requires a fresh confirmation.

Giờ luôn đi kèm timezone, mặc định **Asia/Ho_Chi_Minh** cho deployment Việt Nam.
Không có trò hẹn 7 giờ sáng xong nàng đem UTC ra úp sọt m 😭

## Supported times

| Input in setup | Meaning |
|---|---|
| `07:00` | Next 07:00 in your selected timezone |
| `ngày mai 07:00` / `tomorrow 07:00` | Tomorrow morning |
| `mỗi ngày 07:00` / `daily 07:00` | Daily |
| `hàng tuần t2,t4 07:00` / `weekly mon,wed 07:00` | Monday and Wednesday |
| `2026-10-17 07:00` | One specific local date/time |
| `cron 0 7 * * 1-5` | Weekdays at 07:00 |

Cron supports the standard five numeric fields, ranges, lists and steps. It does
not run shell expressions. Missing daylight-saving wall times are skipped and a
repeated wall time runs once. Explicit ISO offsets are accepted for exact dates.

## Permissions and outcomes

- Owners see only their own schedules and history. Other users' private goals are
  not exposed by relationship profiles or ranks.
- The target server is resolved and authorized at creation, confirmation **and
  dispatch**. Revoked rights block execution. A vague server name does not pick an
  arbitrary target.
- Observe schedules cannot change files/configuration. Change schedules require
  copilot permission; dangerous actions still stop for the existing exact-action
  approval.
- Work goes through the existing planner, tools, evidence checks and progress.
  Dispatching a timer does not mean the job succeeded. `/tasks` shows the actual
  task outcome.
- A wake-up reminder sends a DM. A Discord send receipt proves delivery only;
  Kei cannot prove someone woke up from a message.

## Pause, resume and recovery

Pause/cancel stops future occurrences. A task already dispatched remains visible
as its own job; cancelling a schedule cannot undo a command already sent. Resume
asks for another clock confirmation. Use task controls to stop ongoing work.

Occurrence IDs persist in SQLite. Restarts reuse the same task rather than
creating another mutation. Interrupted/uncertain changes wait for reconciliation.
Read-only failures may retry once after a backoff; changes do not automatically
replay. An unfinished occurrence prevents overlapping runs of the same schedule.

When Kei is offline, missed recurring intervals are consolidated rather than
spamming all missed runs. Defaults allow a task up to 24 hours late and an alarm
up to one hour late. The operator can change these bounds:

```yaml
scheduler:
  task_timeout_seconds: 1800
  task_max_lateness_seconds: 86400
  alarm_max_lateness_seconds: 3600
```

A timeout is recorded as unverified; it does not silently kill host processes or
pretend a running external operation was undone. The database and task audit keep
the evidence needed to inspect it before retrying.
