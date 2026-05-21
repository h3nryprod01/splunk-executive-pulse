# Makefile
# One-command operations for the entire stack.

.PHONY: help bootstrap up down restart logs seed data demo demo-all \
        clean test test-pipeline test-no-hallucination tail-pipeline \
        web dev

.DEFAULT_GOAL := help

help:  ## Show this help
	@awk 'BEGIN {FS = ":.*##"; printf "\n\033[1mUsage:\033[0m\n  make \033[36m<target>\033[0m\n\n\033[1mTargets:\033[0m\n"} /^[a-zA-Z_-]+:.*?##/ { printf "  \033[36m%-22s\033[0m %s\n", $$1, $$2 } /^##@/ { printf "\n\033[1m%s\033[0m\n", substr($$0, 5) } ' $(MAKEFILE_LIST)

##@ Setup

bootstrap: ## First-time setup: install local deps + .env
	@if [ ! -f .env ]; then cp .env.example .env; echo "✏️  Edit .env with your API keys"; fi
	pip install -r requirements.txt
	cd web && npm install

##@ Stack

up: ## Boot the full stack (detached)
	docker compose up -d
	@echo "⏳ Waiting for Splunk to be healthy (this can take 60s on first run)..."
	@until docker compose ps splunk | grep -q "healthy"; do sleep 5; done
	@echo "✅ Splunk healthy at http://localhost:8000 (admin / changeme123!)"
	@echo "✅ Postgres at localhost:5432 (pulse/pulse_dev)"
	@echo "✅ MCP server at http://localhost:9000"

down: ## Stop and remove containers (volumes preserved)
	docker compose down

restart: down up  ## Restart stack

logs: ## Tail logs from all services
	docker compose logs -f --tail=100

tail-pipeline: ## Tail pipeline worker logs only
	docker compose logs -f pipeline

##@ Data

data: ## Generate synthetic demo dataset (350K events, 5 stories)
	python splunk_data/generate_full_dataset.py

seed: ## Load synthetic events into Splunk + business context into Postgres
	@echo "📦 Loading business context..."
	python -m business_context.loader
	@echo "🎬 Pushing events to Splunk HEC..."
	python splunk_data/push_to_splunk_hec.py
	@echo "✅ Seed complete"

##@ Demo

demo: ## Run CEO briefing end-to-end (default persona)
	docker compose exec pipeline python -m orchestration.runner CEO

demo-all: ## Run briefings for ALL 5 personas in parallel
	docker compose exec pipeline python -c \
	  "import asyncio; from orchestration.runner import run_all_personas; \
	   asyncio.run(run_all_personas())"

web: ## Run the dashboard dev server (host machine)
	cd web && npm run dev

dev: up data seed demo web  ## End-to-end: up + data + seed + demo + web

##@ Testing

test: ## Run all unit tests
	pytest tests/ -v

test-pipeline: ## Run integration tests against the live stack
	pytest tests/integration/ -v -m integration

test-no-hallucination: ## Run anti-hallucination test suite
	pytest tests/integration/test_no_hallucination.py -v -s

##@ Cleanup

clean: ## Remove containers + volumes (DESTRUCTIVE)
	docker compose down -v
	rm -rf demo/sample_outputs/*.mp3 demo/sample_outputs/*.png

clean-outputs: ## Remove only generated outputs
	rm -rf demo/sample_outputs/*.mp3 demo/sample_outputs/*.png demo/sample_outputs/*.json
