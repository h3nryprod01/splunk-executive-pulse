"""
Keyless end-to-end run of the REAL LangGraph pipeline.

The deterministic agents run for real (signal_collector -> business_enricher ->
impact_quantifier -> executive_editor). The three nodes that need external
credentials — narrative_writer (LLM), audio_producer (ElevenLabs), delivery
(email/Slack) — are stubbed so the full graph (state flow, conditional routing,
checkpointer, observability) executes without any keys or live stack.

    python orchestration/graph_e2e_demo.py --persona CISO
"""
from __future__ import annotations
import argparse
import asyncio
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from agents.business_enricher.tools import InMemoryContextStore
from agents.executive_editor.models import Persona
from agents.narrative_writer.models import NarrativeScript
from agents.audio_producer.models import AudioOutput, ChapterMarker
from orchestration import nodes as N
from orchestration.pipeline import MockSplunkClient
from orchestration.runner import run_briefing

SEED_DIR = Path(__file__).resolve().parent.parent / "business_context" / "seed_data"


class _FakeWriter:
    def __init__(self, llm=None):
        pass

    async def write(self, editor_output, sig_index) -> NarrativeScript:
        text = "Good morning. " + " ".join(
            c.theme.value.replace("_", " ") for c in editor_output.clusters
        )
        return NarrativeScript(
            script_text=text,
            ssml_version=f"<speak>{text}</speak>",
            persona=editor_output.persona.value,
            briefing_date=editor_output.briefing_date,
            estimated_duration_sec=170,
            word_count=len(text.split()),
            citations=[],
            drill_down_links=[],
            llm_model_used="stub (keyless e2e)",
            llm_passes=1,
            self_critique_score=0.9,
        )


class _FakeAudio:
    def __init__(self, *a, **k):
        pass

    async def produce(self, script) -> AudioOutput:
        return AudioOutput(
            audio_url="stub://briefing.mp3",
            local_path="/tmp/briefing.mp3",
            duration_sec=script.estimated_duration_sec,
            chapters=[ChapterMarker(start_sec=0.0, title="Headline")],
            voice_preset="bloomberg_male",
            file_size_bytes=512_000,
            expires_at=datetime.now(timezone.utc) + timedelta(days=1),
        )


async def _ok(*a, **k):
    return True


async def _dash(*a, **k):
    return "stub://dashboard/ceo"


def _install_stubs() -> None:
    inmem = InMemoryContextStore(SEED_DIR)
    # Pre-seed the lazy dependency container with keyless mocks.
    N.DEPS._splunk_mcp = MockSplunkClient()
    N.DEPS._business_store = inmem
    N.DEPS._mcp_client = inmem
    N.NarrativeWriterAgent = _FakeWriter
    N.AudioProducerAgent = _FakeAudio
    # delivery.email imports the optional `resend` SDK at module load; stub it.
    import types
    sys.modules.setdefault("resend", types.ModuleType("resend"))
    # delivery functions are imported inside node_delivery; patch the modules.
    import delivery.email, delivery.slack, delivery.dashboard
    delivery.email.deliver_email = _ok
    delivery.slack.deliver_slack = _ok
    delivery.dashboard.publish_dashboard = _dash
    return inmem


async def main(persona: Persona) -> None:
    inmem = _install_stubs()
    await inmem.init()

    state = await run_briefing(
        persona=persona,
        briefing_date=datetime(2026, 5, 21, 6, 30, tzinfo=timezone.utc),
    )

    print(f"\nGraph status : {state.get('status')}")
    print(f"stages timed : {list(state.get('node_durations_ms', {}).keys())}")
    print(f"errors       : {len(state.get('errors', []))}")
    q = state.get("quantifier_output")
    ed = state.get("editor_output")
    if q:
        print(f"exposure     : ${q.total_exposure_usd:,.0f}")
    if ed:
        print(f"persona      : {ed.persona.value}  headline_cluster={ed.headline_cluster_id}")
    print(f"delivered    : email={state.get('delivered_email')} "
          f"slack={state.get('delivered_slack')} dash={state.get('delivered_dashboard_url')}")


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--persona", default="CEO", choices=[x.value for x in Persona])
    asyncio.run(main(Persona(p.parse_args().persona)))
