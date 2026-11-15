from pydantic import BaseModel, HttpUrl, Field
from typing import List, Optional, Dict, Any
from datetime import datetime

class SentimentResult(BaseModel):
    sentiment_label: str = Field(description="Positive, Neutral, or Negative")
    sentiment_score: float = Field(description="Score between -10.0 and +10.0")
    confidence: float = Field(default=0.8, ge=0.0, le=1.0)
    impact_type: str = Field(default="Unknown", description="Earnings, Regulatory, Macro, Corporate Action, etc.")
    reasoning: str = Field(default="", max_length=250)

class Article(BaseModel):
    id: str
    title: str
    link: str
    published: str
    published_iso: Optional[str] = None
    source: str
    source_weight: float = 1.0
    summary: Optional[str] = None
    sector: str = "Broad Market"
    stock_mentions: List[str] = []
    sentiment_label: str = "Neutral"
    sentiment_score: float = 0.0
    confidence: float = 0.5
    impact_type: str = "Unknown"
    reasoning: Optional[str] = None
    age_hours: float = 0.0
    decayed_score: float = 0.0

class StockGainerLoser(BaseModel):
    symbol: str
    positive_score: float
    negative_score: float
    net_score: float
    sentiment_label: str
    article_count: int
    sector: str
    top_article_title: Optional[str] = None

class SectorSummary(BaseModel):
    sector: str
    article_count: int
    avg_sentiment: float
    positive_count: int
    negative_count: int
    neutral_count: int
    sentiment_label: str

class MarketOverview(BaseModel):
    timestamp: str
    total_articles: int
    overall_sentiment_score: float
    market_mood: str
    sectors: List[SectorSummary]
    top_gainers: List[StockGainerLoser]
    top_losers: List[StockGainerLoser]

class SummarizeRequest(BaseModel):
    url: str

class SummarizeResponse(BaseModel):
    url: str
    title: str
    summary_bullets: List[str]
    sentiment: SentimentResult
    key_catalysts: List[str]
    source: str
