# FinSentiq — Indian Stock Market Intelligence Platform
## Backend Architecture v2.0

---

## Module Overview

```
finsentiq_backend/
├── app.py                  # Application factory, auth routes, watchlist routes, entry point
├── news_routes.py          # News Analyzer blueprint (all /api/... + /news-analyzer)
├── rss_service.py          # Multi-threaded RSS feed aggregation (ThreadPoolExecutor)
├── sentiment_service.py    # Groq LLM sentiment engine + lexicon fallback
├── sector_service.py       # Sector classification + stock symbol extraction
├── summarizer_service.py   # Extractive summarization + full-text extraction pipeline
├── cache_service.py        # Thread-safe TTL cache (namespace-scoped)
├── duplicate_service.py    # Hash-based sliding-window deduplication
└── company.csv             # NSE/BSE company master (symbols, names, sectors)
```

---

## Key Architectural Decisions

### 1. Modular Blueprint Architecture
The news analyzer is a Flask Blueprint (`news_bp`) completely decoupled from auth and watchlist. Each domain can be deployed, tested, or scaled independently.

### 2. Groq Sentiment Engine — Strict JSON Schema
The sentiment engine enforces a strict output contract:
```json
{
  "sentiment_label": "Positive | Neutral | Negative",
  "sentiment_score": -10.0 to +10.0,
  "confidence": 0.0 to 1.0,
  "impact_type": "Earnings | Regulatory | Macro | Corporate Action | Management | Sector | Unknown",
  "reasoning": "<max 120 chars>"
}
```
Temperature=0 ensures deterministic, reproducible outputs for the same headline.

### 3. Three-Layer Sentiment Scoring
Every article's raw sentiment_score is modified by:
1. **Source weight** — High-quality financial sources (ET, Business Standard, Livemint) get 1.15–1.30x multiplier; aggregators get 0.85–0.90x
2. **Time decay** — Score halves every 6 hours: `decay = 0.5^(age_hours/6)`. A 12-hour old article has 25% of the signal weight of a fresh one.
3. **Lexicon fallback** — If Groq is unavailable, rule-based scoring activates automatically. Same output shape, lower confidence.

### 4. Hash-Based Deduplication
SHA-256 of normalized title (lowercase, no punctuation, stop-words removed, tokens sorted) enables order-independent duplicate detection. "Reliance Q3 profit rises" and "Q3 profit rises: Reliance" produce the same hash. URL hashing catches reposts with different headline wording.

### 5. ThreadPoolExecutor for RSS Fetching
`ThreadPoolExecutor(max_workers=20)` replaces raw `threading.Thread` management:
- Bounded thread pool (no unbounded spawning under load)
- `as_completed()` with per-feed timeout isolation
- One failing feed never blocks others

### 6. Cache Namespace Scoping
```python
cache.set("sector_articles", data, ttl=600, namespace="news")
cache.set("gainers_losers",  data, ttl=600, namespace="news")
cache.flush_namespace("news")  # Atomic invalidation of all news keys
```
Prevents cache key collisions if cache is extended to other domains.

### 7. Zero-Redundancy CSV Loading
`company.csv` is loaded **once** at `sector_service.py` import time and exposed as module-level sets/dicts (`VALID_SYMBOLS`, `COMPANY_TO_SYMBOL`, `SYMBOL_TO_SECTOR`). All services import from this single source.

---

## Sentiment Score Interpretation

| Score Range | Label    | Signal                          |
|-------------|----------|---------------------------------|
| +6 to +10   | Positive | Strong bullish catalyst         |
| +2 to +5.9  | Positive | Moderate positive news          |
| -1.9 to +1.9| Neutral  | Informational, limited impact   |
| -2 to -5.9  | Negative | Moderate negative news          |
| -6 to -10   | Negative | Strong bearish catalyst         |

---

## API Endpoints

| Method | Endpoint                    | Description                              |
|--------|-----------------------------|------------------------------------------|
| GET    | `/news-analyzer`            | Main dashboard (HTML)                    |
| GET    | `/api/sector/<name>`        | Articles for one sector (JSON)           |
| GET    | `/api/market-summary`       | Cross-sector sentiment overview (JSON)   |
| GET    | `/api/summarize?url=<url>`  | Full article extraction + summary (JSON) |
| GET    | `/api/feed-health`          | RSS feed health + cache stats (JSON)     |
| POST   | `/api/refresh-cache`        | Force cache invalidation (JSON)          |
| GET    | `/health`                   | App health check (JSON)                  |

---

## Environment Variables

```env
GROQ_API_KEY=gsk_...          # Required for LLM sentiment
FLASK_SECRET_KEY=...          # Required in production
PORT=5000                     # Optional, default 5000
```

---

## Performance Profile

| Operation              | Latency      | Notes                                |
|------------------------|-------------|--------------------------------------|
| Dashboard (cache hit)  | < 50ms       | Pure template render                 |
| Dashboard (cache miss) | 15–45s       | Full 30-feed parallel fetch          |
| Sentiment (Groq)       | 200–600ms    | Per article, batched in threads      |
| Sentiment (fallback)   | < 1ms        | Lexicon scoring, no network          |
| Duplicate check        | O(1)         | Hash set lookup                      |
| Summarization          | < 5ms        | In-process extractive, no API        |
| Article extraction     | 2–8s         | Newspaper3k/Trafilatura + HTTP       |

---

## Dependencies

```
flask
feedparser
pandas
beautifulsoup4
requests
trafilatura
newspaper3k
groq
python-dotenv
werkzeug
```
