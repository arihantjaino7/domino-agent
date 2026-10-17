# AI assistance disclosure

The hackathon rules require disclosing AI assistance. This file is kept up to date at every milestone.

- **Tool:** Claude Code (Anthropic), working from the plan in `docs/PLAN.md` and the rules in `CLAUDE.md`.
- **Planning:** `docs/PLAN.md` was written before the event started, as planning notes (allowed by rule 8). All code was written after Oct 15 00:01 IST.
- **M1 (scaffold + capability spike):** Claude Code generated the repo skeleton (backend, frontend placeholder, compose, Makefile) and `scripts/spike.py`. The author reviewed the spike results in `docs/SPIKE.md` and the decisions in `docs/DECISIONS.md`.
- **M2 (world generator, loader, schema):** Claude Code wrote `seed/` (catalog, motifs, generator), `graph/run_query.py`, `graph/schema.py`, `graph/lifecycle.py`, the `queries/` files and the tests. It followed the motif design tables in PLAN §5.6 and §5.8, which the author wrote before the event. The author reviews the motif numbers and the decisions in `docs/DECISIONS.md`.
- **M3 (exposure and shortage):** Claude Code wrote `engines/incident.py`, `engines/exposure.py`, `engines/shortage.py`, `cli.py`, the `queries/incident|exposure|shortage` files, and the tiny-world and adversarial fixtures with their hand-worked expected values. Nothing in M2/M3 calls an LLM at runtime.
- **M4 (true capacity and alternatives):** Claude Code wrote `engines/capacity.py`, `engines/alternatives.py`, the `queries/flow|alternatives` files, the CLI capacity/alternatives sections and the M4 tests with hand-worked values.
- **M5 (allocator, sandboxes, executor, verifier):** Claude Code wrote `allocators/`, `engines/upstream.py`, `engines/executor.py`, `engines/verifier.py`, `engines/sandbox.py`, the `queries/upstream|decision|execute|verify` files, the CLI sections 6–7 and the M5 tests, including negative tests where bad plans must be caught.
- **M6 (MCP tools, agent loop, approval, memory):** Claude Code wrote `agent/` (context, tools, loop, memory, scripted stand-in, headless CLI, system prompt), `mcp/server.py`, `api/runs.py`, the `queries/agent|memory` files and the M6 tests. It followed the claude-api skill for the model settings. DOMINO itself calls Claude at runtime as the agent; all numbers still come from the deterministic engines.
- **M7 (deployment):** Claude Code wrote the `Dockerfile`, `docker-compose.prod.yml`, `Caddyfile`, `docs/DEPLOY.md`, the start-up seeding step, the rate limits and the MCP key check, and tested the stack locally. Nothing was deployed to a server.
