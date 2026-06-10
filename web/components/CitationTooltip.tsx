"use client";
import { useState } from "react";
import type { Citation } from "@/lib/types";

export default function CitationTooltip({
  children, citation,
}: {
  children: React.ReactNode;
  citation: Citation;
}) {
  const [open, setOpen] = useState(false);
  const confidencePct = Math.round(citation.confidence * 100);
  const confidenceColor =
    citation.confidence >= 0.8 ? "bg-splunk"
      : citation.confidence >= 0.5 ? "bg-gold"
      : "bg-red-500";

  return (
    <span className="relative inline-block">
      <button
        onClick={() => setOpen(!open)}
        onMouseEnter={() => setOpen(true)}
        onMouseLeave={() => setOpen(false)}
        onFocus={() => setOpen(true)}
        onBlur={() => setOpen(false)}
        onKeyDown={(e) => e.key === "Escape" && setOpen(false)}
        aria-expanded={open}
        aria-label="Show calculation methodology"
        className="text-gold underline decoration-dotted underline-offset-4 cursor-help"
      >
        {children}
      </button>
      {open && (
        <span className="absolute z-50 left-0 top-full mt-2 w-80 bg-elevated border border-border rounded-xl p-4 shadow-2xl text-left">
          <span className="block text-xs text-muted uppercase tracking-wider mb-2">
            How we calculated this
          </span>
          <span className="block text-sm text-white font-mono mb-3">
            {citation.methodology}
          </span>
          <span className="block text-xs text-dim mb-1">Confidence</span>
          <span className="flex items-center gap-2">
            <span className="flex-1 h-1.5 bg-border rounded-full overflow-hidden">
              <span className={`block h-full ${confidenceColor}`} style={{ width: `${confidencePct}%` }} />
            </span>
            <span className="text-xs font-mono text-dim">{confidencePct}%</span>
          </span>
          {citation.splunk_dashboard_url && (
            <a
              href={citation.splunk_dashboard_url}
              className="block mt-3 text-xs text-splunk hover:underline"
              onClick={(e) => e.stopPropagation()}
            >
              → View Splunk dashboard
            </a>
          )}
        </span>
      )}
    </span>
  );
}
