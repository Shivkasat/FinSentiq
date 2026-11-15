import os
import json
import logging
from typing import List, Dict, Any, Optional
from pydantic import BaseModel
from fastapi import APIRouter, HTTPException
from app.api.stocks import get_stock_quote

router = APIRouter(prefix="/watchlist", tags=["User Watchlist"])
logger = logging.getLogger("finsentiq.api.watchlist")

WATCHLIST_FILE = "backend/data/watchlists.json"

class WatchlistAddRequest(BaseModel):
    user_id: str = "guest_user"
    symbol: str

def _resolve_file() -> str:
    from pathlib import Path
    base = Path(__file__).resolve().parent.parent.parent  # backend/
    target = base / "data" / "watchlists.json"
    os.makedirs(target.parent, exist_ok=True)
    return str(target)

def _load_watchlists() -> Dict[str, List[str]]:
    filepath = _resolve_file()
    if os.path.exists(filepath):
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}
    return {}

def _save_watchlists(data: Dict[str, List[str]]):
    filepath = _resolve_file()
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)

@router.get("/{user_id}")
async def get_watchlist(user_id: str):
    data = _load_watchlists()
    symbols = data.get(user_id, [])
    
    # Enrich with live price & change
    stocks_with_quotes = []
    for sym in symbols:
        try:
            quote = await get_stock_quote(sym)
            stocks_with_quotes.append(quote)
        except Exception:
            stocks_with_quotes.append({
                "symbol": sym,
                "price": 0.0,
                "change": 0.0,
                "percent_change": 0.0,
                "sector": "Broad Market"
            })

    return {
        "user_id": user_id,
        "symbols": symbols,
        "stocks": stocks_with_quotes,
        "total_stocks": len(symbols)
    }

@router.post("/add")
async def add_symbol(req: WatchlistAddRequest):
    data = _load_watchlists()
    sym = req.symbol.strip().upper()
    if not sym:
        raise HTTPException(status_code=400, detail="Symbol cannot be empty")
    
    current = data.get(req.user_id, [])
    if sym not in current:
        current.append(sym)
        data[req.user_id] = current
        _save_watchlists(data)

    return await get_watchlist(req.user_id)

@router.delete("/remove/{user_id}/{symbol}")
async def remove_symbol(user_id: str, symbol: str):
    data = _load_watchlists()
    sym = symbol.strip().upper()
    current = data.get(user_id, [])
    if sym in current:
        current.remove(sym)
        data[user_id] = current
        _save_watchlists(data)

    return await get_watchlist(user_id)
