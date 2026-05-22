import type { CritiqueStep } from "@/lib/spl-copilot";

interface CritiqueTraceProps {
  steps: CritiqueStep[];
}

// The hero panel: shows each self-correction the copilot applied, with a
// before -> after SPL diff. Empty steps render a subtle "valid on first try".
export default function CritiqueTrace({ steps }: CritiqueTraceProps) {
  if (steps.length === 0) {
    return (
      <div className="bg-splunk/10 border border-splunk/40 rounded-2xl p-5">
        <div className="flex items-center gap-2 text-sm text-splunk font-mono uppercase tracking-widest">
          <span className="w-2 h-2 rounded-full bg-splunk" />
          Valid on first try
        </div>
        <p className="text-dim text-sm mt-2">
          No corrections needed. The generated SPL passed schema validation and
          returned rows on the first run.
        </p>
      </div>
    );
  }

  return (
    <div className="space-y-3">
      {steps.map((step, i) => (
        <div
          key={i}
          className="bg-card border border-gold/40 rounded-2xl p-5 space-y-3"
        >
          <div className="flex items-center gap-2 text-sm text-gold font-mono uppercase tracking-widest">
            <span className="w-2 h-2 rounded-full bg-gold animate-pulse" />
            Self-critique step {i + 1}
          </div>
          <p className="text-moat text-sm">{step.reason}</p>

          <div className="space-y-2">
            <div className="rounded-lg bg-bg/60 border border-red-500/30 p-3">
              <div className="text-[10px] text-red-400 font-mono uppercase tracking-widest mb-1">
                Before
              </div>
              <code className="text-xs text-red-200 font-mono break-all whitespace-pre-wrap">
                {step.before_spl}
              </code>
            </div>
            <div className="rounded-lg bg-bg/60 border border-splunk/40 p-3">
              <div className="text-[10px] text-splunk font-mono uppercase tracking-widest mb-1">
                After
              </div>
              <code className="text-xs text-green-200 font-mono break-all whitespace-pre-wrap">
                {step.after_spl}
              </code>
            </div>
          </div>
        </div>
      ))}
    </div>
  );
}
