import sys
import json
import os
from pathlib import Path

# Add backend to path
sys.path.insert(0, os.path.abspath("."))
sys.path.insert(0, os.path.abspath("backend"))
from app.services.sector_engine import sector_engine
from app.services.sentiment_engine import sentiment_engine

candidates = [
    Path("data/market_store.json"),
    Path("backend/data/market_store.json"),
    Path("../data/market_store.json")
]

source_file = None
max_articles = 0
best_data = None

for c in candidates:
    if c.exists():
        try:
            with open(c, "r", encoding="utf-8") as f:
                d = json.load(f)
                count = sum(len(arts) for arts in d.get("sector_articles", {}).values())
                if count > max_articles:
                    max_articles = count
                    source_file = c
                    best_data = d
        except Exception:
            pass

print(f"Selected richest source: {source_file} with {max_articles} total sector entries")
data = best_data

# Extract all unique articles
seen_links = set()
unique_articles = []
for sec, arts in data.get("sector_articles", {}).items():
    for a in arts:
        link = a.get("link")
        if link not in seen_links:
            seen_links.add(link)
            unique_articles.append(a)

print(f"Total unique raw articles to process: {len(unique_articles)}")

# Re-process each article: fix symbols, fix sectors, detect roundups
new_sector_articles = {}
stock_scores = {}
roundup_count = 0
single_catalyst_count = 0

for a in unique_articles:
    title_text = a.get("title", "") + " " + a.get("summary", "")
    meta = sector_engine.extract_symbols_with_metadata(title_text, title=a.get("title", ""))
    
    symbols = meta["symbols"]
    is_roundup = meta["is_roundup"]
    is_single = meta["is_single_stock"]
    primary_sym = meta["primary_symbol"]

    a["stock_mentions"] = symbols
    a["is_roundup"] = is_roundup
    a["is_single_stock"] = is_single
    a["primary_symbol"] = primary_sym

    # Re-evaluate with contextual financial sentiment engine
    sent = sentiment_engine.lexicon_score(title_text)
    a["sentiment_label"] = sent["sentiment_label"]
    a["sentiment_score"] = sent["sentiment_score"]
    a["impact_type"] = sent["impact_type"]
    a["reasoning"] = sent["reasoning"]

    if is_roundup:
        roundup_count += 1
    elif is_single:
        single_catalyst_count += 1

    # Collect all sectors this article belongs to based on mentioned stocks
    article_sectors = set()
    for sym in symbols:
        sym_sec = sector_engine.symbol_to_sector.get(sym)
        if sym_sec and sym_sec != "Broad Market":
            article_sectors.add(sym_sec)

    # Keyword fallback
    keyword_sec = sector_engine.classify_sector(a.get("title", ""), symbols)
    if keyword_sec and keyword_sec != "Broad Market":
        article_sectors.add(keyword_sec)

    if not article_sectors:
        article_sectors.add("Broad Market")

    a["all_sectors"] = sorted(list(article_sectors))
    a["sector"] = a["all_sectors"][0]

    # Add to each sector
    for s in article_sectors:
        if s not in new_sector_articles:
            new_sector_articles[s] = []
        new_sector_articles[s].append(a)

    # STRICT ACCURACY GUARANTEE: Exclude generic market roundup listicles from contaminating stock sentiment!
    if is_roundup:
        continue

    # Pure company catalysts (single stock) get 1.25x high-conviction multiplier
    weight_mult = 1.25 if is_single else 1.0

    for sym in symbols:
        canonical_sector = sector_engine.symbol_to_sector.get(sym, "Broad Market")
        if sym not in stock_scores:
            stock_scores[sym] = {
                "symbol": sym,
                "positive_score": 0.0,
                "negative_score": 0.0,
                "article_count": 0,
                "sector": canonical_sector,
                "top_article_title": a.get("title", "")
            }
        score = a.get("sentiment_score", 0.0) * weight_mult
        if score > 0:
            stock_scores[sym]["positive_score"] += score
        elif score < 0:
            stock_scores[sym]["negative_score"] += abs(score)
        stock_scores[sym]["article_count"] += 1

stocks_list = []
for sym, d in stock_scores.items():
    net = round(d["positive_score"] - d["negative_score"], 2)
    d["net_score"] = net
    d["sentiment_label"] = "Bullish" if net > 1.5 else "Bearish" if net < -1.5 else "Neutral"
    stocks_list.append(d)

gainers = sorted([s for s in stocks_list if s["net_score"] > 0], key=lambda x: x["net_score"], reverse=True)[:10]
losers = sorted([s for s in stocks_list if s["net_score"] < 0], key=lambda x: x["net_score"])[:10]

sector_summaries = []
for sec, arts in new_sector_articles.items():
    scores = [a.get("sentiment_score", 0.0) for a in arts]
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

data["sector_articles"] = new_sector_articles
data["gainers_losers"] = {"gainers": gainers, "losers": losers}
if "market_summary" not in data:
    data["market_summary"] = {}
data["market_summary"]["sectors"] = sorted(sector_summaries, key=lambda x: x["article_count"], reverse=True)
data["market_summary"]["total_articles"] = len(unique_articles)

# Write to both locations using canonical absolute paths
canonical_paths = [
    Path(r"C:\Sentix\data\market_store.json"),
    Path(r"C:\Sentix\backend\data\market_store.json")
]

for dest in canonical_paths:
    dest.parent.mkdir(parents=True, exist_ok=True)
    with open(dest, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
    print(f"Saved synchronized store to {dest.resolve()}")

print(f"Identified {roundup_count} generic roundups (cleanly isolated from stock sentiment).")
print(f"Identified {single_catalyst_count} pure single-stock catalysts.")
print("--- CLEAN TOP GAINERS ---")
for g in gainers:
    print(f"  {g['symbol']} | Sector: {g['sector']} | Score: {g['net_score']} | Count: {g['article_count']}")
print("--- CLEAN TOP LOSERS ---")
for l in losers:
    print(f"  {l['symbol']} | Sector: {l['sector']} | Score: {l['net_score']} | Count: {l['article_count']}")
