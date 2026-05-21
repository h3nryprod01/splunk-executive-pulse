"""
Deterministic backbone of the Executive Pulse pipeline, runnable with zero
infrastructure and zero API keys:

    Signal Collector (mock Splunk) -> Business Enricher (CSV store)
        -> Impact Quantifier -> Executive Editor (per persona)

The LLM-backed Narrative Writer and the ElevenLabs Audio Producer sit after
the Editor and are intentionally NOT invoked here (they need credentials).

    python orchestration/pipeline.py --persona CEO
"""
from __future__ import annotations
import argparse
import asyncio
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from agents.signal_collector.agent import SignalCollectorAgent
from agents.signal_collector.models import CollectorConfig, SignalCategory
from agents.business_enricher.agent import BusinessEnricherAgent
from agents.business_enricher.tools import InMemoryContextStore
from agents.business_enricher.models import RawSignal as EnricherRawSignal
from agents.impact_quantifier.agent import ImpactQuantifierAgent
from agents.executive_editor.agent import ExecutiveEditorAgent
from agents.executive_editor.models import Persona

SEED_DIR = Path(__file__).resolve().parent.parent / "business_context" / "seed_data"


class MockSplunkClient:
    """
    Stands in for SplunkMCPSearchClient: replays the scripted demo night
    (20→21 May). Routes by SPL fingerprint so each detector gets its rows:
      Story A — payment 5xx spike (revenue)   -> error_spike detector
      Story B — credential stuffing (security) -> security detector
      Story C — checkout latency burn (ops)    -> latency detector
    """

    def __init__(self) -> None:
        self.searches_executed = 0

    async def search(self, spl: str, earliest=None, latest=None, max_count=10000):
        self.searches_executed += 1

        if "status>=500" in spl:                       # Story A
            return [
                {"_time": "2026-05-21T02:47:00Z", "service": "payment-api",
                 "error_count": 18, "baseline_avg": 2.3, "sigma_deviation": 8.1},
                {"_time": "2026-05-21T02:48:00Z", "service": "payment-api",
                 "error_count": 16, "baseline_avg": 2.3, "sigma_deviation": 7.6},
                {"_time": "2026-05-21T02:49:00Z", "service": "payment-api",
                 "error_count": 13, "baseline_avg": 2.3, "sigma_deviation": 6.2},
            ]
        if "index=security" in spl:                    # Story B
            return [
                {"window_start": "2026-05-21T01:15:00Z",
                 "window_end": "2026-05-21T04:30:00Z",
                 "total_attempts": 340000, "baseline_attempts": 1200,
                 "sigma": 11.4, "top_asn": "AS4837", "unique_ips": 12000},
            ]
        if "sourcetype IN" in spl and "span=1h" in spl:  # Story C
            return [
                {"_time": "2026-05-21T00:00:00Z", "service": "checkout-api",
                 "latency_metric": "p99_ms", "latency_value": 612,
                 "baseline_value": 380, "sigma": 4.2,
                 "window_min": 60, "request_count": 184000},
            ]
        return []


def _to_enricher_signal(sig) -> EnricherRawSignal:
    """Collector RawSignal -> Enricher RawSignal (contract-identical schemas)."""
    return EnricherRawSignal.model_validate(sig.model_dump(mode="json"))


async def run_backbone(persona: Persona) -> None:
    # 1. Signal Collector (mock Splunk)
    config = CollectorConfig(
        time_window_start=datetime(2026, 5, 21, 0, 0, tzinfo=timezone.utc),
        time_window_end=datetime(2026, 5, 21, 23, 59, tzinfo=timezone.utc),
        enabled_detectors=[
            SignalCategory.ERROR_SPIKE,
            SignalCategory.SECURITY,
            SignalCategory.LATENCY,
        ],
    )
    collector = SignalCollectorAgent(splunk=MockSplunkClient(), config=config)
    collected = await collector.run()
    print(f"[1] Signal Collector: {len(collected.signals)} signal(s), "
          f"{collected.splunk_searches_executed} search(es)")

    # 2. Business Enricher (CSV-backed store)
    store = InMemoryContextStore(SEED_DIR)
    await store.init()
    enricher = BusinessEnricherAgent(store=store, mcp=store)
    enriched = await enricher.run([_to_enricher_signal(s) for s in collected.signals])
    print(f"[2] Business Enricher: {len(enriched.enriched_signals)} enriched, "
          f"confidence={enriched.enriched_signals[0].business_context.enrichment_confidence:.2f}")

    # 3. Impact Quantifier (deterministic $ math)
    quantifier = ImpactQuantifierAgent()
    quantified = quantifier.run(enriched)
    print(f"[3] Impact Quantifier: total exposure ${quantified.total_exposure_usd:,.0f}, "
          f"top priority {quantified.highest_priority_score:.0f}/100")

    # 4. Executive Editor (persona-ranked briefing)
    editor = ExecutiveEditorAgent()
    brief = editor.edit(quantified, persona=persona)
    print(f"[4] Executive Editor ({persona.value}): {len(brief.clusters)} stories, "
          f"${brief.total_exposure_usd_shown:,.0f} shown, "
          f"{len(brief.decisions_required)} decision(s)")

    print("\n--- Briefing skeleton (input to Narrative Writer) ---")
    for c in brief.clusters:
        marker = "  HEADLINE" if c.cluster_id == brief.headline_cluster_id else ""
        print(f"  [{c.theme.value}] exposure ${c.aggregate_exposure_usd:,.0f}{marker}")
    for d in brief.decisions_required:
        print(f"  DECISION: {d.model_dump()}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--persona", default="CEO",
                        choices=[p.value for p in Persona])
    args = parser.parse_args()
    asyncio.run(run_backbone(Persona(args.persona)))


if __name__ == "__main__":
    main()
