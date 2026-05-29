"""Typed contracts for the SOC Triage Copilot."""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Alert:
    alert_id: str
    title: str
    alert_type: str  # e.g. "credential_stuffing"
    index: str
    sourcetype: str


@dataclass(frozen=True)
class Finding:
    """One investigation step: a question the agent asked and what it found."""

    step: int
    question: str
    spl: str
    row_count: int
    summary: str


@dataclass(frozen=True)
class TimelineEvent:
    time: str
    actor: str
    action: str
    detail: str


@dataclass(frozen=True)
class TriageVerdict:
    severity: str  # CRITICAL | HIGH | MEDIUM | LOW
    classification: str
    confidence: float
    recommended_actions: tuple[str, ...]
    rationale: str


@dataclass(frozen=True)
class IncidentReport:
    alert: Alert
    findings: tuple[Finding, ...]
    timeline: tuple[TimelineEvent, ...]
    verdict: TriageVerdict
    searches_run: int
    narrative: str = ""
    narrative_source: str = "offline"  # hosted-models | offline
