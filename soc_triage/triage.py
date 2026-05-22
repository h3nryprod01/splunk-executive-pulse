"""Turn investigation facts into a triage verdict + containment actions.

Deterministic so the demo verdict never drifts (mirrors the main project's
anti-hallucination stance). An LLM could narrate the rationale in live mode.
"""
from __future__ import annotations

from .models import Finding, TriageVerdict


def assess(facts: dict, findings: tuple[Finding, ...]) -> TriageVerdict:
    attacker_ips: list[str] = facts.get("attacker_ips", [])
    comp_users: list[str] = facts.get("compromised_users", [])
    data_access: list[dict] = facts.get("data_access", [])

    if comp_users:
        actions = [f'Disable account(s): {", ".join(comp_users)}',
                   f'Block source IP(s): {", ".join(attacker_ips)}',
                   "Force password reset + revoke active sessions"]
        if data_access:
            records = sum(int(a.get("count", 0)) for a in data_access)
            actions.append(f"Open data-breach review — {records} records accessed")
        return TriageVerdict(
            severity="CRITICAL",
            classification="Account takeover via credential stuffing",
            confidence=0.9,
            recommended_actions=tuple(actions),
            rationale=("A successful login followed a brute-force burst from the same "
                       f'source IP(s) ({", ".join(attacker_ips)}); '
                       f'account(s) {", ".join(comp_users)} are presumed compromised'
                       + (" with post-compromise data export." if data_access else ".")),
        )

    if attacker_ips:
        return TriageVerdict(
            severity="HIGH",
            classification="Credential-stuffing attack (no confirmed compromise)",
            confidence=0.7,
            recommended_actions=(
                f'Block source IP(s): {", ".join(attacker_ips)}',
                "Enable rate limiting / CAPTCHA on auth endpoint",
                "Enforce MFA for targeted accounts"),
            rationale=("Repeated blocked login attempts from a small set of source IPs; "
                       "no successful login observed."),
        )

    return TriageVerdict(
        severity="LOW", classification="No actionable signal", confidence=0.5,
        recommended_actions=("Monitor — no follow-up required",),
        rationale="No blocked-auth burst found for this alert window.")
