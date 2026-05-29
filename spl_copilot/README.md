# SPL Copilot — "Cursor for Splunk"

A DevEx agent that turns plain English into **correct, runnable SPL**. Unlike a
plain NL→SPL wrapper, it runs a **self-critique loop**: when a generated query
references a field the index doesn't have, the agent rewrites it against the
real schema and re-runs — instead of silently returning zero results.

Built for the **Splunk Agentic Ops Hackathon 2026** · targets *Best of Platform
& DevEx* and *Best Use of Splunk AI Assistant for SPL*. Independent of the
Executive Pulse submission; shares only the low-level Splunk clients.

## The loop

1. **NL → SPL** — Splunk AI Assistant for SPL (`agents/common/splunk_ai`, with
   an offline phrasebook so demos run keyless).
2. **Run** — `MockExecutor` (keyless) or `MCPExecutor` (live Splunk MCP server).
3. **Self-critique** — on an unknown field, remap against the index schema
   (alias table + fuzzy match); if that fails and credentials are present, fall
   back to **Splunk Hosted Models** for the remap. Re-run, up to `max_fixes` times.
4. **Explain** — pipe-by-pipe breakdown via **Splunk Hosted Models** when
   configured, with a deterministic offline template as the keyless fallback
   (`explanation_source` records which was used).

## Run it (zero infra, zero keys)

```bash
python -m spl_copilot.demo "show me payment errors"
pytest spl_copilot/tests -q
```

Expected: the assistant emits `status>=500`, the executor flags `status` as
unknown for `payment-svc`, the copilot remaps it to `http_status`, re-runs, and
returns rows — with the correction shown in the trace.

## Live Splunk

Wrap the shared MCP client and swap the executor:

```python
from agents.signal_collector.splunk_mcp import SplunkMCPSearchClient
from spl_copilot.executor import MCPExecutor
from spl_copilot.copilot import SPLCopilot

executor = MCPExecutor(SplunkMCPSearchClient(mcp_url=..., api_token=...))
```

## Layout

| File | Role |
|---|---|
| `copilot.py` | orchestrates NL→SPL→run→self-fix→explain |
| `critique.py` | field remapping (alias + fuzzy) |
| `mock_index.py` | keyless in-memory Splunk + SPL parser/validator |
| `executor.py` | `MockExecutor` / `MCPExecutor` |
| `explain.py` | pipe-by-pipe explanation |
| `models.py` | typed result contracts |
