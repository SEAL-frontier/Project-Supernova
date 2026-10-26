"""Untrusted proposals within the existing social turn, not another classifier."""
import copy
import math

GUIDANCE = (
    'HUMAN MESSAGE HANDOFF: Use messenger_actions for an explicit current human request to send/ask someone, '
    'move the selected conversation/report to their own DM, deliver after an owned job, at an actual time, or at next contact. '
    'Use ordinary intent=chat, not a Minecraft worker. Send only the selected point, never unrelated private history. '
    'recipient must be the exact name/mention/ID written by the human, or omit only for their own explicit DM/source destination. '
    'A question body should naturally attribute the requester; never impersonate them or commit on their behalf. '
    'Only current source IDs and explicit selected attachment IDs are usable. Ask one short clarification if ambiguous. '
    'Send now by default. A question about tonight is not a request to wait until tonight or next contact. '
    'Use delayed when only if the current human actually requests delay. Explicit requested peer/self DMs are not proactive opt-in. '
    'at is a Unix timestamp; next_contact means the recipient actually talks to Kei, not online surveillance. '
    'task_complete needs the exact requester-owned task_id; use $current only with a new copilot task in this same turn. '
    'Use reply/decline/defer only for the bound question this recipient received; return a selected answer to requester DM. '
    'Revise/cancel can change only unsent content; no pretend unsending. No visible tickets, cards, delivery receipts, '
    'mandatory acknowledgments or stage announcements. Backend acceptance is pending, not proof of sending. '
    'A short natural acknowledgment or silence is enough; do not claim sent/delivered/seen before an actual receipt. '
    'A normal reply without messenger_actions cannot send, schedule or promise future contact. '
)

_STRING_FIELDS = {'id':100,'recipient':100,'text':1800,'task_id':100,'reply_to':100}
_ENUM_FIELDS = {
    'action':('send','ask','revise','cancel','reply','decline','defer'),
    'delivery':('dm','source'), 'when':('now','at','next_contact','task_complete'),
    'return_to':('dm','source'),
}

def schema():
    fields={key:{'type':'string','maxLength':limit} for key,limit in _STRING_FIELDS.items()}
    fields.update({key:{'type':'string','enum':list(values)} for key,values in _ENUM_FIELDS.items()})
    fields.update({key:{'type':'array','maxItems':limit,'items':{'type':'string','maxLength':100}}
                   for key,limit in (('source_ids',8),('attachment_ids',4))})
    fields['when']['description']='now unless human explicitly requests waiting until a time, owned task completion, or next actual conversation. Do not confuse the time asked ABOUT with delivery time.'
    fields['at']={'type':'number'}
    return {'type':'array','maxItems':4,'description':'Explicit human messages only; no extra classifier or operational authority. Empty unless current human asks. No success receipt UI.',
            'items':{'type':'object','additionalProperties':False,'properties':fields,'required':['action']}}

def validate(operations):
    if operations is None:return []
    if not isinstance(operations,list) or len(operations)>4:raise ValueError('invalid_messenger_actions')
    allowed=set(_STRING_FIELDS)|set(_ENUM_FIELDS)|{'source_ids','attachment_ids','at'}
    for op in operations:
        if not isinstance(op,dict) or set(op)-allowed or op.get('action') not in _ENUM_FIELDS['action']:
            raise ValueError('invalid_messenger_action')
        for key,limit in _STRING_FIELDS.items():
            if key in op and (not isinstance(op[key],str) or len(op[key])>limit):raise ValueError('invalid_messenger_field')
        for key,values in _ENUM_FIELDS.items():
            if key in op and op[key] not in values:raise ValueError('invalid_messenger_enum')
        for key,limit in (('source_ids',8),('attachment_ids',4)):
            if key in op and (not isinstance(op[key],list) or len(op[key])>limit or any(not isinstance(v,str) or len(v)>100 for v in op[key])):
                raise ValueError('invalid_messenger_sources')
        if 'at' in op and (type(op['at']) not in (int,float) or not math.isfinite(op['at'])):raise ValueError('invalid_messenger_time')
    return copy.deepcopy(operations)
