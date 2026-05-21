import type { Decision } from "@/lib/types";

export default function DecisionCard({ decision }: { decision: Decision }) {
  return (
    <div className="bg-moat text-bg rounded-2xl p-6 border-2 border-gold">
      <div className="flex items-start justify-between mb-3">
        <div>
          <div className="text-xs uppercase tracking-wider font-mono opacity-70">
            Decision Required · Owner: {decision.owner}
          </div>
          <h3 className="text-xl font-bold mt-1">{decision.title}</h3>
        </div>
        <div className="text-right">
          {decision.cost_usd && (
            <div className="text-2xl font-extrabold">${(decision.cost_usd / 1000).toFixed(0)}K</div>
          )}
          <div className="text-xs opacity-60 mt-1">by {decision.deadline}</div>
        </div>
      </div>
      <p className="text-bg/80 text-sm mb-4">{decision.context}</p>
      <div className="flex gap-2 flex-wrap">
        {decision.options.map((opt, i) => (
          <button
            key={i}
            className={`px-4 py-2 rounded-lg text-sm font-semibold transition ${
              i === 0
                ? "bg-bg text-moat hover:bg-elevated"
                : "border-2 border-bg/30 hover:bg-bg/10"
            }`}
          >
            {opt.label}
            {opt.cost_usd ? ` · $${(opt.cost_usd / 1000).toFixed(0)}K` : ""}
          </button>
        ))}
      </div>
    </div>
  );
}
