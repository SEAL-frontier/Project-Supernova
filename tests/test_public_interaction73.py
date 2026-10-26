"""Synthetic, offline interaction and cost boundaries for the public engine."""
import asyncio
import copy
import json
import time

import pytest

from minecraft_agent.v3.config import DEFAULTS
from minecraft_agent.v3.engine import Engine
from minecraft_agent.v3.store import Store


class Model:
    def __init__(self):
        self.calls = []
        self.revoke = None
        self.invalid = False

    async def chat(self, history, tools=None, **kwargs):
        self.calls.append(copy.deepcopy(history))
        if self.revoke:
            self.revoke()
        value = {'intent': 'chat', 'response_action': 'silence', 'reply': ''}
        return {'tool_calls': [{'function': {'name': 'social_turn', 'arguments': 'invalid' if self.invalid else json.dumps(value)}}]}


@pytest.fixture
def world(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    cfg = copy.deepcopy(DEFAULTS)
    cfg.update(owner_id='200', persona='Synthetic character.', timezone='UTC',
               secrets_file=str(tmp_path / 'secrets.json'), servers=[], assignments={},
               provider_key='', discord_token='')
    db = Store(':memory:')
    model = Model()
    engine = Engine(cfg, db, model)
    engine.prompt = lambda *args: [{'role': 'system', 'content': 'Synthetic prompt.'}]
    yield engine, db, model
    db.db.close()


def source(world, ident, text='ok', actor='200', addressed=1, captured=True):
    engine, db, _ = world
    scope = 'guild:400:500'
    db.add_message(scope, actor, 'user', text, ident)
    db.execute('INSERT OR REPLACE INTO kei_event_meta VALUES (?,?,?,?,?,?,?,?,?)',
               (ident, 'discord', engine.identity.person_for_user(actor), actor, '', scope, '500', addressed, time.time()))
    if captured:
        rows = db.rows("SELECT * FROM kei_messages WHERE scope=? AND role='user' ORDER BY at", (scope,))
        data = {'status': 'ok', 'guild': '400', 'channel': '500', 'request_ids': [ident],
                'messages': [dict(id=r['id'], author_id=r['user'], content=r['content'], at=r['at'], bot=False, reply_to=None) for r in rows]}
        db.execute('INSERT OR REPLACE INTO kei_nearby VALUES (?,?,?,?,?,?)',
                   (ident, scope, actor, '500', json.dumps(data), time.time()))
    return scope


def test_direct_short_name_does_not_buy_classifier(world):
    engine, db, model = world
    scope = source(world, '10', 'Kei')
    async def forbidden(*args, **kwargs):
        pytest.fail('A strong direct name must use the existing main pass')
    engine.decisions.evaluate = forbidden
    asyncio.run(engine.converse('200', scope, '500', 'Kei', ['10']))
    assert len(model.calls) == 1
    assert 'selected_bounded_observations' in str(model.calls[0])


def test_first_ack_and_first_burst_reach_main_then_skip(world):
    engine, db, model = world
    async def forbidden(*args, **kwargs):
        pytest.fail('Direct acknowledgments and first observed burst use main')
    engine.decisions.evaluate = forbidden
    for ident in ['10', '11', '12']:
        scope = source(world, ident)
        asyncio.run(engine.converse('200', scope, '500', 'ok', [ident]))
    assert len(model.calls) == 2
    assert not db.rows('SELECT * FROM kei_social_actions')


@pytest.mark.parametrize('change', ['edit', 'forget', 'service'])
def test_inflight_revocation_blocks_effect_and_accept(world, change):
    engine, db, model = world
    scope = source(world, '10', 'Please explain the example')
    allowed = [True]
    async def authorize(*args):
        return allowed[0]
    engine.service_authorize = authorize
    def revoke():
        if change == 'edit':
            engine.conversation.invalidate_interactions('10')
        elif change == 'forget':
            db.execute('UPDATE kei_messages SET forgotten=1 WHERE id=?', ('10',))
        else:
            allowed[0] = False
    model.revoke = revoke
    result = asyncio.run(engine.converse('200', scope, '500', 'Please explain the example', ['10']))
    assert result['action'] == 'silence'
    assert not db.rows('SELECT * FROM kei_social_actions')
    assert not getattr(engine.conversation, '_interaction_accepted', {})


def test_missing_request_is_unavailable_and_retained_scope_is_bounded(world):
    engine, db, model = world
    scope = source(world, '10', 'Kei', captured=False)
    db.add_message('dm:200', '200', 'user', 'PRIVATE OTHER SCOPE', '99')
    context = engine.conversation.context(scope, '10')
    assert context['coverage']['complete'] is False
    assert 'PRIVATE OTHER SCOPE' not in str(context)
    assert not engine.conversation.context(scope, 'missing')['messages']


def test_protected_and_unknown_reply_edges_never_skip(world):
    engine, db, model = world
    for ident in ['10', '11']:
        scope = source(world, ident)
        obs = engine.conversation.interaction_observation(scope, ident, '200')
        assert engine.conversation.accept_interaction(obs)
    source(world, '12')
    assert engine.conversation.interaction_observation(scope, '12', '200', protected=True)['action'] == 'consider'
    assert engine.conversation.interaction_observation(scope, '12', '200', awaited_answer=True)['action'] == 'consider'
    source(world, '13', captured=False)
    assert engine.conversation.interaction_observation(scope, '13', '200')['action'] == 'consider'


def test_voice_varies_closer_without_changing_literal():
    from minecraft_agent.v3.voice import render_reply
    recent = [{'role': 'assistant', 'content': 'Previous prose :))'}]
    assert render_reply('hello', 'Current prose :))', recent) == 'Current prose'
    assert render_reply('say exactly :))', 'Current prose :))', recent) == 'Current prose :))'


def test_numeric_cost_telemetry_rejects_prose_and_boolean(world):
    from minecraft_agent.v3.telemetry import Telemetry
    _, db, _ = world
    metrics = Telemetry(db, {'telemetry': {'enabled': True}})
    metrics.record('conversation', decision_calls=1, decision_ms=2.5, repeat_skips=0)
    row = db.one('SELECT data FROM kei_telemetry_events')
    assert json.loads(row['data']) == {'decision_calls': 1, 'decision_ms': 2.5, 'repeat_skips': 0}
    for invalid in ('PRIVATE', True, float('nan')):
        with pytest.raises(ValueError):
            metrics.record('conversation', decision_calls=invalid)


def test_invalid_parse_never_accepts_burst(world):
    engine, db, model = world
    source(world, '10')
    scope = source(world, '11')
    model.invalid = True
    with pytest.raises(ValueError, match='schema invalid'):
        asyncio.run(engine.converse('200', scope, '500', 'ok', ['11']))
    assert not getattr(engine.conversation, '_interaction_accepted', {})


@pytest.mark.parametrize('text', ['36', 'no', 'help', 'stop', 'cancel', 'confirm', '2+2'])
def test_short_meaningful_current_dialogue_uses_main(world, text):
    engine, db, model = world
    scope = source(world, '10', text, addressed=2)
    async def forbidden(*args, **kwargs):
        pytest.fail('A short meaningful dialogue turn is not optional noise classification')
    engine.decisions.evaluate = forbidden
    asyncio.run(engine.converse('200', scope, '500', text, ['10']))
    assert model.calls


def test_canonical_mention_capture_keeps_reply_edge(world):
    from datetime import datetime, timezone
    from types import SimpleNamespace as NS
    engine, db, model = world
    scope = source(world, '10', 'ok')
    channel = NS(id=500, _state=NS(user=NS(id=999)))
    message = NS(id=10, channel=channel, content='<@999> ok',
                 author=NS(id=200, name='synthetic', bot=False),
                 created_at=datetime.now(timezone.utc), reference=NS(message_id=9))
    row = engine.conversation._capture_record(message, scope)
    assert row['content'] == 'ok' and row['reply_to'] == '9'
    message.content = '<@999> changed'
    assert engine.conversation._capture_record(message, scope)['content'] != 'ok'


def test_actual_cost_counters_are_numeric_without_dialogue(world):
    from minecraft_agent.v3.telemetry import Telemetry
    engine, db, model = world
    Telemetry(db, {'telemetry': {'enabled': True}})
    scope = source(world, '10', 'Kei')
    asyncio.run(engine.converse('200', scope, '500', 'Kei', ['10']))
    data = json.loads(db.one('SELECT data FROM kei_telemetry_events')['data'])
    assert data['route_calls'] == 1 and data['decision_calls'] == 0 and data['repeat_skips'] == 0
    assert all(type(v) in (int, float) for v in data.values())

def test_failed_final_action_does_not_accept_ack_burst(world):
    engine, db, model = world
    scope = source(world, '10')
    asyncio.run(engine.converse('200', scope, '500', 'ok', ['10']))
    source(world, '11')
    good_chat = model.chat
    async def invalid_final(history, tools=None, **kwargs):
        result = await good_chat(history, tools, **kwargs)
        value = json.loads(result['tool_calls'][0]['function']['arguments'])
        value['memory_action'] = 'invalid'
        result['tool_calls'][0]['function']['arguments'] = json.dumps(value)
        return result
    model.chat = invalid_final
    with pytest.raises(ValueError, match='Invalid memory action'):
        asyncio.run(engine.converse('200', scope, '500', 'ok', ['11']))
    assert not next(iter(engine.conversation._interaction_accepted.values()))['burst']
    source(world, '12')
    assert engine.conversation.interaction_observation(scope, '12', '200')['action'] == 'consider'

