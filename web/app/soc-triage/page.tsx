"use client";
import { useEffect, useState } from "react";
import {
  FALLBACK_INCIDENT,
  type IncidentReport,
  type TriageVerdict,
} from "@/lib/soc-triage";

const SEVERITY_STYLE: Record<TriageVerdict["severity"], string> = {
  CRITICAL: "bg-red-500/15 border-red-500/50 text-red-300",
  HIGH: "bg-orange-500/15 border-orange-500/50 text-orange-300",
  MEDIUM: "bg-yellow-500/15 border-yellow-500/50 text-yellow-200",
  LOW: "bg-green-500/15 border-green-500/50 text-green-300",
};

export default function SocTriagePage() {
  const [report, setReport] = useState<IncidentReport>(FALLBACK_INCIDENT);

  // Prefer the report computed by the Python pipeline; fall back to mock.
  useEffect(() => {
    let alive = true;
    fetch("/api/soc-triage")
      .then((r) => (r.ok ? r.json() : Promise.reject()))
      .then((d: IncidentReport) => {
        if (alive && d?.verdict) setReport(d);
      })
      .catch(() => {
        /* keep fallback */
      });
    return () => {
      alive = false;
    };
  }, []);

  const { alert, findings, timeline, verdict, searches_run } = report;

  return (
    <main className="max-w-6xl mx-auto p-6 md:p-12 space-y-6">
      <header className="text-center mb-2">
        <div className="inline-flex items-center gap-2 text-xs text-dim font-mono uppercase tracking-widest">
          <span className="w-2 h-2 rounded-full bg-splunk animate-pulse" />
          SOC Triage Copilot · Autonomous Tier-1 analyst
        </div>
        <h1 className="text-2xl md:text-3xl font-bold mt-3">
          Alert to incident verdict, automatically
        </h1>
        <p className="text-dim mt-2 max-w-2xl mx-auto">
          A security agent that investigates an alert across multiple SPL
          searches, pivoting on what it finds, then issues a triage verdict.
        </p>
      </header>

      {/* Alert + verdict banner */}
      <section
        className={`border rounded-2xl p-5 space-y-2 ${SEVERITY_STYLE[verdict.severity]}`}
      >
        <div className="flex items-center justify-between flex-wrap gap-2">
          <span className="font-mono text-xs uppercase tracking-widest">
            {alert.alert_id} · {searches_run} searches run
          </span>
          <span className="font-mono text-xs uppercase tracking-widest">
            confidence {(verdict.confidence * 100).toFixed(0)}%
          </span>
        </div>
        <h2 className="text-lg font-bold">
          {verdict.severity} — {verdict.classification}
        </h2>
        <p className="text-sm opacity-90">{alert.title}</p>
        <p className="text-sm opacity-80 leading-relaxed">{verdict.rationale}</p>
      </section>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Investigation steps */}
        <section className="bg-card border border-border rounded-2xl p-5 space-y-4">
          <h2 className="text-sm text-muted uppercase tracking-widest font-mono">
            Investigation
          </h2>
          {findings.map((f) => (
            <div key={f.step} className="space-y-1 border-l-2 border-splunk/40 pl-3">
              <div className="text-sm text-moat font-semibold">
                {f.step}. {f.question}
              </div>
              <pre className="bg-bg border border-border rounded-lg p-2 overflow-x-auto">
                <code className="text-xs text-green-200 font-mono whitespace-pre-wrap break-all">
                  {f.spl}
                </code>
              </pre>
              <div className="text-xs text-dim">
                {f.summary} <span className="text-muted">({f.row_count} rows)</span>
              </div>
            </div>
          ))}
        </section>

        {/* Timeline + actions */}
        <section className="space-y-4">
          <div className="bg-card border border-border rounded-2xl p-5 space-y-3">
            <h2 className="text-sm text-muted uppercase tracking-widest font-mono">
              Attack timeline
            </h2>
            <ol className="space-y-2">
              {timeline.map((t, i) => (
                <li key={i} className="flex gap-3 text-xs font-mono">
                  <span className="text-muted w-16 shrink-0">{t.time}</span>
                  <span
                    className={`w-24 shrink-0 ${
                      t.action.includes("allowed") || t.action === "export"
                        ? "text-red-300"
                        : "text-dim"
                    }`}
                  >
                    {t.action}
                  </span>
                  <span className="text-moat">{t.actor}</span>
                  <span className="text-dim">{t.detail}</span>
                </li>
              ))}
            </ol>
          </div>

          <div className="bg-card border border-border rounded-2xl p-5 space-y-2">
            <h2 className="text-sm text-muted uppercase tracking-widest font-mono">
              Recommended containment
            </h2>
            <ul className="space-y-2">
              {verdict.recommended_actions.map((a, i) => (
                <li key={i} className="flex items-start gap-2 text-sm text-moat">
                  <span className="text-splunk mt-0.5">›</span>
                  {a}
                </li>
              ))}
            </ul>
          </div>
        </section>
      </div>

      <footer className="text-center text-xs text-muted font-mono py-8 border-t border-border mt-8">
        SOC Triage Copilot · multi-step pivoting investigation · runs keyless
        from an exported incident report
      </footer>
    </main>
  );
}
