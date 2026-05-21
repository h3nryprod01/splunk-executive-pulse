"""
Recompute each briefing's headline_quote from its saved script_text — pick the
first substantive impact sentence (skipping the greeting) so the dashboard header
leads with the story, not "Good morning". No LLM calls.

    python orchestration/polish_headlines.py
"""
from __future__ import annotations
import json
import re
from pathlib import Path

OUT_DIR = Path(__file__).resolve().parent.parent / "web" / "public" / "briefings"
_GREETING = re.compile(r"good morning|executive pulse|this is your", re.I)


def pick_headline(script_text: str) -> str:
    sentences = [s.strip() for s in re.split(r"(?<=[.!?])\s+", script_text) if s.strip()]
    # Prefer the first sentence with a dollar/number impact and no greeting.
    for s in sentences:
        if _GREETING.search(s):
            continue
        if "$" in s or re.search(r"\b(thousand|million|percent|customers|dollars)\b", s, re.I):
            return s
    # Otherwise the first non-greeting sentence.
    for s in sentences:
        if not _GREETING.search(s):
            return s
    return sentences[0] if sentences else ""


def main() -> None:
    changed = 0
    for f in sorted(OUT_DIR.glob("*-latest.json")):
        d = json.loads(f.read_text())
        script = d.get("script_text")
        if not script:
            continue
        new_q = pick_headline(script)
        if new_q and new_q != d.get("headline_quote"):
            d["headline_quote"] = new_q
            dated = f.with_name(f.name.replace("-latest", f"-{d['briefing_date']}"))
            text = json.dumps(d, indent=2)
            f.write_text(text)
            if dated.exists():
                dated.write_text(text)
            changed += 1
            print(f"  {d['persona']}: {new_q[:80]}")
    print(f"Polished {changed} briefings.")


if __name__ == "__main__":
    main()
