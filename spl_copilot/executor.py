"""Executors the copilot can run SPL through.

`MockExecutor` (in mock_index) is the keyless default. `MCPExecutor` wraps the
real Splunk MCP search client so the same copilot runs against a live stack.
"""
from __future__ import annotations

from datetime import datetime, timedelta
from typing import Protocol

from .mock_index import MockExecutor
from .models import RunResult


class Executor(Protocol):
    def run(self, spl: str) -> RunResult: ...
    def fields_for(self, spl: str) -> set[str]: ...


class MCPExecutor:
    """Adapts agents.signal_collector.splunk_mcp.SplunkMCPSearchClient.

    Field validation against a live index would come from `| fieldsummary`;
    omitted here since the live path needs credentials. The mock path exercises
    the self-critique loop end to end.
    """

    def __init__(self, client, window_hours: int = 24):
        self._client = client
        self._window = timedelta(hours=window_hours)

    def fields_for(self, spl: str) -> set[str]:
        return set()

    async def run_async(self, spl: str) -> RunResult:
        latest = datetime.utcnow()
        try:
            rows = await self._client.search(spl, latest - self._window, latest)
            return RunResult(spl=spl, rows=tuple(rows))
        except Exception as e:  # pragma: no cover - network path
            return RunResult(spl=spl, error=str(e))


__all__ = ["Executor", "MockExecutor", "MCPExecutor"]
