# agents/impact_quantifier/calculators/sla_credits.py
from __future__ import annotations
from typing import Optional
from agents.business_enricher.models import EnrichedSignal
from .base import BaseCalculator
from ..models import CalculationStep


class SLACreditsCalculator(BaseCalculator):
    """
    SLA credits liability = sum of credits owed per breached contract.
    The Enricher already computed this; we wrap with citation.
    """
    name = "sla_credits"
    label = "SLA credit liability"

    def calculate(self, signal: EnrichedSignal) -> Optional[CalculationStep]:
        sla = signal.business_context.sla
        if not sla.breached or sla.estimated_credit_liability_usd <= 0:
            return None

        return CalculationStep(
            calculator_name=self.name,
            label=self.label,
            formula=f"{sla.contracts_affected} contracts × avg credit per contract",
            inputs={
                "contracts_affected": sla.contracts_affected,
                "total_credit_usd": sla.estimated_credit_liability_usd,
            },
            result_usd=round(sla.estimated_credit_liability_usd, 2),
            confidence=0.95,  # contractually defined → high confidence
        )
