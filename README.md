# Agentic Stock Intelligence

Multi-agent stock intelligence for **Indian (NSE/BSE) and US markets**. Live news and market data. Enter a company name or ticker — e.g. `Tata Motors`, `TATAMOTORS.NS`, `NVDA`. **Not financial advice.**

**Stack:** Next.js · FastAPI · LangGraph · BM25/hybrid RAG · SQLite

## Run locally (no Docker)

Requires Python 3.12 and Node 20.

```bash
git clone https://github.com/abi-raghavan/agentic-stock-intelligence.git
cd agentic-stock-intelligence
make local-setup
```

Terminal 1: `make local-api`  
Terminal 2: `make local-web`

Open http://localhost:3000

**Demo:** Tata Motors — *"Should I be worried about Tata Motors over the next 30 days?"*

## Docker (optional)

```bash
cp .env.example .env
make deploy
```

## Tests

```bash
make test
```
