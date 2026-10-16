"""Discord paragraphs stay together; split fenced blocks remain well formed."""

import re


def chat_chunks(text, limit=2000):
    """Line-separated conversation bubbles; fenced code and structured lists stay together."""
    result=[];buffer=[];fenced=False;structured=False
    def flush():
        nonlocal buffer
        body='\n'.join(buffer).strip()
        if body:result.extend(chunks(body,limit))
        buffer=[]
    for line in str(text or '').strip().splitlines():
        marker=line.lstrip().startswith('```')
        if marker:
            if not fenced:flush()
            buffer.append(line);fenced=not fenced
            if not fenced:flush()
            continue
        if fenced:buffer.append(line);continue
        if line.startswith('-#') and result and not buffer:
            prior=result.pop();result.extend(chunks(prior+'\n'+line,limit));continue
        is_structure=bool(re.match(r'^\s*(?:[-*+] |\d+[.)] |> |#{1,3} )',line))
        if is_structure:buffer.append(line);structured=True
        elif not line.strip():flush();structured=False
        elif structured:buffer.append(line)
        else:buffer.append(line);flush()
    flush()
    return result


def chunks(text, limit=2000):
    text = str(text or "").strip()
    if not text:
        return []
    if limit < 32:
        raise ValueError("Discord chunk limit must leave room for Markdown fences")
    if len(text) <= limit:
        return [text]
    out, current, fence = [], "", None

    def emit():
        nonlocal current
        body = current.rstrip()
        if body and body != fence:
            out.append(body + ("\n```" if fence else ""))
        current = fence + "\n" if fence else ""

    for line in text.splitlines(keepends=True):
        marker = re.fullmatch(r"\s*```([^`\r\n]*)\s*(?:\r?\n)?", line)
        if marker and fence is None:
            header = "```" + marker.group(1).strip()[: min(64, limit // 4)]
            if len(current) + len(header) + 5 > limit:
                emit()
            current += header + "\n"
            fence = header
            continue
        if marker and fence and not marker.group(1).strip():
            current = current.rstrip() + "\n```\n"
            fence = None
            continue
        while line:
            reserve = 4 if fence else 0
            room = limit - len(current) - reserve
            if room <= 0:
                emit()
                continue
            if len(line) <= room:
                current += line
                break
            prefix = fence + "\n" if fence else ""
            if current != prefix and len(line) <= limit - len(prefix) - reserve:
                emit()
                continue
            cut = line.rfind(" ", 0, room)
            if cut < room // 2:
                cut = room
            current += line[:cut]
            line = line[cut:].lstrip(" ")
            emit()
    if current.strip() and current.strip() != fence:
        out.append(current.rstrip() + ("\n```" if fence else ""))
    return out
