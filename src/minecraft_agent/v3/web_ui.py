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
    "intro": "Một người bạn để trò chuyện. Một copilot để chăm Minecraft. Cùng một Kei, biết lúc nào nên nghe và lúc nào cần bắt tay vào việc.",
    "repo_url": "https://github.com/TonyBucket/keys-keys",
    "community_url": "",
}


def branding(values=None):
    if values is None:
        values = {}
    if not isinstance(values, dict) or set(values) - set(DEFAULT_BRANDING):
        raise ValueError("web.branding có trường chưa hỗ trợ; xem docs/SETTINGS.md.")
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
            raise ValueError("web.branding." + key + " cần một đoạn chữ ngắn, hợp lệ.")
        out[key] = value.strip()
    for key in ("repo_url", "community_url"):
        value = out[key]
        if key == "community_url" and value == "":
            continue
        if not isinstance(value, str) or len(value) > 500:
            raise ValueError("web.branding." + key + " cần URL HTTPS.")
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
            raise ValueError("web.branding." + key + " cần URL HTTPS không kèm credential/query.")
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
                raise ValueError("community_url cần link invite Discord thật, hoặc để trống.")
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
            + '" target="_blank" rel="noopener noreferrer">Discord cộng đồng <span aria-hidden="true">↗</span></a>'
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
        content = content.replace("__LOGIN_STATE__", "Discord login chưa sẵn sàng")
    else:
        content = content.replace("__LOGIN_HELP_CLASS__", "notice notice-setup hidden")
        content = content.replace("__LOGIN_STATE__", "Đăng nhập bằng Discord")
    return content


HTML = r"""<!doctype html>
<html lang="vi">
<head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="theme-color" content="#fbfafb"><meta name="description" content="__INTRO__">
<title>__NAME__ · Minecraft copilot & a little company</title>
<link rel="icon" href="/assets/kei.png" type="image/png">
<style nonce="__NONCE__">
:root{color-scheme:light;--page:#fbfafb;--paper:#fff;--ink:#252533;--body:#525363;--muted:#676979;--line:#e5e4eb;--silver:#f1f1f6;--pink:#fae8ee;--pink-line:#edc6d3;--red:#ae2048;--red-dark:#881334;--shadow:0 18px 60px #33324a0a;--radius:24px}*{box-sizing:border-box}html{scroll-behavior:smooth;scroll-padding-top:30px}body{margin:0;background:var(--page);color:var(--body);font:16px/1.65 ui-sans-serif,system-ui,-apple-system,"Segoe UI",sans-serif;-webkit-font-smoothing:antialiased}a{color:var(--red);text-underline-offset:4px}button,input,select,textarea{font:inherit}button,a,input,select,summary{touch-action:manipulation}button:focus-visible,a:focus-visible,input:focus-visible,select:focus-visible,summary:focus-visible{outline:3px solid #ae204877;outline-offset:4px}.wrap{width:min(1140px,calc(100% - 64px));margin-inline:auto}.site-header{min-height:112px;display:flex;align-items:center;justify-content:space-between;gap:24px;border-bottom:1px solid var(--line)}.brand{color:var(--ink);display:flex;align-items:center;gap:12px;text-decoration:none;min-width:0}.brand-mark{width:40px;height:40px;border:1px solid var(--pink-line);border-radius:13px;background:var(--pink);color:var(--red);display:grid;place-items:center;font-size:18px;font-weight:800;letter-spacing:-3px;padding-right:3px;flex-shrink:0}.brand strong{display:block;font-size:20px;line-height:1.3;letter-spacing:-.7px}.brand small{display:block;color:var(--muted);font-size:11px;letter-spacing:.03em;max-width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}.header-links,.header-actions,.actions{display:flex;align-items:center;gap:20px}.header-links a{text-decoration:none;font-size:14px;color:var(--body)}.header-links a:hover{color:var(--red)}.button,button{display:inline-flex;align-items:center;justify-content:center;gap:10px;min-height:44px;padding:10px 17px;border:1px solid var(--line);border-radius:12px;background:white;color:var(--ink);font-weight:600;text-decoration:none;font-size:14px;cursor:pointer;transition:background .18s,border-color .18s,transform .18s}.button:hover,button:hover{border-color:var(--pink-line);background:#fff8fa}.button.primary,button.primary{background:var(--red);border-color:var(--red);color:#fff;box-shadow:0 6px 18px #ae204818}.button.primary:hover,button.primary:hover{background:var(--red-dark)}.button[aria-disabled=true]{background:var(--silver);border-color:var(--line);color:var(--muted);box-shadow:none}.button.small{font-size:13px;padding:8px 13px}.arrow{font-size:19px;font-weight:400;line-height:1}.skip{position:fixed;z-index:20;left:16px;top:-70px;background:white;padding:12px}.skip:focus{top:12px}.hero{padding:66px 0 58px;display:grid;grid-template-columns:1.3fr 1fr;gap:68px;align-items:center}.eyebrow{display:flex;align-items:center;gap:9px;text-transform:uppercase;letter-spacing:.13em;font-size:11px;font-weight:750;color:var(--red);margin:0 0 19px}.eyebrow:before{content:"";height:6px;width:6px;border-radius:50%;background:currentColor}h1,h2,h3,p{margin-top:0}h1,h2,h3{color:var(--ink)}h1{font-size:clamp(42px,5.1vw,64px);font-weight:760;line-height:1.08;letter-spacing:-.055em;margin-bottom:23px}h1 .accent{color:var(--red)}.lead{font-size:17px;line-height:1.75;max-width:535px;margin-bottom:27px}.hero .actions{gap:12px;flex-wrap:wrap}.fine{font-size:12px;color:var(--muted);margin:14px 0 0}.portrait{position:relative;margin:0;max-width:370px;justify-self:end}.portrait:before{content:"";position:absolute;inset:22px -18px -18px 22px;border:1px solid var(--pink-line);border-radius:33px;background:var(--pink);z-index:0}.portrait img{display:block;width:100%;height:auto;aspect-ratio:1;object-fit:cover;position:relative;border-radius:28px;border:7px solid white;box-shadow:var(--shadow)}.portrait figcaption{position:absolute;z-index:1;bottom:19px;left:-23px;background:#fffffff5;border:1px solid var(--line);padding:10px 15px;border-radius:12px;box-shadow:0 10px 30px #24243a0d;color:var(--ink);font-size:12px;line-height:1.5}.portrait figcaption strong{display:block;color:var(--red);font-size:10px;text-transform:uppercase;letter-spacing:.1em}.section{padding:40px 0}.intro-grid{display:grid;grid-template-columns:1fr 1fr;gap:56px;border-top:1px solid var(--line);border-bottom:1px solid var(--line);padding:31px 0 30px}.section-label{font-size:11px;text-transform:uppercase;letter-spacing:.12em;color:var(--red);margin-bottom:9px;font-weight:750}h2{font-size:26px;line-height:1.3;font-weight:710;letter-spacing:-.035em;margin-bottom:14px}h3{font-size:17px;letter-spacing:-.015em;margin-bottom:8px}.intro-grid p{font-size:14px;line-height:1.8;margin:0;max-width:480px}.example-layout{display:grid;grid-template-columns:.9fr 1.1fr;gap:60px;align-items:center;padding:20px 0 34px}.example-copy p{font-size:14px;max-width:370px}.example-tabs{display:flex;gap:7px;flex-wrap:wrap;margin:22px 0 0}.example-tabs button{font-size:12px;min-height:36px;padding:7px 12px;border-radius:100px;background:transparent}.example-tabs button[aria-selected=true]{background:var(--pink);color:var(--red);border-color:var(--pink-line)}.conversation{background:var(--paper);border:1px solid var(--line);border-radius:var(--radius);box-shadow:var(--shadow);padding:25px}.conversation-header{display:flex;align-items:center;gap:11px;padding-bottom:18px;border-bottom:1px solid var(--line);font-size:13px;color:var(--ink)}.conversation-header img{width:35px;height:35px;border-radius:12px;object-fit:cover}.conversation-header small{color:var(--muted);display:block;font-size:11px}.bubble-user{background:var(--silver);border-radius:13px 13px 3px 13px;padding:12px 15px;margin:20px 0 15px 48px;color:var(--ink);font-size:14px}.bubble-bot{background:var(--pink);border:1px solid #f1d7e0;border-radius:13px 13px 13px 3px;padding:13px 15px;margin-right:24px;color:#632f40;font-size:14px}.example-note{font-size:11px;margin:15px 0 0;color:var(--muted)}.getting-started{display:flex;justify-content:space-between;align-items:center;gap:30px;padding:26px 30px;border:1px solid var(--pink-line);border-radius:20px;background:#fff7fa;margin:12px 0 32px}.getting-started h3{margin-bottom:4px}.getting-started p{font-size:13px;margin:0}.command{font:12px ui-monospace,SFMono-Regular,Consolas,monospace;background:#fff;border:1px solid var(--line);padding:3px 6px;border-radius:5px;color:var(--ink);white-space:nowrap}.site-footer{padding:26px 0 33px;border-top:1px solid var(--line);display:flex;justify-content:space-between;gap:22px;align-items:start;font-size:11px;color:var(--muted)}.footer-links{display:flex;gap:18px;flex-wrap:wrap}.footer-links a{color:var(--body)}.site-footer p{margin:0}.notice{margin-top:22px;padding:14px 18px;border-radius:13px;border:1px solid var(--pink-line);background:var(--pink);font-size:13px;white-space:pre-line;color:#6f3044}.notice-setup{background:#fff5e9;border-color:#ead7bd;color:#73532a}.hidden{display:none!important}.dashboard-heading{padding:43px 0 26px;display:flex;justify-content:space-between;align-items:end;gap:24px}.dashboard-heading h1{font-size:36px;margin:0 0 7px;letter-spacing:-.04em}.dashboard-heading p{font-size:14px;margin:0}.count-badge{border:1px solid var(--line);background:white;border-radius:100px;padding:7px 13px;font-size:12px;white-space:nowrap}.dashboard-tabs{display:flex;gap:6px;border-bottom:1px solid var(--line);overflow:auto;margin-bottom:25px;padding-bottom:10px;scrollbar-width:thin}.dashboard-tabs button{background:transparent;border-color:transparent;border-radius:9px;white-space:nowrap;font-size:13px;padding:8px 13px;min-height:40px}.dashboard-tabs button[aria-selected=true]{background:var(--pink);color:var(--red);border-color:var(--pink-line)}.panel-grid{display:grid;grid-template-columns:1fr 1fr;gap:20px;margin-bottom:25px}.card{padding:25px;border:1px solid var(--line);border-radius:21px;background:white;box-shadow:var(--shadow);min-width:0}.card h2{font-size:20px;margin-bottom:6px}.card .description{font-size:13px;color:var(--muted);margin:0 0 20px}.wide{grid-column:1/-1}.form-grid{display:grid;grid-template-columns:1fr 1fr;gap:0 18px}.field{min-width:0;margin-bottom:17px}.field:last-child{margin-bottom:0}label{display:block;margin:0 0 6px;color:var(--ink);font-size:13px;font-weight:600}input,select,textarea{display:block;width:100%;max-width:100%;border:1px solid #deddE6;border-radius:10px;background:#fdfdff;color:var(--ink);padding:10px 11px;min-height:44px;font-size:14px}input::placeholder{color:#9291a0}input:focus,select:focus,textarea:focus{border-color:var(--red);background:#fff}input:disabled,select:disabled,button:disabled{opacity:.55;cursor:default}small,.hint{font-size:11px;color:var(--muted)}.hint{display:block;margin-top:6px}.save-row{display:flex;align-items:center;justify-content:space-between;gap:20px;background:white;border:1px solid var(--line);border-radius:15px;padding:13px 18px;margin-bottom:28px}.save-row p{font-size:12px;margin:0}.button-row{display:flex;gap:8px;flex-wrap:wrap;margin-top:18px}.button-row button{font-size:12px;min-height:39px;padding:8px 12px}button.danger{color:#a42043;background:white;border-color:#ecc7d2}button.danger:hover{background:#fff1f5}.item{padding:15px 0;border-bottom:1px solid var(--line);font-size:13px;overflow-wrap:anywhere;white-space:pre-line}.item:last-child{border-bottom:0}.item-title{font-size:15px;color:var(--ink);font-weight:700;margin:0 0 4px}.item-meta{font-size:11px;color:var(--muted);margin:0}.item-actions{display:flex;gap:7px;flex-wrap:wrap;margin-top:10px}.item-actions button{font-size:11px;min-height:34px;padding:6px 10px}.stats{display:grid;grid-template-columns:1fr 1fr;gap:14px;margin:25px 0}.stat-label{display:flex;justify-content:space-between;font-size:11px;color:var(--body);margin-bottom:4px}meter{width:100%;height:6px;display:block;border:0;background:var(--silver);border-radius:10px}meter::-webkit-meter-bar{background:var(--silver);border:0;border-radius:10px}meter::-webkit-meter-optimum-value{background:#c95f7d;border-radius:10px}meter::-moz-meter-bar{background:#c95f7d;border-radius:10px}.rank{display:inline-block;color:var(--red);border:1px solid var(--pink-line);border-radius:100px;background:var(--pink);padding:5px 12px;font-size:12px;font-weight:700}.profile-heading{display:flex;gap:15px;align-items:center}.profile-heading img{width:60px;height:60px;border-radius:18px;object-fit:cover}.profile-heading h2{margin:0 0 6px}.empty{padding:22px;border:1px dashed var(--line);border-radius:14px;color:var(--muted);font-size:13px;background:#fcfbfd}.account-code{font-family:ui-monospace,Consolas,monospace;font-size:14px;white-space:pre-wrap;color:var(--red);overflow-wrap:anywhere}.capabilities{display:flex;flex-wrap:wrap;gap:5px;margin-top:10px}.capability{background:var(--silver);border-radius:6px;padding:3px 7px;font-size:10px;color:#5e6070}.fade-in{animation:rise .55s ease-out both}@keyframes rise{from{opacity:0;transform:translateY(12px)}to{opacity:1;transform:translateY(0)}}.noscript{padding:16px;color:var(--red)}
@media(min-width:1280px){.hero{padding-top:77px;padding-bottom:72px}}@media(max-width:900px){.header-links{display:none}.hero{gap:35px;padding-top:43px}.portrait{max-width:310px}.hero h1{font-size:49px}.lead{font-size:15px}.intro-grid{gap:30px}.example-layout{gap:30px}.panel-grid{gap:15px}.card{padding:21px}}@media(max-width:650px){.wrap{width:calc(100% - 36px)}.site-header{min-height:90px;gap:12px}.brand small{max-width:155px;font-size:9px}.brand strong{font-size:18px}.brand-mark{width:33px;height:33px;border-radius:10px;font-size:15px}.brand{gap:9px}.header-actions{gap:6px}.header-actions .button{font-size:11px;padding:8px 10px;min-height:39px}.header-actions .arrow{display:none}.hero{grid-template-columns:1fr;gap:33px;padding:34px 0 41px}.hero h1{font-size:47px;max-width:450px}.eyebrow{font-size:10px;margin-bottom:15px}.lead{max-width:490px;font-size:15px;margin-bottom:20px}.portrait{width:240px;max-width:72%;justify-self:center;margin-right:14px}.portrait img{border-radius:24px;border-width:5px}.portrait:before{inset:14px -12px -12px 14px;border-radius:27px}.portrait figcaption{left:-18px;bottom:13px;padding:8px 12px;font-size:10px}.portrait figcaption strong{font-size:9px}.intro-grid{grid-template-columns:1fr;gap:24px;padding:27px 0}.intro-grid p{font-size:13px}.section{padding:26px 0}.section h2{font-size:25px}.example-layout{grid-template-columns:1fr;gap:24px;padding-bottom:14px}.example-copy p{max-width:none}.example-tabs{margin-top:16px}.conversation{padding:20px}.getting-started{align-items:start;flex-direction:column;gap:14px;padding:21px;margin-top:8px}.getting-started .button{font-size:12px}.site-footer{flex-direction:column;gap:14px;padding-top:21px}.dashboard-heading{padding:28px 0 20px;align-items:start;flex-direction:column;gap:13px}.dashboard-heading h1{font-size:30px}.dashboard-tabs{gap:1px}.dashboard-tabs button{font-size:12px;padding:7px 11px}.panel-grid{grid-template-columns:1fr}.card{padding:20px;border-radius:18px}.form-grid{grid-template-columns:1fr}.save-row{align-items:start;padding:13px;gap:12px}.save-row p{font-size:11px}.save-row button{white-space:nowrap;padding-inline:12px;font-size:12px}.stats{gap:12px}.notice{margin-top:16px;font-size:12px}.bubble-user{margin-left:24px}.bubble-bot{margin-right:10px}}@media(max-width:370px){.brand small{max-width:110px}.hero h1{font-size:42px}.header-actions .button{font-size:10px;padding:7px 8px}.brand-mark{display:none}}@media(prefers-reduced-motion:reduce){html{scroll-behavior:auto}*,*:before,*:after{animation:none!important;transition:none!important}}
</style>
</head>
<body>
<a class="skip" href="#main">Đến nội dung</a>
<header class="site-header wrap">
 <a href="/" class="brand" aria-label="__NAME__ trang chủ"><span class="brand-mark" aria-hidden="true">kk</span><span><strong>__NAME__</strong><small>__DEPLOYMENT_LABEL__</small></span></a>
 <nav class="header-links" aria-label="Dự án"><a href="#project">Kei là gì?</a><a href="__REPO_URL__" target="_blank" rel="noopener noreferrer">GitHub <span aria-hidden="true">↗</span></a>__COMMUNITY_LINK__</nav>
 <div class="header-actions"><a id="login" class="button primary small" href="/login" data-login-link>Đăng nhập Discord <span class="arrow" aria-hidden="true">↗</span></a><button id="logout" class="hidden">Đăng xuất</button></div>
</header>
<main id="main" class="wrap">
<div id="status" class="notice hidden" role="status" aria-live="polite"></div>
<div id="login-help" class="__LOGIN_HELP_CLASS__" role="status"><strong>Discord login chưa sẵn sàng.</strong> Operator cần hoàn tất cấu hình OAuth. Bạn vẫn có thể dùng <span class="command">/setup</span> và <span class="command">/settings</span> trong Discord.</div>
<div id="welcome">
 <section class="hero">
  <div class="fade-in"><p class="eyebrow">Minecraft copilot. Có cả tính cách.</p><h1>Server của bạn.<br><span class="accent">Để __BOT_NAME__ lo cùng.</span></h1><p class="lead">__INTRO__</p><div class="actions"><a class="button primary" href="/login" data-login-link>Mở không gian của bạn <span class="arrow" aria-hidden="true">→</span></a><a class="button" href="#project">Kei là gì?</a></div><p class="fine">__LOGIN_STATE__ · Thiết lập, memory và server được phép của riêng bạn.</p></div>
  <figure class="portrait fade-in"><img src="/assets/kei.png" alt="__BOT_NAME__, chỉnh kính và nhìn bạn đầy phán xét" width="400" height="400" fetchpriority="high"><figcaption><strong>__BOT_NAME__ · server copilot</strong>__TAGLINE__</figcaption></figure>
 </section>
 <section id="project" class="intro-grid" aria-label="Dự án này là gì và vì sao tồn tại">
  <div><p class="section-label">01 / What is this?</p><h2>Chat được. Làm việc cũng được.</h2><p>__NAME__ là một chatbot Discord kiêm Minecraft copilot có thể tự host. Bạn trò chuyện trong DM hoặc kênh chung; khi cần, nhờ đọc log, xem trạng thái hoặc xử lý việc trên server đã được cấp quyền.</p></div>
  <div><p class="section-label">02 / Why does it exist?</p><h2>Đỡ đổi tab. Đỡ phải đoán.</h2><p>Vì chat không cần biến thành một ca trực kỹ thuật, còn “check server giúp mình” cần kết quả thật. __BOT_NAME__ giữ mạch trò chuyện và những chuyện đáng nhớ, rồi đi kiểm tra, làm việc và báo bằng chứng khi được nhờ.</p></div>
 </section>
 <section class="section example-layout" aria-labelledby="examples-title">
  <div class="example-copy"><p class="section-label">Cùng một Kei, đúng việc đúng lúc</p><h2 id="examples-title">Không phải câu nào<br>cũng cần mở console.</h2><p>Chọn một ví dụ để xem hai kiểu trò chuyện khác nhau. Đây là minh họa; không gửi tin hay chạy lệnh thật.</p><div class="example-tabs" role="tablist" aria-label="Ví dụ"><button role="tab" aria-selected="true" data-example="chat">Tán gẫu</button><button role="tab" aria-selected="false" data-example="work">Nhờ việc</button><button role="tab" aria-selected="false" data-example="schedule">Hẹn giờ</button></div></div>
  <div class="conversation"><div class="conversation-header"><img src="/assets/kei.png" alt="" width="35" height="35" loading="lazy"><span><strong>__BOT_NAME__</strong><small>Ví dụ hội thoại</small></span></div><div id="example-user" class="bubble-user">Kei, hôm nay mình hơi mệt.</div><div id="example-bot" class="bubble-bot" aria-live="polite">Vậy nghỉ một chút đã. Có chuyện gì thì kể mình nghe.</div><p id="example-note" class="example-note">Chat thường đi đường nhẹ. Không tự gọi công cụ quản lý server.</p></div>
 </section>
 <section class="getting-started"><div><h3>Bắt đầu từ hai lệnh thôi.</h3><p><span class="command">/setup</span> để làm quen. <span class="command">/settings</span> để chỉnh lại. Không cần có Minecraft server để chat.</p></div><a class="button" href="__REPO_URL__" target="_blank" rel="noopener noreferrer">Tự host & hướng dẫn <span aria-hidden="true">↗</span></a></section>
</div>
<div id="settings" class="hidden">
 <div class="dashboard-heading"><div><p class="eyebrow">Không gian của bạn</p><h1>Chào, <span id="name"></span>.</h1><p>Chỉnh cách Kei trò chuyện, những gì được nhớ và server bạn quản lý.</p></div><span class="count-badge" id="server-count"></span></div>
 <nav class="dashboard-tabs" role="tablist" aria-label="Thiết lập"><button id="tab-personal" role="tab" aria-selected="true" aria-controls="panel-personal" data-tab="personal">Cá nhân</button><button id="tab-memory" role="tab" aria-selected="false" aria-controls="panel-memory" data-tab="memory" tabindex="-1">Quan hệ & memory</button><button id="tab-minecraft" role="tab" aria-selected="false" aria-controls="panel-minecraft" data-tab="minecraft" tabindex="-1">Minecraft</button><button id="tab-tasks" role="tab" aria-selected="false" aria-controls="panel-tasks" data-tab="tasks" tabindex="-1">Lịch hẹn</button></nav>
 <section id="panel-personal" class="dashboard-panel" role="tabpanel" aria-labelledby="tab-personal">
  <div class="panel-grid"><div class="card"><h2>Đúng gu của bạn</h2><p class="description">Cách nói chuyện và mức hiển thị khi Kei làm việc.</p><div class="field"><label for="persona">Tính cách</label><select id="persona"><option value="auto">Linh hoạt theo cuộc trò chuyện</option><option value="soft">Dịu hơn</option><option value="spicy">Đậm vị hơn</option></select></div><div class="field"><label for="debug">Tiến độ công việc</label><select id="debug"><option value="off">Ẩn tiến độ</option><option value="minimal">Chỉ checklist ngắn</option><option value="advanced">Checklist + lệnh và log</option></select></div><div class="field"><label for="timezone">Múi giờ</label><input id="timezone" value="Asia/Ho_Chi_Minh" autocomplete="off"><span class="hint">Giờ yên lặng và lịch hẹn dùng múi giờ này.</span></div></div>
  <div class="card"><h2>Gần gũi, có chừng mực</h2><p class="description">Bạn quyết định khi nào muốn nghe Kei và chuyện nào được gợi nhắc.</p><div class="field"><label for="dm">Chủ động nhắn DM</label><select id="dm"><option value="false">Tắt</option><option value="true">Cho phép, có giờ yên lặng</option></select></div><div class="field"><label for="muted">Tham gia trò chuyện với bạn</label><select id="muted"><option value="false">Bình thường</option><option value="true">Để mình yên một chút</option></select><span class="hint">Không chặn công việc hợp lệ đã được giao.</span></div><div class="field"><label for="sharing">Memory giữa các ngữ cảnh</label><select id="sharing"><option value="strict">Chỉ nơi đã nói</option><option value="discreet">Được gợi nhắc kín đáo</option></select><span class="hint">Không quote DM riêng ra kênh chung.</span></div><div class="field"><label for="rank">Thông báo khi quan hệ thay đổi</label><select id="rank"><option value="true">Hiện ngắn gọn</option><option value="false">Tắt</option></select></div></div></div>
  <div class="save-row"><p>Lưu riêng cho bạn. Không cần khởi động lại bot.</p><button id="save" class="primary">Lưu thay đổi</button></div>
 </section>
 <section id="panel-memory" class="dashboard-panel hidden" role="tabpanel" aria-labelledby="tab-memory"><div class="panel-grid"><div class="card"><div class="profile-heading"><img src="/assets/kei.png" alt="" width="60" height="60"><div><h2>__BOT_NAME__ ↔ Bạn</h2><span id="relationship-rank" class="rank">Đang đọc…</span></div></div><p id="relationship" class="description"></p><div id="dimensions" class="stats"></div><small>Quan hệ thân thiết không thay thế quyền quản lý server.</small></div><div class="card"><h2>Chuyện chung đáng nhớ</h2><p class="description">Những episode đã chọn lưu trong DM của bạn.</p><div id="memories"></div><div class="button-row"><button id="forget" class="danger">Quên memory trong DM</button><button id="forget-all" class="danger">Quên dữ liệu của mình</button></div><span class="hint">Kei cũng xóa phần dẫn xuất liên quan. Mỗi thao tác sẽ hỏi xác nhận.</span></div></div></section>
 <section id="panel-minecraft" class="dashboard-panel hidden" role="tabpanel" aria-labelledby="tab-minecraft"><div class="panel-grid"><div class="card wide"><h2>Minecraft của bạn</h2><p class="description">Chỉ hiện server bạn được phép dùng. Chọn đúng nơi trước khi nhờ việc.</p><div class="form-grid"><div class="field"><label for="default-server">Server mặc định cho DM</label><select id="default-server"></select></div><div class="field"><label>&nbsp;</label><button id="default-save">Lưu server mặc định</button></div></div><div id="servers"></div></div>
  <div class="card"><h2>Tài khoản Minecraft</h2><p class="description">Nối Discord với nhân vật trong game, không tự cấp thêm quyền.</p><div id="accounts"></div><div class="button-row"><button id="link">Tạo mã link</button><button id="unlink" class="danger">Gỡ link</button></div><p id="link-code" class="account-code" aria-live="polite"></p><span class="hint">Login Minecraft rồi nhập mã. Cần plugin Kei đang kết nối trên server.</span></div>
  <div id="connect-card" class="card hidden"><h2>Kết nối server</h2><p class="description">Dùng account Panel thật sự có quyền server.</p><div class="field"><label for="panel-url">Panel URL</label><input id="panel-url" type="url" placeholder="https://panel.example.com"></div><div class="field"><label for="panel-key">Client API key</label><input id="panel-key" type="password" autocomplete="off"><span class="hint">Trong Pterodactyl/Pelican: Account → API Credentials.</span></div><button id="preview">Kiểm tra kết nối</button><div id="candidate" class="hidden"><div class="field"><label for="candidate-server">Server từ Panel</label><select id="candidate-server"></select></div><div class="field"><label for="candidate-guild">Gắn với guild (tùy chọn)</label><select id="candidate-guild"><option value="">Chưa gắn guild</option></select></div><button id="commit" class="primary">Kết nối server này</button></div><span class="hint">Key giữ phía bot, không đưa cho model. SSH và local setup vẫn có trong CLI.</span></div>
  <div id="access-card" class="card wide hidden"><h2>Ai được làm gì?</h2><p class="description">Cấp quyền theo đúng server. Owner có thể bổ nhiệm và gỡ admin.</p><div class="form-grid"><div class="field"><label for="access-server">Server</label><select id="access-server"></select></div><div class="field"><label for="subject">Discord user ID</label><input id="subject" inputmode="numeric" autocomplete="off"></div><div class="field"><label for="action">Thao tác</label><select id="action"><option value="grant">Cấp quyền</option><option value="revoke">Thu hồi quyền</option><option value="admin">Bổ nhiệm admin (owner)</option><option value="unadmin">Gỡ admin (owner)</option></select></div><div class="field"><label for="level">Phạm vi</label><select id="level"><option value="observe">Chỉ xem server</option><option value="copilot">Thao tác được phép</option><option value="chat">Chỉ trò chuyện</option></select></div></div><button id="access-save">Lưu phân quyền</button><span class="hint">Admin chỉ quản lý server được giao. Người cấp và phạm vi được ghi lại.</span></div></div>
 </section>
 <section id="panel-tasks" class="dashboard-panel hidden" role="tabpanel" aria-labelledby="tab-tasks"><div id="tasks-card" class="panel-grid hidden"><div class="card"><h2>Lịch hẹn của bạn</h2><p class="description">Lịch mới hoặc sửa lịch cần bấm 🕒 xác nhận. Kết quả gửi về Discord DM.</p><div id="tasks-list"></div></div><div class="card"><h2 id="task-form-title">Hẹn Kei một việc</h2><p class="description" id="task-timezone"></p><div class="field"><label for="task-goal">Việc hoặc lời nhắc</label><input id="task-goal" maxlength="1000" placeholder="Nhắc mình đi ngủ / kiểm tra TPS"></div><div class="field"><label for="task-when">Khi nào?</label><input id="task-when" placeholder="ngày mai 07:00 / mỗi ngày 07:00"></div><div class="field"><label for="task-mode">Loại việc</label><select id="task-mode"><option value="alarm">Lời nhắc</option><option value="observe">Kiểm tra server (chỉ xem)</option><option value="change">Làm việc được phép trên server</option></select></div><div class="field"><label for="task-server">Server</label><select id="task-server"><option value="">Không cần server</option></select></div><div class="button-row"><button id="task-save" class="primary">Đề xuất lịch</button><button id="task-reset">Tạo lịch mới</button></div><span class="hint">Mỗi lần chạy vẫn kiểm quyền; lịch hẹn không bỏ qua xác nhận cho thao tác nguy hiểm.</span></div></div><p id="tasks-unavailable" class="empty hidden">Lịch hẹn chưa sẵn sàng ở deployment này. Những tác vụ đang chạy vẫn được giữ nguyên.</p></section>
</div>
<noscript><p class="noscript">Bật JavaScript để dùng dashboard. Bạn vẫn dùng /setup và /settings trong Discord được.</p></noscript>
</main>
<footer class="site-footer wrap"><div><p><strong>__NAME__</strong> · Supernova __VERSION__</p><p>Code MIT · Tendou Kei fan artwork: Manic-san.</p></div><nav class="footer-links" aria-label="Liên kết"><a href="__REPO_URL__" target="_blank" rel="noopener noreferrer">Mã nguồn & hướng dẫn ↗</a>__COMMUNITY_LINK__</nav></footer>
<script nonce="__NONCE__">
'use strict';
let state=null,candidate=null,editingTask=null;
const $=id=>document.getElementById(id);
const empty=(parent,text)=>{const el=document.createElement('p');el.className='empty';el.textContent=text;parent.append(el);};
function note(text){$('status').textContent=text;$('status').classList.remove('hidden');}
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
const examples={chat:['Kei, hôm nay mình hơi mệt.','Vậy nghỉ một chút đã. Có chuyện gì thì kể mình nghe.','Chat thường đi đường nhẹ. Không tự gọi công cụ quản lý server.'],work:['Kei, kiểm tra TPS server giúp mình.','Mình đọc số liệu thật rồi báo lại. Nếu thấy vấn đề, mình sẽ nói rõ đã kiểm tra được gì.','Công việc cần quyền đúng server, tiến độ và bằng chứng; không đoán là đã làm xong.'],schedule:['Mai 07:00 nhắc mình kiểm tra backup nhé.','Được. Lịch đang chờ bạn xác nhận 🕒 rồi mới bật.','Lịch hẹn dùng múi giờ của bạn. Có thể xem, sửa, tạm dừng và hủy.']};
document.querySelectorAll('[data-example]').forEach(button=>{button.onclick=()=>{const sample=examples[button.dataset.example];document.querySelectorAll('[data-example]').forEach(b=>b.setAttribute('aria-selected',String(b===button)));$('example-user').textContent=sample[0];$('example-bot').textContent=sample[1];$('example-note').textContent=sample[2];};});
const capabilities={status:'Trạng thái',console:'Console',power:'Bật / tắt',files:'Tệp',plugins:'Plugin',plugin_install:'Cài plugin',logs:'Log',profiler:'Profiler',tps:'TPS',players:'Người chơi',host:'Máy chủ',remote_shell:'SSH',web_search:'Tìm trên web',fetch_url:'Đọc trang',plugin_search:'Tìm plugin',health:'Sức khỏe server'};
function renderServers(){
 $('servers').replaceChildren();$('default-server').replaceChildren();$('access-server').replaceChildren();$('task-server').replaceChildren();option($('task-server'),'','Không cần server');
 for(const server of state.servers){
  option($('default-server'),server.id,server.name);option($('task-server'),server.id,server.name);
  const row=block($('servers'),'');block(row,server.name,'item-title');block(row,server.level==='copilot'?'Được nhờ thao tác':server.level==='observe'?'Chỉ xem':'Chỉ trò chuyện','item-meta');
  const caps=block(row,'','capabilities');for(const cap of server.capabilities)block(caps,capabilities[cap]||cap,'capability');
  const controls=block(row,'','item-actions');action(controls,'Kiểm tra kết nối',async()=>{note('Đang kiểm tra '+server.name+'…');const result=await api('/api/server/test',{server:server.id});note(result.message);});
  if(server.manage_access){option($('access-server'),server.id,server.name);for(const grant of server.grants||[])block(row,grant.subject+' · '+grant.level+(grant.admin?' + admin':'')+' · cấp bởi '+grant.issuer,'item-meta');}
 }
 if(!state.servers.length)empty($('servers'),'Chưa có server được phân công. Bạn vẫn trò chuyện với Kei bình thường được.');
 $('default-server').disabled=!state.servers.length;$('default-save').disabled=!state.servers.length;
 if(state.default_server)$('default-server').value=state.default_server;
 $('server-count').textContent=state.servers.length+' server được phép';
 $('connect-card').classList.toggle('hidden',!state.can_connect);$('access-card').classList.toggle('hidden',!state.servers.some(server=>server.manage_access));
 $('candidate-guild').replaceChildren();option($('candidate-guild'),'','Chưa gắn guild');for(const guild of state.guilds.filter(g=>g.manage_guild))option($('candidate-guild'),guild.id,guild.name);
 updateTaskMode();
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
 $('memories').replaceChildren();for(const memory of(profile.memories||[]).slice(0,5)){const row=block($('memories'),'');block(row,friendlyMemoryTitle(memory.title),'item-title');if(memory.summary)block(row,memory.summary,'');}
 if(!profile.memories?.length)empty($('memories'),'Chưa có episode đã chọn lưu ở đây. Những chuyện đáng nhớ sẽ xuất hiện theo thời gian.');
}
async function load(){
 state=await api('/api/state');$('name').textContent=state.name;document.querySelectorAll('[data-login-link]').forEach(link=>link.classList.add('hidden'));$('logout').classList.remove('hidden');$('welcome').classList.add('hidden');$('login-help').classList.add('hidden');$('settings').classList.remove('hidden');document.querySelector('.header-links').classList.add('hidden');
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
$('save').onclick=run(async()=>{await api('/api/settings',{persona:$('persona').value,debug:$('debug').value,timezone:$('timezone').value,dm_opt_in:$('dm').value==='true',muted:$('muted').value==='true',sharing:$('sharing').value,rank_notifications:$('rank').value==='true'});await load();note('Đã lưu thiết lập của bạn.');});
$('default-save').onclick=run(async()=>{await api('/api/settings',{default_server:$('default-server').value});note('Đã lưu server mặc định cho DM.');});
$('link').onclick=run(async()=>{const result=await api('/api/link',{});$('link-code').textContent=result.command+' · hết hạn sau 10 phút.';});
$('unlink').onclick=run(async()=>{if(confirm('Gỡ các liên kết Minecraft của bạn?')){await api('/api/unlink',{});await load();note('Đã gỡ link.');}});
for(const[id,all]of[['forget',false],['forget-all',true]])$(id).onclick=run(async()=>{if(confirm(all?'Quên toàn bộ dữ liệu của bạn ở mọi ngữ cảnh?':'Quên memory của bạn trong DM?')){await api('/api/forget',{confirm:true,all});await loadProfile();note('Đã quên dữ liệu và phần dẫn xuất liên quan.');}});
$('preview').onclick=run(async()=>{note('Đang kiểm tra Panel…');candidate=await api('/api/connect/preview',{url:$('panel-url').value,token:$('panel-key').value});$('panel-key').value='';$('candidate-server').replaceChildren();for(const server of candidate.servers)option($('candidate-server'),String(server.index),server.name);$('candidate').classList.remove('hidden');note('Đã đọc danh sách từ Panel. Chọn đúng server để kết nối.');});
$('commit').onclick=run(async()=>{const result=await api('/api/connect/commit',{connection:candidate.connection,index:Number($('candidate-server').value),guild:$('candidate-guild').value});candidate=null;$('candidate').classList.add('hidden');await load();note('Đã kết nối '+result.name+'.');});
$('access-save').onclick=run(async()=>{await api('/api/access',{server:$('access-server').value,subject:$('subject').value,action:$('action').value,level:$('level').value});await load();note('Đã lưu phân quyền.');});
$('task-save').onclick=run(async()=>{await api('/api/tasks/propose',{id:editingTask,goal:$('task-goal').value,when:$('task-when').value,server:$('task-mode').value==='alarm'?'':$('task-server').value,mode:$('task-mode').value,timezone:$('timezone').value});editingTask=null;$('task-form-title').textContent='Hẹn Kei một việc';$('task-save').textContent='Đề xuất lịch';await loadTasks();note('Lịch đang chờ. Bấm 🕒 Xác nhận nếu đúng thời gian và công việc.');});
$('task-reset').onclick=()=>{editingTask=null;$('task-goal').value='';$('task-when').value='';$('task-mode').value='alarm';$('task-server').value='';$('task-save').textContent='Đề xuất lịch';$('task-form-title').textContent='Hẹn Kei một việc';updateTaskMode();};
$('logout').onclick=run(async()=>{await api('/logout',{});location.reload();});
load().catch(error=>{if(error.message!=='Đăng nhập Discord trước nhé.')note(error.message);});
</script>
</body></html>"""
