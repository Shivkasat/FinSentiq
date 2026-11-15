"""
sector_service.py — Sentix Intelligence Platform
-------------------------------------------------
Sector classification and stock-symbol extraction engine.

Design goals:
  - Single source of truth for all sector ↔ company ↔ symbol mappings
  - Zero-redundancy CSV loading (loaded once at import, shared via module state)
  - Weighted scoring: company name match > symbol match > generic keyword match
  - Short-symbol false-positive guard (e.g., "IT", "IN", "AM" filtered out)
  - Context-aware extraction: stock mention only valid when financial context present
"""

import re
import csv
import logging
from pathlib import Path
from collections import defaultdict
from typing import Optional

logger = logging.getLogger("sentix.sector")

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_CSV_PATH = Path("company.csv")

# Tokens that look like symbols but are not (common English words / abbreviations)
_SYMBOL_FALSE_POSITIVES = frozenset({
    "IT", "AM", "PM", "IN", "ON", "AT", "TO", "OR", "AN", "AS", "BE",
    "IS", "DO", "GO", "BY", "IF", "NO", "SO", "UP", "US", "UK", "EU",
    "FY", "YY", "QQ", "MF", "PE", "PB", "CF"
})

# Article must contain at least one of these to qualify as a stock-related piece
_FINANCIAL_CONTEXT_TOKENS = frozenset({
    "share", "stock", "equity", "bse", "nse", "sensex", "nifty",
    "market", "trading", "investor", "price", "gains", "falls",
    "q1", "q2", "q3", "q4", "earnings", "profit", "loss", "revenue",
    "crore", "lakh", "billion", "ipo", "dividend", "listing", "results",
    "buyback", "fundraise", "stake", "shareholding", "bonus", "split"
})


# ---------------------------------------------------------------------------
# Sector taxonomy
# ---------------------------------------------------------------------------

SECTOR_TAXONOMY: dict[str, dict] = {
    "Banking": {
        "companies": [
            "hdfc bank", "icici bank", "sbi", "state bank", "axis bank",
            "kotak mahindra", "indusind bank", "federal bank", "yes bank",
            "idfc first bank", "rbl bank", "bandhan bank", "punjab national bank",
            "pnb", "bank of baroda", "bob", "canara bank", "union bank",
            "indian bank", "central bank", "bank of india",
        ],
        "keywords": [
            "bank", "banking", "loans", "deposits", "npa", "credit", "lending",
            "borrowing", "casa", "net interest margin", "nim", "advances",
            "asset quality", "retail banking", "slippage", "provisioning",
        ],
        "symbols": [
            "HDFCBANK", "ICICIBANK", "SBIN", "AXISBANK", "KOTAKBANK",
            "INDUSINDBK", "FEDERALBNK", "YESBANK", "IDFCFIRSTB", "RBLBANK",
            "BANDHANBNK", "PNB", "BANKBARODA", "CANBK", "UNIONBANK", "INDIANB",
        ],
        "weights": {"company": 15, "symbol": 8, "keyword": 3},
    },
    "Financial Services": {
        "companies": [
            "bajaj finance", "bajaj finserv", "hdfc life", "sbi life",
            "icici prudential", "lic", "life insurance", "cholamandalam",
            "muthoot finance", "shriram finance", "piramal", "manappuram",
        ],
        "keywords": [
            "nbfc", "non banking", "financial services", "insurance",
            "life insurance", "mutual fund", "amc", "housing finance",
            "microfinance", "gold loan", "aum", "premium", "claim ratio",
        ],
        "symbols": [
            "BAJFINANCE", "BAJAJFINSV", "HDFCLIFE", "SBILIFE", "ICICIPRULI",
            "LICI", "CHOLAFIN", "MUTHOOTFIN", "SHRIRAMFIN", "PIRAMAL",
            "MANAPPURAM",
        ],
        "weights": {"company": 15, "symbol": 8, "keyword": 3},
    },
    "IT": {
        "companies": [
            "tcs", "tata consultancy", "infosys", "wipro", "hcl tech",
            "tech mahindra", "l&t technology", "ltts", "persistent",
            "coforge", "ltimindtree", "happiest minds", "mastek", "mphasis",
            "hexaware", "kpit technologies",
        ],
        "keywords": [
            "software", "technology", "information technology", "digital",
            "cloud", "saas", "software services", "consulting", "outsourcing",
            "bpo", "ai", "artificial intelligence", "automation", "deal win",
            "attrition", "headcount", "visa",
        ],
        "symbols": [
            "TCS", "INFY", "WIPRO", "HCLTECH", "TECHM", "LTTS",
            "PERSISTENT", "COFORGE", "LTIM", "HAPPSTMNDS", "MASTEK",
            "MPHASIS", "KPITTECH",
        ],
        "weights": {"company": 15, "symbol": 8, "keyword": 3},
    },
    "Oil & Gas": {
        "companies": [
            "reliance", "reliance industries", "ongc", "oil and natural gas",
            "bpcl", "bharat petroleum", "ioc", "indian oil", "hpcl",
            "hindustan petroleum", "gail", "gail india", "oil india",
            "petronet lng", "igl", "indraprastha gas", "mahanagar gas",
        ],
        "keywords": [
            "oil", "gas", "petroleum", "refinery", "crude oil", "energy",
            "petrol", "diesel", "lng", "cng", "natural gas", "lpg",
            "petrochemical", "fuel", "opec", "brent", "wti", "pipeline",
        ],
        "symbols": [
            "RELIANCE", "ONGC", "BPCL", "IOC", "HPCL", "GAIL",
            "OIL", "PETRONET", "IGL", "MGL",
        ],
        "weights": {"company": 15, "symbol": 8, "keyword": 3},
    },
    "Pharmaceuticals": {
        "companies": [
            "sun pharma", "sun pharmaceutical", "cipla", "dr reddy",
            "dr reddys", "divis labs", "lupin", "aurobindo pharma",
            "torrent pharma", "alkem", "biocon", "zydus", "zydus lifesciences",
            "glenmark", "ipca", "abbott india",
        ],
        "keywords": [
            "pharma", "pharmaceutical", "healthcare", "drugs", "medicines",
            "vaccine", "formulations", "api", "generic drugs", "fda",
            "usfda", "warning letter", "clinical trial", "biosimilar",
        ],
        "symbols": [
            "SUNPHARMA", "CIPLA", "DRREDDY", "DIVISLAB", "LUPIN",
            "AUROPHARMA", "TORNTPHARM", "ALKEM", "BIOCON", "ZYDUSLIFE",
            "GLENMARK", "IPCALAB", "ABBOTINDIA",
        ],
        "weights": {"company": 15, "symbol": 8, "keyword": 3},
    },
    "Automobile": {
        "companies": [
            "maruti", "maruti suzuki", "tata motors", "mahindra", "m&m",
            "bajaj auto", "hero motocorp", "tvs motor", "eicher motors",
            "ashok leyland", "ola electric", "force motors",
        ],
        "keywords": [
            "automobile", "auto", "cars", "bikes", "vehicles",
            "electric vehicle", "ev", "two wheeler", "four wheeler",
            "commercial vehicle", "tractors", "sales volumes", "dispatches",
        ],
        "symbols": [
            "MARUTI", "TATAMOTORS", "M&M", "BAJAJ-AUTO", "HEROMOTOCO",
            "TVSMOTOR", "EICHERMOT", "ASHOKLEY",
        ],
        "weights": {"company": 15, "symbol": 8, "keyword": 3},
    },
    "Defense": {
        "companies": [
            "bharat electronics", "bel", "hal", "hindustan aeronautics",
            "bharat dynamics", "bdl", "cochin shipyard", "mazagon dock",
            "garden reach", "paras defence",
        ],
        "keywords": [
            "defense", "defence", "military", "aerospace", "aviation",
            "weapons", "missiles", "radars", "naval", "shipyard",
            "electronic warfare", "drdo", "order book", "ministry of defence",
        ],
        "symbols": [
            "BEL", "HAL", "BDL", "COCHINSHIP", "MAZDOCK",
            "GRSE", "PARAS",
        ],
        "weights": {"company": 15, "symbol": 8, "keyword": 4},
    },
    "Metals & Mining": {
        "companies": [
            "tata steel", "jsw steel", "hindalco", "vedanta", "sail",
            "steel authority", "jindal steel", "nmdc", "coal india",
            "hindustan zinc", "nalco", "ratnamani metals",
        ],
        "keywords": [
            "steel", "metals", "mining", "aluminium", "copper", "zinc",
            "iron ore", "coal", "commodities", "steel production",
            "realization", "coking coal", "scrap",
        ],
        "symbols": [
            "TATASTEEL", "JSWSTEEL", "HINDALCO", "VEDL", "SAIL",
            "JSPL", "NMDC", "COALINDIA", "HINDZINC", "NALCO",
        ],
        "weights": {"company": 15, "symbol": 8, "keyword": 3},
    },
    "FMCG": {
        "companies": [
            "hindustan unilever", "hul", "itc", "nestle", "britannia",
            "dabur", "godrej consumer", "marico", "colgate", "tata consumer",
            "emami", "jyothy labs", "varun beverages",
        ],
        "keywords": [
            "fmcg", "consumer goods", "personal care", "food products",
            "beverages", "packaged foods", "snacks", "dairy", "household",
            "volume growth", "rural demand", "urban consumption",
        ],
        "symbols": [
            "HINDUNILVR", "ITC", "NESTLEIND", "BRITANNIA", "DABUR",
            "GODREJCP", "MARICO", "COLPAL", "TATACONSUM", "EMAMILTD",
            "JYOTHYLAB", "VBL",
        ],
        "weights": {"company": 15, "symbol": 8, "keyword": 3},
    },
    "Real Estate": {
        "companies": [
            "dlf", "godrej properties", "oberoi realty", "prestige estates",
            "brigade", "sobha", "phoenix mills", "lodha", "macrotech",
            "sunteck realty", "kolte patil",
        ],
        "keywords": [
            "real estate", "realty", "property", "residential",
            "commercial property", "construction", "housing", "apartments",
            "pre-sales", "collections", "inventory", "launches",
        ],
        "symbols": [
            "DLF", "GODREJPROP", "OBEROIRLTY", "PRESTIGE",
            "BRIGADE", "SOBHA", "PHOENIXLTD", "LODHA",
        ],
        "weights": {"company": 15, "symbol": 8, "keyword": 3},
    },
    "Cement": {
        "companies": [
            "ultratech", "shree cement", "acc", "ambuja cement",
            "dalmia bharat", "jk cement", "ramco cements", "nuvoco",
        ],
        "keywords": [
            "cement", "building materials", "construction materials",
            "concrete", "cement prices", "cement production", "clinker",
            "capacity utilization", "realization per tonne",
        ],
        "symbols": [
            "ULTRACEMCO", "SHREECEM", "ACC", "AMBUJACEM",
            "DALBHARAT", "JKCEMENT", "RAMCOCEM",
        ],
        "weights": {"company": 15, "symbol": 8, "keyword": 4},
    },
    "Telecom": {
        "companies": [
            "bharti airtel", "airtel", "vodafone idea", "vi",
            "indus towers", "tata communications", "sterlite technologies",
        ],
        "keywords": [
            "telecom", "mobile", "broadband", "internet", "5g", "4g",
            "network", "spectrum", "subscriber", "arpu", "tariff hike",
        ],
        "symbols": [
            "BHARTIARTL", "IDEA", "INDUSTOWER", "TATACOMM",
        ],
        "weights": {"company": 15, "symbol": 8, "keyword": 4},
    },
    "Power": {
        "companies": [
            "ntpc", "power grid", "adani power", "tata power",
            "jsw energy", "adani green", "torrent power", "cesc",
        ],
        "keywords": [
            "power", "electricity", "energy", "renewable", "solar", "wind",
            "thermal", "power generation", "transmission", "ppa",
            "plant load factor", "plf", "capacity addition",
        ],
        "symbols": [
            "NTPC", "POWERGRID", "ADANIPOWER", "TATAPOWER",
            "ADANIGREEN", "JSWENERGY", "TORNTPOWER", "CESC",
        ],
        "weights": {"company": 15, "symbol": 8, "keyword": 3},
    },
    "Retail": {
        "companies": [
            "dmart", "avenue supermarts", "trent", "titan",
            "aditya birla fashion", "shoppers stop", "v-mart", "zara india",
        ],
        "keywords": [
            "retail", "shopping", "stores", "supermarket", "fashion retail",
            "jewelry", "footwear", "apparel", "same store sales",
            "like for like", "store additions",
        ],
        "symbols": [
            "DMART", "TRENT", "TITAN", "ABFRL", "SHOPERSTOP", "VMART",
        ],
        "weights": {"company": 15, "symbol": 8, "keyword": 3},
    },
}


# ---------------------------------------------------------------------------
# Data loading — executed ONCE at module import
# ---------------------------------------------------------------------------

def _load_company_data() -> tuple[set, dict, dict]:
    """
    Load company.csv once. Returns:
      valid_symbols   : set of all uppercase NSE/BSE symbols
      company_to_sym  : lowercase company name → symbol
      symbol_to_sector: symbol → sector string (from CSV)
    """
    valid_symbols: set[str] = set()
    company_to_sym: dict[str, str] = {}
    symbol_to_sector: dict[str, str] = {}

    try:
        with open(_CSV_PATH, newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                sym = row.get("SYMBOL", "").strip().upper()
                name = row.get("COMPANY_NAME", "").strip()
                sector = row.get("SECTOR", "").strip()

                if sym:
                    valid_symbols.add(sym)
                    symbol_to_sector[sym] = sector
                if name and sym:
                    company_to_sym[name.lower()] = sym

        logger.info(
            f"CSV loaded: {len(valid_symbols)} symbols, "
            f"{len(company_to_sym)} company names"
        )
    except FileNotFoundError:
        logger.error(f"company.csv not found at {_CSV_PATH}. Using fallback dataset.")
        _apply_fallback(valid_symbols, company_to_sym, symbol_to_sector)
    except Exception as exc:
        logger.exception(f"CSV load error: {exc}")
        _apply_fallback(valid_symbols, company_to_sym, symbol_to_sector)

    return valid_symbols, company_to_sym, symbol_to_sector


def _apply_fallback(
    valid_symbols: set,
    company_to_sym: dict,
    symbol_to_sector: dict,
) -> None:
    defaults = [
        ("RELIANCE", "Reliance Industries", "Oil & Gas"),
        ("TCS", "TCS", "IT"),
        ("HDFCBANK", "HDFC Bank", "Banking"),
        ("BEL", "Bharat Electronics", "Defense"),
        ("INFY", "Infosys", "IT"),
        ("WIPRO", "Wipro", "IT"),
        ("ICICIBANK", "ICICI Bank", "Banking"),
        ("SBIN", "State Bank Of India", "Banking"),
    ]
    for sym, name, sector in defaults:
        valid_symbols.add(sym)
        company_to_sym[name.lower()] = sym
        symbol_to_sector[sym] = sector


# Module-level singletons (loaded once)
VALID_SYMBOLS, COMPANY_TO_SYMBOL, SYMBOL_TO_SECTOR = _load_company_data()


# ---------------------------------------------------------------------------
# Sector classification
# ---------------------------------------------------------------------------

class SectorService:
    """
    Classifies a news article into a sector using weighted term matching.

    Scoring tiers:
      Company name match → highest weight (15 pts)
      Symbol match       → medium weight  (8 pts)
      Keyword match      → base weight    (3–4 pts, sector-specific)
    """

    def classify(self, title: str, description: str) -> Optional[str]:
        """
        Returns the best-matching sector name, or None if no confident match.
        Confidence threshold: score ≥ 3 (at least one keyword or symbol match).
        """
        article_text = f"{title} {description}".lower()
        best_sector: Optional[str] = None
        best_score = 0

        for sector, data in SECTOR_TAXONOMY.items():
            weights = data.get("weights", {"company": 15, "symbol": 8, "keyword": 3})
            score = 0

            for company in data["companies"]:
                if company in article_text:
                    score += weights["company"]

            for symbol in data["symbols"]:
                if symbol.lower() in article_text:
                    score += weights["symbol"]

            for keyword in data["keywords"]:
                if keyword in article_text:
                    score += weights["keyword"]

            if score > best_score:
                best_score = score
                best_sector = sector

        if best_score >= 3:
            logger.debug(f"Classified → '{best_sector}' (score={best_score})")
            return best_sector

        return None

    # ------------------------------------------------------------------
    # Stock symbol extraction
    # ------------------------------------------------------------------

    def extract_stocks(self, title: str) -> list[str]:
        """
        Extract stock symbols mentioned in a headline.

        CRITICAL FIX — Root cause of misattribution bugs:
        ─────────────────────────────────────────────────
        The original code used simple `.lower() in text` substring matching.
        This caused "energy" in "Adani Green Energy" to match "JSWENERGY"
        because "energy" IS a substring of "jswenergy".

        ALL symbol checks now use strict \b word-boundary regex so that
        "JSWENERGY" only matches if the exact token "JSWENERGY" appears
        in the headline — never as a partial substring of another word.

        Company name matching also uses word-boundary anchored regex
        instead of raw `in` to prevent "jsw" matching "jswsteel" etc.

        Rules:
          1. Financial context required before any symbol is accepted
          2. ALL symbols (short or long) → strict \b word-boundary match
          3. Short symbols (≤3 chars) → additional clean-spacing guard
          4. Company names → word-boundary aware regex match
          5. False-positive filter applied last
        """
        if not title:
            return []

        title_upper = title.upper()
        title_lower = title.lower()
        found: list[str] = []

        # Require at least one financial context word in the title
        # before doing any expensive symbol scanning
        has_financial_context = any(
            ctx in title_lower for ctx in _FINANCIAL_CONTEXT_TOKENS
        )
        if not has_financial_context:
            return []

        # ── Direct symbol matching — strict word-boundary for ALL ──────
        # CRITICAL: \b prevents "energy" matching inside "jswenergy"
        for symbol in VALID_SYMBOLS:
            pattern = r"\b" + re.escape(symbol) + r"\b"

            if len(symbol) <= 3:
                # Extra guard for short symbols: must be surrounded by
                # whitespace or punctuation, not mid-word
                strict_pattern = r"(?:^|[\s,.()\[\]'\"/])" + re.escape(symbol) + r"(?:[\s,.()\[\]'\"/]|$)"
                if re.search(strict_pattern, title_upper):
                    found.append(symbol)
            else:
                if re.search(pattern, title_upper):
                    found.append(symbol)

        # ── Company name → symbol lookup — word-boundary aware ─────────
        # CRITICAL: Use \b anchored regex, NOT simple `name in title_lower`
        # Prevents "jsw" from matching inside "jswenergy" or "jswsteel"
        for name, symbol in COMPANY_TO_SYMBOL.items():
            if len(name) < 5 or symbol in found:
                continue
            # Escape the company name and wrap in word boundaries
            name_pattern = r"\b" + re.escape(name) + r"\b"
            if re.search(name_pattern, title_lower):
                found.append(symbol)

        # ── Taxonomy company name lookup — same word-boundary fix ───────
        for sector_data in SECTOR_TAXONOMY.values():
            syms = sector_data["symbols"]
            for i, company in enumerate(sector_data["companies"]):
                if len(company) < 5:
                    continue
                if i >= len(syms):
                    continue
                sym = syms[i]
                if sym in found or sym not in VALID_SYMBOLS:
                    continue
                # Word-boundary match on multi-word company names
                name_pattern = r"\b" + re.escape(company) + r"\b"
                if re.search(name_pattern, title_lower):
                    found.append(sym)

        # ── False-positive filter ─────────────────────────────────────
        found = [s for s in found if s not in _SYMBOL_FALSE_POSITIVES]

        # ── Dedup while preserving order ──────────────────────────────
        seen: set[str] = set()
        unique: list[str] = []
        for s in found:
            if s not in seen:
                seen.add(s)
                unique.append(s)

        return unique[:5]  # Cap at 5 per article to avoid noise

    def get_sector_for_symbol(self, symbol: str) -> Optional[str]:
        """Look up sector by symbol from CSV data."""
        return SYMBOL_TO_SECTOR.get(symbol.upper())

    def get_all_sectors(self) -> list[str]:
        return list(SECTOR_TAXONOMY.keys())


# ---------------------------------------------------------------------------
# Singleton instance
# ---------------------------------------------------------------------------
sector_service = SectorService()
