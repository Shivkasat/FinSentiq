import os
import json
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone
import httpx
from groq import AsyncGroq
from app.core.config import settings

logger = logging.getLogger("finsentiq.sentiment")

# Financial Lexicon Fallback
BULLISH_KEYWORDS = {
    "surge", "jump", "rally", "gain", "profit", "growth", "high", "record",
    "expansion", "dividend", "upbeat", "bull", "upgrade", "outperform",
    "order win", "acquisition", "bonus", "buyback", "recovery", "positive"
}

BEARISH_KEYWORDS = {
    "drop", "fall", "plunge", "decline", "loss", "crash", "down", "low",
    "slump", "probe", "investigation", "penalty", "default", "downgrade",
    "underperform", "fraud", "scam", "weak", "bear", "layoff", "selloff"
}

SOURCE_WEIGHTS = {
    "Economic Times": 1.25,
    "Livemint": 1.20,
    "Business Standard": 1.20,
    "Financial Express": 1.15,
    "Moneycontrol": 1.15,
    "Reuters": 1.30,
    "Bloomberg": 1.30,
    "NDTV Profit": 1.05,
    "Zee Business": 1.00,
    "CNBC TV18": 1.10
}

class SentimentEngine:
    def __init__(self):
        self.client = None
        if settings.GROQ_API_KEY:
            self.client = AsyncGroq(api_key=settings.GROQ_API_KEY)
        else:
            logger.warning("GROQ_API_KEY not set. Operating with deterministic lexicon fallback.")

    @staticmethod
    def compute_time_decay(published_iso: Optional[str]) -> tuple[float, float]:
        """
        Calculates age in hours and decay multiplier.
        Decay formula: score halves every 6 hours (0.5 ^ (age_hours / 6))
        """
        if not published_iso:
            return 0.0, 1.0
        try:
            pub_dt = datetime.fromisoformat(published_iso)
            now = datetime.now(timezone.utc)
            if pub_dt.tzinfo is None:
                pub_dt = pub_dt.replace(tzinfo=timezone.utc)
            age_hours = max(0.0, (now - pub_dt).total_seconds() / 3600.0)
            decay = 0.5 ** (age_hours / 6.0)
            return round(age_hours, 2), round(max(0.05, decay), 3)
        except Exception:
            return 0.0, 1.0

    def lexicon_score(self, text: str) -> Dict[str, Any]:
        """Rule-based fallback when LLM is unavailable or for instant latency."""
        words = text.lower().split()
        bull_count = sum(1 for w in words if w in BULLISH_KEYWORDS)
        bear_count = sum(1 for w in words if w in BEARISH_KEYWORDS)

        net = bull_count - bear_count
        if net > 0:
            label = "Positive"
            score = min(10.0, round(net * 2.5, 1))
        elif net < 0:
            label = "Negative"
            score = max(-10.0, round(net * 2.5, 1))
        else:
            label = "Neutral"
            score = 0.0

        return {
            "sentiment_label": label,
            "sentiment_score": score,
            "confidence": 0.65 if net != 0 else 0.5,
            "impact_type": "Sector / Market Update",
            "reasoning": f"Lexical keyword density matched ({bull_count} positive, {bear_count} negative triggers)"
        }

    async def analyze_sentiment(self, title: str, summary: Optional[str] = None) -> Dict[str, Any]:
        """Analyze sentiment via Groq Async LLM with strict JSON schema."""
        if not self.client:
            return self.lexicon_score(title + " " + (summary or ""))

        prompt = f"""You are an elite quantitative financial analyst for the Indian Stock Market (NSE/BSE).
Analyze this headline for market catalyst and sentiment impact.

Headline: {title}
{f"Summary: {summary}" if summary else ""}

Respond ONLY with a JSON object adhering strictly to this schema:
{{
  "sentiment_label": "Positive" | "Neutral" | "Negative",
  "sentiment_score": <float between -10.0 (extreme bearish) to +10.0 (extreme bullish)>,
  "confidence": <float between 0.0 and 1.0>,
  "impact_type": "Earnings" | "Regulatory" | "Macro" | "Corporate Action" | "Management" | "Sector" | "Unknown",
  "reasoning": "<concise explanation under 100 characters>"
}}
"""
        try:
            response = await self.client.chat.completions.create(
                model=settings.GROQ_MODEL,
                messages=[
                    {"role": "system", "content": "You are a specialized financial sentiment classification system. Return valid JSON only."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.0,
                response_format={"type": "json_object"}
            )
            content = response.choices[0].message.content
            data = json.loads(content)
            # Ensure valid bounds
            data["sentiment_score"] = max(-10.0, min(10.0, float(data.get("sentiment_score", 0.0))))
            data["confidence"] = max(0.0, min(1.0, float(data.get("confidence", 0.8))))
            return data
        except Exception as e:
            if "expired_api_key" in str(e) or "401" in str(e):
                logger.warning("GROQ_API_KEY is invalid or expired. Switching to deterministic financial lexicon engine.")
                self.client = None
            else:
                logger.warning(f"Groq sentiment analysis failed, falling back to lexicon: {e}")
            return self.lexicon_score(title + " " + (summary or ""))

sentiment_engine = SentimentEngine()
