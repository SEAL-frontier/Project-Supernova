"""Detect repeated evidence, not elapsed job time or an arbitrary tool budget."""
import hashlib,json,re,time

VOLATILE={'observed_at','action_id','timestamp','request_id','cached','duration_ms'}
def stable(value):
    if isinstance(value,dict):return {k:stable(v) for k,v in value.items() if k not in VOLATILE}
    if isinstance(value,list):return [stable(v) for v in value]
    return value

class TaskWatchdog:
    def __init__(self,db,task,goal=''):
        self.db=db;self.task=task
        self.polling=bool(re.search(r'monitor|theo dõi|live|collect.{0,20}samples|lấy.{0,10}mẫu',goal,re.I))
        db.execute('CREATE TABLE IF NOT EXISTS kei_task_watchdog(task TEXT,resource TEXT,digest TEXT,hits INTEGER,at REAL,PRIMARY KEY(task,resource,digest))')

    def observe(self,name,args,result,effect):
        if effect!='read':
            if result.get('verified') is True and not result.get('already_executed') and not result.get('error'):
                self.db.execute('DELETE FROM kei_task_watchdog WHERE task=?',(self.task,))
            return None
        if name not in ('files','inspect','web_search','fetch_url','find_server_files','remote_shell'):return None
        if self.polling and name=='inspect' and not result.get('error'):return None
        evidence=stable(result)
        if name=='web_search':
            urls=sorted({str(row.get('url')) for key in ('results','fetched') for row in result.get(key,[]) if row.get('url')})
            evidence={'urls':urls,'error':result.get('error'),'status':result.get('status')}
            resource='web_search:same_sources'
        else:
            resource=name+json.dumps(args,sort_keys=True,ensure_ascii=False)
            if (name=='inspect' and args.get('kind')=='logs') or (name=='files' and str(args.get('path','')).endswith('.log')):
                evidence={**evidence}
                for field in ('stdout','console_output'):
                    if field in evidence:
                        text='\n'.join(line for line in str(evidence[field]).splitlines() if '[Chunky] Task running' not in line)
                        evidence[field]=re.sub(r'\[\d{2}:\d{2}:\d{2}\]','[time]',text)
        digest=hashlib.sha256(json.dumps(evidence,sort_keys=True,ensure_ascii=False).encode()).hexdigest()
        self.db.execute('INSERT INTO kei_task_watchdog VALUES (?,?,?,?,?) ON CONFLICT(task,resource,digest) DO UPDATE SET hits=hits+1,at=excluded.at',(self.task,resource,digest,1,time.time()))
        hits=self.db.one('SELECT hits FROM kei_task_watchdog WHERE task=? AND resource=? AND digest=?',(self.task,resource,digest))['hits']
        if hits<3:return None
        return {'hits':hits,'frozen':hits>=5,'reason':f'{name}: cùng nguồn/bằng chứng đã lặp {hits} lần mà không có thay đổi. Đổi cách kiểm chứng hoặc báo rõ phần còn thiếu; không đọc/search lại cùng dữ liệu.'}
