"""Detect repeated evidence, not elapsed job time or an arbitrary tool budget."""
import hashlib,json,posixpath,re,time

VOLATILE={'observed_at','action_id','timestamp','request_id','cached','duration_ms'}
def stable(value):
    if isinstance(value,dict):return {k:stable(v) for k,v in value.items() if k not in VOLATILE}
    if isinstance(value,list):return [stable(v) for v in value]
    if isinstance(value,str) and value.lstrip().startswith(('{','[')):
        try:return stable(json.loads(value))
        except (ValueError,TypeError):pass
    return value

class TaskWatchdog:
    def __init__(self,db,task,goal=''):
        self.db=db;self.task=task
        self.set_goal(goal)
        db.execute('CREATE TABLE IF NOT EXISTS kei_task_watchdog(task TEXT,resource TEXT,digest TEXT,hits INTEGER,at REAL,PRIMARY KEY(task,resource,digest))')

    def set_goal(self,goal):
        self.polling=bool(re.search(r'\b(?:monitor|monitoring|watch|live)\b|theo dõi|collect.{0,20}samples|lấy.{0,10}mẫu',goal,re.I))
        self.configuration=bool(re.search(r'\bconfig(?:uration)?\b|cấu hình',goal,re.I))

    def hit(self,resource,evidence):
        digest=hashlib.sha256(json.dumps(evidence,sort_keys=True,ensure_ascii=False).encode()).hexdigest()
        self.db.execute('INSERT INTO kei_task_watchdog VALUES (?,?,?,?,?) ON CONFLICT(task,resource,digest) DO UPDATE SET hits=hits+1,at=excluded.at',(self.task,resource,digest,1,time.time()))
        return self.db.one('SELECT hits FROM kei_task_watchdog WHERE task=? AND resource=? AND digest=?',(self.task,resource,digest))['hits']

    def observe(self,name,args,result,effect):
        failed=bool(result.get('error') or result.get('blocked') or result.get('exit_code',0))
        if effect!='read' and not failed and result.get('verified') is True and not result.get('already_executed') and result.get('accepted') is not False:
            # Only the first receipt for a distinct mutation is progress. Cycling
            # through no-op writes must not erase evidence of a read loop.
            if self.hit('mutation:'+name,stable(args))==1:
                self.db.execute("DELETE FROM kei_task_watchdog WHERE task=? AND resource NOT LIKE 'mutation:%'",(self.task,))
                return None
        if self.polling and name in ('inspect','console','profiler') and effect=='read' and not failed:return None
        canonical={k:v for k,v in args.items() if k not in ('lines','limit')}
        if name=='verify_action':
            canonical={k:v for k,v in canonical.items() if k!='postcondition'}
            try:
                check=json.loads(canonical.get('check_args_json','{}'))
                canonical['check_args_json']={k:v for k,v in check.items() if k not in ('lines','limit')}
            except (ValueError,TypeError,AttributeError):pass
        if isinstance(canonical.get('path'),str):canonical['path']=posixpath.normpath(canonical['path'].replace('\\','/'))
        if isinstance(canonical.get('command'),str):canonical['command']=' '.join(canonical['command'].strip().lstrip('/').split())
        evidence=stable(result)
        if name=='verify_action' and result.get('readback') is not None:
            evidence={'verified':result.get('verified'),'readback':stable(result['readback'])}
        if name=='web_search':
            urls=sorted({str(row.get('url')) for key in ('results','fetched') for row in result.get(key,[]) if row.get('url')})
            evidence={'urls':urls,'error':result.get('error'),'status':result.get('status')}
            resource='web_search:same_sources'
        else:
            resource=name+json.dumps(canonical,sort_keys=True,ensure_ascii=False)
            # For a config job, normal heap/TPS jitter is not evidence that a
            # config reload worked. Preserve full samples for diagnostic goals.
            if self.configuration and not self.polling and name=='inspect' and args.get('kind')=='status' and not failed:
                data=result.get('data') or result
                state=data.get('state',data.get('current_state'))
                if isinstance(state,str):evidence={'state':state,'verified':result.get('verified')}
            if name=='task_evidence':
                # Completed receipt IDs are stable even if their wrapper or
                # human-readable verification reason changes.
                evidence=stable(result.get('receipts',result))
            if (name=='inspect' and args.get('kind')=='logs') or (name=='files' and str(args.get('path','')).endswith('.log')):
                evidence={**evidence}
                for field in ('stdout','console_output'):
                    if field in evidence:
                        text='\n'.join(line for line in str(evidence[field]).splitlines() if '[Chunky] Task running' not in line)
                        evidence[field]=re.sub(r'\[\d{2}:\d{2}:\d{2}\]','[time]',text)
        hits=self.hit(resource,evidence)
        if hits<3:return None
        return {'hits':hits,'frozen':hits>=5,'reason':f'{name}: cùng nguồn/bằng chứng đã lặp {hits} lần mà không có thay đổi. Đổi cách kiểm chứng hoặc báo rõ phần còn thiếu; không đọc/search lại cùng dữ liệu.'}
