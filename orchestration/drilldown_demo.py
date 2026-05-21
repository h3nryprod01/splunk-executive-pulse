"""
Briefing drill-down loop demo: after the morning brief, an executive asks a
plain-English follow-up. The Splunk AI Assistant for SPL turns it into SPL,
which would run via the MCP search tool. Runs zero-infra (offline fallback).

    python orchestration/drilldown_demo.py
"""
from __future__ import annotations
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from agents.common.splunk_ai.spl_assistant import SplunkSPLAssistant

QUESTIONS = [
    "Tell me more about that payment incident — show me the payment errors.",
    "Was there a credential stuffing attack last night?",
    "Why is checkout latency degrading?",
    "Are we over budget on infrastructure cost this month?",
]


async def main() -> None:
    assistant = SplunkSPLAssistant()
    print("Executive drill-down  (Splunk AI Assistant for SPL)\n")
    for q in QUESTIONS:
        s = await assistant.generate_spl(q)
        print(f"Q: {q}")
        print(f"   SPL [{s.source} · conf {s.confidence:.1f}]: {s.spl}")
        print(f"   → {s.explanation}\n")


if __name__ == "__main__":
    asyncio.run(main())
