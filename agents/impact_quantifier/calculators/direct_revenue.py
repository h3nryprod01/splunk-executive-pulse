# agents/impact_quantifier/calculators/direct_revenue.py
from __future__ import annotations
from typing import Optional
from agents.business_enricher.models import EnrichedSignal
from .base import BaseCalculator
from ..models import CalculationStep


class DirectRevenueCalculator(BaseCalculator):
    """
    Direct revenue loss = revenue_per_minute × duration_min × failure_rate.
    Only applies to revenue-critical services with downtime/error signals.
    """
    name = "direct_revenue"
    label = "Direct revenue loss"

    def calculate(self, signal: EnrichedSignal) -> Optional[CalculationStep]:
        ctx = signal.business_context
        raw = signal.raw_signal

        # Applicability gate
        if not ctx.revenue.revenue_critical:
            return None
        if ctx.revenue.revenue_per_minute_usd is None:
            return None
        if raw.category.value not in ("error_spike", "availability"):
            return None

        rpm = ctx.revenue.revenue_per_minute_usd
        duration_min = raw.duration_minutes
        # Failure rate inference — conservative
        # If signal magnitude has baseline > 0, compute (value - baseline) / total_traffic
        # For demo: assume 100% failure during error_spike windows
        failure_rate = self._infer_failure_rate(signal)

        loss = rpm * duration_min * failure_rate

        confidence = self._confidence(
            base=1.0,
            signal=signal,
            penalty_factors=[
                ctx.revenue.revenue_per_minute_usd is None,
                duration_min < 1.0,                 # very short → noisy
                failure_rate > 0.95 and raw.raw_sample_size < 30,  # small sample
            ],
        )

        return CalculationStep(
            label=self.label,
            formula=f"${rpm:,.0f}/min × {duration_min:.1f} min × {failure_rate*100:.0f}% failure",
            inputs={
                "revenue_per_minute_usd": rpm,
                "duration_minutes": duration_min,
                "failure_rate": failure_rate,
            },
            result_usd=round(loss, 2),
            confidence=round(confidence, 2),
        )

    @staticmethod
    def _infer_failure_rate(signal: EnrichedSignal) -> float:
        # Naïve heuristic; replace with traffic-aware version in prod
        if signal.raw_signal.category.value == "error_spike":
            return 1.0
        if signal.raw_signal.category.value == "availability":
            return 1.0
        return 0.5
