# agents/narrative_writer/ssml_converter.py
"""
Convert plain script → SSML with prosody hints for executive-grade audio.
"""
from __future__ import annotations
import re
import html


def to_ssml(script: str, voice_speed: float = 0.97) -> str:
    """
    Wrap script in SSML with:
      - calmer global rate (Bloomberg pace = ~145 wpm vs default 160)
      - emphasis on section openers
      - pauses between paragraphs
      - phonetic hints for "Splunk"
    """
    # Escape HTML special chars
    text = html.escape(script.strip())

    # Add 500ms pause between paragraphs
    text = re.sub(r"\n\s*\n", '\n<break time="600ms"/>\n', text)

    # Emphasize "Good morning" intro
    text = re.sub(
        r"(Good morning\.)",
        r'<emphasis level="moderate">\1</emphasis>',
        text, count=1,
    )

    # Short pauses after section transitions
    transitions = [
        "But one story needs your attention",
        "Second story",
        "Third story",
        "One positive note",
        "decisions need your attention",
        "Full details are in your dashboard",
    ]
    for t in transitions:
        text = text.replace(t, f'<break time="300ms"/>{t}')

    # Phonetic hint for product name
    text = text.replace("Splunk", '<phoneme alphabet="ipa" ph="splʌŋk">Splunk</phoneme>')

    rate_pct = int(voice_speed * 100)
    return (
        f'<speak>'
        f'<prosody rate="{rate_pct}%" pitch="-2st">'
        f'{text}'
        f'</prosody>'
        f'</speak>'
    )


def estimate_duration_sec(script: str, wpm: int = 145) -> int:
    """Bloomberg pace ≈ 145 wpm."""
    words = len(script.split())
    return round(words / wpm * 60)
