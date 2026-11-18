import logging
from typing import List, Optional
from pydantic import BaseModel
from fastapi import APIRouter, Query, HTTPException
from app.services.sector_engine import sector_engine
from app.services.market_data import market_data_service
from app.core.store import central_store

router = APIRouter(prefix="/stocks", tags=["Stock Search & Info"])
logger = logging.getLogger("finsentiq.api.stocks")

class StockSearchResult(BaseModel):
    symbol: str
    name: str
    sector: str

@router.get("/search", response_model=List[StockSearchResult])
async def search_stocks(q: str = Query(..., min_length=1, description="Stock ticker symbol or company name")):
    """
    Fast in-memory autocomplete search across 750+ NSE/BSE stocks and company names.
    """
    query = q.strip().lower()
    results = []
    seen = set()

    # 1. Exact symbol match
    for sym in sector_engine.valid_symbols:
        if sym.lower() == query and sym not in seen:
            seen.add(sym)
            sec = sector_engine.symbol_to_sector.get(sym, "Broad Market")
            results.append({"symbol": sym, "name": sym, "sector": sec})

    # 2. Symbol starts with
    for sym in sorted(sector_engine.valid_symbols):
        if sym.lower().startswith(query) and sym not in seen:
            seen.add(sym)
            sec = sector_engine.symbol_to_sector.get(sym, "Broad Market")
            results.append({"symbol": sym, "name": sym, "sector": sec})
            if len(results) >= 15:
                return results

    # 3. Company name match
    for company_name, sym in sector_engine.company_to_symbol.items():
        if query in company_name.lower() and sym not in seen:
            seen.add(sym)
            sec = sector_engine.symbol_to_sector.get(sym, "Broad Market")
            results.append({
                "symbol": sym,
                "name": company_name.title(),
                "sector": sec
            })
            if len(results) >= 20:
                break

    return results

@router.get("/quote/{symbol}")
async def get_stock_quote(symbol: str):
    """
    Returns live market quote with auto-validation for a given stock symbol.
    """
    sym = symbol.strip().upper()
    sec = sector_engine.symbol_to_sector.get(sym)
    if not sec and sym not in sector_engine.valid_symbols:
        raise HTTPException(status_code=404, detail="Stock symbol not found")

    quote = market_data_service.get_stock_price(sym)
    quote["sector"] = sec or "Broad Market"
    return quote

@router.get("/accuracy")
async def get_prediction_accuracy():
    """
    Returns empirical signal verification metrics (Win Rate, Alpha Spread, Precision@K).
    """
    overview = central_store.get_market_overview()
    gainers = overview.get("gainers", [])
    losers = overview.get("losers", [])
    return market_data_service.evaluate_signals_accuracy(gainers, losers)
