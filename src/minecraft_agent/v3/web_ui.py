"""Reusable, escaped presentation for the self-hosted dashboard; no credentials here."""

from __future__ import annotations

from html import escape
from pathlib import Path
import re
from urllib.parse import urlsplit

from . import VERSION

AVATAR = Path(__file__).with_name("web_assets") / "kei.png"
DEFAULT_BRANDING = {
    "name": "keys keys",
    "bot_name": "Kei",
    "deployment_label": "Self-hosted Minecraft copilot",
    "tagline": "Her problem. Your server.",
    "intro": 'A friend to chat with. A copilot to run Minecraft. One Kei who knows when to listen and when to get to work.',
    "repo_url": "https://github.com/TonyBucket/keys-keys",
    "community_url": "",
}


def branding(values=None):
    if values is None:
        values = {}
    if not isinstance(values, dict) or set(values) - set(DEFAULT_BRANDING):
        raise ValueError('web.branding contains unsupported fields; see docs/SETTINGS.md.')
    out = {**DEFAULT_BRANDING, **values}
    for key, limit in (
        ("name", 50),
        ("bot_name", 40),
        ("deployment_label", 80),
        ("tagline", 120),
        ("intro", 400),
    ):
        value = out[key]
        if (
            not isinstance(value, str)
            or not value.strip()
            or len(value) > limit
            or re.search(r"[\x00-\x1f\x7f]", value)
        ):
            raise ValueError("web.branding." + key + ' needs a short, valid piece of text.')
        out[key] = value.strip()
    for key in ("repo_url", "community_url"):
        value = out[key]
        if key == "community_url" and value == "":
            continue
        if not isinstance(value, str) or len(value) > 500:
            raise ValueError("web.branding." + key + ' requires an HTTPS URL.')
        parsed = urlsplit(value)
        if (
            parsed.scheme != "https"
            or not parsed.hostname
            or parsed.username
            or parsed.password
            or parsed.query
            or parsed.fragment
            or re.search(r"[\s\\]", value)
        ):
            raise ValueError("web.branding." + key + ' requires an HTTPS URL without credentials or query parameters.')
        if key == "community_url":
            host = parsed.hostname.casefold()
            path = parsed.path.rstrip("/")
            if not (
                (host == "discord.gg" and re.fullmatch(r"/[A-Za-z0-9-]{2,100}", path))
                or (
                    host in ("discord.com", "www.discord.com")
                    and re.fullmatch(r"/invite/[A-Za-z0-9-]{2,100}", path)
                )
            ):
                raise ValueError('community_url requires a real Discord invite link, or leave it blank.')
        out[key] = value
    return out


def render_home(nonce, values=None, auth_ready=True):
    chosen = branding(values)
    content = HTML
    for key, value in chosen.items():
        if key == "community_url":
            continue
        content = content.replace("__" + key.upper() + "__", escape(value, quote=True))
    community = (
        (
            '<a href="'
            + escape(chosen["community_url"], quote=True)
            + '" target="_blank" rel="noopener noreferrer">Community Discord <span aria-hidden="true">↗</span></a>'
        )
        if chosen["community_url"]
        else ""
    )
    content = content.replace("__COMMUNITY_LINK__", community)
    content = content.replace("__VERSION__", escape(VERSION)).replace(
        "__NONCE__", escape(nonce, quote=True)
    )
    if not auth_ready:
        content = content.replace(
            'href="/login" data-login-link',
            'href="#login-help" aria-disabled="true" data-login-link',
        )
        content = content.replace("__LOGIN_HELP_CLASS__", "notice notice-setup")
        content = content.replace("__LOGIN_STATE__", 'Discord login is not ready')
    else:
        content = content.replace("__LOGIN_HELP_CLASS__", "notice notice-setup hidden")
        content = content.replace("__LOGIN_STATE__", 'Log in with Discord')
    return content


_ASSETS = Path(__file__).with_name("web_assets")
HTML = (_ASSETS / "dashboard.html").read_text("utf-8").replace(
    "__STYLES__", (_ASSETS / "dashboard.css").read_text("utf-8")
).replace("__SCRIPT__", (_ASSETS / "dashboard.js").read_text("utf-8"))
