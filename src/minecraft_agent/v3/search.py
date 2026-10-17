"""Search receipts distinguish discovery, successful page fetch, empty and failure."""

from __future__ import annotations
import asyncio, contextvars, html, ipaddress, re, socket, time
from urllib.parse import urlsplit
import httpx
from ..v2.web_search import WebSearch

SEARCH_SINK = contextvars.ContextVar("kei_search_sink", default=None)

def lookup_hint(text):
    own=str(text).split('[REPLIED MESSAGE',1)[0].split('[ATTACHMENT',1)[0].strip()
    explicit=re.search(r'^\s*(?:kei[, !:]*)?search\b|\b(?:search (?:for|about)|tra (?:cứu|tài liệu)|tìm (?:trên (?:web|mạng)|link|nguồn)|(?:hãy|giúp|thử|dùng).{0,20}(?:search|tìm trên mạng))',own,re.I)
    current=re.search(r'\bmới nhất\b|latest (?:version|release|news)|giá .{0,25}(?:hôm nay|hiện tại)|(?:version|phiên bản).{0,25}(?:hiện tại|current)',own,re.I)
    return re.sub(r'<@!?\d+>','',own)[:220] if explicit or current else ''


async def public_url(url):
    parsed = urlsplit(url)
    if (
        parsed.scheme not in ("http", "https")
        or not parsed.hostname
        or parsed.username
        or parsed.password
    ):
        raise ValueError("Invalid public source URL")
    records = await asyncio.to_thread(
        socket.getaddrinfo,
        parsed.hostname,
        parsed.port or (443 if parsed.scheme == "https" else 80),
        0,
        socket.SOCK_STREAM,
    )
    if any(not ipaddress.ip_address(r[4][0]).is_global for r in records):
        raise ValueError("Private source URL")


class Search(WebSearch):
    async def notify(self, phase, **data):
        sink = SEARCH_SINK.get()
        if sink:
            await sink(phase, **data)

    async def fetch(self, client, url):
        for _ in range(4):
            await public_url(url)
            async with client.stream("GET", url, follow_redirects=False) as r:
                if r.status_code in (301, 302, 303, 307, 308):
                    url = str(r.url.join(r.headers["location"]))
                    continue
                r.raise_for_status()
                content = bytearray()
                async for part in r.aiter_bytes():
                    content.extend(part)
                    if len(content) > 1024 * 1024:
                        raise ValueError("Source page too large")
                mime = r.headers.get("content-type", "")
                if not any(t in mime for t in ("text/", "json", "xml")):
                    raise ValueError("Source is not readable text")
                text = content.decode("utf-8", "replace")
                text = re.sub(r"<(script|style)\b[^>]*>.*?</\1>", " ", text, flags=re.S | re.I)
                text = html.unescape(re.sub("<[^>]+>", " ", text))
                text = re.sub(r"\s+", " ", text).strip()
                if len(text) < 60:
                    raise ValueError("Source has insufficient readable content")
                return {"url": url, "domain": urlsplit(url).hostname, "text": text[:6000]}
        raise ValueError("Too many source redirects")

    async def search(self, query, limit=5):
        await self.notify("searching")
        result = await super().search(query, limit)
        restrictions=re.findall(r'\bsite:([^\s\"]+)',query,re.I)
        if restrictions and result.get('results'):
            def relevant(row):
                actual=urlsplit(row.get('url',''))
                for restriction in restrictions:
                    expected=urlsplit('https://'+restriction)
                    if (actual.hostname==expected.hostname or (actual.hostname or '').endswith('.'+str(expected.hostname))) and actual.path.casefold().startswith(expected.path.casefold().rstrip('/')):return True
                return False
            original=result['results'];result['results']=[row for row in original if relevant(row)];result['discarded_offsite']=len(original)-len(result['results'])
            if 'fetched' in result:
                result['fetched']=[row for row in result['fetched'] if relevant(row)]
                result['fetched_pages']=len(result['fetched']);result['searched_sites']=len({row['domain'] for row in result['fetched']})
            if not result['results'] and not result.get('error'):result['status']='empty'
        if result.get("cached") and "searched_sites" in result:
            await self.notify(
                "done",
                sites=result["searched_sites"],
                pages=result["fetched_pages"],
                status=result["status"],
                errors=len(result["fetch_errors"]),
                receipts=[{'url':r['url'],'domain':r['domain']} for r in result['fetched']],
            )
            return result
        result["status"] = (
            "error" if result.get("error") else ("results" if result.get("results") else "empty")
        )
        fetched = []
        errors = []
        if result.get("results"):
            async with httpx.AsyncClient(
                timeout=12, headers={"User-Agent": "keys-keys source reader"}
            ) as client:

                async def read(row):
                    try:
                        page = await self.fetch(client, row["url"])
                        fetched.append(page)
                        await self.notify("fetch", pages=len(fetched), domain=page["domain"])
                    except (httpx.HTTPError, ValueError, OSError) as exc:
                        errors.append(
                            {"domain": urlsplit(row["url"]).hostname, "error": type(exc).__name__}
                        )

                await asyncio.gather(*(read(row) for row in result["results"][: min(5, limit)]))
        result.update(
            fetched=fetched,
            fetched_pages=len(fetched),
            searched_sites=len({p["domain"] for p in fetched}),
            fetch_errors=errors,
        )
        await self.notify(
            "done",
            sites=result["searched_sites"],
            pages=len(fetched),
            status=result["status"],
            errors=len(errors),
            receipts=[{'url':r['url'],'domain':r['domain']} for r in fetched],
        )
        return result
