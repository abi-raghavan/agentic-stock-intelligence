.PHONY: local local-api local-web up down logs test deploy snapshots

# --- No Docker (company laptop friendly) ---
local-setup:
	cp -n .env.local.example .env || true
	python3.12 -m venv .venv
	. .venv/bin/activate && pip install -r requirements.txt
	cd apps/web && npm install

local-api:
	. .venv/bin/activate && uvicorn apps.api.main:app --host 127.0.0.1 --port 8000 --reload

local-web:
	cd apps/web && npm run dev

local:
	@echo "Open two terminals:"
	@echo "  make local-api"
	@echo "  make local-web"
	@echo "Then visit http://localhost:3000"

test:
	python3.12 -m pytest tests/ -q

# Refresh the offline fallback snapshot. Run from a non-datacenter connection,
# since Yahoo Finance rate limits cloud IPs.
snapshots:
	. .venv/bin/activate && PYTHONPATH=. python scripts/refresh_snapshots.py

# --- Docker (optional) ---
up:
	docker compose up --build -d

down:
	docker compose down

logs:
	docker compose logs -f api web

pull-model:
	docker compose exec ollama ollama pull llama3.2:3b

deploy: up pull-model
