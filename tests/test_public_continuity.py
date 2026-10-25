"""Synthetic Engine integration, without provider or Discord network access."""
import asyncio
import copy
import json

import pytest

from minecraft_agent.v3.config import DEFAULTS
from minecraft_agent.v3.engine import Engine
from minecraft_agent.v3.store import Store


class Model:
    def __init__(self):
        self.calls = []
        self.after_worker = None

    async def chat(self, history, tools=None, **kwargs):
        self.calls.append(copy.deepcopy(history))
        name = tools[0]['function']['name'] if tools else ''
        if name == 'social_turn':
            value = {'intent': 'copilot', 'response_action': 'reply', 'reply': 'Checking.',
                     'goal': 'Inspect selected template', 'server': 'sandbox', 'mode': 'observe',
                     'complexity': 'simple', 'plan': ['Inspect']}
            return {'role': 'assistant', 'tool_calls': [{'id': 'route', 'type': 'function',
                    'function': {'name': 'social_turn', 'arguments': json.dumps(value)}}]}
        if self.after_worker:
            self.after_worker()
        return {'role': 'assistant', 'tool_calls': [{'id': 'question', 'type': 'function',
                'function': {'name': 'ask_requester', 'arguments': json.dumps({'question': 'Which file?'})}}]}


@pytest.fixture
def world(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    cfg = copy.deepcopy(DEFAULTS)
    cfg.update(owner_id='200', persona='Synthetic character.', timezone='UTC',
               secrets_file=str(tmp_path / 'secrets.json'), provider_key='', discord_token='',
               servers=[{'id': 'sandbox', 'name': 'Synthetic', 'connectors': {'local': {'root': str(tmp_path)}}}],
               assignments={'200': ['sandbox']})
    db = Store(':memory:')
    model = Model()
    bot = Engine(cfg, db, model)
    bot.prompt = lambda *args: [{'role': 'system', 'content': 'Synthetic public prompt.'}]
    bot.launch = lambda k: None
    yield bot, db, model
    db.db.close()


def make_task(world, scope='dm:200'):
    bot, db, model = world
    db.add_message(scope, '200', 'user', 'Please show options for the synthetic template.', '310')
    db.add_message(scope, '200', 'assistant', 'Option three is the amber-template with a bounded read-only plan.', '311')
    ack = bot.conversation.queue('100', '310', 'reply',
        'Option three is the amber-template with a bounded read-only plan.', scope, '200')
    db.execute("UPDATE kei_social_actions SET status='sent' WHERE id=?", (ack,))
    db.add_message(scope, '200', 'user', 'Use option three and inspect it only.', '312')
    asyncio.run(bot.converse('200', scope, '100', 'Use option three and inspect it only.', ['312']))
    return db.one('SELECT * FROM kei_tasks')


def test_actual_fresh_worker_gets_prior_assistant_option_without_persisted_quote(world):
    bot, db, model = world
    task = make_task(world)
    asyncio.run(bot.run(task['id']))
    assert 'amber-template' in str(model.calls[-1])
    # The task history carries worker receipts, not a second stored conversation copy.
    persisted = db.one('SELECT history FROM kei_tasks WHERE id=?', (task['id'],))['history']
    assert 'amber-template' not in persisted


def test_same_dm_context_survives_summary_but_never_enters_guild(world):
    bot, db, model = world
    make_task(world)
    assert 'amber-template' in str(model.calls[0])
    bot.launch = lambda k: None
    db.add_message('guild:400:500', '200', 'user', 'Inspect the selected template.', '320')
    asyncio.run(bot.converse('200', 'guild:400:500', '500', 'Inspect the selected template.', ['320']))
    assert 'amber-template' not in str(model.calls[-1])


@pytest.mark.parametrize('revocation', ['forget', 'service', 'cancel'])
def test_revocation_during_worker_inference_blocks_clarification_effect(world, revocation):
    bot, db, model = world
    task = make_task(world)
    before = len(db.rows('SELECT * FROM kei_outbox'))
    async def authorize(*args):
        return revocation != 'service' or model.after_worker is not None
    bot.service_authorize = authorize
    def revoke():
        if revocation == 'forget':
            db.execute('UPDATE kei_messages SET forgotten=1 WHERE id=?', ('311',))
        elif revocation == 'cancel':
            db.update_task(task['id'], status='cancelled')
        model.after_worker = None
    model.after_worker = revoke
    asyncio.run(bot.run(task['id']))
    assert len(db.rows('SELECT * FROM kei_outbox')) == before
    assert db.one('SELECT status FROM kei_tasks WHERE id=?', (task['id'],))['status'] in ('paused', 'cancelled')
