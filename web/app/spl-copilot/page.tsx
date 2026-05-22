"use client";
import { useEffect, useState } from "react";
import {
  FALLBACK_SCENARIOS,
  type CopilotScenario,
  type ScenariosPayload,
} from "@/lib/spl-copilot";
import CritiqueTrace from "@/components/CritiqueTrace";
import ResultsTable from "@/components/ResultsTable";

export default function SplCopilotPage() {
  const [scenarios, setScenarios] = useState<CopilotScenario[]>(
    FALLBACK_SCENARIOS.scenarios
  );
  const [intent, setIntent] = useState<string>(
    FALLBACK_SCENARIOS.scenarios[0].intent
  );
  const [active, setActive] = useState<CopilotScenario>(
    FALLBACK_SCENARIOS.scenarios[0]
  );

  // Prefer scenarios computed by the Python pipeline; fall back to mock.
  useEffect(() => {
    let alive = true;
    fetch("/api/spl-copilot")
      .then((r) => (r.ok ? r.json() : Promise.reject()))
      .then((d: ScenariosPayload) => {
        if (!alive || !d.scenarios?.length) return;
        setScenarios(d.scenarios);
        setIntent(d.scenarios[0].intent);
        setActive(d.scenarios[0]);
      })
      .catch(() => {
        /* keep fallback */
      });
    return () => {
      alive = false;
    };
  }, []);

  const run = () => {
    const found = scenarios.find((s) => s.intent === intent);
    if (found) setActive(found);
  };

  return (
    <main className="max-w-6xl mx-auto p-6 md:p-12 space-y-6">
      <header className="text-center mb-2">
        <div className="inline-flex items-center gap-2 text-xs text-dim font-mono uppercase tracking-widest">
          <span className="w-2 h-2 rounded-full bg-splunk animate-pulse" />
          SPL Copilot · Cursor for Splunk
        </div>
        <h1 className="text-2xl md:text-3xl font-bold mt-3">
          Natural language to correct, runnable SPL
        </h1>
        <p className="text-dim mt-2 max-w-2xl mx-auto">
          A DevEx agent that drafts SPL, runs a self-critique loop to catch bad
          fields, and explains the query pipe by pipe.
        </p>
      </header>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Left: NL input + scenario picker */}
        <section className="bg-card border border-border rounded-2xl p-5 space-y-4">
          <h2 className="text-sm text-muted uppercase tracking-widest font-mono">
            Ask in plain English
          </h2>

          <label className="block text-xs text-dim font-mono uppercase tracking-widest">
            Scenario
          </label>
          <select
            value={intent}
            onChange={(e) => setIntent(e.target.value)}
            className="w-full bg-elevated border border-border rounded-lg px-3 py-2 text-sm text-moat font-mono focus:outline-none focus:border-splunk"
          >
            {scenarios.map((s) => (
              <option key={s.intent} value={s.intent}>
                {s.intent}
              </option>
            ))}
          </select>

          <textarea
            value={intent}
            onChange={(e) => setIntent(e.target.value)}
            rows={3}
            className="w-full bg-bg border border-border rounded-lg px-3 py-2 text-sm text-moat font-mono focus:outline-none focus:border-splunk resize-none"
          />

          <button
            onClick={run}
            className="w-full bg-splunk hover:bg-splunk-dark transition-colors text-bg font-semibold rounded-lg px-4 py-2 text-sm uppercase tracking-widest"
          >
            Run
          </button>

          <div className="pt-2">
            <h3 className="text-sm text-muted uppercase tracking-widest font-mono mb-2">
              Self-critique trace
            </h3>
            <CritiqueTrace steps={active.steps} />
          </div>
        </section>

        {/* Right: SPL + results + explanation */}
        <section className="space-y-4">
          <div className="bg-card border border-border rounded-2xl p-5 space-y-3">
            <div className="flex items-center justify-between">
              <h2 className="text-sm text-muted uppercase tracking-widest font-mono">
                Generated SPL
              </h2>
              <span className="text-[10px] text-dim font-mono uppercase tracking-widest">
                source: {active.spl_source}
              </span>
            </div>
            <pre className="bg-bg border border-splunk/30 rounded-lg p-3 overflow-x-auto">
              <code className="text-sm text-green-200 font-mono whitespace-pre-wrap break-all">
                {active.final_spl}
              </code>
            </pre>
          </div>

          <div className="bg-card border border-border rounded-2xl p-5 space-y-3">
            <h2 className="text-sm text-muted uppercase tracking-widest font-mono">
              Results · {active.row_count} rows
            </h2>
            <ResultsTable rows={active.rows} />
          </div>

          <div className="bg-card border border-border rounded-2xl p-5 space-y-2">
            <h2 className="text-sm text-muted uppercase tracking-widest font-mono">
              Explanation
            </h2>
            <p className="text-dim text-sm whitespace-pre-wrap leading-relaxed">
              {active.explanation}
            </p>
          </div>
        </section>
      </div>

      <footer className="text-center text-xs text-muted font-mono py-8 border-t border-border mt-8">
        SPL Copilot · NL to SPL with a self-critique loop · runs keyless from
        exported scenarios
      </footer>
    </main>
  );
}
