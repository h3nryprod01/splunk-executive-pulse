"""Typed data contracts for the SPL Copilot."""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class RunResult:
    """Outcome of executing one SPL query."""

    spl: str
    rows: tuple[dict, ...] = ()
    error: str | None = None
    unknown_fields: tuple[str, ...] = ()

    @property
    def ok(self) -> bool:
        return self.error is None and not self.unknown_fields and len(self.rows) > 0


@dataclass(frozen=True)
class CritiqueStep:
    """One self-correction the copilot applied before re-running."""

    reason: str
    before_spl: str
    after_spl: str


@dataclass(frozen=True)
class CopilotResult:
    """Final answer after NL->SPL, self-critique loop, and explanation."""

    intent: str
    final_spl: str
    rows: tuple[dict, ...]
    steps: tuple[CritiqueStep, ...]
    explanation: str
    spl_source: str
    row_count: int
