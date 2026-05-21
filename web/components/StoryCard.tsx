import type { Story } from "@/lib/types";
import CitationTooltip from "./CitationTooltip";

const THEME_ICON: Record<string, string> = {
  revenue_incident: "💰",
  security_threat: "🛡️",
  performance_degradation: "📉",
  cost_overrun: "💸",
  deploy_incident: "🚀",
  capacity_risk: "📊",
  compliance_risk: "⚖️",
};

const PRIORITY_BADGE = (p: number) => {
  if (p >= 80) return { label: "CRITICAL", cls: "bg-red-500/20 text-red-400 border-red-500/40" };
  if (p >= 60) return { label: "HIGH", cls: "bg-gold/20 text-gold border-gold/40" };
  return { label: "NOTABLE", cls: "bg-splunk/20 text-splunk border-splunk/40" };
};

export default function StoryCard({ story, index }: { story: Story; index: number }) {
  const badge = PRIORITY_BADGE(story.priority_score);
  return (
    <div className="bg-card border border-border rounded-2xl p-6 hover:border-splunk/50 transition-colors">
      <div className="flex items-start justify-between gap-4 mb-3">
        <div className="flex items-center gap-3">
          <span className="text-3xl">{THEME_ICON[story.theme] || "📌"}</span>
          <div>
            <div className="text-xs text-muted uppercase tracking-wider font-mono">
              Story {index + 1} · {story.theme.replace(/_/g, " ")}
            </div>
            <h3 className="text-xl font-semibold mt-1 leading-tight">
              {story.headline}
            </h3>
          </div>
        </div>
        <span className={`text-xs font-mono font-semibold px-2 py-1 rounded border ${badge.cls}`}>
          {badge.label}
        </span>
      </div>

      <p className="text-dim leading-relaxed mb-4">{story.summary}</p>

      {story.citations.length > 0 && (
        <div className="border-t border-border pt-4 mt-4">
          <div className="text-xs text-muted uppercase tracking-wider mb-3 font-mono">
            Receipts
          </div>
          <div className="flex flex-wrap gap-2">
            {story.citations.map((c, i) => (
              <CitationTooltip key={i} citation={c}>
                {c.claim_text}
              </CitationTooltip>
            ))}
          </div>
        </div>
      )}

      <div className="flex items-center justify-between mt-4 pt-4 border-t border-border">
        <div className="flex items-center gap-4 text-sm text-dim">
          {story.exposure_usd > 0 && (
            <span>
              Exposure: <span className="text-white font-semibold">
                ${story.exposure_usd.toLocaleString()}
              </span>
            </span>
          )}
          {story.affected_customers && (
            <span>{story.affected_customers.toLocaleString()} customers</span>
          )}
          {story.duration_min && <span>{story.duration_min}min duration</span>}
        </div>
        <a href={story.drill_down_url} className="text-sm text-splunk hover:underline">
          View dashboard →
        </a>
      </div>
    </div>
  );
}
