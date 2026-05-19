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
  avg_cost?: number;
  position_percent?: number;
  // Snapshot dimension (populated for snapshot-ingested rows)
  snapshot_id?: string;
  snapshot_date?: string;
  account?: "etoro" | "tr" | "manual";
  shares?: number;
  current_price?: number;
  market_value_usd?: number;
  pnl_total_pct?: number;
  pnl_day_pct?: number;
  verdict?: "buy" | "hold" | "sell";
  entry_date?: string;
  notes?: string;
  stock?: Stock;
}

// ── Snapshot APIs (Phase C) ──

export interface SnapshotListItem {
  id: string;
  report_date: string;
  source: "broker_sync" | "report_upload" | "manual";
  combined_total_usd: number | null;
  combined_cash_usd: number | null;
  cash_ratio_pct: number | null;
  holdings_count: number;
  created_at: string;
}

export interface SnapshotDetail {
  id: string;
  user_id: string;
  report_date: string;
  source: string;
  etoro_total_usd: number | null;
  etoro_cash_usd: number | null;
  etoro_invested_usd: number | null;
  etoro_pnl_day_usd: number | null;
  tr_total_eur: number | null;
  tr_cash_eur: number | null;
  tr_invested_eur: number | null;
  tr_pnl_day_eur: number | null;
  eur_usd_rate: number | null;
  combined_total_usd: number | null;
  combined_cash_usd: number | null;
  cash_ratio_pct: number | null;
  holdings_count: number;
  created_at: string;
}

export interface HoldingSnapshotRow {
  id: string;
  ticker: string;
  account: "etoro" | "tr" | "manual" | null;
  shares: number | null;
  avg_cost: number | null;
  current_price: number | null;
  market_value_usd: number | null;
  pnl_total_pct: number | null;
  pnl_day_pct: number | null;
  position_percent: number | null;
  verdict: string | null;
}

export interface HoldingDiff {
  ticker: string;
  account: string | null;
  change_type: "added" | "removed" | "changed" | "unchanged";
  from_shares: number | null;
  to_shares: number | null;
  shares_delta: number | null;
  from_market_value_usd: number | null;
  to_market_value_usd: number | null;
  value_delta_usd: number | null;
  from_pnl_pct: number | null;
  to_pnl_pct: number | null;
}

export interface SnapshotCompare {
  from_date: string;
  to_date: string;
  from_total_usd: number | null;
  to_total_usd: number | null;
  total_delta_usd: number | null;
  from_cash_usd: number | null;
  to_cash_usd: number | null;
  cash_delta_usd: number | null;
  holdings: HoldingDiff[];
}

export interface HoldingHistoryPoint {
  report_date: string;
  account: string | null;
  shares: number | null;
  avg_cost: number | null;
  current_price: number | null;
  market_value_usd: number | null;
  pnl_total_pct: number | null;
}

export interface PortfolioSummaryPoint {
  report_date: string;
  combined_total_usd: number | null;
  combined_cash_usd: number | null;
  cash_ratio_pct: number | null;
  etoro_total_usd: number | null;
  tr_total_eur: number | null;
}

export interface ReportUploadResponse {
  snapshot_id: string;
  morning_report_id: string;
  report_date: string;
  source: string;
  holdings_count: number;
  recommendations_parsed: number;
  recommendations_persisted: number;
  skipped_holdings: number;
  skipped_recommendations: number;
}

export interface BulkLoadFileResult {
  file: string;
  report_date: string | null;
  snapshot_id: string | null;
  holdings: number | null;
  recommendations: number | null;
  error: string | null;
}

export interface BulkLoadResponse {
  path: string;
  pattern: string;
  found: number;
  loaded: number;
  failed: number;
  files: BulkLoadFileResult[];
}

// ── Review APIs (Phase C) ──

export type ExecutionStatus = "executed" | "skipped" | "partial";
export type SkipReason = "forgot" | "disagreed" | "no_cash" | "waiting_better_price" | "other";

export interface StockBrief {
  id: string;
  ticker: string;
  name: string;
}

export interface RecommendationListItem {
  id: string;
  ticker: string;
  direction: string;
  priority: string | null;
  account: string | null;
  reference_price: number | null;
  report_date: string | null;
  operation_advice: string | null;
  has_execution: boolean;
  execution_status: ExecutionStatus | null;
  stock: StockBrief | null;
}

export interface ExecutionRead {
  id: string;
  status: ExecutionStatus;
  actual_price: number | null;
  actual_shares: number | null;
  execution_date: string | null;
  skip_reason: SkipReason | null;
  skip_note: string | null;
  created_at: string;
  updated_at: string;
}

export interface SimulationRead {
  id: string;
  sim_entry_price: number;
  sim_entry_date: string;
  sim_entry_shares: number;
  sim_exit_price: number | null;
  sim_exit_date: string | null;
  sim_pnl_usd: number | null;
  sim_pnl_pct: number | null;
  actual_pnl_usd: number | null;
  regret_usd: number | null;
  created_at: string;
}

export interface RecommendationDetail {
  id: string;
  morning_report_id: string | null;
  sector_recommendation_id: string | null;
  ticker: string;
  direction: string;
  priority: string | null;
  account: string | null;
  reference_price: number | null;
  report_date: string | null;
  logic_analysis: string | null;
  operation_advice: string | null;
  created_at: string;
  stock: StockBrief | null;
  executions: ExecutionRead[];
  simulations: SimulationRead[];
}

export interface ReviewStats {
  total: number;
  executed: number;
  skipped: number;
  pending: number;
  execution_rate_pct: number | null;
  avg_sim_pnl_pct: number | null;
  avg_regret_usd: number | null;
}

export interface RegretItem {
  recommendation_id: string;
  ticker: string;
  report_date: string | null;
  skip_reason: SkipReason | null;
  sim_pnl_usd: number | null;
  sim_pnl_pct: number | null;
  regret_usd: number | null;
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
