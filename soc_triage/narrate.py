"""Analyst-facing incident narrative.

Prefers Splunk Hosted Models (via the shared LLMClient) to write the prose; the
triage VERDICT itself stays deterministic. Falls back to a templated narrative
when no model credentials are configured, so the demo runs keyless.
"""
from __future__ import annotations

import asyncio
import logging
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from .models import Finding, TriageVerdict

logger = logging.getLogger(__name__)


def _llm_enabled() -> bool:
    return bool(os.getenv("SPLUNK_LLM_ENDPOINT")
                or os.getenv("ANTHROPIC_API_KEY")
                or os.getenv("OPENAI_API_KEY"))


def narrate(alert_title: str, findings: tuple[Finding, ...],
            verdict: TriageVerdict, facts: dict) -> tuple[str, str]:
    """Return (narrative_text, source) where source is hosted-models|offline."""
    if _llm_enabled():
        try:
            asyncio.get_running_loop()
        except RuntimeError:
            # No running loop: safe to drive the coroutine with asyncio.run.
            try:
                return asyncio.run(_llm_narrate(alert_title, findings, verdict, facts)), "hosted-models"
            except Exception as exc:  # pragma: no cover - network/credential path
                logger.debug("narrate fell back to offline: %s", exc, exc_info=True)
        else:
            # Inside a running event loop: asyncio.run would raise, so fall back
            # to the deterministic offline narrative instead.
            logger.debug("narrate fell back to offline: running event loop detected")
    return _offline_narrate(alert_title, verdict, facts), "offline"


def _offline_narrate(alert_title: str, verdict: TriageVerdict, facts: dict) -> str:
    ips = ", ".join(facts.get("attacker_ips", [])) or "unknown source(s)"
    users = ", ".join(facts.get("compromised_users", []))
    parts = [
        f"Alert '{alert_title}' was triaged as {verdict.severity} "
        f"({verdict.classification}, confidence {verdict.confidence:.0%}).",
        verdict.rationale,
    ]
    if users and verdict.recommended_actions:
        parts.append(
            f"Recommend immediate containment: {verdict.recommended_actions[0]}. "
            f"Source IP(s) {ips} should be blocked at the edge."
        )
    return " ".join(parts)


async def _llm_narrate(alert_title, findings, verdict, facts) -> str:  # pragma: no cover
    from agents.narrative_writer.llm_client import LLMClient

    system = ("You are a SOC analyst. Write a concise (3-4 sentence) incident "
              "summary for a Tier-2 reviewer. Do not invent facts. Respond as "
              'JSON: {"narrative": "..."}.')
    user = (f"Alert: {alert_title}\n"
            f"Verdict: {verdict.severity} - {verdict.classification} "
            f"(confidence {verdict.confidence}). Rationale: {verdict.rationale}\n"
            f"Facts: {facts}\n"
            "Findings: " + " | ".join(f"{f.step}. {f.summary}" for f in findings))
    data = await LLMClient().complete_json(system, user, max_tokens=400)
    return str(data.get("narrative", "")).strip() or _offline_narrate(alert_title, verdict, facts)
