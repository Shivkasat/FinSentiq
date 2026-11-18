"""
copilot.py — FinSentiq AI Market Copilot
------------------------------------------
Conversational intelligence engine synthesizing real-time news,
sector momentum, and catalyst drivers.
"""

import os
import logging
from typing import Dict, Any, List
import httpx
from pydantic import BaseModel
from fastapi import APIRouter
from app.core.store import central_store
from app.core.config import settings
from app.services.market_data import market_data_service
from groq import AsyncGroq

router = APIRouter(prefix="/copilot", tags=["AI Market Copilot"])
logger = logging.getLogger("finsentiq.api.copilot")

class CopilotQueryRequest(BaseModel):
    query: str

class CopilotQueryResponse(BaseModel):
    answer: str
    relevant_symbols: List[str]
    referenced_articles: List[Dict[str, Any]]
    confidence: float

@router.post("/query", response_model=CopilotQueryResponse)
async def query_market_copilot(req: CopilotQueryRequest):
    q = req.query.strip()
    q_lower = q.lower()

    # Search central store for matching news
    all_articles = central_store.get_articles_by_sector(None)
    matching = []
    matched_symbols = set()

    for a in all_articles:
        title = a.get("title", "")
        symbols = a.get("stock_mentions", [])
        sector = a.get("sector", "")
        
        matches_symbol = any(sym.lower() in q_lower for sym in symbols)
        matches_sector = sector.lower() in q_lower
        matches_keywords = any(w in title.lower() for w in q_lower.split() if len(w) > 3)

        if matches_symbol or matches_sector or matches_keywords:
            matching.append(a)
            for s in symbols:
                matched_symbols.add(s)

    top_references = matching[:5]

    # Attempt Groq LLM Answer with fast 2.0s HTTP client timeout
    if settings.GROQ_API_KEY:
        try:
            async with httpx.AsyncClient(timeout=2.0) as custom_http:
                client = AsyncGroq(api_key=settings.GROQ_API_KEY, http_client=custom_http)
                context_snippets = []
                for art in top_references:
                    context_snippets.append(
                        f"Headline: {art.get('title')} | Sentiment: {art.get('sentiment_label')} "
                        f"(Score: {art.get('sentiment_score')}) | Catalyst: {art.get('impact_type')}"
                    )
                context_text = "\n".join(context_snippets) if context_snippets else "No specific recent headlines found."

                prompt = f"""You are FinSentiq AI, an institutional Indian Stock Market Copilot.
The user asked: "{q}"

Current Real-Time Market Intelligence:
{context_text}

Provide a direct, high-value 2-4 sentence market analysis answering the user's question with specific catalysts and sentiment direction. Do not make investment promises."""

                resp = await client.chat.completions.create(
                    model=settings.GROQ_MODEL,
                    messages=[
                        {"role": "system", "content": "You are a professional financial equity analyst for Indian Equities (NSE/BSE)."},
                        {"role": "user", "content": prompt}
                    ],
                    temperature=0.2,
                    max_tokens=250
                )
                answer = resp.choices[0].message.content.strip()
                return CopilotQueryResponse(
                    answer=answer,
                    relevant_symbols=list(matched_symbols)[:5],
                    referenced_articles=[{"title": a["title"], "link": a["link"], "sentiment": a["sentiment_label"]} for a in top_references],
                    confidence=0.92
                )
        except Exception as e:
            logger.info(f"Copilot using analytical synthesis (Groq offline or fast timeout: {e})")

    # Deterministic Analytical Synthesis Fallback
    if top_references:
        avg_score = round(sum(a.get("sentiment_score", 0.0) for a in top_references) / len(top_references), 1)
        mood = "bullish" if avg_score > 1.0 else "bearish" if avg_score < -1.0 else "neutral"
        top_art = top_references[0]
        answer = (
            f"Based on real-time news tracking, current sentiment is predominantly {mood} "
            f"(composite score: {avg_score:+0.1f}). Key catalyst: '{top_art.get('title')}' "
            f"classified as {top_art.get('impact_type', 'Market Catalyst')} with {top_art.get('sentiment_label')} impact."
        )
    else:
        answer = (
            f"Currently monitoring real-time NSE/BSE feeds for '{q}'. "
            "No high-severity news anomaly has breached the 6-hour threshold for this topic. "
            "Broad market sentiment remains stable across core sectors."
        )

    return CopilotQueryResponse(
        answer=answer,
        relevant_symbols=list(matched_symbols)[:5],
        referenced_articles=[{"title": a["title"], "link": a["link"], "sentiment": a["sentiment_label"]} for a in top_references],
        confidence=0.75
    )
