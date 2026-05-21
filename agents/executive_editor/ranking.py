from __future__ import annotations
from .models import StoryCluster, Persona
from .persona.base import BasePersonaProfile

# How strongly the persona "lens" dominates raw priority. >1 makes relevance
# super-linear so each role's headline reflects what THAT executive cares about
# (e.g. the CISO leads with a blocked-but-serious attack even when a larger-$
# revenue incident exists), instead of every persona headlining the biggest $.
RELEVANCE_EXPONENT = 2.0


def rank_clusters(
    clusters: list[StoryCluster], persona: BasePersonaProfile,
) -> list[StoryCluster]:
    """
    Compute persona-specific final score, filter by floor, sort desc.
    Mutates cluster.persona_relevance to record the score for downstream UI.
    """
    scored = []
    for c in clusters:
        relevance = persona.cluster_relevance(c)
        c.persona_relevance[persona.persona.value] = round(relevance, 2)
        final_score = c.aggregate_priority * (relevance ** RELEVANCE_EXPONENT)
        if final_score >= persona.priority_floor * 0.5:  # softer floor (relevance-aware)
            scored.append((final_score, c))

    scored.sort(key=lambda t: t[0], reverse=True)
    return [c for _, c in scored]
