import type { Briefing } from "@/lib/types";

export default function BriefingHeader({ b }: { b: Briefing }) {
  return (
    <div className="bg-elevated rounded-2xl p-8 border border-border">
      <div className="flex items-center justify-between mb-6">
        <div>
          <div className="text-sm text-splunk font-mono uppercase tracking-widest mb-2">
            Splunk Executive Pulse
          </div>
          <h1 className="text-3xl font-bold">{b.briefing_date}</h1>
        </div>
        <div className="text-right text-sm text-dim font-mono">
          Persona: <span className="text-gold font-bold">{b.persona}</span>
        </div>
      </div>

      <p className="text-lg text-white/90 leading-relaxed italic mb-6">
        "{b.headline_quote}"
      </p>

      <div className="grid grid-cols-3 gap-4">
        <Stat label="Revenue" value={`$${(b.revenue_usd / 1e6).toFixed(1)}M`} hint="+4% vs forecast" />
        <Stat label="Uptime" value={`${b.uptime_pct}%`} hint="last 24h" />
        <Stat
          label="Total Exposure"
          value={`$${(b.total_exposure_usd / 1000).toFixed(0)}K`}
          hint="all open issues"
        />
      </div>
    </div>
  );
}

function Stat({ label, value, hint }: { label: string; value: string; hint: string }) {
  return (
    <div className="bg-card rounded-xl p-4 border border-border">
      <div className="text-xs text-muted uppercase tracking-wider font-mono">{label}</div>
      <div className="text-2xl font-bold mt-2">{value}</div>
      <div className="text-xs text-dim mt-1">{hint}</div>
    </div>
  );
}
