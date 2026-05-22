"""
Run the real SPL Copilot pipeline (NL -> SPL, self-critique loop, explanation)
over a handful of sample intents and export the serialized CopilotResults to
web/public/spl_copilot/scenarios.json.

The Next.js /spl-copilot page reads these scenarios via /api/spl-copilot, so the
UI shows output computed by the actual copilot - no API keys or live Splunk
required (the copilot falls back to an offline deterministic source).

    python -m spl_copilot.export_demo
"""
from __future__ import annotations

import asyncio
import dataclasses
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from spl_copilot.copilot import SPLCopilot

ROOT = Path(__file__).resolve().parent.parent
OUT_DIR = ROOT / "web" / "public" / "spl_copilot"

# A nonsense intent is included on purpose to show the "could not fix" state.
INTENTS: tuple[str, ...] = (
    "show me payment errors",
    "blocked logins by source ip",
    "checkout latency",
    "purple monkey dishwasher zorp",
)


async def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    copilot = SPLCopilot()

    scenarios: list[dict] = []
    for intent in INTENTS:
        result = await copilot.run(intent)
        scenarios.append(dataclasses.asdict(result))
        print(
            f"  {intent!r}: {result.row_count} rows, "
            f"{len(result.steps)} critique step(s), source={result.spl_source}"
        )

    payload = {"scenarios": scenarios}
    (OUT_DIR / "scenarios.json").write_text(json.dumps(payload, indent=2))
    print(f"Wrote {len(scenarios)} scenarios to {OUT_DIR / 'scenarios.json'}")


if __name__ == "__main__":
    asyncio.run(main())
