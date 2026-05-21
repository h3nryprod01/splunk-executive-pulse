"use client";
import { useState } from "react";

interface SplResult {
  spl: string;
  explanation: string;
  source: string;
  confidence: number;
}

const SUGGESTIONS = [
  "Show me last night's payment errors",
  "Was there a credential stuffing attack?",
  "Why is checkout latency degrading?",
  "Are we over budget on infrastructure cost?",
];

export default function DrillDown() {
  const [q, setQ] = useState("");
  const [result, setResult] = useState<SplResult | null>(null);
  const [loading, setLoading] = useState(false);

  async function ask(question: string) {
    const query = question.trim();
    if (!query) return;
    setQ(query);
    setLoading(true);
    try {
      const r = await fetch(`/api/drilldown?q=${encodeURIComponent(query)}`);
      setResult(r.ok ? await r.json() : null);
    } catch {
      setResult(null);
    } finally {
      setLoading(false);
    }
  }

  return (
    <section className="space-y-4">
      <h2 className="text-sm text-muted uppercase tracking-widest font-mono">
        🔎 Ask about last night
      </h2>
      <div className="bg-card border border-border rounded-2xl p-5 space-y-4">
        <form
          onSubmit={(e) => {
            e.preventDefault();
            ask(q);
          }}
          className="flex gap-2"
        >
          <input
            value={q}
            onChange={(e) => setQ(e.target.value)}
            placeholder="e.g. show me last night's payment errors"
            className="flex-1 bg-bg border border-border rounded-xl px-4 py-3 text-sm
                       text-white placeholder:text-muted focus:outline-none focus:border-splunk"
          />
          <button
            type="submit"
            className="px-5 py-3 rounded-xl text-sm font-semibold bg-splunk text-bg
                       hover:opacity-90 transition disabled:opacity-50"
            disabled={loading}
          >
            {loading ? "…" : "Ask"}
          </button>
        </form>

        <div className="flex flex-wrap gap-2">
          {SUGGESTIONS.map((s) => (
            <button
              key={s}
              onClick={() => ask(s)}
              className="text-xs text-dim border border-border rounded-lg px-3 py-1.5
                         hover:border-splunk hover:text-white transition"
            >
              {s}
            </button>
          ))}
        </div>

        {result && (
          <div className="space-y-2 pt-2 border-t border-border">
            <div className="flex items-center gap-2 text-xs font-mono text-muted">
              <span className="text-splunk uppercase tracking-widest">Splunk AI Assistant for SPL</span>
              <span>·</span>
              <span>{result.source}</span>
              <span>·</span>
              <span>conf {result.confidence.toFixed(1)}</span>
            </div>
            <pre className="bg-bg border border-border rounded-xl p-4 text-sm font-mono
                            text-splunk overflow-x-auto whitespace-pre-wrap">{result.spl}</pre>
            <p className="text-dim text-sm">→ {result.explanation}</p>
          </div>
        )}
      </div>
    </section>
  );
}
