"""Keyless CLI demo for the SOC Triage Copilot.

    python -m soc_triage.demo
"""
from __future__ import annotations

from .copilot import SOCTriageCopilot
from .models import Alert

SAMPLE_ALERT = Alert(
    alert_id="ALERT-2026-0517",
    title="Spike in blocked authentication attempts on auth-svc",
    alert_type="credential_stuffing",
    index="security",
    sourcetype="auth-svc",
)


def main() -> None:
    report = SOCTriageCopilot().triage(SAMPLE_ALERT)

    print(f"\n=== {report.alert.alert_id}: {report.alert.title} ===")
    print(f"Searches run: {report.searches_run}\n")

    print("Investigation:")
    for f in report.findings:
        print(f"  [{f.step}] {f.question}")
        print(f"      SPL: {f.spl}")
        print(f"      -> {f.summary}  ({f.row_count} rows)")

    print("\nAttack timeline:")
    for t in report.timeline:
        print(f"  {t.time}  {t.actor:<12} {t.action:<14} {t.detail}")

    v = report.verdict
    print(f"\nVERDICT: {v.severity} — {v.classification} (confidence {v.confidence:.2f})")
    print(f"  {v.rationale}")
    print("  Recommended actions:")
    for a in v.recommended_actions:
        print(f"    - {a}")
    print()


if __name__ == "__main__":
    main()
