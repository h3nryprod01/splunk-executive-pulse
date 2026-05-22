"""Plain-English, pipe-by-pipe explanation of an SPL query (offline)."""
from __future__ import annotations

import re


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
