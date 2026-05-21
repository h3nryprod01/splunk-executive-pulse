"""
Dump the Splunk-AI-Assistant-for-SPL offline phrasebook to a static JSON the
Next.js dashboard reads, so the drill-down works on a fresh clone without Python.
Python remains the source of truth (agents/common/splunk_ai/spl_assistant.py).

    python orchestration/export_spl_phrasebook.py
"""
from __future__ import annotations
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from agents.common.splunk_ai.spl_assistant import _PHRASEBOOK

OUT = Path(__file__).resolve().parent.parent / "web" / "public" / "spl-phrasebook.json"


def main() -> None:
    data = [
        {"keywords": list(keywords), "spl": spl, "explanation": explanation}
        for keywords, spl, explanation in _PHRASEBOOK
    ]
    OUT.write_text(json.dumps(data, indent=2))
    print(f"Wrote {len(data)} phrasebook entries -> {OUT}")


if __name__ == "__main__":
    main()
