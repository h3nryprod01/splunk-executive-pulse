# agents/impact_quantifier/tests/test_no_inflation.py
"""
The Impact Quantifier MUST be deterministic. Same input → same $.
This guards against LLM creep or non-deterministic side effects.
"""
import pytest
from datetime import datetime, timezone
from agents.impact_quantifier.agent import ImpactQuantifierAgent
from agents.business_enricher.models import (
    EnrichedSignal, EnricherOutput, BusinessContext,
    RevenueContext, CustomerContext, CustomerTierBreakdown,
    SLAContext, ComplianceContext, HistoryContext,
    RawSignal, SignalCategory, SignalMagnitude,
)


@pytest.fixture
def payment_outage_enriched():
    raw = RawSignal(
        signal_id="sig_001",
        category=SignalCategory.ERROR_SPIKE,
        service="svc-001",
        started_at=datetime(2026,5,21,2,47,tzinfo=timezone.utc),
        ended_at=datetime(2026,5,21,2,59,tzinfo=timezone.utc),
        magnitude=SignalMagnitude(metric="http_5xx_count", value=47,
                                  baseline=2.3, deviation_sigma=8.4),
        splunk_query="index=prod ...",
        raw_sample_size=47,
    )
    ctx = BusinessContext(
        revenue=RevenueContext(service_tier="tier-0",
                               revenue_per_minute_usd=3916.0,
                               revenue_critical=True,
                               business_function="payments"),
        customer=CustomerContext(
            total_affected=1247,
            by_tier=CustomerTierBreakdown(enterprise=34, mid_market=210,
                                          smb=1003, free=0),
            named_accounts=["Acme Corp", "Globex Inc"],
            customer_facing=True,
        ),
        sla=SLAContext(breached=True, contracts_affected=12,
                       estimated_credit_liability_usd=18000.0),
        compliance=ComplianceContext(
            regulated_data_touched=["PCI"],
            reportable_to_regulator=False,
            reputation_risk_score=3,
        ),
        history=HistoryContext(occurrences_last_30d=2, trend="worsening"),
        enrichment_confidence=0.85,
        missing_data_flags=[],
    )
    return EnrichedSignal(signal_id="sig_001", raw_signal=raw,
                          business_context=ctx, needs_manual_review=False)


def test_deterministic_dollars(payment_outage_enriched):
    """Run quantifier 5x — every $ figure must be identical."""
    agent = ImpactQuantifierAgent()
    runs = [agent.quantify_one(payment_outage_enriched) for _ in range(5)]

    references = runs[0].financial_impact
    for r in runs[1:]:
        assert r.financial_impact.direct_revenue_loss_usd == references.direct_revenue_loss_usd
        assert r.financial_impact.indirect_exposure_usd == references.indirect_exposure_usd
        assert r.financial_impact.sla_credit_liability_usd == references.sla_credit_liability_usd
        assert r.financial_impact.total_exposure_usd == references.total_exposure_usd
        assert r.priority_score == runs[0].priority_score


def test_every_dollar_has_citation(payment_outage_enriched):
    agent = ImpactQuantifierAgent()
    result = agent.quantify_one(payment_outage_enriched)

    # Every non-zero $ field must be backed by at least one CalculationStep
    fi = result.financial_impact
    if fi.direct_revenue_loss_usd > 0:
        assert any("Direct revenue" in s.label for s in fi.calculations)
    if fi.indirect_exposure_usd > 0:
        assert any("churn" in s.label.lower() for s in fi.calculations)
    if fi.sla_credit_liability_usd > 0:
        assert any("SLA" in s.label for s in fi.calculations)

    # Each step must have a formula AND inputs
    for s in fi.calculations:
        assert s.formula
        assert s.inputs
        assert s.confidence > 0


def test_low_confidence_triggers_qualitative_only(payment_outage_enriched):
    """When enrichment confidence is poor, refuse to quote $."""
    payment_outage_enriched.business_context.enrichment_confidence = 0.3

    agent = ImpactQuantifierAgent()
    result = agent.quantify_one(payment_outage_enriched)

    assert result.qualitative_only is True


def test_revenue_calc_math(payment_outage_enriched):
    """Hand-check the most important number."""
    agent = ImpactQuantifierAgent()
    result = agent.quantify_one(payment_outage_enriched)

    # $3916/min × 12 min × 100% = $46,992
    expected = 3916 * 12 * 1.0
    assert abs(result.financial_impact.direct_revenue_loss_usd - expected) < 1.0
