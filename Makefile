# Recipes are plain commands that work under cmd.exe (native Windows make), bash and zsh.
# Anything fancier lives in a Python script under scripts/.

.PHONY: help up down seed test dev api cli demo-headless eval spike

help:
	@echo Targets: up down seed test dev api cli demo-headless eval spike

up: ## start FalkorDB and wait until it answers PING
	docker compose up -d --wait

down:
	docker compose down

seed: ## M2
	$(error make seed is not built yet - milestone M2)

test:
	cd backend && uv run pytest

dev: ## backend :8000 + frontend :5173
	uv run --project backend python scripts/dev.py

api: ## backend only
	cd backend && uv run uvicorn domino.api.main:app --reload --host 127.0.0.1 --port 8000

cli: ## M3: make cli SCENARIO=monsoon
	$(error make cli is not built yet - milestone M3)

demo-headless: ## M7: make demo-headless SCENARIO=monsoon
	$(error make demo-headless is not built yet - milestone M7)

eval: ## M10
	$(error make eval is not built yet - milestone M10)

spike: ## M1 capability spike -> docs/SPIKE.md
	uv run --project backend python scripts/spike.py
