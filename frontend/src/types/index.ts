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
