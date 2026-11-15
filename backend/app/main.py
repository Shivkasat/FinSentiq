import logging
import asyncio
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from apscheduler.schedulers.asyncio import AsyncIOScheduler

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

scheduler = AsyncIOScheduler()

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application Lifespan Events:
    - On Startup: Start background scheduler for periodic RSS ingestion.
    - If store is empty, trigger initial asynchronous ingestion worker.
    - On Shutdown: Cleanly shut down scheduler.
    """
    logger.info("Initializing FinSentiq FastAPI Engine...")
    
    # Check if central store has articles, if not trigger initial ingest
    overview = central_store.get_market_overview()
    if not overview.get("summary") or overview["summary"].get("total_articles", 0) == 0:
        logger.info("Central store is cold. Triggering initial ingestion task...")
        asyncio.create_task(rss_engine.ingest_and_process_all())

    # Schedule background ingestion every X minutes
    scheduler.add_job(
        rss_engine.ingest_and_process_all,
        "interval",
        minutes=settings.FEED_FETCH_INTERVAL_MINUTES,
        id="rss_ingest_job"
    )
    scheduler.start()
    logger.info(f"Background Ingestion Job scheduled every {settings.FEED_FETCH_INTERVAL_MINUTES} minutes.")

    yield

    logger.info("Shutting down FinSentiq Engine...")
    scheduler.shutdown(wait=False)

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
        allow_origins=["*"],  # Production: configure explicitly via settings.CORS_ORIGINS
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
            "last_updated": overview.get("last_updated")
        }

    return app

app = create_application()
