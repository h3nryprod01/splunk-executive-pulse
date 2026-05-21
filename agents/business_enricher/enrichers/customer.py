from __future__ import annotations
from ..models import RawSignal, CustomerContext, CustomerTierBreakdown


async def enrich_customer(
    signal: RawSignal, store,
) -> tuple[CustomerContext, list[str]]:
    flags: list[str] = []
    customers = await store.lookup_affected_customers(
        signal.service, signal.started_at, signal.ended_at,
    )

    if not customers:
        # Could mean: zero impact, OR no transaction log for service
        svc = await store.lookup_service(signal.service)
        if svc and svc.get("customer_facing"):
            flags.append("customer-facing service but no transactions found in window")
        return CustomerContext(), flags

    breakdown = CustomerTierBreakdown()
    named = []
    for c in customers:
        tier = c["tier"]
        if tier == "enterprise":
            breakdown.enterprise += 1
        elif tier == "mid-market":
            breakdown.mid_market += 1
        elif tier == "smb":
            breakdown.smb += 1
        elif tier == "free":
            breakdown.free += 1
        if c.get("named_account"):
            named.append(c["customer_name"])

    svc = await store.lookup_service(signal.service)
    return CustomerContext(
        total_affected=len(customers),
        by_tier=breakdown,
        named_accounts=sorted(named)[:5],   # cap for executive brevity
        customer_facing=bool(svc and svc.get("customer_facing")),
    ), flags
