import type { Briefing, Persona } from "./types";

export const BRIEFINGS: Record<Persona, Briefing> = {
  CEO: {
    persona: "CEO",
    briefing_date: "Tuesday, May 21, 2026",
    audio_url: "/pulse-sample.mp3",
    duration_sec: 178,
    word_count: 412,
    total_exposure_usd: 304992,
    uptime_pct: 99.94,
    revenue_usd: 2_300_000,
    headline_quote:
      "Overall a positive night. Revenue hit $2.3M, 4% above forecast — but one story needs your attention.",
    stories: [
      {
        cluster_id: "cl_payment",
        theme: "revenue_incident",
        headline: "Payment system failed for 12 minutes overnight",
        summary:
          "At 2:47 AM our payment gateway failed for 12 minutes. We estimate ~$47K in direct revenue loss; 1,247 customers affected, including 34 enterprise accounts. Root cause: a deploy that bypassed staging. Engineering reviewing today.",
        exposure_usd: 304992,
        priority_score: 87,
        affected_customers: 1247,
        duration_min: 12,
        citations: [
          {
            claim_text: "$46,992 direct revenue loss",
            methodology: "$3,916/min × 12 min × 100% failure",
            confidence: 0.85,
            splunk_dashboard_url: "https://splunk.demo/payment-outage",
          },
          {
            claim_text: "1,247 customers affected",
            methodology: "transaction log count, status=failed",
            confidence: 0.92,
          },
          {
            claim_text: "$18,000 SLA credit liability",
            methodology: "12 contracts × avg credit",
            confidence: 0.95,
          },
          {
            claim_text: "$240,000 indirect churn exposure",
            methodology: "34 ent × 5% churn risk × $141K ACV × 1.2x history",
            confidence: 0.65,
          },
        ],
        drill_down_url: "https://splunk.demo/payment-outage",
      },
      {
        cluster_id: "cl_attack",
        theme: "security_threat",
        headline: "Third credential stuffing attack this month — all blocked",
        summary:
          "Overnight WAF blocked 340K malicious login attempts from APAC. No accounts compromised. Attack frequency rising 40% MoM. CISO is asking for $240K to roll out MFA for tier-2 users.",
        exposure_usd: 0,
        priority_score: 72,
        citations: [
          {
            claim_text: "340,000 attempts blocked",
            methodology: "WAF block count, sourcetype=auth-svc",
            confidence: 0.98,
          },
          {
            claim_text: "3rd attack in 30 days",
            methodology: "incidents_history count where category=security",
            confidence: 0.95,
          },
        ],
        drill_down_url: "https://splunk.demo/auth-attack",
      },
      {
        cluster_id: "cl_checkout",
        theme: "performance_degradation",
        headline: "Checkout speed degraded 7 days running",
        summary:
          "p99 checkout latency drifted from 380ms to 612ms over the past week. Estimated 2.3% conversion drop — roughly $180K/month if unaddressed. Engineering has a fix in flight by end of week.",
        exposure_usd: 180000,
        priority_score: 68,
        citations: [
          {
            claim_text: "2.3% conversion drop",
            methodology: "A/B vs baseline, week-over-week",
            confidence: 0.7,
          },
          {
            claim_text: "$180,000/month exposure",
            methodology: "traffic × conversion drop × AOV",
            confidence: 0.6,
          },
        ],
        drill_down_url: "https://splunk.demo/checkout-perf",
      },
    ],
    decisions: [
      {
        decision_id: "dec_mfa",
        title: "Approve MFA rollout for tier-2 users",
        context: "3rd credential stuffing attack this month; trend worsening 40% MoM.",
        options: [
          { label: "Approve", cost_usd: 240000, benefit: "Eliminates attack vector" },
          { label: "Defer 30 days", risk: "Attack frequency likely continues to rise" },
          { label: "Discuss in exec meeting" },
        ],
        cost_usd: 240000,
        deadline: "2026-05-28",
        owner: "CISO",
      },
    ],
    good_news: {
      headline: "Black Friday capacity test passed at 3x peak",
      summary: "All services held under 3x peak load overnight; we're ready for the holiday season.",
    },
  },

  CFO: {
    persona: "CFO",
    briefing_date: "Tuesday, May 21, 2026",
    audio_url: "/pulse-sample.mp3",
    duration_sec: 175,
    word_count: 398,
    total_exposure_usd: 379992,
    uptime_pct: 99.94,
    revenue_usd: 2_300_000,
    headline_quote:
      "Three financial items need your attention today: a payment incident, a budget overage, and an MFA investment ask.",
    stories: [
      {
        cluster_id: "cl_payment_cfo",
        theme: "revenue_incident",
        headline: "Payment outage cost ~$305K total exposure",
        summary:
          "$47K direct loss + $18K SLA credits + $240K indirect churn exposure across 34 enterprise accounts. Total exposure ~$305K. Recoverable through CSM outreach.",
        exposure_usd: 304992,
        priority_score: 87,
        citations: [],
        drill_down_url: "#",
      },
      {
        cluster_id: "cl_cost",
        theme: "cost_overrun",
        headline: "Q2 infrastructure spend tracking +18% vs budget",
        summary:
          "Driven by ad-hoc GPU jobs from the data science team. Projected overage: $75K this quarter.",
        exposure_usd: 75000,
        priority_score: 78,
        citations: [],
        drill_down_url: "#",
      },
    ],
    decisions: [
      {
        decision_id: "dec_budget",
        title: "Approve $75K infra budget overage",
        context: "Q2 spend +18% vs plan, driven by GPU on-demand usage.",
        options: [
          { label: "Approve overage", cost_usd: 75000 },
          { label: "Throttle workloads", risk: "Delays roadmap ~2 weeks" },
        ],
        cost_usd: 75000,
        deadline: "2026-05-26",
        owner: "CFO",
      },
    ],
  },

  CISO: {
    persona: "CISO",
    briefing_date: "Tuesday, May 21, 2026",
    audio_url: "/pulse-sample.mp3",
    duration_sec: 172,
    word_count: 405,
    total_exposure_usd: 0,
    uptime_pct: 99.94,
    revenue_usd: 2_300_000,
    headline_quote: "We blocked 340K malicious login attempts overnight — but the trend is up 40% month-over-month.",
    stories: [
      {
        cluster_id: "cl_attack_ciso",
        theme: "security_threat",
        headline: "Third credential stuffing attack this month",
        summary: "340K attempts blocked from 12K APAC IPs across 89 ASNs. Zero compromises. Trend up 40% MoM.",
        exposure_usd: 0,
        priority_score: 90,
        citations: [],
        drill_down_url: "#",
      },
    ],
    decisions: [
      {
        decision_id: "dec_mfa_ciso",
        title: "MFA rollout for tier-2 users — your ask",
        context: "Recommended response to rising attack frequency.",
        options: [
          { label: "Submit for CFO approval", cost_usd: 240000 },
          { label: "Pilot first" },
        ],
        cost_usd: 240000,
        deadline: "2026-05-28",
        owner: "CISO",
      },
    ],
  },

  CTO: {
    persona: "CTO",
    briefing_date: "Tuesday, May 21, 2026",
    audio_url: "/pulse-sample.mp3",
    duration_sec: 176,
    word_count: 415,
    total_exposure_usd: 304992,
    uptime_pct: 99.94,
    revenue_usd: 2_300_000,
    headline_quote: "One incident from a deploy that bypassed staging, one weeklong perf regression, and a clean 3x load test.",
    stories: [
      {
        cluster_id: "cl_deploy",
        theme: "deploy_incident",
        headline: "Deploy v2.3.1 caused 12-min payment outage",
        summary: "OOM in payment service after deploy at 17:00 yesterday; rollback gate was skipped. Process review today.",
        exposure_usd: 304992,
        priority_score: 87,
        citations: [],
        drill_down_url: "#",
      },
    ],
    decisions: [
      {
        decision_id: "dec_checkout",
        title: "Authorize emergency checkout perf fix",
        context: "7-day p99 regression now impacting conversion.",
        options: [{ label: "Approve sprint reprioritization" }, { label: "Wait for next sprint", risk: "$180K/month exposure continues" }],
        deadline: "2026-05-24",
        owner: "CTO",
      },
    ],
    good_news: {
      headline: "3x peak load test passed cleanly",
      summary: "Black Friday capacity readiness confirmed.",
    },
  },

  COO: {
    persona: "COO",
    briefing_date: "Tuesday, May 21, 2026",
    audio_url: "/pulse-sample.mp3",
    duration_sec: 174,
    word_count: 401,
    total_exposure_usd: 304992,
    uptime_pct: 99.94,
    revenue_usd: 2_300_000,
    headline_quote: "12 SLA breaches overnight; checkout experience degrading for a 7th consecutive day.",
    stories: [
      {
        cluster_id: "cl_sla",
        theme: "revenue_incident",
        headline: "12 SLA contracts breached overnight",
        summary: "Payment outage triggered breach clauses on 12 enterprise contracts. Estimated $18K credit liability. CSM outreach in progress.",
        exposure_usd: 18000,
        priority_score: 82,
        citations: [],
        drill_down_url: "#",
      },
    ],
    decisions: [],
  },
};
