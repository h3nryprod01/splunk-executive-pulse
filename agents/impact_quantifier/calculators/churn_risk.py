# agents/impact_quantifier/calculators/churn_risk.py
from __future__ import annotations
from typing import Optional
from agents.business_enricher.models import EnrichedSignal
from .base import BaseCalculator
from ..models import CalculationStep


class ChurnRiskCalculator(BaseCalculator):
    """
    Indirect exposure = enterprise_customers_affected × churn_risk × avg_ACV.

    Conservative: only models enterprise tier (highest signal-to-noise).
    Churn lift = base_churn_rate × incident_severity_multiplier.
    """
    name = "churn_risk"
    label = "Indirect churn exposure"

    # Severity multiplier by signal category — tunable
    SEVERITY_MULT = {
        "error_spike": 1.25,
        "availability": 1.50,
        "latency": 1.10,
        "security": 2.00,  # data breach style
    }

    # Average enterprise ACV — could be loaded from DB
    ENT_AVG_ACV_USD = 480_000.0

    def calculate(self, signal: EnrichedSignal) -> Optional[CalculationStep]:
        ctx = signal.business_context
        ent_count = ctx.customer.by_tier.enterprise

        if ent_count == 0:
            return None

        base_churn = 0.04  # Could read from customer table avg
        mult = self.SEVERITY_MULT.get(signal.raw_signal.category.value, 1.0)
        effective_churn = base_churn * mult

        exposure = ent_count * effective_churn * self.ENT_AVG_ACV_USD

        # History worsens it — repeat offenders churn more
        history_mult = 1.0
        if ctx.history.occurrences_last_30d >= 3:
            history_mult = 1.4
        elif ctx.history.occurrences_last_30d >= 2:
            history_mult = 1.2
        exposure *= history_mult

        confidence = self._confidence(
            base=0.7,    # indirect models inherently less certain
            signal=signal,
            penalty_factors=[
                ent_count < 5,
                ctx.history.trend == "unknown",
            ],
        )

        return CalculationStep(
            label=self.label,
            formula=(
                f"{ent_count} enterprise × {effective_churn*100:.1f}% churn risk "
                f"× ${self.ENT_AVG_ACV_USD:,.0f} ACV × {history_mult}x history"
            ),
            inputs={
                "enterprise_customers_affected": ent_count,
                "base_churn_rate": base_churn,
                "severity_multiplier": mult,
                "history_multiplier": history_mult,
                "avg_acv_usd": self.ENT_AVG_ACV_USD,
            },
            result_usd=round(exposure, 2),
            confidence=round(confidence, 2),
            notes="Indirect estimate; not realized loss",
        )
