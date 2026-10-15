"""Panel client API or browser-derived session; no agent-generated UI clicks."""

from __future__ import annotations
import json, time
from pathlib import Path
from urllib.parse import unquote
import httpx
from .config import atomic


class Panel:
    def __init__(self, profile, secrets, session_dir="data/panel-sessions"):
        self.p = profile
        self.secrets = secrets
        self.url = profile["url"].rstrip("/")
        self.session_dir = Path(session_dir)
        import hashlib

        self.session_file = self.session_dir / (
            hashlib.sha256((self.url + str(profile.get("username", ""))).encode()).hexdigest()[:20]
            + ".json"
        )
        self.client = httpx.Client(
            base_url=self.url + "/",
            timeout=25,
            follow_redirects=True,
            headers={"Accept": "application/json", "User-Agent": "keys-keys/3"},
        )
        self.token = secrets.get(profile.get("token"))
        if self.token:
            self.client.headers["Authorization"] = "Bearer " + self.token
        elif self.session_file.exists():
            state = json.loads(self.session_file.read_text())
            for cookie in state.get("cookies", []):
                self.client.cookies.set(
                    cookie["name"],
                    cookie["value"],
                    domain=cookie.get("domain", ""),
                    path=cookie.get("path", "/"),
                )

    def close(self):
        self.client.close()

    def _csrf(self):
        cookie = next((c.value for c in self.client.cookies.jar if c.name == "XSRF-TOKEN"), None)
        if cookie:
            self.client.headers["X-XSRF-TOKEN"] = unquote(cookie)
        self.client.headers["Referer"] = self.url + "/"
        self.client.headers["Origin"] = self.url

    def login(self):
        user = self.p.get("username", "")
        password = self.secrets.get(self.p.get("password"))
        if not user or not password:
            raise PermissionError(
                "Panel cần API key hoặc account/password. Chạy keys-keys server add."
            )
        # Pterodactyl login supports HTTP. Pelican/JS forms use the optional browser.
        self.client.get("sanctum/csrf-cookie")
        self._csrf()
        r = self.client.post("auth/login", json={"user": user, "password": password})
        if r.status_code in (200, 204) and not ("complete" in r.text and "false" in r.text.lower()):
            check = self.client.get("api/client")
            if check.status_code == 200 and "data" in check.json():
                self._save_http()
                return
        try:
            from playwright.sync_api import sync_playwright
        except ImportError:
            raise RuntimeError(
                "Panel login cần JavaScript. Dùng image -browser hoặc pip install .[panel-login] rồi playwright install chromium."
            )
        with sync_playwright() as browser_runtime:
            browser = browser_runtime.chromium.launch(headless=True)
            try:
                context = browser.new_context()
                page = context.new_page()
                page.goto(self.url + "/login", wait_until="domcontentloaded")
                name = page.locator(
                    'input[type="email"], input[name="user"], input[name="email"], input[id$="email"], input[id$="user"]'
                ).first
                name.fill(user)
                page.locator('input[type="password"]').first.fill(password)
                page.locator('button[type="submit"]').first.click()
                page.wait_for_timeout(1800)
                if page.locator(
                    'input[autocomplete="one-time-code"], input[name="token"], iframe[src*="captcha"]'
                ).count():
                    raise PermissionError(
                        "Panel yêu cầu 2FA/captcha; cung cấp session đã xác thực bằng keys-keys server add --session-file. Không tắt 2FA."
                    )
                state = context.storage_state()
                atomic(self.session_file, json.dumps(state))
                self.client.cookies.clear()
                for cookie in state["cookies"]:
                    self.client.cookies.set(
                        cookie["name"],
                        cookie["value"],
                        domain=cookie.get("domain", ""),
                        path=cookie.get("path", "/"),
                    )
            finally:
                browser.close()
        self._csrf()
        r = self.client.get("api/client")
        if r.status_code != 200:
            raise PermissionError(
                "Đăng nhập Panel chưa hoàn tất; kiểm tra account/challenge/session."
            )

    def _save_http(self):
        atomic(
            self.session_file,
            json.dumps(
                {
                    "cookies": [
                        {"name": c.name, "value": c.value, "domain": c.domain, "path": c.path}
                        for c in self.client.cookies.jar
                    ]
                }
            ),
        )

    def request(self, method, path, body=None, **kwargs):
        if not self.token:
            self._csrf()
        r = self.client.request(method, "api/client/" + path.lstrip("/"), json=body, **kwargs)
        if r.status_code in (401, 419) and not self.token:
            self.login()
            self._csrf()
            r = self.client.request(method, "api/client/" + path.lstrip("/"), json=body, **kwargs)
        if r.status_code == 403 and ("cloudflare" in r.text.casefold() or "cf-ray" in r.headers):
            raise RuntimeError(
                "Panel gateway blocked this client request; credentials not established. Use an approved API hostname or reachable internal endpoint."
            )
        if r.status_code in (401, 403):
            raise PermissionError(
                "Panel không cấp quyền cho thao tác này (" + str(r.status_code) + ")."
            )
        r.raise_for_status()
        if not r.content:
            return {}
        return r.json() if "json" in r.headers.get("content-type", "") else {"text": r.text}

    def servers(self):
        rows = []
        page = 1
        while True:
            out = self.request("GET", "", params={"page": page})
            rows.extend(x.get("attributes", x) for x in out.get("data", []))
            if page >= out.get("meta", {}).get("pagination", {}).get("total_pages", 1):
                return rows
            page += 1

    def server(self, method, suffix="", body=None, **kwargs):
        return self.request(method, "servers/" + self.p["server"] + suffix, body, **kwargs)

    def read(self, path):
        out = self.server("GET", "/files/contents", params={"file": "/" + path})
        return out.get("text", out)

    def write(self, path, content):
        self._csrf()
        url = "api/client/servers/" + self.p["server"] + "/files/write"
        r = self.client.post(
            url,
            params={"file": "/" + path},
            content=content,
            headers={"Content-Type": "text/plain"},
        )
        if r.status_code in (401, 419) and not self.token:
            self.login()
            self._csrf()
            r = self.client.post(
                url,
                params={"file": "/" + path},
                content=content,
                headers={"Content-Type": "text/plain"},
            )
        r.raise_for_status()

    def upload(self, path, data, filename):
        signed = self.server("GET", "/files/upload")
        url = signed.get("attributes", signed).get("url")
        if not url:
            raise RuntimeError("Panel returned no upload URL")
        r = httpx.post(
            url,
            params={"directory": "/" + path.strip("/")},
            files={"files": (filename, data)},
            timeout=90,
        )
        r.raise_for_status()
