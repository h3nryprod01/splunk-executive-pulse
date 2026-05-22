"""Keyless in-memory security events + a minimal SPL search executor.

Enough to drive a multi-step investigation without a live Splunk stack. The
data tells one story: a credential-stuffing burst from 5.5.5.5 that ends in a
successful login (account takeover) and bulk customer-data export.
"""
from __future__ import annotations

import re

EVENTS: list[dict] = [
    # Credential-stuffing burst from two source IPs.
    {"index": "security", "sourcetype": "auth-svc", "_time": "06:00:11", "result": "blocked", "src_ip": "5.5.5.5", "asn": "AS999", "username": "alice"},
    {"index": "security", "sourcetype": "auth-svc", "_time": "06:00:14", "result": "blocked", "src_ip": "5.5.5.5", "asn": "AS999", "username": "bob"},
    {"index": "security", "sourcetype": "auth-svc", "_time": "06:00:19", "result": "blocked", "src_ip": "5.5.5.5", "asn": "AS999", "username": "carol"},
    {"index": "security", "sourcetype": "auth-svc", "_time": "06:00:22", "result": "blocked", "src_ip": "5.5.5.6", "asn": "AS999", "username": "dave"},
    {"index": "security", "sourcetype": "auth-svc", "_time": "06:00:31", "result": "blocked", "src_ip": "5.5.5.5", "asn": "AS999", "username": "alice"},
    # The pivot: a SUCCESSFUL login from the attacker IP -> takeover.
    {"index": "security", "sourcetype": "auth-svc", "_time": "06:01:05", "result": "allowed", "src_ip": "5.5.5.5", "asn": "AS999", "username": "alice"},
    # Post-compromise data access.
    {"index": "security", "sourcetype": "api-svc", "_time": "06:03:40", "username": "alice", "action": "export", "object": "customer_records", "count": 1247},
]

_META = {"index", "sourcetype", "source", "host"}
_CMP = re.compile(r'([A-Za-z_][\w.]*)\s*(>=|<=|!=|=|>|<)\s*("[^"]*"|[^\s|]+)')


def search(spl: str) -> list[dict]:
    """Run the leading search clause of an SPL string against EVENTS."""
    clause = re.sub(r"^\s*search\s+", "", spl.split("|", 1)[0].strip(), flags=re.IGNORECASE)
    comps = _CMP.findall(clause)
    idx = next((v for k, _, v in comps if k == "index"), None)
    st = next((v for k, _, v in comps if k == "sourcetype"), None)
    filters = [(k, op, v.strip('"')) for k, op, v in comps if k not in _META]
    return [
        e for e in EVENTS
        if idx in (None, "*", e.get("index"))
        and st in (None, e.get("sourcetype"))
        and all(_match(e, k, op, v) for k, op, v in filters)
    ]


def _match(event: dict, key: str, op: str, value: str) -> bool:
    if key not in event:
        return False
    actual = event[key]
    if isinstance(actual, (int, float)) and re.fullmatch(r"-?\d+(\.\d+)?", value):
        num = float(value)
        return {"=": actual == num, "!=": actual != num, ">": actual > num,
                "<": actual < num, ">=": actual >= num, "<=": actual <= num}[op]
    return actual == value if op == "=" else actual != value if op == "!=" else False
