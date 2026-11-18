import os
import csv
import re
import logging
from pathlib import Path
from typing import Dict, Set, List, Optional, Any
from app.core.config import settings

logger = logging.getLogger("finsentiq.sector")

# Tokens that look like symbols but are common English words, commodities, or currencies
FALSE_POSITIVE_SYMBOLS = frozenset({
    "IT", "AM", "PM", "IN", "ON", "AT", "TO", "OR", "AN", "AS", "BE",
    "IS", "DO", "GO", "BY", "IF", "NO", "SO", "UP", "US", "UK", "EU",
    "FY", "YY", "QQ", "MF", "PE", "PB", "CF", "ALL", "NEW", "BUY", "SELL",
    "DOLLAR", "OIL", "GOLD", "GAS", "TEA", "IDEA", "POWER", "STEEL", "BANK",
    "NET", "HIGH", "LOW", "GAIN", "FALL", "BEST", "CARE", "FAST", "STAR",
    "REAL", "TRUE", "FREE", "COST", "DEAL", "AUTO", "TECH", "DATA", "CORP",
    "INDIAN", "INDIA", "GLOBAL", "MARKET", "STOCK", "TRADE", "SHARE", "PRICE",
    "NEWS", "TODAY", "RECORD", "VALUE", "ALERT", "BULL", "BEAR", "CALL", "PUT",
    "HOLD", "TARGET", "VIEW", "TIME", "OPEN", "CLOSE", "WAR", "PEACE", "RATE",
    "UNIT", "KEY", "TOP", "LOSS", "BASE", "BOND", "FUND", "FLOW", "GROW",
    "RISE", "BEAT", "MISS", "HIKE", "DROP", "CRASH", "BOOM", "PEAK", "SLIP", "SURGE"
})

ROUNDUP_PATTERNS = [
    r"\bstocks to watch\b",
    r"\bbuzzing stocks\b",
    r"\btop stocks (to|for)\b",
    r"\bstocks in (news|focus|action)\b",
    r"\bmarket (wrap|live|updates|closing|outlook)\b",
    r"\bgift nifty\b",
    r"\bopening bell\b",
    r"\bclosing bell\b",
    r"\bf&o ban\b",
    r"\btrade setup\b",
    r"\bwhat to watch\b",
    r"\btrading guide\b",
    r"\bbrokerage radar\b",
    r"\bstock radar\b",
    r"\bshare market today\b",
    r"\bsensex today\b",
    r"\bnifty today\b",
    r"\bsensex, nifty\b",
    r"\bnifty, sensex\b",
    r"\b5 stocks\b",
    r"\b10 stocks\b",
    r"\bbuy or sell\b",
    r"\bbuzzing scrips\b"
]

# Well-known Indian market company aliases mapping directly to ticker symbols
WELL_KNOWN_ALIASES = {
    "reliance industries": "RELIANCE",
    "reliance": "RELIANCE",
    "ril": "RELIANCE",
    "tata consultancy services": "TCS",
    "tata consultancy": "TCS",
    "tcs": "TCS",
    "infosys": "INFY",
    "infy": "INFY",
    "hdfc bank": "HDFCBANK",
    "hdfc": "HDFCBANK",
    "icici bank": "ICICIBANK",
    "icici": "ICICIBANK",
    "state bank of india": "SBIN",
    "state bank": "SBIN",
    "sbi": "SBIN",
    "bharti airtel": "BHARTIARTL",
    "airtel": "BHARTIARTL",
    "tata motors": "TATAMOTORS",
    "maruti suzuki": "MARUTI",
    "maruti": "MARUTI",
    "mahindra & mahindra": "M&M",
    "mahindra and mahindra": "M&M",
    "mahindra": "M&M",
    "m&m": "M&M",
    "bajaj finance": "BAJFINANCE",
    "bajaj finserv": "BAJAJFINSV",
    "larsen & toubro": "LT",
    "larsen and toubro": "LT",
    "larsen": "LT",
    "l&t": "LT",
    "itc": "ITC",
    "hindustan unilever": "HINDUNILVR",
    "hul": "HINDUNILVR",
    "wipro": "WIPRO",
    "hcl tech": "HCLTECH",
    "hcl technologies": "HCLTECH",
    "tech mahindra": "TECHM",
    "axis bank": "AXISBANK",
    "kotak mahindra bank": "KOTAKBANK",
    "kotak bank": "KOTAKBANK",
    "kotak": "KOTAKBANK",
    "sun pharma": "SUNPHARMA",
    "sun pharmaceuticals": "SUNPHARMA",
    "dr reddy": "DRREDDY",
    "dr reddy's": "DRREDDY",
    "dr reddys": "DRREDDY",
    "cipla": "CIPLA",
    "tata steel": "TATASTEEL",
    "jsw steel": "JSWSTEEL",
    "hindalco": "HINDALCO",
    "adani enterprises": "ADANIENT",
    "adani ports": "ADANIPORTS",
    "adani green": "ADANIGREEN",
    "adani power": "ADANIPOWER",
    "ntpc": "NTPC",
    "ongc": "ONGC",
    "power grid": "POWERGRID",
    "powergrid": "POWERGRID",
    "coal india": "COALINDIA",
    "titan company": "TITAN",
    "titan": "TITAN",
    "zomato": "ZOMATO",
    "swiggy": "SWIGGY",
    "paytm": "PAYTM",
    "one97": "PAYTM",
    "jio financial": "JIOFIN",
    "jio financial services": "JIOFIN",
    "vedanta": "VEDL",
    "dlf": "DLF",
    "ultratech cement": "ULTRACEMCO",
    "ultratech": "ULTRACEMCO",
    "grasim industries": "GRASIM",
    "grasim": "GRASIM",
    "indusind bank": "INDUSINDBK",
    "indusind": "INDUSINDBK",
    "canara bank": "CANBK",
    "punjab national bank": "PNB",
    "pnb": "PNB",
    "bank of baroda": "BANKBARODA",
    "bharat electronics": "BEL",
    "bel": "BEL",
    "hindustan aeronautics": "HAL",
    "hal": "HAL",
    "senco gold": "SENCO",
    "mazagon dock": "MAZDOCK",
    "garden reach": "GRSE",
    "j kumar infra": "JKUMAR",
    "j kumar": "JKUMAR",
    "j. kumar": "JKUMAR",
    "jagatjit industries": "JAGATJIT",
    "jagatjit": "JAGATJIT",
    "mobikwik": "MOBIKWIK"
}

SECTOR_KEYWORDS = {
    "Banking & Finance": [
        "bank", "banking", "rbi", "nbfc", "credit", "loan", "lending", "npa",
        "fintech", "repo rate", "monetary policy", "liquidity", "deposit"
    ],
    "Information Technology": [
        "it", "software", "tech", "ai", "artificial intelligence", "cloud",
        "saas", "digital", "cybersecurity", "outsourcing"
    ],
    "Automotive": [
        "auto", "automobile", "ev", "electric vehicle", "car", "suv", "two-wheeler", "oems"
    ],
    "Pharma & Healthcare": [
        "pharma", "pharmaceutical", "drug", "fda", "usfda", "biotech", "hospital", "clinical"
    ],
    "Energy, Oil & Gas": [
        "oil", "gas", "petroleum", "crude", "refinery", "energy", "solar", "renewable", "power"
    ],
    "Metals & Mining": [
        "metal", "steel", "iron", "aluminum", "copper", "mining", "coal"
    ],
    "FMCG & Consumer": [
        "fmcg", "consumer", "retail", "food", "beverage", "rural demand"
    ],
    "Infrastructure & Realty": [
        "infrastructure", "infra", "realty", "real estate", "housing", "construction", "cement"
    ],
    "Telecom & Media": [
        "telecom", "5g", "spectrum", "broadband", "media", "entertainment"
    ],
    "Defence & Aerospace": [
        "defence", "defense", "aerospace", "missile", "warship", "ammunition", "ordnance"
    ]
}

GENERIC_STOP_WORDS = frozenset({
    "bank", "finance", "industries", "services", "enterprises", "india",
    "power", "steel", "motors", "group", "holdings", "energy", "pharma",
    "capital", "technology", "technologies", "corp", "corporation",
    "dollar", "oil", "gas", "gold", "silver", "copper", "coal", "sugar",
    "tea", "coffee", "cement", "paper", "chemicals", "market", "global",
    "national", "international", "digital", "system", "systems", "solutions",
    "securities", "life", "general", "mutual", "fund", "funds", "ltd", "limited"
})

class SectorEngine:
    def __init__(self):
        self.valid_symbols: Set[str] = set()
        self.symbol_to_sector: Dict[str, str] = {}
        self.company_to_symbol: Dict[str, str] = {}
        self._load_csv()

    def _load_csv(self):
        base_dir = Path(__file__).resolve().parent.parent
        candidates = [
            base_dir / "company.csv",
            Path("backend/app/company.csv"),
            Path("app/company.csv"),
            Path("company.csv")
        ]

        csv_file = None
        for p in candidates:
            if p.exists():
                csv_file = p
                break

        if not csv_file:
            logger.warning("company.csv could not be located. Initializing with well-known market tickers.")
            for alias, sym in WELL_KNOWN_ALIASES.items():
                self.valid_symbols.add(sym)
                self.company_to_symbol[alias] = sym
            return

        try:
            with open(csv_file, mode="r", encoding="utf-8-sig") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    symbol = (row.get("SYMBOL") or row.get("Symbol") or "").strip().upper()
                    company = (row.get("COMPANY_NAME") or row.get("Company Name") or "").strip()
                    sector = (row.get("SECTOR") or row.get("Sector") or row.get("Industry") or "").strip() or "Broad Market"

                    if symbol:
                        self.valid_symbols.add(symbol)
                        self.symbol_to_sector[symbol] = sector
                        if company:
                            clean_name = re.sub(r"\b(ltd|limited|pvt|corporation|corp|india|industries)\b", "", company, flags=re.IGNORECASE).strip()
                            if len(clean_name) >= 3 and clean_name.lower() not in GENERIC_STOP_WORDS:
                                self.company_to_symbol[clean_name.lower()] = symbol
                            if len(company) >= 4 and company.lower() not in GENERIC_STOP_WORDS:
                                self.company_to_symbol[company.lower()] = symbol

            for alias, sym in WELL_KNOWN_ALIASES.items():
                self.valid_symbols.add(sym)
                self.company_to_symbol[alias] = sym
                if sym not in self.symbol_to_sector:
                    self.symbol_to_sector[sym] = "Broad Market"

            logger.info(f"SectorEngine successfully loaded {len(self.valid_symbols)} stock symbols and {len(self.company_to_symbol)} company mappings from {csv_file}")
        except Exception as e:
            logger.error(f"Error loading company CSV: {e}")

    def is_market_roundup(self, text: str) -> bool:
        """Determines if a headline or article is a generic morning listicle or broad market wrap."""
        if not text:
            return False
        t_lower = text.lower()
        return any(re.search(p, t_lower) for p in ROUNDUP_PATTERNS)

    def extract_symbols(self, text: str) -> List[str]:
        """
        High-precision symbol extraction without blanket uppercase conversion.
        Prevents common dictionary collisions and commodity false positives.
        """
        if not text:
            return []

        found = set()
        text_lower = text.lower()

        # 1. Match company aliases (ordered from longest phrase to shortest)
        sorted_aliases = sorted(self.company_to_symbol.keys(), key=len, reverse=True)
        for name in sorted_aliases:
            if len(name) < 3 or name in GENERIC_STOP_WORDS:
                continue
            pattern = r"\b" + re.escape(name) + r"\b"
            if re.search(pattern, text_lower):
                found.add(self.company_to_symbol[name])
                if len(found) >= 5:
                    break

        # 2. Match raw UPPERCASE tickers ONLY (strictly avoiding text.upper() blanket conversions)
        raw_caps = re.findall(r"\b[A-Z]{3,12}\b", text)
        for word in raw_caps:
            if word in self.valid_symbols and word not in FALSE_POSITIVE_SYMBOLS:
                found.add(word)
                if len(found) >= 5:
                    break

        return list(found)[:5]

    def extract_symbols_with_metadata(self, text: str, title: str = "") -> Dict[str, Any]:
        """
        Extracts symbols along with institutional metadata:
        identifying whether an article is a listicle roundup or a focused single-stock catalyst.
        """
        check_title = title if title else text[:140]
        is_roundup = self.is_market_roundup(check_title)
        symbols = self.extract_symbols(text)

        # Multi-stock articles (3 or more) in headlines behave like listicle roundups
        if len(symbols) >= 3:
            is_roundup = True

        is_single = (len(symbols) == 1 and not is_roundup)
        primary = symbols[0] if symbols else None

        return {
            "symbols": symbols,
            "is_roundup": is_roundup,
            "is_single_stock": is_single,
            "primary_symbol": primary
        }

    def classify_sector(self, text: str, symbols: List[str]) -> str:
        if symbols:
            first_symbol = symbols[0]
            if first_symbol in self.symbol_to_sector:
                csv_sector = self.symbol_to_sector[first_symbol]
                if csv_sector and csv_sector != "Broad Market":
                    return csv_sector

        text_lower = text.lower()
        sector_scores = {}
        for sector, keywords in SECTOR_KEYWORDS.items():
            score = sum(1 for kw in keywords if re.search(r"\b" + re.escape(kw) + r"\b", text_lower))
            if score > 0:
                sector_scores[sector] = score

        if sector_scores:
            return max(sector_scores, key=sector_scores.get)

        return "Broad Market"

sector_engine = SectorEngine()
