"""
Generate an .srt caption file for a persona's hero narration, timed to the real
mp3 duration (via ffprobe). Cues are ~9-word chunks, allocated proportional to
word count so they track the audio reasonably without manual timing.

    python docs/submission/video_assets/make_srt.py --persona ceo

Import the resulting .srt into CapCut/Premiere/DaVinci for the hero segment, or
just use it as a starting point and let CapCut auto-caption refine.
"""
from __future__ import annotations
import argparse
import json
import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
BRIEFINGS = ROOT / "web" / "public" / "briefings"
AUDIO = ROOT / "web" / "public" / "audio"
WORDS_PER_CUE = 9


def audio_duration(mp3: Path, fallback: float) -> float:
    try:
        out = subprocess.run(
            ["ffprobe", "-v", "error", "-show_entries", "format=duration",
             "-of", "csv=p=0", str(mp3)],
            capture_output=True, text=True, check=True,
        )
        return float(out.stdout.strip())
    except Exception:
        return fallback


def ts(seconds: float) -> str:
    ms = int(round(seconds * 1000))
    h, ms = divmod(ms, 3_600_000)
    m, ms = divmod(ms, 60_000)
    s, ms = divmod(ms, 1000)
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


def chunk(words: list[str], n: int) -> list[str]:
    return [" ".join(words[i:i + n]) for i in range(0, len(words), n)]


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--persona", default="ceo")
    args = ap.parse_args()
    slug = args.persona.lower()

    d = json.loads((BRIEFINGS / f"{slug}-latest.json").read_text())
    script = re.sub(r"\s+", " ", d["script_text"]).strip()
    mp3 = next(AUDIO.glob(f"*{slug}*.mp3"), None)
    total = audio_duration(mp3, float(d.get("duration_sec", 120))) if mp3 else float(d.get("duration_sec", 120))

    words = script.split()
    cues = chunk(words, WORDS_PER_CUE)
    per_word = total / max(1, len(words))

    lines, t = [], 0.0
    for i, cue in enumerate(cues, 1):
        dur = len(cue.split()) * per_word
        start, end = t, min(total, t + dur)
        lines += [str(i), f"{ts(start)} --> {ts(end)}", cue, ""]
        t = end

    out = Path(__file__).parent / f"captions_{slug}.srt"
    out.write_text("\n".join(lines))
    print(f"Wrote {len(cues)} cues over {total:.1f}s -> {out}")


if __name__ == "__main__":
    main()
