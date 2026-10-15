from __future__ import annotations
import copy, json, os, re, tempfile, threading
from pathlib import Path
from zoneinfo import ZoneInfo
import yaml
from dotenv import load_dotenv
DEFAULTS = {'timezone': 'Asia/Ho_Chi_Minh', 'database': 'data/kei.db', 'social': {'triggers': ['kei'], 'ambient': {'enabled': False, 'mode': 'whitelist', 'channels': []}, 'reply_cooldown': 120, 'followup_seconds': 90, 'ambient_interval': 60, 'context_messages': 10, 'dm_daily_limit': 3, 'dm_interval_hours': 4, 'quiet_start': 22, 'quiet_end': 8}, 'memory': {'retention_days': 90, 'cross_context': 'discreet', 'incremental_hours': 6, 'daily_hour': 4, 'recent_turns': 96, 'context_chars': 120000, 'memory_context_chars': 32000}, 'bridge': {'enabled': False, 'host': '0.0.0.0', 'port': 8767}, 'decisions': {'provider': 'off', 'min_confidence': 0.65, 'timeout': 8}, 'servers': [], 'assignments': {}}

def merge(base, extra):
    out = copy.deepcopy(base)
    for k, v in extra.items():
        out[k] = merge(out[k], v) if isinstance(v, dict) and isinstance(out.get(k), dict) else v
    return out

def atomic(path, content, mode=384):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(prefix='.' + path.name, dir=path.parent)
    try:
        with os.fdopen(fd, 'w', encoding='utf-8') as f:
            f.write(content)
        os.chmod(tmp, mode)
        os.replace(tmp, path)
    finally:
        if os.path.exists(tmp):
            os.unlink(tmp)

class Secrets:
    _locks = {}

    def __init__(self, path='data/secrets.json'):
        self.path = Path(path)

    def all(self):
        return json.loads(self.path.read_text()) if self.path.exists() else {}

    def put(self, name, value):
        if not re.fullmatch('[A-Za-z0-9_.-]+', name):
            raise ValueError('Invalid secret name')
        lock = self._locks.setdefault(str(self.path.resolve()), threading.RLock())
        with lock:
            data = self.all()
            data[name] = value
            atomic(self.path, json.dumps(data))
        return 'secret:' + name

    def get(self, ref, default=''):
        if not ref:
            return default
        if str(ref).startswith('secret:'):
            return self.all().get(str(ref)[7:], default)
        if str(ref).startswith('env:'):
            return os.environ.get(str(ref)[4:], default)
        return os.environ.get(str(ref), default)

def normalize_profile(p):
    p = copy.deepcopy(p)
    if 'host_admins' in p:
        admins = p['host_admins']
        if not isinstance(admins, list) or any((not str(user).isdigit() for user in admins)):
            raise ValueError('host_admins must be a list of Discord user IDs in operator config')
        p['host_admins'] = list(dict.fromkeys(map(str, admins)))
    p.setdefault('name', p.get('id', 'Server'))
    cs = p.setdefault('connectors', {})
    if p.get('wings_url'):
        cs.setdefault('wings', {'url': p['wings_url'], 'token': 'env:' + p['wings_token_env'], 'uuid': p['uuid']})
    if p.get('host') and p.get('ssh_user'):
        cs.setdefault('ssh', {'host': p['host'], 'user': p['ssh_user'], 'password': 'env:' + p.get('password_env', ''), 'known_hosts': p.get('known_hosts', 'known_hosts'), 'volume': p.get('volume'), 'file_owner': p.get('file_owner'), 'port': p.get('ssh_port', 22)})
    return p

def load_config(path=None, check=True):
    load_dotenv()
    load_dotenv('data/secrets.env', override=False)
    path = Path(path or os.environ.get('KEI_CONFIG') or ('data/config.yaml' if Path('data/config.yaml').exists() else 'kei.yaml'))
    if not path.is_file():
        raise RuntimeError('Chưa setup. Chạy: keys-keys setup / Not configured: run keys-keys setup')
    raw = yaml.safe_load(path.read_text(encoding='utf-8'))
    if not isinstance(raw, dict):
        raise ValueError('Config must be a YAML mapping')
    cfg = merge(DEFAULTS, raw)
    cfg['_path'] = str(path)
    cfg['owner_id'] = str(cfg.get('owner_id', ''))
    ZoneInfo(cfg['timezone'])
    secrets = Secrets(cfg.get('secrets_file', 'data/secrets.json'))
    cfg['discord_token'] = secrets.get(cfg.get('discord_token_ref', 'env:DISCORD_BOT_TOKEN'))
    cfg['provider_key'] = secrets.get(cfg.get('provider_key_ref', 'env:PROVIDER_API_KEY'))
    cfg['provider_model'] = cfg.get('provider_model') or os.environ.get('PROVIDER_MODEL', 'ag/gemini-3.8-flash-medium')
    cfg['servers'] = [normalize_profile(p) for p in cfg['servers']]
    prompt = Path(cfg.get('persona_file', 'data/persona.md'))
    cfg['persona'] = prompt.read_text(encoding='utf-8') if prompt.is_file() else ''
    cfg['persona_variants'] = {}
    for mode in ('auto', 'soft', 'spicy'):
        candidate = prompt.parent / ('persona-' + mode + '.md')
        if candidate.is_file() and candidate.read_text().strip():
            cfg['persona_variants'][mode] = candidate.read_text()
    if cfg['social']['ambient']['mode'] not in ('free', 'whitelist'):
        raise ValueError('ambient mode: free or whitelist')
    if cfg['memory']['cross_context'] not in ('strict', 'discreet'):
        raise ValueError('cross_context: strict or discreet')
    if check:
        missing = [k for k in ('discord_token', 'provider_key', 'provider_base', 'owner_id', 'persona') if not cfg.get(k)]
        if missing:
            raise RuntimeError('Thiếu / Missing ' + ', '.join(missing) + '. Chạy keys-keys setup để sửa từng bước.')
        if not cfg['owner_id'].isdigit():
            raise ValueError('owner_id must be your Discord user ID')
    return cfg

def save_config(cfg, path):
    public = {k: v for k, v in cfg.items() if k not in ('persona', 'persona_variants', 'discord_token', 'provider_key') and (not k.startswith('_'))}
    atomic(path, yaml.safe_dump(public, allow_unicode=True, sort_keys=False))
