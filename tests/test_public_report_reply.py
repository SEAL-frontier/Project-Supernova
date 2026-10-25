"""Exercise the real outbox sender and discord.py HTTP serialization offline."""
import asyncio
from types import SimpleNamespace

import discord
import pytest

from minecraft_agent.v3.application import Kei
from minecraft_agent.v3.conversation import Conversation, CURRENT_TASK
from minecraft_agent.v3.store import Store


@pytest.mark.parametrize('revocation', [None, 'cancel', 'service'])
def test_actual_outbox_serializes_exact_request_reply_without_content_mentions(monkeypatch, revocation):
    payloads = []
    context = {}
    class HTTP:
        async def send_message(self, channel, *, params):
            payloads.append(params.payload)
            return {'id': '900'}
    class Channel(discord.abc.Messageable):
        id = 100
        def __init__(self):
            self._state = SimpleNamespace(http=HTTP(), allowed_mentions=discord.AllowedMentions.none(),
                create_message=lambda **kw: SimpleNamespace(id=900))
        async def _get_channel(self):
            return self
        async def fetch_message(self, ident):
            if revocation == 'cancel':
                context['db'].update_task(context['task'], status='cancelled')
            context['revoked'] = True
            return SimpleNamespace(id=ident, channel=self, created_at=__import__('datetime').datetime.now(__import__('datetime').timezone.utc), author=SimpleNamespace(id=200, bot=False),
                to_reference=lambda **kw: discord.MessageReference(message_id=ident, channel_id=100))
    async def run():
        db = Store(':memory:')
        conv = Conversation(db, {})
        task = db.create_task('sandbox', 'dm:200', '100', '200', 'Inspect', 'observe', [])
        context.update(db=db, task=task, revoked=False)
        conv.task_origin(task, 'dm:200', '200', '100', '301')
        token = CURRENT_TASK.set(task)
        try:
            db.queue('100', 'Saved summary <@200> <@&600> @everyone')
        finally:
            CURRENT_TASK.reset(token)
        channel = Channel()
        async def destination(*args):
            return channel
        async def ready():
            pass
        bot = SimpleNamespace(store=db, engine=SimpleNamespace(conversation=conv), destination=destination,
            mark_exchange=lambda *a: None, wait_until_ready=ready, is_closed=iter((False, True)).__next__)
        async def authority(*args):
            return not (revocation == 'service' and context['revoked'])
        bot.engine.service_authorize = authority
        monkeypatch.setattr('minecraft_agent.v3.application.asyncio.sleep', ready_sleep)
        await Kei.outbox_loop(bot)
        assert db.one('SELECT status FROM kei_outbox')['status'] == ('failed' if revocation else 'sent')
        db.db.close()
    async def ready_sleep(*args):
        pass
    asyncio.run(run())
    if revocation:
        assert not payloads
    else:
        assert payloads[0]['message_reference']['message_id'] == 301
        assert payloads[0]['allowed_mentions'] == {'parse': [], 'replied_user': True}
