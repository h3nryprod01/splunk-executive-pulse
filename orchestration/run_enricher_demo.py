"""
Zero-infra demo of the moat slice: a RawSignal (the payment-gateway outage
from the demo night) is enriched with business context loaded from the seed
CSVs — no Splunk, no Postgres required.

    python orchestration/run_enricher_demo.py
"""
from __future__ import annotations
import asyncio
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from agents.business_enricher.agent import BusinessEnricherAgent
from agents.business_enricher.tools import InMemoryContextStore
from agents.business_enricher.models import RawSignal, SignalCategory, SignalMagnitude

SEED_DIR = Path(__file__).resolve().parent.parent / "business_context" / "seed_data"


def payment_outage_signal() -> RawSignal:
    return RawSignal(
        signal_id="sig_demo_001",
        category=SignalCategory.ERROR_SPIKE,
        service="svc-001",
        started_at=datetime(2026, 5, 21, 2, 47, tzinfo=timezone.utc),
        ended_at=datetime(2026, 5, 21, 2, 59, tzinfo=timezone.utc),
        magnitude=SignalMagnitude(
            metric="http_5xx_count", value=47, baseline=2.3, deviation_sigma=8.4),
        splunk_query="index=prod sourcetype=payment-svc status>=500",
        correlation_ids=["deploy_v2.3.1"],
    )


async def main() -> None:
    store = InMemoryContextStore(SEED_DIR)
    await store.init()

    agent = BusinessEnricherAgent(store=store, mcp=store)
    out = await agent.run([payment_outage_signal()])

    print(json.dumps(out.model_dump(mode="json"), indent=2, default=str))

    sig = out.enriched_signals[0]
    ctx = sig.business_context
    print("\n--- Executive headline (raw inputs for the Narrative Writer) ---")
    print(f"service tier      : {ctx.revenue.service_tier}")
    print(f"revenue / minute  : ${ctx.revenue.revenue_per_minute_usd:,.0f}")
    print(f"customers affected: {ctx.customer.total_affected:,} "
          f"({ctx.customer.by_tier.enterprise} enterprise)")
    print(f"SLA breaches      : {ctx.sla.contracts_affected} contracts, "
          f"${ctx.sla.estimated_credit_liability_usd:,.0f} credit liability")
    print(f"regulated data    : {', '.join(ctx.compliance.regulated_data_touched) or 'none'}")
    print(f"confidence        : {ctx.enrichment_confidence:.2f}")


if __name__ == "__main__":
    asyncio.run(main())
