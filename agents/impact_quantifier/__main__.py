# agents/impact_quantifier/__main__.py
"""
python -m agents.impact_quantifier
Pipes from Business Enricher output JSON on stdin → QuantifierOutput on stdout.
"""
import sys, json
from agents.business_enricher.models import EnricherOutput
from .agent import ImpactQuantifierAgent


def main():
    raw = sys.stdin.read()
    enricher_out = EnricherOutput.model_validate_json(raw)
    agent = ImpactQuantifierAgent()
    out = agent.run(enricher_out)
    print(json.dumps(out.model_dump(mode="json"), indent=2, default=str))


if __name__ == "__main__":
    main()
