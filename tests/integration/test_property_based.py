# tests/integration/test_property_based.py
"""
Property-based tests: invariants that must hold for ANY input.
Uses Hypothesis to generate adversarial inputs.
"""
import pytest
from hypothesis import given, strategies as st, settings
from agents.narrative_writer.citation_enforcer import (
    validate_citations, find_numeric_claims, normalize_number,
)
from agents.narrative_writer.models import Citation


def _cit(claim: str, methodology: str = "test formula") -> Citation:
    return Citation(claim_text=claim, source_signal_id="sig_x",
                    methodology=methodology, confidence=0.85)


@given(amount=st.integers(min_value=100, max_value=10_000_000))
@settings(max_examples=200)
def test_any_dollar_amount_with_matching_citation_passes(amount):
    """For any amount with a matching citation, validator must accept."""
    script = f"We lost about ${amount:,} overnight."
    citations = [_cit(f"${amount:,}", f"formula = {amount}")]
    uncited = validate_citations(script, citations)
    assert uncited == []


@given(
    cited_amount=st.integers(min_value=1000, max_value=1_000_000),
    actual_amount=st.integers(min_value=1000, max_value=1_000_000),
)
@settings(max_examples=200)
def test_mismatched_amounts_get_flagged(cited_amount, actual_amount):
    """When script number differs >5% from citations, must flag."""
    if abs(actual_amount - cited_amount) / cited_amount <= 0.05:
        return  # within tolerance — skip
    script = f"We lost about ${actual_amount:,} overnight."
    citations = [_cit(f"${cited_amount:,}", f"formula = {cited_amount}")]
    uncited = validate_citations(script, citations)
    # At least one number should be flagged
    assert len(uncited) >= 1


@given(year=st.integers(min_value=1900, max_value=2100))
def test_years_never_flagged_as_uncited(year):
    script = f"This is your briefing for May 21, {year}."
    uncited = validate_citations(script, [])
    assert uncited == []
