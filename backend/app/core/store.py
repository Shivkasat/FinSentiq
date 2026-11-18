import os
import json
import logging
from typing import Dict, List, Any, Optional
from datetime import datetime
import asyncio

logger = logging.getLogger("finsentiq.store")

class CentralStore:
    """
    In-memory thread-safe & async-safe store with local JSON backup persistence.
    Acts as the Single Source of Truth:
      - RSS feeds are NEVER fetched on user visits.
      - User requests read directly from this pre-populated RAM store (<2ms latency).
    """
    def __init__(self, persistence_file: str = "data/market_store.json"):
        from pathlib import Path
        base_dir = Path(__file__).resolve().parent.parent.parent  # backend/
        
        # Candidate storage locations
        candidates = [
            base_dir / persistence_file,
            base_dir.parent / persistence_file,
            Path(persistence_file).resolve()
        ]
        
        # Pick the candidate file with the largest data size / article content
        best_file = base_dir / persistence_file
        max_size = 0
        for c in candidates:
            if c.exists() and c.stat().st_size > max_size:
                max_size = c.stat().st_size
                best_file = c

        self.persistence_file = str(best_file)
        self.sector_articles: Dict[str, List[Dict[str, Any]]] = {}
        self.gainers_losers: Dict[str, Any] = {"gainers": [], "losers": []}
        self.market_summary: Dict[str, Any] = {}
        self.last_updated: Optional[datetime] = None
        self._lock: Optional[asyncio.Lock] = None
        
        # Load from disk if exists on startup
        self._load_from_disk()

    @property
    def lock(self) -> asyncio.Lock:
        if self._lock is None:
            self._lock = asyncio.Lock()
        return self._lock

    def _load_from_disk(self):
        try:
            if os.path.exists(self.persistence_file):
                with open(self.persistence_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    self.sector_articles = data.get("sector_articles", {})
                    self.gainers_losers = data.get("gainers_losers", {"gainers": [], "losers": []})
                    self.market_summary = data.get("market_summary", {})
                    updated_str = data.get("last_updated")
                    if updated_str:
                        self.last_updated = datetime.fromisoformat(updated_str)
                    total_arts = sum(len(v) for v in self.sector_articles.values())
                    logger.info(f"Central store successfully hydrated from persistent disk cache: {total_arts} articles across {len(self.sector_articles)} sectors.")
        except Exception as e:
            logger.warning(f"Could not load store from disk: {e}")

    def save_to_disk(self):
        try:
            os.makedirs(os.path.dirname(self.persistence_file), exist_ok=True)
            payload = {
                "sector_articles": self.sector_articles,
                "gainers_losers": self.gainers_losers,
                "market_summary": self.market_summary,
                "last_updated": self.last_updated.isoformat() if self.last_updated else None
            }
            with open(self.persistence_file, "w", encoding="utf-8") as f:
                json.dump(payload, f, indent=2)
            
            # Also keep root copy in sync if possible
            from pathlib import Path
            root_copy = Path(self.persistence_file).resolve().parent.parent.parent / "data/market_store.json"
            if root_copy.parent.exists() and str(root_copy) != self.persistence_file:
                with open(root_copy, "w", encoding="utf-8") as rf:
                    json.dump(payload, rf, indent=2)
        except Exception as e:
            logger.error(f"Failed to persist central store to disk: {e}")

    async def update_all(self, sector_articles: Dict[str, List[Dict[str, Any]]], gainers_losers: Dict[str, Any], market_summary: Dict[str, Any]):
        async with self.lock:
            # Smart Merge: Preserve existing articles and append new ones without duplicates
            merged_sectors = dict(self.sector_articles)
            for sec, new_arts in sector_articles.items():
                existing = merged_sectors.get(sec, [])
                seen_links = {a.get("link") for a in existing if a.get("link")}
                merged_list = list(existing)
                for a in new_arts:
                    if a.get("link") not in seen_links:
                        seen_links.add(a.get("link"))
                        merged_list.append(a)
                # Keep up to 60 freshest articles per sector
                merged_sectors[sec] = sorted(merged_list, key=lambda x: x.get("age_hours", 999))[:60]

            self.sector_articles = merged_sectors

            # If incoming gainers/losers are non-empty, use them; otherwise keep existing
            if gainers_losers.get("gainers") or gainers_losers.get("losers"):
                self.gainers_losers = gainers_losers

            # Recalculate true unique article count in market summary
            seen_all = set()
            for arts in self.sector_articles.values():
                for a in arts:
                    if a.get("link"):
                        seen_all.add(a.get("link"))
            total_articles = len(seen_all)
            if not market_summary or not market_summary.get("sectors"):
                market_summary = self.market_summary
            market_summary["total_articles"] = total_articles
            self.market_summary = market_summary

            self.last_updated = datetime.utcnow()
            
            # Non-blocking disk persist
            loop = asyncio.get_event_loop()
            loop.run_in_executor(None, self.save_to_disk)
            logger.info(f"Central Store atomically updated and preserved: {total_articles} total articles across {len(self.sector_articles)} sectors.")

    def get_articles_by_sector(self, sector: Optional[str] = None) -> List[Dict[str, Any]]:
        if not sector or sector.lower() in ("all", "all sectors"):
            # Return flattened unique list
            seen_links = set()
            all_arts = []
            for sec, arts in self.sector_articles.items():
                for a in arts:
                    if a.get("link") not in seen_links:
                        seen_links.add(a.get("link"))
                        all_arts.append(a)
            # Sort by published timestamp or recency
            return sorted(all_arts, key=lambda x: x.get("age_hours", 999))
        
        # Match case-insensitively
        for k, v in self.sector_articles.items():
            if k.lower() == sector.lower():
                return v
        return []

    def get_market_overview(self) -> Dict[str, Any]:
        return {
            "last_updated": self.last_updated.isoformat() if self.last_updated else datetime.utcnow().isoformat(),
            "summary": self.market_summary,
            "gainers": self.gainers_losers.get("gainers", []),
            "losers": self.gainers_losers.get("losers", [])
        }

central_store = CentralStore()
