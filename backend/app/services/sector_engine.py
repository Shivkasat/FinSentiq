import os
import csv
import re
import logging
from typing import Dict, Set, List, Optional
from app.core.config import settings

logger = logging.getLogger("finsentiq.sector")

# Primary Sector mapping and keywords
SECTOR_KEYWORDS = {
    "Banking & Finance": [
        "bank", "banking", "rbi", "nbfc", "credit", "loan", "lending", "npa",
        "fintech", "repo rate", "monetary policy", "liquidity", "deposit", "hdfc", "sbi", "icici", "kotak", "axis"
    ],
    "Information Technology": [
        "it", "software", "tech", "ai", "artificial intelligence", "cloud",
        "saas", "digital", "tcs", "infosys", "wipro", "hcl", "tech mahindra", "cybersecurity"
    ],
    "Automotive": [
        "auto", "automobile", "ev", "electric vehicle", "car", "suv", "two-wheeler",
        "tata motors", "maruti", "mahindra", "bajaj auto", "hero motocorp", "oems"
    ],
    "Pharma & Healthcare": [
        "pharma", "pharmaceutical", "drug", "fda", "usfda", "biotech", "hospital",
        "sun pharma", "dr reddy", "cipla", "lupin", "healthcare", "clinical"
    ],
    "Energy, Oil & Gas": [
        "oil", "gas", "petroleum", "crude", "refinery", "energy", "solar",
        "renewable", "power", "ntpc", "ongc", "reliance", "bpcl", "ioc", "adani green"
    ],
    "Metals & Mining": [
        "metal", "steel", "iron", "aluminum", "copper", "mining", "coal",
        "tata steel", "jsw steel", "hindalco", "vedanta", "nmdc"
    ],
    "FMCG & Consumer": [
        "fmcg", "consumer", "retail", "food", "beverage", "hul", "itc",
        "nestle", "britannia", "dabur", "marico", "rural demand"
    ],
    "Infrastructure & Realty": [
        "infrastructure", "infra", "realty", "real estate", "housing", "construction",
        "cement", "l&t", "dlf", "ultratech", "godrej properties", "highways", "railways"
    ],
    "Telecom & Media": [
        "telecom", "5g", "spectrum", "broadband", "airtel", "jio", "vodafone",
        "media", "entertainment", "broadcasting"
    ]
}

class SectorEngine:
    def __init__(self, csv_path: str = settings.COMPANY_CSV_PATH):
        self.csv_path = csv_path
        self.valid_symbols: Set[str] = set()
        self.symbol_to_sector: Dict[str, str] = {}
        self.company_to_symbol: Dict[str, str] = {}
        self._load_csv()

    def _load_csv(self):
        if not os.path.exists(self.csv_path):
            # Try alternate path relative to root
            alt_path = "company.csv"
            if os.path.exists(alt_path):
                self.csv_path = alt_path
            else:
                logger.warning(f"Company CSV file not found at {self.csv_path}. Symbol lookup will be limited.")
                return

        try:
            with open(self.csv_path, mode="r", encoding="utf-8-sig") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    symbol = row.get("Symbol", "").strip().upper()
                    company = row.get("Company Name", "").strip()
                    sector = row.get("Industry", "").strip() or row.get("Sector", "").strip() or "Broad Market"

                    if symbol:
                        self.valid_symbols.add(symbol)
                        self.symbol_to_sector[symbol] = sector
                        if company:
                            # Clean company name
                            clean_name = re.sub(r"\b(ltd|limited|pvt|corporation|corp|india|industries)\b", "", company, flags=re.IGNORECASE).strip()
                            if len(clean_name) > 3:
                                self.company_to_symbol[clean_name.lower()] = symbol
            logger.info(f"Loaded {len(self.valid_symbols)} stock symbols from {self.csv_path}")
        except Exception as e:
            logger.error(f"Error loading company CSV: {e}")

    def extract_symbols(self, text: str) -> List[str]:
        """Extract stock tickers and mapped company names from headline/text."""
        found = set()
        text_upper = text.upper()
        text_lower = text.lower()

        # 1. Match against known NSE symbols with word boundary
        for word in re.findall(r"\b[A-Z]{3,12}\b", text_upper):
            if word in self.valid_symbols:
                found.add(word)

        # 2. Match company names
        for company_name, symbol in self.company_to_symbol.items():
            if re.search(r"\b" + re.escape(company_name) + r"\b", text_lower):
                found.add(symbol)

        return list(found)

    def classify_sector(self, text: str, symbols: List[str]) -> str:
        """Classify article into sector based on extracted symbols and text keywords."""
        # Symbol priority
        if symbols:
            first_symbol = symbols[0]
            if first_symbol in self.symbol_to_sector:
                csv_sector = self.symbol_to_sector[first_symbol]
                # Map to our standard sectors
                for std_sector, keywords in SECTOR_KEYWORDS.items():
                    if any(k in csv_sector.lower() for k in keywords):
                        return std_sector
                return csv_sector

        # Keyword frequency scoring
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
