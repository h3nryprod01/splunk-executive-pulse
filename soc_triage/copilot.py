"""SOC Triage Copilot: alert in -> autonomous investigation -> incident report.

    from soc_triage.copilot import SOCTriageCopilot
    report = SOCTriageCopilot().triage(alert)
"""
from __future__ import annotations

from .investigator import Investigator, Searcher
from .models import Alert, IncidentReport
from .triage import assess


class SOCTriageCopilot:
    def __init__(self, searcher: Searcher | None = None):
        self._searcher = searcher

    def triage(self, alert: Alert) -> IncidentReport:
        investigator = Investigator(searcher=self._searcher)
        findings, timeline, facts = investigator.investigate(alert)
        verdict = assess(facts, tuple(findings))
        return IncidentReport(
            alert=alert,
            findings=tuple(findings),
            timeline=tuple(timeline),
            verdict=verdict,
            searches_run=investigator.searches_run,
        )
