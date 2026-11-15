import logging
from typing import List, Optional
from fastapi import APIRouter, Query, HTTPException
from app.core.store import central_store
from app.services.rss_engine import rss_engine

router = APIRouter(prefix="/news", tags=["News & Sentiment"])
logger = logging.getLogger("finsentiq.api.news")

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

    return {
        "count": len(articles),
        "articles": articles
    }

@router.get("/market-overview")
async def get_market_overview():
    """Returns sector sentiment heatmap and top bullish/bearish stock movers."""
    return central_store.get_market_overview()

@router.post("/refresh-feeds", status_code=202)
async def trigger_refresh():
    """Admin endpoint to manually trigger background ingestion worker without waiting for cron."""
    import asyncio
    asyncio.create_task(rss_engine.ingest_and_process_all())
    return {"message": "Background feed ingestion started successfully."}
