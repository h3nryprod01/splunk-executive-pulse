import pytest
from datetime import datetime, timezone
from unittest.mock import AsyncMock

from agents.business_enricher.agent import BusinessEnricherAgent
from agents.business_enricher.models import RawSignal, SignalCategory, SignalMagnitude


@pytest.fixture
def payment_outage_signal() -> RawSignal:
    return RawSignal(
        signal_id="sig_001",
        category=SignalCategory.ERROR_SPIKE,
        service="svc-001",
        started_at=datetime(2026, 5, 21, 2, 47, tzinfo=timezone.utc),
        ended_at=datetime(2026, 5, 21, 2, 59, tzinfo=timezone.utc),
        magnitude=SignalMagnitude(
            metric="http_5xx_count", value=47, baseline=2.3,
            deviation_sigma=8.4,
        ),
        splunk_query='index=prod sourcetype=payment-svc status>=500',
        correlation_ids=["deploy_v2.3.1"],
        raw_sample_size=47,
    )


@pytest.fixture
def mock_store():
    store = AsyncMock()
    store.lookup_service.return_value = {
        "service_id": "svc-001",
        "service_name": "payment-api",
        "tier": "tier-0",
        "revenue_per_min_usd": 3916.0,
        "revenue_critical": True,
        "business_function": "payments",
        "customer_facing": True,
        "regulated_data": ["PCI"],
    }
    store.lookup_affected_customers.return_value = [
        {"customer_id": f"c{i}", "customer_name": f"Customer {i}",
         "tier": "enterprise" if i < 34 else "smb",
         "acv_usd": 480000 if i < 34 else 12000,
         "churn_risk_base": 0.04, "named_account": i < 5,
         "failed_txns": 3}
        for i in range(1247)
    ]
    store.lookup_sla_breaches.return_value = [
        {"contract_id": f"sla-{i}", "customer_id": f"c{i}",
         "credit_owed_usd": 18000.0, "uptime_target_pct": 99.95,
         "credit_pct_per_breach": 10, "monthly_fee_usd": 180000}
        for i in range(12)
    ]
    store.lookup_incident_history.return_value = [
        {"incident_id": "inc-099", "occurred_at": datetime(2026, 5, 14)}
    ]
    return store


@pytest.mark.asyncio
async def test_payment_outage_enrichment(payment_outage_signal, mock_store):
    mcp = AsyncMock()
    mcp.calls_made = 0
    agent = BusinessEnricherAgent(store=mock_store, mcp=mcp)

    result = await agent.enrich_one(payment_outage_signal)

    ctx = result.business_context
    assert ctx.revenue.service_tier == "tier-0"
    assert ctx.revenue.revenue_per_minute_usd == 3916.0
    assert ctx.customer.total_affected == 1247
    assert ctx.customer.by_tier.enterprise == 34
    assert ctx.sla.breached is True
    assert ctx.sla.contracts_affected == 12
    assert "PCI" in ctx.compliance.regulated_data_touched
    assert ctx.enrichment_confidence > 0.7
    assert result.needs_manual_review is False


@pytest.mark.asyncio
async def test_unknown_service_lowers_confidence(payment_outage_signal, mock_store):
    mock_store.lookup_service.return_value = None
    mcp = AsyncMock(); mcp.calls_made = 0
    agent = BusinessEnricherAgent(store=mock_store, mcp=mcp)

    result = await agent.enrich_one(payment_outage_signal)

    assert result.business_context.revenue.service_tier == "unknown"
    assert result.business_context.enrichment_confidence < 0.5
    assert result.needs_manual_review is True
    assert any("not found in catalog" in f
               for f in result.business_context.missing_data_flags)


@pytest.mark.asyncio
async def test_partial_enricher_failure_does_not_crash(payment_outage_signal, mock_store):
    mock_store.lookup_sla_breaches.side_effect = RuntimeError("DB timeout")
    mcp = AsyncMock(); mcp.calls_made = 0
    agent = BusinessEnricherAgent(store=mock_store, mcp=mcp)

    result = await agent.enrich_one(payment_outage_signal)

    # Other enrichers should still succeed
    assert result.business_context.revenue.service_tier == "tier-0"
    # Failed enricher should leave a flag
    assert any("sla_enricher_failed" in f
               for f in result.business_context.missing_data_flags)
