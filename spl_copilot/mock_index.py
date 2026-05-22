"""A tiny in-memory Splunk, just enough to demo the self-critique loop keyless.

It parses the leading `search` clause of an SPL string, validates every field
reference against a per-(index, sourcetype) schema, and applies the simple
comparison filters. Transforming commands (timechart/stats/...) are not
evaluated — their field references are still validated so the copilot can catch
and fix bad field names exactly as it would against a real index.
"""
from __future__ import annotations

import re

# Real field catalog per (index, sourcetype). Note `http_status`, NOT `status`:
# the AI Assistant phrasebook emits `status>=500`, so the copilot must self-fix.
SCHEMA: dict[tuple[str, str], set[str]] = {
    ("prod", "payment-svc"): {"_time", "http_status", "response_ms", "customer_id"},
    ("prod", "checkout-svc"): {"_time", "response_ms", "customer_id"},
    ("security", "auth-svc"): {"_time", "result", "src_ip", "asn", "username"},
}

EVENTS: list[dict] = [
    {"index": "prod", "sourcetype": "payment-svc", "_time": "06:01", "http_status": 500, "response_ms": 1200, "customer_id": "C-1001"},
    {"index": "prod", "sourcetype": "payment-svc", "_time": "06:02", "http_status": 503, "response_ms": 1500, "customer_id": "C-1002"},
    {"index": "prod", "sourcetype": "payment-svc", "_time": "06:03", "http_status": 200, "response_ms": 120, "customer_id": "C-1003"},
    {"index": "prod", "sourcetype": "payment-svc", "_time": "06:04", "http_status": 500, "response_ms": 1800, "customer_id": "C-1004"},
    {"index": "security", "sourcetype": "auth-svc", "_time": "06:01", "result": "blocked", "src_ip": "5.5.5.5", "asn": "AS999", "username": "alice"},
    {"index": "security", "sourcetype": "auth-svc", "_time": "06:02", "result": "blocked", "src_ip": "5.5.5.6", "asn": "AS999", "username": "bob"},
    {"index": "security", "sourcetype": "auth-svc", "_time": "06:03", "result": "allowed", "src_ip": "10.0.0.1", "asn": "AS1", "username": "carol"},
]

_META_KEYS = {"index", "sourcetype", "source", "host", "eventtype"}
_CMP = re.compile(r"([A-Za-z_][\w.]*)\s*(>=|<=|!=|=|>|<)\s*([^\s|]+)")


def _search_clause(spl: str) -> str:
    head = spl.split("|", 1)[0]
    return re.sub(r"^\s*search\s+", "", head.strip(), flags=re.IGNORECASE)


def _transform_fields(spl: str) -> set[str]:
    """Field references in piped commands: `by foo`, `p99(bar)`, `count by baz`."""
    rest = spl.split("|", 1)[1] if "|" in spl else ""
    fields: set[str] = set()
    fields.update(re.findall(r"\bby\s+([A-Za-z_][\w]*)", rest))
    fields.update(re.findall(r"[A-Za-z_]\w*\(([A-Za-z_][\w]*)\)", rest))
    return fields


def schema_for(spl: str) -> set[str]:
    """Available fields for the index/sourcetype named in this SPL."""
    clause = _search_clause(spl)
    selector = {k: v for k, v, *_ in
                ((m[0], m[2]) for m in _CMP.finditer(clause)) if k in _META_KEYS}
    idx = selector.get("index")
    st = selector.get("sourcetype")
    fields: set[str] = set()
    for (i, s), cols in SCHEMA.items():
        if (idx in (None, "*", i)) and (st in (None, s)):
            fields |= cols
    return fields


class MockExecutor:
    """Runs SPL against the in-memory EVENTS. Mirrors the MCP client surface."""

    def fields_for(self, spl: str) -> set[str]:
        return schema_for(spl)

    def run(self, spl: str) -> "RunResult":
        from .models import RunResult

        clause = _search_clause(spl)
        comps = [(k, op, v) for k, op, v in _CMP.findall(clause)]
        available = schema_for(spl)

        referenced = {k for k, _, _ in comps if k not in _META_KEYS}
        referenced |= _transform_fields(spl)
        unknown = sorted(f for f in referenced if f not in available)
        if unknown:
            return RunResult(spl=spl, unknown_fields=tuple(unknown))

        idx = next((v for k, _, v in comps if k == "index"), None)
        st = next((v for k, _, v in comps if k == "sourcetype"), None)
        field_filters = [(k, op, v) for k, op, v in comps if k not in _META_KEYS]

        rows = [
            e for e in EVENTS
            if (idx in (None, "*", e["index"]))
            and (st in (None, e["sourcetype"]))
            and all(_match(e, k, op, v) for k, op, v in field_filters)
        ]
        return RunResult(spl=spl, rows=tuple(rows))


def _match(event: dict, key: str, op: str, value: str) -> bool:
    if key not in event:
        return False
    actual = event[key]
    if isinstance(actual, (int, float)) and re.fullmatch(r"-?\d+(\.\d+)?", value):
        num = float(value)
        return {
            "=": actual == num, "!=": actual != num,
            ">": actual > num, "<": actual < num,
            ">=": actual >= num, "<=": actual <= num,
        }[op]
    sval = value.strip('"')
    return actual == sval if op == "=" else actual != sval if op == "!=" else False
