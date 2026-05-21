# agents/audio_producer/__main__.py
"""
Generate a real sample audio file from a hardcoded sample script.

Usage:
    export ELEVENLABS_API_KEY=...
    python -m agents.audio_producer

    # then play:
    open demo/sample_outputs/pulse-2026-05-21-ceo-norm.mp3
"""
import asyncio
import os
import sys
from datetime import datetime, timezone
from agents.audio_producer.agent import AudioProducerAgent
from agents.narrative_writer.models import NarrativeScript, Citation


SAMPLE_SCRIPT = """\
Good morning. This is your Splunk Executive Pulse for Tuesday, May twenty-first.

Overall, a positive night. Online revenue hit two point three million dollars overnight, four percent above forecast. But one story needs your attention.

At 2:47 AM, our payment system failed for twelve minutes. We estimate about forty-seven thousand dollars in lost revenue. Twelve hundred customers were affected, including thirty-four enterprise accounts. The root cause was a deployment yesterday afternoon that bypassed our release process. Engineering is reviewing this today.

Second story: overnight, we blocked our third automated login attack this month. No accounts were compromised. The trend is rising sharply, and your security chief is asking for two hundred forty thousand dollars to roll out multi-factor authentication. Decision needed by next Wednesday.

Third story: checkout speed has been degrading for seven days. This is costing us roughly two percent in conversions, about a hundred and eighty thousand dollars a month if unaddressed. Engineering has a fix in flight, expected by end of week.

One positive note. Our load test simulating three times Black Friday peak passed cleanly overnight. We are ready for the holiday season.

Full details are in your dashboard. Have a productive day."""


async def main():
    if not os.getenv("ELEVENLABS_API_KEY"):
        print("ERROR: set ELEVENLABS_API_KEY first.")
        print("Get a free key at https://elevenlabs.io")
        sys.exit(1)

    from agents.narrative_writer.ssml_converter import to_ssml, estimate_duration_sec

    script = NarrativeScript(
        script_text=SAMPLE_SCRIPT,
        ssml_version=to_ssml(SAMPLE_SCRIPT),
        persona="CEO",
        briefing_date=datetime(2026, 5, 21, tzinfo=timezone.utc),
        estimated_duration_sec=estimate_duration_sec(SAMPLE_SCRIPT),
        word_count=len(SAMPLE_SCRIPT.split()),
        citations=[],
        drill_down_links=[],
        llm_model_used="manual-sample",
        llm_passes=1,
        self_critique_score=1.0,
    )

    producer = AudioProducerAgent()
    print("🎙️  Generating audio with ElevenLabs...")
    out = await producer.produce(script)

    print(f"\n✅ Done!")
    print(f"   File:     {out.local_path}")
    print(f"   Duration: {out.duration_sec}s")
    print(f"   Size:     {out.file_size_bytes / 1024:.1f} KB")
    print(f"   Voice:    {out.voice_preset}")
    print(f"   Waveform: {out.waveform_url}")
    print(f"\n🔊 Play: open '{out.local_path}'")


if __name__ == "__main__":
    asyncio.run(main())
