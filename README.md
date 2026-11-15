# FinSentiq — Indian Stock Market Intelligence Platform
## High-Concurrency Cloud Architecture (FastAPI + React 18 TypeScript)

FinSentiq is an institutional-grade financial intelligence engine that monitors real-time news across the Indian Stock Market (NSE/BSE), quantifies market sentiment using Groq LLM (Llama 3.3 70B), and surfaces real-time sector catalysts.

---

## 🏛️ Clean Architecture

```
FinSentiq/
├── backend/                        # FastAPI Asynchronous ASGI Engine
│   ├── app/
│   │   ├── api/                    # REST Endpoints (/api/v1/news, /api/v1/watchlist)
│   │   ├── core/                   # Configuration, Settings & Persistent Central Store
│   │   ├── services/               # Async RSS Engine, Groq Sentiment, Sector Ticker Engine
│   │   ├── schemas/                # Strict Pydantic v2 Contracts
│   │   ├── company.csv             # NSE/BSE Master Ticker Dataset
│   │   └── main.py                 # FastAPI Application with Lifespan Background Workers
│   ├── requirements.txt            # Python Dependencies
│   └── Dockerfile                  # Cloud Container Definition
│
├── frontend/                       # Modern React 18 + Vite + Tailwind CSS
│   ├── src/
│   │   ├── api/                    # Axios API Client
│   │   ├── components/             # SectorHeatmap, MarketMovers, ArticleCard, Navbar
│   │   ├── types/                  # TypeScript Data Models
│   │   ├── App.tsx                 # Real-time Reactive Dashboard
│   │   └── main.tsx
│   ├── package.json
│   ├── tailwind.config.js
│   └── vite.config.ts
│
├── docker-compose.yml              # Local & Cloud Multi-container Orchestration
├── .gitignore                      # Security & Secret protection
└── README.md
```

---

## ⚡ Zero User-Triggered Feed Reloads (Performance Guarantee)

FinSentiq is engineered for high concurrency:
1. **Background Async Ingestion:** An asynchronous background worker (`APScheduler`) polls RSS feeds periodically and computes Groq sentiment scores in batches.
2. **Central Pre-populated Store:** Market data and sector sentiment are stored in an in-memory thread-safe store backed by local persistence.
3. **Sub-2ms Client Latency:** User visits or page refreshes **never trigger external feed fetches or LLM calls**, eliminating rate-limit spikes and guaranteeing sub-2ms response times.
4. **Client-side Caching:** TanStack Query prevents duplicate network requests on window/tab focus.

---

## 🚀 Quickstart

### 1. Backend (FastAPI)
```bash
cd backend
python -m venv venv
venv\Scripts\activate   # On Windows
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```
API Documentation: `http://localhost:8000/docs`

### 2. Frontend (React 18 + Vite)
```bash
cd frontend
npm install
npm run dev
```
Dashboard: `http://localhost:5173`

### 3. Docker (Full Stack)
```bash
docker-compose up --build
```
