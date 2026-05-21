# agents/impact_quantifier/calculators/base.py
from __future__ import annotations
from abc import ABC, abstractmethod
from typing import Optional
from agents.business_enricher.models import EnrichedSignal
from ..models import CalculationStep


class BaseCalculator(ABC):
    """
    A calculator computes ONE specific kind of financial impact.
    Each returns a CalculationStep (or None if not applicable).
    """

    name: str
    label: str  # human label, shown in UI tooltips

    @abstractmethod
    def calculate(self, signal: EnrichedSignal) -> Optional[CalculationStep]:
        ...

    def _confidence(
        self, base: float, signal: EnrichedSignal, penalty_factors: list[bool],
    ) -> float:
        """
        Common confidence model:
          start at base, subtract 0.1 per missing input,
          multiply by enrichment confidence.
        """
        c = base
        for missing in penalty_factors:
            if missing:
                c -= 0.1
        c *= signal.business_context.enrichment_confidence
        return max(0.0, min(1.0, c))
