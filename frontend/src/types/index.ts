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

// ── Broker Sync ───────────────────────────────────────────────────────────────

export type Broker = "etoro" | "tr";

export interface BrokerSyncLog {
  id: string;
  broker: Broker;
  status: "running" | "success" | "failed" | "partial";
  positions_read: number;
  positions_synced: number;
  portfolio_id: string | null;
  error_msg: string | null;
  started_at: string;
  finished_at: string | null;
}

export interface BrokerPortfolioMapping {
  id: string;
  broker: Broker;
  portfolio_id: string;
  portfolio_name: string | null;
  created_at: string;
}

export interface BrokerSyncStatus {
  etoro_last_sync: BrokerSyncLog | null;
  tr_last_sync: BrokerSyncLog | null;
  etoro_mapping: BrokerPortfolioMapping | null;
  tr_mapping: BrokerPortfolioMapping | null;
}

// ── Simulation ────────────────────────────────────────────────────────────────

export type TradeAction = "BUY_LONG" | "SELL_LONG" | "SELL_SHORT" | "BUY_SHORT";
export type PositionDirection = "LONG" | "SHORT";
export type TriggerSource = "MANUAL" | "AI_SIGNAL" | "RESEARCH";

export interface SimulatedPortfolio {
  id: string;
  user_id: string;
  name: string;
  initial_capital: number;
  cash_balance: number;
  currency: string;
  max_leverage: number;
  maintenance_margin_rate: number;
  is_active: boolean;
  created_at: string;
  updated_at: string;
  // computed by backend
  total_margin_used: number;
  unrealized_pnl: number;
  equity: number;
  margin_level: number | null;
  margin_call: boolean;
  total_return_pct: number;
}

export interface SimulatedPosition {
  id: string;
  portfolio_id: string;
  ticker: string;
  direction: PositionDirection;
  quantity: number;
  avg_entry_price: number;
  leverage_ratio: number;
  margin_used: number;
  notional_value: number;
  stop_loss: number | null;
  take_profit: number | null;
  opened_at: string;
  // computed
  current_price: number | null;
  unrealized_pnl: number | null;
  unrealized_pnl_pct: number | null;
}

export interface SimulatedTrade {
  id: string;
  portfolio_id: string;
  ticker: string;
  action: TradeAction;
  quantity: number;
  price: number;
  leverage_ratio: number;
  margin_used: number;
  notional_value: number;
  rationale: string;
  triggered_by: TriggerSource;
  signal_id: string | null;
  stop_loss: number | null;
  take_profit: number | null;
  realized_pnl: number | null;
  fees: number;
  executed_at: string;
}

export interface TradeReview {
  id: string;
  portfolio_id: string;
  trade_id: string | null;
  ticker: string;
  entry_rationale: string;
  actual_outcome: string;
  pnl_realized: number;
  lessons_learned: string | null;
  rating: number;
  reviewed_at: string;
}

export interface HoldingSnapshot {
  ticker: string;
  cost_basis: number;
  current_price: number | null;
  position_percent: number;
  unrealized_pnl: number | null;
  unrealized_pnl_pct: number | null;
}

export interface PortfolioComparison {
  comparison_date: string;
  sim_name: string;
  sim_equity: number;
  sim_initial_capital: number;
  sim_return_pct: number;
  sim_unrealized_pnl: number;
  sim_positions: SimulatedPosition[];
  real_portfolio_name: string | null;
  real_holdings: HoldingSnapshot[];
  real_return_pct: number | null;
  alpha_pct: number | null;
}
