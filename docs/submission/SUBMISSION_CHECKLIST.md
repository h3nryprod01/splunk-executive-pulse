# Submission checklist — Splunk Agentic Ops Hackathon

## Devpost requirements coverage

| Requirement | Status | Where |
|---|---|---|
| Text description (project story) | ✅ | [SUBMISSION.md](SUBMISSION.md) |
| Demo video (≤ 3 min) | ⬜ **record** | script in [DEMO_SCRIPT.md](DEMO_SCRIPT.md) |
| Open-source repository | ⬜ **push to GitHub** | `git init` done locally — see below |
| README | ✅ | [../../README.md](../../README.md) |
| Architecture diagram | ✅ | [../../ARCHITECTURE.md](../../ARCHITECTURE.md) (3 Mermaid diagrams) |
| Open-source license | ✅ | [../../LICENSE](../../LICENSE) (MIT) |

## Required Splunk capabilities (used → eligible for prizes)

| Capability | Used | Code |
|---|---|---|
| Splunk MCP Server | ✅ | `agents/signal_collector/splunk_mcp.py`, `agents/business_enricher/tools.py` |
| Splunk Hosted Models | ✅ (primary LLM) | `agents/narrative_writer/llm_client.py` |
| Splunk AI Assistant for SPL | ✅ | `agents/common/splunk_ai/spl_assistant.py`, `orchestration/drilldown_demo.py` |
| Splunk AI Toolkit (MLTK) | ✅ | `agents/common/splunk_ai/mltk.py`, `agents/signal_collector/detectors/forecast.py` |
| AI agents | ✅ | 7-agent LangGraph pipeline |

## Judging-criteria mapping

- **Technological Implementation** — typed 7-agent LangGraph pipeline runs end-to-end;
  deterministic financial math; 20 automated tests (unit + Hypothesis property tests).
- **Design** — audio-first 3-min brief; Next.js dashboard; per-persona personalization.
- **Potential Impact** — expands Splunk's audience from engineers to the C-suite;
  every Splunk customer has a C-suite that doesn't consume Splunk today.
- **Quality of the Idea** — the Business Context Layer is a defensible moat, not an LLM
  wrapper; per-persona headline differentiation ("same data, different lens").

## Tracks

Cross-track: Observability (anomaly detection), Security (credential-stuffing signal),
Platform & DevEx (a new agentic product layer + NL→SPL drill-down).

## Verify before submitting (all keyless)

```bash
python -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt
python business_context/seed_data/generate_customers.py
pytest -q                                                          # 17 passed
SKIP_STACK_CHECK=1 SKIP_SEED=1 pytest tests/integration/test_property_based.py -q  # 3 passed
python orchestration/graph_e2e_demo.py --persona CISO              # status: succeeded
cd web && npm install && npm run build                             # ✓ compiled
```

## Final steps

1. **Record the demo video** following [DEMO_SCRIPT.md](DEMO_SCRIPT.md); upload public/unlisted; put the link in the README badge + Devpost.
2. **Publish the repo:**
   ```bash
   git init && git add . && git commit -m "Splunk Executive Pulse"
   gh repo create splunk-executive-pulse --public --source=. --push
   ```
   (`.env`, `node_modules/`, `.next/`, `*.mp3`, generated `customers.csv` are gitignored.)
3. **Fill the Devpost form** with the sections from [SUBMISSION.md](SUBMISSION.md);
   add the repo URL + video URL; select the 4 target prizes; tag the "Built with" list.
4. Double-check no secrets are committed (`.env` is ignored; only `.env.example` ships).
