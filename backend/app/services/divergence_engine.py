"""
divergence_engine.py — FinSentiq Smart Divergence & Mispricing Radar Engine
----------------------------------------------------------------------------
Detects institutional price-sentiment disconnects across NSE/BSE equities.
Identifies:
  1. Zone 1: Accumulation / Institutional Dip-Buy (Bullish News + Lagging Price)
  2. Zone 2: Distribution / Retail Trap (Bearish News + Artificial Green Price)
  3. Zone 3: High-Conviction Momentum Confluence (Bullish News + Strong Breakout)
  4. Zone 4: Confirmed Capitulation (Bearish News + Strong Selloff)
"""

import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone

from app.core.store import central_store
from app.services.market_data import market_data_service
from app.services.sector_engine import sector_engine, FALSE_POSITIVE_SYMBOLS

logger = logging.getLogger("finsentiq.divergence")

class DivergenceRadarEngine:
    def scan_radar(self) -> Dict[str, Any]:
        """
        Scans all actively monitored equities with verified news catalysts,
        evaluates price vs sentiment divergence, and classifies them into 4 actionable quadrants.
        """
        all_articles = central_store.get_articles_by_sector("all")
        overview = central_store.get_market_overview()
        gainers = overview.get("gainers", [])
        losers = overview.get("losers", [])

        # Map each stock to its best (most relevant / single-stock) catalyst article
        stock_catalysts: Dict[str, Dict[str, Any]] = {}
        for a in all_articles:
            if a.get("is_roundup", False):
                continue
            for sym in a.get("stock_mentions", []):
                sym = sym.strip().upper()
                if not sym or sym in FALSE_POSITIVE_SYMBOLS:
                    continue
                # Prefer pure single-stock catalysts
                current_best = stock_catalysts.get(sym)
                if not current_best or (a.get("is_single_stock") and not current_best.get("is_single_stock")):
                    stock_catalysts[sym] = a

        # Tracked universe from gainers, losers, and stock catalysts
        universe_symbols = set(stock_catalysts.keys())
        for g in gainers:
            universe_symbols.add(g.get("symbol", "").upper())
        for l in losers:
            universe_symbols.add(l.get("symbol", "").upper())

        # Discard invalid or generic symbols
        universe_symbols = {s for s in universe_symbols if s and s in sector_engine.valid_symbols and s not in FALSE_POSITIVE_SYMBOLS}

        anomalies: List[Dict[str, Any]] = []

        for sym in universe_symbols:
            # Determine sentiment score
            catalyst_art = stock_catalysts.get(sym)
            sector = sector_engine.symbol_to_sector.get(sym, "Broad Market")
            
            # Find in gainers / losers if available
            g_match = next((g for g in gainers if g.get("symbol", "").upper() == sym), None)
            l_match = next((l for l in losers if l.get("symbol", "").upper() == sym), None)

            if g_match:
                sentiment_score = g_match.get("net_score", 4.0)
            elif l_match:
                sentiment_score = l_match.get("net_score", -4.0)
            elif catalyst_art:
                sentiment_score = catalyst_art.get("sentiment_score", 0.0)
            else:
                continue

            if abs(sentiment_score) < 1.0:
                continue  # Ignore neutral/noise stocks

            # Fetch independent market price quote (evaluating true market response vs sentiment)
            quote = market_data_service.get_stock_price(sym)
            price = quote.get("price", 100.0)
            percent_change = quote.get("percent_change", 0.0)

            # Divergence formula: (Sentiment * 10) - (Price Return % * 2)
            divergence_score = round((sentiment_score * 10) - (percent_change * 2), 2)
            abs_divergence = abs(divergence_score)

            # Quadrant Classification
            quadrant_id = None
            quadrant_label = None
            action_code = None
            action_description = None
            rebound_target_pct = 0.0
            trailing_stop_pct = 1.5

            if sentiment_score >= 2.5 and percent_change <= -0.1:
                # ZONE 1: Accumulation / Institutional Dip-Buy
                quadrant_id = "ZONE_1_ACCUMULATION"
                quadrant_label = "Accumulation / Dip-Buy"
                action_code = "STRONG_BUY_DIP"
                action_description = "Institutional Dip-Buy Opportunity. Catalyst positive, temporary price lag."
                rebound_target_pct = round(abs(percent_change) + (sentiment_score * 0.75), 2)
                trailing_stop_pct = round(max(1.2, abs(percent_change) * 0.7), 2)

            elif sentiment_score <= -2.0 and percent_change >= 0.1:
                # ZONE 2: Distribution / Retail Bull Trap Danger
                quadrant_id = "ZONE_2_DISTRIBUTION"
                quadrant_label = "Distribution / Bull Trap"
                action_code = "EXIT_TRAP_SHORT"
                action_description = "Retail Bull Trap Warning. Severe negative catalyst masked by temporary rally."
                rebound_target_pct = round(-(percent_change + abs(sentiment_score) * 0.75), 2)
                trailing_stop_pct = round(max(1.5, percent_change * 0.8), 2)

            elif sentiment_score >= 2.5 and percent_change >= 0.6:
                # ZONE 3: Momentum Confluence Breakout
                quadrant_id = "ZONE_3_MOMENTUM"
                quadrant_label = "Momentum Breakout"
                action_code = "RIDE_MOMENTUM"
                action_description = "Bullish Catalyst confirmed by heavy institutional buying surge."
                rebound_target_pct = round(percent_change * 1.5, 2)
                trailing_stop_pct = 1.8

            elif sentiment_score <= -2.0 and percent_change <= -0.6:
                # ZONE 4: Confirmed Capitulation Breakdown
                quadrant_id = "ZONE_4_CAPITULATION"
                quadrant_label = "Confirmed Capitulation"
                action_code = "SHORT_BREAKDOWN"
                action_description = "Bearish Catalyst confirmed by aggressive institutional distribution."
                rebound_target_pct = round(percent_change * 1.4, 2)
                trailing_stop_pct = 1.6

            if not quadrant_id:
                continue

            # Conviction Rating
            if abs(sentiment_score) >= 7.0 and (quadrant_id in ("ZONE_1_ACCUMULATION", "ZONE_2_DISTRIBUTION")):
                conviction = "VERY HIGH"
            elif abs(sentiment_score) >= 4.5:
                conviction = "HIGH"
            else:
                conviction = "MODERATE"

            headline = catalyst_art.get("title", f"Institutional activity and catalyst tracked for {sym}") if catalyst_art else f"Order book and trading volumes shift for {sym}"
            link = catalyst_art.get("link", "#") if catalyst_art else "#"
            impact_type = catalyst_art.get("impact_type", "Corporate Action") if catalyst_art else "Market Flow"
            is_single = catalyst_art.get("is_single_stock", True) if catalyst_art else True

            anomalies.append({
                "symbol": sym,
                "sector": sector,
                "price": price,
                "percent_change": percent_change,
                "sentiment_score": round(sentiment_score, 2),
                "sentiment_label": "Bullish" if sentiment_score > 0 else "Bearish",
                "divergence_score": divergence_score,
                "abs_divergence": abs_divergence,
                "quadrant_id": quadrant_id,
                "quadrant_label": quadrant_label,
                "action_code": action_code,
                "action_description": action_description,
                "conviction": conviction,
                "rebound_target_pct": rebound_target_pct,
                "trailing_stop_pct": trailing_stop_pct,
                "catalyst_headline": headline,
                "catalyst_link": link,
                "catalyst_type": impact_type,
                "is_single_stock": is_single,
                "detected_at": datetime.now(timezone.utc).isoformat()
            })

        # Sort anomalies by greatest divergence magnitude
        anomalies.sort(key=lambda x: x["abs_divergence"], reverse=True)

        zone_1 = [a for a in anomalies if a["quadrant_id"] == "ZONE_1_ACCUMULATION"]
        zone_2 = [a for a in anomalies if a["quadrant_id"] == "ZONE_2_DISTRIBUTION"]
        zone_3 = [a for a in anomalies if a["quadrant_id"] == "ZONE_3_MOMENTUM"]
        zone_4 = [a for a in anomalies if a["quadrant_id"] == "ZONE_4_CAPITULATION"]

        # Market Disconnect Index: average divergence intensity
        avg_disconnect = round(sum(a["abs_divergence"] for a in anomalies) / max(1, len(anomalies)), 1)

        return {
            "total_anomalies": len(anomalies),
            "market_disconnect_index": avg_disconnect,
            "quadrants": {
                "zone_1_accumulation": {
                    "label": "Accumulation / Dip-Buy Opportunities",
                    "count": len(zone_1),
                    "items": zone_1
                },
                "zone_2_distribution": {
                    "label": "Distribution / Bull Trap Danger",
                    "count": len(zone_2),
                    "items": zone_2
                },
                "zone_3_momentum": {
                    "label": "Momentum Breakout Confluence",
                    "count": len(zone_3),
                    "items": zone_3
                },
                "zone_4_capitulation": {
                    "label": "Confirmed Capitulation Breakdown",
                    "count": len(zone_4),
                    "items": zone_4
                }
            },
            "top_mispricings": anomalies[:6],
            "last_scan": datetime.now(timezone.utc).isoformat()
        }

divergence_engine = DivergenceRadarEngine()
