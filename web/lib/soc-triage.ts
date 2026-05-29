// Types and mock fallback for the SOC Triage demo. Mirrors the serialized
// IncidentReport shape from soc_triage/models.py so the page renders even when
// web/public/soc_triage/incident.json is missing.

export interface Alert {
  alert_id: string;
  title: string;
  alert_type: string;
  index: string;
  sourcetype: string;
}

export interface Finding {
  step: number;
  question: string;
  spl: string;
  row_count: number;
  summary: string;
}

export interface TimelineEvent {
  time: string;
  actor: string;
  action: string;
  detail: string;
}

export interface TriageVerdict {
  severity: "CRITICAL" | "HIGH" | "MEDIUM" | "LOW";
  classification: string;
  confidence: number;
  recommended_actions: string[];
  rationale: string;
}

export interface IncidentReport {
  alert: Alert;
  findings: Finding[];
  timeline: TimelineEvent[];
  verdict: TriageVerdict;
  searches_run: number;
  narrative: string;
  narrative_source: string;
}

// Built-in fallback so the demo always renders without an exported report.
export const FALLBACK_INCIDENT: IncidentReport = {
  alert: {
    alert_id: "ALERT-2026-0517",
    title: "Spike in blocked authentication attempts on auth-svc",
    alert_type: "credential_stuffing",
    index: "security",
    sourcetype: "auth-svc",
  },
  findings: [
    {
      step: 1,
      question: "How many blocked auth attempts, and from which source IPs?",
      spl: "search index=security sourcetype=auth-svc result=blocked",
      row_count: 5,
      summary: "5 blocked attempts from 2 IP(s): 5.5.5.5, 5.5.5.6.",
    },
    {
      step: 2,
      question: "Did any login succeed from the attacker IP(s)?",
      spl: "... result=allowed src_ip IN (5.5.5.5, 5.5.5.6)",
      row_count: 1,
      summary:
        "1 SUCCESSFUL login(s): account(s) alice likely compromised.",
    },
    {
      step: 3,
      question: "What did alice do after logging in?",
      spl: 'search index=security sourcetype=api-svc username="alice"',
      row_count: 1,
      summary: "Post-compromise activity by alice: export 1247 customer_records.",
    },
  ],
  timeline: [
    { time: "06:00:11", actor: "5.5.5.5", action: "login blocked", detail: "user=alice asn=AS999" },
    { time: "06:00:14", actor: "5.5.5.5", action: "login blocked", detail: "user=bob asn=AS999" },
    { time: "06:00:31", actor: "5.5.5.5", action: "login blocked", detail: "user=alice asn=AS999" },
    { time: "06:01:05", actor: "5.5.5.5", action: "login allowed", detail: "user=alice asn=AS999" },
    { time: "06:03:40", actor: "alice", action: "export", detail: "customer_records count=1247" },
  ],
  verdict: {
    severity: "CRITICAL",
    classification: "Account takeover via credential stuffing",
    confidence: 0.9,
    recommended_actions: [
      "Disable account(s): alice",
      "Block source IP(s): 5.5.5.5, 5.5.5.6",
      "Force password reset + revoke active sessions",
      "Open data-breach review — 1247 records accessed",
    ],
    rationale:
      "A successful login followed a brute-force burst from the same source IP(s) (5.5.5.5, 5.5.5.6); account(s) alice are presumed compromised with post-compromise data export.",
  },
  searches_run: 4,
  narrative:
    "Alert 'Spike in blocked authentication attempts on auth-svc' was triaged as CRITICAL (Account takeover via credential stuffing, confidence 90%). A successful login followed a brute-force burst from the same source IP(s) (5.5.5.5, 5.5.5.6); account(s) alice are presumed compromised with post-compromise data export. Recommend immediate containment: Disable account(s): alice. Source IP(s) 5.5.5.5, 5.5.5.6 should be blocked at the edge.",
  narrative_source: "offline",
};
