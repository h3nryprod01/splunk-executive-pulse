# orchestration/nodes.py
"""
Each LangGraph node is a thin wrapper around one agent.
Responsibilities:
  - Read needed input from state
  - Apply retry policy
  - Capture errors into state.errors
  - Record duration
  - Return state UPDATES (LangGraph merge-reducer style)
"""
from __future__ import annotations
import asyncio
import logging
import time
import uuid
from datetime import datetime, timezone

from agents.signal_collector.agent import SignalCollectorAgent
from agents.signal_collector.models import CollectorConfig
from agents.signal_collector.splunk_mcp import SplunkMCPSearchClient
from agents.business_enricher.agent import BusinessEnricherAgent
from agents.business_enricher.tools import BusinessContextStore, MCPClient
from agents.business_enricher.models import RawSignal as EnricherRawSignal
from agents.impact_quantifier.agent import ImpactQuantifierAgent
from agents.executive_editor.agent import ExecutiveEditorAgent
from agents.narrative_writer.agent import NarrativeWriterAgent
from agents.narrative_writer.llm_client import LLMClient
from agents.audio_producer.agent import AudioProducerAgent

from .state import PipelineState, NodeError
from .retry_policy import RetryPolicy, with_retry
from .observability import span, structured_log

logger = logging.getLogger(__name__)


# ============================================================
# DEPENDENCY CONTAINER
# Lazily-built singletons. In prod, inject via DI framework.
# ============================================================
class Dependencies:
    def __init__(self):
        self._splunk_mcp = None
        self._business_store = None
        self._mcp_client = None
        self._llm = None

    @property
    def splunk_mcp(self) -> SplunkMCPSearchClient:
        if self._splunk_mcp is None:
            import os
            self._splunk_mcp = SplunkMCPSearchClient(
                mcp_url=os.environ["SPLUNK_MCP_URL"],
                api_token=os.environ["SPLUNK_MCP_TOKEN"],
            )
        return self._splunk_mcp

    async def get_business_store(self) -> BusinessContextStore:
        if self._business_store is None:
            import os
            self._business_store = BusinessContextStore(dsn=os.environ["PG_DSN"])
            await self._business_store.init()
        return self._business_store

    @property
    def mcp_client(self) -> MCPClient:
        if self._mcp_client is None:
            import os
            self._mcp_client = MCPClient(
                mcp_url=os.environ["SPLUNK_MCP_URL"],
                api_token=os.environ["SPLUNK_MCP_TOKEN"],
            )
        return self._mcp_client

    @property
    def llm(self) -> LLMClient:
        if self._llm is None:
            self._llm = LLMClient()
        return self._llm


DEPS = Dependencies()


def _record_error(state: PipelineState, node: str, exc: Exception, attempt: int) -> NodeError:
    return NodeError(
        node=node, error_type=type(exc).__name__,
        message=str(exc), attempt=attempt,
        timestamp=datetime.now(timezone.utc).isoformat(),
    )


# ============================================================
# NODE 1: Signal Collector
# ============================================================
async def node_signal_collector(state: PipelineState) -> dict:
    async with span("signal_collector", run_id=state["run_id"]):
        start = time.perf_counter()
        try:
            config = CollectorConfig(
                time_window_start=state["time_window_start"],
                time_window_end=state["time_window_end"],
            )
            agent = SignalCollectorAgent(splunk=DEPS.splunk_mcp, config=config)
            policy = RetryPolicy(max_attempts=3, base_delay_s=2.0)
            output = await with_retry(agent.run, policy, "signal_collector")
            duration_ms = int((time.perf_counter() - start) * 1000)
            structured_log("node.signal_collector.done",
                           signals=len(output.signals), duration_ms=duration_ms)
            return {
                "collector_output": output,
                "node_durations_ms": {"signal_collector": duration_ms},
                "current_stage": "enricher",
            }
        except Exception as e:
            return {
                "errors": [_record_error(state, "signal_collector", e, 3)],
                "status": "failed",
                "current_stage": "signal_collector_failed",
            }


# ============================================================
# NODE 2: Business Enricher
# ============================================================
async def node_business_enricher(state: PipelineState) -> dict:
    async with span("business_enricher", run_id=state["run_id"]):
        start = time.perf_counter()
        if not state.get("collector_output"):
            return {"errors": [_record_error(state, "business_enricher",
                    RuntimeError("no collector output"), 1)], "status": "failed"}
        try:
            store = await DEPS.get_business_store()
            agent = BusinessEnricherAgent(store=store, mcp=DEPS.mcp_client)
            policy = RetryPolicy(max_attempts=2, base_delay_s=1.0)
            # Cross-module boundary: re-validate collector signals into the
            # enricher's RawSignal (schemas are identical by contract).
            signals = [
                EnricherRawSignal.model_validate(s.model_dump(mode="json"))
                for s in state["collector_output"].signals
            ]
            output = await with_retry(
                lambda: agent.run(signals),
                policy, "business_enricher",
            )
            duration_ms = int((time.perf_counter() - start) * 1000)
            structured_log("node.business_enricher.done",
                           enriched=len(output.enriched_signals),
                           skipped=len(output.skipped_signals),
                           duration_ms=duration_ms)
            return {
                "enricher_output": output,
                "node_durations_ms": {"business_enricher": duration_ms},
                "current_stage": "quantifier",
            }
        except Exception as e:
            return {
                "errors": [_record_error(state, "business_enricher", e, 2)],
                "status": "failed",
            }


# ============================================================
# NODE 3: Impact Quantifier (sync — pure math, no external calls)
# ============================================================
async def node_impact_quantifier(state: PipelineState) -> dict:
    async with span("impact_quantifier", run_id=state["run_id"]):
        start = time.perf_counter()
        if not state.get("enricher_output"):
            return {"errors": [_record_error(state, "impact_quantifier",
                    RuntimeError("no enricher output"), 1)], "status": "failed"}
        try:
            agent = ImpactQuantifierAgent()
            # Sync agent — wrap in to_thread for graph compatibility
            output = await asyncio.to_thread(agent.run, state["enricher_output"])
            duration_ms = int((time.perf_counter() - start) * 1000)
            structured_log("node.impact_quantifier.done",
                           total_exposure_usd=output.total_exposure_usd,
                           top_priority=output.highest_priority_score,
                           duration_ms=duration_ms)
            return {
                "quantifier_output": output,
                "node_durations_ms": {"impact_quantifier": duration_ms},
                "current_stage": "editor",
            }
        except Exception as e:
            return {
                "errors": [_record_error(state, "impact_quantifier", e, 1)],
                "status": "failed",
            }


# ============================================================
# NODE 4: Executive Editor
# ============================================================
async def node_executive_editor(state: PipelineState) -> dict:
    async with span("executive_editor",
                    run_id=state["run_id"], persona=state["persona"].value):
        start = time.perf_counter()
        if not state.get("quantifier_output"):
            return {"errors": [_record_error(state, "executive_editor",
                    RuntimeError("no quantifier output"), 1)], "status": "failed"}
        try:
            agent = ExecutiveEditorAgent()
            output = await asyncio.to_thread(
                agent.edit, state["quantifier_output"], state["persona"],
                state["briefing_date"],
            )
            duration_ms = int((time.perf_counter() - start) * 1000)
            structured_log("node.executive_editor.done",
                           clusters=len(output.clusters),
                           decisions=len(output.decisions_required),
                           duration_ms=duration_ms)
            return {
                "editor_output": output,
                "node_durations_ms": {"executive_editor": duration_ms},
                "current_stage": "writer",
            }
        except Exception as e:
            return {
                "errors": [_record_error(state, "executive_editor", e, 1)],
                "status": "failed",
            }


# ============================================================
# NODE 5: Narrative Writer
# ============================================================
async def node_narrative_writer(state: PipelineState) -> dict:
    async with span("narrative_writer", run_id=state["run_id"]):
        start = time.perf_counter()
        if not state.get("editor_output"):
            return {"errors": [_record_error(state, "narrative_writer",
                    RuntimeError("no editor output"), 1)], "status": "failed"}
        try:
            agent = NarrativeWriterAgent(llm=DEPS.llm)
            policy = RetryPolicy(max_attempts=2, base_delay_s=2.0)
            sig_index = {
                s.signal_id: s
                for s in state["quantifier_output"].quantified_signals
            }
            output = await with_retry(
                lambda: agent.write(state["editor_output"], sig_index),
                policy, "narrative_writer",
            )
            duration_ms = int((time.perf_counter() - start) * 1000)
            structured_log("node.narrative_writer.done",
                           words=output.word_count,
                           duration_sec=output.estimated_duration_sec,
                           llm_passes=output.llm_passes,
                           critic_score=output.self_critique_score,
                           duration_ms=duration_ms)
            return {
                "narrative_script": output,
                "node_durations_ms": {"narrative_writer": duration_ms},
                "current_stage": "audio",
            }
        except Exception as e:
            return {
                "errors": [_record_error(state, "narrative_writer", e, 2)],
                "status": "failed",
            }


# ============================================================
# NODE 6: Audio Producer
# ============================================================
async def node_audio_producer(state: PipelineState) -> dict:
    async with span("audio_producer", run_id=state["run_id"]):
        start = time.perf_counter()
        if not state.get("narrative_script"):
            return {"errors": [_record_error(state, "audio_producer",
                    RuntimeError("no narrative script"), 1)], "status": "failed"}
        try:
            agent = AudioProducerAgent()
            policy = RetryPolicy(max_attempts=2, base_delay_s=3.0)
            output = await with_retry(
                lambda: agent.produce(state["narrative_script"]),
                policy, "audio_producer",
            )
            duration_ms = int((time.perf_counter() - start) * 1000)
            structured_log("node.audio_producer.done",
                           audio_url=output.audio_url,
                           size_kb=output.file_size_bytes // 1024,
                           duration_ms=duration_ms)
            return {
                "audio_output": output,
                "node_durations_ms": {"audio_producer": duration_ms},
                "current_stage": "delivery",
            }
        except Exception as e:
            return {
                "errors": [_record_error(state, "audio_producer", e, 2)],
                "status": "failed",
            }


# ============================================================
# NODE 7: Delivery (fan-out: email + slack + dashboard)
# ============================================================
async def node_delivery(state: PipelineState) -> dict:
    """Parallel delivery to all channels. Tolerates partial failures."""
    from delivery.email import deliver_email
    from delivery.slack import deliver_slack
    from delivery.dashboard import publish_dashboard

    async with span("delivery", run_id=state["run_id"]):
        start = time.perf_counter()
        if not state.get("audio_output") or not state.get("narrative_script"):
            return {"errors": [_record_error(state, "delivery",
                    RuntimeError("missing audio or script"), 1)], "status": "failed"}

        results = await asyncio.gather(
            deliver_email(state),
            deliver_slack(state),
            publish_dashboard(state),
            return_exceptions=True,
        )
        email_ok, slack_ok, dash_result = (
            not isinstance(r, Exception) for r in results
        )
        dash_url = results[2] if not isinstance(results[2], Exception) else None

        any_failed = any(isinstance(r, Exception) for r in results)
        status = "partial" if any_failed else "succeeded"

        duration_ms = int((time.perf_counter() - start) * 1000)
        structured_log("node.delivery.done",
                       email_ok=email_ok, slack_ok=slack_ok, dash_ok=bool(dash_url),
                       duration_ms=duration_ms)

        errors = []
        for ch, r in zip(["email", "slack", "dashboard"], results):
            if isinstance(r, Exception):
                errors.append(_record_error(state, f"delivery.{ch}", r, 1))

        return {
            "delivered_email": email_ok,
            "delivered_slack": slack_ok,
            "delivered_dashboard_url": dash_url,
            "node_durations_ms": {"delivery": duration_ms},
            "current_stage": "done",
            "status": status,
            "errors": errors,
        }
