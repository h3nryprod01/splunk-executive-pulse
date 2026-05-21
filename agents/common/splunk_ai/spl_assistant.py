"""
Splunk AI Assistant for SPL — natural-language <-> SPL.

Wraps the Splunk AI Assistant for SPL (agentic NL->SPL generation, backed by
Splunk-hosted LLMs). Two modes:
  - online:  POST to the AI Assistant endpoint (SPLUNK_AI_ASSISTANT_URL/TOKEN)
  - offline: a deterministic intent->SPL phrasebook, so demos and the
             briefing drill-down loop work without a live Assistant.

Used for:
  1. Detector SPL generation/validation from a plain-English intent.
  2. The briefing drill-down loop: an executive's follow-up question
     ("show me last night's payment errors") -> SPL -> Splunk.
"""
from __future__ import annotations
import logging
import os
import re
from typing import Optional

import httpx
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class SPLSuggestion(BaseModel):
    intent: str
    spl: str
    explanation: str
    source: str = Field(description="splunk-ai-assistant | offline-fallback")
    confidence: float = Field(ge=0.0, le=1.0)


# Intent phrasebook: (keyword set, SPL, explanation). First match wins.
_PHRASEBOOK: list[tuple[tuple[str, ...], str, str]] = [
    (("payment", "error"),
     "search index=prod sourcetype=payment-svc status>=500 | timechart span=1m count",
     "Payment-service 5xx errors per minute."),
    (("login", "fail"),
     "search index=security sourcetype=auth-svc result=blocked | stats count by src_ip, asn",
     "Blocked login attempts grouped by source IP and ASN."),
    (("credential", "stuffing"),
     "search index=security sourcetype=auth-svc result IN (blocked, challenged) "
     "| bin _time span=15m | stats count AS attempts, dc(src_ip) AS unique_ips by _time",
     "Credential-stuffing volume and unique source IPs over 15-minute windows."),
    (("latency", "checkout"),
     "search index=prod sourcetype=checkout-svc | timechart span=1h p99(response_ms)",
     "Checkout p99 latency by hour."),
    (("latency",),
     "search index=prod | timechart span=1h p99(response_ms) by sourcetype",
     "p99 latency by service, hourly."),
    (("cost",),
     "search index=finance sourcetype=aws-billing | timechart span=1d sum(cost_usd) by service",
     "Daily infrastructure spend by service."),
    (("sla", "breach"),
     "search index=prod status>=500 | stats count by service "
     "| where count > 0",
     "Services with errors that may breach SLA."),
]


class SplunkSPLAssistant:
    """Client for Splunk AI Assistant for SPL, with an offline fallback."""

    def __init__(self, endpoint: Optional[str] = None, token: Optional[str] = None,
                 timeout_s: int = 30):
        self.endpoint = endpoint or os.getenv("SPLUNK_AI_ASSISTANT_URL")
        self.token = token or os.getenv("SPLUNK_AI_ASSISTANT_TOKEN")
        self.timeout = timeout_s

    async def generate_spl(self, nl_intent: str) -> SPLSuggestion:
        """Translate a natural-language request into SPL."""
        if self.endpoint and self.token:
            try:
                return await self._call_remote(nl_intent)
            except Exception as e:  # pragma: no cover - network path
                logger.warning(f"AI Assistant unavailable ({e}); using offline fallback")
        return self._offline_generate(nl_intent)

    async def _call_remote(self, nl_intent: str) -> SPLSuggestion:  # pragma: no cover
        async with httpx.AsyncClient(timeout=self.timeout) as c:
            r = await c.post(
                f"{self.endpoint.rstrip('/')}/v1/spl/generate",
                headers={"Authorization": f"Bearer {self.token}"},
                json={"natural_language": nl_intent},
            )
            r.raise_for_status()
            data = r.json()
            return SPLSuggestion(
                intent=nl_intent,
                spl=data["spl"],
                explanation=data.get("explanation", ""),
                source="splunk-ai-assistant",
                confidence=float(data.get("confidence", 0.9)),
            )

    def _offline_generate(self, nl_intent: str) -> SPLSuggestion:
        text = nl_intent.lower()
        for keywords, spl, explanation in _PHRASEBOOK:
            if all(k in text for k in keywords):
                return SPLSuggestion(
                    intent=nl_intent, spl=spl, explanation=explanation,
                    source="offline-fallback", confidence=0.6,
                )
        # Generic fallback: keyword search over all indexes.
        terms = [t for t in re.findall(r"[a-z0-9_]+", text) if len(t) > 2][:5]
        spl = "search index=* " + " ".join(terms) + " | head 100"
        return SPLSuggestion(
            intent=nl_intent, spl=spl,
            explanation="Generic keyword search (no template matched).",
            source="offline-fallback", confidence=0.3,
        )
