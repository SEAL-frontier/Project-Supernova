"""Offline regression coverage for persisted, request-scoped reply guards."""
import asyncio
from contextlib import asynccontextmanager
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

import pytest

from minecraft_agent.v3.application import Kei
from minecraft_agent.v3.conversation import Conversation
from minecraft_agent.v3.store import Store


@pytest.fixture
def harness(tmp_path):
    store = Store(str(tmp_path / 'synthetic.sqlite'))
    conversation = Conversation(store, {})
    channel = SimpleNamespace(id=100)
    key = ('guild:10:100', '200')

    @asynccontextmanager
    async def typing(*args):
        yield

    bot = SimpleNamespace(
        store=store,
        engine=SimpleNamespace(conversation=conversation),
        buffers={key: {'channel': channel, 'user': '200',
                       'messages': [('301', 'hello'), ('302', 'there')],
                       'first': 0, 'last': 0}},
        conversation_typing=typing,
        end_typing=Mock(),
    )
    conversation.capture = AsyncMock()
    yield bot, key, conversation
    store.db.close()


def run_failure(harness, *, status=None, receipt=False, kind='reply',
                request='301', channel='100', actor='200',
                scope='guild:10:100', provenance=True):
    bot, key, conversation = harness
    if status is not None:
        action = conversation.queue(channel, request, kind, 'synthetic answer', scope, actor)
        bot.store.execute('UPDATE kei_social_actions SET status=? WHERE id=?', (status, action))
        if not provenance:
            bot.store.execute('DELETE FROM kei_delivery_targets WHERE action=?', (action,))
        if receipt:
            bot.store.execute('INSERT INTO kei_social_sent VALUES (?,?)', (action, '900'))
    before = bot.store.rows('SELECT * FROM kei_social_actions')
    bot.engine.converse = AsyncMock(side_effect=RuntimeError('synthetic postprocessing error'))
    asyncio.run(Kei.flush(bot, key))
    after = bot.store.rows('SELECT * FROM kei_social_actions')
    return bot, before, after


@pytest.mark.parametrize('status,receipt', [
    ('pending', False), ('sending', False), ('uncertain', False),
    ('sent', True), ('failed', True),
])
@pytest.mark.parametrize('kind', ['reply', 'short_reply'])
def test_persisted_reply_prevents_duplicate_failure(harness, status, receipt, kind):
    bot, before, after = run_failure(harness, status=status, receipt=receipt, kind=kind)
    assert after == before  # Never fabricate a sent state or delivery receipt.
    assert bot.store.rows('SELECT * FROM kei_social_sent') == (
        [{'action': before[0]['id'], 'message': '900'}] if receipt else [])
    assert bot.end_typing.call_count == (0 if status in ('pending', 'sending') else 1)


@pytest.mark.parametrize('change', [
    {}, {'status': 'failed'}, {'status': 'sent'},
    {'status': 'pending', 'request': '999'},
    {'status': 'pending', 'channel': '101'},
    {'status': 'pending', 'actor': '201'},
    {'status': 'pending', 'scope': 'guild:11:100'},
    {'status': 'pending', 'kind': 'react'},
    {'status': 'pending', 'provenance': False},
])
def test_true_no_output_or_unrelated_reply_preserves_failure_notice(harness, change):
    bot, before, after = run_failure(harness, **change)
    assert len(after) == len(before) + 1
    failure = next(row for row in after if row['id'] not in {r['id'] for r in before})
    assert failure['message'] == '302'
    assert failure['channel'] == '100'
    assert failure['kind'] == 'reply'
    assert failure['status'] == 'pending'
    assert 'lỗi xử lý' in failure['content']
    target = bot.store.one('SELECT * FROM kei_delivery_targets WHERE action=?', (failure['id'],))
    assert (target['scope'], target['actor']) == ('guild:10:100', '200')
    assert bot.end_typing.call_count == 1
