"""
rss_service.py — Sentix Intelligence Platform
-----------------------------------------------
Production-grade multi-threaded RSS feed aggregator for Indian equity news.

Key upgrades over original:
  - ThreadPoolExecutor (not raw threads) for proper pool management
  - Per-feed configurable max_articles and timeout
  - Source weight aware: feeds tagged with their source_key
  - 50-hour rolling window for article freshness (configurable)
  - Indian market filter enforced before any processing (saves CPU)
  - Structured article schema — consistent shape for all downstream consumers
  - All errors isolated per-feed; one bad feed never blocks others
  - Feed health tracking: success/fail counts per source
"""

import time
import logging
import threading
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor, as_completed, TimeoutError as FuturesTimeout
from collections import defaultdict
from typing import Optional
from dataclasses import dataclass, field

import feedparser
from bs4 import BeautifulSoup

from sector_service import sector_service, VALID_SYMBOLS, COMPANY_TO_SYMBOL
from sentiment_service import sentiment_service

from summarizer_service import summarizer_service, get_source_display_name

logger = logging.getLogger("sentix.rss")


# ---------------------------------------------------------------------------
# Indian market filter — executed FIRST on every article (cheap & fast)
# ---------------------------------------------------------------------------

_INDIA_KEYWORDS = frozenset({
    "india", "indian", "mumbai", "delhi", "bangalore", "hyderabad", "chennai",
    "nse", "bse", "sensex", "nifty", "rupee", "rbi", "sebi", "mcx",
    "dalal street", "d-street",
})

# All Indian company names and symbols from CSV (loaded via sector_service)
_ALL_INDIAN_TERMS = (
    {name.lower() for name in COMPANY_TO_SYMBOL}
    | {sym.lower() for sym in VALID_SYMBOLS}
)


def _is_indian_market_news(title: str, description: str) -> bool:
    """
    Fast Indian market relevance filter.
    Returns True if article clearly relates to Indian equities.
    """
    combined = f"{title} {description}".lower()
    if any(kw in combined for kw in _INDIA_KEYWORDS):
        return True
    if any(term in combined for term in _ALL_INDIAN_TERMS if len(term) >= 4):
        return True
    return False


# ---------------------------------------------------------------------------
# Structured article schema
# ---------------------------------------------------------------------------

@dataclass
class NewsArticle:
    title: str
    description: str
    url: str
    source_key: str
    source_name: str
    published_ts: Optional[float]          # Unix timestamp
    published_date: str                    # Human-readable
    stock_mentions: list[str]
    sector: Optional[str]
    sentiment_label: str
    sentiment_score: float
    confidence: float
    impact_type: str
    reasoning: str
    summary: str
    time_decay: float = 1.0


# ---------------------------------------------------------------------------
# RSS feed registry
# Each entry: source_key → { url, max_articles, timeout_seconds }
# ---------------------------------------------------------------------------

RSS_FEEDS: dict[str, dict] = {
    # ── Economic Times ───────────────────────────────────────────────────
    "economic_times_market":        {"url": "https://economictimes.indiatimes.com/markets/rssfeeds/1977021501.cms",       "max_articles": 25, "timeout": 15},
    "economic_times_stocks":        {"url": "https://economictimes.indiatimes.com/markets/stocks/rssfeeds/2146842.cms",   "max_articles": 25, "timeout": 15},
    "economic_times_ipos":          {"url": "https://economictimes.indiatimes.com/markets/ipo/rssfeeds/67812142.cms",     "max_articles": 15, "timeout": 12},
    "economic_times_commodities":   {"url": "https://economictimes.indiatimes.com/markets/commodities/rssfeeds/1808152121.cms", "max_articles": 15, "timeout": 12},

    # ── Moneycontrol ─────────────────────────────────────────────────────
    "moneycontrol":                 {"url": "https://www.moneycontrol.com/rss/business.xml",           "max_articles": 25, "timeout": 15},
    "moneycontrol_news":            {"url": "https://www.moneycontrol.com/rss/latestnews.xml",         "max_articles": 25, "timeout": 15},
    "moneycontrol_markets":         {"url": "https://www.moneycontrol.com/rss/marketreports.xml",      "max_articles": 20, "timeout": 12},
    "moneycontrol_stocks":          {"url": "https://www.moneycontrol.com/rss/stockmarket.xml",        "max_articles": 20, "timeout": 12},

    # ── Business Standard ────────────────────────────────────────────────
    "business_standard":            {"url": "https://www.business-standard.com/rss/markets-106.rss",          "max_articles": 25, "timeout": 15},
    "business_standard_companies":  {"url": "https://www.business-standard.com/rss/companies-101.rss",        "max_articles": 20, "timeout": 12},
    "business_standard_economy":    {"url": "https://www.business-standard.com/rss/economy-policy-102.rss",   "max_articles": 15, "timeout": 12},

    # ── Financial Express ────────────────────────────────────────────────
    "financial_express":            {"url": "https://www.financialexpress.com/market/feed/",    "max_articles": 20, "timeout": 12},
    "financial_express_industry":   {"url": "https://www.financialexpress.com/industry/feed/",  "max_articles": 15, "timeout": 12},

    # ── Livemint ─────────────────────────────────────────────────────────
    "livemint":                     {"url": "https://www.livemint.com/rss/markets",   "max_articles": 25, "timeout": 15},
    "livemint_companies":           {"url": "https://www.livemint.com/rss/companies", "max_articles": 20, "timeout": 12},
    "livemint_money":               {"url": "https://www.livemint.com/rss/money",     "max_articles": 15, "timeout": 12},

    # ── NDTV Profit ──────────────────────────────────────────────────────
    "ndtv_business":                {"url": "https://feeds.feedburner.com/ndtvprofit-latest", "max_articles": 20, "timeout": 12},

    # ── Zee Business ─────────────────────────────────────────────────────
    "zeebiz":                       {"url": "https://www.zeebiz.com/rss/markets.xml",         "max_articles": 20, "timeout": 12},
    "zeebiz_stocks":                {"url": "https://www.zeebiz.com/rss/market-news.xml",     "max_articles": 20, "timeout": 12},

    # ── CNBC TV18 ────────────────────────────────────────────────────────
    "cnbc_market":                  {"url": "https://www.cnbctv18.com/rss/marketnews.xml",  "max_articles": 20, "timeout": 12},
    "cnbc_business":                {"url": "https://www.cnbctv18.com/rss/latestnews.xml",  "max_articles": 20, "timeout": 12},

    # ── BQ Prime ─────────────────────────────────────────────────────────
    "bq_prime_markets":             {"url": "https://www.bqprime.com/markets.rss",  "max_articles": 20, "timeout": 12},
    "bq_prime_business":            {"url": "https://www.bqprime.com/business.rss", "max_articles": 20, "timeout": 12},

    # ── Hindu Business Line ──────────────────────────────────────────────
    "hindu_business_line":          {"url": "https://www.thehindubusinessline.com/markets/stock-markets/feeder/default.rss", "max_articles": 20, "timeout": 12},

    # ── Business Today ───────────────────────────────────────────────────
    "business_today_markets":       {"url": "https://www.businesstoday.in/rss/market",   "max_articles": 15, "timeout": 12},
    "business_today_companies":     {"url": "https://www.businesstoday.in/rss/company",  "max_articles": 15, "timeout": 12},

    # ── Reuters India ────────────────────────────────────────────────────
    "reuters_india":                {"url": "https://www.reuters.com/rssFeed/INbusinessNews", "max_articles": 20, "timeout": 15},

    # ── Google News (targeted) ───────────────────────────────────────────
    "google_india_business":        {"url": "https://news.google.com/rss/topics/CAAqJggKIiBDQkFTRWdvSUwyMHZNRFp0Y0RvU0FtVnVHZ0pKVGtnQVAB?hl=en-IN&gl=IN&ceid=IN:en", "max_articles": 20, "timeout": 15},
    "google_india_stocks":          {"url": "https://news.google.com/rss/search?q=indian%20stocks&hl=en-IN&gl=IN&ceid=IN:en", "max_articles": 15, "timeout": 15},
    "google_sensex":                {"url": "https://news.google.com/rss/search?q=sensex&hl=en-IN&gl=IN&ceid=IN:en",          "max_articles": 10, "timeout": 12},
    "google_nifty":                 {"url": "https://news.google.com/rss/search?q=nifty&hl=en-IN&gl=IN&ceid=IN:en",           "max_articles": 10, "timeout": 12},

    # ── Times of India ───────────────────────────────────────────────────
    "toi_business":                 {"url": "https://timesofindia.indiatimes.com/rssfeeds/1898055.cms", "max_articles": 15, "timeout": 12},

    # ── Investing.com ────────────────────────────────────────────────────
    "investing_india":              {"url": "https://www.investing.com/rss/news_301.rss", "max_articles": 15, "timeout": 12},

    # ── OFFICIAL REGULATORS ──────────────────────────────────────────────
    # Run validate_feeds.py on your machine first.
    # Paste ONLY the feeds that print "PASS" below.
    # Delete this comment block once done.
    #
    # EXAMPLE (replace with your actual passing feeds):
    # "rbi_press_releases": {"url": "https://www.rbi.org.in/rss/Rss.aspx?Id=1", "max_articles": 20, "timeout": 12},
    # "rbi_circulars":      {"url": "https://www.rbi.org.in/rss/Rss.aspx?Id=4", "max_articles": 20, "timeout": 12},
    # "rbi_notifications":  {"url": "https://www.rbi.org.in/rss/Rss.aspx?Id=7", "max_articles": 20, "timeout": 12},
    # "sebi_news":          {"url": "https://www.sebi.gov.in/sebirss.xml",        "max_articles": 20, "timeout": 12},
    # "sebi_orders":        {"url": "https://www.sebi.gov.in/sebirssorders.xml",  "max_articles": 20, "timeout": 12},
    # "bse_announcements":  {"url": "https://www.bseindia.com/xml-data/corpfiling/announcements.xml", "max_articles": 20, "timeout": 12},
}

# Maximum age of articles to process (hours)
NEWS_WINDOW_HOURS: int = 50

# ThreadPool configuration
MAX_WORKERS: int = 20                   # Concurrent feed fetchers
FEED_TIMEOUT_SECONDS: int = 30          # Max wait per feed before giving up


# ---------------------------------------------------------------------------
# Feed health tracker
# ---------------------------------------------------------------------------

class FeedHealthTracker:
    """Tracks success/failure per source for observability."""

    def __init__(self):
        self._stats: dict[str, dict] = defaultdict(lambda: {"success": 0, "fail": 0, "last_error": None})
        self._lock = threading.Lock()

    def record_success(self, source_key: str, article_count: int) -> None:
        with self._lock:
            self._stats[source_key]["success"] += 1
            self._stats[source_key]["last_count"] = article_count

    def record_failure(self, source_key: str, error: str) -> None:
        with self._lock:
            self._stats[source_key]["fail"] += 1
            self._stats[source_key]["last_error"] = str(error)[:200]

    def get_stats(self) -> dict:
        with self._lock:
            return dict(self._stats)


_health = FeedHealthTracker()


# ---------------------------------------------------------------------------
# Core feed processor
# ---------------------------------------------------------------------------

def _process_feed(source_key: str, config: dict) -> list[NewsArticle]:
    """
    Process a single RSS feed.
    Returns a list of NewsArticle objects passing all filters.
    Fully isolated — exceptions never propagate to caller.
    """
    feed_url = config["url"]
    max_articles = config.get("max_articles", 20)
    cutoff = datetime.now() - timedelta(hours=NEWS_WINDOW_HOURS)
    results: list[NewsArticle] = []

    try:
        logger.debug(f"[{source_key}] Fetching {feed_url}")
        feed = feedparser.parse(feed_url)

        if not hasattr(feed, "entries") or not feed.entries:
            logger.warning(f"[{source_key}] Empty feed response")
            _health.record_failure(source_key, "Empty feed")
            return results

        for entry in feed.entries[:max_articles]:
            title = (entry.get("title") or "").strip()
            link  = (entry.get("link")  or "").strip()

            if not title or not link:
                continue

            # ── Parse publication date ────────────────────────────────
            pub_ts: Optional[float] = None
            pub_date_str = "Unknown"
            if hasattr(entry, "published_parsed") and entry.published_parsed:
                try:
                    pub_dt = datetime.fromtimestamp(time.mktime(entry.published_parsed))
                    pub_ts = pub_dt.timestamp()
                    pub_date_str = pub_dt.strftime("%Y-%m-%d %H:%M")
                    if pub_dt < cutoff:
                        continue           # Too old — skip
                except Exception:
                    pass

            # ── Clean description ─────────────────────────────────────
            raw_desc    = entry.get("summary", "")
            description = BeautifulSoup(raw_desc, "html.parser").get_text()[:800]

            # ── Indian market filter ──────────────────────────────────
            if not _is_indian_market_news(title, description):
                continue

          

            # ── Stock extraction ──────────────────────────────────────
            stock_mentions = sector_service.extract_stocks(title)
            if not stock_mentions:
                continue                   # No recognisable stock → skip

            # ── Sector classification ─────────────────────────────────
            sector = sector_service.classify(title, description)
            if not sector:
                continue                   # Unclassifiable → skip

            # ── Sentiment analysis ────────────────────────────────────
            sentiment_result = sentiment_service.analyze(
                title=title,
                description=description,
                source_key=source_key,
                published_timestamp=pub_ts,
            )

            # ── Quick summary from description ────────────────────────
            summary = summarizer_service.summarize_description(description, max_chars=200)

            article = NewsArticle(
                title=title,
                description=description,
                url=link,
                source_key=source_key,
                source_name=get_source_display_name(source_key),
                published_ts=pub_ts,
                published_date=pub_date_str,
                stock_mentions=stock_mentions,
                sector=sector,
                sentiment_label=sentiment_result.sentiment_label,
                sentiment_score=sentiment_result.sentiment_score,
                confidence=sentiment_result.confidence,
                impact_type=sentiment_result.impact_type,
                reasoning=sentiment_result.reasoning,
                summary=summary,
                time_decay=sentiment_result.sentiment_score,
            )

            results.append(article)

        _health.record_success(source_key, len(results))
        logger.info(f"[{source_key}] ✅ {len(results)} articles processed")

    except Exception as exc:
        _health.record_failure(source_key, str(exc))
        logger.error(f"[{source_key}] ❌ Feed processing error: {exc}", exc_info=False)

    return results


# ---------------------------------------------------------------------------
# Public aggregation function
# ---------------------------------------------------------------------------

def fetch_all_feeds() -> dict[str, list[dict]]:
    """
    Fetch and process all RSS feeds concurrently using ThreadPoolExecutor.

    Returns:
        Sector-keyed dict: { sector_name: [article_dict, ...] }
        Articles are serialized to plain dicts for JSON compatibility.
    """
    logger.info(
        f"🚀 Starting news fetch: {len(RSS_FEEDS)} feeds, "
        f"max_workers={MAX_WORKERS}, window={NEWS_WINDOW_HOURS}h"
    )
    start_time = time.time()

    sector_articles: dict[str, list[dict]] = defaultdict(list)
    total_articles = 0

    with ThreadPoolExecutor(max_workers=MAX_WORKERS, thread_name_prefix="sentix-rss") as executor:
        future_to_key = {
            executor.submit(_process_feed, source_key, config): source_key
            for source_key, config in RSS_FEEDS.items()
        }

        for future in as_completed(future_to_key, timeout=FEED_TIMEOUT_SECONDS + 10):
            source_key = future_to_key[future]
            try:
                articles: list[NewsArticle] = future.result(timeout=FEED_TIMEOUT_SECONDS)
                for article in articles:
                    if article.sector:
                        sector_articles[article.sector].append(_article_to_dict(article))
                        total_articles += 1
            except FuturesTimeout:
                logger.warning(f"[{source_key}] Timeout — skipped")
            except Exception as exc:
                logger.error(f"[{source_key}] Future exception: {exc}")

    elapsed = round(time.time() - start_time, 2)
    logger.info(
        f"🎉 Fetch complete: {total_articles} articles across "
        f"{len(sector_articles)} sectors in {elapsed}s"
    )

    return dict(sector_articles)


def get_feed_health() -> dict:
    """Expose feed health stats for monitoring endpoints."""
    return _health.get_stats()


# ---------------------------------------------------------------------------
# Serialization helper
# ---------------------------------------------------------------------------

def _article_to_dict(article: NewsArticle) -> dict:
    """Convert NewsArticle dataclass to JSON-serializable dict."""
    return {
        "title":           article.title,
        "description":     article.description,
        "url":             article.url,
        "source_key":      article.source_key,
        "source_name":     article.source_name,
        "published_ts":    article.published_ts,
        "published_date":  article.published_date,
        "stock_mentions":  article.stock_mentions,
        "sector":          article.sector,
        "sentiment_label": article.sentiment_label,
        "sentiment_score": article.sentiment_score,
        "confidence":      article.confidence,
        "impact_type":     article.impact_type,
        "reasoning":       article.reasoning,
        "summary":         article.summary,
    }
