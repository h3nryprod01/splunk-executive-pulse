# agents/narrative_writer/agent.py
"""
Narrative Writer Agent — two-pass generation with self-critique.

Flow:
  1. DRAFT pass: LLM generates script using citations table.
  2. VALIDATE: regex-check every numeric claim → uncited list.
  3. CRITIC pass: separate LLM call scores draft on 6 dimensions.
  4. REVISE: if validation fails OR critic score < threshold,
             re-prompt with specific feedback. Max 2 retries.
  5. SSML wrap + duration estimate.
"""
from __future__ import annotations
import logging
import time
import json
from datetime import datetime, timezone

from agents.executive_editor.models import EditorOutput
from agents.impact_quantifier.models import QuantifiedSignal
from .models import NarrativeScript, Citation, DrillDownLink, WriterValidationError
from .llm_client import LLMClient
from .citation_enforcer import validate_citations, redact_uncited_claims
from .ssml_converter import to_ssml, estimate_duration_sec
from .prompts.system_prompt import SYSTEM_PROMPT
from .prompts.few_shot_examples import GOLD_STANDARD_EXAMPLE
from .prompts.critic_prompt import CRITIC_PROMPT
from .prompts.retry_prompt import RETRY_PROMPT_TEMPLATE

logger = logging.getLogger(__name__)


CRITIC_PASS_THRESHOLD = 0.75
MAX_RETRIES = 2


class NarrativeWriterAgent:

    def __init__(self, llm: LLMClient):
        self.llm = llm

    async def write(
        self,
        editor_output: EditorOutput,
        signals_by_id: dict[str, QuantifiedSignal],
        dashboard_url_template: str = "https://splunk.demo/dashboard/{cluster_id}",
    ) -> NarrativeScript:
        start = time.perf_counter()

        # 1. Build citations table from quantified signals
        citations = self._build_citations(editor_output, signals_by_id)
        drilldowns = self._build_drilldowns(editor_output, dashboard_url_template)

        # 2. Build the user prompt
        user_prompt = self._build_user_prompt(editor_output, signals_by_id, citations)

        # 3. DRAFT pass
        draft_response = await self.llm.complete_json(
            system=SYSTEM_PROMPT + "\n\n" + GOLD_STANDARD_EXAMPLE,
            user=user_prompt,
            temperature=0.4,
        )
        script_text = draft_response["script_text"]
        passes = 1

        # 4. Validate + revise loop
        critic_score = 0.0
        for attempt in range(MAX_RETRIES + 1):
            uncited = validate_citations(script_text, citations)
            critique = await self._critique(script_text, citations)
            critic_score = critique["overall_score"]

            logger.info(
                f"Pass {passes}: uncited={len(uncited)} critic_score={critic_score:.2f}"
            )

            publishable = (
                len(uncited) == 0
                and critic_score >= CRITIC_PASS_THRESHOLD
                and not critique["must_fix"]
            )
            if publishable or attempt == MAX_RETRIES:
                break

            # REVISE
            retry_user = RETRY_PROMPT_TEMPLATE.format(
                uncited_list="\n".join(f"  - '{u.text}'" for u in uncited) or "  (none)",
                critic_feedback=json.dumps({
                    "must_fix": critique["must_fix"],
                    "jargon_to_replace": critique["jargon_to_replace"],
                }, indent=2),
            )
            revised = await self.llm.complete_json(
                system=SYSTEM_PROMPT,
                user=user_prompt + "\n\nYOUR PREVIOUS DRAFT:\n" + script_text + "\n\n" + retry_user,
                temperature=0.3,
            )
            script_text = revised["script_text"]
            passes += 1

        # Hard anti-hallucination guarantee: if any numeric claim STILL lacks
        # a citation after the retry loop, REDACT it rather than publish a
        # fabricated number. No dollar/number ships without a citation.
        remaining = validate_citations(script_text, citations)
        if remaining:
            logger.warning(
                f"Redacting {len(remaining)} uncited numeric claim(s) before "
                f"publishing — anti-hallucination last-resort guarantee"
            )
            script_text = redact_uncited_claims(script_text, citations)
            assert not validate_citations(script_text, citations), (
                "redaction failed to remove all uncited claims"
            )

        # 5. Wrap to SSML — recomputed from the (possibly redacted) text
        ssml = to_ssml(script_text)
        word_count = len(script_text.split())
        duration = estimate_duration_sec(script_text)

        duration_ms = int((time.perf_counter() - start) * 1000)
        logger.info(
            f"Narrative ready in {duration_ms}ms: {word_count} words, ~{duration}s, "
            f"{passes} pass(es), critic={critic_score:.2f}"
        )

        return NarrativeScript(
            script_text=script_text,
            ssml_version=ssml,
            persona=editor_output.persona.value,
            briefing_date=editor_output.briefing_date,
            estimated_duration_sec=duration,
            word_count=word_count,
            citations=citations,
            drill_down_links=drilldowns,
            llm_model_used=self.llm.last_model_used,
            llm_passes=passes,
            self_critique_score=critic_score,
        )

    # ---------- helpers ----------
    def _build_citations(
        self, editor_output: EditorOutput,
        signals_by_id: dict[str, QuantifiedSignal],
    ) -> list[Citation]:
        cites: list[Citation] = []
        for cluster in editor_output.clusters:
            for sid in cluster.signal_ids:
                sig = signals_by_id.get(sid)
                if not sig:
                    continue
                for step in sig.financial_impact.calculations:
                    cites.append(Citation(
                        claim_text=f"${step.result_usd:,.0f} ({step.label})",
                        source_signal_id=sid,
                        methodology=step.formula,
                        confidence=step.confidence,
                        splunk_query=sig.enriched.raw_signal.splunk_query,
                    ))
                # Customer counts also become citations
                if sig.customer_impact.affected_count > 0:
                    cites.append(Citation(
                        claim_text=f"{sig.customer_impact.affected_count} customers affected",
                        source_signal_id=sid,
                        methodology="transaction log count",
                        confidence=0.9,
                    ))
        return cites

    def _build_drilldowns(self, editor_output, url_template) -> list[DrillDownLink]:
        return [
            DrillDownLink(
                cluster_id=c.cluster_id,
                headline=c.headline_hint,
                splunk_dashboard_url=url_template.format(cluster_id=c.cluster_id),
            )
            for c in editor_output.clusters
        ]

    def _build_user_prompt(self, editor_output, signals_by_id, citations) -> str:
        """Compose the structured input the LLM sees."""
        lines = [
            f"PERSONA: {editor_output.persona.value}",
            f"DATE: {editor_output.briefing_date.strftime('%A, %B %d, %Y')}",
            "",
            "CLUSTERS TO COVER (ordered by importance):",
        ]
        for i, c in enumerate(editor_output.clusters, 1):
            primary = signals_by_id.get(c.primary_signal_id)
            lines.append(f"  {i}. [{c.theme.value}] {c.headline_hint}")
            if primary:
                ctx = primary.enriched.business_context
                lines.append(f"     duration: {primary.enriched.raw_signal.duration_minutes:.0f} min")
                lines.append(f"     customers: {primary.customer_impact.affected_count}")
                lines.append(f"     SLA breached: {ctx.sla.breached}")
                lines.append(f"     priority: {c.aggregate_priority}")
                lines.append(f"     exposure: ${c.aggregate_exposure_usd:,.0f}")

        if editor_output.decisions_required:
            lines.append("\nDECISIONS REQUIRED:")
            for d in editor_output.decisions_required:
                lines.append(f"  - {d.title} (owner: {d.owner}, cost: ${d.cost_usd or 0:,.0f}, deadline: {d.deadline})")
                lines.append(f"    context: {d.context_one_liner}")

        lines.append("\nCITATIONS TABLE (ONLY use numbers that appear here):")
        for i, cit in enumerate(citations, 1):
            lines.append(f"  c{i}: {cit.claim_text} | {cit.methodology} | conf={cit.confidence}")

        return "\n".join(lines)

    async def _critique(self, script_text: str, citations) -> dict:
        cite_table = "\n".join(
            f"  - {c.claim_text} ({c.methodology})" for c in citations
        )
        user = f"DRAFT SCRIPT:\n\n{script_text}\n\nCITATIONS TABLE:\n{cite_table}"
        return await self.llm.complete_json(
            system=CRITIC_PROMPT, user=user,
            temperature=0.1,
        )
