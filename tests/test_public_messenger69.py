"""Public messenger: actual Engine/router/outbox with synthetic sources only."""
import asyncio
import copy
import json
import time
from types import SimpleNamespace, MethodType
from unittest.mock import AsyncMock

import pytest

from minecraft_agent.v3.config import DEFAULTS
from minecraft_agent.v3.engine import Engine, chat_router
from minecraft_agent.v3.store import Store


class Provider:
    def __init__(self, decisions):
        self.decisions = iter(decisions)
        self.calls = []

    async def chat(self, history, tools=None, **kwargs):
        self.calls.append((copy.deepcopy(history), copy.deepcopy(tools)))
        if tools[0]['function']['name'] == 'compose_handoff':
            op = self.last['messenger_actions'][0]
            return {'tool_calls': [{'function': {'name': 'compose_handoff', 'arguments': json.dumps({'authorized': True, 'text': op.get('text', '')})}}]}
        self.last = next(self.decisions)
        return {'tool_calls': [{'function': {'name': 'social_turn', 'arguments': json.dumps(self.last)}}]}


def turn(**extra):
    return {'intent': 'chat', 'response_action': 'silence', 'reply': '', **extra}


@pytest.fixture
def engine(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    cfg = copy.deepcopy(DEFAULTS)
    cfg.update(owner_id='1', persona='Synthetic test character.', provider_key='', discord_token='', timezone='UTC')
    cfg['decisions'] = {'provider': 'disabled'}
    db = Store(str(tmp_path / 'synthetic.sqlite'))
    model = Provider([])
    e = Engine(cfg, db, model)
    e.prompt = lambda *a: [{'role': 'system', 'content': 'Synthetic public chat.'}]
    e.launch = lambda *a: pytest.fail('Human message must not launch work')
    e.messenger_resolve = AsyncMock(return_value={'id': '2', 'human': True, 'verified': True})
    yield e, db, model
    db.db.close()


def source(e, text, actor='1', scope='dm:1', ident='100', channel='10'):
    e.identity.resolve('discord', actor)
    e.db.add_message(scope, actor, 'user', text, ident)
    e.db.execute('INSERT OR REPLACE INTO kei_event_meta VALUES (?,?,?,?,?,?,?,?,?)',
                 (ident, 'discord', e.identity.person_for_user(actor), actor, '', scope, channel, 1, time.time()))
    return ident


def test_router_exposes_messenger_proposals():
    props = chat_router()['function']['parameters']['properties']
    assert 'messenger_actions' in props
    assert props['messenger_actions']['maxItems'] == 4


def test_actual_chat_queues_one_human_dm_without_worker_or_receipt(engine):
    e, db, model = engine
    text = 'Ask Alice: Are you playing tonight?'
    source(e, text)
    model.decisions = iter([turn(messenger_actions=[{'action': 'ask', 'recipient': 'Alice', 'text': 'Are you playing tonight?'}])])
    asyncio.run(e.converse('1', 'dm:1', '10', text, ['100']))
    rows = db.rows('SELECT * FROM kei_outbox')
    assert len(rows) == 1 and rows[0]['channel'] == 'dm:2'
    assert rows[0]['content'] == 'Are you playing tonight?'
    assert not db.rows('SELECT * FROM kei_tasks')
    assert not db.rows('SELECT * FROM kei_social_actions')
    assert len(model.calls) == 2
    assert 'HUMAN MESSAGE HANDOFF' in model.calls[0][0][0]['content']


def test_parser_rejects_unknown_action_fields_before_effects(engine):
    e, db, model = engine
    bad = turn(messenger_actions=[{'action': 'send', 'channel': '999'}])
    model.decisions = iter([bad, bad])
    with pytest.raises(ValueError, match='schema invalid'):
        asyncio.run(e.route_turn([{'role': 'system', 'content': 'synthetic'}]))
    assert not db.rows('SELECT * FROM kei_outbox')


def test_pending_acceptance_cannot_emit_unconfirmed_sent_claim(engine):
    e, db, model = engine
    text = 'Send to Alice: Selected message.'
    source(e, text)
    model.decisions = iter([turn(response_action='reply', reply='Sent and delivered.', messenger_actions=[{'action': 'send', 'recipient': 'Alice', 'text': 'Selected message.'}])])
    asyncio.run(e.converse('1', 'dm:1', '10', text, ['100']))
    assert db.one('SELECT * FROM kei_outbox')['status'] == 'pending'
    assert not db.rows('SELECT * FROM kei_social_actions')


def test_own_selected_conversation_moves_to_dm_and_other_scope_stays_denied(engine):
    e, db, model = engine
    scope = 'guild:5:10'
    source(e, 'Chosen explanation.', scope=scope, ident='90')
    source(e, 'Private neighboring material.', scope='dm:1', ident='91')
    text = 'Send the selected explanation to my DM.'
    source(e, text, scope=scope)
    db.execute('INSERT INTO kei_messenger_selections69 VALUES (?,?,?,?)', ('100', '1', scope, '90'))
    model.decisions = iter([turn(messenger_actions=[{'action': 'send', 'delivery': 'dm', 'text': 'Chosen explanation.', 'source_ids': ['90']}])])
    asyncio.run(e.converse('1', scope, '10', text, ['100']))
    row = db.one('SELECT * FROM kei_outbox')
    assert row['channel'] == 'dm:1' and row['content'] == 'Chosen explanation.'
    assert not e.messenger_source_allowed('1', scope, db.one('SELECT * FROM kei_messages WHERE id=?', ('91',)))
    source(e, 'Send the other selection to my DM.', scope=scope, ident='101')
    result = asyncio.run(e.messenger.apply('1', scope, '10', ['101'], [{'action': 'send', 'delivery': 'dm', 'source_ids': ['91'], 'text': 'Private neighboring material.'}]))
    assert not result['ok'] and result['needs_clarification'][0]['reason'] == 'selected_source_denied'
    assert len(db.rows('SELECT * FROM kei_outbox')) == 1


def test_memory_forget_purges_handoff_and_outbox_body(engine):
    e, db, _ = engine
    source(e, 'Send to Alice: Selected message.')
    result = asyncio.run(e.messenger.apply('1', 'dm:1', '10', ['100'], [{'action': 'send', 'recipient': 'Alice', 'text': 'Selected message.'}]))
    assert result['ok']
    e.memory.forget('1', 'dm:1', ['100'])
    handoff = db.one('SELECT * FROM kei_handoffs69')
    row = db.one('SELECT * FROM kei_outbox')
    assert handoff['body'] == '' and row['content'] == ''
    assert row['status'] == 'cancelled' and not e.messenger.delivery_current(row['id'])


def test_muted_recipient_denies_one_off_without_requiring_proactive_opt_in(engine):
    e, db, _ = engine
    source(e, 'Send to Alice: Selected message.')
    person = e.identity.person_for_user('2')
    e.memory.set_preference(person, muted=1)
    result = asyncio.run(e.messenger.apply('1', 'dm:1', '10', ['100'], [{'action': 'send', 'recipient': 'Alice', 'text': 'Selected message.'}]))
    assert not result['ok'] and not db.rows('SELECT * FROM kei_outbox')


def test_existing_terminal_result_routes_to_own_dm_without_rerunning(engine):
    e, db, model = engine
    task = db.create_task('synthetic', 'guild:5:10', '10', '1', 'Inspect', 'observe', [])
    db.update_task(task, status='succeeded', result='Actual saved result.')
    text = 'Send the completed job result to my DM.'
    source(e, text)
    model.decisions = iter([turn(messenger_actions=[{'action': 'send', 'delivery': 'dm', 'when': 'task_complete', 'task_id': task}])])
    asyncio.run(e.converse('1', 'dm:1', '10', text, ['100']))
    actual = db.one('SELECT * FROM kei_tasks WHERE id=?', (task,))
    e.deliver_task_result(actual, actual['result'])
    rows = db.rows('SELECT * FROM kei_outbox')
    assert len(rows) == 1 and rows[0]['channel'] == 'dm:1'
    assert rows[0]['content'] == 'Actual saved result.'
    assert actual['status'] == 'succeeded'


def test_next_contact_is_only_released_by_real_admitted_turn(engine):
    e, db, model = engine
    source(e, 'Ask Alice next time: Are you playing tonight?')
    result = asyncio.run(e.messenger.apply('1', 'dm:1', '10', ['100'], [{'action': 'ask', 'recipient': 'Alice', 'when': 'next_contact', 'text': 'Are you playing tonight?'}]))
    assert result['ok'] and not db.rows('SELECT * FROM kei_outbox')
    source(e, 'Hello Kei', actor='2', scope='dm:2', channel='20', ident='101')
    model.decisions = iter([turn()])
    asyncio.run(e.converse('2', 'dm:2', '20', 'Hello Kei', ['101']))
    assert db.one('SELECT * FROM kei_outbox')['channel'] == 'dm:2'


def test_bound_reply_returns_only_selected_answer_to_requester_dm(engine):
    e, db, model = engine
    source(e, 'Ask Alice: Are you playing tonight?', scope='guild:5:10')
    result = asyncio.run(e.messenger.apply('1', 'guild:5:10', '10', ['100'], [{'action': 'ask', 'recipient': 'Alice', 'text': 'Are you playing tonight?', 'return_to': 'source'}]))
    outgoing = db.one('SELECT * FROM kei_outbox')
    assert e.messenger.sent(outgoing['id'], '800')
    source(e, 'Tell them: Yes at eight. Private detail stays here.', actor='2', scope='dm:2', channel='20', ident='101')
    model.decisions = iter([turn(messenger_actions=[{'action': 'reply', 'reply_to': '800', 'text': 'Yes at eight.'}])])
    asyncio.run(e.converse('2', 'dm:2', '20', 'Tell them: Yes at eight. Private detail stays here.', ['101']))
    row = db.one("SELECT * FROM kei_outbox WHERE status='pending'")
    assert row['channel'] == 'dm:1' and row['content'] == 'Yes at eight.'
    assert 'BOUND HUMAN HANDOFF CONTEXT' in model.calls[0][0][0]['content']
    assert all('Private detail' not in r['content'] for r in db.rows('SELECT * FROM kei_outbox'))


class DM:
    id = 20
    guild = None
    recipients = None
    def __init__(self, actor=2):
        self.recipient = SimpleNamespace(id=actor)
        self.sent = []
    async def send(self, content, **kwargs):
        assert kwargs['allowed_mentions'].to_dict()['parse'] == []
        self.sent.append(content)
        return SimpleNamespace(id=9001)


def sender(e, channel):
    from minecraft_agent.v3.application import Kei
    user = SimpleNamespace(id=channel.recipient.id, bot=False, system=False, create_dm=AsyncMock(return_value=channel))
    async def fetch(ident):
        if ident == user.id:
            return user
        return SimpleNamespace(id=ident, bot=False, system=False)
    b = SimpleNamespace(store=e.db, engine=e, guilds=[], fetch_user=fetch, wait_until_ready=AsyncMock())
    checks = iter((False, True))
    b.is_closed = lambda: next(checks)
    return b


def test_actual_outbox_loop_serializes_dm_and_exact_receipt(engine):
    import discord
    from minecraft_agent.v3.application import Kei
    e, db, _ = engine
    source(e, 'Send to Alice: Selected message.')
    asyncio.run(e.messenger.apply('1', 'dm:1', '10', ['100'], [{'action': 'send', 'recipient': 'Alice', 'text': 'Selected message.'}]))
    payloads = []
    class HTTP:
        async def send_message(self, channel, *, params):
            payloads.append(params.payload)
            return {'id': '9001'}
    class Channel(discord.abc.Messageable):
        id = 20
        guild = None
        recipients = None
        recipient = SimpleNamespace(id=2)
        def __init__(self):
            self._state = SimpleNamespace(http=HTTP(), allowed_mentions=discord.AllowedMentions.none(), create_message=lambda **kw: SimpleNamespace(id=9001))
        async def _get_channel(self):
            return self
    channel = Channel()
    asyncio.run(Kei.outbox_loop(sender(e, channel)))
    row = db.one('SELECT * FROM kei_outbox')
    assert row['status'] == 'sent' and row['message'] == '9001'
    assert e.messenger.mapping_for(row['id'])['message'] == '9001'
    assert payloads[0]['content'] == 'Selected message.'
    assert payloads[0]['allowed_mentions'] == {'parse': []}


def test_erase_during_dm_lookup_prevents_real_send(engine):
    from minecraft_agent.v3.application import Kei
    e, db, _ = engine
    source(e, 'Send to Alice: Selected message.')
    asyncio.run(e.messenger.apply('1', 'dm:1', '10', ['100'], [{'action': 'send', 'recipient': 'Alice', 'text': 'Selected message.'}]))
    channel = DM()
    b = sender(e, channel)
    original = b.fetch_user
    async def erase(ident):
        e.memory.forget('1', 'dm:1', ['100'])
        return await original(ident)
    b.fetch_user = erase
    asyncio.run(Kei.outbox_loop(b))
    assert not channel.sent
    assert db.one('SELECT * FROM kei_outbox')['content'] == ''


def test_unknown_send_outcome_stops_retries(engine):
    from minecraft_agent.v3.application import Kei
    e, db, _ = engine
    source(e, 'Send to Alice: Selected message.')
    asyncio.run(e.messenger.apply('1', 'dm:1', '10', ['100'], [{'action': 'send', 'recipient': 'Alice', 'text': 'Selected message.'}]))
    channel = DM()
    async def unknown(*a, **kw):
        raise OSError('synthetic lost response')
    channel.send = unknown
    asyncio.run(Kei.outbox_loop(sender(e, channel)))
    assert db.one('SELECT * FROM kei_outbox')['status'] == 'uncertain'
    assert db.one('SELECT * FROM kei_handoffs69')['status'] == 'uncertain'


def test_semantic_compose_exports_only_selected_sources_with_shared_call_budget(engine):
    e, db, model = engine
    text = 'Ask Alice whether she can join tonight.'
    source(e, 'Unrelated private history.', ident='90')
    source(e, text)
    model.decisions = iter([turn(messenger_actions=[{'action': 'ask', 'recipient': 'Alice', 'text': 'Unrelated private history.'}])])
    original = model.chat
    async def chat(history, tools=None, **kwargs):
        if tools[0]['function']['name'] == 'compose_handoff':
            model.calls.append((copy.deepcopy(history), copy.deepcopy(tools)))
            assert 'Unrelated private history.' not in json.dumps(history)
            assert text in json.dumps(history)
            return {'tool_calls': [{'function': {'name': 'compose_handoff', 'arguments': json.dumps({'authorized': True, 'text': 'Can you join tonight?'})}}]}
        return await original(history, tools, **kwargs)
    model.chat = chat
    asyncio.run(e.converse('1', 'dm:1', '10', text, ['100']))
    assert db.one('SELECT * FROM kei_outbox')['content'] == 'Can you join tonight?'
    assert len(model.calls) == 2


def test_application_resolver_freshly_verifies_humans_and_rejects_ambiguous_alias(engine):
    from minecraft_agent.v3.application import Kei
    e, db, model = engine
    actor = SimpleNamespace(id=1, bot=False, system=False, name='Requester', global_name=None, nick=None)
    alice = SimpleNamespace(id=2, bot=False, system=False, name='Alice', global_name=None, nick=None)
    class Guild:
        id = 5
        members = [actor, alice]
        def get_member(self, ident):
            return next((u for u in self.members if u.id == ident), None)
        async def fetch_member(self, ident):
            return self.get_member(ident)
    guild = Guild()
    channel = SimpleNamespace(id=10, guild=guild)
    b = SimpleNamespace(engine=e, store=db, guilds=[guild], destination=AsyncMock(return_value=channel))
    e.messenger_resolve = MethodType(Kei.resolve_messenger_recipient, b)
    source(e, 'Ask Alice: Are you playing tonight?', scope='guild:5:10')
    model.decisions = iter([turn(messenger_actions=[{'action': 'ask', 'recipient': 'Alice', 'text': 'Are you playing tonight?'}])])
    asyncio.run(e.converse('1', 'guild:5:10', '10', 'Ask Alice: Are you playing tonight?', ['100']))
    assert db.one('SELECT * FROM kei_outbox')['channel'] == 'dm:2'
    guild.members = [actor, alice, SimpleNamespace(id=3, bot=False, system=False, name='Alice', global_name=None, nick=None)]
    source(e, 'Ask Alice: Are you playing tomorrow?', scope='guild:5:10', ident='101')
    model.decisions = iter([turn(reply='Sent.', response_action='reply', messenger_actions=[{'action': 'ask', 'recipient': 'Alice', 'text': 'Are you playing tomorrow?'}]), turn(reply='Which Alice?', response_action='reply')])
    asyncio.run(e.converse('1', 'guild:5:10', '10', 'Ask Alice: Are you playing tomorrow?', ['101']))
    assert len(db.rows('SELECT * FROM kei_outbox')) == 1
    assert db.one('SELECT * FROM kei_social_actions')['content'] == 'Which Alice?'


def test_explicit_no_send_is_checked_only_for_actual_proposal(engine):
    e, db, model = engine
    text = 'Do NOT send Alice this message.'
    source(e, text)
    model.decisions = iter([turn(messenger_actions=[{'action': 'send', 'recipient': 'Alice', 'text': text}]), turn(reply='Nothing will be sent.', response_action='reply')])
    original = model.chat
    async def chat(history, tools=None, **kwargs):
        if tools[0]['function']['name'] == 'compose_handoff':
            model.calls.append((copy.deepcopy(history), copy.deepcopy(tools)))
            assert text in json.dumps(history)
            return {'tool_calls': [{'function': {'name': 'compose_handoff', 'arguments': json.dumps({'authorized': False, 'text': ''})}}]}
        return await original(history, tools, **kwargs)
    model.chat = chat
    asyncio.run(e.converse('1', 'dm:1', '10', text, ['100']))
    assert not db.rows('SELECT * FROM kei_outbox') and len(model.calls) == 3


def test_after_send_forget_keeps_confirmed_remote_id_without_body(engine):
    from minecraft_agent.v3.application import Kei
    e, db, _ = engine
    source(e, 'Send to Alice: Selected message.')
    asyncio.run(e.messenger.apply('1', 'dm:1', '10', ['100'], [{'action': 'send', 'recipient': 'Alice', 'text': 'Selected message.'}]))
    channel = DM()
    async def forget_after_send(*a, **kw):
        e.memory.forget('1', 'dm:1', ['100'])
        return SimpleNamespace(id=9001)
    channel.send = forget_after_send
    asyncio.run(Kei.outbox_loop(sender(e, channel)))
    row = db.one('SELECT * FROM kei_outbox')
    assert row['message'] == '9001' and row['status'] == 'sent' and row['content'] == ''
    assert e.messenger.mapping_for(row['id'])['message'] == '9001'

def test_new_copilot_task_registers_explicit_dm_result_without_lost_projection(engine):
    e,db,model=engine
    e.refresh_servers=lambda:None
    e.select=lambda *a:'synthetic'
    e.assigned=lambda *a:['synthetic']
    e.permission=lambda *a:'copilot'
    e.servers={'synthetic':{'id':'synthetic','name':'Synthetic'}}
    e.tools={'synthetic':SimpleNamespace(capabilities=lambda:[])}
    launched=[];e.launch=launched.append
    text='Inspect this server, then DM me the resulting report.'
    source(e,text)
    model.decisions=iter([turn(intent='copilot',goal='Inspect server',mode='observe',plan=['Read status'],
        messenger_actions=[{'action':'send','delivery':'dm','when':'task_complete','task_id':'$current','text':'resulting report'}])])
    asyncio.run(e.converse('1','dm:1','10',text,['100']))
    assert len(launched)==1
    handoff=db.one('SELECT * FROM kei_handoffs69')
    assert handoff and handoff['task']==launched[0]
    db.update_task(launched[0],status='succeeded',result='Actual newly completed result.')
    e.deliver_task_result(db.one('SELECT * FROM kei_tasks WHERE id=?',(launched[0],)),'Actual newly completed result.')
    outgoing=db.rows('SELECT * FROM kei_outbox')
    assert len(outgoing)==1 and outgoing[0]['channel']=='dm:1'

def test_actual_gateway_reply_to_confirmed_answer_uses_internal_source(engine,monkeypatch):
    from minecraft_agent.v3.application import Kei
    from minecraft_agent.v2.application import Kei as LegacyKei
    from unittest.mock import patch
    e,db,_=engine
    cfg=copy.deepcopy(e.cfg);cfg.update(_path='data/synthetic.yaml',secrets_file='data/synthetic-secrets.json')
    bot=Kei(cfg,db,SimpleNamespace(model='offline'))
    bot._connection.user=SimpleNamespace(id=999)
    db.add_message('dm:1','1','assistant','Selected prior answer.','internal-answer')
    action=bot.engine.conversation.queue('10','old','reply','Selected prior answer.','dm:1','1')
    db.execute("UPDATE kei_social_actions SET status='sent' WHERE id=?",(action,))
    db.execute('INSERT INTO kei_social_sent VALUES (?,?)',(action,'9001'))
    db.execute('INSERT INTO kei_conversation_sent VALUES (?,?,?)',(action,0,'9001'))
    ref=SimpleNamespace(id=9001,author=bot.user,content='Selected prior answer.')
    channel=SimpleNamespace(id=10,fetch_message=AsyncMock(return_value=ref),guild=None)
    message=SimpleNamespace(id=100,author=SimpleNamespace(id=1,bot=False),webhook_id=None,channel=channel,guild=None,
        content='Send this selected answer to my DM.',mentions=[],reference=SimpleNamespace(resolved=ref,message_id=9001))
    with patch.object(LegacyKei,'on_message',new=AsyncMock()),patch('minecraft_agent.v3.social_runtime.capture'):
        asyncio.run(bot.on_message(message))
    selection=db.one('SELECT * FROM kei_messenger_selections69 WHERE request=?',('100',))
    assert selection and selection['source']=='internal-answer' and selection['user']=='1'


def test_sender_failure_returns_only_one_natural_notice_to_original_request(engine):
    from minecraft_agent.v3.application import Kei
    e,db,_=engine
    source(e,'Tell Alice: Selected message.')
    asyncio.run(e.messenger.apply('1','dm:1','10',['100'],[{'action':'send','recipient':'Alice','text':'Selected message.'}]))
    channel=DM(actor=2)
    async def failure(*a,**kw):raise TimeoutError('unknown transport result')
    channel.send=failure
    bot=sender(e,channel);bot.cfg=e.cfg
    asyncio.run(Kei.outbox_loop(bot))
    row=db.one('SELECT * FROM kei_outbox')
    notice=db.one("SELECT * FROM kei_social_actions WHERE kind='short_reply'")
    assert row['status']=='uncertain' and notice and notice['channel']=='10' and notice['message']=='100'
    assert 'Selected message.' not in notice['content']
    assert e.messenger.failure_notice(row['id'],'uncertain',{'uncertain':'unknown'}) is None
