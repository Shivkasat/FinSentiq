import logging
import asyncio
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.core.store import central_store
from app.services.rss_engine import rss_engine
from app.api.news import router as news_router
from app.api.watchlist import router as watchlist_router

# Configure Structured Logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("finsentiq.main")

async def periodic_feed_worker():
    """Native non-blocking async background worker for periodic feed ingestion."""
    while True:
        try:
            await asyncio.sleep(settings.FEED_FETCH_INTERVAL_MINUTES * 60)
            logger.info("Executing scheduled background RSS ingestion...")
            await rss_engine.ingest_and_process_all()
        except asyncio.CancelledError:
            logger.info("Background feed worker stopped.")
            break
        except Exception as e:
            logger.error(f"Error in background ingestion loop: {e}")
            await asyncio.sleep(60)

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application Lifespan Events:
    - On Startup: Start native async background worker.
    - If store has no articles, trigger initial ingest task.
    - On Shutdown: Cancel worker cleanly.
    """
    logger.info("Initializing FinSentiq FastAPI Engine...")
    
    # Check if central store has articles
    overview = central_store.get_market_overview()
    if not overview.get("summary") or overview["summary"].get("total_articles", 0) == 0:
        logger.info("Central store is cold. Triggering initial background ingestion...")
        asyncio.create_task(rss_engine.ingest_and_process_all())

    # Launch native background periodic worker
    worker_task = asyncio.create_task(periodic_feed_worker())
    logger.info(f"Background Ingestion Worker active (every {settings.FEED_FETCH_INTERVAL_MINUTES} mins).")

    yield

    logger.info("Shutting down FinSentiq Engine...")
    worker_task.cancel()

def create_application() -> FastAPI:
    app = FastAPI(
        title=settings.PROJECT_NAME,
        version=settings.VERSION,
        description="Institutional-grade Indian Stock Market Intelligence & Sentiment Analysis Platform",
        lifespan=lifespan
    )

    # CORS Setup
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Routers
    app.include_router(news_router, prefix=settings.API_V1_STR)
    app.include_router(watchlist_router, prefix=settings.API_V1_STR)

    @app.get("/health", tags=["Health"])
    async def health_check():
        overview = central_store.get_market_overview()
        total = overview.get("summary", {}).get("total_articles", 0)
        return {
            "status": "healthy",
            "version": settings.VERSION,
            "cached_articles_count": total,
            "gainers_count": len(overview.get("gainers", [])),
            "losers_count": len(overview.get("losers", [])),
            "last_updated": overview.get("last_updated")
        }

    return app

app = create_application()
