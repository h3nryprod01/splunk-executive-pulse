"""Keyless CLI demo for the SPL Copilot.

    python -m spl_copilot.demo "show me payment errors"
    python -m spl_copilot.demo            # runs a default scenario
"""
from __future__ import annotations

import asyncio
import sys

from .copilot import SPLCopilot


async def _main(intent: str) -> None:
    copilot = SPLCopilot()
    result = await copilot.run(intent)

    print(f"\nIntent      : {result.intent}")
    print(f"SPL source  : {result.spl_source}")
    if result.steps:
        print("\nSelf-critique:")
        for i, step in enumerate(result.steps, 1):
            print(f"  {i}. {step.reason}")
            print(f"     before: {step.before_spl}")
            print(f"     after : {step.after_spl}")
    else:
        print("\nSelf-critique: (none — query was valid on first try)")

    print(f"\nFinal SPL   : {result.final_spl}")
    print(f"Rows        : {result.row_count}")
    print("\nExplanation :")
    print(result.explanation)
    print()


if __name__ == "__main__":
    intent = " ".join(sys.argv[1:]) or "show me payment errors"
    asyncio.run(_main(intent))
