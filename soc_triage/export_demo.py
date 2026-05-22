"""Export a SOC Triage incident report to JSON for the web demo.

    python -m soc_triage.export_demo
    -> web/public/soc_triage/incident.json

Mirrors spl_copilot/export_demo.py and the main project's export_briefings.py.
"""
from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path

from .copilot import SOCTriageCopilot
from .demo import SAMPLE_ALERT

OUT = Path(__file__).resolve().parent.parent / "web" / "public" / "soc_triage" / "incident.json"


def main() -> None:
    report = SOCTriageCopilot().triage(SAMPLE_ALERT)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(asdict(report), indent=2))
    print(f"Wrote incident report ({report.verdict.severity}, "
          f"{report.searches_run} searches) to {OUT}")


if __name__ == "__main__":
    main()
