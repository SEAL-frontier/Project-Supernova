import json,re

def console_receipt(command,output):
    """Fresh console-log postconditions for message commands, not human read receipts."""
    command=command.strip().lstrip('/');words=command.split(None,2)
    if not words:return None
    name=words[0].split(':')[-1].lower()
    text=re.sub(r'§[0-9a-fk-or]','',output,flags=re.I)
    if re.search(r'unknown command|player not found|no player|cannot find|not online|không.*(?:tìm thấy|trực tuyến)|usage:|exception|\[ERROR\]',text,re.I):return None
    if name in ('say',):
        body=command.split(None,1)[1] if len(command.split(None,1))>1 else ''
        if body and any('[Server]' in line and body in line for line in text.splitlines()):return {'kind':'console_message_echo','scope':'message emitted by server','evidence':text[-2500:]}
    if name in ('msg','tell','w','whisper') and len(words)==3:
        target,body=words[1:]
        if any(re.search(r'\[[^\]\n]*(?:->|→)\s*'+re.escape(target)+r'\]',line,re.I) and body in line for line in text.splitlines()):return {'kind':'console_private_message_echo','scope':'message emitted to target; not proof they read it','evidence':text[-2500:]}
    if name in ('broadcast','bc','ebroadcast'):
        if command in text and re.search(r'CONSOLE issued server command:',text):return {'kind':'console_command_processed','scope':'broadcast command processed in fresh server log; no client read receipt','evidence':text[-2500:]}
    return None

def missing_verification(actions):
    missing=[]
    for index,a in enumerate(actions):
        if a['effect']=='read' or a['status']!='done':continue
        try:result=json.loads(a['result'] or '{}')
        except ValueError:result={}
        if result.get('verified') is True and (a['tool']!='console' or result.get('verification')):continue
        later=[r for r in actions[index+1:] if r['effect']=='read' and r['status']=='done']
        if not later:missing.append({'action_id':a['id'],'tool':a['tool'],'args':json.loads(a['args'])})
    return missing
