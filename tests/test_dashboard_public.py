"""Offline public-dashboard boundaries; synthetic identities only."""
from pathlib import Path
import re

from minecraft_agent.v3.web_ui import render_home

ASSETS = Path(__file__).parents[1] / 'src/minecraft_agent/v3/web_assets'


def test_public_ui_contains_dashboard_not_introduction():
    html = render_home('synthetic-nonce')
    for marker in ('class="hero', 'id="welcome"', 'id="project"', 'id="demo"',
                   'data-info', 'data-demo', 'data-example', 'playExample',
                   'exampleTimer', 'kei-spring', 'About Kei', 'About the project',
                   "Your server?", 'Sample conversation', 'Blue Archive',
                   'Who is Kei?', 'Her problem. Your server.'):
        assert marker not in html, marker
    assert 'id="settings"' in html
    assert 'data-login-link' in html
    assert not (ASSETS / 'kei-spring.jpg').exists()
    assert not (ASSETS / 'kei.png').exists()
    assert not re.search(r'\.hero|\.intro-grid|\.example-|\.bubble-|\.getting-started|\.feature-grid',
                         (ASSETS / 'dashboard.css').read_text('utf-8'))


def test_missing_oauth_login_stays_disabled_after_session_restore():
    html = render_home('nonce', auth_ready=False)
    assert 'Setup required: configure Discord OAuth' in html
    assert 'href="/login"' not in html
    script = (ASSETS / 'dashboard.js').read_text('utf-8')
    assert "if(el.getAttribute('href')==='/login')el.removeAttribute('aria-disabled')" in script


import asyncio
import json
import time
from types import SimpleNamespace
from urllib.parse import urlsplit, parse_qs

from aiohttp.test_utils import TestClient, TestServer
from minecraft_agent.v3.dashboard import Dashboard
from minecraft_agent.v3.store import Store


class OfflineOAuth:
    def __init__(self):
        self.calls = 0

    async def exchange(self, code, verifier):
        assert code == 'synthetic-code' and len(verifier) >= 43
        self.calls += 1
        return ({'id': '123', 'username': 'Synthetic'}, [],
                {'access_token': 'offline', 'refresh_token': 'offline-refresh',
                 'expires_at': time.time() + 3600})

    async def identity(self, token):
        return {'id': '123'}, []


def test_oauth_sessions_protected_routes_csrf_and_logout(tmp_path, monkeypatch):
    monkeypatch.delenv('DISCORD_CLIENT_SECRET', raising=False)

    async def exercise():
        db = Store(':memory:')
        oauth = OfflineOAuth()
        ux = SimpleNamespace(db=db, bot=SimpleNamespace(guilds=[]),
            cfg={'web': {'public_url': 'http://127.0.0.1', 'client_id': '123'},
                 'owner_id': '999', 'secrets_file': str(tmp_path / 'synthetic-secrets.json')},
            engine=SimpleNamespace(servers={}), access=SimpleNamespace(visible=lambda user: []),
            state=lambda user: {'servers': [], 'user': user},
            update=lambda user, body: {'saved': user})
        dashboard = Dashboard(ux, oauth=oauth)
        async with TestClient(TestServer(dashboard.app())) as client:
            home = await client.get('/')
            assert home.status == 200
            assert "script-src 'nonce-" in home.headers['Content-Security-Policy']
            for path in ('/api/state', '/api/profile', '/api/global/settings', '/api/tasks'):
                assert (await client.get(path)).status == 401
            assert (await client.post('/api/settings', json={})).status == 401
            assert (await client.get('/assets/kei-spring.jpg')).status == 404
            assert (await client.get('/assets/kei.png')).status == 404
            assert (await (await client.get('/api/session')).json())['signed_in'] is False
            assert (await client.get('/oauth/callback?code=synthetic-code&state=bad')).status == 403
            response = await client.get('/login', allow_redirects=False)
            query = parse_qs(urlsplit(response.headers['Location']).query)
            assert query['code_challenge_method'] == ['S256']
            assert response.cookies['kei_oauth']['httponly']
            callback = '/oauth/callback?code=synthetic-code&state=' + query['state'][0]
            assert (await client.get(callback, allow_redirects=False)).status == 302
            assert (await client.get(callback, allow_redirects=False)).status == 403
            assert oauth.calls == 1
            hint = await (await client.get('/api/session')).json()
            assert hint == {'signed_in': True, 'name': 'Synthetic'}
            state = await (await client.get('/api/state')).json()
            assert state['user'] == '123' and state['csrf']
            assert (await client.get('/api/global/settings')).status == 403
            assert (await client.post('/api/settings', json={})).status == 403
            headers = {'Origin': dashboard.origin, 'X-CSRF-Token': state['csrf']}
            assert (await client.post('/api/settings', json={}, headers={**headers, 'Origin': 'https://other.invalid'})).status == 403
            assert (await client.post('/api/settings', json={}, headers=headers)).status == 200
            assert (await client.post('/logout', json={}, headers=headers)).status == 200
            assert (await client.get('/api/state')).status == 401
            assert (await (await client.get('/api/session')).json())['signed_in'] is False
        db.db.close()

    asyncio.run(exercise())


def test_missing_oauth_server_reports_setup_required(tmp_path, monkeypatch):
    monkeypatch.delenv('DISCORD_CLIENT_SECRET', raising=False)

    async def exercise():
        db = Store(':memory:')
        ux = SimpleNamespace(db=db, bot=SimpleNamespace(), cfg={'web': {'public_url': 'http://127.0.0.1'},
            'secrets_file': str(tmp_path / 'missing-secrets.json')})
        async with TestClient(TestServer(Dashboard(ux).app())) as client:
            for path in ('/login', '/api/state', '/oauth/callback'):
                response = await client.get(path)
                assert response.status == 503
                assert 'configure Discord OAuth' in (await response.json())['error']
            assert 'Setup required' in await (await client.get('/')).text()
        db.db.close()

    asyncio.run(exercise())


import os
import shutil
import subprocess
import pytest


def test_chrome_dashboard_session_restore_has_no_dom_errors():
    """Optional real Chrome; all HTTP is intercepted, no Discord/network calls."""
    chrome = Path('C:/Program Files/Google/Chrome/Application/chrome.exe')
    playwright = Path(os.environ.get('KEI_PLAYWRIGHT_CORE',
        str(Path.home() / 'AppData/Local/hermes/cache/scratch/kei-dashboard42-dom/node_modules/playwright-core')))
    if not chrome.exists() or not playwright.exists() or not shutil.which('node'):
        pytest.skip('Optional Chrome/playwright-core not installed')
    script = r"""
const {chromium}=require(process.argv[1]);
let input='';process.stdin.setEncoding('utf8');process.stdin.on('data',x=>input+=x);
process.stdin.on('end',async()=>{
 const pages=JSON.parse(input); const browser=await chromium.launch({executablePath:process.argv[2],headless:true});
 try{
 for(const mode of ['anonymous','missing','signed-in']){
  const context=await browser.newContext();const page=await context.newPage();const errors=[];const requests=[];
  page.on('pageerror',e=>errors.push(e.message));
  await page.route('**/*',async route=>{
   const path=new URL(route.request().url()).pathname;requests.push(path);
   let body;
   if(path==='/')return route.fulfill({contentType:'text/html',body:pages[mode]});
   if(path==='/api/session')body={signed_in:mode==='signed-in',name:mode==='signed-in'?'Synthetic':null};
   else if(path==='/api/state')body={name:'Synthetic',csrf:'synthetic',servers:[],guilds:[],linked_accounts:[],preferences:{},persona:'auto',debug:'minimal',is_bot_owner:false};
   else if(path==='/api/profile')body={calibrated:false,dimensions:{},signals:[]};
   else if(path==='/api/memories')body={items:[],total:0,next_offset:null};
   else if(path==='/api/tasks')body={available:false,items:[]};
   else throw Error('Unexpected request '+path);
   return route.fulfill({contentType:'application/json',body:JSON.stringify(body)});
  });
  await page.goto('http://127.0.0.1/');await page.waitForFunction(()=>document.querySelector('#auth-loading').classList.contains('hidden'));
  if(mode==='signed-in'){
   if(!await page.locator('#settings').isVisible()||await page.locator('#login-shell').isVisible())throw Error('Dashboard visibility');
   for(const name of ['memory','minecraft','access','notifications','tasks','personal'])await page.locator('[data-tab="'+name+'"]').click();
   await page.locator('#start-setup').click();await page.locator('#setup-next').click();await page.locator('#setup-close').click();
  }else{
   if(!await page.locator('#login-shell').isVisible()||await page.locator('#settings').isVisible())throw Error('Login shell visibility');
   if(requests.some(p=>p!=='/'&&p!=='/api/session'))throw Error('Anonymous protected request');
  }
  if(mode==='missing'&&await page.locator('#login').getAttribute('aria-disabled')!=='true')throw Error('Setup login re-enabled');
  if(errors.length)throw Error(JSON.stringify(errors));
  console.log(mode+': no DOM/page errors');await context.close();
 }
 }finally{await browser.close();}
}).on('error',e=>{console.error(e);process.exitCode=1});
"""
    pages = {mode: render_home('synthetic-nonce', auth_ready=mode != 'missing')
             for mode in ('anonymous', 'missing', 'signed-in')}
    result = subprocess.run(['node', '-e', script, str(playwright), str(chrome)],
                            input=json.dumps(pages), text=True, capture_output=True, timeout=60)
    assert result.returncode == 0, result.stdout + result.stderr
    assert result.stdout.count('no DOM/page errors') == 3
