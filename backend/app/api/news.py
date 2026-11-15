import logging
from typing import List, Optional
from fastapi import APIRouter, Query, HTTPException
from app.core.store import central_store
from app.services.rss_engine import rss_engine

router = APIRouter(prefix="/news", tags=["News & Sentiment"])
logger = logging.getLogger("finsentiq.api.news")

def calculate_movers_for_articles(articles: list) -> tuple[list, list]:
    stock_scores = {}
    for a in articles:
        for sym in a.get("stock_mentions", []):
            if sym not in stock_scores:
                stock_scores[sym] = {
                    "symbol": sym,
                    "positive_score": 0.0,
                    "negative_score": 0.0,
                    "article_count": 0,
                    "sector": a.get("sector", "Broad Market"),
                    "top_article_title": a.get("title")
                }
            score = a.get("sentiment_score", 0.0)
            if score > 0:
                stock_scores[sym]["positive_score"] += score
            elif score < 0:
                stock_scores[sym]["negative_score"] += abs(score)
            stock_scores[sym]["article_count"] += 1

    stocks_list = []
    for sym, d in stock_scores.items():
        net = round(d["positive_score"] - d["negative_score"], 2)
        d["net_score"] = net
        d["sentiment_label"] = "Bullish" if net > 1.5 else "Bearish" if net < -1.5 else "Neutral"
        stocks_list.append(d)

    gainers = sorted([s for s in stocks_list if s["net_score"] > 0], key=lambda x: x["net_score"], reverse=True)[:10]
    losers = sorted([s for s in stocks_list if s["net_score"] < 0], key=lambda x: x["net_score"])[:10]
    return gainers, losers

@router.get("/articles")
async def get_articles(
    sector: Optional[str] = Query(None, description="Sector name to filter by, or 'All'"),
    sentiment: Optional[str] = Query(None, description="Positive, Negative, Neutral"),
    search: Optional[str] = Query(None, description="Search term in headline or symbol")
):
    """
    Sub-millisecond query from memory store.
    Zero feed reloads triggered by user request.
    """
    articles = central_store.get_articles_by_sector(sector)

    if sentiment:
        articles = [a for a in articles if a.get("sentiment_label", "").lower() == sentiment.lower()]

    if search:
        s = search.lower()
        articles = [
            a for a in articles
            if s in a.get("title", "").lower() or any(s in sym.lower() for sym in a.get("stock_mentions", []))
        ]

    # Calculate dynamic gainers & losers for this specific filtered view
    sector_gainers, sector_losers = calculate_movers_for_articles(articles)

    return {
        "count": len(articles),
        "articles": articles,
        "sector": sector or "All",
        "sector_gainers": sector_gainers,
        "sector_losers": sector_losers
    }

@router.get("/market-overview")
async def get_market_overview():
    """Returns overall market sector sentiment heatmap and overall top bullish/bearish stock movers."""
    return central_store.get_market_overview()

@router.post("/refresh-feeds", status_code=202)
async def trigger_refresh():
    import asyncio
    asyncio.create_task(rss_engine.ingest_and_process_all())
    return {"message": "Background feed ingestion started successfully."}
