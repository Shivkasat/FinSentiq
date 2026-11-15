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
