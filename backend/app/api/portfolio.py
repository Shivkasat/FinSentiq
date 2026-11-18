"""
portfolio.py — FinSentiq Portfolio Risk Scanner
-------------------------------------------------
Scans user holdings against real-time news catalysts,
quantifies exposure risks, and delivers actionable mitigation alerts.
"""

import logging
from typing import List, Dict, Any, Optional
from pydantic import BaseModel
from fastapi import APIRouter, HTTPException
from app.core.store import central_store
from app.services.market_data import market_data_service
from app.services.sector_engine import sector_engine

router = APIRouter(prefix="/portfolio", tags=["Portfolio Risk Scanner"])
logger = logging.getLogger("finsentiq.api.portfolio")

class HoldingItem(BaseModel):
    symbol: str
    quantity: int = 10
    buy_price: float = 0.0

class PortfolioScanRequest(BaseModel):
    holdings: List[HoldingItem]
    user_id: Optional[str] = "guest_user"

class ScannedHolding(BaseModel):
    symbol: str
    sector: str
    quantity: int
    buy_price: float
    current_price: float
    invested_value: float
    current_value: float
    pnl_amount: float
    pnl_percent: float
    article_count: int
    sentiment_score: float
    sentiment_label: str
    risk_level: str
    primary_catalyst: Optional[str] = None
    catalyst_headline: Optional[str] = None
    catalyst_link: Optional[str] = None

class PortfolioScanResponse(BaseModel):
    total_invested: float
    total_current: float
    total_pnl: float
    total_pnl_percent: float
    portfolio_sentiment_score: float
    overall_risk_rating: str
    actionable_summary: str
    scanned_holdings: List[ScannedHolding]
    flagged_risk_count: int

@router.post("/scan", response_model=PortfolioScanResponse)
def scan_portfolio(req: PortfolioScanRequest):
    if not req.holdings:
        raise HTTPException(status_code=400, detail="Holdings list cannot be empty.")

    all_articles = central_store.get_articles_by_sector(None)
    scanned_list: List[ScannedHolding] = []
    
    total_invested = 0.0
    total_current = 0.0
    weighted_sentiment_sum = 0.0
    flagged_risks = 0

    for h in req.holdings:
        sym = h.symbol.strip().upper()
        sec = sector_engine.symbol_to_sector.get(sym, "Broad Market")
        
        # Match news articles for this ticker
        related = [
            a for a in all_articles
            if sym in a.get("stock_mentions", []) or sym.lower() in a.get("title", "").lower()
        ]

        scores = [a.get("sentiment_score", 0.0) for a in related]
        avg_score = round(sum(scores) / len(scores), 2) if scores else 0.0
        
        # Get live reference quote
        quote = market_data_service.get_stock_price(sym, sentiment_score=avg_score)
        curr_price = quote["price"]
        buy_p = h.buy_price if h.buy_price > 0 else round(curr_price * 0.96, 2)

        inv_val = round(buy_p * h.quantity, 2)
        cur_val = round(curr_price * h.quantity, 2)
        pnl_amt = round(cur_val - inv_val, 2)
        pnl_pct = round((pnl_amt / inv_val * 100), 2) if inv_val > 0 else 0.0

        total_invested += inv_val
        total_current += cur_val
        weighted_sentiment_sum += avg_score * cur_val

        # Risk classification
        if avg_score < -2.5:
            risk = "Severe Headwind Alert"
            flagged_risks += 1
        elif avg_score < -0.8:
            risk = "Moderate Caution"
            flagged_risks += 1
        elif avg_score > 2.0:
            risk = "Bullish Catalyst"
        else:
            risk = "Neutral"

        # Identify most impactful article
        top_art = None
        if related:
            sorted_by_abs = sorted(related, key=lambda a: abs(a.get("sentiment_score", 0.0)), reverse=True)
            top_art = sorted_by_abs[0]

        sent_lbl = "Bullish" if avg_score > 1.0 else "Bearish" if avg_score < -1.0 else "Neutral"

        scanned_list.append(ScannedHolding(
            symbol=sym,
            sector=sec,
            quantity=h.quantity,
            buy_price=buy_p,
            current_price=curr_price,
            invested_value=inv_val,
            current_value=cur_val,
            pnl_amount=pnl_amt,
            pnl_percent=pnl_pct,
            article_count=len(related),
            sentiment_score=avg_score,
            sentiment_label=sent_lbl,
            risk_level=risk,
            primary_catalyst=top_art.get("impact_type") if top_art else "No Major Catalyst",
            catalyst_headline=top_art.get("title") if top_art else "No immediate high-severity news detected",
            catalyst_link=top_art.get("link") if top_art else None
        ))

    overall_pnl = round(total_current - total_invested, 2)
    overall_pnl_pct = round((overall_pnl / total_invested * 100), 2) if total_invested > 0 else 0.0
    overall_sent = round(weighted_sentiment_sum / max(1.0, total_current), 2)

    if flagged_risks >= 2 or overall_sent < -1.5:
        risk_rating = "Elevated Risk Detected"
        actionable_summary = f"{flagged_risks} holding(s) face breaking bearish news flow or regulatory caution. Review trailing stops."
    elif overall_sent > 1.5:
        risk_rating = "Bullish Tailwinds (Low Risk)"
        actionable_summary = "Portfolio supported by strong positive earnings catalysts and favorable sector momentum."
    else:
        risk_rating = "Balanced / Neutral Exposure"
        actionable_summary = "News sentiment is stable across holdings with limited directional threat."

    return PortfolioScanResponse(
        total_invested=round(total_invested, 2),
        total_current=round(total_current, 2),
        total_pnl=overall_pnl,
        total_pnl_percent=overall_pnl_pct,
        portfolio_sentiment_score=overall_sent,
        overall_risk_rating=risk_rating,
        actionable_summary=actionable_summary,
        scanned_holdings=scanned_list,
        flagged_risk_count=flagged_risks
    )

@router.get("/sample", response_model=PortfolioScanResponse)
def get_sample_portfolio_scan():
    """Generates an instant demo scan of a typical diversified Indian equity portfolio."""
    sample_holdings = [
        HoldingItem(symbol="RELIANCE", quantity=15, buy_price=1240.0),
        HoldingItem(symbol="HDFCBANK", quantity=25, buy_price=1720.0),
        HoldingItem(symbol="TCS", quantity=10, buy_price=3850.0),
        HoldingItem(symbol="TATAMOTORS", quantity=30, buy_price=795.0),
        HoldingItem(symbol="TATASTEEL", quantity=100, buy_price=142.0)
    ]
    return scan_portfolio(PortfolioScanRequest(holdings=sample_holdings))
