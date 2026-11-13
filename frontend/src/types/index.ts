export interface IndexQuote {
  name: string;
  symbol: string;
  price: number;
  change: number;
  change_percent: number;
  open?: number;
  high?: number;
  low?: number;
  previous_close?: number;
  currency: string;
  is_live: boolean;
  is_market_open: boolean;
  timestamp: string;
  data_source: string;
  is_demo: boolean;
}

export interface MarketOverview {
  indices: IndexQuote[];
  market_status: 'OPEN' | 'CLOSED';
  market_message: string;
  current_time_ist: string;
  top_movers?: Array<{
    symbol: string;
    name: string;
    price: number;
    change: number;
    change_percent: number;
    is_demo: boolean;
  }>;
}

export interface StockQuote {
  symbol: string;
  name: string;
  exchange: string;
  price: number;
  change: number;
  change_percent: number;
  open?: number;
  high?: number;
  low?: number;
  close?: number;
  volume?: number;
  previous_close?: number;
  fifty_two_week_high?: number;
  fifty_two_week_low?: number;
  market_cap?: number;
  pe_ratio?: number;
  sector?: string;
  is_live: boolean;
  is_market_open: boolean;
  timestamp: string;
  data_source: string;
  is_demo: boolean;
}

export interface OHLCVPoint {
  timestamp: string;
  open: number;
  high: number;
  low: number;
  close: number;
  volume: number;
}

export interface StockHistory {
  symbol: string;
  period: string;
  interval: string;
  count: number;
  data: OHLCVPoint[];
  data_source: string;
  is_demo: boolean;
}

export interface IndicatorPoint {
  timestamp: string;
  close: number;
  sma_20?: number;
  sma_50?: number;
  sma_200?: number;
  ema_12?: number;
  ema_26?: number;
  rsi_14?: number;
  macd_line?: number;
  macd_signal?: number;
  macd_histogram?: number;
}

export interface IndicatorSummary {
  current_rsi?: number;
  rsi_signal: string;
  macd_signal: string;
  trend_sma: string;
  overall_signal: string;
}

export interface TechnicalIndicatorResponse {
  symbol: string;
  summary: IndicatorSummary;
  indicators: IndicatorPoint[];
  data_source: string;
  is_demo: boolean;
  disclaimer: string;
}

export interface WatchlistItem {
  id: number;
  user_id: number;
  symbol: string;
  company_name?: string;
  exchange: string;
  notes?: string;
  created_at: string;
  current_price?: number;
  change?: number;
  change_percent?: number;
}

export interface HoldingSummary {
  symbol: string;
  company_name?: string;
  exchange: string;
  total_quantity: number;
  avg_buy_price: number;
  invested_value: number;
  current_price: number;
  current_value: number;
  unrealized_pnl: number;
  unrealized_pnl_percent: number;
}

export interface PortfolioOverview {
  total_invested: number;
  current_portfolio_value: number;
  total_pnl: number;
  total_pnl_percent: number;
  holdings_count: number;
  holdings: HoldingSummary[];
}

export interface PortfolioTransaction {
  id: number;
  user_id: number;
  symbol: string;
  company_name?: string;
  exchange: string;
  transaction_type: string;
  quantity: number;
  purchase_price: number;
  transaction_date: string;
  notes?: string;
  created_at: string;
}

export interface PriceAlert {
  id: number;
  user_id: number;
  symbol: string;
  company_name?: string;
  target_price: number;
  condition: 'ABOVE' | 'BELOW';
  is_active: boolean;
  is_triggered: boolean;
  triggered_at?: string;
  notes?: string;
  created_at: string;
  current_price?: number;
}

export interface PredictionResult {
  predicted_price: number;
  expected_change: number;
  expected_change_percent: number;
  predicted_direction: 'UP' | 'DOWN' | 'FLAT';
  model_mae: number;
  directional_accuracy_hist: number;
}

export interface StockPredictionResponse {
  symbol: string;
  current_price: number;
  as_of_date: string;
  target_date: string;
  predictions: Record<string, PredictionResult>;
  consensus_predicted_price: number;
  consensus_predicted_direction: string;
  confidence_level: 'LOW' | 'MODERATE' | 'HIGH';
  data_source: string;
  is_demo: boolean;
  disclaimer: string;
}

export interface ModelMetric {
  mae: number;
  rmse: number;
  directional_accuracy: number;
  sample_count: number;
}

export interface ModelEvaluationSummary {
  model_name: string;
  description: string;
  test_metrics: ModelMetric;
  walk_forward_metrics?: ModelMetric;
  feature_importances?: Record<string, number>;
}

export interface ModelComparisonResponse {
  symbol: string;
  train_date_range: string;
  test_date_range: string;
  train_samples: number;
  test_samples: number;
  models: Record<string, ModelEvaluationSummary>;
  best_model_by_mae: string;
  best_model_by_directional_accuracy: string;
  disclaimer: string;
}

export interface ModelInfoResponse {
  architecture: string;
  supported_models: string[];
  features_used: string[];
  validation_strategy: string;
  metrics: string[];
  data_leakage_safeguards: string[];
  disclaimer: string;
}

export interface HealthResponse {
  status: string;
  service: string;
  version: string;
  environment: string;
  database: {
    status: string;
    database_type: string;
    connectivity_result: string;
    verified_tables: string[];
  };
  current_time_ist: string;
  indian_market: {
    is_open: boolean;
    status_message: string;
  };
}

export interface MarketEventSource {
  title: string;
  url?: string;
  publisher?: string;
  published_at?: string;
}

export interface MarketEvent {
  id: number;
  symbol: string;
  company_name?: string;
  event_date: string;
  event_type: string;
  severity: 'NORMAL' | 'ELEVATED' | 'HIGH' | 'EXTREME' | string;
  price_change_pct: number;
  volume_ratio: number;
  intraday_range_pct: number;
  open_price: number;
  high_price: number;
  low_price: number;
  close_price: number;
  volume: number;
  explanation_summary?: string;
  explanation_detail?: string;
  sources: MarketEventSource[];
  is_verified: boolean;
  created_at?: string;
}

export interface MarketEventListResponse {
  count: number;
  events: MarketEvent[];
}

export interface AnalyzeEventsResponse {
  symbol: string;
  company_name?: string;
  analyzed_sessions: number;
  detected_events_count: number;
  newly_persisted_count: number;
  events: MarketEvent[];
}

export interface HoldingPerformance {
  symbol: string;
  company_name?: string;
  exchange: string;
  total_quantity: number;
  avg_buy_price: number;
  invested_value: number;
  current_price: number;
  current_value: number;
  unrealized_pnl: number;
  unrealized_pnl_percent: number;
  realized_pnl: number;
  portfolio_weight_pct: number;
}

export interface StockAllocation {
  symbol: string;
  company_name?: string;
  current_value: number;
  weight_pct: number;
}

export interface PortfolioAnalytics {
  accounting_methodology: string;
  total_invested: number;
  current_portfolio_value: number;
  realized_pnl: number;
  unrealized_pnl: number;
  total_pnl: number;
  overall_return_percent: number;
  active_holdings_count: number;
  holdings: HoldingPerformance[];
  allocations: StockAllocation[];
}

export interface StockVolatilityItem {
  symbol: string;
  weight_pct: number;
  annualized_volatility_pct: number;
  daily_volatility_pct: number;
}

export interface PortfolioRiskConcentration {
  top_holding_symbol?: string;
  top_holding_weight_pct: number;
  top_3_weight_pct: number;
  hhi: number;
  effective_n: number;
  classification: string;
  thresholds?: any;
}

export interface PortfolioRiskVolatility {
  annualized_portfolio_volatility_pct: number;
  daily_portfolio_volatility_pct: number;
  classification: string;
  stock_volatilities: StockVolatilityItem[];
  thresholds?: any;
}

export interface PortfolioRiskDrawdown {
  maximum_drawdown_pct: number;
  peak_date?: string;
  trough_date?: string;
  classification: string;
  thresholds?: any;
}

export interface PortfolioRiskAnalysis {
  is_empty: boolean;
  insufficient_data?: boolean;
  message?: string;
  risk_score: number;
  risk_level: string;
  concentration: PortfolioRiskConcentration;
  volatility: PortfolioRiskVolatility;
  drawdown: PortfolioRiskDrawdown;
  benchmark_beta?: number | null;
  has_benchmark: boolean;
  benchmark_symbol?: string | null;
  sessions_analyzed: number;
  disclaimer: string;
}

export interface AlertHistoryItem {
  id: number;
  user_id: number;
  alert_id?: number | null;
  symbol?: string | null;
  alert_type: string;
  severity: string;
  title: string;
  message: string;
  trigger_value?: number | null;
  threshold_value?: number | null;
  status: 'TRIGGERED' | 'ACKNOWLEDGED' | 'RESOLVED';
  created_at: string;
  acknowledged_at?: string | null;
  resolved_at?: string | null;
}

export interface AlertPreferences {
  id: number;
  user_id: number;
  price_alerts_enabled: boolean;
  portfolio_alerts_enabled: boolean;
  market_event_alerts_enabled: boolean;
  volume_spike_alerts_enabled: boolean;
  min_price_change_pct: number;
  portfolio_loss_threshold_pct: number;
  portfolio_drawdown_threshold_pct: number;
  cooldown_minutes: number;
  updated_at: string;
}

export interface AlertEvaluateResponse {
  evaluated_at: string;
  new_alerts_triggered_count: number;
  alerts: AlertHistoryItem[];
}

// Stage 7: AI Stock Research & Investment Assistant Types
export interface CompanyFundamentals {
  symbol: string;
  company_name: string;
  sector: string;
  industry: string;
  business_summary: string;
  website: string;
  currency: string;
  reporting_period: string;
  data_source: string;
  retrieved_at: string;
  data_freshness: string;
  overview?: {
    company_name: string;
    sector: string;
    industry: string;
    business_summary: string;
    website: string;
  };
  valuation: {
    market_cap?: number | null;
    market_cap_formatted?: string;
    trailing_pe?: number | null;
    forward_pe?: number | null;
    price_to_book?: number | null;
    price_to_sales?: number | null;
    enterprise_value?: number | null;
    ev_to_ebitda?: number | null;
  };
  growth: {
    revenue_growth_yoy_pct?: number | null;
    profit_growth_yoy_pct?: number | null;
  };
  financial_performance: {
    total_revenue?: number | null;
    revenue_growth_yoy_pct?: number | null;
    net_profit?: number | null;
    profit_growth_yoy_pct?: number | null;
    trailing_eps?: number | null;
    forward_eps?: number | null;
  };
  profitability: {
    roe_pct?: number | null;
    return_on_equity_pct?: number | null;
    roa_pct?: number | null;
    roce_pct?: number | null;
    operating_margin_pct?: number | null;
    net_margin_pct?: number | null;
    free_cash_flow?: number | null;
  };
  financial_health: {
    debt_to_equity?: number | null;
    debt_to_equity_pct?: number | null;
    current_ratio?: number | null;
    quick_ratio?: number | null;
    dividend_yield_pct?: number | null;
  };
  dividends?: {
    dividend_yield_pct?: number | null;
  };
  missing_metrics: string[];
  disclaimer: string;
}

export interface TechnicalAnalysis {
  symbol: string;
  status: string;
  current_price?: number;
  overall_sentiment: 'BULLISH' | 'BEARISH' | 'NEUTRAL' | 'CONFLICTING';
  bullish_signals: string[];
  bearish_signals: string[];
  neutral_conflicts: string[];
  indicators: {
    sma_20?: number | null;
    sma_50?: number | null;
    sma_200?: number | null;
    ema_12?: number | null;
    ema_26?: number | null;
    rsi_14?: number | null;
    macd_line?: number | null;
    macd_signal?: number | null;
    macd_histogram?: number | null;
    historical_volatility_20d_annualized?: number | null;
  };
  support_levels: {
    pivot: number;
    s1: number;
    s2: number;
    swing_low_20d?: number;
  };
  resistance_levels: {
    pivot: number;
    r1: number;
    r2: number;
    swing_high_20d?: number;
  };
  data_horizon: string;
  data_source: string;
  is_demo: boolean;
  retrieved_at: string;
}

export interface StockComparison {
  symbols: string[];
  period: string;
  quotes: StockQuote[];
  fundamentals: CompanyFundamentals[];
  technicals: TechnicalAnalysis[];
  metrics_matrix: Array<{
    category: string;
    metric: string;
    unit: string;
    values: Record<string, any>;
  }>;
  normalized_series: Array<Record<string, any>>;
  comparative_summary: string[];
  generated_at: string;
}

export interface ResearchCitation {
  source: string;
  category: string;
  timestamp: string;
  details: string;
}

export interface ResearchChatMessageItem {
  id?: number;
  session_id: string;
  symbol?: string | null;
  role: 'user' | 'assistant' | 'system';
  content: string;
  sources?: ResearchCitation[] | null;
  retrieved_context?: any;
  provider_used?: string;
  created_at: string;
}

export interface ResearchReportItem {
  id: number;
  symbol: string;
  company_name?: string | null;
  title: string;
  summary: string;
  overview?: any;
  fundamentals?: CompanyFundamentals;
  technicals?: TechnicalAnalysis;
  events?: any[];
  risk_factors?: Array<{
    category: string;
    severity: 'LOW' | 'MEDIUM' | 'HIGH';
    description: string;
  }>;
  sources?: ResearchCitation[];
  conclusion?: string;
  created_at?: string;
}
