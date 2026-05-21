from __future__ import annotations
from ..models import RawSignal, ComplianceContext, SignalCategory

# Regulated-data classes that, if touched, are reportable to a regulator.
_REPORTABLE = {"PCI", "PHI", "GDPR"}


async def enrich_compliance(
    signal: RawSignal, store,
) -> tuple[ComplianceContext, list[str]]:
    flags: list[str] = []
    svc = await store.lookup_service(signal.service)

    if svc is None:
        flags.append(f"service '{signal.service}' not found for compliance lookup")
        return ComplianceContext(), flags

    regulated = svc.get("regulated_data") or []
    if isinstance(regulated, str):
        regulated = [d for d in regulated.split(",") if d]

    reportable = bool(set(regulated) & _REPORTABLE)
    risk = _reputation_risk(signal.category, bool(regulated), svc.get("customer_facing"))

    return ComplianceContext(
        regulated_data_touched=regulated,
        reportable_to_regulator=reportable,
        reputation_risk_score=risk,
    ), flags


def _reputation_risk(category: SignalCategory, regulated: bool, customer_facing) -> int:
    score = 1
    if customer_facing:
        score += 1
    if regulated:
        score += 1
    if category in (SignalCategory.SECURITY, SignalCategory.AVAILABILITY):
        score += 2
    return max(1, min(5, score))
