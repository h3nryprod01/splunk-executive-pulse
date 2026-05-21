"use client";
import clsx from "clsx";
import type { Persona } from "@/lib/types";

const ICONS: Record<Persona, string> = {
  CEO: "👔", CFO: "💰", CISO: "🛡️", CTO: "⚙️", COO: "📊",
};

export default function PersonaSwitch({
  current, onChange,
}: { current: Persona; onChange: (p: Persona) => void }) {
  const personas: Persona[] = ["CEO", "CFO", "CISO", "CTO", "COO"];
  return (
    <div className="flex gap-2 bg-card border border-border rounded-2xl p-2">
      {personas.map((p) => (
        <button
          key={p}
          onClick={() => onChange(p)}
          className={clsx(
            "flex-1 px-4 py-3 rounded-xl text-sm font-semibold transition-all",
            current === p
              ? "bg-splunk text-bg shadow-lg shadow-splunk/20"
              : "text-dim hover:bg-elevated hover:text-white"
          )}
        >
          <div className="text-xl mb-1">{ICONS[p]}</div>
          <div>{p}</div>
        </button>
      ))}
    </div>
  );
}
