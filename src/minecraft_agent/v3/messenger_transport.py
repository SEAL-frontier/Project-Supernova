"""Discord-only messenger boundary. No inference, retries, queue or policy writes.

The caller owns retained-source authority, recipient refusal and durable uncertainty.
All callbacks must be local closures, never model-supplied code or paths.
"""
from __future__ import annotations

import hashlib
import inspect
import io
import itertools
import json
import os
import pathlib
import re
import stat
import time
import unicodedata
from dataclasses import dataclass

import discord

MAX_LOOKUP = 1024
_ID = re.compile(r'[0-9]{1,20}\Z')
_MENTION = re.compile(r'<@!?([0-9]{1,20})>\Z')


def _id(value):
    value = str(value)
    return value if _ID.fullmatch(value) and 0 < int(value) < 2**64 else ''


def _check(check):
    if check is not None:
        result = check()
        if inspect.isawaitable(result):
            if inspect.iscoroutine(result):
                result.close()
            raise TypeError('messenger_check_must_be_synchronous')
        if result is not True:
            raise PermissionError('messenger_source_revoked')


async def _await(awaitable, check=None):
    try:
        return await awaitable
    finally:
        _check(check)


async def _admit(bot, actor, scope, check=None):
    gate = getattr(bot, 'service_authorize', None)
    if gate is None:
        return getattr(bot, 'guild_access', None) is None
    return await _await(gate(str(actor), str(scope), 'messenger'), check) is True


def _human(user, expected):
    return bool(user is not None and _id(getattr(user, 'id', '')) == str(expected)
                and getattr(user, 'bot', True) is False
                and not getattr(user, 'system', False))


def _alias(user):
    text = str(getattr(user, 'nick', None) or getattr(user, 'global_name', None)
               or getattr(user, 'name', None) or 'Discord user')
    text = ''.join(c for c in text if not unicodedata.category(c).startswith('C'))
    text = re.sub(r'[@`*_~<>\\|]', '', text).strip()
    return text[:80] or 'Discord user'


def _identity(user):
    ident, alias = str(user.id), _alias(user)
    return {'id': ident, 'user_id': ident, 'alias': alias, 'name': alias, 'human': True, 'verified': True}


def _names(user, guild_alias):
    values = [getattr(user, 'name', None), getattr(user, 'global_name', None)]
    if guild_alias:
        values.append(getattr(user, 'nick', None))
    return {str(v).casefold() for v in values if v}


async def resolve_recipient(bot, query, requester, scope, channel, known=None, *, guard=None):
    """Exact aliases only; cached discovery followed by exact fresh member reads.

    `known` may narrow candidate IDs but cannot introduce an unverified alias.
    Name lookups never fetch arbitrary users or search a guild over REST.
    """
    _check(guard)
    requester, scope = _id(requester), str(scope)
    if not requester or not isinstance(query, str) or not query or len(query) > 120:
        return {'status': 'not_found', 'candidates': []}
    guild = getattr(channel, 'guild', None)
    if guild:
        if scope != f'guild:{guild.id}:{channel.id}':
            return {'status': 'denied', 'candidates': []}
    elif scope != 'dm:' + requester:
        return {'status': 'denied', 'candidates': []}
    if not await _admit(bot, requester, scope, guard):
        return {'status': 'denied', 'candidates': []}
    try:
        if guild:
            actor = await _await(guild.fetch_member(int(requester)), guard)
        else:
            actor = await _await(bot.fetch_user(int(requester)), guard)
    except PermissionError:
        raise
    except (LookupError, OSError):
        return {'status': 'denied', 'candidates': []}
    except Exception as exc:
        if isinstance(exc, PermissionError):
            raise
        return {'status': 'denied', 'candidates': []}
    if not _human(actor, requester):
        return {'status': 'denied', 'candidates': []}
    match = _MENTION.fullmatch(query)
    explicit = _id(match.group(1) if match else query)
    if not explicit and (query.startswith('<@') or query.isdecimal()):
        return {'status': 'not_found', 'candidates': []}
    candidates = {}
    guilds = [guild] if guild else list(itertools.islice(getattr(bot, 'guilds', ()), 64))
    budget = MAX_LOOKUP
    for context in guilds:
        # A DM alias must belong to an actual common guild, not bot-global users.
        if not guild and not context.get_member(int(requester)):
            continue
        for member in itertools.islice(getattr(context, 'members', ()), budget):
            budget -= 1
            ident = _id(getattr(member, 'id', ''))
            if ident and (ident == explicit if explicit else query.casefold() in _names(member, bool(guild))):
                candidates.setdefault(ident, (member, context))
        if budget <= 0:
            break
    # Indexed username/global-name discovery is bounded and still needs a real
    # guild context. Stored nicknames/account_display never become global aliases.
    store = getattr(bot, 'store', None)
    if store is not None and not explicit:
        try:
            rows = store.rows('SELECT user_id FROM kei_users WHERE bot=0 AND (username=? COLLATE NOCASE OR global_name=? COLLATE NOCASE) LIMIT 33', (query, query))
        except Exception:
            rows = []
        for row in rows:
            ident = _id(row['user_id'])
            for context in guilds:
                if not guild and not context.get_member(int(requester)):
                    continue
                member = context.get_member(int(ident)) if ident else None
                if member and query.casefold() in _names(member, bool(guild)):
                    candidates.setdefault(ident, (member, context))
    if explicit and explicit not in candidates:
        try:
            user = await _await(bot.fetch_user(int(explicit)), guard)
        except PermissionError:
            raise
        except Exception:
            user = None
        if _human(user, explicit):
            candidates[explicit] = (user, None)
    if len(candidates) > 16 or (budget <= 0 and not explicit):
        return {'status': 'ambiguous', 'candidates': [], 'too_many': True}
    verified = []
    for ident, (user, context) in sorted(candidates.items()):
        try:
            if context is not None:
                user = await _await(context.fetch_member(int(ident)), guard)
                if not guild:
                    fresh_actor = await _await(context.fetch_member(int(requester)), guard)
                    if not _human(fresh_actor, requester):
                        continue
        except PermissionError:
            raise
        except Exception:
            continue
        if (not _human(user, ident) or (not explicit and query.casefold() not in _names(user, bool(guild)))):
            continue
        if await _admit(bot, ident, 'dm:' + ident, guard):
            verified.append(_identity(user))
    _check(guard)
    if len(verified) == 1:
        return {'status': 'resolved', **verified[0], 'candidates': []}
    return {'status': 'ambiguous' if verified else 'not_found', 'candidates': verified}


@dataclass(frozen=True)
class AttachmentSelection:
    id: str
    path: pathlib.Path
    filename: str
    sha256: str
    size: int


def _list(value):
    if isinstance(value, str):
        try:
            value = json.loads(value)
        except ValueError:
            raise ValueError('messenger_invalid_sources') from None
    if not isinstance(value, (tuple, list)) or len(value) > 128:
        raise ValueError('messenger_invalid_sources')
    return [str(v) for v in value]


def _owner(row):
    return str(row.get('requester') or row.get('actor') or '')


def _sources(row, override=None):
    return _list(override if override is not None else row.get('source_ids', row.get('sources', [])))


def _filename(value):
    if (not isinstance(value, str) or not value or len(value) > 240
            or value in ('.', '..') or any(c in value for c in '/\\:')
            or any(unicodedata.category(c).startswith('C') for c in value)):
        raise ValueError('messenger_invalid_attachment_name')
    return value


def _safe_bytes(bot, path, size, digest):
    root = pathlib.Path(getattr(bot, 'attachment_dir', 'data/attachments')).absolute()
    path = pathlib.Path(path).absolute()
    if '..' in path.parts or not path.is_relative_to(root):
        raise PermissionError('messenger_attachment_path_denied')
    # Reject links/reparse points on every lexical component before resolving.
    for part in (root, *root.parents, path, *path.parents):
        st = part.lstat()
        if stat.S_ISLNK(st.st_mode) or getattr(st, 'st_file_attributes', 0) & 0x400:
            raise PermissionError('messenger_attachment_link_denied')
    if not path.resolve().is_relative_to(root.resolve()):
        raise PermissionError('messenger_attachment_path_denied')
    flags = os.O_RDONLY | getattr(os, 'O_BINARY', 0) | getattr(os, 'O_NOFOLLOW', 0)
    fd = os.open(path, flags)
    try:
        before = os.fstat(fd)
        if (not stat.S_ISREG(before.st_mode) or before.st_size != size
                or not 0 <= size <= 64 * 1024 * 1024):
            raise ValueError('messenger_attachment_size_mismatch')
        with os.fdopen(fd, 'rb', closefd=False) as handle:
            raw = handle.read(size + 1)
        after = os.fstat(fd)
        if ((before.st_size, before.st_mtime_ns, before.st_ino) != (after.st_size, after.st_mtime_ns, after.st_ino)
                or len(raw) != size or hashlib.sha256(raw).hexdigest() != digest):
            raise ValueError('messenger_attachment_integrity_mismatch')
        return raw
    finally:
        os.close(fd)


def select_attachments(bot, handoff, attachment_ids, *, source_ids=None, now=None):
    """Resolve saved upload IDs, never model-provided local filesystem paths."""
    ids = _list(attachment_ids)
    if len(ids) > 10 or len(set(ids)) != len(ids):
        raise ValueError('messenger_invalid_attachment_selection')
    if not ids:
        return []
    store = bot.store
    sources = _sources(handoff, source_ids)
    if not sources or store.tombstoned(sources):
        raise PermissionError('messenger_attachment_source_forgotten')
    now = time.time() if now is None else now
    selected = []
    for ident in ids:
        row = store.one('SELECT * FROM kei_attachments WHERE id=?', (ident,))
        if (not row or str(row['actor']) != _owner(handoff) or row['scope'] != handoff.get('scope')
                or str(row['message']) not in sources or store.tombstoned([str(row['message'])])):
            raise PermissionError('messenger_attachment_binding_denied')
        if not now - 86400 <= float(row['at']) <= now + 60:
            raise ValueError('messenger_attachment_expired')
        filename = _filename(row['filename'])
        size = int(row['bytes'])
        digest = str(row['sha256'])
        if not re.fullmatch(r'[0-9a-f]{64}', digest):
            raise ValueError('messenger_attachment_integrity_mismatch')
        _safe_bytes(bot, row['path'], size, digest)
        selected.append(AttachmentSelection(ident, pathlib.Path(row['path']), filename, digest, size))
    return selected


class DeliveryUncertain(RuntimeError):
    """The caller must durably stop retries, including for cancellation in send."""
    def __init__(self, message_id=None):
        super().__init__('messenger_delivery_uncertain')
        self.message_id = message_id


async def _core_authorize(authorize, check):
    outcome = authorize()
    if not inspect.isawaitable(outcome):
        raise TypeError('messenger_authorize_must_be_async')
    if await _await(outcome, check) is not True:
        raise PermissionError('messenger_delivery_denied')


async def _fresh_person(bot, ident, scope, check):
    try:
        if str(scope).startswith('guild:'):
            gid = str(scope).split(':')[1]
            guild = next((g for g in getattr(bot, 'guilds', ()) if str(g.id) == gid), None)
            if guild is None:
                raise PermissionError('messenger_unknown_source_guild')
            user = await _await(guild.fetch_member(int(ident)), check)
        else:
            user = await _await(bot.fetch_user(int(ident)), check)
    except PermissionError:
        raise
    except Exception:
        raise PermissionError('messenger_human_unavailable') from None
    if not _human(user, ident):
        raise PermissionError('messenger_human_unverified')
    return user


async def send_messenger(bot, row, payload, *, check, authorize):
    """Single Discord send; the existing outbox worker owns state and uncertainty.

    payload may be a flat core delivery mapping or {handoff: mapping, ...}.
    Core policy must check recipient mute/block/no-peer refusal, not proactive
    opt-in/quota. Explicit one-off authority is never inferred by this adapter.
    """
    if not callable(check) or not callable(authorize):
        raise TypeError('messenger_authority_callbacks_required')
    _check(check)
    nested = payload.get('handoff')
    handoff = nested if isinstance(nested, dict) else dict(payload)
    if isinstance(nested, str) and not handoff.get('requester_scope'):
        store = getattr(bot, 'store', None)
        parent = store.one('SELECT requester,scope,channel,kind FROM kei_handoffs69 WHERE id=?', (nested,)) if store else None
        if parent:
            if str(parent['requester']) != _owner(handoff):
                raise PermissionError('messenger_requester_mismatch')
            handoff.update(requester_scope=parent['scope'],requester_channel=parent['channel'])
    requester = _id(_owner(handoff))
    recipient = _id(handoff.get('recipient_id', handoff.get('recipient', '')))
    origin_scope = str(handoff.get('requester_scope') or handoff.get('origin_scope') or handoff.get('scope', ''))
    origin_channel = str(handoff.get('requester_channel') or handoff.get('origin_channel') or handoff.get('channel', ''))
    text = payload.get('content', row.get('content', ''))
    if not requester or not recipient or not isinstance(text, str) or len(text) > 2000:
        raise ValueError('messenger_invalid_payload')
    if not (origin_scope == 'dm:' + requester or re.fullmatch(r'guild:[0-9]+:[0-9]+', origin_scope)):
        raise PermissionError('messenger_invalid_source_scope')
    if not await _admit(bot, requester, origin_scope, check):
        raise PermissionError('messenger_requester_denied')
    await _fresh_person(bot, requester, origin_scope, check)
    person = await _fresh_person(bot, recipient, 'dm:' + recipient, check)
    if not await _admit(bot, recipient, 'dm:' + recipient, check):
        raise PermissionError('messenger_recipient_denied')
    await _core_authorize(authorize, check)
    key = str(row.get('channel', ''))
    if key in (recipient, 'dm:' + recipient):
        channel = await _await(person.create_dm(), check)
    elif key == origin_channel and recipient == requester:
        channel = await _await(bot.destination(key), check)
    else:
        raise PermissionError('messenger_destination_mismatch')
    raw = getattr(channel, 'raw', channel)
    guild = getattr(raw, 'guild', None)
    if guild:
        actual_scope = f'guild:{guild.id}:{raw.id}'
        if actual_scope != origin_scope or str(raw.id) != key or recipient != requester:
            raise PermissionError('messenger_destination_mismatch')
    else:
        if (str(getattr(getattr(raw, 'recipient', None), 'id', '')) != recipient
                or getattr(raw, 'recipients', None)):
            raise PermissionError('messenger_destination_mismatch')
    # Optional anchor contains identifiers only: never read raw message content.
    anchor = payload.get('anchor')
    reference = None
    if anchor is not None:
        if (not isinstance(anchor, dict) or str(anchor.get('channel')) != str(raw.id)
                or _id(anchor.get('actor', '')) != requester
                or not _id(anchor.get('message', '')) or recipient != requester):
            raise PermissionError('messenger_anchor_mismatch')
        store = getattr(bot, 'store', None)
        if store is not None and store.tombstoned([str(anchor['message'])]):
            raise PermissionError('messenger_anchor_forgotten')
        message = await _await(channel.fetch_message(int(anchor['message'])), check)
        if (str(message.id) != str(anchor['message']) or str(message.channel.id) != str(raw.id)
                or not _human(message.author, requester)):
            raise PermissionError('messenger_anchor_mismatch')
        reference = message.to_reference(fail_if_not_exists=False)
    ids = payload.get('attachment_ids', handoff.get('attachment_ids', []))
    source_ids = payload.get('source_ids', handoff.get('source_ids'))
    attachment_owner = _id(handoff.get('actor', requester))
    attachment_scope = origin_scope
    snapshots = handoff.get('sources', [])
    if isinstance(snapshots, str):
        try:
            snapshots = json.loads(snapshots)
        except ValueError:
            raise PermissionError('messenger_invalid_source_projection') from None
    actor_scopes = {s.get('scope') for s in snapshots if isinstance(s, dict) and str(s.get('user')) == attachment_owner}
    if actor_scopes:
        if len(actor_scopes) != 1:
            raise PermissionError('messenger_ambiguous_attachment_scope')
        attachment_scope = next(iter(actor_scopes))
    elif attachment_owner != requester:
        raise PermissionError('messenger_actor_source_required')
    attachment_context = dict(handoff, requester=attachment_owner, scope=attachment_scope)
    if attachment_owner != requester:
        if not await _admit(bot, attachment_owner, attachment_scope, check):
            raise PermissionError('messenger_reply_actor_denied')
        await _fresh_person(bot, attachment_owner, attachment_scope, check)
    selected = select_attachments(bot, attachment_context, ids, source_ids=source_ids)
    _check(check)
    streams, files = [], []
    try:
        total = 0
        for saved in selected:
            raw_bytes = _safe_bytes(bot, saved.path, saved.size, saved.sha256)
            total += len(raw_bytes)
            limit = int(getattr(guild, 'filesize_limit', 10 * 1024 * 1024))
            if saved.size > limit or total > 64 * 1024 * 1024:
                raise ValueError('messenger_attachment_upload_limit')
            stream = io.BytesIO(raw_bytes)
            streams.append(stream)
            files.append(discord.File(stream, filename=saved.filename))
        if not text and not files:
            raise ValueError('messenger_empty_message')
        extra = {'allowed_mentions': discord.AllowedMentions.none()}
        if files:
            extra['files'] = files
        if reference is not None:
            extra['reference'] = reference
        if payload.get('notification') is True:
            mode = payload.get('mode', handoff.get('mode', handoff.get('kind')))
            if reference is None or mode not in ('remind', 'report') or payload.get('ordinal', 0) != 0:
                raise PermissionError('messenger_notification_anchor_required')
            extra['mention_author'] = True
        # The wrapper must finish its final awaited gate BEFORE the no-await
        # revision/source fence; sending through wrapper.send would reopen it.
        await _core_authorize(authorize, check)
        if not await _admit(bot, requester, origin_scope, check):
            raise PermissionError('messenger_requester_denied')
        if not await _admit(bot, recipient, 'dm:' + recipient, check):
            raise PermissionError('messenger_recipient_denied')
        wrapper_check = getattr(channel, 'check', None)
        if callable(wrapper_check) and getattr(channel, 'raw', None) is not None:
            await _await(wrapper_check(), check)
            raw = channel.raw
        await _core_authorize(authorize, check)
        # Re-read indexed attachments/tombstones after all awaited work. Bytes
        # already copied into owned buffers, so no filesystem access during HTTP.
        if select_attachments(bot, attachment_context, ids, source_ids=source_ids) != selected:
            raise PermissionError('messenger_attachment_selection_changed')
        if anchor is not None and getattr(bot, 'store', None) is not None and bot.store.tombstoned([str(anchor['message'])]):
            raise PermissionError('messenger_anchor_forgotten')
        _check(check)
        try:
            sent = await raw.send(text, **extra)
        except (discord.Forbidden, discord.NotFound):
            raise
        except BaseException as exc:
            raise DeliveryUncertain() from exc
        ident = _id(getattr(sent, 'id', ''))
        if not ident:
            raise DeliveryUncertain()
        try:
            _check(check)
        except BaseException as exc:
            raise DeliveryUncertain(ident) from exc
        return ident
    finally:
        for uploaded in files:
            uploaded.close()
        for stream in streams:
            stream.close()


async def send_handoff(bot, handoff, outbox, data, rendered_text, attachment_paths=(), *, channel=None,
                       anchor=None, notification=False, guard, authorize):
    """Compatibility entry point: file selections must come from the upload index."""
    if channel is not None:
        raise ValueError('messenger_use_exact_outbox_destination')
    if any(not isinstance(item, AttachmentSelection) for item in attachment_paths):
        raise PermissionError('messenger_arbitrary_attachment_path_denied')
    payload = dict(data, handoff=handoff, content=rendered_text, anchor=anchor, notification=notification)
    if attachment_paths:
        payload['attachment_ids'] = [item.id for item in attachment_paths]
    return await send_messenger(bot, outbox, payload, check=guard, authorize=authorize)
