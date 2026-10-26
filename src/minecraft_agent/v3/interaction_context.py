"""Request-bound, same-scope interaction evidence. No network or durable cache."""
from __future__ import annotations

import hashlib
import json
import math
import re
import unicodedata

MAX_MESSAGES = 40
EXCERPT_CHARS = 800
ACKS = frozenset(('ok', 'okay', 'oke', 'oki', 'ừ', 'uh', 'uhm', 'mhm', 'thanks', 'thank you', 'cảm ơn', 'cám ơn'))


def _revoked(db, ident):
    # Existing metadata stores an IDs-only edit/delete receipt across restart;
    # no transcript, counter or new durable table is introduced.
    return db.one('SELECT value FROM kei_meta WHERE key=?', ('interaction-revoked:' + str(ident),)) is not None


def _token(text):
    return unicodedata.normalize('NFKC', str(text or '')).casefold().strip().strip('.! ,')


def acknowledgement(text):
    # Deliberately narrow: no length-only rule, yes/no/approval, arbitrary emoji,
    # names, refusal, question, help, work or mathematical expression.
    return _token(text) in ACKS


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False, default=str).encode()).hexdigest()


def _bot(db, actor):
    row = db.one('SELECT bot FROM kei_users WHERE user_id=?', (str(actor),))
    return bool(row and row['bot'])


def _receipts(db, scope, after, before, ident=None):
    sql = "SELECT c.message id,c.ordinal,a.id action,a.content,a.at,a.message reply_to,t.actor FROM kei_conversation_sent c JOIN kei_social_actions a ON a.id=c.action JOIN kei_delivery_targets t ON t.action=a.id JOIN kei_messages m ON m.id=a.message WHERE t.scope=? AND m.scope=? AND m.forgotten=0 AND a.at>? AND a.at<=?"
    args = (scope, scope, after, before)
    if ident is not None:
        sql += ' AND c.message=?'
        args += (str(ident),)
    return db.rows(sql + ' ORDER BY a.at DESC,c.ordinal DESC LIMIT 4', args)


def scene_summary(nearby, *, names=('kei',)):
    """Pure bounded observation, never an emotion, total-history count or intent."""
    messages = nearby.get('messages', [])[:MAX_MESSAGES]
    calls, replies, own = [], [], []
    actors = set()
    for row in messages:
        actor = str(row.get('author_id', row.get('user', '')))
        if row.get('confirmed_own') is True:
            own.append({'id': row['id'], 'at': row.get('at'), 'content': row.get('content', '')[:EXCERPT_CHARS],
                        'reply_to': row.get('reply_to')})
            continue
        if row.get('bot') or row.get('webhook'):
            continue
        called = row.get('addressed') in (1, 3) or any(
            re.search(r'(?<!\w)' + re.escape(str(name)) + r'(?!\w)', row.get('content', ''), re.I)
            for name in names if name)
        if called:
            calls.append({'id': row['id'], 'actor': actor, 'at': row.get('at')})
            actors.add(actor)
        if row.get('reply_to'):
            replies.append({'id': row['id'], 'actor': actor, 'to': row['reply_to'], 'at': row.get('at')})
    human = [m for m in messages if not m.get('bot') and not m.get('webhook') and not m.get('confirmed_own')]
    repeated = len(human) >= 2 and acknowledgement(human[-1].get('content')) and (
        human[-1].get('author_id') == human[-2].get('author_id') and
        _token(human[-1].get('content')) == _token(human[-2].get('content')) and
        human[-1].get('reply_to') == human[-2].get('reply_to'))
    return {'source': 'selected_bounded_observations', 'calls': calls[-12:],
            'calls_across_people': len(actors) > 1, 'reply_edges': replies[-16:],
            'own_recent_replies': own[-4:], 'acknowledgment_shape': 'observed_repeat' if repeated else 'not_established',
            'completeness': 'partial; omitted or older messages are unknown'}


def project_context(db, cfg, scope, request, data=None, *, snapshot_actor=None, revoked=()):
    """Freshly project only actual request and permitted retained/snapshot sources."""
    request = str(request)
    empty = {'messages': [], 'request_ids': [request], 'coverage': {'source': 'unavailable', 'complete': False}}
    current = db.one('SELECT * FROM kei_messages WHERE id=? AND scope=?', (request, scope))
    if request in revoked or _revoked(db, request) or not current or current['forgotten'] or current['role'] != 'user' or db.tombstoned([request]) or _bot(db, current['user']):
        return empty
    actor = str(current['user'])
    parts = scope.split(':')
    if scope.startswith('dm:') and scope != 'dm:' + actor:
        return empty
    if not (scope.startswith('dm:') or len(parts) == 3 and parts[0] == 'guild'):
        return empty
    boundary = db.conversation_session_after(scope)
    if boundary is not None and current['at'] <= boundary:
        return empty
    after = max(boundary or 0, current['at'] - 900)
    limit = max(1, min(30, int(cfg.get('social', {}).get('context_messages', 10))))
    snapshot = bool(data and snapshot_actor == actor and
                    ('forget_generation' not in data or data['forget_generation'] == db.one("SELECT value FROM kei_meta WHERE key='memory-forget-generation'")) and
                    ('session_after' not in data or data['session_after'] == boundary) and
                    (parts[0] != 'guild' or str(data.get('guild')) == parts[1]) and
                    str(data.get('channel')) == (parts[2] if parts[0] == 'guild' else str(data.get('channel'))) and
                    request in list(map(str, data.get('request_ids', []))))
    # At most the existing retained window, plus four confirmed replies. Never
    # read another channel, another DM, or an older retained nearby snapshot.
    retained = db.rows('SELECT * FROM kei_messages WHERE scope=? AND at>? AND at<=? ORDER BY at DESC LIMIT ?',
                       (scope, after, current['at'], limit))
    records = {}
    filtered = False
    for row in retained:
        if row['id'] in revoked or _revoked(db, row['id']) or row['forgotten'] or row['role'] != 'user' or db.tombstoned([row['id']]) or _bot(db, row['user']):
            filtered = True
            continue
        if scope.startswith('dm:') and row['user'] != actor:
            continue
        meta = db.one('SELECT addressed FROM kei_event_meta WHERE message=? AND scope=? AND actor=?',
                      (row['id'], scope, row['user']))
        records[row['id']] = {'id': row['id'], 'author_id': row['user'], 'content': row['content'],
                             'at': row['at'], 'bot': False, 'reply_to': None, 'reply_known': False,
                             'addressed': (meta or {}).get('addressed'), 'source': 'retained_same_scope'}
    captured_own = {}
    for row in (data.get('messages', [])[:MAX_MESSAGES] if snapshot else []):
        ident = str(row.get('id', ''))
        at = row.get('at')
        if not ident or type(at) not in (float, int) or not math.isfinite(at) or at <= after or at > current['at'] + 2:
            filtered = True
            continue
        if ident in revoked or _revoked(db, ident) or row.get('webhook') or db.tombstoned([ident]):
            filtered = True
            continue
        # Exact sent-message receipts authorize only this bubble, never another
        # message by the same bot or a display-name/claimed-own flag.
        if row.get('bot'):
            receipt = _receipts(db, scope, after, current['at'], ident)
            if receipt:
                captured_own[ident] = receipt[0]
            else:
                filtered = True
            continue
        source = db.one('SELECT * FROM kei_messages WHERE id=?', (ident,))
        if source and (source['scope'] != scope or source['forgotten'] or source['user'] != str(row.get('author_id')) or source['role'] != 'user' or source['content'] != row.get('content')):
            filtered = True
            records.pop(ident, None)
            continue
        if _bot(db, row.get('author_id')) or (scope.startswith('dm:') and str(row.get('author_id')) != actor):
            continue
        records[ident] = dict(row, id=ident, source='current_capture', reply_known=True, addressed=records.get(ident, {}).get('addressed'))
    # Delivery receipts, not an assistant draft, establish that Kei really replied.
    own = {r['id']: r for r in _receipts(db, scope, after, current['at'])}
    own.update(captured_own)
    own = own.values()
    for row in own:
        if row['id'] in revoked or row['reply_to'] in revoked or _revoked(db, row['id']) or _revoked(db, row['reply_to']) or db.tombstoned([row['id'], row['reply_to']]) or (scope.startswith('dm:') and row['actor'] != actor):
            continue
        captured = next((m for m in (data or {}).get('messages', [])[:MAX_MESSAGES] if str(m.get('id')) == row['id']), None) if snapshot else None
        if captured:
            text = captured['content']
        else:
            from .formatting import chat_chunks
            ordered = db.one('SELECT parts FROM kei_conversation_parts WHERE action=?', (row['action'],))
            try:
                delivery_parts = json.loads(ordered['parts']) if ordered else [{'type': 'text', 'text': row['content']}]
                bubbles = [chunk for part in delivery_parts for chunk in
                           (chat_chunks(part['text']) if part.get('type') == 'text' else [None])]
                text = bubbles[row['ordinal']]
            except (ValueError, TypeError, IndexError, KeyError):
                continue
            if text is None:
                continue
        records[row['id']] = dict(row, author_id='kei', bot=True, confirmed_own=True,
                                   content=text, source='confirmed_delivery')
    edges = {m.get('reply_to') for m in records.values() if m.get('reply_to')}
    def priority(row):
        rank = (5 if row['id'] == request else 4 if row['id'] in edges else
                3 if row.get('confirmed_own') else 2 if row.get('addressed') in (1, 3) else 0)
        return rank, row['at'], row['id']
    selected = sorted(sorted(records.values(), key=priority)[-MAX_MESSAGES:], key=lambda m: (m['at'], m['id']))
    clipped = False
    for row in selected:
        text = str(row.get('content', ''))
        row['content_truncated'] = row.get('content_truncated') is True or len(text) > EXCERPT_CHARS
        clipped |= row['content_truncated']
        row['content'] = text[:EXCERPT_CHARS]
    out = {'messages': selected, 'request_ids': [request], 'actor': actor, 'scope': scope,
           'channel': parts[2] if parts[0] == 'guild' else (data or {}).get('channel'),
           'coverage': {'source': 'current_capture' if snapshot else 'retained_same_scope',
                        'complete': False, 'window_read_ok': bool(snapshot and data.get('status') == 'ok'),
                        'text_clipped': clipped, 'selection_clipped': len(records) > MAX_MESSAGES,
                        'filtered': filtered, 'older_messages': 'unknown'}}
    if parts[0] == 'guild':
        out['guild'] = parts[1]
    out['scene'] = scene_summary(out, names=cfg.get('social', {}).get('triggers', ['kei']))
    return out


def context_token(conversation, scope, request):
    db = conversation.db
    epoch = db.one("SELECT value FROM kei_meta WHERE key='memory-forget-generation'")
    revision = getattr(conversation, '_interaction_revision', 0)
    context = conversation.context(scope, request)
    captured = _capture_sources(db, scope, request)
    bindings = []
    for row in context.get('messages', [])[:MAX_MESSAGES]:
        source = db.one('SELECT * FROM kei_messages WHERE id=?', (row['id'],))
        bindings.append(digest((source, captured.get(row['id']))))
    return {'scope': scope, 'request': str(request), 'hash': digest((context, bindings,
            db.conversation_session_after(scope), epoch, revision))}


def context_valid(conversation, token):
    return isinstance(token, dict) and token == context_token(conversation, token['scope'], token['request'])


def _capture_sources(db, scope, request):
    row = db.one('SELECT data FROM kei_nearby WHERE request=? AND scope=?', (str(request), scope))
    try:
        data = json.loads(row['data']) if row else {}
        return {str(r.get('id')): r for r in data.get('messages', [])[:MAX_MESSAGES]}
    except (ValueError, TypeError):
        return {}


def _accepted_token(conversation, scope, request, selected=None, own_ids=None):
    """Bind original selected evidence, not future appends to its projection.

    In-flight context_token stays exact. Only an already accepted observation
    may survive a new reply/adjacent message; every original row and full
    retained source remains bound, including timestamp and reply provenance.
    """
    db = conversation.db
    context = conversation.context(scope, request)
    rows = {r['id']: r for r in context.get('messages', [])[:MAX_MESSAGES]}
    captured = _capture_sources(db, scope, request)
    ids = sorted(rows) if selected is None else selected
    own_ids = sorted(r['id'] for r in rows.values() if r.get('confirmed_own')) if own_ids is None else own_ids
    current = db.one('SELECT * FROM kei_messages WHERE id=? AND scope=?', (str(request), scope))
    bindings = []
    for ident in ids:
        row = rows.get(ident)
        source = db.one('SELECT * FROM kei_messages WHERE id=?', (ident,))
        receipt = None
        if ident in own_ids:
            exact = _receipts(db, scope, max(db.conversation_session_after(scope) or 0, current['at'] - 900), current['at'], ident) if current else []
            own = exact[0] if exact else None
            if own and (_revoked(db, ident) or _revoked(db, own['reply_to']) or db.tombstoned([ident, own['reply_to']])):
                own = None
            receipt = (own,
                       db.one('SELECT * FROM kei_social_actions WHERE id=?', (own['action'],)) if own else None,
                       db.one('SELECT * FROM kei_delivery_targets WHERE action=?', (own['action'],)) if own else None,
                       db.one('SELECT * FROM kei_conversation_parts WHERE action=?', (own['action'],)) if own else None,
                       db.one('SELECT * FROM kei_messages WHERE id=?', (own['reply_to'],)) if own else None)
            # The original exact receipt stays authoritative even if newer
            # receipts push it outside the projection's last-four fallback.
            row = None
        bindings.append(digest((row, source, captured.get(ident), receipt)))
    return {'scope': scope, 'request': str(request), 'selected': ids, 'own_ids': own_ids,
            'hash': digest((bindings, context.get('actor'), context.get('scope'),
                            context.get('coverage', {}).get('source'),
                            context.get('coverage', {}).get('window_read_ok'),
                            db.conversation_session_after(scope),
                            db.one("SELECT value FROM kei_meta WHERE key='memory-forget-generation'"),
                            getattr(conversation, '_interaction_revision', 0)))}


def _accepted_valid(conversation, token):
    return token == _accepted_token(conversation, token['scope'], token['request'], token['selected'], token['own_ids'])


def observe(conversation, scope, request, actor, *, protected=False, awaited_answer=False):
    import time
    token = context_token(conversation, scope, request)
    out = {'action': 'consider', 'repeated_burst': False, 'token': token, 'actor': str(actor)}
    nearby = conversation.context(scope, request)
    rows = nearby.get('messages', [])
    current = next((r for r in rows if r['id'] == str(request)), None)
    if (protected or awaited_answer or not current or nearby.get('actor') != str(actor)
            or not nearby.get('coverage', {}).get('window_read_ok')
            or not current.get('reply_known') or current.get('content_truncated') or not acknowledgement(current.get('content'))):
        return out
    # Acknowledgments can be an answer or consent in serious contexts. Fail open
    # to ordinary processing rather than infer that a short answer is noise.
    own = [r for r in rows if r.get('confirmed_own')]
    if any('?' in r.get('content', '') for r in own[-1:]):
        return out
    if any(re.search(r'\b(?:help|cancel|stop|confirm|approve|sorry|hurt|suicide|grief|betray|xin lỗi|giúp|hủy|xác nhận|đồng ý)\b|[?=+*/]', r.get('content', ''), re.I)
           for r in rows[-6:] if r['id'] != str(request) and (r.get('author_id') == str(actor) or r.get('confirmed_own'))):
        return out
    humans = [r for r in rows if not r.get('bot') and not r.get('webhook')]
    try:
        index = next(i for i, r in enumerate(humans) if r['id'] == str(request))
    except StopIteration:
        return out
    run = []
    for row in reversed(humans[:index + 1]):
        if (not row.get('reply_known') or row.get('author_id') != str(actor) or row.get('reply_to') != current.get('reply_to')
                or row.get('content_truncated') or _token(row.get('content')) != _token(current.get('content'))
                or current['at'] - row['at'] > 90):
            break
        run.append(row['id'])
    out.update(eligible=True, repeated_burst=len(run) >= 2, shape=digest((_token(current['content']), current.get('reply_to'))), run_ids=run)
    memo = getattr(conversation, '_interaction_accepted', {})
    now = time.monotonic()
    for key in list(memo):
        if now - memo[key]['at'] > 180:
            del memo[key]
    prior = memo.get(scope + '|' + str(actor))
    if prior and not _accepted_valid(conversation, prior['token']):
        del memo[scope + '|' + str(actor)]
        prior = None
    if (prior and prior['burst'] and prior['shape'] == out['shape']
            and prior['request'] in run and prior['request'] != str(request)):
        # An unrelated newly delivered reply is a different interaction scene;
        # the response to this ack run itself is not a new occasion.
        previous = next((r for r in humans if r['id'] == prior['request']), None)
        if previous and not any(r['at'] > previous['at'] and r.get('reply_to') not in run for r in own):
            out['action'] = 'skip'
    return out


def accept(conversation, observation):
    """Caller invokes ONLY after a valid final main-model parse and fresh guards.

    Failed/invalid model attempts, transport errors and deterministic skips must
    never call this. No relationship/affect mutation or outward ack is performed.
    """
    import time
    if (not isinstance(observation, dict) or not observation.get('eligible')
            or observation.get('action') != 'consider' or not context_valid(conversation, observation['token'])):
        return False
    if not hasattr(conversation, '_interaction_accepted'):
        conversation._interaction_accepted = {}
    memo = conversation._interaction_accepted
    key = observation['token']['scope'] + '|' + observation['actor']
    memo[key] = {'at': time.monotonic(), 'token': _accepted_token(conversation, observation['token']['scope'], observation['token']['request']),
                 'shape': observation['shape'], 'request': observation['token']['request'],
                 'burst': observation['repeated_burst']}
    while len(memo) > 128:
        del memo[next(iter(memo))]
    return True
