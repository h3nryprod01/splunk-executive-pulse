# agents/impact_quantifier/agent.py
"""
Impact Quantifier Agent.

Runs all calculators per signal, aggregates financial impact,
computes priority score, gates qualitative-only when confidence too low.
"""
from __future__ import annotations
import logging
import time
from typing import Optional

from agents.business_enricher.models import EnrichedSignal, EnricherOutput
from .calculators.base import BaseCalculator
from .calculators.direct_revenue import DirectRevenueCalculator
from .calculators.churn_risk import ChurnRiskCalculator
from .calculators.sla_credits import SLACreditsCalculator
from .calculators.incident_cost import IncidentResponseCostCalculator
from .models import (
    QuantifiedSignal, QuantifierOutput,
    FinancialImpact, CalculationStep,
)
from .priority import compute_priority_score, compute_customer_score

logger = logging.getLogger(__name__)


# Confidence threshold below which we DO NOT present $ figures.
# Below this, briefing uses qualitative language only.
QUALITATIVE_ONLY_THRESHOLD = 0.40
ATTENTION_PRIORITY_THRESHOLD = 60.0


class ImpactQuantifierAgent:

    def __init__(self, calculators: Optional[list[BaseCalculator]] = None):
        self.calculators = calculators or [
            DirectRevenueCalculator(),
            ChurnRiskCalculator(),
            SLACreditsCalculator(),
            IncidentResponseCostCalculator(),
        ]

    # ---------- public ----------
    def quantify_one(self, signal: EnrichedSignal) -> QuantifiedSignal:
        steps: list[CalculationStep] = []
        for calc in self.calculators:
            try:
                step = calc.calculate(signal)
                if step is not None:
                    steps.append(step)
            except Exception as e:
                logger.exception(
                    f"Calculator {calc.name} failed for signal {signal.signal_id}: {e}"
                )
                # Skip this calculator; keep going
                continue

        financial = self._aggregate(steps)
        customer  = compute_customer_score(signal)
        priority  = compute_priority_score(signal, financial, customer)

        qualitative_only = financial.aggregated_confidence < QUALITATIVE_ONLY_THRESHOLD

        return QuantifiedSignal(
            signal_id=signal.signal_id,
            enriched=signal,
            financial_impact=financial,
            customer_impact=customer,
            priority_score=priority,
            executive_attention_required=priority >= ATTENTION_PRIORITY_THRESHOLD,
            qualitative_only=qualitative_only,
        )

    def run(self, enricher_output: EnricherOutput) -> QuantifierOutput:
        start = time.perf_counter()
        results, failed = [], []

        for signal in enricher_output.enriched_signals:
            try:
                results.append(self.quantify_one(signal))
            except Exception as e:
                logger.exception(f"Quantification failed for {signal.signal_id}: {e}")
                failed.append({"signal_id": signal.signal_id, "error": str(e)})

        total = sum(q.financial_impact.total_exposure_usd for q in results)
        top_priority = max((q.priority_score for q in results), default=0.0)

        duration_ms = int((time.perf_counter() - start) * 1000)
        logger.info(
            f"Quantified {len(results)}/{len(enricher_output.enriched_signals)} "
            f"signals; total exposure ${total:,.0f}; top priority {top_priority}"
        )

        return QuantifierOutput(
            quantified_signals=results,
            total_exposure_usd=round(total, 2),
            highest_priority_score=top_priority,
            failed_quantifications=failed,
            duration_ms=duration_ms,
        )

    # ---------- private ----------
    # Stable calculator-name → FinancialImpact field. Dispatching on the
    # calculator's `name` (not its human-readable label) decouples financial
    # correctness from UI wording.
    _CALCULATOR_FIELD_MAP = {
        "direct_revenue": "direct_revenue_loss_usd",
        "churn_risk": "indirect_exposure_usd",
        "sla_credits": "sla_credit_liability_usd",
        "incident_response_cost": "incident_response_cost_usd",
    }

    @classmethod
    def _aggregate(cls, steps: list[CalculationStep]) -> FinancialImpact:
        impact = FinancialImpact(calculations=steps, aggregated_confidence=1.0)
        if not steps:
            impact.aggregated_confidence = 0.0
            return impact

        # Dispatch each step into its FinancialImpact field by stable
        # calculator_name. Unknown calculator names are logged and ignored
        # so they never silently inflate (or get dropped from) the total.
        for s in steps:
            field = cls._CALCULATOR_FIELD_MAP.get(s.calculator_name)
            if field is None:
                logger.warning(
                    f"No FinancialImpact field mapped for calculator "
                    f"'{s.calculator_name}' (label={s.label!r}); skipping"
                )
                continue
            setattr(impact, field, s.result_usd)

        impact.total_exposure_usd = round(
            impact.direct_revenue_loss_usd +
            impact.indirect_exposure_usd +
            impact.sla_credit_liability_usd +
            impact.incident_response_cost_usd +
            impact.cost_overrun_usd,
            2,
        )

        # Aggregated confidence: weighted ARITHMETIC mean, each step weighted
        # by its share of total dollar contribution. Uses the same `steps`
        # set as total_exposure for a consistent denominator.
        total = sum(s.result_usd for s in steps) or 1.0
        weighted_conf = sum(s.confidence * (s.result_usd / total) for s in steps)
        impact.aggregated_confidence = round(weighted_conf, 2)
        return impact
