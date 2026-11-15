"""
news_routes.py — Sentix Intelligence Platform
-----------------------------------------------
Flask Blueprint containing all News Analyzer routes.

Strictly separated from:
  - Authentication (auth_routes.py)
  - Watchlist (watchlist_routes.py)

This module is purely the news intelligence layer. It exposes:
  GET  /news-analyzer              → Main dashboard (sector + gainer/loser data)
  GET  /api/sector/<sector>        → Filtered articles for one sector
  GET  /api/market-summary         → Cross-sector sentiment aggregation
  GET  /api/summarize              → On-demand article full-text summarization
  GET  /api/feed-health            → Feed health stats (ops/monitoring)
  GET  /api/logs                   → Processing log tail
  POST /api/refresh-cache          → Force cache invalidation + re-fetch
"""

import logging
from datetime import datetime
from collections import defaultdict
from flask import Blueprint, jsonify, render_template, request, session

from cache_service import cache
from rss_service import fetch_all_feeds, get_feed_health
from sentiment_service import compute_time_decay
from sector_service import sector_service, SYMBOL_TO_SECTOR
from summarizer_service import summarizer_service

logger = logging.getLogger("sentix.routes.news")

news_bp = Blueprint("news", __name__)

# ---------------------------------------------------------------------------
# Cache configuration
# ---------------------------------------------------------------------------

_CACHE_NS          = "news"
_CACHE_KEY_SECTOR  = "sector_articles"
_CACHE_KEY_GAINERS = "gainers_losers"
_CACHE_TTL         = 600       # 10 minutes — news refresh cycle


# ---------------------------------------------------------------------------
# Internal data layer helpers
# ---------------------------------------------------------------------------

def _get_sector_articles() -> dict[str, list[dict]]:
    active = cache.get("sector_articles_old", namespace="news")

    if active is not None:
        return active

    logger.info("No active cache found — fetching initial dataset")
    fresh_data = fetch_all_feeds()

    cache.set("sector_articles_old", fresh_data or {}, ttl=_CACHE_TTL, namespace="news")

    return fresh_data or {}


def _get_gainers_losers(sector_articles: dict) -> dict:
    """Build gainers/losers per sector. Cached separately from raw articles."""
    cached = cache.get(_CACHE_KEY_GAINERS, namespace=_CACHE_NS)
    if cached is not None:
        return cached

    result = _build_gainers_losers(sector_articles)
    cache.set(_CACHE_KEY_GAINERS, result, ttl=_CACHE_TTL, namespace=_CACHE_NS)
    return result


def _build_gainers_losers(sector_articles: dict) -> dict:
    """
    Build gainers/losers data structure per sector.

    Logic:
      - A stock is a 'gainer' if it has more positive articles than negative
        (weighted by sentiment_score, not raw count)
      - Articles are attributed to their CSV sector, not the article's classified sector
        (prevents cross-sector contamination)
    """
    # Aggregate per symbol
    stock_data: dict[str, dict] = defaultdict(lambda: {
        "positive_score": 0.0,
        "negative_score": 0.0,
        "articles": [],
        "csv_sector": None,
    })

    for _, articles in sector_articles.items():
        for art in articles:
            mentions = art.get("stock_mentions", [])
            label    = art.get("sentiment_label", "Neutral")
            score    = abs(art.get("sentiment_score", 0.0))

            for symbol in mentions:
                csv_sector = SYMBOL_TO_SECTOR.get(symbol)
                if not csv_sector:
                    continue

                sd = stock_data[symbol]
                sd["csv_sector"] = csv_sector
                sd["articles"].append(art)

                if label == "Positive":
                    sd["positive_score"] += score
                elif label == "Negative":
                    sd["negative_score"] += score

    # Build per-sector result
    result: dict[str, dict] = {}
    all_sectors = sector_articles.keys()

    for sector in set(list(all_sectors) + list(SYMBOL_TO_SECTOR.values())):
        gainers = []
        losers  = []

        for symbol, sd in stock_data.items():
            if sd["csv_sector"] != sector:
                continue

            pos_score = sd["positive_score"]
            neg_score = sd["negative_score"]

            if pos_score > neg_score and pos_score > 0:
                gainers.append({
                    "symbol":         symbol,
                    "score":          round(pos_score, 2),
                    "article_count":  len(sd["articles"]),
                    "articles":       sd["articles"][:3],
                })
            elif neg_score > pos_score and neg_score > 0:
                losers.append({
                    "symbol":         symbol,
                    "score":          round(neg_score, 2),
                    "article_count":  len(sd["articles"]),
                    "articles":       sd["articles"][:3],
                })

        # Sort by score
        gainers.sort(key=lambda x: x["score"], reverse=True)
        losers.sort(key=lambda x: x["score"], reverse=True)

        # Collect positive/negative articles for this sector
        positive_arts = []
        negative_arts = []
        for arts in sector_articles.values():
            for art in arts:
                if any(SYMBOL_TO_SECTOR.get(s) == sector for s in art.get("stock_mentions", [])):
                    if art["sentiment_label"] == "Positive":
                        positive_arts.append(art)
                    elif art["sentiment_label"] == "Negative":
                        negative_arts.append(art)

        if gainers or losers or positive_arts or negative_arts:
            result[sector] = {
                "gainers":  gainers[:10],
                "losers":   losers[:10],
                "positive": positive_arts[:10],
                "negative": negative_arts[:10],
            }

    return result


def _market_sentiment_summary(sector_articles: dict) -> dict:
    """
    Cross-sector sentiment aggregation for market overview widget.

    Returns:
      overall_sentiment, overall_score, sector_breakdown, top_movers
    """
    total_score = 0.0
    count = 0
    sector_breakdown = {}

    for sector, articles in sector_articles.items():
        if not articles:
            continue

        sector_score = sum(a.get("sentiment_score", 0) for a in articles)
        avg_score = sector_score / len(articles)
        pos_count = sum(1 for a in articles if a.get("sentiment_label") == "Positive")
        neg_count = sum(1 for a in articles if a.get("sentiment_label") == "Negative")

        sector_breakdown[sector] = {
            "avg_score":     round(avg_score, 2),
            "article_count": len(articles),
            "positive":      pos_count,
            "negative":      neg_count,
            "neutral":       len(articles) - pos_count - neg_count,
        }

        total_score += sector_score
        count += len(articles)

    overall_score = total_score / count if count > 0 else 0.0

    if overall_score > 1.5:
        overall_label = "Bullish"
    elif overall_score < -1.5:
        overall_label = "Bearish"
    else:
        overall_label = "Neutral"

    return {
        "overall_sentiment": overall_label,
        "overall_score":     round(overall_score, 2),
        "total_articles":    count,
        "sector_breakdown":  sector_breakdown,
    }


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@news_bp.route("/news-analyzer")
def news_analyzer():
    """Main dashboard — renders sector cards with gainer/loser data."""
    try:
        sector_articles = _get_sector_articles()
        sector_data     = _get_gainers_losers(sector_articles)
        total_articles  = sum(len(v) for v in sector_articles.values())
        cache_stats     = cache.get_stats()

        username       = session.get("username")
        watchlist_count = 0

        if "user_id" in session:
            # Lazy import to keep news layer decoupled from auth
            try:
                from watchlist_service import get_watchlist_count
                watchlist_count = get_watchlist_count(session["user_id"])
            except ImportError:
                pass

        return render_template(
            "test.html",
            sector_data     = sector_data,
            total_articles  = total_articles,
            last_updated    = datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            username        = username,
            watchlist_count = watchlist_count,
            cache_hit_rate  = cache_stats.get("hit_rate_pct", 0),
        )

    except Exception as exc:
        logger.exception(f"Dashboard render error: {exc}")
        return jsonify({"error": str(exc)}), 500


@news_bp.route("/api/sector/<sector_name>")
def api_sector_articles(sector_name: str):
    """
    Return all articles for a specific sector.
    Supports ?sentiment=Positive|Negative|Neutral filter.
    Supports ?limit=N (default 20).
    """
    try:
        sector_articles = _get_sector_articles()

        # Case-insensitive sector lookup
        matched_sector = next(
            (k for k in sector_articles if k.lower() == sector_name.lower()),
            None
        )

        if not matched_sector:
            available = list(sector_articles.keys())
            return jsonify({"error": f"Sector '{sector_name}' not found", "available": available}), 404

        articles = sector_articles[matched_sector]

        # Apply filters
        sentiment_filter = request.args.get("sentiment")
        if sentiment_filter and sentiment_filter in ("Positive", "Negative", "Neutral"):
            articles = [a for a in articles if a.get("sentiment_label") == sentiment_filter]

        limit = min(int(request.args.get("limit", 20)), 100)
        articles = articles[:limit]

        return jsonify({
            "sector":        matched_sector,
            "article_count": len(articles),
            "articles":      articles,
        })

    except Exception as exc:
        logger.exception(f"Sector API error: {exc}")
        return jsonify({"error": str(exc)}), 500


@news_bp.route("/api/market-summary")
def api_market_summary():
    """Cross-sector market sentiment overview."""
    try:
        sector_articles = _get_sector_articles()
        summary = _market_sentiment_summary(sector_articles)
        return jsonify(summary)
    except Exception as exc:
        logger.exception(f"Market summary error: {exc}")
        return jsonify({"error": str(exc)}), 500


@news_bp.route("/api/summarize")
def api_summarize():
    """
    On-demand article full-text extraction, summarization and AI analysis.

    Query params:
      url   : Article URL (required) — may be a redirect/Google News URL
      title : Article headline from RSS feed (optional but strongly recommended)
              When provided, Groq analyses the real headline, not the URL string.

    All defects fixed:
      D1/D10: title param (real headline) passed to sentiment engine, not URL
      D4:     URL redirect resolution happens inside extract_and_summarize
      D6:     Never returns HTTP 500 — extract_and_summarize always returns dict
    """
    url   = request.args.get("url",   "").strip()
    title = request.args.get("title", "").strip()

    if not url:
        return jsonify({"error": "url parameter is required", "success": False}), 400

    # extract_and_summarize handles ALL errors internally — never raises  (D6 FIX)
    result = summarizer_service.extract_and_summarize(url, article_title=title)

    if not result["success"]:
        # Return 200 with success=False so the frontend can show the error message
        # cleanly instead of seeing an HTTP error status
        return jsonify(result), 200

    return jsonify(result), 200


@news_bp.route("/api/feed-health")
def api_feed_health():
    """
    Feed health statistics for operational monitoring.
    Requires admin session in production (stub check here).
    """
    health = get_feed_health()
    cache_stats = cache.get_stats()

    return jsonify({
        "feeds":       health,
        "cache":       cache_stats,
        "timestamp":   datetime.now().isoformat(),
    })


@news_bp.route("/api/refresh-cache", methods=["POST"])
def api_refresh_cache():
    """Force cache invalidation and trigger fresh news fetch."""
    # In production: require admin auth token
    # token = request.headers.get("X-Admin-Token")
    # if token != os.getenv("ADMIN_TOKEN"): return 403

    try:
        flushed = cache.flush_namespace(_CACHE_NS)
        logger.info(f"Cache force-refresh: {flushed} keys flushed")

        # Eagerly pre-warm cache in background
        import threading
        def _prefetch():
            sector_articles = fetch_all_feeds()
            cache.set(_CACHE_KEY_SECTOR, sector_articles, ttl=_CACHE_TTL, namespace=_CACHE_NS)
            logger.info("Cache pre-warmed after force-refresh")

        threading.Thread(target=_prefetch, daemon=True).start()

        return jsonify({
            "success":      True,
            "keys_flushed": flushed,
            "message":      "Cache invalidated. Background re-fetch started.",
        })

    except Exception as exc:
        logger.exception(f"Cache refresh error: {exc}")
        return jsonify({"error": str(exc)}), 500


@news_bp.route("/api/logs")
def api_logs():
    """Return recent processing logs (for live dashboard log widget)."""
    from logging import getLogger
    # In production wire this to a proper log handler buffer
    # Returning placeholder for now
    return jsonify({
        "logs":      [],
        "timestamp": datetime.now().isoformat(),
    })
