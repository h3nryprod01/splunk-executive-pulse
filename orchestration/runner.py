# orchestration/runner.py
"""
High-level API: run a briefing for one persona.

Usage:
    from orchestration.runner import run_briefing
    state = await run_briefing(persona=Persona.CEO)
"""
from __future__ import annotations
import asyncio
import logging
import uuid
from datetime import datetime, timezone, timedelta
from typing import Optional

from agents.executive_editor.models import Persona
from .graph import build_graph
from .nodes import validate_environment
from .state import PipelineState
from .observability import structured_log

logger = logging.getLogger(__name__)


async def run_briefing(
    persona: Persona,
    briefing_date: Optional[datetime] = None,
    time_window_hours: int = 24,
    thread_id: Optional[str] = None,
) -> PipelineState:
    # Fail fast on missing required config instead of crashing mid-pipeline.
    validate_environment()

    briefing_date = briefing_date or datetime.now(tz=timezone.utc)
    run_id = f"run_{uuid.uuid4().hex[:10]}"
    thread_id = thread_id or f"{persona.value}-{briefing_date.date().isoformat()}"

    initial_state: PipelineState = {
        "run_id": run_id,
        "persona": persona,
        "briefing_date": briefing_date,
        "time_window_end": briefing_date,
        "time_window_start": briefing_date - timedelta(hours=time_window_hours),
        "errors": [],
        "node_durations_ms": {},
        "current_stage": "signal_collector",
        "status": "running",
    }

    structured_log("pipeline.start", run_id=run_id, persona=persona.value,
                   briefing_date=briefing_date.isoformat())

    graph = build_graph()
    final_state = await graph.ainvoke(
        initial_state,
        config={"configurable": {"thread_id": thread_id}},
    )

    total_ms = sum(final_state.get("node_durations_ms", {}).values())
    structured_log(
        "pipeline.done", run_id=run_id, status=final_state.get("status"),
        total_ms=total_ms, errors=len(final_state.get("errors", [])),
    )
    return final_state


async def run_all_personas(
    briefing_date: Optional[datetime] = None,
) -> dict[Persona, PipelineState]:
    """Fan out to all 5 personas in parallel."""
    personas = [Persona.CEO, Persona.CFO, Persona.CISO, Persona.CTO, Persona.COO]
    results = await asyncio.gather(
        *[run_briefing(p, briefing_date) for p in personas],
        return_exceptions=True,
    )
    output = {}
    for p, r in zip(personas, results):
        if isinstance(r, Exception):
            logger.exception(f"Persona {p.value} pipeline crashed: {r}")
            output[p] = {"status": "crashed", "errors": [{"message": str(r)}]}
        else:
            output[p] = r
    return output


if __name__ == "__main__":
    import sys
    persona_arg = Persona(sys.argv[1].upper()) if len(sys.argv) > 1 else Persona.CEO
    asyncio.run(run_briefing(persona=persona_arg))
