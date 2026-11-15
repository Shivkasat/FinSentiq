"""
summarizer_service.py — Sentix Intelligence Platform v2.2
-----------------------------------------------------------
Production-grade article extraction and summarization engine.

DEFECTS FIXED IN THIS VERSION:
  D4  Google News / redirect URLs now resolved to final destination BEFORE
      passing to any extractor. Newspaper3k was receiving google.com redirect
      pages, not the actual article — causing universal extraction failure.

  D5  Newspaper3k now configured with:
        - browser-grade User-Agent
        - request_timeout=15 (was unlimited)
        - follow_meta_refresh=True (handles AMP/redirect pages)
        - fetch_images=False (faster)
      Config applied ONCE at module level, not per-call.

  D6  extract_and_summarize no longer swallows exceptions silently.
      All failure modes return structured error dicts — never raise to caller.
      The /api/summarize route was getting unhandled exceptions causing HTTP 500.

  D9  extract_and_summarize now accepts `article_title` parameter.
      The actual article headline (from RSS feed) is passed through to the
      sentiment engine and to extract_stocks.

  D10 Groq sentiment in the summarize pipeline now receives:
        title=article_title  (real headline from newspaper3k/trafilatura)
        description=summary  (extracted content summary)
      Previously it received title=url which made Groq analyze a URL string.

  D2  extract_stocks now called on title first (most signal-dense),
      falling back to first 500 chars of content only if title yields nothing.

  D3  SOURCE_DISPLAY_NAMES registry maps all source_keys to clean brand names.
      "economic_times_market" → "Economic Times" (not "Economic Times Market")
      "ndtv_business" → "NDTV Profit" (not "Ndtv Business")
      "bq_prime_markets" → "BQ Prime" (not "Bq Prime Markets")

  D8  summarize_description max_chars increased 200→300 for meaningful summaries.
"""

import re
import logging
import requests
from typing import Optional

logger = logging.getLogger("sentix.summarizer")


# ---------------------------------------------------------------------------
# Source display name registry  (D3 FIX)
# Maps machine source_key → clean brand name shown in UI
# ---------------------------------------------------------------------------
SOURCE_DISPLAY_NAMES: dict[str, str] = {
    "economic_times_market":        "Economic Times",
    "economic_times_stocks":        "Economic Times",
    "economic_times_ipos":          "Economic Times",
    "economic_times_commodities":   "Economic Times",
    "moneycontrol":                 "Moneycontrol",
    "moneycontrol_news":            "Moneycontrol",
    "moneycontrol_markets":         "Moneycontrol",
    "moneycontrol_stocks":          "Moneycontrol",
    "business_standard":            "Business Standard",
    "business_standard_companies":  "Business Standard",
    "business_standard_economy":    "Business Standard",
    "financial_express":            "Financial Express",
    "financial_express_industry":   "Financial Express",
    "livemint":                     "Livemint",
    "livemint_companies":           "Livemint",
    "livemint_money":               "Livemint",
    "ndtv_business":                "NDTV Profit",
    "zeebiz":                       "Zee Business",
    "zeebiz_stocks":                "Zee Business",
    "zeebiz_personal_finance":      "Zee Business",
    "cnbc_market":                  "CNBC TV18",
    "cnbc_business":                "CNBC TV18",
    "bq_prime_markets":             "BQ Prime",
    "bq_prime_business":            "BQ Prime",
    "hindu_business_line":          "Hindu Business Line",
    "business_today_markets":       "Business Today",
    "business_today_companies":     "Business Today",
    "reuters_india":                "Reuters",
    "google_india_business":        "Google News",
    "google_india_stocks":          "Google News",
    "google_sensex":                "Google News",
    "google_nifty":                 "Google News",
    "toi_business":                 "Times of India",
    "investing_india":              "Investing.com",
}

def get_source_display_name(source_key: str) -> str:
    """Return clean human-readable source name for any source_key."""
    return SOURCE_DISPLAY_NAMES.get(
        source_key,
        source_key.replace("_", " ").title()
    )


# ---------------------------------------------------------------------------
# Newspaper3k config — built once at module level  (D5 FIX)
# ---------------------------------------------------------------------------
_NEWSPAPER_CONFIG = None

def _get_newspaper_config():
    """Lazy-singleton: build Newspaper3k Config once, reuse forever."""
    global _NEWSPAPER_CONFIG
    if _NEWSPAPER_CONFIG is not None:
        return _NEWSPAPER_CONFIG
    try:
        from newspaper import Config
        cfg = Config()
        cfg.browser_user_agent = (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/122.0.0.0 Safari/537.36"
        )
        cfg.request_timeout    = 15
        cfg.fetch_images       = False
        cfg.memoize_articles   = False
        cfg.follow_meta_refresh = True
        _NEWSPAPER_CONFIG = cfg
        logger.debug("Newspaper3k Config initialized")
        return cfg
    except ImportError:
        return None


# ---------------------------------------------------------------------------
# Financial domain keyword set for sentence scoring
# ---------------------------------------------------------------------------
_FINANCIAL_KEYWORDS = frozenset({
    # Financials & results
    "profit", "revenue", "growth", "earnings", "sales", "margin", "ebitda",
    "pat", "net profit", "gross profit", "operating profit", "eps",
    "quarter", "q1", "q2", "q3", "q4", "fy", "fy24", "fy25", "fy26",
    "annual", "quarterly", "half-year", "half year",
    # Monetary values
    "crore", "lakh", "billion", "million", "rupee", "percent", "%",
    "inr", "usd", "rs.", "₹",
    # Corporate events
    "announced", "reported", "declared", "approved", "signed", "awarded",
    "launched", "acquired", "merger", "acquisition", "stake", "ipo",
    "listing", "buyback", "dividend", "bonus", "split", "fund", "order",
    "contract", "deal", "partnership", "joint venture", "divestment",
    "fundraise", "qip", "rights issue", "ncd",
    # Price action
    "increased", "decreased", "rose", "fell", "gained", "lost", "surged",
    "plunged", "climbed", "tumbled", "rallied",
    # Analyst signals
    "upgraded", "downgraded", "target", "outlook", "guidance", "forecast",
    "beat", "miss", "above", "below", "estimate", "reiterated", "raised", "cut",
    # Market
    "stock", "share", "equity", "investor", "market", "nse", "bse",
    "nifty", "sensex", "52-week", "all-time high", "52 week",
    # Regulatory / macro
    "rbi", "sebi", "fii", "dii", "fdi", "interest rate", "inflation",
    "gdp", "policy", "regulation", "penalty", "fine", "probe", "investigation",
})


# ---------------------------------------------------------------------------
# SummarizerService
# ---------------------------------------------------------------------------
class SummarizerService:
    """
    Extractive summarizer + multi-method article content extractor.

    The extraction chain handles:
      - Redirect URLs (HTTP 301/302 chains)
      - Google News AMP redirect URLs  (D4 FIX — was root cause of HTTP 500)
      - Paywalled pages (graceful failure with clear message)
      - JS-heavy pages (BeautifulSoup static fallback)
    """

    def __init__(self, max_sentences: int = 3, min_word_count: int = 6):
        self.max_sentences  = max_sentences
        self.min_word_count = min_word_count
        logger.info(f"SummarizerService initialized (max_sentences={max_sentences})")

    # ------------------------------------------------------------------
    # Summarization
    # ------------------------------------------------------------------

    def summarize(self, text: str, max_sentences: Optional[int] = None) -> str:
        """Generate extractive summary. Returns original-order top sentences."""
        n = max_sentences or self.max_sentences

        if not text or len(text.strip()) < 80:
            return text.strip()

        sentences = self._split_sentences(text)
        if not sentences:
            return text[:400].strip() + "..."
        if len(sentences) <= n:
            return ". ".join(s.strip(". ") for s in sentences) + "."

        scored = [
            (self._score_sentence(s, i, len(sentences)), i, s)
            for i, s in enumerate(sentences)
        ]
        top = sorted(scored, reverse=True)[:n]
        top.sort(key=lambda x: x[1])

        return ". ".join(s[2].strip(". ") for s in top) + "."

    def summarize_description(self, description: str, max_chars: int = 300) -> str:
        """
        Quick summary from RSS description text.
        D8 FIX: max_chars increased 200 → 300.
        """
        if not description:
            return ""

        # Strip residual HTML tags
        clean = re.sub(r"<[^>]+>", " ", description)
        clean = re.sub(r"\s+", " ", clean).strip()

        sentences = self._split_sentences(clean)
        result = ""
        for sent in sentences:
            candidate = (result + " " + sent).strip()
            if len(candidate) <= max_chars:
                result = candidate
            else:
                break

        if not result:
            result = clean[:max_chars].rsplit(" ", 1)[0] + "..."

        return result.strip()

    # ------------------------------------------------------------------
    # Full extraction + summarization pipeline (for /api/summarize)
    # D4, D5, D6, D9, D10 FIXES applied here
    # ------------------------------------------------------------------

    def extract_and_summarize(self, url: str, article_title: str = "") -> dict:
        """
        Complete pipeline:
          1. Resolve redirect/Google-News URL → canonical article URL  (D4)
          2. Extract full text via Newspaper3k/Trafilatura/BS4         (D5)
          3. Extractive summarization
          4. Stock extraction from title, then content                  (D2)
          5. Sentiment on real title + summary (NOT the URL string)     (D10)

        NEVER raises — always returns structured dict.                  (D6)
        """
        try:
            # Step 1: URL resolution
            resolved_url = self._resolve_final_url(url)

            # Step 2: Content extraction
            content, method, extracted_title = self._extract_content(resolved_url)

            # D9 FIX: use RSS title if available; fall back to extracted title
            final_title = article_title.strip() or extracted_title.strip() or ""

            if not content or len(content.split()) < 30:
                return self._failure_response(
                    title=final_title,
                    method=method,
                    reason="Could not extract sufficient article content. "
                           "The article may be paywalled, require JavaScript, "
                           "or the source blocked the request.",
                )

            # Step 3: Summarize
            summary = self.summarize(content, max_sentences=4)

            # Step 4: Stock extraction — title first, then content  (D2 FIX)
            from sector_service import sector_service
            stocks = sector_service.extract_stocks(final_title)
            if not stocks:
                stocks = sector_service.extract_stocks(content[:600])

            # Step 5: Sentiment with REAL title, not URL  (D10 FIX)
            from sentiment_service import sentiment_service
            sentiment = sentiment_service.analyze(
                title=final_title,
                description=summary,
            )

            return {
                "success":            True,
                "title":              final_title,
                "summary":            summary,
                "word_count":         len(content.split()),
                "summary_word_count": len(summary.split()),
                "extraction_method":  method,
                "stock_mentions":     stocks[:6],
                "sentiment_label":    sentiment.sentiment_label,
                "sentiment_score":    round(sentiment.sentiment_score, 2),
                "confidence":         round(sentiment.confidence, 2),
                "impact_type":        sentiment.impact_type,
                "reasoning":          sentiment.reasoning,
            }

        except Exception as exc:
            logger.error(f"extract_and_summarize fatal error [{url[:80]}]: {exc}", exc_info=True)
            return self._failure_response(
                title=article_title,
                method="error",
                reason=f"Unexpected error: {str(exc)[:120]}",
            )

    # ------------------------------------------------------------------
    # Sentence scoring
    # ------------------------------------------------------------------

    def _score_sentence(self, sentence: str, position: int, total: int) -> float:
        words      = sentence.split()
        word_count = len(words)

        if word_count < self.min_word_count:
            return 0.0

        score      = 0.0
        sent_lower = sentence.lower()

        # 1. Positional bias — inverted pyramid
        rel = position / max(total, 1)
        if rel < 0.10:
            score += 14.0
        elif rel < 0.20:
            score += 8.0
        elif rel < 0.35:
            score += 4.0
        elif rel > 0.85:
            score += 2.0   # Conclusion sentences often contain key numbers

        # 2. Financial keyword density (cap 18 pts)
        hits = sum(1 for kw in _FINANCIAL_KEYWORDS if kw in sent_lower)
        score += min(18.0, hits * 2.5)

        # 3. Numeric density
        numbers = re.findall(
            r"\b\d[\d,]*(?:\.\d+)?\s*(?:%|percent|crore|lakh|billion|million|rs\.?|₹)?\b",
            sent_lower,
        )
        score += min(10.0, len(numbers) * 2.5)

        # 4. Named entity signals (ALL-CAPS tokens)
        caps = re.findall(r"\b[A-Z]{2,10}\b", sentence)
        score += min(6.0, len(caps) * 1.5)

        # 5. Length normalization
        if 12 <= word_count <= 40:
            score += 3.0
        elif word_count > 60:
            score -= 3.0

        # 6. Quoted speech slight penalty (adds context, not core fact)
        if sentence.count('"') >= 2 or sentence.count("'") >= 4:
            score -= 1.5

        return round(score, 2)

    # ------------------------------------------------------------------
    # Sentence splitting
    # ------------------------------------------------------------------

    @staticmethod
    def _split_sentences(text: str) -> list[str]:
        """Split text into sentences, protecting financial abbreviations."""
        protected = re.sub(
            r"\b(Rs|Mr|Mrs|Dr|Prof|Co|Ltd|Inc|Corp|vs|No|St|Pvt|Govt|"
            r"Fig|Eq|Jan|Feb|Mar|Apr|Jun|Jul|Aug|Sep|Oct|Nov|Dec|approx)\.",
            r"\1<DOT>",
            text,
        )
        raw = re.split(r"(?<=[.!?])\s+(?=[A-Z\"'])", protected)
        sentences = []
        for s in raw:
            s = s.replace("<DOT>", ".").strip()
            if len(s.split()) >= 5:
                sentences.append(s)
        return sentences

    # ------------------------------------------------------------------
    # URL resolution  (D4 FIX — critical for Google News links)
    # ------------------------------------------------------------------

    @staticmethod
    def _resolve_final_url(url: str) -> str:
        """
        Follow HTTP redirects to reach the canonical article URL.

        Google News RSS links are encoded redirect URLs like:
          https://news.google.com/rss/articles/CBMi...
        Without resolution, Newspaper3k would scrape Google's redirect page,
        not the actual article — causing extraction failure and HTTP 500.
        """
        try:
            headers = {
                "User-Agent": (
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/122.0.0.0 Safari/537.36"
                )
            }
            # HEAD request: fast, no body download, follows all redirects
            resp = requests.head(
                url,
                headers=headers,
                allow_redirects=True,
                timeout=10,
            )
            final = resp.url
            if final and final != url:
                logger.debug(f"URL resolved: {url[:50]!r} → {final[:50]!r}")
            return final or url
        except Exception as exc:
            logger.debug(f"URL resolution skipped ({type(exc).__name__}): {url[:60]}")
            return url

    # ------------------------------------------------------------------
    # Content extraction chain  (D5 FIX: Newspaper3k properly configured)
    # ------------------------------------------------------------------

    def _extract_content(self, url: str) -> tuple[Optional[str], str, str]:
        """
        Try extraction methods in priority order.
        Returns (content_text, method_name, article_title).
        """

        # ── Method 1: Newspaper3k ────────────────────────────────────
        try:
            from newspaper import Article
            cfg = _get_newspaper_config()
            article = Article(url, config=cfg) if cfg else Article(url)
            article.download()
            article.parse()

            text  = (article.text  or "").strip()
            title = (article.title or "").strip()

            if len(text.split()) >= 50:
                logger.debug(f"Newspaper3k: {len(text.split())} words, title={title[:50]!r}")
                return text, "newspaper3k", title

            logger.debug(f"Newspaper3k: only {len(text.split())} words — trying next")
        except Exception as exc:
            logger.debug(f"Newspaper3k failed [{type(exc).__name__}]: {str(exc)[:80]}")

        # ── Method 2: Trafilatura ────────────────────────────────────
        try:
            import trafilatura
            downloaded = trafilatura.fetch_url(url)
            if downloaded:
                text = trafilatura.extract(
                    downloaded,
                    include_comments=False,
                    include_tables=False,
                    no_fallback=False,
                )
                if text and len(text.split()) >= 50:
                    meta  = trafilatura.extract_metadata(downloaded)
                    title = (meta.title if meta and hasattr(meta, "title") else "") or ""
                    logger.debug(f"Trafilatura: {len(text.split())} words")
                    return text, "trafilatura", title

            logger.debug("Trafilatura: insufficient content")
        except Exception as exc:
            logger.debug(f"Trafilatura failed [{type(exc).__name__}]: {str(exc)[:80]}")

        # ── Method 3: BeautifulSoup paragraph scraper ────────────────
        try:
            from bs4 import BeautifulSoup
            headers = {
                "User-Agent": (
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/122.0.0.0 Safari/537.36"
                ),
                "Accept-Language": "en-US,en;q=0.9",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            }
            resp = requests.get(url, headers=headers, timeout=15)
            soup = BeautifulSoup(resp.text, "html.parser")

            title_tag = soup.find("h1") or soup.find("title")
            title = title_tag.get_text(strip=True) if title_tag else ""

            for tag in soup(["script", "style", "nav", "footer", "header",
                              "aside", "form", "noscript", "iframe"]):
                tag.decompose()

            # Prefer article container over full page
            container = (
                soup.find("article") or
                soup.find(attrs={"class": re.compile(r"article|content|story|post", re.I)}) or
                soup.find("main") or
                soup
            )

            paras = container.find_all("p")
            text  = " ".join(
                p.get_text(separator=" ", strip=True)
                for p in paras
                if len(p.get_text(strip=True).split()) > 6
            )

            if len(text.split()) >= 50:
                logger.debug(f"BeautifulSoup: {len(text.split())} words")
                return text, "beautifulsoup", title

            logger.debug("BeautifulSoup: insufficient content")
        except Exception as exc:
            logger.debug(f"BeautifulSoup failed [{type(exc).__name__}]: {str(exc)[:80]}")

        logger.warning(f"All extraction methods failed: {url}")
        return None, "failed", ""

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _failure_response(title: str, method: str, reason: str) -> dict:
        """Structured failure response — never returns HTTP 500."""
        return {
            "success":            False,
            "title":              title,
            "summary":            reason,
            "word_count":         0,
            "summary_word_count": 0,
            "extraction_method":  method,
            "stock_mentions":     [],
            "sentiment_label":    "Neutral",
            "sentiment_score":    0.0,
            "confidence":         0.0,
            "impact_type":        "Unknown",
            "reasoning":          "Content extraction failed.",
        }


# ---------------------------------------------------------------------------
# Singleton
# ---------------------------------------------------------------------------
summarizer_service = SummarizerService(max_sentences=3)
