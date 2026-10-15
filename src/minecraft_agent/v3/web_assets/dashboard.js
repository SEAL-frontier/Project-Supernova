'use strict';
let state=null,candidate=null,editingTask=null;
const $=id=>document.getElementById(id);
const empty=(parent,text)=>{const el=document.createElement('p');el.className='empty';el.textContent=text;parent.append(el);};
let noteTimer;
function note(text){clearTimeout(noteTimer);noteTimer=setTimeout(()=>$('status').classList.add('hidden'),8000);$('status').textContent=text;$('status').classList.remove('hidden');}
async function api(path,data){
 const opts=data===undefined?{}:{method:'POST',headers:{'Content-Type':'application/json','X-CSRF-Token':state?.csrf||''},body:JSON.stringify(data)};
 const response=await fetch(path,opts);
 if(response.status===401)throw Error('Đăng nhập Discord trước nhé.');
 let value;try{value=await response.json();}catch{throw Error('Chưa nhận được phản hồi hợp lệ. Thử lại sau một chút nhé.');}
 if(!response.ok)throw Error(value.error||'Thao tác chưa thành công.');return value;
}
function option(select,value,label){const el=document.createElement('option');el.value=value;el.textContent=label;select.append(el);}
function block(parent,text,cls='item'){const el=document.createElement('div');el.className=cls;el.textContent=text;parent.append(el);return el;}
function action(parent,label,callback,primary=false){const button=document.createElement('button');button.textContent=label;if(primary)button.className='primary';button.onclick=run(callback);parent.append(button);return button;}
function run(fn){return async event=>{const button=event?.currentTarget;try{if(button)button.disabled=true;await fn();}catch(error){note(error.message);}finally{if(button)button.disabled=false;}};}
function tab(name,focus=false){
 document.querySelectorAll('[data-tab]').forEach(button=>{const active=button.dataset.tab===name;button.setAttribute('aria-selected',String(active));button.tabIndex=active?0:-1;if(active&&focus)button.focus();});
 document.querySelectorAll('.dashboard-panel').forEach(panel=>panel.classList.toggle('hidden',panel.id!=='panel-'+name));
}
document.querySelectorAll('[data-tab]').forEach(button=>{
 button.onclick=()=>tab(button.dataset.tab);
 button.onkeydown=event=>{const buttons=[...document.querySelectorAll('[data-tab]')];let index=buttons.indexOf(button);if(event.key==='ArrowRight')index=(index+1)%buttons.length;else if(event.key==='ArrowLeft')index=(index-1+buttons.length)%buttons.length;else if(event.key==='Home')index=0;else if(event.key==='End')index=buttons.length-1;else return;event.preventDefault();tab(buttons[index].dataset.tab,true);};
});
let example='chat',exampleTimer=null,setupStep=0;
function info(){ $('welcome').classList.remove('hidden');$('settings').classList.add('hidden');document.querySelector('#project').scrollIntoView({behavior:'smooth'}); }
function dashboard(){if(!state)return; $('welcome').classList.add('hidden');$('settings').classList.remove('hidden');$('settings').scrollIntoView({behavior:'smooth'});}
document.querySelectorAll('[data-info]').forEach(el=>el.onclick=event=>{event.preventDefault();info();});
$('open-dashboard').onclick=dashboard;
document.querySelectorAll('[data-demo]').forEach(el=>el.onclick=()=>$('demo').scrollIntoView({behavior:'smooth'}));
const examples={chat:['Kei, hôm nay mình hơi mệt.','Vậy nghỉ một chút đã. Có chuyện gì thì kể mình nghe.','Chuyện thường ngày, không gọi công cụ quản lý server.'],work:['Kei, kiểm tra TPS server giúp mình.','TPS đang 19.98. Em đã đọc số liệu mới, chưa thấy dấu hiệu nghẽn tick.','Ví dụ minh họa. Khi chạy thật, số liệu phải đến từ server được cấp quyền.'],schedule:['Mai 07:00 gọi mình dậy đi học.','Rồi, đừng thức tới sáng nữa đấy.\n-# Bấm 🕒 để xác nhận · Mai 07:00','Lịch chỉ bật sau khi bạn xác nhận. Có thể đổi giờ, tạm dừng hoặc hủy.']};
function playExample(key){example=key;clearTimeout(exampleTimer);const sample=examples[key];document.querySelectorAll('[data-example]').forEach(b=>b.setAttribute('aria-pressed',String(b.dataset.example===key)));$('example-user').textContent=sample[0];$('example-bot').textContent='…';$('example-note').textContent='Kei đang trả lời';$('example-progress').classList.toggle('hidden',key!=='work');exampleTimer=setTimeout(()=>{$('example-bot').textContent=sample[1];$('example-note').textContent=sample[2];$('example-bot').classList.remove('highlight');void $('example-bot').offsetWidth;$('example-bot').classList.add('highlight');},matchMedia('(prefers-reduced-motion: reduce)').matches?0:800);}
document.querySelectorAll('[data-example]').forEach(b=>b.onclick=()=>playExample(b.dataset.example));$('replay').onclick=()=>playExample(example);
function setup(step){setupStep=Math.min(2,Math.max(0,step));$('setup-guide').classList.remove('hidden');const copy=[['1. Chọn cách nói chuyện','Chỉnh bên dưới rồi bấm Lưu. Chưa biết chọn gì? Cứ giữ mặc định.','personal'],['2. Có chơi Minecraft không?','Tạo mã liên kết nhân vật ở bên dưới. Có server riêng thì kết nối Panel; chỉ muốn chat thì bỏ qua bước này.','minecraft'],['3. Xong phần làm quen rồi','Thử nhắn “Kei ơi” trong DM. Có thể dặn “gọi mình là anh” hoặc “chỉ hiện tiến độ ngắn thôi” ngay trong chat.','personal']][setupStep];$('setup-title').textContent=copy[0];$('setup-copy').textContent=copy[1];$('setup-next').textContent=setupStep===2?'Xong, đi nói chuyện thôi':'Bước tiếp theo →';document.querySelectorAll('[data-step]').forEach(b=>b.setAttribute('aria-current',Number(b.dataset.step)===setupStep?'step':'false'));tab(copy[2]);}
$('start-setup').onclick=()=>setup(0);$('setup-next').onclick=()=>setupStep===2?$('setup-guide').classList.add('hidden'):setup(setupStep+1);$('setup-close').onclick=()=>$('setup-guide').classList.add('hidden');document.querySelectorAll('[data-step]').forEach(b=>b.onclick=()=>setup(Number(b.dataset.step)));
document.addEventListener('click',event=>{const el=event.target.closest('button,.button');if(!el||matchMedia('(prefers-reduced-motion: reduce)').matches)return;const ripple=document.createElement('span');ripple.className='ripple';el.append(ripple);setTimeout(()=>ripple.remove(),500);});
const capabilities={status:'Trạng thái',console:'Console',power:'Bật / tắt',files:'Tệp',plugins:'Plugin',plugin_install:'Cài plugin',logs:'Log',profiler:'Profiler',tps:'TPS',players:'Người chơi',host:'Máy chủ',remote_shell:'SSH',web_search:'Tìm trên web',fetch_url:'Đọc trang',plugin_search:'Tìm plugin',health:'Sức khỏe server'};
function renderServers(){
 $('servers').replaceChildren();$('default-server').replaceChildren();$('access-server').replaceChildren();$('task-server').replaceChildren();option($('task-server'),'','Không cần server');
 for(const server of state.servers){
  option($('default-server'),server.id,server.name);option($('task-server'),server.id,server.name);
  const row=block($('servers'),'');block(row,server.name,'item-title');block(row,server.level==='copilot'?'Được nhờ thao tác':server.level==='observe'?'Chỉ xem':'Chỉ trò chuyện','item-meta');
  const caps=block(row,'','capabilities');for(const cap of server.capabilities)block(caps,capabilities[cap]||cap,'capability');
  const controls=block(row,'','item-actions');action(controls,'Kiểm tra kết nối',async()=>{note('Đang kiểm tra '+server.name+'…');const result=await api('/api/server/test',{server:server.id});note(result.message);});
  if(server.manage_access){option($('access-server'),server.id,server.name);}
 }
 if(!state.servers.length)empty($('servers'),'Chưa có server được phân công. Bạn vẫn trò chuyện với Kei bình thường được.');
 $('default-server').disabled=!state.servers.length;$('default-save').disabled=!state.servers.length;
 if(state.default_server)$('default-server').value=state.default_server;
 $('server-count').textContent=state.servers.length+' server được phép';
 $('connect-card').classList.toggle('hidden',!state.can_connect);$('access-card').classList.toggle('hidden',!state.servers.some(server=>server.manage_access));
 $('candidate-guild').replaceChildren();option($('candidate-guild'),'','Chưa gắn guild');for(const guild of state.guilds.filter(g=>g.manage_guild))option($('candidate-guild'),guild.id,guild.name);
 renderAccess();updateTaskMode();
}
function updateTaskMode(){$('task-server').disabled=$('task-mode').value==='alarm';}
$('task-mode').onchange=updateTaskMode;
const episodeTitles={warm_exchange:'Một chuyện đáng nhớ',nickname:'Chuyện biệt danh',milestone:'Một dấu mốc',conflict:'Lúc không vui',reconciliation:'Chuyện làm hòa',commitment:'Điều đã hứa',inside_joke:'Chuyện đùa của hai người'};
function friendlyMemoryTitle(title){return Object.prototype.hasOwnProperty.call(episodeTitles,title)?episodeTitles[title]:title||'Chuyện đáng nhớ';}
function friendlyRankReason(reason){return !reason||reason==='No established rank change yet.'?'Chưa có thay đổi quan hệ đủ rõ để đổi rank.':reason;}
async function loadProfile(){
 const profile=await api('/api/profile');$('relationship-rank').textContent=profile.rank?.label||'Neutral';$('relationship').textContent=friendlyRankReason(profile.rank?.reason);$('dimensions').replaceChildren();
 const labels={familiarity:'Quen thuộc',trust:'Tin cậy',warmth:'Ấm áp',playfulness:'Trêu đùa',tension:'Căng thẳng',confidence:'Độ chắc chắn',interaction_frequency:'Tần suất tương tác'};
 for(const[key,value]of Object.entries(profile.dimensions||{})){if(typeof value!=='number')continue;const stat=block($('dimensions'),'','stat');const label=block(stat,'','stat-label');block(label,labels[key]||key,'');block(label,Math.round(value*100)+'%','');const meter=document.createElement('meter');meter.min=0;meter.max=1;meter.value=Math.max(0,Math.min(1,value));meter.setAttribute('aria-label',labels[key]||key);stat.append(meter);}
 const moods={calm:'Bình thường',playful:'Đang muốn trêu',warm:'Dịu hơn một chút',annoyed:'Hơi cáu'};
 $('relationship-mood').textContent=profile.mood?'Giọng trò chuyện gần đây: '+(moods[profile.mood.tone]||profile.mood.tone):'';
 $('rank-progress').textContent=profile.rank_progress?.pending_label?'Đang ghi nhận chuyển biến về '+profile.rank_progress.pending_label+'. Cần thêm tương tác có ý nghĩa để xác nhận.':'Rank lâu dài đổi chậm hơn những chuyển biến trong từng cuộc trò chuyện.';
 $('relationship-signals').replaceChildren();for(const signal of(profile.signals||[])){block($('relationship-signals'),(profile.rank?.label||'Neutral')+' '+(signal.direction==='up'?'↑':'↓').repeat(Math.abs(signal.delta)>=.035?2:1)+' · '+new Date(signal.at*1000).toLocaleString('vi-VN'), 'item');}
 if(!profile.signals?.length)empty($('relationship-signals'),'Chưa có chuyển biến mới được ghi nhận. Giọng cà khịa của Kei không tự tính là mất thiện cảm.');
 await loadMemories();
}
async function load(){
 const initial=!state;state=await api('/api/state');$('name').textContent=state.name;$('open-dashboard').classList.remove('hidden');document.querySelectorAll('[data-login-link]').forEach(link=>link.classList.add('hidden'));$('logout').classList.remove('hidden');if(initial)$('welcome').classList.add('hidden');$('login-help').classList.add('hidden');if(initial)$('settings').classList.remove('hidden');$('custom-instructions').value=state.custom_instructions||'';
 for(const key of['persona','debug'])$(key).value=state[key];$('timezone').value=state.preferences.timezone||'Asia/Ho_Chi_Minh';$('dm').value=String(Boolean(state.preferences.dm_opt_in));$('muted').value=String(Boolean(state.preferences.muted));$('sharing').value=state.preferences.sharing||'strict';$('rank').value=String(state.preferences.rank_notifications!==false);$('task-timezone').textContent='Giờ theo '+$('timezone').value+'. Kết quả gửi về DM của bạn.';
 $('accounts').replaceChildren();for(const account of state.linked_accounts)block($('accounts'),account.account+' · '+account.server+(account.verified?' · đã xác thực':''));if(!state.linked_accounts.length)empty($('accounts'),'Chưa link nhân vật Minecraft.');
 renderServers();await Promise.all([loadProfile(),loadTasks()]);
}
function dateLabel(task){return task.next_run?new Date(task.next_run*1000).toLocaleString('vi-VN',{timeZone:task.timezone||state.preferences.timezone}):'';}
async function loadTasks(){
 const result=await api('/api/tasks');$('tasks-card').classList.toggle('hidden',!result.available);$('tasks-unavailable').classList.toggle('hidden',result.available);$('tasks-list').replaceChildren();
 const labels={pending:'Chờ xác nhận',active:'Đã hẹn',paused:'Tạm dừng',completed:'Hoàn tất',cancelled:'Đã hủy'};
 for(const task of result.items){
  const row=block($('tasks-list'),'');block(row,task.goal,'item-title');block(row,(labels[task.status]||task.status)+(task.next_run?' · '+dateLabel(task):''),'item-meta');const controls=block(row,'','item-actions');
  const actions=task.status==='pending'?[['confirm','🕒 Xác nhận']]:task.status==='active'?[['pause','Tạm dừng']]:task.status==='paused'?[['resume','Tiếp tục']]:[];
  if(!['cancelled','completed'].includes(task.status))actions.push(['cancel','Hủy']);
  for(const[actionName,label]of actions)action(controls,label,async()=>{await api('/api/tasks/action',{id:task.id,action:actionName});await loadTasks();note(actionName==='confirm'?'Đã xác nhận lịch.':actionName==='resume'?'Lịch chờ bạn xác nhận lại.':'Đã cập nhật lịch.');},actionName==='confirm');
  action(controls,'Sửa',async()=>{editingTask=task.id;$('task-goal').value=task.goal;$('task-mode').value=task.alarm?'alarm':task.mode;$('task-server').value=task.server||'';$('task-when').value='';$('task-form-title').textContent='Sửa lịch hẹn';$('task-save').textContent='Đề xuất sửa lịch';updateTaskMode();$('task-when').focus();});
 }
 if(!result.items.length)empty($('tasks-list'),'Chưa có lịch hẹn. Tạo một lời nhắc hoặc việc kiểm tra server nhé.');
}
$('save').onclick=run(async()=>{await api('/api/settings',{persona:$('persona').value,debug:$('debug').value,timezone:$('timezone').value,dm_opt_in:$('dm').value==='true',muted:$('muted').value==='true',sharing:$('sharing').value,rank_notifications:$('rank').value==='true',custom_instructions:$('custom-instructions').value});await load();note('Đã lưu thiết lập của bạn.');});
$('default-save').onclick=run(async()=>{await api('/api/settings',{default_server:$('default-server').value});note('Đã lưu server mặc định cho DM.');});
$('link').onclick=run(async()=>{const result=await api('/api/link',{});$('link-code').textContent=result.command+' · hết hạn sau 10 phút.';});
$('unlink').onclick=run(async()=>{if(confirm('Gỡ các liên kết Minecraft của bạn?')){await api('/api/unlink',{});await load();note('Đã gỡ link.');}});
for(const[id,all]of[['forget',false],['forget-all',true]])$(id).onclick=run(async()=>{if(confirm(all?'Quên toàn bộ dữ liệu của bạn ở mọi ngữ cảnh?':'Quên memory của bạn trong DM?')){await api('/api/forget',{confirm:true,all});await loadProfile();note('Đã quên dữ liệu và phần dẫn xuất liên quan.');}});
$('preview').onclick=run(async()=>{note('Đang kiểm tra Panel…');candidate=await api('/api/connect/preview',{url:$('panel-url').value,token:$('panel-key').value});$('panel-key').value='';$('candidate-server').replaceChildren();for(const server of candidate.servers)option($('candidate-server'),String(server.index),server.name);$('candidate').classList.remove('hidden');note('Đã đọc danh sách từ Panel. Chọn đúng server để kết nối.');});
$('commit').onclick=run(async()=>{const result=await api('/api/connect/commit',{connection:candidate.connection,index:Number($('candidate-server').value),guild:$('candidate-guild').value});candidate=null;$('candidate').classList.add('hidden');await load();note('Đã kết nối '+result.name+'.');});
$('access-save').onclick=run(async()=>{const person=await api('/api/access/preview',{server:$('access-server').value,subject:$('subject').value.trim()});if(!confirm('Áp dụng thay đổi quyền cho '+(person.person?.display_name||$('subject').value)+' trên '+$('access-server').selectedOptions[0].text+'?\n'+$('action').selectedOptions[0].text+' · '+$('level').selectedOptions[0].text+'\n'+$('access-extent').selectedOptions[0].text+' · '+$('access-policy').selectedOptions[0].text))return;await api('/api/access',{server:$('access-server').value,subject:$('subject').value,action:$('action').value,level:$('level').value,...(state.servers.find(s=>s.id===$('access-server').value)?.owner?{execution:{extent:$('access-extent').value,level:$('access-policy').value}}:{})});await load();note('Đã lưu phân quyền.');});
$('task-save').onclick=run(async()=>{await api('/api/tasks/propose',{id:editingTask,goal:$('task-goal').value,when:$('task-when').value,server:$('task-mode').value==='alarm'?'':$('task-server').value,mode:$('task-mode').value,timezone:$('timezone').value});editingTask=null;$('task-form-title').textContent='Hẹn Kei một việc';$('task-save').textContent='Đề xuất lịch';await loadTasks();note('Lịch đang chờ. Bấm 🕒 Xác nhận nếu đúng thời gian và công việc.');});
$('task-reset').onclick=()=>{editingTask=null;$('task-goal').value='';$('task-when').value='';$('task-mode').value='alarm';$('task-server').value='';$('task-save').textContent='Đề xuất lịch';$('task-form-title').textContent='Hẹn Kei một việc';updateTaskMode();};
$('logout').onclick=run(async()=>{await api('/logout',{});location.reload();});
let memoryNext=null;
async function loadMemories(more=false){const result=await api('/api/memories?offset='+(more?memoryNext||0:0)+'&q='+encodeURIComponent($('memory-query').value));if(!more)$('memories').replaceChildren();$('memory-count').textContent=result.total+' chuyện';for(const memory of result.items){const row=document.createElement('details');row.className='memory-card';const title=document.createElement('summary');title.textContent=memory.title;row.append(title);if(memory.at)block(row,new Date(memory.at*1000).toLocaleDateString('vi-VN'),'fine');block(row,memory.summary||'','');for(const quote of memory.excerpts||[]){const el=document.createElement('blockquote');el.textContent=(quote.role==='assistant'?'Kei: ':'Bạn: ')+quote.text;row.append(el);}$('memories').append(row);}if(!result.total)empty($('memories'),$('memory-query').value?'Chưa tìm thấy chuyện nào khớp. Thử một từ khác nhé.':'Chưa có chuyện được chọn lưu ở đây. Những kỷ niệm sẽ xuất hiện dần, không cần lấp đầy bằng chuyện bịa.');memoryNext=result.next_offset;$('memory-more').classList.toggle('hidden',memoryNext===null);}
$('memory-search').onclick=run(()=>loadMemories());$('memory-more').onclick=run(()=>loadMemories(true));$('memory-query').onkeydown=e=>{if(e.key==='Enter')run(()=>loadMemories())();};
function personCard(parent,person,fallback){const row=block(parent,'','person-row');if(person?.avatar_url){const img=document.createElement('img');img.src=person.avatar_url;img.alt='';img.referrerPolicy='no-referrer';row.append(img);}else block(row,(person?.display_name||fallback||'?').slice(0,1),'avatar-fallback');const text=block(row,'','');block(text,person?.display_name||fallback,'item-title');block(text,person?.username?'@'+person.username+' · '+(person.id||fallback):fallback,'item-meta');return row;}
function renderAccess(){const server=state.servers.find(s=>s.id===$('access-server').value);$('access-roster').replaceChildren();$('access-unavailable').classList.toggle('hidden',Boolean(server));if(!server)return;$('access-extent').disabled=!server.owner;$('access-policy').disabled=!server.owner;$('access-extent').querySelector('[value=machine]').disabled=!server.host_available||!server.can_grant_host;for(const grant of server.grants||[]){const row=block($('access-roster'),'','roster-card');personCard(row,grant.person,grant.subject);block(row,grant.role==='owner'?'Chủ server':grant.admin?'Admin server':grant.level==='copilot'?'Copilot':grant.level==='observe'?'Chỉ xem':'Chỉ trò chuyện','pill');block(row,(grant.permissions||[]).join(' · '),'item-meta');block(row,(grant.execution?.extent==='machine'?'Full Machine':'Minecraft-only')+' · '+(grant.execution?.level||'default'),'fine');block(row,'Cấp bởi '+(grant.grantor?.display_name||grant.issuer||'cấu hình chủ bot'),'fine');if(grant.role!=='owner'){const controls=block(row,'','item-actions');action(controls,'Sửa quyền',async()=>{$('subject').value=grant.subject;$('level').value=grant.level;$('action').value='grant';$('access-extent').value=grant.execution?.extent||'minecraft';$('access-policy').value=grant.execution?.level||'default';personCard(($('access-person').replaceChildren(),$('access-person')),grant.person,grant.subject);$('subject').focus();});if(grant.source==='database'||grant.source==='grant'||grant.source==='delegated'||!grant.source)action(controls,'Thu hồi',async()=>{if(confirm('Thu hồi quyền của '+(grant.person?.display_name||grant.subject)+' trên '+server.name+'?')){await api('/api/access',{server:server.id,subject:grant.subject,action:'revoke'});await load();note('Đã thu hồi quyền sử dụng.');}});}}}
$('access-server').onchange=()=>{renderAccess();$('access-person').replaceChildren();$('subject').value='';$('access-extent').value='minecraft';$('access-policy').value='default';};$('access-lookup').onclick=run(async()=>{const result=await api('/api/access/preview',{server:$('access-server').value,subject:$('subject').value.trim()});$('access-person').replaceChildren();personCard($('access-person'),result.person,$('subject').value);$('access-extent').value=result.existing?.execution?.extent||'minecraft';$('access-policy').value=result.existing?.execution?.level||'default';block($('access-person'),result.existing?'Đã có quyền trên server này. Chọn thay đổi bên dưới.':'Chưa được phân quyền trên server này.','fine');});
load().catch(error=>{if(error.message!=='Đăng nhập Discord trước nhé.')note(error.message);});
