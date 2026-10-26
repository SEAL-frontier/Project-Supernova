"""Offline public chat integration: real SQLite, calculator and PNG renderer."""
import asyncio
import copy
import json
from types import SimpleNamespace

import pytest
from PIL import Image

from minecraft_agent.v3.config import DEFAULTS
from minecraft_agent.v3.engine import Engine
from minecraft_agent.v3.store import Store


class Provider:
    def __init__(self, decisions):
        self.decisions = iter(decisions)
        self.calls = []

    async def chat(self, history, tools=None, **kwargs):
        self.calls.append((copy.deepcopy(history), copy.deepcopy(tools)))
        return {'tool_calls': [{'function': {'name': 'social_turn', 'arguments': json.dumps(next(self.decisions))}}]}


class Channel:
    id = 100
    last_message_id = None

    def __init__(self):
        self.sent = []

    async def send(self, content, **kwargs):
        image = kwargs.get('file')
        if image:
            with Image.open(image.fp) as decoded:
                decoded.load()
                assert decoded.format == 'PNG'
        self.sent.append(('image' if image else 'text', content))
        ident = 900 + len(self.sent)
        return SimpleNamespace(id=ident, to_reference=lambda **kw: ident)


def decision(**extra):
    return {'intent': 'chat', 'response_action': 'reply', 'reply': 'waiting', **extra}


@pytest.fixture
def engine(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    db = Store(str(tmp_path / 'synthetic.sqlite'))
    cfg = copy.deepcopy(DEFAULTS)
    cfg.update(owner_id='200', persona='Synthetic test character.', provider_key='', discord_token='', timezone='UTC')
    model = Provider([
        decision(calculations=[{'id': 'sum', 'expression': 'sqrt(81)+2**3'}]),
        decision(reply='17', reply_parts=[{'type': 'text', 'text': 'Result: 17'},
            {'type': 'formula', 'formula': r'\frac{17}{1}=17'}, {'type': 'text', 'text': 'Done.'}]),
    ])
    bot = Engine(cfg, db, model)
    # Only the persona/history prompt is isolated; routing and postprocessing remain real.
    bot.prompt = lambda *args: [{'role': 'system', 'content': 'Synthetic public chat.'}]
    yield bot, db, model
    db.db.close()


def test_math_converse_uses_receipts_and_delivers_ordered_real_png(engine):
    bot, db, model = engine
    db.add_message('dm:200', '200', 'user', 'calculate sqrt(81)+2**3', '301')
    result = asyncio.run(bot.converse('200', 'dm:200', '100', 'calculate sqrt(81)+2**3', ['301']))
    assert result['intent'] == 'chat'
    assert len(model.calls) == 2
    schema = model.calls[0][1][0]['function']['parameters']['properties']
    assert 'calculations' in schema and 'reply_parts' in schema
    assert any('LOCAL CALCULATOR RECEIPTS' in str(m['content']) and '17' in str(m['content']) for m in model.calls[1][0])
    assert db.rows('SELECT * FROM kei_tasks') == []
    row = db.one('SELECT * FROM kei_social_actions')
    channel = Channel()
    assert asyncio.run(bot.conversation.deliver(channel, row)) == '901'
    assert channel.sent == [('text', 'Result: 17'), ('image', None), ('text', 'Done.')]
    assert bot.conversation.sent_ids(row['id']) == ['901', '902', '903']


@pytest.mark.parametrize('visibility', ['public', 'private'])
@pytest.mark.parametrize('mixed', [True, False], ids=['mixed', 'formula-only'])
def test_minecraft_formula_parts_preserve_readable_content_without_png(engine, visibility, mixed):
    bot, db, model = engine
    parts = [{'type': 'formula', 'formula': r'\frac{17}{1}=17'}]
    expected = '(17)/(1)=17'
    if mixed:
        parts = [{'type': 'text', 'text': 'Result: 17'}, *parts,
                 {'type': 'text', 'text': 'Done.'}]
        expected = 'Result: 17\n' + expected + '\nDone.'
    model.decisions = iter([decision(reply='', reply_parts=parts)])
    actor = 'mc:synthetic:player'
    scope = 'mc:synthetic' if visibility == 'public' else 'mc-private:synthetic:player'
    channel = 'mc:synthetic:player:' + visibility
    result = asyncio.run(bot.converse(actor, scope, channel, 'formula please', ['301']))
    assert result['intent'] == 'chat'
    row = db.one('SELECT * FROM kei_social_actions')
    # The Minecraft application sends exactly row.content, not Discord delivery parts.
    assert row['channel'] == channel
    assert row['content'] == expected
    queued = db.rows('SELECT parts FROM kei_conversation_parts')
    assert all(part['type'] == 'text' for item in queued for part in json.loads(item['parts']))
    assert not list(bot.conversation.math_render_root.glob('**/*.png'))
    assert db.rows('SELECT * FROM kei_tasks') == []


def test_partial_delivery_never_replays_confirmed_bubbles(engine):
    bot, db, _ = engine
    action = bot.conversation.queue_parts('100', '301', [
        {'type': 'text', 'text': 'First'}, {'type': 'text', 'text': 'Second'}], 'dm:200', '200')
    channel = Channel()
    original = channel.send

    async def fail_second(content, **kwargs):
        if channel.sent:
            raise RuntimeError('synthetic ambiguous send')
        return await original(content, **kwargs)

    channel.send = fail_second
    row = db.one('SELECT * FROM kei_social_actions WHERE id=?', (action,))
    with pytest.raises(RuntimeError):
        asyncio.run(bot.conversation.deliver(channel, row))
    assert bot.conversation.sent_ids(action) == ['901']
    assert db.one('SELECT status FROM kei_social_actions WHERE id=?', (action,))['status'] == 'uncertain'
    with pytest.raises(ValueError, match='already_started'):
        asyncio.run(bot.conversation.deliver(channel, row))
    assert channel.sent == [('text', 'First')]


def test_search_card_does_not_swallow_formula_parts(engine):
    bot, db, _ = engine
    from minecraft_agent.v3.chat_helpers import render_parts
    parts = render_parts([{'type': 'text', 'text': 'Result'}, {'type': 'formula', 'formula': 'x=17'},
                          {'type': 'text', 'text': 'Done'}], bot.conversation.math_render_root)
    action = bot.conversation.queue_parts('100', '301', parts, 'dm:200', '200')
    db.execute('INSERT INTO kei_search_cards VALUES (?,?,?,?,?,?,0)', ('100', '301', '800', 'Sources', '[]', __import__('time').time()))
    channel = Channel()

    async def fetch(ident):
        async def edit(**kwargs):
            channel.sent.append(('edit', kwargs['content']))
        return SimpleNamespace(id=ident, author=SimpleNamespace(id=999), edit=edit)

    channel._state = SimpleNamespace(user=SimpleNamespace(id=999))
    channel.fetch_message = fetch
    row = db.one('SELECT * FROM kei_social_actions WHERE id=?', (action,))
    asyncio.run(bot.conversation.deliver(channel, row))
    assert any(kind == 'image' for kind, _ in channel.sent)


def test_formula_failure_is_honest_text_and_not_a_task(engine):
    bot, db, model = engine
    model.decisions = iter([decision(reply_parts=[{'type': 'formula', 'formula': r'\input{secret}'}])])
    db.add_message('dm:200', '200', 'user', 'formula please', '301')
    asyncio.run(bot.converse('200', 'dm:200', '100', 'formula please', ['301']))
    row = db.one('SELECT * FROM kei_social_actions')
    assert 'chưa có ảnh' in row['content']
    channel = Channel()
    asyncio.run(bot.conversation.deliver(channel, row))
    assert all(kind == 'text' for kind, _ in channel.sent)
    assert not db.rows('SELECT * FROM kei_tasks')


def test_repeated_calculations_do_not_create_duplicate_receipts(engine):
    bot, db, model = engine
    model.decisions = iter([decision(calculations=[{'id': 'sum', 'expression': '1/0'}]),
                            decision(reply='Cannot verify.', calculations=[{'id': 'sum', 'expression': '1/0'}])])
    db.add_message('dm:200', '200', 'user', 'calculate 1/0', '301')
    asyncio.run(bot.converse('200', 'dm:200', '100', 'calculate 1/0', ['301']))
    assert len(model.calls) == 2
    receipts = [m for m in model.calls[1][0] if 'LOCAL CALCULATOR RECEIPTS' in str(m['content'])]
    assert len(receipts) == 1 and '"verified": false' in receipts[0]['content']


def test_renderer_paths_are_confined_and_decoded(engine, tmp_path):
    bot, db, _ = engine
    outside = tmp_path / 'outside.png'
    Image.new('RGB', (8, 8)).save(outside)
    with pytest.raises(ValueError, match='invalid_conversation_image'):
        bot.conversation.queue_parts('100', '301', [{'type': 'image', 'path': str(outside)}], 'dm:200', '200')
    assert db.rows('SELECT * FROM kei_social_actions') == []
