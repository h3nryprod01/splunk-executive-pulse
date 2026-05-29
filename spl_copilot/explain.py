"""Plain-English, pipe-by-pipe explanation of an SPL query.

Prefers Splunk Hosted Models when credentials are configured; otherwise uses a
deterministic offline template so the demo runs keyless.
"""
from __future__ import annotations

import logging
import os
import re
import sys
from pathlib import Path

logger = logging.getLogger(__name__)


def llm_enabled() -> bool:
    return bool(os.getenv("SPLUNK_LLM_ENDPOINT")
                or os.getenv("ANTHROPIC_API_KEY")
                or os.getenv("OPENAI_API_KEY"))


async def explain_spl_llm(spl: str) -> tuple[str, str]:
    """Return (explanation, source). Falls back to offline on any failure."""
    if not llm_enabled():
        return explain_spl(spl), "offline"
    try:  # pragma: no cover - network/credential path
        sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
        from agents.narrative_writer.llm_client import LLMClient

        system = ("You explain Splunk SPL to engineers. Given an SPL query, "
                  "explain it pipe by pipe, one numbered line per command. "
                  'Respond as JSON: {"explanation": "1. ...\\n2. ..."}.')
        data = await LLMClient().complete_json(system, f"SPL: {spl}", max_tokens=500)
        text = str(data.get("explanation", "")).strip()
        return (text or explain_spl(spl)), ("hosted-models" if text else "offline")
    except Exception as exc:
        logger.debug("explain_spl_llm fell back to offline: %s", exc, exc_info=True)
        return explain_spl(spl), "offline"


_PIPED = ("stats", "timechart", "where", "head", "table", "eval", "sort", "dedup")


def _describe(command: str) -> str:
    c = command.strip()
    low = c.lower()
    if low.startswith("search ") or not low.startswith(_PIPED):
        body = re.sub(r"^\s*search\s+", "", c, flags=re.IGNORECASE)
        return f"Filter events matching: {body}"
    if low.startswith("timechart"):
        return f"Bucket the matching events over time ({c})."
    if low.startswith("stats"):
        return f"Aggregate the matching events ({c})."
    if low.startswith("where"):
        return f"Keep only rows where {c[len('where'):].strip()}."
    if low.startswith("head"):
        return f"Return only the first {c[len('head'):].strip() or 'N'} rows."
    if low.startswith("table"):
        return f"Project columns: {c[len('table'):].strip()}."
    if low.startswith("eval"):
        return f"Compute a derived field: {c[len('eval'):].strip()}."
    if low.startswith("sort"):
        return f"Sort by {c[len('sort'):].strip()}."
    return f"Apply `{c}`."


def explain_spl(spl: str) -> str:
    parts = [p.strip() for p in spl.split("|") if p.strip()]
    lines = [f"{i + 1}. {_describe(p)}" for i, p in enumerate(parts)]
    return "\n".join(lines)
