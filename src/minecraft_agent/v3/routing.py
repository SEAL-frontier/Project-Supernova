"""Deterministic target resolution: permissions first, no arbitrary server fallback."""

from __future__ import annotations


def resolve_server(
    profiles, available_ids, scope, requested=None, selected=None, guild_defaults=None
):
    allowed = set(available_ids).intersection(profiles)
    if not allowed:
        raise PermissionError("Chat vẫn được; copilot cần owner cấp quyền cho server trước nhé.")
    parts = str(scope).split(":")
    guild = parts[1] if len(parts) > 1 and parts[0] == "guild" else None
    mapped = {
        sid
        for sid in allowed
        if not guild
        or not profiles[sid].get("guilds")
        or guild in set(map(str, profiles[sid]["guilds"]))
    }
    if requested:
        name = str(requested).strip().casefold()
        matches = [
            sid
            for sid, p in profiles.items()
            if name in {str(v).casefold() for v in [sid, p.get("name", sid), *p.get("aliases", [])]}
        ]
        if len(matches) > 1:
            raise ValueError(
                "Tên server chưa rõ; dùng ID cụ thể: "
                + ", ".join(sorted(s for s in matches if s in mapped))
            )
        if not matches or matches[0] not in mapped:
            raise PermissionError("Server không được cấp quyền hoặc không thuộc guild này.")
        return matches[0]
    default = (guild_defaults or {}).get(str(guild)) if guild else None
    if default:
        if default not in mapped:
            raise ValueError(
                "Server mặc định của guild không khả dụng hoặc chưa cấp quyền; chọn lại trong /settings."
            )
        return default
    if selected and selected in mapped:
        return selected
    if len(mapped) == 1:
        return next(iter(mapped))
    if not mapped:
        raise PermissionError("Chưa có server được cấp quyền cho guild này.")
    raise ValueError("M muốn làm trên server nào: " + ", ".join(sorted(mapped)) + "?")
