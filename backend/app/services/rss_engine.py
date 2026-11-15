import asyncio
import logging
from datetime import datetime, timezone
from typing import List, Dict, Any
import httpx
import feedparser
from bs4 import BeautifulSoup

from app.services.sector_engine import sector_engine
from app.services.sentiment_engine import sentiment_engine, SOURCE_WEIGHTS
from app.services.deduplication import dedup_service
from app.core.store import central_store

logger = logging.getLogger("finsentiq.rss")

# High-quality Indian Financial RSS Feeds
RSS_FEEDS = [
    {"source": "Economic Times", "url": "https://economictimes.indiatimes.com/markets/stocks/rssfeeds/2146842.cms"},
    {"source": "Economic Times", "url": "https://economictimes.indiatimes.com/news/economy/rssfeeds/1373380680.cms"},
    {"source": "Livemint", "url": "https://www.livemint.com/rss/markets"},
    {"source": "Livemint", "url": "https://www.livemint.com/rss/companies"},
    {"source": "Business Standard", "url": "https://www.business-standard.com/rss/markets-106.rss"},
    {"source": "Business Standard", "url": "https://www.business-standard.com/rss/companies-101.rss"},
    {"source": "Moneycontrol", "url": "https://www.moneycontrol.com/rss/marketreports.xml"},
    {"source": "Moneycontrol", "url": "https://www.moneycontrol.com/rss/business.xml"},
    {"source": "Financial Express", "url": "https://www.financialexpress.com/market/feed/"},
    {"source": "NDTV Profit", "url": "https://www.ndtvprofit.com/rss/feed"}
]

def clean_html(raw_html: str) -> str:
    if not raw_html:
        return ""
    if "<" not in raw_html:
        return raw_html.strip()
    soup = BeautifulSoup(raw_html, "html.parser")
    return soup.get_text(separator=" ", strip=True)

class RSSEngine:
    """Async parallel feed processor with zero impact on user request lifecycle."""

    async def fetch_feed(self, client: httpx.AsyncClient, feed_meta: Dict[str, str]) -> List[Dict[str, Any]]:
        source = feed_meta["source"]
        url = feed_meta["url"]
        articles = []
        try:
            resp = await client.get(url, timeout=12.0)
            if resp.status_code == 200:
                parsed = feedparser.parse(resp.text)
                for entry in parsed.entries[:25]:
                    title = clean_html(entry.get("title", ""))
                    link = entry.get("link", "")
                    if not title or not link or dedup_service.is_duplicate(title, link):
                        continue

                    # Extract summary
                    raw_summary = entry.get("summary") or entry.get("description", "")
                    summary = clean_html(raw_summary)

                    # Extract published datetime
                    pub_date = entry.get("published") or entry.get("updated") or datetime.now(timezone.utc).isoformat()
                    # Try converting to ISO
                    try:
                        if hasattr(entry, "published_parsed") and entry.published_parsed:
                            iso_dt = datetime(*entry.published_parsed[:6], tzinfo=timezone.utc).isoformat()
                        else:
                            iso_dt = datetime.now(timezone.utc).isoformat()
                    except Exception:
                        iso_dt = datetime.now(timezone.utc).isoformat()

                    articles.append({
                        "id": f"{source}_{abs(hash(link))}",
                        "title": title,
                        "link": link,
                        "published": pub_date,
                        "published_iso": iso_dt,
                        "source": source,
                        "source_weight": SOURCE_WEIGHTS.get(source, 1.0),
                        "summary": summary[:400] if summary else ""
                    })
        except Exception as e:
            logger.warning(f"Error fetching feed {url}: {e}")
        return articles

    async def ingest_and_process_all(self):
        """
        Background Job:
        1. Async fetch all feeds simultaneously.
        2. Extract symbols & classify sectors.
        3. Score sentiment (Groq batch / parallel).
        4. Calculate decay and build Gainers/Losers.
        5. Atomically update central_store.
        """
        logger.info("Starting background RSS ingestion cycle...")
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) FinSentiq/3.0"}
        async with httpx.AsyncClient(headers=headers, follow_redirects=True) as client:
            tasks = [self.fetch_feed(client, f) for f in RSS_FEEDS]
            results = await asyncio.gather(*tasks)

        raw_articles = [art for sublist in results for art in sublist]
        logger.info(f"Ingested {len(raw_articles)} new unique articles.")

        if not raw_articles:
            logger.info("No new articles discovered this cycle.")
            return

        # Parallel symbol extraction and sector classification
        processed_articles = []
        for art in raw_articles:
            symbols = sector_engine.extract_symbols(art["title"] + " " + art.get("summary", ""))
            sector = sector_engine.classify_sector(art["title"], symbols)
            art["stock_mentions"] = symbols
            art["sector"] = sector
            processed_articles.append(art)

        # Batch sentiment evaluation (limited concurrency to respect Groq rate limits)
        semaphore = asyncio.Semaphore(10)

        async def score_article(a: Dict[str, Any]):
            async with semaphore:
                sentiment = await sentiment_engine.analyze_sentiment(a["title"], a.get("summary"))
                a["sentiment_label"] = sentiment.get("sentiment_label", "Neutral")
                raw_score = sentiment.get("sentiment_score", 0.0)
                a["sentiment_score"] = raw_score
                a["confidence"] = sentiment.get("confidence", 0.8)
                a["impact_type"] = sentiment.get("impact_type", "Unknown")
                a["reasoning"] = sentiment.get("reasoning", "")
                
                # Apply source weight & time decay
                age_hours, decay = sentiment_engine.compute_time_decay(a.get("published_iso"))
                a["age_hours"] = age_hours
                a["decayed_score"] = round(raw_score * a.get("source_weight", 1.0) * decay, 2)
                return a

        scored_articles = await asyncio.gather(*[score_article(a) for a in processed_articles])

        # Group by Sector & Map Stock Mentions
        sector_articles: Dict[str, List[Dict[str, Any]]] = {}
        stock_scores: Dict[str, Dict[str, Any]] = {}

        for a in scored_articles:
            # Determine all relevant sectors for this article
            # 1. Official sectors of mentioned stocks
            article_sectors = set()
            for sym in a.get("stock_mentions", []):
                sym_sec = sector_engine.symbol_to_sector.get(sym)
                if sym_sec and sym_sec != "Broad Market":
                    article_sectors.add(sym_sec)

            # 2. Keyword-classified sector fallback
            classified_sec = a.get("sector")
            if classified_sec and classified_sec != "Broad Market":
                article_sectors.add(classified_sec)

            if not article_sectors:
                article_sectors.add("Broad Market")

            # Store all associated sectors and canonical primary sector
            a["all_sectors"] = sorted(list(article_sectors))
            a["sector"] = a["all_sectors"][0]

            # Index article under every relevant sector
            for sec in article_sectors:
                if sec not in sector_articles:
                    sector_articles[sec] = []
                sector_articles[sec].append(a)

            # Stock level aggregation for gainers/losers
            # STRICT UNIVERSAL GUARANTEE: Stock's sector is ALWAYS its official canonical sector from company.csv
            for sym in a.get("stock_mentions", []):
                actual_sym_sec = sector_engine.symbol_to_sector.get(sym, "Broad Market")
                if sym not in stock_scores:
                    stock_scores[sym] = {
                        "symbol": sym,
                        "positive_score": 0.0,
                        "negative_score": 0.0,
                        "article_count": 0,
                        "sector": actual_sym_sec,
                        "top_article_title": a["title"]
                    }
                score = a["sentiment_score"]
                if score > 0:
                    stock_scores[sym]["positive_score"] += score
                elif score < 0:
                    stock_scores[sym]["negative_score"] += abs(score)
                stock_scores[sym]["article_count"] += 1

        # Build Gainers and Losers
        stocks_list = []
        for sym, d in stock_scores.items():
            net = round(d["positive_score"] - d["negative_score"], 2)
            d["net_score"] = net
            d["sentiment_label"] = "Bullish" if net > 1.5 else "Bearish" if net < -1.5 else "Neutral"
            stocks_list.append(d)

        gainers = sorted([s for s in stocks_list if s["net_score"] > 0], key=lambda x: x["net_score"], reverse=True)[:10]
        losers = sorted([s for s in stocks_list if s["net_score"] < 0], key=lambda x: x["net_score"])[:10]

        # Build Sector Summaries
        sector_summaries = []
        for sec, arts in sector_articles.items():
            scores = [a["sentiment_score"] for a in arts]
            avg_s = round(sum(scores) / len(scores), 2) if scores else 0.0
            pos = sum(1 for s in scores if s > 1.5)
            neg = sum(1 for s in scores if s < -1.5)
            neu = len(scores) - pos - neg
            sector_summaries.append({
                "sector": sec,
                "article_count": len(arts),
                "avg_sentiment": avg_s,
                "positive_count": pos,
                "negative_count": neg,
                "neutral_count": neu,
                "sentiment_label": "Bullish" if avg_s > 1.0 else "Bearish" if avg_s < -1.0 else "Neutral"
            })

        market_summary = {
            "total_articles": len(scored_articles),
            "sectors": sector_summaries,
            "overall_mood": "Bullish" if sum(a["sentiment_score"] for a in scored_articles) > 0 else "Bearish"
        }

        # Atomically update central store
        await central_store.update_all(
            sector_articles=sector_articles,
            gainers_losers={"gainers": gainers, "losers": losers},
            market_summary=market_summary
        )
        logger.info("Background RSS ingestion and Store update finished successfully.")

rss_engine = RSSEngine()
