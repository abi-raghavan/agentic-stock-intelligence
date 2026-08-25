# Agentic Stock Intelligence

Multi-agent stock intelligence for Indian (NSE/BSE) and US markets. Live news and market data. **Not financial advice.**

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

## Host for free

| Service | Use for | Notes |
|---|---|---|
| [Render](https://render.com) | API + Web | Free tier, sleeps after inactivity |
| [Railway](https://railway.app) | API | $5 free credit/month |
| [Vercel](https://vercel.com) | Web frontend only | Free, connect to Render API |
| [Fly.io](https://fly.io) | API | Free allowance, needs card |

**Recommended:** Frontend on **Vercel**, API on **Render** (free tier).

Set `NEXT_PUBLIC_API_URL` on Vercel to your Render API URL.  
Set `CORS_ORIGINS` on the API to your Vercel URL.

## Tests

```bash
make test
```
