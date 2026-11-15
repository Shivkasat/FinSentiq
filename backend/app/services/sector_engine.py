import os
import csv
import re
import logging
from pathlib import Path
from typing import Dict, Set, List, Optional
from app.core.config import settings

logger = logging.getLogger("finsentiq.sector")

# Tokens that look like symbols but are common English words
FALSE_POSITIVE_SYMBOLS = frozenset({
    "IT", "AM", "PM", "IN", "ON", "AT", "TO", "OR", "AN", "AS", "BE",
    "IS", "DO", "GO", "BY", "IF", "NO", "SO", "UP", "US", "UK", "EU",
    "FY", "YY", "QQ", "MF", "PE", "PB", "CF", "ALL", "NEW", "BUY", "SELL"
})

# Well-known Indian market company aliases mapping directly to ticker symbols
WELL_KNOWN_ALIASES = {
    "reliance": "RELIANCE",
    "ril": "RELIANCE",
    "reliance industries": "RELIANCE",
    "tcs": "TCS",
    "tata consultancy": "TCS",
    "infosys": "INFY",
    "infy": "INFY",
    "hdfc bank": "HDFCBANK",
    "hdfc": "HDFCBANK",
    "icici bank": "ICICIBANK",
    "icici": "ICICIBANK",
    "sbi": "SBIN",
    "state bank of india": "SBIN",
    "state bank": "SBIN",
    "bharti airtel": "BHARTIARTL",
    "airtel": "BHARTIARTL",
    "tata motors": "TATAMOTORS",
    "maruti": "MARUTI",
    "maruti suzuki": "MARUTI",
    "mahindra": "M&M",
    "m&m": "M&M",
    "bajaj finance": "BAJFINANCE",
    "bajaj finserv": "BAJAJFINSV",
    "l&t": "LT",
    "larsen": "LT",
    "larsen & toubro": "LT",
    "itc": "ITC",
    "hindustan unilever": "HINDUNILVR",
    "hul": "HINDUNILVR",
    "wipro": "WIPRO",
    "hcl tech": "HCLTECH",
    "tech mahindra": "TECHM",
    "axis bank": "AXISBANK",
    "kotak bank": "KOTAKBANK",
    "kotak mahindra": "KOTAKBANK",
    "sun pharma": "SUNPHARMA",
    "dr reddy": "DRREDDY",
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
    "coal india": "COALINDIA",
    "titan": "TITAN",
    "zomato": "ZOMATO",
    "swiggy": "SWIGGY",
    "paytm": "PAYTM",
    "one97": "PAYTM",
    "jio financial": "JIOFIN",
    "jio": "JIOFIN",
    "vedanta": "VEDL",
    "dlf": "DLF",
    "ultratech": "ULTRACEMCO",
    "grasim": "GRASIM",
    "indusind bank": "INDUSINDBK",
    "canara bank": "CANBK",
    "punjab national bank": "PNB",
    "pnb": "PNB",
    "bank of baroda": "BANKBARODA"
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
    ]
}

GENERIC_STOP_WORDS = frozenset({
    "bank", "finance", "industries", "services", "enterprises", "india",
    "power", "steel", "motors", "group", "holdings", "energy", "pharma",
    "capital", "technology", "technologies", "corp", "corporation"
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

            for alias, sym in WELL_KNOWN_ALIASES.items():
                self.valid_symbols.add(sym)
                self.company_to_symbol[alias] = sym
                if sym not in self.symbol_to_sector:
                    self.symbol_to_sector[sym] = "Broad Market"

            logger.info(f"SectorEngine successfully loaded {len(self.valid_symbols)} stock symbols and {len(self.company_to_symbol)} company mappings from {csv_file}")
        except Exception as e:
            logger.error(f"Error loading company CSV: {e}")

    def extract_symbols(self, text: str) -> List[str]:
        found = set()
        text_lower = text.lower()
        text_upper = text.upper()

        for name, symbol in self.company_to_symbol.items():
            if len(name) < 3:
                continue
            pattern = r"\b" + re.escape(name) + r"\b"
            if re.search(pattern, text_lower):
                found.add(symbol)

        for word in re.findall(r"\b[A-Z]{3,15}\b", text_upper):
            if word in self.valid_symbols and word not in FALSE_POSITIVE_SYMBOLS:
                found.add(word)

        return list(found)[:5]

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
