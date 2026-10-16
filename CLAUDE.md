# DOMINO: instructions for Claude Code

**Project:** DOMINO, an autonomous multi-tier supply-chain recovery agent built on FalkorDB.
**Event:** WeMakeDevs × FalkorDB Graph Hacks 2026, **Track 1: Agents That Act on Connected Data**.
**Deadline:** Oct 18, 23:59 IST. Internal target: submit by **21:00 IST**.

## Read first
- `docs/PLAN.md`. Sections **§0.1 (crunch plan)** and **§0.2 (review fixes + organizer guidance)** override older sections wherever they differ.
- Build only the current milestone from `START_HERE.md`. Don't start P1 features before the gate in §0.1 is passed.

## Stack
- Backend: Python 3.12 with `uv`, FastAPI, Pydantic v2, `sse-starlette`, the official `falkordb` client, the official MCP Python SDK (`FastMCP`), the `anthropic` SDK, and `ortools` (only if the CP-SAT stretch is reached).
- Frontend: React + Vite + TypeScript, `pnpm`, Tailwind, `@xyflow/react`, `elkjs`, Zustand.
- Infra: Docker Compose (FalkorDB + app), with Caddy for deployment.

## Hard rules
1. **All Cypher** lives in `backend/domino/queries/*.cypher`. It runs only through `run_query(name, params)`, which logs `{name, cypher, params, ms, rows}` for the UI's Cypher drawer and for `docs/QUERIES.md`.
2. Reads use `ro_query` (GRAPH.RO_QUERY). **Alias every relationship you count or sum.** FalkorDB only checks that an unreferenced edge exists.
3. **The LLM never writes Cypher.** Agent tools are a fixed, parameterised catalogue. Every ID argument is resolved against the graph before anything runs; unknown IDs return the outcome `unknown_entity`.
4. **Engines are pure and deterministic and never call the LLM.** MCP tools and API routes are thin wrappers. From async code, call the synchronous engines through `await asyncio.to_thread(...)`.
5. **Units:** integer simulation days (day 0 = incident day), integer units/week, integer cents. All randomness comes from `WORLD_SEED`.
6. **Tests:**
   - Every engine gets pytest tests on `tests/fixtures/tiny_world.py`, with expected values computed by hand.
   - Add adversarial fixtures: a shared cell line, complementary BOM inputs, and a partly exposed supplier.
   - The pristine world must have **0 projected-late orders**.
7. **Domain correctness:**
   - Exposure is not rejection. Reject a source only if its remaining clean capacity is 0.
   - Capacity and material balance are checked **jointly** across components and plants.
   - Assembly needs every required input (take the minimum over complementary inputs).
   - Bottlenecks come from the **min cut** (residual reachability on the full projected network), not from "saturated edges".
8. **Honesty in the UI:**
   - Never show a number that didn't come from an engine or API.
   - Use "protected (projected)" for orders covered by POs, and "fulfilled" only once parts have arrived.
   - "Not in the graph" does not mean safe.
9. **Execution safety:** run the preflight query, then one atomic write, then compare the receipt counts with the plan (V9). Approval is bound to `plan_hash` and `world_version`.
10. Secrets live only in `.env`, which must never be committed.
11. Commit after every milestone with a clear message. Keep `docs/DECISIONS.md` and `docs/AI_DISCLOSURE.md` up to date; the hackathon requires disclosing AI assistance.
12. After each milestone, explain what you built in plain language and **ask me 2–3 questions about the queries and the design**. I must be able to explain everything to the judges (rule 12).
13. Before building the Claude agent loop, **load the `claude-api` skill** and follow its current guidance (model id, adaptive thinking, `tool_choice: auto`, fallbacks, caching).
