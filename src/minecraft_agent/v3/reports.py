"""Owner-scoped operational reports, independent from notification delivery."""
from __future__ import annotations
import hashlib,json,re,time
from ..v2.store import dumps,uid
from ..v2.text import redact

def step_summary(name,args):
    path=str(args.get('path','')).replace('`','')[:180]
    action=args.get('action','')
    if name=='power':return {'start':'Bật server','stop':'Tắt server','restart':'Khởi động lại server','kill':'Buộc dừng server'}.get(action,'Đổi trạng thái server')
    if name in ('file_action','files'):return {'remove':'Xóa tệp hoặc thư mục','restore':'Khôi phục bản sao','backup':'Sao lưu dữ liệu','write':'Ghi lại nội dung tệp'}.get(action,'Thay đổi tệp')+(' `'+path+'`' if path else '')
    if name=='remote_shell':
        command=str(args.get('command',''))
        if re.search(r'\brm\s',command):
            import shlex
            try:
                lexer=shlex.shlex(command,posix=True,punctuation_chars=';&|');lexer.whitespace_split=True;words=list(lexer);targets=[]
                for index,word in enumerate(words):
                    if word not in ('rm','/bin/rm','/usr/bin/rm'):continue
                    for target in words[index+1:]:
                        if target in (';','&&','||','|','&'):break
                        if not target.startswith('-'):targets.append(target.replace('`','')[:200])
                destination=', '.join('`'+t+'`' for t in targets[:4])
            except ValueError:destination=''
            return 'Xóa '+(destination or 'dữ liệu theo lệnh shell; cần xem lại đường dẫn trước khi xác nhận')+'. Cần kiểm tra bản sao lưu trước khi xóa.'
        if re.search(r'\bsudo\b',command) or args.get('sudo'):return 'Chạy lệnh trên máy chủ bằng quyền sudo của tài khoản đã kết nối.'
        return 'Chạy lệnh trực tiếp trên máy chủ; thay đổi có thể ảnh hưởng ngoài Minecraft.'
    if name=='console':return 'Gửi lệnh vào console Minecraft: `'+str(args.get('command','')).replace('`','')[:160]+'`'
    return {'plugin_install':'Cài hoặc cập nhật plugin','write_file':'Ghi nội dung tệp','files':'Thay đổi tệp server'}.get(name,'Thực hiện một thay đổi trên server')+(' `'+path+'`' if path else '')

class Reports:
    def __init__(self,engine):
        self.engine=engine;self.db=engine.db
        self.db.db.executescript('''
        CREATE TABLE IF NOT EXISTS kei_reports(id TEXT PRIMARY KEY,server TEXT,kind TEXT,subject TEXT,summary TEXT,task TEXT,at REAL,dedupe TEXT UNIQUE);
        CREATE TABLE IF NOT EXISTS kei_report_preferences(server TEXT,user TEXT,crash INTEGER DEFAULT 1,admin INTEGER DEFAULT 0,recovery INTEGER DEFAULT 1,PRIMARY KEY(server,user));
        CREATE TABLE IF NOT EXISTS kei_monitor_state(server TEXT PRIMARY KEY,state TEXT,changed REAL,incident TEXT DEFAULT '');
        CREATE TABLE IF NOT EXISTS kei_report_tasks(task TEXT PRIMARY KEY,kind TEXT,report TEXT);
        ''');self.db.db.commit()
        if not self.db.one("SELECT value FROM kei_meta WHERE key='reports-history-v1'"):
            with self.db.atomic():
                for task in self.db.rows("SELECT * FROM kei_tasks WHERE status IN ('succeeded','failed') AND result IS NOT NULL ORDER BY updated DESC LIMIT 100"):
                    if not task['result']:continue
                    ident=self.record(task['server'],'crash' if task['goal'].startswith('Investigate monitoring anomaly') else 'task',task['requester'],task['result'],task['id'],'task-result:'+task['id'],False)
                    if ident:self.db.execute('UPDATE kei_reports SET at=? WHERE id=?',(task['updated'],ident))
                self.db.execute("INSERT OR REPLACE INTO kei_meta VALUES ('reports-history-v1','done')")
    def owners(self,server):
        p=self.engine.servers[server];people={str(self.engine.cfg['owner_id']),*map(str,p.get('owners',[]))}
        row=self.db.one('SELECT owner FROM kei_registered_servers WHERE id=?',(server,))
        if row:people.add(row['owner'])
        for row in self.db.rows('SELECT user FROM kei_server_owners WHERE server=? AND revoked IS NULL',(server,)):people.add(row['user'])
        return sorted(people)
    def settings(self,user,server):
        if str(user) not in self.owners(server):raise PermissionError('Chỉ chủ server được chọn báo cáo gửi riêng cho mình.')
        row=self.db.one('SELECT crash,admin,recovery FROM kei_report_preferences WHERE server=? AND user=?',(server,str(user)))
        return {k:bool(v) for k,v in (row or {'crash':1,'admin':0,'recovery':1}).items()}
    def update(self,user,server,values):
        current=self.settings(user,server)
        if not isinstance(values,dict) or not set(values)<=set(current) or any(type(v)!=bool for v in values.values()):raise ValueError('Chọn bật hoặc tắt cho từng loại thông báo.')
        current.update(values);self.db.execute('INSERT OR REPLACE INTO kei_report_preferences VALUES (?,?,?,?,?)',(server,str(user),int(current['crash']),int(current['admin']),int(current['recovery'])))
        return current
    def record(self,server,kind,subject,summary,task='',dedupe=None,notify=True):
        summary=redact(str(summary),self.engine.progress.secrets)[:3500]
        key=dedupe or uid();ident=uid()
        with self.db.atomic():
            changed=self.db.execute('INSERT OR IGNORE INTO kei_reports VALUES (?,?,?,?,?,?,?,?)',(ident,server,kind,str(subject),summary,task,time.time(),key)).rowcount
            if not changed:return None
            if notify:
                for owner in self.owners(server):
                    if kind in self.settings(owner,server) and self.settings(owner,server)[kind]:
                        self.db.queue(owner,'**'+self.engine.servers[server].get('name',server)+'** · '+summary+'\n-# Đã lưu báo cáo. Có thể hỏi lại Kei hoặc đổi thông báo trong mục Người có quyền.')
        return ident
    def recent(self,user,server,limit=8):
        access=getattr(self.engine,'access',None)
        if not access or not access.manager(str(user),server):raise PermissionError('Bạn chưa có quyền xem báo cáo server này.')
        return self.db.rows('SELECT id,kind,subject,summary,task,at FROM kei_reports WHERE server=? ORDER BY at DESC LIMIT ?',(server,max(1,min(20,int(limit)))))
    def recover(self):
        groups={}
        for task in self.db.rows("SELECT * FROM kei_tasks WHERE status='reconcile'"):
            key='reconcile:'+task['id']
            if self.db.one('SELECT id FROM kei_reports WHERE dedupe=?',(key,)):continue
            self.record(task['server'],'recovery',task['requester'],'Tác vụ bị ngắt; cần kiểm tra kết quả thực tế trước khi làm tiếp: '+task['goal'].split('\n')[0][:220],task['id'],key,False)
            old_notice=self.db.one("SELECT id FROM kei_outbox WHERE channel=? AND at>=? AND content LIKE 'Kei bị ngắt giữa thao tác%' LIMIT 1",(task['channel'],task['updated']))
            if not old_notice:groups.setdefault((task['server'],task['channel'],task['requester']),[]).append(task)
        for (server,channel,requester),tasks in groups.items():
            # Preferences govern automatic recovery notices too. Persisted report remains queryable.
            if requester in self.owners(server) and not self.settings(requester,server)['recovery']:continue
            self.db.queue(channel,'-# '+str(len(tasks))+' việc trên '+self.engine.servers[server].get('name',server)+' cần kiểm tra lại sau khi Kei bị ngắt. Tiến độ đã lưu; chưa tự chạy lại thay đổi.')
    def monitor_sample(self,server,status,resources,limit,now=None):
        now=time.time() if now is None else now
        previous=self.db.one('SELECT * FROM kei_monitor_state WHERE server=?',(server,))
        changed=previous['changed'] if previous and previous['state']==status else now
        incident=previous['incident'] if previous else ''
        if status=='running' and (not limit or resources.get('memory_bytes',0)<=limit*.85):incident=''
        self.db.execute('INSERT OR REPLACE INTO kei_monitor_state VALUES (?,?,?,?)',(server,status,changed,incident))
        # Start/stop are normal lifecycle states. Offline gets a quiet persisted report,
        # never a crash claim; a running -> offline transition may be investigated read-only.
        key=''
        if status in ('crashed','error','failed'):key='failure:'+status+':'+str(int(changed))
        elif status=='starting' and now-changed>=600:key='boot:'+str(int(changed))
        elif status=='running' and limit and resources.get('memory_bytes',0)>limit*.9:key='memory:'+str(int(changed))
        elif status=='offline' and previous and previous['state']=='running':key='offline:'+str(int(changed))
        if not key:return None
        if incident==key:return None
        self.db.execute('UPDATE kei_monitor_state SET incident=? WHERE server=?',(key,server))
        return {'key':key,'state':status,'notify':status!='offline'}

