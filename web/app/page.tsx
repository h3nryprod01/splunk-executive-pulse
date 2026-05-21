"use client";
import { useEffect, useState } from "react";
import { BRIEFINGS } from "@/lib/mock-data";
import type { Briefing, Persona } from "@/lib/types";
import BriefingHeader from "@/components/BriefingHeader";
import AudioPlayer from "@/components/AudioPlayer";
import StoryCard from "@/components/StoryCard";
import DecisionCard from "@/components/DecisionCard";
import PersonaSwitch from "@/components/PersonaSwitch";
import DrillDown from "@/components/DrillDown";

export default function Home() {
  const [persona, setPersona] = useState<Persona>("CEO");
  const [briefing, setBriefing] = useState<Briefing>(BRIEFINGS["CEO"]);

  // Prefer live briefings computed by the Python pipeline; fall back to mock.
  useEffect(() => {
    let active = true;
    fetch(`/api/briefing?persona=${persona}`)
      .then((r) => (r.ok ? r.json() : Promise.reject()))
      .then((d: Briefing) => active && setBriefing(d))
      .catch(() => active && setBriefing(BRIEFINGS[persona]));
    return () => {
      active = false;
    };
  }, [persona]);

  return (
    <main className="max-w-5xl mx-auto p-6 md:p-12 space-y-6">

      <div className="text-center mb-4">
        <div className="inline-flex items-center gap-2 text-xs text-dim font-mono uppercase tracking-widest">
          <span className="w-2 h-2 rounded-full bg-splunk animate-pulse" />
          Delivered at 7:55 AM · 3-min brief
        </div>
      </div>

      <PersonaSwitch current={persona} onChange={setPersona} />

      <BriefingHeader b={briefing} />

      <AudioPlayer src={briefing.audio_url} durationSec={briefing.duration_sec} />

      <section className="space-y-4">
        <h2 className="text-sm text-muted uppercase tracking-widest font-mono">
          📰 Today's Stories
        </h2>
        {briefing.stories.map((s, i) => (
          <StoryCard key={s.cluster_id} story={s} index={i} />
        ))}
      </section>

      {briefing.decisions.length > 0 && (
        <section className="space-y-4">
          <h2 className="text-sm text-muted uppercase tracking-widest font-mono">
            ⚡ Decisions Required
          </h2>
          {briefing.decisions.map((d) => (
            <DecisionCard key={d.decision_id} decision={d} />
          ))}
        </section>
      )}

      <DrillDown />

      {briefing.good_news && (
        <section>
          <div className="bg-splunk/10 border border-splunk/40 rounded-2xl p-6">
            <div className="flex items-center gap-3 mb-2">
              <span className="text-2xl">🎉</span>
              <div className="text-sm text-splunk font-mono uppercase tracking-widest">
                Good News
              </div>
            </div>
            <h3 className="text-lg font-semibold mb-2">{briefing.good_news.headline}</h3>
            <p className="text-dim">{briefing.good_news.summary}</p>
          </div>
        </section>
      )}

      <footer className="text-center text-xs text-muted font-mono py-8 border-t border-border mt-12">
        Splunk Executive Pulse · From data to decisions, in 3 minutes ·{" "}
        <a href="https://github.com/your-team/splunk-executive-pulse" className="text-splunk hover:underline">
          GitHub
        </a>
      </footer>
    </main>
  );
}
