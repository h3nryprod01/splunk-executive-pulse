"""Self-correction: rewrite SPL whose field names don't exist in the schema.

A real SPL copilot would fetch the index's actual fields (`| fieldsummary`) and
remap. Here we do the same deterministically: known aliases first, then a fuzzy
match against the available fields.
"""
from __future__ import annotations

import difflib
import logging
import os
import re
import sys
from pathlib import Path

logger = logging.getLogger(__name__)

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


def _llm_enabled() -> bool:
    return bool(os.getenv("SPLUNK_LLM_ENDPOINT")
                or os.getenv("ANTHROPIC_API_KEY")
                or os.getenv("OPENAI_API_KEY"))


async def llm_fix_unknown_fields(
    spl: str, unknown: tuple[str, ...], available: set[str],
) -> tuple[str, str] | None:
    """LLM fallback when alias + fuzzy matching can't remap a field.

    Asks Splunk Hosted Models to map each unknown field to one of the available
    fields. Returns (rewritten_spl, reason) or None. Keyless safe: returns None
    immediately when no model credentials are configured.
    """
    if not _llm_enabled() or not available:
        return None
    try:  # pragma: no cover - network/credential path
        sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
        from agents.narrative_writer.llm_client import LLMClient

        system = ("You fix Splunk SPL field names. Map each unknown field to the "
                  "closest field that exists in the index. Respond as JSON: "
                  '{"mapping": {"unknown_field": "real_field"}}.')
        user = f"SPL: {spl}\nUnknown fields: {list(unknown)}\nAvailable fields: {sorted(available)}"
        data = await LLMClient().complete_json(system, user, max_tokens=300)
        mapping = data.get("mapping", {})
        new_spl, remapped = spl, []
        for bad, repl in mapping.items():
            if bad in unknown and repl in available:
                new_spl = re.sub(rf"\b{re.escape(bad)}\b", repl, new_spl)
                remapped.append(f"`{bad}` -> `{repl}`")
        if not remapped:
            return None
        return new_spl, "Hosted Models remapped " + ", ".join(remapped)
    except Exception as exc:
        logger.debug("llm_fix_unknown_fields fell back to offline: %s", exc, exc_info=True)
        return None
