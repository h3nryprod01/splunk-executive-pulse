"""
Business Context Enricher Agent — main orchestrator.

Takes raw signals from Signal Collector, fans out enrichment across
revenue/customer/SLA/compliance/history modules, returns typed output.
"""
from __future__ import annotations
import asyncio
import logging
import time

from .models import (
    RawSignal, EnrichedSignal, EnricherOutput, BusinessContext,
)
from .enrichers.revenue import enrich_revenue
from .enrichers.customer import enrich_customer
from .enrichers.sla import enrich_sla
from .enrichers.compliance import enrich_compliance
from .enrichers.history import enrich_history

logger = logging.getLogger(__name__)


class BusinessEnricherAgent:
    """Stateless agent. Safe to invoke concurrently per signal."""

    def __init__(self, store, mcp):
        self.store = store
        self.mcp = mcp

    async def enrich_one(self, signal: RawSignal) -> EnrichedSignal:
        """Enrich a single signal — fan out to all sub-enrichers in parallel."""
        all_flags: list[str] = []

        # Fan out parallel — these touch different tables
        revenue_t, customer_t, sla_t, compliance_t, history_t = await asyncio.gather(
            enrich_revenue(signal, self.store),
            enrich_customer(signal, self.store),
            enrich_sla(signal, self.store),
            enrich_compliance(signal, self.store),
            enrich_history(signal, self.store),
            return_exceptions=True,
        )

        # Tolerate partial failures — log, flag, continue
        revenue, _ = self._safe_unpack(revenue_t, "revenue", all_flags)
        customer, _ = self._safe_unpack(customer_t, "customer", all_flags)
        sla, _ = self._safe_unpack(sla_t, "sla", all_flags)
        compliance, _ = self._safe_unpack(compliance_t, "compliance", all_flags)
        history, _ = self._safe_unpack(history_t, "history", all_flags)

        confidence = self._compute_confidence(all_flags)
        needs_review = confidence < 0.5

        ctx = BusinessContext(
            revenue=revenue,
            customer=customer,
            sla=sla,
            compliance=compliance,
            history=history,
            enrichment_confidence=confidence,
            missing_data_flags=all_flags,
        )

        return EnrichedSignal(
            signal_id=signal.signal_id,
            raw_signal=signal,
            business_context=ctx,
            needs_manual_review=needs_review,
        )

    @staticmethod
    def _safe_unpack(result, name: str, accum_flags: list[str]):
        if isinstance(result, Exception):
            logger.exception(f"Enricher '{name}' failed: {result}")
            accum_flags.append(f"{name}_enricher_failed: {type(result).__name__}")
            from .models import (
                RevenueContext, CustomerContext, SLAContext,
                ComplianceContext, HistoryContext,
            )
            defaults = {
                "revenue": RevenueContext(service_tier="unknown"),
                "customer": CustomerContext(),
                "sla": SLAContext(),
                "compliance": ComplianceContext(),
                "history": HistoryContext(),
            }
            return defaults[name], accum_flags
        ctx, flags = result
        accum_flags.extend(flags)
        return ctx, accum_flags

    @staticmethod
    def _compute_confidence(flags: list[str]) -> float:
        """
        Confidence drops with every missing data flag.
        A catalog miss caps confidence hard: if we cannot identify the
        service, all downstream context is guesswork.
        Floors at 0.1 — never claim zero, never claim certainty.
        """
        base = 1.0
        penalty_per_flag = 0.15
        confidence = max(0.1, base - penalty_per_flag * len(flags))
        if any("not found in catalog" in f for f in flags):
            confidence = min(confidence, 0.3)
        return confidence

    async def run(self, signals: list[RawSignal]) -> EnricherOutput:
        """Main entry point — enrich a batch of signals."""
        start = time.perf_counter()
        logger.info(f"Enriching {len(signals)} signals")

        results = await asyncio.gather(
            *[self.enrich_one(s) for s in signals],
            return_exceptions=True,
        )

        enriched, skipped = [], []
        for sig, res in zip(signals, results):
            if isinstance(res, Exception):
                skipped.append({
                    "signal_id": sig.signal_id,
                    "error": str(res),
                    "error_type": type(res).__name__,
                })
                logger.error(f"Signal {sig.signal_id} skipped: {res}")
            else:
                enriched.append(res)

        duration_ms = int((time.perf_counter() - start) * 1000)
        logger.info(
            f"Enrichment done: {len(enriched)}/{len(signals)} succeeded "
            f"in {duration_ms}ms with {self.mcp.calls_made} MCP calls"
        )

        return EnricherOutput(
            enriched_signals=enriched,
            skipped_signals=skipped,
            enrichment_duration_ms=duration_ms,
            mcp_calls_made=self.mcp.calls_made,
        )
