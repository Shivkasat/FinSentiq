export interface Article {
  id: string;
  title: string;
  link: string;
  published: string;
  published_iso?: string;
  source: string;
  source_weight: number;
  summary?: string;
  sector: string;
  stock_mentions: string[];
  sentiment_label: 'Positive' | 'Neutral' | 'Negative' | 'Bullish' | 'Bearish';
  sentiment_score: number;
  confidence: number;
  impact_type: string;
  reasoning?: string;
  age_hours: number;
  decayed_score: number;
}

export interface StockMover {
  symbol: string;
  positive_score: number;
  negative_score: number;
  net_score: number;
  sentiment_label: 'Bullish' | 'Bearish' | 'Neutral';
  article_count: number;
  sector: string;
  top_article_title?: string;
  price?: number;
  change?: number;
  percent_change?: number;
  prediction_aligned?: boolean;
  validation_outcome?: string;
}

export interface AccuracyScoreboard {
  win_rate: number;
  total_signals: number;
  successful_predictions: number;
  gainers_avg_return: number;
  losers_avg_return: number;
  alpha_spread: number;
  precision_at_k: string;
}

export interface SectorSummary {
  sector: string;
  article_count: number;
  avg_sentiment: number;
  positive_count: number;
  negative_count: number;
  neutral_count: number;
  sentiment_label: 'Bullish' | 'Bearish' | 'Neutral';
}

export interface MarketOverview {
  last_updated: string;
  summary: {
    total_articles: number;
    sectors: SectorSummary[];
    overall_mood: string;
  };
  gainers: StockMover[];
  losers: StockMover[];
  accuracy_scoreboard?: AccuracyScoreboard;
}

export interface CopilotResponse {
  answer: string;
  relevant_symbols: string[];
  referenced_articles: { title: string; link: string; sentiment: string }[];
  confidence: number;
}

export interface StockQuote {
  symbol: string;
  price: number;
  change: number;
  percent_change: number;
  sector: string;
}

export interface WatchlistData {
  user_id: string;
  symbols: string[];
  stocks: StockQuote[];
  total_stocks: number;
}

export interface AISummaryResult {
  url: string;
  title: string;
  summary: string;
  stock_mentions: string[];
  sector: string;
  sentiment: string;
  sentiment_score: number;
  confidence: number;
  impact_type: string;
  reasoning: string;
  word_count: number;
  analysis_success: boolean;
}

export interface HoldingInput {
  symbol: string;
  quantity: number;
  buy_price: number;
}

export interface ScannedHolding {
  symbol: string;
  sector: string;
  quantity: number;
  buy_price: number;
  current_price: number;
  invested_value: number;
  current_value: number;
  pnl_amount: number;
  pnl_percent: number;
  article_count: number;
  sentiment_score: number;
  sentiment_label: string;
  risk_level: string;
  primary_catalyst?: string;
  catalyst_headline?: string;
  catalyst_link?: string;
}

export interface PortfolioScanResult {
  total_invested: number;
  total_current: number;
  total_pnl: number;
  total_pnl_percent: number;
  portfolio_sentiment_score: number;
  overall_risk_rating: string;
  actionable_summary: string;
  scanned_holdings: ScannedHolding[];
  flagged_risk_count: number;
}

export interface DivergenceAnomaly {
  symbol: string;
  sector: string;
  price: number;
  percent_change: number;
  sentiment_score: number;
  sentiment_label: 'Bullish' | 'Bearish';
  divergence_score: number;
  abs_divergence: number;
  quadrant_id: 'ZONE_1_ACCUMULATION' | 'ZONE_2_DISTRIBUTION' | 'ZONE_3_MOMENTUM' | 'ZONE_4_CAPITULATION' | 'EQUILIBRIUM';
  quadrant_label: string;
  action_code: 'STRONG_BUY_DIP' | 'EXIT_TRAP_SHORT' | 'RIDE_MOMENTUM' | 'SHORT_BREAKDOWN' | 'HOLD_NEUTRAL';
  action_description: string;
  conviction: 'VERY HIGH' | 'HIGH' | 'MODERATE' | 'LOW';
  rebound_target_pct: number;
  trailing_stop_pct: number;
  catalyst_headline: string;
  catalyst_link: string;
  catalyst_type: string;
  is_single_stock: boolean;
  detected_at?: string;
}

export interface QuadrantGroup {
  label: string;
  count: number;
  items: DivergenceAnomaly[];
}

export interface DivergenceRadarResponse {
  total_anomalies: number;
  market_disconnect_index: number;
  quadrants: {
    zone_1_accumulation: QuadrantGroup;
    zone_2_distribution: QuadrantGroup;
    zone_3_momentum: QuadrantGroup;
    zone_4_capitulation: QuadrantGroup;
  };
  top_mispricings: DivergenceAnomaly[];
  last_scan: string;
}
