"""
Anti-hallucination gate demo (keyless): when the Business Enricher can't
confidently identify a signal's context, enrichment confidence drops below the
threshold and the Impact Quantifier refuses to quote dollars
(qualitative_only=True). The briefing then uses qualitative language only —
never a fabricated number.

    python orchestration/qualitative_demo.py
"""
from __future__ import annotations
import asyncio
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from agents.business_enricher.agent import BusinessEnricherAgent
from agents.business_enricher.tools import InMemoryContextStore
from agents.business_enricher.models import RawSignal, SignalCategory, SignalMagnitude
from agents.impact_quantifier.agent import ImpactQuantifierAgent, QUALITATIVE_ONLY_THRESHOLD

SEED_DIR = Path(__file__).resolve().parent.parent / "business_context" / "seed_data"


def signal(service: str) -> RawSignal:
    return RawSignal(
        signal_id=f"sig_{service}",
        category=SignalCategory.ERROR_SPIKE,
        service=service,
        started_at=datetime(2026, 5, 21, 2, 47, tzinfo=timezone.utc),
        ended_at=datetime(2026, 5, 21, 2, 59, tzinfo=timezone.utc),
        magnitude=SignalMagnitude(metric="http_5xx_count", value=47, baseline=2.3,
                                  deviation_sigma=8.4),
        splunk_query="index=prod status>=500",
    )


async def main() -> None:
    store = InMemoryContextStore(SEED_DIR)
    await store.init()
    enricher = BusinessEnricherAgent(store=store, mcp=store)
    quant = ImpactQuantifierAgent()

    # Case A: a normal night — full, trusted business context.
    a = await enricher.enrich_one(signal("svc-001"))
    # Case B: a degraded night — overnight data sources were incomplete, so the
    # enricher reports low confidence (simulated here by lowering the score).
    b = await enricher.enrich_one(signal("svc-001"))
    b.business_context.enrichment_confidence = 0.30

    for enriched, label in [
        (a, "NORMAL night — full, trusted business context"),
        (b, "DEGRADED night — overnight context sources incomplete/low-confidence"),
    ]:
        q = quant.quantify_one(enriched)
        print(f"\n{label}")
        print(f"  enrichment confidence  : {enriched.business_context.enrichment_confidence:.2f}")
        print(f"  financial confidence   : {q.financial_impact.aggregated_confidence:.2f}")
        print(f"  qualitative_only       : {q.qualitative_only}")
        if q.qualitative_only:
            print("  -> briefing uses QUALITATIVE language only; the dollar figure is withheld.")
        else:
            print(f"  -> briefing quotes ${q.financial_impact.total_exposure_usd:,.0f}, every figure cited.")

    print("\nGuarantee: when confidence falls below "
          f"{QUALITATIVE_ONLY_THRESHOLD:.0%}, the pipeline withholds the number "
          "rather than fabricate one.")


if __name__ == "__main__":
    asyncio.run(main())
