"""
Live briefing export: runs the deterministic backbone, then the REAL Narrative
Writer (Splunk Hosted Models, or Anthropic/OpenAI fallback) and — with --audio —
the REAL ElevenLabs Audio Producer. Writes dashboard JSON + mp3.

    set -a && source .env && set +a
    python orchestration/export_briefings_live.py --persona CEO
    python orchestration/export_briefings_live.py --all --audio
"""
from __future__ import annotations
import argparse
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
from agents.narrative_writer.agent import NarrativeWriterAgent
from agents.narrative_writer.llm_client import LLMClient
from orchestration.pipeline import MockSplunkClient

ROOT = Path(__file__).resolve().parent.parent
SEED_DIR = ROOT / "business_context" / "seed_data"
OUT_DIR = ROOT / "web" / "public" / "briefings"
AUDIO_DIR = ROOT / "web" / "public" / "audio"
BRIEFING_DATE = datetime(2026, 5, 21, 6, 30, tzinfo=timezone.utc)

REVENUE_USD = 2_300_000
UPTIME_PCT = 99.94
GOOD_NEWS = {
    "headline": "Black Friday capacity test passed",
    "summary": "All services held under a 3x peak load test overnight; "
               "we're ready for the holiday season.",
}


def _first_two_sentences(text: str) -> str:
    parts = [p for p in text.replace("\n", " ").split(". ") if p.strip()]
    return (". ".join(parts[:2]).rstrip(".") + ".") if parts else text


async def run_pipeline(persona: Persona):
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
    return editor, qs_index


def _story(cluster, qs_index, script_citations) -> dict:
    qs = qs_index.get(cluster.primary_signal_id)
    qualitative = bool(qs and qs.qualitative_only)
    cits = [
        {"claim_text": c.claim_text, "methodology": c.methodology,
         "confidence": c.confidence, "splunk_query": c.splunk_query}
        for c in script_citations if c.source_signal_id in cluster.signal_ids
    ]
    if not cits and qs:  # fall back to the quantifier's calculation steps
        cits = [{"claim_text": f"${s.result_usd:,.0f} {s.label.lower()}",
                 "methodology": s.formula, "confidence": s.confidence}
                for s in qs.financial_impact.calculations]
    return {
        "cluster_id": cluster.cluster_id,
        "theme": cluster.theme.value,
        "headline": cluster.headline_hint,
        "summary": cluster.headline_hint,
        "exposure_usd": round(cluster.aggregate_exposure_usd),
        "priority_score": round(cluster.aggregate_priority, 1),
        "affected_customers": qs.customer_impact.affected_count if qs else None,
        "duration_min": round(qs.enriched.raw_signal.duration_minutes) if qs else None,
        "citations": [] if qualitative else cits,
        "drill_down_url": "#",
        "qualitative_only": qualitative,
    }


async def build(persona: Persona, llm: LLMClient, do_audio: bool) -> dict:
    editor, qs_index = await run_pipeline(persona)

    script = await NarrativeWriterAgent(llm=llm).write(editor, qs_index)
    print(f"  [{persona.value}] writer: {script.word_count} words, "
          f"{len(script.citations)} citations, model={script.llm_model_used}, "
          f"passes={script.llm_passes}")

    audio_url = ""
    if do_audio:
        from agents.audio_producer.agent import AudioProducerAgent
        AUDIO_DIR.mkdir(parents=True, exist_ok=True)
        audio = await AudioProducerAgent(output_dir=AUDIO_DIR).produce(script)
        audio_url = f"/audio/{Path(audio.local_path).name}"
        print(f"  [{persona.value}] audio: {audio_url} ({audio.duration_sec}s)")

    return {
        "persona": persona.value,
        "briefing_date": BRIEFING_DATE.date().isoformat(),
        "audio_url": audio_url,
        "duration_sec": script.estimated_duration_sec,
        "word_count": script.word_count,
        "total_exposure_usd": round(editor.total_exposure_usd_shown),
        "uptime_pct": UPTIME_PCT,
        "revenue_usd": REVENUE_USD,
        "headline_quote": _first_two_sentences(script.script_text),
        "script_text": script.script_text,
        "stories": [_story(c, qs_index, script.citations) for c in editor.clusters],
        "decisions": [
            {"decision_id": d.decision_id, "title": d.title,
             "context": d.context_one_liner, "options": d.options,
             "cost_usd": d.cost_usd,
             "deadline": d.deadline.isoformat() if d.deadline else "",
             "owner": d.owner}
            for d in editor.decisions_required
        ],
        "good_news": GOOD_NEWS,
    }


async def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--persona", default="CEO", choices=[p.value for p in Persona])
    ap.add_argument("--all", action="store_true")
    ap.add_argument("--audio", action="store_true")
    args = ap.parse_args()

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    llm = LLMClient()
    personas = list(Persona) if args.all else [Persona(args.persona)]
    for persona in personas:
        briefing = await build(persona, llm, args.audio)
        text = json.dumps(briefing, indent=2)
        slug = persona.value.lower()
        (OUT_DIR / f"{slug}-latest.json").write_text(text)
        (OUT_DIR / f"{slug}-{briefing['briefing_date']}.json").write_text(text)
    print(f"Wrote live briefings to {OUT_DIR}")


if __name__ == "__main__":
    asyncio.run(main())
