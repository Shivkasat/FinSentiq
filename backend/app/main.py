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
from app.api.stocks import router as stocks_router
from app.api.summarize import router as summarize_router
from app.api.logs import router as logs_router, log_event
from app.api.auth import router as auth_router
from app.api.copilot import router as copilot_router
from app.api.portfolio import router as portfolio_router
from app.api.divergence import router as divergence_router

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
            log_event("Triggered scheduled background RSS ingestion cycle")
            await rss_engine.ingest_and_process_all()
            log_event("RSS ingestion and sentiment analysis complete")
        except asyncio.CancelledError:
            logger.info("Background feed worker stopped.")
            break
        except Exception as e:
            logger.error(f"Error in background ingestion loop: {e}")
            log_event(f"Ingestion warning: {e}")
            await asyncio.sleep(60)

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Initializing FinSentiq FastAPI Engine...")
    
    # Trigger immediate live RSS feed ingestion on every server startup
    logger.info("Server started: Launching immediate live RSS feed ingestion cycle...")
    log_event("Server boot: Launching immediate live RSS feed ingestion across all financial sources")
    asyncio.create_task(rss_engine.ingest_and_process_all())

    worker_task = asyncio.create_task(periodic_feed_worker())
    log_event(f"Scheduler active: periodic sweep every {settings.FEED_FETCH_INTERVAL_MINUTES}m")

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

    # Register All API Routers
    app.include_router(news_router, prefix=settings.API_V1_STR)
    app.include_router(watchlist_router, prefix=settings.API_V1_STR)
    app.include_router(stocks_router, prefix=settings.API_V1_STR)
    app.include_router(summarize_router, prefix=settings.API_V1_STR)
    app.include_router(logs_router, prefix=settings.API_V1_STR)
    app.include_router(auth_router, prefix=settings.API_V1_STR)
    app.include_router(copilot_router, prefix=settings.API_V1_STR)
    app.include_router(portfolio_router, prefix=settings.API_V1_STR)
    app.include_router(divergence_router, prefix=settings.API_V1_STR)

    @app.get("/", tags=["Root"])
    async def root():
        overview = central_store.get_market_overview()
        total = overview.get("summary", {}).get("total_articles", 0)
        return {
            "name": settings.PROJECT_NAME,
            "version": settings.VERSION,
            "status": "online",
            "cached_articles_count": total,
            "docs_url": "/docs",
            "health_url": "/health",
            "frontend_dashboard": "http://localhost:5173"
        }

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
