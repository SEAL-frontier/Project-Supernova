import httpx, json, os

MODEL='ag/gemini-3.8-flash-medium'

class Model:
    def __init__(self,base,key,model=None):
        self.model=model or os.environ.get('PROVIDER_MODEL',MODEL)
        self.http=httpx.AsyncClient(base_url=base.rstrip('/')+'/',headers={'Authorization':'Bearer '+key},timeout=90)
    async def chat(self,messages,tools=None,max_tokens=4096,tool_choice=None):
        # Provider adapters may retain only the last system message. Keep persona,
        # identity and later task updates together rather than losing earlier context.
        systems=[m['content'] for m in messages if m['role']=='system']
        if systems:messages=[{'role':'system','content':'\n\n'.join(systems)}]+[m for m in messages if m['role']!='system']
        body={'model':self.model,'messages':messages,'stream':False,'max_tokens':max_tokens}
        if tools:body.update(tools=tools,tool_choice=tool_choice or 'auto')
        r=await self.http.post('chat/completions',json=body)
        if r.status_code>=400:raise RuntimeError('9Router HTTP '+str(r.status_code))
        d=r.json()
        if not d.get('choices'):raise RuntimeError('Provider returned no choices')
        m=d['choices'][0]['message'];m['role']='assistant'
        for tc in m.get('tool_calls') or []:
            if tc.get('type')!='function':raise ValueError('Unsupported tool call')
            args=json.loads(tc['function']['arguments'])
            if not isinstance(args,dict):raise ValueError('Tool args must be object')
        return m
    async def close(self):await self.http.aclose()

def tool(name,description,props,required=()):
    return {'type':'function','function':{'name':name,'description':description,'parameters':{'type':'object','properties':props,'required':list(required)}}}

S={'type':'string'}
def choices(*values):return {'type':'string','enum':list(values)}
