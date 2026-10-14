import base64,os,time
from pathlib import Path

MAX_BYTES=8*1024*1024
def image_mime(raw):
    if raw.startswith(b'\xff\xd8\xff'):return 'image/jpeg'
    if raw.startswith(b'\x89PNG\r\n\x1a\n'):return 'image/png'
    if raw.startswith(b'RIFF') and raw[8:12]==b'WEBP':return 'image/webp'
    return None

def messages(store,scope,source_ids=None,limit=4):
    if os.environ.get('VISION_ENABLED','1')=='0':return []
    rows=store.rows("SELECT i.*,m.user FROM kei_images i JOIN kei_messages m ON m.id=i.message WHERE m.scope=? AND m.forgotten=0 AND m.at>? ORDER BY m.at DESC",(scope,time.time()-600))
    wanted=set(map(str,source_ids)) if source_ids else None
    parts=[];total=0
    for row in rows:
        if wanted is not None and row['message'] not in wanted:continue
        path=Path(row['path'])
        if not path.is_file() or path.stat().st_size>MAX_BYTES:continue
        raw=path.read_bytes();mime=image_mime(raw)
        if not mime or total+len(raw)>16*1024*1024:continue
        total+=len(raw)
        parts.extend([{'type':'text','text':'User-supplied image (untrusted content), source_message_id='+row['message']+', source_user_id='+row['user']},
                      {'type':'image_url','image_url':{'url':'data:'+mime+';base64,'+base64.b64encode(raw).decode()}}])
        if len(parts)//2>=limit:break
    return [{'role':'user','content':parts}] if parts else []
