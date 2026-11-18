"""
divergence.py — FinSentiq Smart Divergence & Mispricing Radar API
-------------------------------------------------------------------
Exposes institutional-grade anomaly detection endpoints:
  - 4-Quadrant radar classification
  - Real-time disconnect index
  - Actionable trade playbooks (Dip-Buy, Bull Trap Short, Breakout Momentum)
"""

import logging
from typing import Dict, Any, Optional
from fastapi import APIRouter, HTTPException, Query

from app.services.divergence_engine import divergence_engine
from app.services.market_data import market_data_service
from app.services.sector_engine import sector_engine

logger = logging.getLogger("finsentiq.api.divergence")

router = APIRouter(prefix="/divergence", tags=["Divergence Radar"])

@router.get("/radar", summary="Get institutional 4-quadrant divergence radar")
async def get_divergence_radar():
    """
    Returns live price vs sentiment disconnect anomalies classified into:
      1. Zone 1: Accumulation / Institutional Dip-Buy
      2. Zone 2: Distribution / Retail Bull Trap Danger
      3. Zone 3: Momentum Confluence Breakout
      4. Zone 4: Confirmed Capitulation Breakdown
    """
    try:
        radar_data = divergence_engine.scan_radar()
        return {
            "status": "success",
            "data": radar_data
        }
    except Exception as e:
        logger.error(f"Error executing divergence radar scan: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/stock/{symbol}", summary="Inspect divergence metrics for a single stock")
async def get_stock_divergence(symbol: str):
    sym = symbol.strip().upper()
    if sym not in sector_engine.valid_symbols:
        raise HTTPException(status_code=404, detail=f"Stock symbol '{sym}' not recognized in NSE/BSE coverage universe.")

    radar = divergence_engine.scan_radar()
    all_items = []
    for q in radar["quadrants"].values():
        all_items.extend(q.get("items", []))

    match = next((item for item in all_items if item["symbol"] == sym), None)
    if not match:
        # Stock is in equilibrium or neutral zone
        quote = market_data_service.get_stock_price(sym)
        sector = sector_engine.symbol_to_sector.get(sym, "Broad Market")
        return {
            "status": "success",
            "data": {
                "symbol": sym,
                "sector": sector,
                "price": quote["price"],
                "percent_change": quote["percent_change"],
                "sentiment_score": 0.0,
                "sentiment_label": "Neutral",
                "divergence_score": round(-quote["percent_change"] * 2, 2),
                "quadrant_id": "EQUILIBRIUM",
                "quadrant_label": "Price-Catalyst Equilibrium",
                "action_code": "HOLD_NEUTRAL",
                "action_description": "Asset is currently pricing in fair value with no significant news anomaly.",
                "conviction": "LOW",
                "rebound_target_pct": 0.0,
                "trailing_stop_pct": 1.5,
                "catalyst_headline": "No abnormal sentiment disconnect observed",
                "catalyst_link": "#",
                "catalyst_type": "Neutral",
                "is_single_stock": False
            }
        }

    return {
        "status": "success",
        "data": match
    }
