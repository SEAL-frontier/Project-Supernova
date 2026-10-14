import re

def discord_chunks(text, limit=2000):
    """Each outside-fence line is a message; code fences survive length splitting."""
    out=[]; code=[]; fence=None
    def long_line(s):
        while s:
            cut=min(len(s),limit)
            if cut<len(s):
                space=s.rfind(' ',0,cut)
                if space>cut//2:cut=space
            out.append(s[:cut]);s=s[cut:].lstrip()
    def flush_code():
        body='\n'.join(code);opening=fence or '```'
        room=limit-len(opening)-8
        while body:
            cut=min(len(body),room)
            if cut<len(body):
                newline=body.rfind('\n',0,cut)
                if newline>0:cut=newline
            out.append(opening+'\n'+body[:cut]+'\n```');body=body[cut:].lstrip('\n')
        if not code:out.append(opening+'\n```')
    for line in str(text or '').splitlines():
        if re.match(r'^\s*```',line):
            if fence is None:fence=line.strip();code=[]
            else:flush_code();fence=None;code=[]
        elif fence is not None:code.append(line)
        elif line.strip():long_line(line.strip())
    if fence is not None:flush_code()
    return out

def redact(value,secrets=()):
    text=str(value)
    for secret in sorted((s for s in secrets if s and len(s)>3),key=len,reverse=True):text=text.replace(secret,'[REDACTED]')
    return re.sub(r'(?i)((?:token|api_key|password|authorization)\s*[:=]\s*)[^\s,]+',r'\1[REDACTED]',text)
