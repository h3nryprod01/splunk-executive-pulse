from __future__ import annotations
from abc import ABC
from agents.impact_quantifier.models import QuantifiedSignal
from ..models import StoryCluster, StoryTheme, Persona


class BasePersonaProfile(ABC):
    """A persona profile defines: weights, attention threshold, focus areas."""
    persona: Persona

    # Theme → relevance weight, 0..1
    theme_weights: dict[StoryTheme, float]

    # Below this priority, story is dropped for this persona
    priority_floor: float = 50.0

    # Max stories in briefing
    max_stories: int = 4

    # Whether this persona cares about good_news
    include_good_news: bool = True

    # Decision routing — what decisions this persona OWNS
    owns_decisions_about: list[str] = []

    def cluster_relevance(self, cluster: StoryCluster) -> float:
        """
        Returns 0..1 relevance for this cluster to this persona.
        Final ranking score = cluster.aggregate_priority × relevance.
        """
        base = self.theme_weights.get(cluster.theme, 0.3)
        # Boost for high $ exposure when persona cares about money
        if cluster.aggregate_exposure_usd > 100_000:
            base = min(1.0, base + 0.1)
        return base
