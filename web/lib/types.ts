export type Persona = "CEO" | "CFO" | "CISO" | "CTO" | "COO";

export interface Citation {
  claim_text: string;
  methodology: string;
  confidence: number;
  splunk_query?: string;
  splunk_dashboard_url?: string;
}

export interface Story {
  cluster_id: string;
  theme: string;
  headline: string;
  summary: string;
  exposure_usd: number;
  priority_score: number;
  affected_customers?: number;
  duration_min?: number;
  citations: Citation[];
  drill_down_url: string;
}

export interface Decision {
  decision_id: string;
  title: string;
  context: string;
  options: Array<{ label: string; cost_usd?: number; risk?: string; benefit?: string }>;
  cost_usd?: number;
  deadline: string;
  owner: string;
}

export interface Briefing {
  persona: Persona;
  briefing_date: string;
  audio_url: string;
  duration_sec: number;
  word_count: number;
  total_exposure_usd: number;
  uptime_pct: number;
  revenue_usd: number;
  headline_quote: string;
  stories: Story[];
  decisions: Decision[];
  good_news?: { headline: string; summary: string };
}
