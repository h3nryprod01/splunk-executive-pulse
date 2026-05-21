"""
Cluster related QuantifiedSignals into StoryClusters.

Strategy:
  1. Group by (service, time-proximity, theme)
  2. Within group, pick highest-priority signal as primary
  3. Detect theme heuristically from category + business_context
"""
from __future__ import annotations
import logging
import uuid
from datetime import timedelta
from collections import defaultdict

from agents.impact_quantifier.models import QuantifiedSignal
from .models import StoryCluster, StoryTheme

logger = logging.getLogger(__name__)

TIME_PROXIMITY_HOURS = 2  # signals within this window may cluster


def infer_theme(signal: QuantifiedSignal) -> StoryTheme:
    """Map a single signal to its story theme."""
    cat = signal.enriched.raw_signal.category.value
    ctx = signal.enriched.business_context

    if cat == "security":
        return StoryTheme.SECURITY_THREAT
    if cat == "cost":
        return StoryTheme.COST_OVERRUN
    if cat == "deploy":
        return StoryTheme.DEPLOY_INCIDENT
    if cat == "capacity":
        return StoryTheme.CAPACITY_RISK
    if cat == "latency":
        return StoryTheme.PERFORMANCE_DEGRAD
    if cat in ("error_spike", "availability"):
        if ctx.revenue.revenue_critical:
            return StoryTheme.REVENUE_INCIDENT
        return StoryTheme.PERFORMANCE_DEGRAD
    return StoryTheme.UNKNOWN


def cluster_signals(signals: list[QuantifiedSignal]) -> list[StoryCluster]:
    """
    Two-pass clustering:
      Pass 1: group by (service, theme) within time proximity
      Pass 2: merge clusters that share correlation_ids
              (e.g., a deploy event explains an error spike)
    """
    if not signals:
        return []

    # Sort by start time for proximity logic
    sorted_sigs = sorted(
        signals, key=lambda s: s.enriched.raw_signal.started_at
    )

    # PASS 1 — bucket by (service, theme)
    buckets: dict[tuple[str, StoryTheme], list[QuantifiedSignal]] = defaultdict(list)
    for s in sorted_sigs:
        theme = infer_theme(s)
        buckets[(s.enriched.raw_signal.service, theme)].append(s)

    # Within each bucket, split if time gap > proximity window
    initial_clusters: list[list[QuantifiedSignal]] = []
    for (_, _), group in buckets.items():
        current: list[QuantifiedSignal] = []
        last_end = None
        for sig in group:
            start = sig.enriched.raw_signal.started_at
            if last_end and (start - last_end) > timedelta(hours=TIME_PROXIMITY_HOURS):
                initial_clusters.append(current)
                current = []
            current.append(sig)
            last_end = sig.enriched.raw_signal.ended_at
        if current:
            initial_clusters.append(current)

    # PASS 2 — merge across services if correlation_ids overlap
    merged = _merge_by_correlation(initial_clusters)

    # Build StoryCluster objects
    clusters: list[StoryCluster] = []
    for group in merged:
        primary = max(group, key=lambda s: s.priority_score)
        theme = infer_theme(primary)
        cluster_id = f"cl_{uuid.uuid4().hex[:8]}"

        # Aggregate priority via max + tiebreaker by count
        agg_priority = max(s.priority_score for s in group)
        agg_exposure = sum(s.financial_impact.total_exposure_usd for s in group)

        headline_hint = _headline_hint(theme, primary, len(group))

        clusters.append(StoryCluster(
            cluster_id=cluster_id,
            theme=theme,
            headline_hint=headline_hint,
            signal_ids=[s.signal_id for s in group],
            primary_signal_id=primary.signal_id,
            aggregate_priority=agg_priority,
            aggregate_exposure_usd=round(agg_exposure, 2),
            persona_relevance={},  # filled by ranking module
        ))

    return clusters


def _merge_by_correlation(
    clusters: list[list[QuantifiedSignal]],
) -> list[list[QuantifiedSignal]]:
    """Union-find merge on shared correlation_ids."""
    n = len(clusters)
    parent = list(range(n))

    def find(i):
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i

    def union(i, j):
        ri, rj = find(i), find(j)
        if ri != rj:
            parent[ri] = rj

    # Build correlation_id → cluster index map
    for i in range(n):
        ids_i = set()
        for s in clusters[i]:
            ids_i.update(s.enriched.raw_signal.correlation_ids)
        for j in range(i + 1, n):
            ids_j = set()
            for s in clusters[j]:
                ids_j.update(s.enriched.raw_signal.correlation_ids)
            # Meaningful correlation: shared deploy version, etc.
            shared = ids_i & ids_j
            if any(":" in c for c in shared):  # filter trivial empties
                union(i, j)

    groups: dict[int, list[QuantifiedSignal]] = defaultdict(list)
    for i in range(n):
        groups[find(i)].extend(clusters[i])
    return list(groups.values())


def _headline_hint(theme: StoryTheme, primary: QuantifiedSignal, n_signals: int) -> str:
    """Short string for downstream writer scaffold — NOT final headline."""
    svc = primary.enriched.raw_signal.service
    if theme == StoryTheme.REVENUE_INCIDENT:
        dur = int(primary.enriched.raw_signal.duration_minutes)
        return f"{svc} revenue incident · {dur}min · ${primary.financial_impact.total_exposure_usd:,.0f} exposure"
    if theme == StoryTheme.SECURITY_THREAT:
        return f"security event on {svc} · {n_signals} related signal(s)"
    if theme == StoryTheme.PERFORMANCE_DEGRAD:
        return f"{svc} performance degradation"
    if theme == StoryTheme.COST_OVERRUN:
        return f"infrastructure cost overrun · {svc}"
    if theme == StoryTheme.DEPLOY_INCIDENT:
        return f"deploy-related incident on {svc}"
    return f"{theme.value} on {svc}"
