#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

if [[ ! -f .env ]]; then
  cp .env.local.example .env
  echo "Created .env from .env.local.example"
fi

if [[ ! -d .venv ]]; then
  python3.12 -m venv .venv
fi
source .venv/bin/activate
pip install -q -r requirements.txt

mkdir -p data

if [[ "${1:-}" == "api" ]]; then
  echo "Starting API at http://127.0.0.1:8000"
  exec uvicorn apps.api.main:app --host 127.0.0.1 --port 8000 --reload
fi

if [[ "${1:-}" == "web" ]]; then
  cd apps/web
  if [[ ! -d node_modules ]]; then
    npm install
  fi
  echo "Starting Web UI at http://localhost:3000"
  exec npm run dev
fi

echo "Run in two terminals:"
echo "  ./scripts/run-local.sh api"
echo "  ./scripts/run-local.sh web"
echo ""
echo "Then open http://localhost:3000"
