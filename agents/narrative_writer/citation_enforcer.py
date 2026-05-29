# agents/narrative_writer/citation_enforcer.py
"""
Strict numerical claim ↔ citation matching.
This module is the trust core of the entire product.
"""
from __future__ import annotations
import re
import logging
from dataclasses import dataclass

from .models import Citation

logger = logging.getLogger(__name__)


# Regex catches: $47K, $47,000, 47 thousand dollars, 2.3%, 1,247 customers
DOLLAR_PATTERNS = [
    r"\$\s?\d[\d,]*(?:\.\d+)?\s?(?:[KkMmBb]|thousand|million|billion)?",
    r"(?:about\s+)?\d+(?:\.\d+)?\s+(?:thousand|million|billion)\s+dollars?",
]
PERCENT_PATTERN = r"\d+(?:\.\d+)?\s?(?:%|percent)"
COUNT_PATTERN = r"\b\d[\d,]{2,}\b"  # 3+ digit numbers (likely counts)


@dataclass
class UncitedClaim:
    text: str
    span: tuple[int, int]
    kind: str  # "dollar" | "percent" | "count"


def find_numeric_claims(script: str) -> list[tuple[str, tuple[int, int], str]]:
    """Return list of (matched_text, (start, end), kind)."""
    claims = []
    for pat in DOLLAR_PATTERNS:
        for m in re.finditer(pat, script, flags=re.IGNORECASE):
            claims.append((m.group(0), (m.start(), m.end()), "dollar"))
    for m in re.finditer(PERCENT_PATTERN, script, flags=re.IGNORECASE):
        claims.append((m.group(0), (m.start(), m.end()), "percent"))
    for m in re.finditer(COUNT_PATTERN, script):
        # Skip if already inside a dollar match
        if not any(s <= m.start() < e for _, (s, e), _ in claims):
            claims.append((m.group(0), (m.start(), m.end()), "count"))
    return claims


def normalize_number(s: str) -> str:
    """Strip $, commas, words like 'about' for comparison."""
    s = s.lower()
    s = re.sub(r"[\$,]", "", s)
    s = re.sub(r"\b(about|roughly|approximately|around)\b", "", s)
    s = re.sub(r"\s+dollars?\b", "", s)
    s = re.sub(r"\s+", " ", s).strip()
    # Convert "47 thousand" → "47000"
    m = re.match(r"^(\d+(?:\.\d+)?)\s*(thousand|million|billion)?", s)
    if m:
        val = float(m.group(1))
        unit = m.group(2)
        if unit == "thousand": val *= 1_000
        elif unit == "million": val *= 1_000_000
        elif unit == "billion": val *= 1_000_000_000
        return str(int(val)) if val.is_integer() else str(val)
    return s


def validate_citations(
    script: str, citations: list[Citation],
    tolerance: float = 0.05,
) -> list[UncitedClaim]:
    """
    Returns list of uncited numerical claims.
    A claim is 'cited' if its normalized number is within tolerance
    of any number found in citations[*].methodology or claim_text.
    """
    # Extract all numbers from citation pool
    cited_numbers: list[float] = []
    for cit in citations:
        for src in (cit.methodology, cit.claim_text):
            for m in re.finditer(r"\d[\d,]*(?:\.\d+)?", src):
                try:
                    cited_numbers.append(float(m.group(0).replace(",", "")))
                except ValueError:
                    pass

    uncited: list[UncitedClaim] = []
    for text, span, kind in find_numeric_claims(script):
        normalized = normalize_number(text)
        try:
            val = float(normalized)
        except ValueError:
            continue

        if any(abs(val - c) / max(abs(c), 1) <= tolerance for c in cited_numbers):
            continue
        # Allow common safe numbers like dates ("2026"), times ("2:47")
        if _looks_like_date_or_time(text, span, script):
            continue
        uncited.append(UncitedClaim(text=text, span=span, kind=kind))

    return uncited


# Neutral qualitative phrase to substitute for each kind of uncited claim.
_REDACTION_PHRASE = {
    "dollar": "an undisclosed amount",
    "count": "a number of",
    "percent": "a small share",
}


def redact_uncited_claims(
    script: str, citations: list[Citation],
    tolerance: float = 0.05,
) -> str:
    """
    Hard guarantee: remove every uncited numeric claim from `script` by
    replacing its substring with a neutral qualitative phrase appropriate
    to its `kind`, rather than ever publishing a fabricated number.

    Replacements are applied from the rightmost span to the leftmost so
    that earlier spans' offsets remain valid as we mutate the string.
    """
    uncited = validate_citations(script, citations, tolerance=tolerance)
    if not uncited:
        return script

    redacted = script
    for claim in sorted(uncited, key=lambda u: u.span[0], reverse=True):
        start, end = claim.span
        phrase = _REDACTION_PHRASE.get(claim.kind, "an undisclosed amount")
        redacted = redacted[:start] + phrase + redacted[end:]

    return redacted


def _looks_like_date_or_time(text: str, span: tuple[int,int], script: str) -> bool:
    val = text.replace(",", "")
    try:
        n = float(val)
        if 1900 <= n <= 2100: return True  # year
        if 0 <= n <= 59:                    # minute/second
            context = script[max(0, span[0]-5):span[0]]
            if ":" in context: return True
    except ValueError:
        pass
    return False
