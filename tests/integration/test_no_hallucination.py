# tests/integration/test_no_hallucination.py
"""
End-to-end anti-hallucination tests.

These tests are NON-NEGOTIABLE. If they fail, the system MUST NOT ship.
They validate that:
  1. Every $ figure in every briefing traces to a citation
  2. Citations point to real Splunk queries / DB lookups
  3. Numbers are stable across re-runs (deterministic where it matters)
  4. Confidence < 0.4 → qualitative language only (no $ in script)
  5. Personas differentiate meaningfully
"""
from __future__ import annotations
import re
import pytest
import asyncio
from datetime import datetime, timezone, timedelta

from agents.executive_editor.models import Persona
from orchestration.runner import run_briefing
from agents.narrative_writer.citation_enforcer import (
    validate_citations, find_numeric_claims,
)

pytestmark = pytest.mark.integration

DEMO_NIGHT = datetime(2026, 5, 21, tzinfo=timezone.utc)


# ============================================================
# Test 1: Every $ figure has a citation
# ============================================================
@pytest.mark.asyncio
@pytest.mark.parametrize("persona", list(Persona))
async def test_every_dollar_figure_has_citation(persona):
    """
    THE NUMBER ONE TEST.
    If this fails, our trust story falls apart.
    """
    state = await run_briefing(persona=persona, briefing_date=DEMO_NIGHT)
    assert state.get("status") in ("succeeded", "partial"), \
        f"pipeline failed for {persona}: {state.get('errors')}"

    script = state["narrative_script"]
    uncited = validate_citations(script.script_text, script.citations)

    if uncited:
        report = "\n".join(f"  - '{u.text}' ({u.kind})" for u in uncited)
        pytest.fail(
            f"\n{persona.value} briefing contains UNCITED numerical claims:\n{report}\n\n"
            f"All claims must trace to a citation with methodology + Splunk query."
        )


# ============================================================
# Test 2: Determinism — same data → same dollars
# ============================================================
@pytest.mark.asyncio
async def test_dollar_figures_deterministic_across_runs():
    """Same inputs must produce the same numbers (modulo LLM creative rewrite)."""
    runs = []
    for _ in range(3):
        state = await run_briefing(persona=Persona.CEO, briefing_date=DEMO_NIGHT)
        runs.append(state)

    # The Quantifier outputs are deterministic — verify $ stays identical
    refs = runs[0]["quantifier_output"].quantified_signals
    for r in runs[1:]:
        sigs = r["quantifier_output"].quantified_signals
        assert len(sigs) == len(refs), "signal count drifted across runs"
        for s_ref, s in zip(
            sorted(refs, key=lambda x: x.signal_id),
            sorted(sigs, key=lambda x: x.signal_id),
        ):
            assert s.financial_impact.total_exposure_usd == s_ref.financial_impact.total_exposure_usd, \
                f"$ drift on signal {s.signal_id}"
            assert s.priority_score == s_ref.priority_score


# ============================================================
# Test 3: Confidence gate
# ============================================================
@pytest.mark.asyncio
async def test_low_confidence_signals_use_qualitative_language():
    """
    If quantifier confidence < 0.4, the script MUST NOT include a
    specific $ figure for that signal — only qualitative language.
    """
    state = await run_briefing(persona=Persona.CEO, briefing_date=DEMO_NIGHT)
    quantified = state["quantifier_output"].quantified_signals
    script_text = state["narrative_script"].script_text

    for sig in quantified:
        if sig.qualitative_only:
            # Numbers from this signal MUST NOT appear as $ figures
            for step in sig.financial_impact.calculations:
                val = step.result_usd
                # Search for the rounded value in script
                rounded_k = round(val / 1000)
                rounded_str = f"{rounded_k} thousand"
                if rounded_str in script_text.lower():
                    pytest.fail(
                        f"Low-confidence value ${val:,.0f} appeared as "
                        f"'{rounded_str}' in script — should be qualitative"
                    )


# ============================================================
# Test 4: Personalization — personas must differentiate
# ============================================================
@pytest.mark.asyncio
async def test_personas_produce_meaningfully_different_briefings():
    """
    CEO and CISO briefings on the same data must lead with different stories.
    Otherwise our personalization claim is fake.
    """
    ceo  = await run_briefing(persona=Persona.CEO,  briefing_date=DEMO_NIGHT)
    ciso = await run_briefing(persona=Persona.CISO, briefing_date=DEMO_NIGHT)

    ceo_lead  = ceo["editor_output"].clusters[0].theme.value
    ciso_lead = ciso["editor_output"].clusters[0].theme.value
    assert ceo_lead != ciso_lead, \
        f"CEO and CISO both led with {ceo_lead} — personas not differentiated"

    # Headline difference at the text level too
    similarity = _text_similarity(
        ceo["narrative_script"].script_text,
        ciso["narrative_script"].script_text,
    )
    assert similarity < 0.65, \
        f"CEO and CISO scripts are {similarity:.0%} similar — too close"


# ============================================================
# Test 5: Length budget
# ============================================================
@pytest.mark.asyncio
@pytest.mark.parametrize("persona", list(Persona))
async def test_briefing_length_within_budget(persona):
    """Spoken duration must be 130-200s (executive attention budget)."""
    state = await run_briefing(persona=persona, briefing_date=DEMO_NIGHT)
    duration = state["narrative_script"].estimated_duration_sec
    assert 130 <= duration <= 200, \
        f"{persona.value} briefing is {duration}s — must be 130-200s"


# ============================================================
# Test 6: Citation methodology actually contains the number
# ============================================================
@pytest.mark.asyncio
async def test_citation_methodology_contains_traceable_number():
    """
    A citation that says 'we lost $47K' but has methodology 'rev × duration'
    with no numbers is useless. Force methodologies to contain real numbers.
    """
    state = await run_briefing(persona=Persona.CEO, briefing_date=DEMO_NIGHT)
    for cit in state["narrative_script"].citations:
        has_number = bool(re.search(r"\d", cit.methodology))
        assert has_number, \
            f"Citation '{cit.claim_text}' has no number in methodology: '{cit.methodology}'"


# ============================================================
# Test 7: No invented customer names
# ============================================================
@pytest.mark.asyncio
async def test_no_invented_customer_names():
    """Customer names in script must exist in the customers DB."""
    from business_context.loader import all_customer_names
    known = set(c.lower() for c in await all_customer_names())

    state = await run_briefing(persona=Persona.CEO, briefing_date=DEMO_NIGHT)
    script = state["narrative_script"].script_text.lower()

    # Look for capitalized words that look like company names
    # (heuristic: 2+ capitalized words in a row, not at sentence start)
    suspects = re.findall(r"(?<![\.\?\!]\s)([A-Z][a-z]+(?:\s+[A-Z][a-z]+){1,3})",
                          state["narrative_script"].script_text)
    for s in suspects:
        if s.lower() in known: continue
        # Whitelist common non-customer phrases
        if s in ("Splunk Executive Pulse", "Customer Success", "Black Friday",
                "Have", "Good", "Engineering", "May", "Tuesday", "Wednesday"):
            continue
        pytest.fail(f"Possible invented entity in script: '{s}'")


# ============================================================
# Test 8: Decisions must have an owner and concrete options
# ============================================================
@pytest.mark.asyncio
async def test_decisions_well_formed():
    state = await run_briefing(persona=Persona.CEO, briefing_date=DEMO_NIGHT)
    for d in state["editor_output"].decisions_required:
        assert d.owner, "decision missing owner"
        assert len(d.options) >= 2, f"decision '{d.title}' has < 2 options"
        # Approve/Discuss/Defer pattern — must have one actionable option
        labels_lower = [o["label"].lower() for o in d.options]
        assert any(k in " ".join(labels_lower) for k in ("approve", "authorize", "submit")), \
            f"decision '{d.title}' has no actionable option"


# ============================================================
# Test 9: Pipeline observability — all stages timed
# ============================================================
@pytest.mark.asyncio
async def test_pipeline_observability():
    state = await run_briefing(persona=Persona.CEO, briefing_date=DEMO_NIGHT)
    expected_stages = {
        "signal_collector", "business_enricher", "impact_quantifier",
        "executive_editor", "narrative_writer", "audio_producer", "delivery",
    }
    timed = set(state["node_durations_ms"].keys())
    assert expected_stages.issubset(timed), \
        f"missing timings for: {expected_stages - timed}"
    # Total budget: pipeline must complete in < 3 minutes
    total = sum(state["node_durations_ms"].values())
    assert total < 180_000, f"pipeline took {total}ms — must be < 180s"


# ============================================================
# Helpers
# ============================================================
def _text_similarity(a: str, b: str) -> float:
    """Jaccard similarity over word sets — coarse but cheap."""
    sa = set(a.lower().split())
    sb = set(b.lower().split())
    if not sa or not sb: return 0.0
    return len(sa & sb) / len(sa | sb)
