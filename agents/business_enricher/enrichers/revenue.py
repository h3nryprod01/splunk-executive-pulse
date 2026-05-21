"""
Revenue context enrichment.
Looks up service tier, revenue-per-minute, criticality.
"""
from __future__ import annotations
from ..models import RawSignal, RevenueContext


async def enrich_revenue(
    signal: RawSignal, store,
) -> tuple[RevenueContext, list[str]]:
    """
    Returns (context, missing_data_flags).
    missing_data_flags is a list of human-readable strings about gaps.
    """
    flags: list[str] = []
    svc = await store.lookup_service(signal.service)

    if svc is None:
        flags.append(f"service '{signal.service}' not found in catalog")
        return RevenueContext(service_tier="unknown"), flags

    return RevenueContext(
        service_tier=svc.get("tier", "unknown"),
        revenue_per_minute_usd=svc.get("revenue_per_min_usd"),
        revenue_critical=svc.get("revenue_critical", False),
        business_function=svc.get("business_function"),
    ), flags
