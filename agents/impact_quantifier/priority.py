# agents/impact_quantifier/priority.py
"""
Priority score = weighted blend of financial, customer, compliance, reputation.
Range 0-100. Used by Executive Editor to rank stories.
"""
from __future__ import annotations
import math
from agents.business_enricher.models import EnrichedSignal
from .models import FinancialImpact, CustomerImpactScore


WEIGHTS = {
    "financial":   0.40,
    "customer":    0.30,
    "compliance":  0.20,
    "reputation":  0.10,
}


def normalize_financial(total_usd: float) -> float:
    """Log-scaled normalization: $1K=20, $10K=40, $100K=60, $1M=80, $10M=100"""
    if total_usd <= 0:
        return 0.0
    return min(100.0, 20.0 * math.log10(max(1.0, total_usd)))


def normalize_customer(score: float) -> float:
    """Already pre-weighted by tier; cap at 100."""
    return min(100.0, score)


def normalize_compliance(signal: EnrichedSignal) -> float:
    c = signal.business_context.compliance
    s = 0.0
    if c.reportable_to_regulator:
        s += 60.0
    if c.regulated_data_touched:
        s += 25.0
    s += min(15.0, len(c.regulated_data_touched) * 5.0)
    return min(100.0, s)


def normalize_reputation(signal: EnrichedSignal) -> float:
    return signal.business_context.compliance.reputation_risk_score * 20.0  # 1-5 → 20-100


def compute_priority_score(
    signal: EnrichedSignal,
    financial: FinancialImpact,
    customer: CustomerImpactScore,
) -> float:
    fin = normalize_financial(financial.total_exposure_usd)
    cust = normalize_customer(customer.tier_weighted_score)
    comp = normalize_compliance(signal)
    rep = normalize_reputation(signal)

    score = (
        WEIGHTS["financial"]  * fin +
        WEIGHTS["customer"]   * cust +
        WEIGHTS["compliance"] * comp +
        WEIGHTS["reputation"] * rep
    )
    return round(score, 1)


def compute_customer_score(signal: EnrichedSignal) -> CustomerImpactScore:
    """Tier-weighted: enterprise=10, mid=3, smb=1, free=0.1"""
    c = signal.business_context.customer
    weighted = (
        c.by_tier.enterprise * 10 +
        c.by_tier.mid_market *  3 +
        c.by_tier.smb        *  1 +
        c.by_tier.free       *  0.1
    )
    # Normalize: enterprise=34 already saturates
    return CustomerImpactScore(
        affected_count=c.total_affected,
        tier_weighted_score=min(100.0, weighted),
        named_accounts_affected=c.named_accounts,
    )
