"""Public regression tests using synthetic inputs and offline transports only."""
import asyncio


import httpx
import pytest

from minecraft_agent.v2 import model


def run_provider(status, payload, *, image=False):
    calls = []
    async def run():
        async def transport(request):
            calls.append(request)
            return httpx.Response(status, json=payload, headers={'x-request-id': 'Bearer-secret'})
        client = model.Model('https://offline.invalid/v1', 'synthetic-key')
        await client.http.aclose()
        client.http = httpx.AsyncClient(base_url='https://offline.invalid/v1/', transport=httpx.MockTransport(transport))
        try:
            content = [{'type': 'image_url', 'image_url': {'url': 'data:image/png;base64,AA=='}}] if image else 'hello'
            return await client.chat([{'role': 'user', 'content': content}])
        finally:
            await client.close()
    try:
        return asyncio.run(run()), calls
    except Exception as exc:
        return exc, calls


@pytest.mark.parametrize('image', [False, True])
def test_bad_request_is_structured_safe_and_never_retried(image):
    error, calls = run_provider(400, {'error': {'message': 'PRIVATE SENTINEL', 'code': 'invalid_argument'}}, image=image)
    assert type(error).__name__ == 'ProviderError'
    assert model.classify_response_failure(error) == 'request_rejected'
    assert len(calls) == 1
    assert error.retryable is False
    assert 'PRIVATE SENTINEL' not in str(error)
    assert error.safe_metadata()['request_id'] is None


@pytest.mark.parametrize('nested', [False, True])
def test_block_reason_has_safe_structured_classification(nested):
    body = {'promptFeedback': {'blockReason': 'SAFETY'}}
    error, calls = run_provider(200, {'response': body} if nested else body)
    assert type(error).__name__ == 'ProviderBlocked'
    assert model.classify_response_failure(error) == 'blocked'
    assert error.safe_metadata()['block_reason'] == 'SAFETY'
    assert len(calls) == 1


def test_unknown_block_reason_is_not_retained():
    error, _ = run_provider(200, {'promptFeedback': {'blockReason': 'PRIVATE SENTINEL'}})
    assert type(error).__name__ == 'ProviderBlocked'
    assert error.block_reason is None
    assert 'PRIVATE SENTINEL' not in str(error.safe_metadata())


@pytest.mark.parametrize('payload,code', [([], 'invalid_response'), ({}, 'missing_choices'), ({'choices': [None]}, 'invalid_response'), ({'choices': [{'message': {'tool_calls': [{'type': 'function', 'function': {'name': 'inspect', 'arguments': '[]'}}]}}]}, 'invalid_tool_call')])
def test_invalid_provider_envelopes_are_structured(payload, code):
    error, calls = run_provider(200, payload)
    assert type(error).__name__ == 'ProviderError'
    assert error.code == code
    assert model.classify_response_failure(error) == 'invalid_response'
    assert len(calls) == 1


def test_valid_response_keeps_public_contract_and_strips_reasoning():
    result, calls = run_provider(200, {'choices': [{'message': {'content': 'ok', 'analysis': 'hidden'}}]})
    assert result == {'role': 'assistant', 'content': 'ok'}
    assert len(calls) == 1


def test_calculator_and_chemistry_helpers_make_real_png(tmp_path):
    from io import BytesIO
    from PIL import Image
    from minecraft_agent.v3 import chat_math, chat_helpers
    assert chat_math.calculate('sqrt(81) + 2**3') == 17
    assert chat_math.handle_tool('calculate', {'expression': '__import__(1)'}).ok is False
    formula = r'\text{pH}=-\log(\mathrm{H}^{+})'
    image = chat_math.render_formula(formula)
    with Image.open(BytesIO(image.png)) as decoded:
        decoded.load()
        assert decoded.format == 'PNG'
        assert decoded.size == (image.width, image.height)
    assert chat_helpers.discord_math_text(r'\mathrm{H}^{+}') == 'H^(+)'
    assert chat_helpers.discord_math_text(r'`\mathrm{H}`') == r'`\mathrm{H}`'
    receipts = []
    parts = chat_helpers.render_parts([{'type': 'formula', 'formula': formula}], tmp_path, receipts=receipts)
    assert parts[0]['type'] == 'image'
    assert receipts == [{'part_index': 0, 'prepared': True, 'delivered': False}]


def test_telemetry_rejects_unknown_enum_without_sqlite_write(tmp_path):
    from minecraft_agent.v3 import telemetry
    from minecraft_agent.v3.store import Store
    db = Store(str(tmp_path / 'metrics.sqlite'))
    try:
        metrics = telemetry.Telemetry(db, {'telemetry': {'enabled': True}})
        metrics.record('conversation', user='synthetic-user', intent='chat', action='reply', reason='direct')
        before = db.one('SELECT count(*) n FROM kei_telemetry_events')['n']
        for invalid in ('not_an_intent', 42, [], {}):
            with pytest.raises(ValueError):
                metrics.record('conversation', intent=invalid)
        assert db.one('SELECT count(*) n FROM kei_telemetry_events')['n'] == before
        row = db.one('SELECT * FROM kei_telemetry_events')
        assert row['actor'] != 'synthetic-user'
        assert 'synthetic-user' not in row['data']
    finally:
        db.db.close()


def test_attachment_dispatch_uses_existing_connector_and_keeps_guards(tmp_path, monkeypatch):
    from minecraft_agent.v2.tools import ServerTools, DangerousAction
    from minecraft_agent.v3.connectors import HybridTools
    from minecraft_agent.v3.attachments import CONTEXT, record
    from minecraft_agent.v3.store import Store
    monkeypatch.chdir(tmp_path)
    source = tmp_path / 'data' / 'attachments' / 'synthetic.txt'
    source.parent.mkdir(parents=True)
    source.write_bytes(b'synthetic attachment')
    volume = tmp_path / 'server'
    volume.mkdir()
    tools = HybridTools({'id': 'synthetic', 'name': 'Synthetic', 'connectors': {'local': {'root': str(volume), 'writable': True}}}, {})
    db = Store(str(tmp_path / 'files.sqlite'))
    ident = record(db, 'synthetic-message', 'synthetic-user', 'synthetic-scope', source, source.name)
    args = {'attachment_id': ident, 'path': 'config/example.txt'}
    token = CONTEXT.set((db, {'requester': 'synthetic-user', 'scope': 'synthetic-scope', 'server': 'synthetic'}))
    try:
        with pytest.raises(PermissionError):
            tools.execute('attachment_install', args, mode='observe')
        with pytest.raises(DangerousAction):
            tools.execute('attachment_install', {**args, 'path': 'world/example.dat'})
        result = tools.execute('attachment_install', args)
        assert result['verified'] is True
        assert (volume / 'config/example.txt').read_bytes() == source.read_bytes()
        plain = ServerTools({'name': 'Synthetic'})
        plain.do_arbitrary = lambda: {'verified': True}
        with pytest.raises(ValueError, match='Unknown tool'):
            plain.execute('arbitrary', {})
        with pytest.raises(ValueError, match='Unknown tool'):
            plain.execute('attachment_install', args)
    finally:
        CONTEXT.reset(token)
        db.db.close()


@pytest.mark.parametrize('expression', ['2**101', 'sqrt(-1)', '1/0', 'True', 'x.y', '1e101', '(' * 30 + '1' + ')' * 30])
def test_calculator_rejects_unsafe_or_unbounded_input(expression):
    from minecraft_agent.v3.chat_math import calculate, MathInputError
    with pytest.raises(MathInputError):
        calculate(expression)


@pytest.mark.parametrize('formula', [r'\input{secret}', r'\text{H_{2}}', r'\ce{H2O}', '{x'])
def test_renderer_rejects_unsupported_commands_and_nested_labels(formula):
    from minecraft_agent.v3.chat_math import render_formula, MathInputError
    with pytest.raises(MathInputError):
        render_formula(formula)
