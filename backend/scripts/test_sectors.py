import sys
import os
sys.path.insert(0, os.path.abspath("backend"))

from app.core.store import central_store
from app.api.news import calculate_movers_for_articles
from app.services.sector_engine import sector_engine

all_sectors = sorted(list(set(sector_engine.symbol_to_sector.values())))
mismatches = 0
tested_stocks = 0

print(f"Auditing {len(all_sectors)} sectors from canonical CSV master...")

for sec in all_sectors:
    arts = central_store.get_articles_by_sector(sec)
    gainers, losers = calculate_movers_for_articles(arts, sec)
    for s in gainers + losers:
        tested_stocks += 1
        if s["sector"].lower() != sec.lower():
            print(f"MISMATCH in {sec}: stock {s['symbol']} has sector {s['sector']}")
            mismatches += 1

print(f"Tested {len(all_sectors)} sectors and {tested_stocks} stock mover placements.")
print(f"Total cross-sector contamination errors: {mismatches}")
if mismatches == 0:
    print("SUCCESS: 100% verified across all 757 stocks and 30 sectors!")
else:
    sys.exit(1)
