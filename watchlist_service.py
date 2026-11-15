"""
watchlist_service.py — Sentix Intelligence Platform
------------------------------------------------------
User watchlist management with live news intelligence overlay.

Features:
  - CRUD operations for user stock watchlists (persisted to JSON files)
  - Live sentiment feed filtered to only watchlisted stocks
  - Sector grouping of watchlist news
  - Per-stock news digest (positive / negative article count + articles)
  - get_watchlist_count() helper consumed by news_routes.py (no circular import)

Storage layout:
  user_data/watchlists/<user_id>_watchlist.json

Watchlist JSON schema:
  {
    "user_id": "...",
    "created_at": "...",
    "updated_at": "...",
    "stocks": [
      {
        "symbol": "RELIANCE",
        "name": "Reliance Industries",
        "sector": "Oil & Gas",
        "added_at": "2025-01-01T12:00:00"
      }
    ]
  }
"""

import json
import logging
import os
from datetime import datetime
from pathlib import Path
from typing import Optional

logger = logging.getLogger("sentix.watchlist")

_WATCHLIST_DIR = Path("user_data/watchlists")
_WATCHLIST_DIR.mkdir(parents=True, exist_ok=True)


# ---------------------------------------------------------------------------
# File I/O helpers
# ---------------------------------------------------------------------------

def _watchlist_path(user_id: str) -> Path:
    return _WATCHLIST_DIR / f"{user_id}_watchlist.json"


def _load_watchlist(user_id: str) -> dict:
    path = _watchlist_path(user_id)
    try:
        with open(path) as f:
            return json.load(f)
    except FileNotFoundError:
        return _create_empty_watchlist(user_id)
    except json.JSONDecodeError:
        logger.error(f"Corrupt watchlist JSON for user {user_id} — resetting")
        return _create_empty_watchlist(user_id)


def _create_empty_watchlist(user_id: str) -> dict:
    data = {
        "user_id":    user_id,
        "created_at": datetime.now().isoformat(),
        "updated_at": datetime.now().isoformat(),
        "stocks":     [],
    }
    _save_watchlist(user_id, data)
    return data


def _save_watchlist(user_id: str, data: dict) -> None:
    data["updated_at"] = datetime.now().isoformat()
    with open(_watchlist_path(user_id), "w") as f:
        json.dump(data, f, indent=2)


# ---------------------------------------------------------------------------
# Public CRUD API
# ---------------------------------------------------------------------------

def get_watchlist_count(user_id: str) -> int:
    """Quick count without loading full watchlist — used by news_routes.py."""
    wl = _load_watchlist(user_id)
    return len(wl.get("stocks", []))


def get_stocks(user_id: str) -> list[dict]:
    """Return all stocks in user's watchlist."""
    wl = _load_watchlist(user_id)
    return wl.get("stocks", [])


def add_stock(user_id: str, symbol: str, name: str = "", sector: str = "") -> tuple[bool, str]:
    """
    Add a stock to the watchlist.
    Returns (success: bool, message: str).
    """
    symbol = symbol.strip().upper()
    if not symbol:
        return False, "Symbol is required"

    wl = _load_watchlist(user_id)
    existing = {s["symbol"] for s in wl.get("stocks", [])}

    if symbol in existing:
        return False, f"{symbol} is already in your watchlist"

    if len(wl.get("stocks", [])) >= 50:
        return False, "Watchlist limit reached (50 stocks)"

    wl.setdefault("stocks", []).append({
        "symbol":   symbol,
        "name":     name.strip(),
        "sector":   sector.strip(),
        "added_at": datetime.now().isoformat(),
    })
    _save_watchlist(user_id, wl)
    logger.info(f"Watchlist [{user_id}]: added {symbol}")
    return True, f"{symbol} added to watchlist"


def remove_stock(user_id: str, symbol: str) -> tuple[bool, str]:
    """
    Remove a stock from the watchlist.
    Returns (success: bool, message: str).
    """
    symbol = symbol.strip().upper()
    wl = _load_watchlist(user_id)
    before = len(wl.get("stocks", []))
    wl["stocks"] = [s for s in wl.get("stocks", []) if s["symbol"] != symbol]

    if len(wl["stocks"]) == before:
        return False, f"{symbol} not found in watchlist"

    _save_watchlist(user_id, wl)
    logger.info(f"Watchlist [{user_id}]: removed {symbol}")
    return True, f"{symbol} removed from watchlist"


def clear_watchlist(user_id: str) -> None:
    """Remove all stocks from the watchlist."""
    wl = _load_watchlist(user_id)
    wl["stocks"] = []
    _save_watchlist(user_id, wl)
    logger.info(f"Watchlist [{user_id}]: cleared")


# ---------------------------------------------------------------------------
# News intelligence overlay
# ---------------------------------------------------------------------------

def get_watchlist_news_digest(user_id: str, sector_articles: dict) -> dict:
    """
    Build a full news intelligence digest for the user's watchlist.

    Returns:
    {
      "stocks": [...],                          # All watchlisted stocks with news counts
      "sector_tabs": {                          # News grouped by sector
        "Banking": {
          "positive": [...article dicts],
          "negative": [...article dicts]
        },
        ...
      },
      "per_stock": {                            # Per-symbol news summary
        "HDFCBANK": {
          "positive_count": 3,
          "negative_count": 1,
          "latest_articles": [...],
          "overall_sentiment": "Positive"
        }
      },
      "total_positive": N,
      "total_negative": N,
      "alert_count": N   # stocks with ≥1 negative article
    }
    """
    stocks = get_stocks(user_id)
    if not stocks:
        return _empty_digest()

    watchlist_symbols = {s["symbol"] for s in stocks}

    # ── Per-stock aggregation ─────────────────────────────────────────
    per_stock: dict[str, dict] = {
        sym: {
            "positive_count": 0,
            "negative_count": 0,
            "neutral_count":  0,
            "latest_articles": [],
            "overall_sentiment": "Neutral",
        }
        for sym in watchlist_symbols
    }

    # ── Sector-grouped news tabs ──────────────────────────────────────
    sector_tabs: dict[str, dict] = {}

    total_positive = 0
    total_negative = 0

    for _sector, articles in sector_articles.items():
        for art in articles:
            mentions = art.get("stock_mentions", [])
            # Only include articles where a watchlisted stock is explicitly mentioned
            matched_symbols = [s for s in mentions if s in watchlist_symbols]
            if not matched_symbols:
                continue

            label = art.get("sentiment_label", "Neutral")

            # Build a clean article card for the template
            article_card = {
                "symbol":          matched_symbols[0],
                "all_symbols":     matched_symbols,
                "title":           art.get("title", ""),
                "url":             art.get("url", ""),
                "summary":         art.get("summary", ""),
                "source_name":     art.get("source_name", ""),
                "published_date":  art.get("published_date", ""),
                "sentiment_label": label,
                "sentiment_score": art.get("sentiment_score", 0.0),
                "confidence":      art.get("confidence", 0.0),
                "impact_type":     art.get("impact_type", "Unknown"),
                "reasoning":       art.get("reasoning", ""),
            }

            # Update per-stock data
            for sym in matched_symbols:
                sd = per_stock[sym]
                if label == "Positive":
                    sd["positive_count"] += 1
                    total_positive += 1
                elif label == "Negative":
                    sd["negative_count"] += 1
                    total_negative += 1
                else:
                    sd["neutral_count"] += 1

                # Keep 5 most recent articles per stock
                if len(sd["latest_articles"]) < 5:
                    sd["latest_articles"].append(article_card)

            # Group into sector tabs
            # Use the CSV sector of the FIRST matched watchlist stock
            from sector_service import SYMBOL_TO_SECTOR
            tab_sector = SYMBOL_TO_SECTOR.get(matched_symbols[0], _sector)

            tab = sector_tabs.setdefault(tab_sector, {"positive": [], "negative": [], "neutral": []})

            if label == "Positive" and len(tab["positive"]) < 15:
                tab["positive"].append(article_card)
            elif label == "Negative" and len(tab["negative"]) < 15:
                tab["negative"].append(article_card)
            elif label == "Neutral" and len(tab["neutral"]) < 10:
                tab["neutral"].append(article_card)

    # ── Compute overall per-stock sentiment ───────────────────────────
    for sym, sd in per_stock.items():
        pos = sd["positive_count"]
        neg = sd["negative_count"]
        if pos > neg and pos > 0:
            sd["overall_sentiment"] = "Positive"
        elif neg > pos and neg > 0:
            sd["overall_sentiment"] = "Negative"
        else:
            sd["overall_sentiment"] = "Neutral"

    # ── Sort sector tabs: sectors with negative news first ────────────
    sorted_tabs = dict(
        sorted(
            sector_tabs.items(),
            key=lambda x: len(x[1]["negative"]),
            reverse=True,
        )
    )

    # ── Alert count: watchlist stocks with any negative news ──────────
    alert_count = sum(
        1 for sd in per_stock.values() if sd["negative_count"] > 0
    )

    # ── Enrich stocks list with news counts ───────────────────────────
    enriched_stocks = []
    for stock in stocks:
        sym = stock["symbol"]
        sd  = per_stock.get(sym, {})
        enriched_stocks.append({
            **stock,
            "positive_count":    sd.get("positive_count", 0),
            "negative_count":    sd.get("negative_count", 0),
            "overall_sentiment": sd.get("overall_sentiment", "Neutral"),
            "has_news":          (sd.get("positive_count", 0) + sd.get("negative_count", 0)) > 0,
        })

    # Sort: stocks with news first, then alphabetical
    enriched_stocks.sort(key=lambda x: (-x["positive_count"] - x["negative_count"], x["symbol"]))

    return {
        "stocks":          enriched_stocks,
        "sector_tabs":     sorted_tabs,
        "per_stock":       per_stock,
        "total_positive":  total_positive,
        "total_negative":  total_negative,
        "alert_count":     alert_count,
    }


def _empty_digest() -> dict:
    return {
        "stocks":         [],
        "sector_tabs":    {},
        "per_stock":      {},
        "total_positive": 0,
        "total_negative": 0,
        "alert_count":    0,
    }
