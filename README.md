# Splunk Executive Pulse

Turns Splunk operational data into a personalized **3-minute daily business
briefing** for C-suite executives — delivered as audio + a one-page brief, in
language executives actually speak.

Built for the **Splunk Agentic Ops Hackathon 2026**.

## The problem

Enterprises spend billions on observability, yet the executives making business
decisions cannot consume that data. It travels through 3-4 layers of translation,
arrives slow and lossy, and rarely connects technical signals to business outcomes.

## The solution

A multi-agent pipeline that reads Splunk overnight, **enriches** every technical
signal with business context (revenue, customers, SLAs, compliance), **quantifies**
impact in dollars with transparent methodology, **personalizes** per executive role,
and **narrates** in a Bloomberg-style brief.

The moat is the **Business Context Layer** — a real enterprise data model that joins
ops signals to revenue/customers/SLAs. Not a wrapper around an LLM.

## Pipeline (6 agents)

1. Signal Collector — Splunk MCP, anomaly detection → `RawSignal[]`
2. **Business Enricher ⭐** — joins business context → `EnrichedSignal[]`
3. **Impact Quantifier ⭐** — deterministic `$` math + citations
4. Executive Editor — persona weighting + clustering (also extracts binary decisions / one-click actions)
5. Narrative Writer — two-pass LLM, citation enforcement
6. Audio Producer — ElevenLabs TTS

> Backlog: a standalone **Decision Highlighter** agent (dedicated binary-decision /
> one-click-action surface) is planned; today the Executive Editor performs decision
> extraction inline.

## What runs today

The **moat slice** (Business Enricher) is implemented, tested, and runnable with
zero infrastructure (CSV-backed in-memory context store):

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# generate the 1,247-customer demo dataset
python business_context/seed_data/generate_customers.py

# unit tests (30 passing)
pytest -q

# anti-hallucination proof (keyless, 3 Hypothesis property tests)
SKIP_STACK_CHECK=1 SKIP_SEED=1 pytest tests/integration/test_property_based.py -q
# full integration suite (tests/integration/test_no_hallucination.py) needs `make up` + an LLM key

# zero-infra demo: enrich the payment-outage signal from the demo night
python orchestration/run_enricher_demo.py

# full deterministic backbone across 3 demo-night stories, per persona
python orchestration/pipeline.py --persona CISO

# the REAL LangGraph pipeline end-to-end, keyless (writer/audio/delivery stubbed)
#   requires langgraph installed (already covered by `pip install -r requirements.txt`)
python orchestration/graph_e2e_demo.py --persona CISO

# executive drill-down: plain-English question -> SPL (Splunk AI Assistant)
python orchestration/drilldown_demo.py

# anti-hallucination gate: low confidence -> dollar figure withheld (not fabricated)
python orchestration/qualitative_demo.py
```

The dashboard also has a live **"Ask about last night"** panel (the drill-down loop)
backed by `/api/drilldown`, and story cards render a **"qualitative only"** notice
(withholding dollar figures) when a signal's confidence is below threshold.

Executive dashboard (Next.js 14, mock-data backed — persona switcher, audio
player, story cards with citation tooltips, decision cards):

```bash
# (optional) keyless briefings (deterministic, no LLM/TTS)
python orchestration/export_briefings.py         # -> web/public/briefings/*.json

# (optional) LIVE briefings: real narration (Splunk Hosted Models / LLM) + audio
#   needs .env with SPLUNK_LLM_* or ANTHROPIC_API_KEY (+ ELEVENLABS_API_KEY for --audio)
set -a && source .env && set +a
python orchestration/export_briefings_live.py --all --audio

cd web && npm install && npm run dev             # http://localhost:3000
```

The dashboard fetches `/api/briefing?persona=X` (served from the exported JSON);
if no briefings have been exported it falls back to built-in mock data, so the UI
always renders.

Expected demo output (Story A — payment gateway outage):

```
service tier      : tier-0
revenue / minute  : $3,916
customers affected: 1,247 (34 enterprise)
SLA breaches      : 12 contracts, $45,780 credit liability
regulated data    : PCI
confidence        : 1.00
```

The production path (`BusinessContextStore`, asyncpg) and `MCPClient` are wired in
`agents/business_enricher/tools.py`; the demo uses `InMemoryContextStore` so the
slice runs without Splunk or Postgres.

## Status

Extracted, compiling, and tested (30 unit tests + 3 Hypothesis property tests = 33 automated tests passing):

- [x] Signal Collector — MCP wrapper + detectors + SPL queries
- [x] Business Enricher — moat layer (CSV store for zero-infra demo)
- [x] Impact Quantifier — deterministic calculators
- [x] Executive Editor — persona logic + clustering
- [x] Narrative Writer — two-pass generation + citation enforcer *(needs LLM key to run)*
- [x] Audio Producer — ElevenLabs integration *(needs key to run)*
- [x] LangGraph orchestration — `state/nodes/graph/retry/observability/runner` *(needs `pip install langgraph` + delivery)*
- [x] Splunk AI Assistant for SPL + AI Toolkit (MLTK) — `agents/common/splunk_ai/`

- [x] delivery/ (email/Slack/dashboard) + integration test suite
- [x] Next.js executive dashboard (`web/` — builds clean with `npm run build`)
- [x] docker-compose (Splunk + Postgres + Redis) + Makefile (`make demo`) + Eventgen plan

- [x] Full LangGraph end-to-end (keyless via `graph_e2e_demo.py`; real stack needs `make up` + LLM/ElevenLabs keys)
- [x] Per-persona headline differentiation — CISO leads with the security threat, CEO/CFO/CTO/COO with the revenue incident

Backlog:

- [ ] Live run against real Splunk + Splunk Hosted Models + ElevenLabs (credentials)

## Companion copilots

Two additional, independently-runnable agents ship in this repo. Both run zero-infra /
keyless (offline-safe) and use Splunk AI capabilities when keys are present. They share
only the low-level Splunk clients with Executive Pulse.

- **SPL Copilot** — NL→SPL with a self-critique loop. When a generated query references
  a field the index doesn't have, the agent remaps it against the real index schema
  (alias table + fuzzy match) and re-runs, instead of silently returning zero results.
  Uses Splunk AI Assistant for SPL / Hosted Models when keys are present.

  ```bash
  python -m spl_copilot.demo "show me payment errors"
  ```

  See [spl_copilot/README.md](spl_copilot/README.md).

- **SOC Triage Copilot** — autonomous credential-stuffing investigation. MLTK
  anomaly detection → pivot to successful logins from the attacker IPs → data-export
  check → deterministic **CRITICAL** verdict + analyst narrative.

  ```bash
  python -m soc_triage.demo
  ```

  See [soc_triage/README.md](soc_triage/README.md).

## Prizes targeted

Grand Prize · Best of Platform & DevEx · Best Use of Splunk MCP Server ·
Best Use of Splunk Hosted Models

## License

MIT
