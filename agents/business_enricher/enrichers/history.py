from __future__ import annotations
from ..models import RawSignal, HistoryContext


async def enrich_history(
    signal: RawSignal, store,
) -> tuple[HistoryContext, list[str]]:
    flags: list[str] = []
    incidents = await store.lookup_incident_history(
        signal.service, signal.category.value, days=30,
    )

    if not incidents:
        return HistoryContext(occurrences_last_30d=0, trend="unknown"), flags

    occurrences = len(incidents)
    last = max((i.get("occurred_at") for i in incidents if i.get("occurred_at")), default=None)
    trend = "worsening" if occurrences >= 3 else "stable"

    return HistoryContext(
        occurrences_last_30d=occurrences,
        trend=trend,
        last_occurrence=last,
    ), flags
