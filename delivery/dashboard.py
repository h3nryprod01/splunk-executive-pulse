# delivery/dashboard.py
"""
Publish briefing JSON to the dashboard backend.
The Next.js dashboard fetches /api/briefings/:persona to render.
"""
from __future__ import annotations
import os
import logging
import json
from pathlib import Path

from orchestration.state import PipelineState

logger = logging.getLogger(__name__)


async def publish_dashboard(state: PipelineState) -> str:
    """Returns the dashboard URL for the published briefing."""
    persona = state["persona"].value.lower()
    date_str = state["briefing_date"].strftime("%Y-%m-%d")

    output_dir = Path(os.getenv("DASHBOARD_OUTPUT_DIR", "web/public/briefings"))
    output_dir.mkdir(parents=True, exist_ok=True)

    payload = _to_dashboard_json(state)
    out_file = output_dir / f"{persona}-{date_str}.json"
    out_file.write_text(json.dumps(payload, default=str, indent=2))

    # Also write a "latest" symlink for easy dashboard lookup
    latest = output_dir / f"{persona}-latest.json"
    if latest.exists() or latest.is_symlink():
        latest.unlink()
    latest.symlink_to(out_file.name)

    base = os.getenv("DASHBOARD_BASE_URL", "http://localhost:3000")
    url = f"{base}/?persona={persona}&date={date_str}"
    logger.info(f"Dashboard published: {url}")
    return url


def _to_dashboard_json(state: PipelineState) -> dict:
    """Transform PipelineState to the dashboard's expected shape."""
    script = state["narrative_script"]
    audio  = state["audio_output"]
    editor = state["editor_output"]

    return {
        "persona": state["persona"].value,
        "briefing_date": state["briefing_date"].isoformat(),
        "audio_url": audio.audio_url,
        "duration_sec": audio.duration_sec,
        "word_count": script.word_count,
        "total_exposure_usd": editor.total_exposure_usd_shown,
        "headline_quote": _first_two_sentences(script.script_text),
        "stories": [
            {
                "cluster_id": c.cluster_id,
                "theme": c.theme.value,
                "headline": c.headline_hint,
                "exposure_usd": c.aggregate_exposure_usd,
                "priority_score": c.aggregate_priority,
                "citations": [
                    {
                        "claim_text": cit.claim_text,
                        "methodology": cit.methodology,
                        "confidence": cit.confidence,
                        "splunk_dashboard_url": cit.splunk_dashboard_url,
                    }
                    for cit in script.citations
                    if cit.source_signal_id in c.signal_ids
                ],
                "drill_down_url": next(
                    (d.splunk_dashboard_url for d in script.drill_down_links
                     if d.cluster_id == c.cluster_id), "#"
                ),
            }
            for c in editor.clusters
        ],
        "decisions": [
            {
                "decision_id": d.decision_id,
                "title": d.title,
                "context": d.context_one_liner,
                "options": d.options,
                "cost_usd": d.cost_usd,
                "deadline": d.deadline.isoformat() if d.deadline else None,
                "owner": d.owner,
            }
            for d in editor.decisions_required
        ],
        "run_id": state["run_id"],
    }


def _first_two_sentences(text: str) -> str:
    parts = text.split(". ")
    return ". ".join(parts[:2]).rstrip(".") + "."
