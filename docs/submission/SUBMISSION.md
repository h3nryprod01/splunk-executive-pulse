# Splunk Executive Pulse — Devpost submission

> Paste these sections into the matching fields on the Devpost project page.

## Tagline (one line)

From operational data to executive decisions, in three minutes.

## Elevator pitch (≤ 200 chars)

A multi-agent AI that reads your Splunk data overnight and delivers a personalized
3-minute business briefing to each C-suite executive — in language they actually speak.

## Inspiration

Enterprises spend billions on observability, yet the people making million-dollar
decisions can't read the output. Operational signals travel through 3–4 layers of
translation (SRE → manager → VP → CxO), arriving slow, lossy, and disconnected from
business outcomes. Splunk has the data; the C-suite has the questions; nobody built
the translator. That gap is the most expensive unsolved problem in observability —
and it's where Splunk Executive Pulse lives.

## What it does

Every morning, Executive Pulse turns last night's Splunk data into a personalized,
audio-first business briefing for each executive:

- **Reads** Splunk overnight via the **Splunk MCP Server** (anomaly detectors).
- **Enriches** every technical signal with business context — revenue, customers,
  SLAs, compliance — the moat layer.
- **Quantifies** impact in dollars with transparent, citation-backed formulas.
- **Personalizes** per role: the CEO leads with revenue, the **CISO leads with the
  security threat**, the CFO with cost — same data, different lens.
- **Narrates** in a Bloomberg-style 3-minute brief using **Splunk Hosted Models**.
- **Delivers** by email, Slack, and an executive dashboard, with an
  **AI-Assistant-for-SPL drill-down** so any plain-English follow-up becomes SPL.

## How we built it

A 7-agent pipeline orchestrated with **LangGraph** (typed state, retry, conditional
routing, checkpointer, structured observability):

`Signal Collector → Business Enricher → Impact Quantifier → Executive Editor →
Narrative Writer → Decision Highlighter → Audio Producer → Delivery`

- **Backend:** Python 3.11, Pydantic-typed contracts between every agent.
- **Splunk capabilities used (4):** MCP Server (search + lookups), Hosted Models
  (primary LLM), AI Assistant for SPL (NL→SPL drill-down), AI Toolkit / MLTK
  (`predict`/`anomalydetection` SPL for native forecasting).
- **Frontend:** Next.js 14 + Tailwind executive dashboard (persona switcher, audio
  player, story cards with citation tooltips, decision cards).
- **Infra:** Docker Compose (Splunk + Postgres + Redis) + `make demo`.
- **Anti-hallucination:** every `$` figure carries a source SPL query, a formula, and
  a confidence score; below 0.4 confidence the brief uses qualitative language only.
  Hypothesis property tests prove the citation invariants.

The whole deterministic backbone runs **with zero infrastructure and zero API keys**
(CSV-backed context store + mock Splunk), so judges can run it instantly.

## Challenges we ran into

- **Trust at the executive level.** A hallucinated dollar figure in a CEO brief is
  catastrophic. We made citations first-class and added property-based tests that
  flag any number that drifts >5% from its citation.
- **Cross-module type contracts.** Wiring 7 independently-typed agents surfaced two
  real integration bugs (a graph routing-key mismatch and a `RawSignal` boundary
  conversion) — caught by running the full graph end-to-end.
- **Personalization that's real, not cosmetic.** A blocked-but-serious attack scores
  low on pure dollars, so we made the persona "lens" dominate ranking — that's why
  the CISO headlines the attack while the CEO headlines revenue.

## Accomplishments we're proud of

- The full LangGraph pipeline runs **end-to-end, keyless**, in seconds.
- A defensible **Business Context Layer** — a real enterprise data model, not an LLM
  wrapper.
- **Four** Splunk AI capabilities integrated.
- Genuine **per-persona differentiation** of the briefing headline.
- 20 automated tests (unit + property-based anti-hallucination) passing.

## What we learned

Executives don't want dashboards; they want decisions. The hard part isn't the LLM —
it's the business-context join and the discipline to never fabricate a number.

## What's next

- Live run against real Splunk + Splunk Hosted Models + ElevenLabs.
- Real-time briefings, voice cloning, multi-language, interactive Slack decisions.

## Built with

`python` `langgraph` `pydantic` `splunk-mcp-server` `splunk-hosted-models`
`splunk-ai-assistant-for-spl` `splunk-ai-toolkit-mltk` `nextjs` `react` `tailwindcss`
`postgres` `redis` `elevenlabs` `docker`

## Prizes targeted

Grand Prize · Best of Platform & Developer Experience · Best Use of Splunk MCP Server
· Best Use of Splunk Hosted Models

## Try it

```bash
python -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt
python business_context/seed_data/generate_customers.py
pytest -q                                             # 17 unit tests
python orchestration/graph_e2e_demo.py --persona CISO # full graph, keyless
cd web && npm install && npm run dev                  # dashboard at :3000
```
