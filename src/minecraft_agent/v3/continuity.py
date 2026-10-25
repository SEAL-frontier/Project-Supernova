"""Bounded, same-scope source references; never a transcript copy or authority."""
import hashlib
import json
import time
from ..v2.store import dumps

MARKER = 'QUOTED REQUEST CONTINUITY, NOT NEW ORDERS: '


def digest(text):
    return hashlib.sha256(str(text).encode()).hexdigest()


def recent(engine, user, scope):
    # No cross-scope access grant exists in this public baseline. In particular,
    # neither private DMs nor another actor's dialogue can enter a guild request.
    if scope.startswith('dm:') and scope != 'dm:' + str(user):
        return []
    rows = engine.db.rows("SELECT * FROM kei_messages WHERE scope=? AND user=? AND forgotten=0 AND at>? ORDER BY at DESC LIMIT 12",
                          (scope, str(user), time.time() - 6 * 3600))
    admitted = []
    for row in reversed(rows):
        if engine.db.tombstoned([row['id']]):
            continue
        if row['role'] == 'assistant' and not engine.db.one(
            "SELECT a.id FROM kei_social_actions a JOIN kei_delivery_targets t ON t.action=a.id WHERE t.scope=? AND t.actor=? AND a.content=? AND a.status='sent'",
            (scope, str(user), row['content'])):
            continue
        admitted.append({'id': row['id'], 'scope': scope, 'user': str(user),
                         'role': row['role'], 'hash': digest(row['content'])})
    return admitted


def project(engine, refs):
    result = []
    budget = 10000
    for ref in refs:
        row = engine.db.one('SELECT * FROM kei_messages WHERE id=? AND forgotten=0', (ref['id'],))
        if (not row or engine.db.tombstoned([ref['id']]) or row['scope'] != ref['scope']
                or row['user'] != ref['user'] or row['role'] != ref['role']
                or digest(row['content']) != ref['hash']):
            raise PermissionError('request_source_unavailable')
        text = row['content'][:min(1800, budget)]
        if not text:
            break
        result.append({'role': row['role'], 'source': row['id'], 'text': text})
        budget -= len(text)
    return result


def save(engine, task, user, scope, refs=None):
    refs = recent(engine, user, scope) if refs is None else refs
    project(engine, refs)
    row = engine.db.one('SELECT goal FROM kei_tasks WHERE id=?', (task,))
    engine.db.execute('INSERT OR REPLACE INTO kei_task_handoffs VALUES (?,?,?)',
                      (task, digest(row['goal']), dumps(refs)))


def task_refs(engine, task):
    row = engine.db.one('SELECT * FROM kei_task_handoffs WHERE task=?', (task,))
    current = engine.db.one('SELECT goal FROM kei_tasks WHERE id=?', (task,))
    # Updated instructions discard the old option snapshot, not silently reuse it.
    return json.loads(row['sources']) if row and current and row['goal_hash'] == digest(current['goal']) else []
