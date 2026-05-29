# agents/impact_quantifier/calculators/incident_cost.py
from __future__ import annotations
from typing import Optional
from agents.business_enricher.models import EnrichedSignal
from .base import BaseCalculator
from ..models import CalculationStep


class IncidentResponseCostCalculator(BaseCalculator):
    """
    Engineering response cost = engineers × hours × loaded_rate.
    Engineers/hours inferred from signal duration and severity.
    """
    name = "incident_response_cost"
    label = "Incident response cost"

    LOADED_RATE_PER_HOUR = 175.0      # USD, loaded engineer cost
    ENGINEERS_BY_SEVERITY = {
        "error_spike":  3,
        "availability": 5,
        "security":     4,
        "latency":      2,
        "capacity":     2,
    }

    def calculate(self, signal: EnrichedSignal) -> Optional[CalculationStep]:
        cat = signal.raw_signal.category.value
        if cat not in self.ENGINEERS_BY_SEVERITY:
            return None

        engineers = self.ENGINEERS_BY_SEVERITY[cat]
        # Response time = incident duration + 2h followup
        hours = signal.raw_signal.duration_minutes / 60.0 + 2.0
        cost = engineers * hours * self.LOADED_RATE_PER_HOUR

        return CalculationStep(
            calculator_name=self.name,
            label=self.label,
            formula=f"{engineers} engineers × {hours:.1f}h × ${self.LOADED_RATE_PER_HOUR}/h",
            inputs={
                "engineers": engineers,
                "hours": hours,
                "loaded_rate_usd": self.LOADED_RATE_PER_HOUR,
            },
            result_usd=round(cost, 2),
            confidence=0.6,
        )
