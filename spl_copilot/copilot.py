"""SPL Copilot: natural language -> SPL -> run -> self-fix -> explain.

The differentiator is the self-critique loop: when a generated query references
a field that doesn't exist in the index, the copilot rewrites it against the
real schema and re-runs — instead of silently returning zero results.
"""
from __future__ import annotations

import sys
from pathlib import Path

# Reuse the shared Splunk AI Assistant (NL->SPL) from the main project.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from agents.common.splunk_ai.spl_assistant import SplunkSPLAssistant  # noqa: E402

from .critique import fix_unknown_fields
from .explain import explain_spl
from .mock_index import MockExecutor
from .models import CopilotResult, CritiqueStep


class SPLCopilot:
    def __init__(self, assistant=None, executor=None, max_fixes: int = 2):
        self.assistant = assistant or SplunkSPLAssistant()
        self.executor = executor or MockExecutor()
        self.max_fixes = max_fixes

    async def run(self, nl_intent: str) -> CopilotResult:
        suggestion = await self.assistant.generate_spl(nl_intent)
        spl = suggestion.spl
        steps: list[CritiqueStep] = []

        result = self.executor.run(spl)
        for _ in range(self.max_fixes):
            if result.ok or not result.unknown_fields:
                break
            fix = fix_unknown_fields(
                spl, result.unknown_fields, self.executor.fields_for(spl),
            )
            if fix is None:
                break
            new_spl, reason = fix
            steps.append(CritiqueStep(reason=reason, before_spl=spl, after_spl=new_spl))
            spl = new_spl
            result = self.executor.run(spl)

        return CopilotResult(
            intent=nl_intent,
            final_spl=spl,
            rows=result.rows,
            steps=tuple(steps),
            explanation=explain_spl(spl),
            spl_source=suggestion.source,
            row_count=len(result.rows),
        )
