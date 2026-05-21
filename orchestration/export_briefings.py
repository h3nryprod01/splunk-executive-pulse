"""
Run the real deterministic pipeline (collector -> enricher -> quantifier ->
editor) for every persona and export dashboard-ready Briefing JSON to
web/public/briefings/<persona>-latest.json.

The Next.js dashboard's /api/briefing route serves these files, so the UI shows
data computed by the actual agents instead of static mock data.

    python orchestration/export_briefings.py
"""
from __future__ import annotations
import asyncio
import json
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
from orchestration.pipeline import MockSplunkClient

ROOT = Path(__file__).resolve().parent.parent
SEED_DIR = ROOT / "business_context" / "seed_data"
OUT_DIR = ROOT / "web" / "public" / "briefings"
BRIEFING_DATE = datetime(2026, 5, 21, 6, 30, tzinfo=timezone.utc)

# Demo-night top-line numbers (would come from a revenue/uptime SPL in prod).
REVENUE_USD = 2_300_000
UPTIME_PCT = 99.94
GOOD_NEWS = {
    "headline": "Black Friday capacity test passed",
    "summary": "All services held under a 3x peak load test overnight; "
               "we're ready for the holiday season.",
}


def _citations_for(qs) -> list[dict]:
    return [
        {
            "claim_text": f"${step.result_usd:,.0f} {step.label.lower()}"
            if step.result_usd else step.label,
            "methodology": step.formula,
            "confidence": step.confidence,
            "splunk_query": qs.enriched.raw_signal.splunk_query,
        }
        for step in qs.financial_impact.calculations
    ]


def _story(cluster, qs_index) -> dict:
    qs = qs_index.get(cluster.primary_signal_id)
    affected = qs.customer_impact.affected_count if qs else None
    duration = round(qs.enriched.raw_signal.duration_minutes) if qs else None
    qualitative = bool(qs and qs.qualitative_only)
    return {
        "cluster_id": cluster.cluster_id,
        "theme": cluster.theme.value,
        "headline": cluster.headline_hint,
        "summary": cluster.headline_hint,
        "exposure_usd": round(cluster.aggregate_exposure_usd),
        "priority_score": round(cluster.aggregate_priority, 1),
        "affected_customers": affected,
        "duration_min": duration,
        # When confidence is too low we withhold the dollar figures (no citations).
        "citations": [] if qualitative else (_citations_for(qs) if qs else []),
        "drill_down_url": "#",
        "qualitative_only": qualitative,
    }


def _decision(d) -> dict:
    return {
        "decision_id": d.decision_id,
        "title": d.title,
        "context": d.context_one_liner,
        "options": d.options,
        "cost_usd": d.cost_usd,
        "deadline": d.deadline.isoformat() if d.deadline else "",
        "owner": d.owner,
    }


async def build_briefing(persona: Persona) -> dict:
    config = CollectorConfig(
        time_window_start=datetime(2026, 5, 21, 0, 0, tzinfo=timezone.utc),
        time_window_end=datetime(2026, 5, 21, 23, 59, tzinfo=timezone.utc),
        enabled_detectors=[
            SignalCategory.ERROR_SPIKE, SignalCategory.SECURITY, SignalCategory.LATENCY,
        ],
    )
    collected = await SignalCollectorAgent(splunk=MockSplunkClient(), config=config).run()

    store = InMemoryContextStore(SEED_DIR)
    await store.init()
    signals = [EnricherRawSignal.model_validate(s.model_dump(mode="json"))
               for s in collected.signals]
    enriched = await BusinessEnricherAgent(store=store, mcp=store).run(signals)

    quantified = ImpactQuantifierAgent().run(enriched)
    qs_index = {qs.signal_id: qs for qs in quantified.quantified_signals}

    editor = ExecutiveEditorAgent().edit(quantified, persona=persona,
                                         briefing_date=BRIEFING_DATE)

    headline = next((c for c in editor.clusters
                     if c.cluster_id == editor.headline_cluster_id), None)
    quote = (f"{headline.headline_hint}." if headline
             else "Here is your briefing for the night.")

    return {
        "persona": persona.value,
        "briefing_date": BRIEFING_DATE.date().isoformat(),
        "audio_url": "",
        "duration_sec": 178,
        "word_count": 0,
        "total_exposure_usd": round(editor.total_exposure_usd_shown),
        "uptime_pct": UPTIME_PCT,
        "revenue_usd": REVENUE_USD,
        "headline_quote": quote,
        "stories": [_story(c, qs_index) for c in editor.clusters],
        "decisions": [_decision(d) for d in editor.decisions_required],
        "good_news": GOOD_NEWS,
    }


async def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    for persona in Persona:
        briefing = await build_briefing(persona)
        text = json.dumps(briefing, indent=2)
        slug = persona.value.lower()
        (OUT_DIR / f"{slug}-latest.json").write_text(text)
        (OUT_DIR / f"{slug}-{briefing['briefing_date']}.json").write_text(text)
        print(f"  {persona.value}: {len(briefing['stories'])} stories, "
              f"${briefing['total_exposure_usd']:,} exposure, "
              f"headline={briefing['stories'][0]['theme'] if briefing['stories'] else '—'}")
    print(f"Wrote briefings to {OUT_DIR}")


if __name__ == "__main__":
    asyncio.run(main())
