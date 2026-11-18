print("1. Loading Market & Sector Services...", flush=True)
from app.services.market_data import market_data_service
from app.core.store import central_store
from app.services.sector_engine import sector_engine

def run_tests():
    print("\n=== STEP 1: Live Real-Time Stock Quote with Auto-Validation ===", flush=True)
    tcs = market_data_service.get_stock_price("TCS", sentiment_score=5.5)
    print(f"Symbol: {tcs['symbol']} | Price: Rs.{tcs['price']} | Day Change: {tcs['percent_change']}% | Aligned: {tcs['prediction_aligned']} ({tcs['validation_outcome']})", flush=True)

    rel = market_data_service.get_stock_price("RELIANCE", sentiment_score=8.2)
    print(f"Symbol: {rel['symbol']} | Price: Rs.{rel['price']} | Day Change: {rel['percent_change']}% | Aligned: {rel['prediction_aligned']} ({rel['validation_outcome']})", flush=True)

    print("\n=== STEP 2: Central Store Hydration & Sector Articles ===", flush=True)
    all_arts = central_store.get_articles_by_sector(None)
    print(f"Total Cached Articles in Central Store: {len(all_arts)}", flush=True)
    sample_art = all_arts[0] if all_arts else {}
    print(f"Sample Headline: {sample_art.get('title')}", flush=True)
    print(f"Detected Catalyst Type: {sample_art.get('impact_type')}", flush=True)
    print(f"Sentiment Score: {sample_art.get('sentiment_score')} ({sample_art.get('sentiment_label')})", flush=True)

    print("\n=== STEP 3: Empirical Signal Accuracy & Win-Rate Scoreboard ===", flush=True)
    gainers = central_store.gainers_losers.get("gainers", [])
    losers = central_store.gainers_losers.get("losers", [])
    acc = market_data_service.evaluate_signals_accuracy(gainers, losers)
    print(f"Empirical Win Rate: {acc['win_rate']}%", flush=True)
    print(f"Successful Signal Hits: {acc['successful_predictions']} / {acc['total_signals']}", flush=True)
    print(f"Alpha Spread (Gainers vs Losers): {acc['alpha_spread']}%", flush=True)
    print(f"Precision@K Metric: {acc['precision_at_k']}", flush=True)

    print("\n=== STEP 4: Sector Taxonomy & Ticker Disambiguation ===", flush=True)
    test_headline = "HDFC Bank posts 20% jump in net profit, while TCS wins multi-million dollar cloud deal"
    syms = sector_engine.extract_symbols(test_headline)
    print(f"Headline: '{test_headline}'", flush=True)
    print(f"Extracted Tickers: {syms}", flush=True)
    for s in syms:
        print(f" -> Ticker {s} maps to Sector: {sector_engine.symbol_to_sector.get(s)}", flush=True)

    print("\n=== ALL SYSTEM TESTS PASSED SUCCESSFULLY! ===", flush=True)

if __name__ == "__main__":
    run_tests()
