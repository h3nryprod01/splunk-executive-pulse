# SOC Triage Copilot

An autonomous Tier-1 SOC analyst. Given a security alert, it **investigates
across multiple SPL searches**, pivoting on what it finds — brute-force burst →
did a login succeed from the attacker IP? → what did the compromised account do
next? — then issues a triage verdict with containment actions.

Built for the **Splunk Agentic Ops Hackathon 2026** · targets the **Security**
track and *Best Use of Splunk MCP Server* (investigation = many real searches).
Independent of the Executive Pulse and SPL Copilot submissions; shares only the
low-level Splunk clients.

## The agentic loop (pivoting investigation)

1. **Detect** with **MLTK** `| anomalydetection`: is the blocked-auth rate a
   real spike, and from which source IPs? (replaces assuming the alert is valid).
2. **Pivot** on the discovered IPs: did any login *succeed* from them? → takeover.
3. **Pivot** on the compromised account: post-login data access?
4. **Verdict**: deterministic severity + classification + containment actions.
5. **Narrate**: an analyst-facing incident summary via **Splunk Hosted Models**
   when configured (offline template otherwise); the verdict stays deterministic.

Each step's output feeds the next query — that is the agentic behaviour, not a
fixed report.

## Run it (zero infra, zero keys)

```bash
python -m soc_triage.demo
pytest soc_triage/tests -q
```

Expected: 4 searches, an ordered attack timeline, and a **CRITICAL — Account
takeover** verdict recommending account disable + IP block + breach review.

## Live Splunk

Inject a searcher backed by the shared MCP client:

```python
from soc_triage.copilot import SOCTriageCopilot
report = SOCTriageCopilot(searcher=my_mcp_search).triage(alert)
```

`searcher` is any `Callable[[str], list[dict]]` — wrap
`agents/signal_collector/splunk_mcp.py:SplunkMCPSearchClient.search`.

## Layout

| File | Role |
|---|---|
| `copilot.py` | alert -> investigation -> verdict -> narrative |
| `investigator.py` | multi-step pivoting search loop + timeline |
| `detection.py` | MLTK anomalydetection (shared `agents.common.splunk_ai.mltk`) |
| `triage.py` | deterministic severity/verdict/containment |
| `narrate.py` | Hosted Models incident narrative + offline fallback |
| `mock_splunk.py` | keyless security events + SPL search executor |
| `models.py` | typed contracts |
