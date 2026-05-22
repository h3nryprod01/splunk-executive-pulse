"""Self-correction: rewrite SPL whose field names don't exist in the schema.

A real SPL copilot would fetch the index's actual fields (`| fieldsummary`) and
remap. Here we do the same deterministically: known aliases first, then a fuzzy
match against the available fields.
"""
from __future__ import annotations

import difflib
import re

# Common ways an LLM/analyst names a field vs. what the index actually calls it.
_ALIASES: dict[str, tuple[str, ...]] = {
    "http_status": ("status", "status_code", "statuscode", "code"),
    "src_ip": ("ip", "source_ip", "client_ip", "srcip"),
    "username": ("user", "user_name", "account"),
    "response_ms": ("latency", "latency_ms", "resp_ms", "duration"),
}
_ALIAS_LOOKUP = {alias: canonical
                 for canonical, aliases in _ALIASES.items()
                 for alias in aliases}


def _resolve(bad_field: str, available: set[str]) -> str | None:
    canonical = _ALIAS_LOOKUP.get(bad_field)
    if canonical and canonical in available:
        return canonical
    match = difflib.get_close_matches(bad_field, available, n=1, cutoff=0.6)
    return match[0] if match else None


def fix_unknown_fields(
    spl: str, unknown: tuple[str, ...], available: set[str],
) -> tuple[str, str] | None:
    """Return (rewritten_spl, reason) or None if nothing could be remapped."""
    new_spl = spl
    remapped: list[str] = []
    for bad in unknown:
        repl = _resolve(bad, available)
        if not repl:
            continue
        new_spl = re.sub(rf"\b{re.escape(bad)}\b", repl, new_spl)
        remapped.append(f"`{bad}` -> `{repl}`")
    if not remapped:
        return None
    reason = "Field(s) not in schema; remapped " + ", ".join(remapped)
    return new_spl, reason
