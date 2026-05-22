// Types and mock fallback for the SPL Copilot demo. Mirrors the serialized
// CopilotResult shape from spl_copilot/models.py so the page renders even when
// web/public/spl_copilot/scenarios.json is missing.

export interface CritiqueStep {
  reason: string;
  before_spl: string;
  after_spl: string;
}

export interface CopilotScenario {
  intent: string;
  final_spl: string;
  rows: Record<string, unknown>[];
  steps: CritiqueStep[];
  explanation: string;
  spl_source: string;
  row_count: number;
}

export interface ScenariosPayload {
  scenarios: CopilotScenario[];
}

// Built-in fallback so the demo always renders. Kept small but representative:
// one scenario with a self-critique fix, one valid-on-first-try.
export const FALLBACK_SCENARIOS: ScenariosPayload = {
  scenarios: [
    {
      intent: "show me payment errors",
      final_spl:
        "search index=prod sourcetype=payment-svc http_status>=500 | timechart span=1m count",
      rows: [
        { _time: "06:01", http_status: 500, response_ms: 1200, customer_id: "C-1001" },
        { _time: "06:02", http_status: 503, response_ms: 1500, customer_id: "C-1002" },
        { _time: "06:03", http_status: 500, response_ms: 1100, customer_id: "C-1003" },
      ],
      steps: [
        {
          reason: "Field(s) not in schema; remapped `status` -> `http_status`",
          before_spl:
            "search index=prod sourcetype=payment-svc status>=500 | timechart span=1m count",
          after_spl:
            "search index=prod sourcetype=payment-svc http_status>=500 | timechart span=1m count",
        },
      ],
      explanation:
        "1. Filter events matching: index=prod sourcetype=payment-svc http_status>=500\n2. Bucket the matching events over time (timechart span=1m count).",
      spl_source: "offline-fallback",
      row_count: 3,
    },
    {
      intent: "blocked logins by source ip",
      final_spl:
        "search index=prod sourcetype=auth action=blocked | stats count by src_ip",
      rows: [
        { src_ip: "10.0.0.4", count: 42 },
        { src_ip: "10.0.0.9", count: 17 },
      ],
      steps: [],
      explanation:
        "1. Filter events matching: index=prod sourcetype=auth action=blocked\n2. Aggregate with stats count by src_ip.",
      spl_source: "offline-fallback",
      row_count: 7,
    },
  ],
};
