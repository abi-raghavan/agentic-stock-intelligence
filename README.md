# Agentic Stock Intelligence

Multi-agent stock intelligence for Indian (NSE/BSE) and US markets. Live news and market data. **Not financial advice.**

Live Demo: https://agentic-stock-intelligence.vercel.app/
**Stack:** Next.js · FastAPI · LangGraph · BM25 RAG · SQLite

## Run locally (no Docker)

Python 3.12 and Node 20 required.

```bash
git clone https://github.com/abi-raghavan/agentic-stock-intelligence.git
cd agentic-stock-intelligence
make local-setup
make local-api   # terminal 1
make local-web   # terminal 2
```

Open http://localhost:3000

Examples: `Tata Motors`, `RELIANCE.NS`, `TCS`, `NVDA`

## Deploy free (Render + Vercel)

Do this in order: **API first, then frontend.**

### 1. Render — API

1. Go to [render.com](https://render.com) and sign in with GitHub.
2. **New + → Web Service**.
3. Select `abi-raghavan/agentic-stock-intelligence`.
4. Settings:

| Field | Value |
|---|---|
| Name | `agentic-stock-api` |
| Region | Singapore (or closest) |
| Branch | `main` |
| Runtime | Python 3 |
| Build command | `pip install -r requirements.txt` |
| Start command | `uvicorn apps.api.main:app --host 0.0.0.0 --port $PORT` |
| Instance | **Free** |

5. Environment variables:

```
PYTHONPATH=.
ENABLE_LIVE_DATA=true
ENABLE_QDRANT=false
ENABLE_OLLAMA=false
SEED_DATA_ON_STARTUP=true
SAMPLE_DATA_DIR=sample_data
DATABASE_URL=sqlite:////tmp/stock_intel.db
CORS_ORIGINS=http://localhost:3000
```

6. Click **Deploy**. Wait until it is Live.
7. Copy the URL, e.g. `https://agentic-stock-api.onrender.com`.
8. Open `https://YOUR-API.onrender.com/health` — you should see `{"status":"ok"}`.

First request after idle can take 30–60s (free tier sleep).

### 2. Vercel — Web UI

1. Go to [vercel.com](https://vercel.com) and sign in with GitHub.
2. **Add New → Project** → `agentic-stock-intelligence`.
3. Settings:

| Field | Value |
|---|---|
| Framework | Next.js |
| Root Directory | `apps/web` (click Edit) |
| Build Command | `npm run build` |
| Output | default |

4. Environment variable:

```
NEXT_PUBLIC_API_URL=https://YOUR-API.onrender.com
```

Use the Render URL from step 1. No trailing slash.

5. Click **Deploy**. Copy the Vercel URL, e.g. `https://agentic-stock-intelligence.vercel.app`.

### 3. Allow the frontend on the API

1. Render → your API → **Environment**.
2. Set:

```
CORS_ORIGINS=https://YOUR-APP.vercel.app
```

No trailing slash. Redeploy the API (or wait for auto restart).

### 4. Test

Open the Vercel URL → type `Tata Motors` → Analyze.

If the UI loads but Analyze fails, check:
- `NEXT_PUBLIC_API_URL` matches Render exactly
- `CORS_ORIGINS` matches Vercel exactly
- Render logs for the failed request

## Data sources and offline fallback

Live data comes from Yahoo Finance (prices, fundamentals) and Google News RSS
(headlines). Yahoo rate limits shared datacenter IPs, so a cloud-hosted instance
will regularly get `YFRateLimitError`.

Each source degrades independently rather than failing the run. When a live fetch
is throttled, the platform falls back to a committed snapshot in
`sample_data/market_snapshots.json`. Any cached input is labelled in the report's
provenance caveat, and cached data caps confidence at medium so a conclusion is
never presented as more certain than its evidence.

Refresh the snapshot from a residential connection:

```bash
make snapshots
```

## Tests

```bash
make test
```
