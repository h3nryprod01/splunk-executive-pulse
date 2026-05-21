from __future__ import annotations
from ..models import RawSignal, SLAContext


async def enrich_sla(
    signal: RawSignal, store,
) -> tuple[SLAContext, list[str]]:
    flags: list[str] = []
    breaches = await store.lookup_sla_breaches(
        signal.service, signal.started_at, signal.ended_at,
        signal.duration_minutes,
    )

    if not breaches:
        return SLAContext(), flags

    total_credit = sum(float(b.get("credit_owed_usd", 0.0)) for b in breaches)
    return SLAContext(
        breached=True,
        contracts_affected=len(breaches),
        estimated_credit_liability_usd=round(total_credit, 2),
        breached_customer_ids=sorted(
            {b["customer_id"] for b in breaches if b.get("customer_id")}
        ),
    ), flags
