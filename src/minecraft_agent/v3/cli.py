from __future__ import annotations
import argparse, asyncio, copy, getpass, hashlib, json, os, re, secrets, shlex, socket, sys, time
from pathlib import Path
from zoneinfo import ZoneInfo
import httpx, yaml, paramiko
from . import VERSION
from .config import DEFAULTS, Secrets, atomic, load_config, merge, normalize_profile, save_config
from .panel import Panel

class Wizard:

    def __init__(self, answers=None, language='vi'):
        self.answers = answers or {}
        self.language = language

    def ask(self, key, label, default='', secret=False, required=False):
        english = {'timezone': 'IANA timezone (Vietnam: Asia/Ho_Chi_Minh)', 'discord_token': 'Discord bot token (hidden)', 'provider_base': 'Provider URL (OpenAI-compatible /v1)', 'provider_key': 'Provider API key (hidden)', 'provider_model': 'Model', 'chat_model': 'Chat model', 'agent_model': 'Agent model', 'owner_id': 'Discord user ID (leave blank to claim with /settings)', 'persona_file': 'Private persona file', 'persona': 'Describe your persona in one sentence', 'connection': 'Start with (chat/panel/ssh/bridge)', 'kind': 'Connector (panel/ssh/bridge)', 'panel_url': 'Panel URL', 'panel_auth': 'Authentication (key/password/session)', 'panel_key': 'Client API key (not a Wings token)', 'panel_username': 'Panel email/account', 'panel_password': 'Panel password (hidden)', 'session_file': 'Authenticated Playwright storage-state file', 'server_index': 'Choose server number', 'server_id': 'Server ID', 'server_name': 'Server name', 'ssh_host': 'SSH host', 'ssh_port': 'SSH port', 'ssh_user': 'SSH account', 'ssh_auth': 'SSH auth (key/password)', 'ssh_password': 'SSH password (hidden)', 'ssh_key': 'Private key path (inside runtime)', 'ssh_volume': 'Server directory (blank to discover)', 'volume_index': 'Choose directory number', 'minecraft_version': 'Minecraft version', 'trust_host_key': 'Verified fingerprint? (yes/no)', 'bridge_port': 'Bot bridge listening port', 'bridge_url': 'Bot WebSocket URL reachable from Minecraft'}
        if self.language == 'en' and key in english:
            label = english[key]
        if key in self.answers:
            value = str(self.answers[key])
        elif not sys.stdin.isatty():
            if required and (not default):
                raise ValueError('Thiếu ' + key + '; chạy tương tác hoặc dùng --answers <private.json>.')
            value = str(default)
        else:
            prompt = label + (' [' + str(default) + ']' if default and (not secret) else '') + ': '
            value = (getpass.getpass(prompt) if secret else input(prompt)).strip() or str(default)
        if required and (not value):
            raise ValueError('Cần nhập ' + key)
        return value

    def choose(self, key, label, values, default):
        value = self.ask(key, label + ' (' + '/'.join(values) + ')', default)
        if value not in values:
            raise ValueError(key + ': chọn ' + ', '.join(values))
        return value

def timezone_default():
    for candidate in [os.environ.get('TZ', ''), Path('/etc/timezone').read_text().strip() if Path('/etc/timezone').is_file() else '']:
        try:
            ZoneInfo(candidate)
            return candidate
        except (ValueError, KeyError):
            pass
    return 'Asia/Ho_Chi_Minh'

def setup(w, path='data/config.yaml', edit=False):
    path = Path(path)
    if path.exists() and (not edit):
        raise ValueError('Config đã có. Dùng setup --edit để chỉnh từng bước; không ghi đè ngầm.')
    cfg = load_config(path, check=False) if path.exists() else copy.deepcopy(DEFAULTS)
    if path.exists():
        atomic(str(path) + '.before-setup-' + str(int(time.time())), path.read_text())
    cfg['language'] = w.choose('language', 'Ngôn ngữ / Language', ('vi', 'en'), cfg.get('language', 'vi'))
    w.language = cfg['language']
    cfg['timezone'] = w.ask('timezone', 'Timezone IANA (Việt Nam: Asia/Ho_Chi_Minh)', cfg.get('timezone') or timezone_default())
    ZoneInfo(cfg['timezone'])
    secret_store = Secrets(cfg.get('secrets_file', 'data/secrets.json'))
    cfg['secrets_file'] = str(secret_store.path)
    token = w.ask('discord_token', 'Discord bot token (ẩn / hidden)', secret=True, required=not (cfg.get('discord_token') or secret_store.get(cfg.get('discord_token_ref'))))
    if token:
        cfg['discord_token_ref'] = secret_store.put('discord-token', token)
    base = w.ask('provider_base', 'Provider URL (OpenAI-compatible /v1)', cfg.get('provider_base', ''), required=True).rstrip('/')
    if not base.startswith(('http://', 'https://')):
        raise ValueError('Provider URL phải bắt đầu http:// hoặc https://')
    cfg['provider_base'] = base if base.endswith('/v1') else base + '/v1'
    key = w.ask('provider_key', 'Provider API key (ẩn / hidden)', secret=True, required=not (cfg.get('provider_key') or secret_store.get(cfg.get('provider_key_ref'))))
    if key:
        cfg['provider_key_ref'] = secret_store.put('provider-key', key)
    previous_model = cfg.get('provider_model')
    cfg['provider_model'] = w.ask('provider_model', 'Model', cfg.get('provider_model', 'ag/gemini-3.8-flash-medium'))
    for role, label in (('chat_model', 'Model trò chuyện'), ('agent_model', 'Model làm việc')):
        default = DEFAULTS[role] if 'gemini-3.8' in cfg['provider_model'] else cfg['provider_model']
        if path.exists() and previous_model == cfg['provider_model']:
            default = cfg.get(role) or default
        cfg[role] = w.ask(role, label, default)
    owner = w.ask('owner_id', 'Discord user ID (để trống để claim qua /settings)', cfg.get('owner_id', ''))
    if owner == '0':
        owner = ''
    if owner and (not owner.isdigit()):
        raise ValueError('owner_id là số Discord user ID, không phải display name.')
    cfg['owner_id'] = owner or '0'
    if not owner:
        claim = secrets.token_hex(8)
        cfg['owner_claim_hash'] = hashlib.sha256(claim.encode()).hexdigest()
        print('OWNER CLAIM — giữ riêng / keep private: /settings → Claim bot → code:' + claim)
    persona = Path(w.ask('persona_file', 'Persona file riêng', cfg.get('persona_file', 'data/persona.md')))
    cfg['persona_file'] = str(persona)
    if not persona.exists() or not persona.read_text(encoding='utf-8').strip():
        text = w.ask('persona', 'Mô tả persona bằng một câu / Describe your persona', required=True)
        atomic(persona, text + '\n')
    cfg['social']['ambient']['enabled'] = False
    save_config(cfg, path)
    kind = w.choose('connection', 'Bắt đầu với / Start with', ('chat', 'panel', 'ssh', 'bridge', 'local'), 'chat')
    if kind != 'chat':
        add_server(w, cfg, path, kind)
    print('SETUP SAVED — ' + str(path))
    print('Tiếp / Next: keys-keys doctor; keys-keys run')
    print('Discord Developer Portal: enable Message Content Intent; invite with bot + applications.commands. See docs/QUICKSTART.md.' if w.language == 'en' else 'Discord Developer Portal: bật Message Content Intent; invite với bot + applications.commands. Xem docs/QUICKSTART.md.')
    return cfg

def add_server(w, cfg, path, kind=None):
    kind = kind or w.choose('kind', 'Kiểu kết nối / Connector', ('panel', 'ssh', 'bridge', 'local'), 'panel')
    store = Secrets(cfg.get('secrets_file', 'data/secrets.json'))
    cs = {}
    profile = {}
    if kind == 'panel':
        url = w.ask('panel_url', 'Panel URL', required=True).rstrip('/')
        auth = w.choose('panel_auth', 'Xác thực / Auth', ('key', 'password', 'session'), 'key')
        panel = {'url': url}
        if auth == 'key':
            panel['token'] = store.put('panel-' + secrets.token_hex(4), w.ask('panel_key', 'Client API key (không phải Wings token)', secret=True, required=True))
        elif auth == 'password':
            panel['username'] = w.ask('panel_username', 'Email/account', required=True)
            panel['password'] = store.put('panel-password-' + secrets.token_hex(4), w.ask('panel_password', 'Password', secret=True, required=True))
        else:
            panel['username'] = w.ask('panel_username', 'Email/account', required=True)
        client = Panel(panel, store)
        try:
            if auth == 'session':
                source = Path(w.ask('session_file', 'Authenticated Playwright storage-state file', required=True))
                atomic(client.session_file, source.read_text())
                client.close()
                client = Panel(panel, store)
            rows = client.servers()
            if not rows:
                raise ValueError('Panel account không truy cập server nào.')
            for i, r in enumerate(rows):
                print(str(i + 1) + '. ' + str(r['name']))
            index = int(w.ask('server_index', 'Chọn số server / Choose server', '1')) - 1
            if index < 0 or index >= len(rows):
                raise ValueError('Server selection out of range')
            selected = rows[index]
            panel['server'] = selected['uuid']
            cs['panel'] = panel
            profile.update(name=selected['name'], uuid=selected['uuid'])
        finally:
            client.close()
    elif kind == 'ssh':
        ssh = {'host': w.ask('ssh_host', 'SSH host', required=True), 'port': int(w.ask('ssh_port', 'SSH port', '22')), 'user': w.ask('ssh_user', 'SSH account', required=True), 'known_hosts': 'data/known_hosts'}
        auth = w.choose('ssh_auth', 'SSH auth', ('key', 'password'), 'key')
        if auth == 'password':
            ssh['password'] = store.put('ssh-' + secrets.token_hex(4), w.ask('ssh_password', 'SSH password', secret=True, required=True))
        else:
            ssh['key_file'] = w.ask('ssh_key', 'Private key path (inside runtime/container)', required=True)
        known = Path(ssh['known_hosts'])
        known.parent.mkdir(parents=True, exist_ok=True)
        hosts = paramiko.HostKeys(str(known)) if known.exists() else paramiko.HostKeys()
        hostkey_name = ssh['host'] if ssh['port'] == 22 else '[' + ssh['host'] + ']:' + str(ssh['port'])
        transport = paramiko.Transport((ssh['host'], ssh['port']))
        try:
            transport.start_client(timeout=10)
            key = transport.get_remote_server_key()
            fingerprint = 'SHA256:' + __import__('base64').b64encode(hashlib.sha256(key.asbytes()).digest()).decode().rstrip('=')
            if hosts.lookup(hostkey_name):
                if not hosts.check(hostkey_name, key):
                    raise PermissionError('SSH host key CHANGED. Verify host identity before replacing the existing key.')
            else:
                print('SSH fingerprint:', fingerprint)
                if w.choose('trust_host_key', 'Đối chiếu fingerprint rồi tin host? / Verified fingerprint?', ('yes', 'no'), 'no') != 'yes':
                    raise PermissionError('Chưa tin SSH host key; chưa thực thi gì.')
                hosts.add(hostkey_name, key.get_name(), key)
                hosts.save(str(known))
                os.chmod(known, 384)
        finally:
            transport.close()
        from .connectors import HybridTools
        client = HybridTools({'id': 'setup', 'name': 'Setup', 'connectors': {'ssh': ssh}}, store)
        volume = w.ask('ssh_volume', 'Server directory (để trống để tự dò)')
        if not volume:
            result = client.shell('find /var/lib/pterodactyl/volumes /var/lib/pelican/volumes /root/wings/wings/volumes /home -maxdepth 4 -name server.properties -print 2>/dev/null', timeout=30)
            candidates = list(dict.fromkeys((str(Path(x).parent).replace('\\', '/') for x in result['stdout'].splitlines() if x.startswith('/'))))
            for i, candidate in enumerate(candidates):
                print(str(i + 1) + '. ' + candidate)
            if not candidates:
                raise ValueError('Không dò được volume; chạy lại với ssh_volume hoặc nhập directory.')
            volume = candidates[int(w.ask('volume_index', 'Chọn thư mục', '1')) - 1]
        if not volume.startswith('/') or '\n' in volume:
            raise ValueError('Absolute Linux server directory required')
        ssh['volume'] = volume
        metadata = client.shell('stat -c "%u:%g" ' + shlex.quote(volume) + '; grep -m1 "Starting minecraft server version" ' + shlex.quote(volume + '/logs/latest.log') + ' || true')
        lines = metadata['stdout'].splitlines()
        ssh['file_owner'] = next((x for x in lines if re.fullmatch('\\d+:\\d+', x)), None)
        found = re.search('Starting minecraft server version\\s+(\\S+)', metadata['stdout'])
        profile['minecraft_version'] = found[1] if found else w.ask('minecraft_version', 'Minecraft version (vd 1.21.11)', required=True)
        profile['uuid'] = Path(volume).name
        cs['ssh'] = ssh
        profile['name'] = w.ask('server_name', 'Tên server / Server name', 'Minecraft')
    elif kind == 'local':
        from .local import LocalAccess
        local = {'root': w.ask('local_root', 'Thư mục server nhìn thấy từ bot / Server directory visible to bot', required=True), 'writable': w.choose('local_writable', 'Cho phép sửa file / Allow writes?', ('no', 'yes'), 'no') == 'yes'}
        detected = LocalAccess(local).detect()
        if not detected['root_visible']:
            raise ValueError('Bot chưa đọc được thư mục này. Kiểm tra path/bind mount và quyền; cùng host không có nghĩa là cùng filesystem.')
        cs['local'] = local
        profile['name'] = w.ask('server_name', 'Tên server / Server name', 'Minecraft')
        print('Local access:', 'read/write' if detected['files_writable'] else 'read-only', '· process control needs explicitly registered actions')
    elif kind == 'bridge':
        profile['name'] = w.ask('server_name', 'Tên server / Server name', 'Minecraft')
        cs['bridge'] = {'token': store.put('bridge-' + secrets.token_hex(4), secrets.token_urlsafe(32))}
        cfg['bridge']['enabled'] = True
        cfg['bridge']['port'] = int(w.ask('bridge_port', 'Bot bridge listening port', str(os.environ.get('SERVER_PORT') or cfg['bridge']['port'])))
    else:
        raise ValueError('Unsupported connection kind')
    default_id = re.sub('[^a-z0-9-]', '-', profile.get('name', 'server').casefold()).strip('-')[:30] or 'minecraft'
    sid = w.ask('server_id', 'Server ID', default_id)
    if not re.fullmatch('[a-zA-Z0-9_-]{1,60}', sid):
        raise ValueError('Server ID: letters, numbers, - or _')
    existing = next((p for p in cfg['servers'] if p['id'] == sid), None)
    if existing:
        if kind in normalize_profile(existing)['connectors']:
            raise ValueError('Connector đã có; setup --edit hoặc sửa config có backup.')
        existing.setdefault('connectors', normalize_profile(existing)['connectors']).update(cs)
        profile = existing
    else:
        profile.update(id=sid, connectors=cs, owners=[cfg['owner_id']])
        cfg['servers'].append(profile)
    if cfg['owner_id'] != '0':
        cfg['assignments'].setdefault(cfg['owner_id'], [])
        cfg['assignments'][cfg['owner_id']] = list(dict.fromkeys(cfg['assignments'][cfg['owner_id']] + [sid]))
    if kind == 'bridge':
        endpoint = w.ask('bridge_url', 'URL Minecraft truy cập được tới bot (ws://HOST:PORT/v1/bridge)', required=True)
        generated = Path('data/bridge-configs') / sid / 'config.yml'
        atomic(generated, yaml.safe_dump({'server-id': sid, 'endpoint': endpoint, 'token': store.get(cs['bridge']['token']), 'triggers': cfg['social']['triggers']}, allow_unicode=True, sort_keys=False))
        print('Plugin config riêng:', generated)
        print('Copy vào plugins/KeysKeysBridge/config.yml rồi restart server. Không hot reload.')
    save_config(cfg, path)
    print('SERVER SAVED:', sid)
    return profile

async def doctor_async(cfg, offline=False):
    results = []

    def note(name, ok, detail):
        results.append({'check': name, 'status': 'verified' if ok is True else 'not_checked' if ok is None else 'failed', 'detail': detail})
        print(('OK ' if ok is True else 'SKIP ' if ok is None else 'FAIL ') + name + ': ' + detail)
    note('config', True, 'timezone=' + cfg['timezone'] + '; persona configured; secrets hidden')
    if offline:
        for name in ('discord', 'provider tools', 'connectors', 'vision'):
            note(name, None, 'offline check does not establish connectivity')
        return results
    async with httpx.AsyncClient(timeout=20) as client:
        try:
            r = await client.get('https://discord.com/api/v10/users/@me', headers={'Authorization': 'Bot ' + cfg['discord_token']})
            r.raise_for_status()
            assert r.json().get('bot')
            note('discord', True, 'bot token accepted; no Gateway consumer started')
        except Exception as exc:
            note('discord', False, type(exc).__name__ + '; check token, intents and Developer Portal instructions')
    from ..v2.model import Model, tool
    model = Model(cfg['provider_base'], cfg['provider_key'], cfg['provider_model'])
    try:
        definition = tool('setup_ping', 'Return this tool with ok=true', {'ok': {'type': 'boolean'}}, ['ok'])
        r = await model.chat([{'role': 'user', 'content': 'Call setup_ping with ok=true. No other task.'}], [definition], tool_choice={'type': 'function', 'function': {'name': 'setup_ping'}}, max_tokens=100)
        call = r['tool_calls'][0]
        assert call['function']['name'] == 'setup_ping' and json.loads(call['function']['arguments']).get('ok') is True
        note('provider tools', True, 'actual native function call received')
    except Exception as exc:
        note('provider tools', False, type(exc).__name__ + '; verify /v1 endpoint, model ID and tool support')
    finally:
        await model.close()
    from .connectors import HybridTools
    store = Secrets(cfg.get('secrets_file', 'data/secrets.json'))
    for p in cfg['servers']:
        executor = HybridTools(p, store)
        for kind, connector in p['connectors'].items():
            try:
                if kind == 'panel':
                    await asyncio.to_thread(executor.panel.server, 'GET', '')
                    note(p['id'] + '/panel', True, 'read actual selected server')
                elif kind == 'wings':
                    wings_only = HybridTools(dict(p, connectors={'wings': connector}), store)
                    await asyncio.to_thread(wings_only.api, 'GET', '')
                    note(p['id'] + '/wings', True, 'read actual daemon state')
                elif kind == 'ssh':
                    r = await asyncio.to_thread(executor.shell, 'printf kei-ssh-ready', sudo=False)
                    assert r['stdout'] == 'kei-ssh-ready'
                    note(p['id'] + '/ssh', True, 'verified host and authentication')
                elif kind == 'bridge':
                    note(p['id'] + '/bridge', None, 'use /server after bot + plugin start; pairing is not a live handshake')
            except Exception as exc:
                note(p['id'] + '/' + kind, False, type(exc).__name__ + '; rerun server add or inspect endpoint/credentials')
            finally:
                if kind == 'panel':
                    executor.panel.close()
    note('vision', None, 'Run keys-keys doctor --vision <image> for an actual image request; model name alone is not proof')
    return results

def main():
    parser = argparse.ArgumentParser(prog='keys-keys', description='Supernova setup, diagnostics and runtime')
    parser.add_argument('--version', action='version', version=VERSION)
    sub = parser.add_subparsers(dest='command', required=True)
    for name in ('setup', 'doctor', 'run', 'migrate'):
        p = sub.add_parser(name)
        p.add_argument('--config', default=None)
        if name == 'setup':
            p.add_argument('--answers')
            p.add_argument('--edit', action='store_true')
        if name == 'doctor':
            p.add_argument('--offline', action='store_true')
            p.add_argument('--vision')
    server = sub.add_parser('server')
    ss = server.add_subparsers(dest='server_command', required=True)
    add = ss.add_parser('add')
    add.add_argument('--config')
    add.add_argument('--kind', choices=['panel', 'ssh', 'bridge', 'local'])
    add.add_argument('--answers')
    add.add_argument('--session-file')
    args = parser.parse_args()
    try:
        if args.command == 'setup':
            answers = json.loads(Path(args.answers).read_text()) if args.answers else {}
            setup(Wizard(answers), args.config or 'data/config.yaml', args.edit)
            return
        if args.command == 'run' and os.environ.get('KEI_GATEWAY_ENABLED') == '0':
            print('keys-keys ' + VERSION + ': Discord gateway disabled.')
            return
        cfg = load_config(args.config, check=args.command not in ('migrate',))
        if args.command == 'doctor':
            results = asyncio.run(doctor_async(cfg, args.offline))
            if args.vision and (not args.offline):
                asyncio.run(vision_doctor(cfg, args.vision))
            if any((r['status'] == 'failed' for r in results)):
                raise SystemExit(1)
        elif args.command == 'server':
            answers = json.loads(Path(args.answers).read_text()) if args.answers else {}
            if args.session_file:
                answers.update(panel_auth='session', session_file=args.session_file)
            add_server(Wizard(answers), cfg, cfg['_path'], args.kind)
        elif args.command == 'migrate':
            from .store import Store
            database = Path(cfg['database'])
            stamp = str(int(time.time()))
            import sqlite3
            if database.exists():
                source = sqlite3.connect(database)
                dest = sqlite3.connect(str(database) + '.before-v3-' + stamp)
                source.backup(dest)
                dest.close()
                source.close()
                os.chmod(str(database) + '.before-v3-' + stamp, 384)
            db = Store(str(database))
            assert db.one('PRAGMA integrity_check')['integrity_check'] == 'ok'
            print('Schema 3 ready; legacy rows preserved. Backup created if database existed.')
        elif args.command == 'run':
            run(cfg)
    except (ValueError, RuntimeError, PermissionError, FileNotFoundError, KeyError, httpx.HTTPError, paramiko.SSHException, OSError) as exc:
        print('Setup chưa hoàn tất / Setup needs attention: ' + str(exc), file=sys.stderr)
        raise SystemExit(1)

async def vision_doctor(cfg, path):
    from ..v2.model import Model
    from ..v2.vision import image_mime, MAX_BYTES
    import base64
    raw = Path(path).read_bytes()
    mime = image_mime(raw)
    if not mime or len(raw) > MAX_BYTES:
        raise ValueError('JPEG/PNG/WebP <=8 MiB required')
    model = Model(cfg['provider_base'], cfg['provider_key'], cfg['provider_model'])
    try:
        response = await model.chat([{'role': 'user', 'content': [{'type': 'text', 'text': 'Describe only what you can see in this image; say if unreadable.'}, {'type': 'image_url', 'image_url': {'url': 'data:' + mime + ';base64,' + base64.b64encode(raw).decode()}}]}], max_tokens=400)
        print('VISION RESPONSE — inspect accuracy, HTTP acceptance alone is not proof:', response.get('content', ''))
    finally:
        await model.close()

def run(cfg):
    import logging
    from ..v2.model import Model
    from .store import Store
    from .application import Kei
    logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(name)s %(message)s')
    Path('data').mkdir(exist_ok=True)
    lock = open('data/runtime.lock', 'a+')
    try:
        if os.name == 'nt':
            import msvcrt
            lock.seek(0)
            lock.write('1')
            lock.flush()
            lock.seek(0)
            msvcrt.locking(lock.fileno(), msvcrt.LK_NBLCK, 1)
        else:
            import fcntl
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except OSError:
        raise RuntimeError('Bot đã chạy trong data directory này; không mở consumer thứ hai.')
    store = Store(cfg['database'])
    model = Model(cfg['provider_base'], cfg['provider_key'], cfg['provider_model'])
    bot = Kei(cfg, store, model)
    try:
        bot.run(cfg['discord_token'], log_handler=None)
    finally:
        lock.close()
if __name__ == '__main__':
    main()
