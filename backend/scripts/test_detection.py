from app.services.sector_engine import sector_engine

test_cases = [
    "Indian economy grows at 7 percent in Q3",
    "Bank credit growth slows down this quarter",
    "Idea behind new budget explained by finance minister",
    "Steel prices drop in global market",
    "Gold prices hit record high in domestic bullion trade",
    "Top stocks to watch today: Senco Gold, Adani Enterprises, BSE, Cipla shares in focus",
    "Tata Motors signs Rs 2000 cr EV bus order with state govt"
]

for t in test_cases:
    syms = sector_engine.extract_symbols(t)
    print(f"Input: '{t}'")
    print(f"  -> Extracted: {syms}\n")
