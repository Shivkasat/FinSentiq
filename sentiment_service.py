"""
sentiment_service.py — Sentix Intelligence Platform
-----------------------------------------------------
Institutional-grade sentiment analysis engine for Indian equity news.

Architecture:
  Primary  → Groq LLM (llama-3.1-8b-instant) with strict JSON output schema
  Fallback → Rule-based lexicon scoring (zero-latency, zero-cost)

Sentiment schema (per article):
  {
    "sentiment_label" : "Positive" | "Neutral" | "Negative",
    "sentiment_score" : float  [-10.0 … +10.0],
    "confidence"      : float  [0.0 … 1.0],
    "impact_type"     : "Earnings" | "Regulatory" | "Macro" | "Corporate Action"
                        | "Management" | "Sector" | "Unknown",
    "reasoning"       : str    (max 120 chars — concise analyst note)
  }

Key design decisions:
  - Strict JSON schema enforced in system prompt — no markdown leakage
  - Temperature=0 for deterministic, reproducible classification
  - Per-article retry with exponential backoff on transient Groq errors
  - Source weight multiplier applied AFTER base sentiment computation
  - Time-decay applied AFTER source-weighted score
  - All scoring paths produce identical output shape for downstream consumers
"""

import os
import re
import json
import time
import logging
from dataclasses import dataclass, asdict
from typing import Optional

from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger("sentix.sentiment")


# ---------------------------------------------------------------------------
# Sentiment result dataclass — strict output contract
# ---------------------------------------------------------------------------

@dataclass
class SentimentResult:
    sentiment_label: str           # Positive | Neutral | Negative
    sentiment_score: float         # -10.0 to +10.0
    confidence: float              # 0.0 to 1.0
    impact_type: str               # Earnings | Regulatory | Macro | ...
    reasoning: str                 # Short analyst note

    def to_dict(self) -> dict:
        return asdict(self)

    @property
    def is_positive(self) -> bool:
        return self.sentiment_label == "Positive"

    @property
    def is_negative(self) -> bool:
        return self.sentiment_label == "Negative"


# ---------------------------------------------------------------------------
# Source weight registry
# Weights reflect editorial quality and market-moving credibility
# Scores are multipliers applied on top of the raw LLM sentiment_score
# ---------------------------------------------------------------------------

SOURCE_WEIGHTS: dict[str, float] = {
    # Tier 1 — high institutional credibility
    "economic_times_market":    1.30,
    "economic_times_stocks":    1.30,
    "business_standard":        1.25,
    "business_standard_companies": 1.25,
    "livemint":                 1.20,
    "livemint_companies":       1.20,
    "bq_prime_markets":         1.20,
    "bq_prime_business":        1.20,
    "hindu_business_line":      1.15,
    "financial_express":        1.15,

    # Tier 2 — mainstream financial media
    "moneycontrol":             1.10,
    "moneycontrol_markets":     1.10,
    "moneycontrol_stocks":      1.10,
    "cnbc_market":              1.10,
    "cnbc_business":            1.10,
    "ndtv_business":            1.05,
    "zeebiz":                   1.05,
    "zeebiz_stocks":            1.05,

    # Tier 3 — aggregators & general business news
    "google_india_stocks":      0.90,
    "google_sensex":            0.90,
    "google_nifty":             0.90,
    "google_india_business":    0.90,
    "reuters_india":            1.15,
    "investing_india":          1.00,
    "business_today_markets":   1.00,
    "toi_business":             0.85,
    "india_today_business":     0.80,
}

DEFAULT_SOURCE_WEIGHT = 1.00


# ---------------------------------------------------------------------------
# Time-decay parameters
# News freshness model: value halves every `HALF_LIFE_HOURS` hours
# ---------------------------------------------------------------------------

HALF_LIFE_HOURS: float = 6.0   # Sentiment impact halves every 6 hours

def compute_time_decay(published_timestamp: Optional[float]) -> float:
    """
    Returns a decay multiplier ∈ (0, 1].
    Formula: decay = 0.5 ^ (age_hours / HALF_LIFE_HOURS)
    Very recent news → ~1.0; 24h old → ~0.06; 6h old → ~0.5
    """
    if published_timestamp is None:
        return 0.75  # Unknown age → moderate decay assumed

    age_seconds = max(0, time.time() - published_timestamp)
    age_hours = age_seconds / 3600
    decay = 0.5 ** (age_hours / HALF_LIFE_HOURS)
    return round(decay, 4)


# ---------------------------------------------------------------------------
# Lexicon-based fallback engine
# ---------------------------------------------------------------------------

_POSITIVE_LEXICON = frozenset({
    "profit", "growth", "up", "rise", "gain", "surge", "bullish", "positive",
    "beat", "strong", "earnings", "revenue", "high", "record", "boost",
    "rally", "jump", "soar", "upgrade", "outperform", "buy", "overweight",
    "expansion", "margin", "order win", "contract", "healthy", "robust",
    "momentum", "recovery", "upside", "breakout", "dividend", "bonus",
})

_NEGATIVE_LEXICON = frozenset({
    "loss", "down", "fall", "decline", "crash", "bearish", "negative",
    "miss", "weak", "drop", "slump", "plunge", "tumble", "collapse",
    "worry", "fear", "downgrade", "underperform", "sell", "underweight",
    "contraction", "warning", "probe", "investigation", "npa", "default",
    "delay", "withdrawal", "shortfall", "writeoff", "impairment", "fraud",
})

def _lexicon_sentiment(text: str) -> SentimentResult:
    """Zero-latency fallback when Groq is unavailable."""
    lower = text.lower()
    pos = sum(1 for w in _POSITIVE_LEXICON if w in lower)
    neg = sum(1 for w in _NEGATIVE_LEXICON if w in lower)

    if pos > neg:
        score = min(10.0, (pos - neg) * 1.5)
        return SentimentResult(
            sentiment_label="Positive",
            sentiment_score=round(score, 2),
            confidence=0.55,
            impact_type="Unknown",
            reasoning="Lexicon fallback: positive terms dominate",
        )
    elif neg > pos:
        score = max(-10.0, -((neg - pos) * 1.5))
        return SentimentResult(
            sentiment_label="Negative",
            sentiment_score=round(score, 2),
            confidence=0.55,
            impact_type="Unknown",
            reasoning="Lexicon fallback: negative terms dominate",
        )
    else:
        return SentimentResult(
            sentiment_label="Neutral",
            sentiment_score=0.0,
            confidence=0.50,
            impact_type="Unknown",
            reasoning="Lexicon fallback: balanced or no sentiment signals",
        )


# ---------------------------------------------------------------------------
# Groq LLM engine
# ---------------------------------------------------------------------------

_GROQ_SYSTEM_PROMPT = """You are an institutional equity research analyst specializing in Indian stock markets (NSE/BSE).

Your task: Analyze the following financial news headline/excerpt and return a structured JSON sentiment assessment.

OUTPUT RULES — STRICT:
- Respond with ONLY valid JSON. No markdown, no code fences, no explanation.
- All fields are REQUIRED.
- sentiment_score: float between -10.0 (extremely bearish) and +10.0 (extremely bullish). 0.0 = neutral.
- confidence: float between 0.0 and 1.0.
- impact_type must be one of: "Earnings", "Regulatory", "Macro", "Corporate Action", "Management", "Sector", "Unknown"
- reasoning: max 120 characters, concise analyst perspective on market impact.

JSON SCHEMA:
{
  "sentiment_label": "Positive" | "Neutral" | "Negative",
  "sentiment_score": <float -10.0 to 10.0>,
  "confidence": <float 0.0 to 1.0>,
  "impact_type": "Earnings" | "Regulatory" | "Macro" | "Corporate Action" | "Management" | "Sector" | "Unknown",
  "reasoning": "<max 120 chars>"
}

Examples of correct output:
{"sentiment_label":"Positive","sentiment_score":7.5,"confidence":0.88,"impact_type":"Earnings","reasoning":"Strong Q3 beat with margin expansion signals healthy operating leverage."}
{"sentiment_label":"Negative","sentiment_score":-6.0,"confidence":0.82,"impact_type":"Regulatory","reasoning":"SEBI probe triggers uncertainty and could dampen institutional buying."}
{"sentiment_label":"Neutral","sentiment_score":1.5,"confidence":0.65,"impact_type":"Macro","reasoning":"Policy update with moderate positive bias; market impact depends on implementation."}"""


def _parse_groq_response(raw: str) -> Optional[SentimentResult]:
    """Parse and validate Groq JSON response. Returns None on parse failure."""
    try:
        # Strip any accidental markdown or whitespace
        clean = re.sub(r"```(?:json)?", "", raw).strip()
        data = json.loads(clean)

        label = data.get("sentiment_label", "Neutral")
        if label not in ("Positive", "Neutral", "Negative"):
            label = "Neutral"

        score = float(data.get("sentiment_score", 0.0))
        score = max(-10.0, min(10.0, score))

        conf = float(data.get("confidence", 0.7))
        conf = max(0.0, min(1.0, conf))

        impact = data.get("impact_type", "Unknown")
        valid_impacts = {"Earnings", "Regulatory", "Macro", "Corporate Action",
                         "Management", "Sector", "Unknown"}
        if impact not in valid_impacts:
            impact = "Unknown"

        reasoning = str(data.get("reasoning", ""))[:120]

        return SentimentResult(
            sentiment_label=label,
            sentiment_score=score,
            confidence=conf,
            impact_type=impact,
            reasoning=reasoning,
        )
    except (json.JSONDecodeError, ValueError, TypeError) as exc:
        logger.warning(f"Groq response parse failure: {exc} | raw={raw[:200]}")
        return None


# ---------------------------------------------------------------------------
# Main SentimentService
# ---------------------------------------------------------------------------

class SentimentService:
    """
    Unified sentiment analysis service.

    Usage:
        result = sentiment_service.analyze(title, description, source_key, pub_ts)
        print(result.sentiment_label, result.sentiment_score)
    """

    def __init__(self):
        self._groq_available = False
        self._groq_client = None
        self._init_groq()

    def _init_groq(self) -> None:
        api_key = os.getenv("GROQ_API_KEY")
        if not api_key:
            logger.warning("GROQ_API_KEY not set — using lexicon fallback only")
            return

        try:
            from groq import Groq
            self._groq_client = Groq(api_key=api_key)
            # Connectivity check with minimal tokens
            self._groq_client.chat.completions.create(
                model="llama-3.1-8b-instant",
                messages=[{"role": "user", "content": "ping"}],
                max_tokens=5,
                temperature=0,
            )
            self._groq_available = True
            logger.info("✅ Groq LLM engine connected")
        except Exception as exc:
            logger.warning(f"Groq init failed: {exc} — fallback active")
            self._groq_available = False

    def analyze(
        self,
        title: str,
        description: str = "",
        source_key: str = "",
        published_timestamp: Optional[float] = None,
        max_retries: int = 2,
    ) -> SentimentResult:
        """
        Full pipeline:
          1. Base sentiment via Groq (or fallback)
          2. Apply source credibility weight to score
          3. Apply time-decay to weighted score
          4. Return final SentimentResult
        """
        text = f"{title}. {description}".strip()[:1200]  # Token budget cap

        # Step 1: Base sentiment
        base_result = self._groq_analyze(text, max_retries) if self._groq_available \
            else _lexicon_sentiment(text)

        # Step 2: Source weight
        source_weight = SOURCE_WEIGHTS.get(source_key, DEFAULT_SOURCE_WEIGHT)

        # Step 3: Time-decay
        decay = compute_time_decay(published_timestamp)

        # Apply weights: score is scaled but label/confidence unchanged
        weighted_score = base_result.sentiment_score * source_weight * decay
        weighted_score = round(max(-10.0, min(10.0, weighted_score)), 2)

        return SentimentResult(
            sentiment_label=base_result.sentiment_label,
            sentiment_score=weighted_score,
            confidence=base_result.confidence,
            impact_type=base_result.impact_type,
            reasoning=base_result.reasoning,
        )

    def _groq_analyze(self, text: str, max_retries: int) -> SentimentResult:
        """Call Groq with retry + exponential backoff."""
        last_exc = None

        for attempt in range(1, max_retries + 1):
            try:
                response = self._groq_client.chat.completions.create(
                    model="llama-3.1-8b-instant",
                    messages=[
                        {"role": "system", "content": _GROQ_SYSTEM_PROMPT},
                        {"role": "user", "content": f'Analyze: "{text}"'},
                    ],
                    max_tokens=200,
                    temperature=0,
                )

                raw = response.choices[0].message.content.strip()
                result = _parse_groq_response(raw)

                if result:
                    logger.debug(
                        f"Groq sentiment: {result.sentiment_label} "
                        f"({result.sentiment_score:+.1f}) conf={result.confidence:.2f}"
                    )
                    return result

                logger.warning(f"Groq attempt {attempt}: invalid JSON response")

            except Exception as exc:
                last_exc = exc
                wait = 2 ** attempt
                logger.warning(f"Groq attempt {attempt} failed: {exc}. Retrying in {wait}s")
                time.sleep(wait)

        logger.error(f"Groq exhausted retries. Using lexicon fallback. Last: {last_exc}")
        return _lexicon_sentiment(text)

    def analyze_batch(
        self,
        articles: list[dict],
        source_key: str = "",
    ) -> list[SentimentResult]:
        """
        Analyze a batch of articles. Throttles to avoid Groq rate limits.
        Each article dict expected to have 'title' and optionally 'description', 'published_ts'.
        """
        results = []
        for i, article in enumerate(articles):
            result = self.analyze(
                title=article.get("title", ""),
                description=article.get("description", ""),
                source_key=source_key,
                published_timestamp=article.get("published_ts"),
            )
            results.append(result)

            # Throttle: ~50 requests/minute to stay within free tier limits
            if i > 0 and i % 10 == 0:
                time.sleep(0.5)

        return results


# ---------------------------------------------------------------------------
# Singleton instance
# ---------------------------------------------------------------------------
sentiment_service = SentimentService()
