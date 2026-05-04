export type Market = "A-share" | "US" | "HK";
export type ReportPhase = "0" | "1" | "2" | "3" | "4" | "5" | "6" | "7" | "8" | "9" | "synthesis";
export type SourceQuality = "A" | "B" | "C" | "D" | "E";

export interface Stock {
  id: string;
  ticker: string;
  name: string;
  market: Market;
  sector?: string;
  industry?: string;
  created_at: string;
}

export interface Portfolio {
  id: string;
  name: string;
  description?: string;
  holding_count?: number;
  created_at: string;
}

export interface Holding {
  id: string;
  portfolio_id: string;
  stock_id: string;
  ticker: string;
  cost_basis: number;
  position_percent: number;
  entry_date?: string;
  notes?: string;
  stock?: Stock;
}

export interface ResearchReport {
  id: string;
  stock_id: string;
  phase: ReportPhase;
  title: string;
  content: string;
  signal_rating?: string;
  confidence?: string;
  intensity?: number;
  core_thesis?: string;
  stock?: Stock;
  created_at: string;
}

export interface Citation {
  id: string;
  research_report_id: string;
  author_org: string;
  publication_date?: string;
  source_title: string;
  url?: string;
  quality_rating: SourceQuality;
  claim_text?: string;
}

export interface MorningReport {
  id: string;
  report_date: string;
  html_content: string;
  headline?: string;
  key_themes?: string[];
  macro_signals?: MacroSignal[];
}

export interface MacroSignal {
  signal_name: string;
  current_status: string;
  mechanism: string;
  impact_direction: "positive" | "negative" | "neutral";
}

export interface User {
  id: string;
  username: string;
  email?: string;
}
