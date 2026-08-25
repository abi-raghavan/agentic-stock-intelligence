.PHONY: up down logs test pull-model deploy

up:
	docker compose up --build -d
	@echo "Waiting for API..."
	@sleep 8
	@echo "Pulling Ollama model (first run)..."
	-docker compose exec ollama ollama pull llama3.2:3b
	@echo "Live stack ready:"
	@echo "  Web UI:  http://localhost:3000"
	@echo "  API:     http://localhost:8000/docs"

down:
	docker compose down

logs:
	docker compose logs -f api web

test:
	python3.12 -m pytest tests/ -q

pull-model:
	docker compose exec ollama ollama pull llama3.2:3b

deploy: up pull-model
