# orchestration/state.py
"""
The pipeline State is the single source of truth flowing through all nodes.
LangGraph nodes read it, mutate (return updates), and pass it on.
"""
from __future__ import annotations
from datetime import datetime
from typing import Optional, TypedDict, Literal, Annotated
import operator

from agents.signal_collector.models import CollectorOutput
from agents.business_enricher.models import EnricherOutput
from agents.impact_quantifier.models import QuantifierOutput
from agents.executive_editor.models import EditorOutput, Persona
from agents.narrative_writer.models import NarrativeScript
from agents.audio_producer.models import AudioOutput


class NodeError(TypedDict):
    node: str
    error_type: str
    message: str
    attempt: int
    timestamp: str


class PipelineState(TypedDict, total=False):
    # ============ INPUTS ============
    run_id: str
    persona: Persona
    briefing_date: datetime
    time_window_start: datetime
    time_window_end: datetime

    # ============ OUTPUTS per stage ============
    collector_output: Optional[CollectorOutput]
    enricher_output: Optional[EnricherOutput]
    quantifier_output: Optional[QuantifierOutput]
    editor_output: Optional[EditorOutput]
    narrative_script: Optional[NarrativeScript]
    audio_output: Optional[AudioOutput]

    # ============ OBSERVABILITY ============
    errors: Annotated[list[NodeError], operator.add]   # accumulated
    node_durations_ms: Annotated[dict[str, int], lambda a, b: {**a, **b}]
    current_stage: str
    status: Literal["pending", "running", "succeeded", "failed", "partial"]

    # ============ DELIVERY ============
    delivered_email: bool
    delivered_slack: bool
    delivered_dashboard_url: Optional[str]
