"""Multi-step investigation: the agent runs SPL, reads the results, and uses
what it learns to decide the next query (the pivot).

The keyless executor is `mock_splunk.search`; swap in the shared MCP client
(`agents/signal_collector/splunk_mcp.py`) for a live stack.
"""
from __future__ import annotations

from collections.abc import Callable

from .models import Alert, Finding, TimelineEvent
from .mock_splunk import search as mock_search

Searcher = Callable[[str], list[dict]]


class Investigator:
    def __init__(self, searcher: Searcher | None = None):
        self._search = searcher or mock_search
        self.searches_run = 0

    def _run(self, spl: str) -> list[dict]:
        self.searches_run += 1
        return self._search(spl)

    def investigate(self, alert: Alert) -> tuple[list[Finding], list[TimelineEvent], dict]:
        findings: list[Finding] = []
        events: list[dict] = []
        facts: dict = {}

        # Step 1 — quantify the burst and identify attacker IPs.
        spl1 = f"search index={alert.index} sourcetype={alert.sourcetype} result=blocked"
        blocked = self._run(spl1)
        events += blocked
        attacker_ips = sorted({e["src_ip"] for e in blocked})
        facts["attacker_ips"] = attacker_ips
        findings.append(Finding(
            step=1,
            question="How many blocked auth attempts, and from which source IPs?",
            spl=spl1, row_count=len(blocked),
            summary=f"{len(blocked)} blocked attempts from {len(attacker_ips)} IP(s): "
                    f"{', '.join(attacker_ips)}.",
        ))

        # Step 2 — PIVOT: did any login SUCCEED from an attacker IP?
        compromised: list[dict] = []
        for ip in attacker_ips:
            spl2 = (f"search index={alert.index} sourcetype={alert.sourcetype} "
                    f'result=allowed src_ip="{ip}"')
            hits = self._run(spl2)
            events += hits
            compromised += hits
        comp_users = sorted({e["username"] for e in compromised})
        facts["compromised_users"] = comp_users
        findings.append(Finding(
            step=2,
            question="Did any login succeed from the attacker IP(s)?",
            spl=f'... result=allowed src_ip IN ({", ".join(attacker_ips)})',
            row_count=len(compromised),
            summary=("No successful logins — attack appears blocked."
                     if not compromised else
                     f"{len(compromised)} SUCCESSFUL login(s): account(s) "
                     f"{', '.join(comp_users)} likely compromised."),
        ))

        # Step 3 — PIVOT: what did a compromised account do afterwards?
        for user in comp_users:
            spl3 = f'search index={alert.index} sourcetype=api-svc username="{user}"'
            actions = self._run(spl3)
            events += actions
            facts.setdefault("data_access", []).extend(actions)
            if actions:
                detail = ", ".join(
                    f'{a.get("action")} {a.get("count", "")} {a.get("object", "")}'.strip()
                    for a in actions)
                findings.append(Finding(
                    step=3,
                    question=f"What did {user} do after logging in?",
                    spl=spl3, row_count=len(actions),
                    summary=f"Post-compromise activity by {user}: {detail}.",
                ))

        timeline = _build_timeline(events)
        return findings, timeline, facts


def _build_timeline(events: list[dict]) -> list[TimelineEvent]:
    seen: set[tuple] = set()
    out: list[TimelineEvent] = []
    for e in sorted(events, key=lambda x: x["_time"]):
        if e.get("sourcetype") == "auth-svc":
            actor, action = e["src_ip"], f'login {e["result"]}'
            detail = f'user={e["username"]} asn={e.get("asn", "")}'
        else:
            actor, action = e.get("username", "?"), e.get("action", "activity")
            detail = f'{e.get("object", "")} count={e.get("count", "")}'
        key = (e["_time"], actor, action, detail)
        if key in seen:
            continue
        seen.add(key)
        out.append(TimelineEvent(time=e["_time"], actor=actor, action=action, detail=detail))
    return out
