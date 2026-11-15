import os
import json
import logging
from typing import List, Dict, Any, Optional
from pydantic import BaseModel
from fastapi import APIRouter, HTTPException, Depends
from app.core.config import settings

router = APIRouter(prefix="/watchlist", tags=["User Watchlist"])
logger = logging.getLogger("finsentiq.api.watchlist")

WATCHLIST_FILE = "data/watchlists.json"

class WatchlistAddRequest(BaseModel):
    user_id: str = "guest_user"
    symbol: str

class WatchlistResponse(BaseModel):
    user_id: str
    symbols: List[str]

def _load_watchlists() -> Dict[str, List[str]]:
    if os.path.exists(WATCHLIST_FILE):
        try:
            with open(WATCHLIST_FILE, "r") as f:
                return json.load(f)
        except Exception:
            return {}
    return {}

def _save_watchlists(data: Dict[str, List[str]]):
    os.makedirs(os.path.dirname(WATCHLIST_FILE), exist_ok=True)
    with open(WATCHLIST_FILE, "w") as f:
        json.dump(data, f, indent=2)

@router.get("/{user_id}", response_model=WatchlistResponse)
async def get_watchlist(user_id: str):
    data = _load_watchlists()
    return {"user_id": user_id, "symbols": data.get(user_id, [])}

@router.post("/add", response_model=WatchlistResponse)
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

    return {"user_id": req.user_id, "symbols": current}

@router.delete("/remove/{user_id}/{symbol}", response_model=WatchlistResponse)
async def remove_symbol(user_id: str, symbol: str):
    data = _load_watchlists()
    sym = symbol.strip().upper()
    current = data.get(user_id, [])
    if sym in current:
        current.remove(sym)
        data[user_id] = current
        _save_watchlists(data)
    return {"user_id": user_id, "symbols": current}
