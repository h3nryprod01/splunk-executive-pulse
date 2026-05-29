# agents/narrative_writer/tests/test_citation_redaction.py
"""
Anti-hallucination hard guarantee: any numeric claim that is NOT backed by a
citation must be REDACTED (replaced with a neutral qualitative phrase), never
published as a fabricated number.
"""
from agents.narrative_writer.citation_enforcer import (
    redact_uncited_claims,
    validate_citations,
)
from agents.narrative_writer.models import Citation


def _citations() -> list[Citation]:
    # Only $46,992 is a legitimately cited figure.
    return [
        Citation(
            claim_text="$46,992 (Direct revenue loss)",
            source_signal_id="sig_001",
            methodology="$3,916/min × 12 min",
            confidence=0.9,
        ),
    ]


def test_fabricated_dollar_is_redacted_and_validation_passes():
    citations = _citations()

    # $250,000 appears nowhere in the citation pool — a fabricated figure.
    script = (
        "The payment outage caused $46,992 in direct revenue loss, "
        "and we estimate another $250,000 in downstream damage."
    )

    # Sanity check: the fabricated number is flagged before redaction.
    pre = validate_citations(script, citations)
    assert any("250,000" in u.text or "250000" in u.text.replace(",", "")
               for u in pre)

    redacted = redact_uncited_claims(script, citations)

    # (a) the fabricated number is gone
    assert "$250,000" not in redacted
    assert "250,000" not in redacted
    # cited figure is preserved
    assert "$46,992" in redacted
    # replaced with a neutral qualitative phrase for a dollar claim
    assert "an undisclosed amount" in redacted

    # (b) validation on the redacted text is empty
    assert validate_citations(redacted, citations) == []


def test_redaction_is_noop_when_all_cited():
    citations = _citations()
    script = "Direct revenue loss was $46,992 during the incident."
    assert redact_uncited_claims(script, citations) == script
