import os
import json
import logging
import time
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
    "Zee Business Hindi": 1.00,
    "Moneycontrol Hindi": 1.10,
    "CNBC TV18": 1.10
}

class SentimentEngine:
    def __init__(self):
        self.client = None
        self.active_model = settings.GROQ_MODEL
        self._rate_limited_until: float = 0.0
        if settings.GROQ_API_KEY:
            # Set max_retries=0 to avoid blocking retry loops on 429
            self.client = AsyncGroq(api_key=settings.GROQ_API_KEY, max_retries=0)
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

    @staticmethod
    def detect_catalyst_type(text: str) -> str:
        """Classify article into institutional catalyst taxonomy."""
        t = text.lower()
        if any(w in t for w in ["q1", "q2", "q3", "q4", "results", "quarterly", "net profit", "revenue", "ebitda", "pat", "margin"]):
            return "Earnings & Results"
        if any(w in t for w in ["rbi", "sebi", "penalty", "probe", "investigation", "court", "compliance", "fraud", "ban", "guidelines"]):
            return "Regulatory Action"
        if any(w in t for w in ["order win", "contract", "bagged", "capex", "expansion", "factory", "commission", "deal", "mou"]):
            return "Orders & Expansion"
        if any(w in t for w in ["dividend", "buyback", "demerger", "merger", "acquisition", "bonus", "stock split", "fundraise"]):
            return "Corporate Action"
        if any(w in t for w in ["fda", "anda", "drug approval", "usfda", "pharma", "clinical"]):
            return "Pharma Approvals"
        if any(w in t for w in ["repo rate", "inflation", "crude", "rupee", "fii", "dii", "gdp", "trade deficit"]):
            return "Macro & Policy"
        return "Market Catalyst"

    def lexicon_score(self, text: str) -> Dict[str, Any]:
        """
        Institutional context-aware financial sentiment analyzer.
        Correctly parses compound earnings phrases (e.g. 'profit falls', 'loss narrows').
        """
        import re
        t = text.lower()
        score = 0.0
        label = "Neutral"
        reason = ""

        # 1. High-Conviction Earnings Phrase Detection
        # A. Profit/Revenue decline (e.g., "profit falls 19%", "revenue drops")
        if re.search(r'\b(profit|pat|revenue|sales|ebitda|income|margin)\b.{1,25}\b(fall|falls|fell|drop|drops|dropped|decline|declines|plunge|plunges|down|slip|slips|shrink|shrinks|contract|narrow)\b', t) or \
           re.search(r'\b(fall|falls|fell|drop|drops|dropped|decline|declines|plunge|plunges|down|slip|slips)\b.{1,25}\b(profit|pat|revenue|sales|ebitda|income|margin)\b', t):
            score = -6.0
            label = "Negative"
            reason = "Financial results decline: Profit / revenue / margin compression detected"

        # B. Loss widens / posts net loss
        elif re.search(r'\b(loss|losses)\b.{1,25}\b(widen|widens|widened|expand|expands|rise|surge|increase)\b', t) or re.search(r'\b(net loss|posts loss)\b', t):
            score = -5.0
            label = "Negative"
            reason = "Loss expansion or net loss reported"

        # C. Loss narrows (Bullish turnaround)
        elif re.search(r'\b(loss|losses)\b.{1,25}\b(narrow|narrows|narrowed|shrink|shrinks|cut)\b', t):
            score = 5.0
            label = "Positive"
            reason = "Turnaround catalyst: Quarterly loss narrowed significantly"

        # D. Profit/Revenue surge (e.g. "profit rises 15%", "revenue jumps")
        elif re.search(r'\b(profit|pat|revenue|sales|ebitda|income|margin)\b.{1,25}\b(rise|rises|rose|surge|surges|jump|jumps|up|grow|grows|growth|beat|beats|spike|spikes|double|doubles)\b', t) or \
             re.search(r'\b(rise|rises|rose|surge|surges|jump|jumps|growth|spike|spikes)\b.{1,25}\b(profit|pat|revenue|sales|ebitda|income|margin)\b', t):
            score = 6.0
            label = "Positive"
            reason = "Strong earnings beat: Profit / revenue expansion reported"

        # 2. General Corporate Actions (Buyback, Order Win, SEBI Penalty)
        elif any(w in t for w in ["buyback", "share buyback", "order win", "bagged order", "contract win"]):
            score = 5.5
            label = "Positive"
            reason = "Positive corporate action: Buyback or order win announced"

        elif any(w in t for w in ["penalty", "probe", "investigation", "fraud", "auditor resigns", "pledge"]):
            score = -5.5
            label = "Negative"
            reason = "Regulatory governance risk: Probe / penalty detected"

        # 3. Fallback to Keyword Density
        else:
            words = set(re.findall(r'\b[a-z]{3,}\b', t))
            bull_count = sum(1 for w in words if w in BULLISH_KEYWORDS)
            bear_count = sum(1 for w in words if w in BEARISH_KEYWORDS)
            net = bull_count - bear_count
            if net > 0:
                label = "Positive"
                score = min(8.0, round(net * 2.5, 1))
                reason = f"Keyword density: {bull_count} positive signals"
            elif net < 0:
                label = "Negative"
                score = max(-8.0, round(net * 2.5, 1))
                reason = f"Keyword density: {bear_count} negative signals"
            else:
                label = "Neutral"
                score = 0.0
                reason = "Balanced sentiment signals"

        catalyst = self.detect_catalyst_type(text)

        return {
            "sentiment_label": label,
            "sentiment_score": score,
            "confidence": 0.85 if abs(score) >= 5.0 else 0.65,
            "impact_type": catalyst,
            "reasoning": reason
        }

    async def analyze_sentiment(self, title: str, summary: Optional[str] = None) -> Dict[str, Any]:
        """Analyze sentiment via Groq Async LLM with strict JSON schema."""
        combined_text = title + " " + (summary or "")
        
        # If no client or currently in rate-limit cooldown, use contextual financial grammar immediately
        if not self.client or time.time() < self._rate_limited_until:
            return self.lexicon_score(combined_text)

        # Trim summary to save tokens and prevent exceeding Groq TPM limits
        clean_summary = ""
        if summary:
            # Strip excessive whitespace / HTML artifacts and cap at 140 chars
            clean_summary = " ".join(summary.split())[:140]

        prompt = f"""Analyze Indian market catalyst (NSE/BSE).
Title: {title}
{f"Context: {clean_summary}" if clean_summary else ""}

Return JSON ONLY:
{{
  "sentiment_label": "Positive" | "Neutral" | "Negative",
  "sentiment_score": <float -10.0 to 10.0>,
  "confidence": <float 0.0 to 1.0>,
  "impact_type": "Earnings" | "Regulatory" | "Macro" | "Corporate Action" | "Management" | "Sector" | "Unknown",
  "reasoning": "<under 80 chars>"
}}"""
        try:
            import asyncio
            candidate_models = [self.active_model, "openai/gpt-oss-120b", "qwen/qwen3.8-27b"]
            last_err = None

            for model_name in candidate_models:
                try:
                    response = await asyncio.wait_for(
                        self.client.chat.completions.create(
                            model=model_name,
                            messages=[
                                {"role": "system", "content": "You are a specialized financial sentiment classification system. Return valid JSON only."},
                                {"role": "user", "content": prompt}
                            ],
                            temperature=0.0,
                            response_format={"type": "json_object"}
                        ),
                        timeout=3.0
                    )
                    content = response.choices[0].message.content
                    data = json.loads(content)
                    self.active_model = model_name
                    # Ensure valid bounds
                    data["sentiment_score"] = max(-10.0, min(10.0, float(data.get("sentiment_score", 0.0))))
                    data["confidence"] = max(0.0, min(1.0, float(data.get("confidence", 0.85))))
                    return data
                except Exception as me:
                    err_str = str(me)
                    last_err = me
                    if "429" in err_str or "rate_limit" in err_str.lower():
                        self._rate_limited_until = time.time() + 5.0
                        logger.info("Groq free-tier rate limit (429) reached. Seamlessly routing to contextual financial grammar engine.")
                        return self.lexicon_score(combined_text)
                    if "model_not_found" in err_str or "404" in err_str:
                        continue
                    raise me

            if last_err:
                raise last_err

        except Exception as e:
            err_msg = str(e)
            if "429" in err_msg or "rate_limit" in err_msg.lower():
                self._rate_limited_until = time.time() + 5.0
                logger.info("Groq free-tier rate limit (429) reached. Seamlessly routing to contextual financial grammar engine.")
            elif "expired_api_key" in err_msg or "401" in err_msg:
                logger.warning(f"Groq API Key invalid ({err_msg}). Operating with financial grammar lexicon engine.")
                self.client = None
            else:
                logger.debug(f"Groq fallback to lexicon: {e}")
            return self.lexicon_score(combined_text)

sentiment_engine = SentimentEngine()
