"""
Heuristic decision extraction from clusters.
Each cluster type can spawn 0-1 decisions framed for the persona.
"""
from __future__ import annotations
import uuid
from datetime import datetime, timedelta

from agents.impact_quantifier.models import QuantifiedSignal
from .models import StoryCluster, StoryTheme, DecisionAsk
from .persona.base import BasePersonaProfile


def extract_decisions(
    clusters: list[StoryCluster],
    signals_by_id: dict[str, QuantifiedSignal],
    persona: BasePersonaProfile,
) -> list[DecisionAsk]:
    decisions: list[DecisionAsk] = []
    for cluster in clusters:
        primary = signals_by_id[cluster.primary_signal_id]
        d = _decision_from_cluster(cluster, primary, persona)
        if d:
            decisions.append(d)
    return decisions[:3]  # cap


def _decision_from_cluster(
    cluster: StoryCluster, primary: QuantifiedSignal,
    persona: BasePersonaProfile,
) -> DecisionAsk | None:
    theme = cluster.theme
    history = primary.enriched.business_context.history

    # === Security pattern → MFA / WAF investment ===
    if theme == StoryTheme.SECURITY_THREAT and history.occurrences_last_30d >= 3:
        if "security-investment" in persona.owns_decisions_about or \
           persona.persona.value in ("CEO", "CFO", "CISO"):
            return DecisionAsk(
                decision_id=f"dec_{uuid.uuid4().hex[:8]}",
                title="Approve MFA rollout for tier-2 users",
                context_one_liner=f"{history.occurrences_last_30d} similar attacks in last 30 days; trend worsening.",
                options=[
                    {"label": "Approve", "cost_usd": 240000,
                     "benefit": "Eliminates this attack vector"},
                    {"label": "Defer 30 days",
                     "risk": "Attack frequency likely continues to rise"},
                    {"label": "Discuss in exec meeting"},
                ],
                cost_usd=240000,
                deadline=datetime.utcnow() + timedelta(days=7),
                owner="CISO",
                supporting_cluster_ids=[cluster.cluster_id],
            )

    # === Cost overrun → budget approval ===
    if theme == StoryTheme.COST_OVERRUN and cluster.aggregate_exposure_usd > 50_000:
        if persona.persona.value in ("CFO", "CEO", "CTO"):
            return DecisionAsk(
                decision_id=f"dec_{uuid.uuid4().hex[:8]}",
                title="Approve infrastructure budget overage",
                context_one_liner=f"Q2 spend tracking +18% vs budget; driven by ad-hoc GPU jobs.",
                options=[
                    {"label": "Approve overage", "cost_usd": 75000},
                    {"label": "Throttle workloads",
                     "risk": "Delays data-science roadmap ~2 weeks"},
                    {"label": "Discuss in exec meeting"},
                ],
                cost_usd=75000,
                deadline=datetime.utcnow() + timedelta(days=5),
                owner="CFO",
                supporting_cluster_ids=[cluster.cluster_id],
            )

    # === Performance degradation → engineering investment ===
    if theme == StoryTheme.PERFORMANCE_DEGRAD and cluster.aggregate_exposure_usd > 100_000:
        if persona.persona.value in ("CTO", "COO"):
            return DecisionAsk(
                decision_id=f"dec_{uuid.uuid4().hex[:8]}",
                title="Authorize emergency checkout perf fix",
                context_one_liner="7-day latency regression now impacting conversion.",
                options=[
                    {"label": "Approve sprint reprioritization"},
                    {"label": "Wait for next sprint",
                     "risk": f"~${cluster.aggregate_exposure_usd:,.0f}/month exposure continues"},
                ],
                deadline=datetime.utcnow() + timedelta(days=3),
                owner="CTO",
                supporting_cluster_ids=[cluster.cluster_id],
            )

    return None
