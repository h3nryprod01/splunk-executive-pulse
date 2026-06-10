# orchestration/graph.py
"""
LangGraph DAG wiring 7 agents.

Flow:
  signal_collector → enricher → quantifier → editor → writer → audio → delivery

Conditional routing: if any node sets status=failed, jump to terminal_error.
"""
from __future__ import annotations
import logging
import os
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver

from .state import PipelineState
from .nodes import (
    node_signal_collector, node_business_enricher, node_impact_quantifier,
    node_executive_editor, node_narrative_writer, node_audio_producer,
    node_delivery,
)

logger = logging.getLogger(__name__)


def should_continue(state: PipelineState) -> str:
    """Conditional edge router."""
    if state.get("status") == "failed":
        return "terminal_error"
    return state.get("current_stage", "end")


async def terminal_error_node(state: PipelineState) -> dict:
    """Best-effort: at least try to alert the team on Slack."""
    from delivery.slack import deliver_failure_alert
    try:
        await deliver_failure_alert(state)
    except Exception as e:
        # Never crash the error path itself, but never lose the trace either.
        logger.error(
            "terminal_error_node: failure alert could not be delivered "
            "(run_id=%s): %s: %s",
            state.get("run_id", "?"), type(e).__name__, e,
        )
    return {"status": "failed", "current_stage": "terminal_error"}


def build_graph(use_checkpointer: bool = True):
    g = StateGraph(PipelineState)

    # Register nodes
    g.add_node("signal_collector",   node_signal_collector)
    g.add_node("business_enricher",  node_business_enricher)
    g.add_node("impact_quantifier",  node_impact_quantifier)
    g.add_node("executive_editor",   node_executive_editor)
    g.add_node("narrative_writer",   node_narrative_writer)
    g.add_node("audio_producer",     node_audio_producer)
    g.add_node("delivery",           node_delivery)
    g.add_node("terminal_error",     terminal_error_node)

    # Entry
    g.set_entry_point("signal_collector")

    # Linear happy path with conditional bail-outs.
    # On success each node sets state.current_stage to the SHORT name below,
    # which should_continue returns as the routing key.
    for src, success_stage, next_node in [
        ("signal_collector",  "enricher",   "business_enricher"),
        ("business_enricher", "quantifier", "impact_quantifier"),
        ("impact_quantifier", "editor",     "executive_editor"),
        ("executive_editor",  "writer",     "narrative_writer"),
        ("narrative_writer",  "audio",      "audio_producer"),
        ("audio_producer",    "delivery",   "delivery"),
    ]:
        g.add_conditional_edges(
            src, should_continue,
            {success_stage: next_node, "terminal_error": "terminal_error"},
        )

    g.add_edge("delivery", END)
    g.add_edge("terminal_error", END)

    # Checkpointer enables resume-from-failure and inspectability
    checkpointer = None
    if use_checkpointer:
        try:
            from langgraph.checkpoint.redis import RedisSaver
            checkpointer = RedisSaver.from_conn_string(
                os.environ.get("REDIS_URL", "redis://localhost:6379")
            )
        except ImportError:
            checkpointer = MemorySaver()

    return g.compile(checkpointer=checkpointer)
