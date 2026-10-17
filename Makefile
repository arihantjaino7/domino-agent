# Recipes are plain commands that work under cmd.exe (native Windows make), bash and zsh.
# Anything fancier lives in a Python script under scripts/.

.PHONY: help up down seed test dev api cli demo-headless eval spike agent-workspace

help:
	@echo Targets: up down seed test dev api cli demo-headless eval spike

up: ## start FalkorDB and wait until it answers PING
	docker compose up -d --wait

down:
	docker compose down

seed: ## M2: generate from WORLD_SEED, build world:pristine, GRAPH.COPY to world:live
	cd backend && uv run python -m domino.seed

test:
	cd backend && uv run pytest

dev: ## backend :8000 + frontend :5173
	uv run --project backend python scripts/dev.py

api: ## backend only
	cd backend && uv run uvicorn domino.api.main:app --reload --host 127.0.0.1 --port 8000

SCENARIO ?= monsoon
cli: ## M3: make cli SCENARIO=monsoon (or panel_fire)
	cd backend && uv run python -m domino.cli $(SCENARIO)

demo-headless: ## M6: make demo-headless SCENARIO=monsoon [DRY_RUN=1 for the free scripted check]
	cd backend && uv run python -m domino.agent.headless $(SCENARIO) $(if $(DRY_RUN),--dry-run,)

eval: ## M10: offline evaluation on isolated graphs; no paid API
	uv run --project backend python -m eval.run

agent-workspace: ## create ../domino-agent so Claude Code can be the agent over MCP (free)
	uv run --project backend python scripts/agent_workspace.py

spike: ## M1 capability spike -> docs/SPIKE.md
	uv run --project backend python scripts/spike.py

queries-md: ## regenerate docs/QUERIES.md from backend/domino/queries
	uv run --project backend python scripts/gen_queries_md.py
