import asyncio, httpx, json, math, os, re, uuid
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime


# Never retain provider messages, arbitrary error codes or response headers: they
# can contain prompts, credentials, URLs and upstream account details.
_NETWORK_CODES={
    httpx.ConnectTimeout:'connect_timeout',httpx.ReadTimeout:'read_timeout',
    httpx.WriteTimeout:'write_timeout',httpx.PoolTimeout:'pool_timeout',
    httpx.TimeoutException:'timeout',httpx.ConnectError:'connect_error',
    httpx.ReadError:'read_error',httpx.WriteError:'write_error',
    httpx.CloseError:'close_error',httpx.RemoteProtocolError:'remote_protocol_error',
}
_PROVIDER_CODES={
    'invalid_argument','bad_request','invalid_request_error','context_length_exceeded',
    'model_not_found','authentication_error','permission_denied','insufficient_quota',
    'rate_limit_exceeded','resource_exhausted','server_error','unavailable',
}
_PERMANENT_CODES=_PROVIDER_CODES-{'rate_limit_exceeded','resource_exhausted','server_error','unavailable'}
_ERROR_CODES=_PROVIDER_CODES | {'http_error','transport_error','payload_too_large','vision_input_rejected',
              'provider_blocked','invalid_tool_call','invalid_json','invalid_response','missing_choices',*_NETWORK_CODES.values()}
_RETRY_STATUSES={429,502,503,504}
_MAX_ATTEMPTS=2
_MAX_RETRY_DELAY=2.0
_BLOCK_REASONS={'SAFETY','BLOCKLIST','PROHIBITED_CONTENT','OTHER','IMAGE_SAFETY'}


def _retry_delay(response):
    """Respect Retry-After without extending an interactive turn indefinitely."""
    value=response.headers.get('retry-after')
    if value is None:return 0.25
    try:delay=float(value)
    except ValueError:
        try:
            at=parsedate_to_datetime(value)
            if at.tzinfo is None:at=at.replace(tzinfo=timezone.utc)
            delay=(at-datetime.now(timezone.utc)).total_seconds()
        except (TypeError,ValueError,OverflowError):return None
    if not math.isfinite(delay):return None
    return max(0.0,delay) if delay<=_MAX_RETRY_DELAY else None


def _safe_identifier(value):
    if not isinstance(value,str) or not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_.:-]{0,127}',value):return None
    if re.search(r'(?:bearer|sk-|AIza|api[_-]?key|token|secret|gh[pousr]_|github_pat_|^eyJ)',value,re.I):return None
    return value


class ProviderError(RuntimeError):
    """Allowlisted diagnostics only; safe to include in local error telemetry."""
    def __init__(self,*,status=None,code='http_error',retryable=False,correlation_id=None,
                 request_id=None,provider_correlation_id=None,attempts=1,block_reason=None):
        self.status=status
        self.code=code if code in _ERROR_CODES or code=='http_error' else 'http_error'
        self.retryable=bool(retryable)
        self.correlation_id=_safe_identifier(correlation_id)
        self.request_id=_safe_identifier(request_id)
        self.provider_correlation_id=_safe_identifier(provider_correlation_id)
        self.attempts=attempts
        self.block_reason=block_reason if isinstance(block_reason,str) and block_reason in _BLOCK_REASONS else None
        self.user_message=(
            'Yêu cầu vượt giới hạn kích thước phía model/proxy (HTTP 413); Kei chưa có kết quả cho lượt này. '
            'Gửi lại nguyên yêu cầu có thể vẫn bị; hãy giảm ảnh/tệp hoặc chia nhỏ nội dung.'
            if self.code=='payload_too_large' else
            'Provider rejected a request containing an image; image was not read'
            if self.code=='vision_input_rejected' else None)
        notice=f'; {self.user_message}' if self.user_message else ''
        label='ProviderBlocked' if self.code=='provider_blocked' else 'ProviderError'
        super().__init__(f'{label} status={status} code={self.code} retryable={self.retryable} correlation_id={self.correlation_id}{notice}')

    def safe_metadata(self):
        return {'failure_kind':classify_response_failure(self), **{name:getattr(self,name) for name in (
            'status','code','retryable','correlation_id','request_id','provider_correlation_id','attempts','block_reason')}}


def classify_response_failure(error):
    """Classify structured failures only; never inspect exception text or requests.

    Local validation is not proof of an upstream rejection. Image-bearing 400s
    remain request rejections: presence of an image does not establish causation.
    This API does not authorize retries or invalidate completed tool receipts.
    """
    if not isinstance(error,ProviderError):
        return 'local_validation' if isinstance(error,ValueError) else 'unknown'
    code,status=error.code,error.status
    if code=='provider_blocked':return 'blocked'
    if code=='payload_too_large' or status==413:return 'payload_too_large'
    if code.endswith('_timeout') or code=='timeout':return 'timeout'
    if code in _NETWORK_CODES.values() or code=='transport_error':return 'transport'
    if code in {'invalid_tool_call','invalid_json','invalid_response','missing_choices'}:return 'invalid_response'
    if status==401 or code=='authentication_error':return 'authentication'
    if status==403 or code=='permission_denied':return 'authorization'
    if status==429 or code in {'rate_limit_exceeded','resource_exhausted'}:return 'rate_limited'
    if isinstance(status,int) and 500<=status<=599:return 'provider_unavailable'
    if isinstance(status,int) and 400<=status<=499:return 'request_rejected'
    return 'unknown'


def _response_error(response,correlation_id,attempts,image_input=False):
    code='http_error'
    try:
        data=response.json()
        error=data.get('error',{}) if isinstance(data,dict) else {}
        if isinstance(error,dict):
            for field in ('code','status','type'):
                candidate=error.get(field)
                if isinstance(candidate,str) and candidate.lower() in _PROVIDER_CODES:
                    code=candidate.lower();break
    except (ValueError,UnicodeError,RecursionError):pass
    if response.status_code==413:code='payload_too_large'
    return ProviderError(status=response.status_code,code=code,retryable=response.status_code in _RETRY_STATUSES and code not in _PERMANENT_CODES,correlation_id=correlation_id,
                         request_id=response.headers.get('x-request-id'),
                         provider_correlation_id=response.headers.get('x-correlation-id'),attempts=attempts)


def _envelope_error(response,code,correlation_id,attempts):
    return ProviderError(status=response.status_code,code=code,correlation_id=correlation_id,
                         request_id=response.headers.get('x-request-id'),
                         provider_correlation_id=response.headers.get('x-correlation-id'),attempts=attempts)


MODEL='ag/gemini-3.8-flash-medium'

class ProviderBlocked(ProviderError):
    """Provider declined the prompt; retrying unchanged input cannot fix it."""
    def __init__(self,*,status=200,correlation_id=None,request_id=None,provider_correlation_id=None,attempts=1,block_reason=None):
        super().__init__(status=status,code='provider_blocked',correlation_id=correlation_id,
                         request_id=request_id,provider_correlation_id=provider_correlation_id,attempts=attempts,block_reason=block_reason)


class Model:
    def __init__(self,base,key,model=None):
        self.model=model or os.environ.get('PROVIDER_MODEL',MODEL)
        self.http=httpx.AsyncClient(base_url=base.rstrip('/')+'/',headers={'Authorization':'Bearer '+key,'x-9router-token-saver':'off'},timeout=90)
    def for_model(self,name):
        parent=self
        class View:
            model=name
            async def chat(self,*args,**kwargs):return await parent.chat(*args,**kwargs,model=name)
        return View()
    async def chat(self,messages,tools=None,max_tokens=4096,tool_choice=None,model=None):
        # Provider adapters may retain only the last system message. Keep persona,
        # identity and later task updates together rather than losing earlier context.
        systems=[m['content'] for m in messages if m['role']=='system']
        if systems:messages=[{'role':'system','content':'\n\n'.join(systems)}]+[m for m in messages if m['role']!='system']
        body={'model':model or self.model,'messages':messages,'stream':False,'max_tokens':max_tokens}
        if tools:body.update(tools=tools,tool_choice=tool_choice or 'auto')
        correlation_id=uuid.uuid4().hex
        for attempt in range(1,_MAX_ATTEMPTS+1):
            r=None
            try:r=await self.http.post('chat/completions',json=body,headers={'x-correlation-id':correlation_id})
            except httpx.TransportError as exc:
                code=next((code for kind,code in _NETWORK_CODES.items() if isinstance(exc,kind)),'transport_error')
                error=ProviderError(code=code,retryable=code!='transport_error',correlation_id=correlation_id,attempts=attempt)
            else:
                if r.status_code<400:break
                image_input=any(isinstance(m.get('content'),list) and any(isinstance(p,dict) and p.get('type')=='image_url' for p in m['content']) for m in messages)
                error=_response_error(r,correlation_id,attempt,image_input)
            # Only repeat inference, before any caller can execute returned tools.
            # Raise outside except so raw request-bearing exceptions aren't chained.
            delay=(_retry_delay(r) if r is not None else 0.25) if error.retryable and attempt<_MAX_ATTEMPTS else None
            if delay is None:raise error from None
            if r is not None:await r.aclose()
            await asyncio.sleep(delay)
        invalid_json=False
        try:d=r.json()
        except (ValueError,UnicodeError,RecursionError):invalid_json=True
        if invalid_json:raise _envelope_error(r,'invalid_json',correlation_id,attempt) from None
        if not isinstance(d,dict):raise _envelope_error(r,'invalid_response',correlation_id,attempt) from None
        nested=d.get('response') if isinstance(d.get('response'),dict) else {}
        feedback=d.get('promptFeedback') or nested.get('promptFeedback')
        if isinstance(feedback,dict) and feedback.get('blockReason'):
            raise ProviderBlocked(status=r.status_code,correlation_id=correlation_id,
                                  request_id=r.headers.get('x-request-id'),
                                  provider_correlation_id=r.headers.get('x-correlation-id'),attempts=attempt,
                                  block_reason=feedback.get('blockReason')) from None
        if not d.get('choices'):raise _envelope_error(r,'missing_choices',correlation_id,attempt) from None
        choices=d['choices']
        if not isinstance(choices,list) or not isinstance(choices[0],dict) or not isinstance(choices[0].get('message'),dict):
            raise _envelope_error(r,'invalid_response',correlation_id,attempt) from None
        m=dict(choices[0]['message']);m['role']='assistant'
        # Provider reasoning is neither conversational history nor user-facing debug.
        for private_key in ('reasoning_content','reasoning','analysis'):m.pop(private_key,None)
        calls=m.get('tool_calls')
        if calls is None:calls=[]
        invalid_call=False
        try:
            if not isinstance(calls,list):raise ValueError
            for tc in calls:
                if not isinstance(tc,dict) or tc.get('type')!='function':raise ValueError
                function=tc['function']
                if not isinstance(function,dict) or not isinstance(function.get('name'),str):raise ValueError
                if function['name']=='social_turn':continue # Social router owns strict schema/repair.
                args=json.loads(function['arguments'])
                if not isinstance(args,dict):raise ValueError
        except (ValueError,KeyError,TypeError,RecursionError):invalid_call=True
        if invalid_call:raise _envelope_error(r,'invalid_tool_call',correlation_id,attempt) from None
        return m
    async def close(self):await self.http.aclose()

def tool(name,description,props,required=()):
    return {'type':'function','function':{'name':name,'description':description,'parameters':{'type':'object','properties':props,'required':list(required)}}}

S={'type':'string'}
def choices(*values):return {'type':'string','enum':list(values)}
