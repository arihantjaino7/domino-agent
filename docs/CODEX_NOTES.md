# Codex handoff notes

## Summary

Completed the seven documentation and frontend cleanup tasks. The task commits are listed below; this handoff log is committed separately. Nothing was pushed. Claude Code and author review remains pending.

- `21b0801` — Generate docs/QUERIES.md from the query files
- `a429603` — Add the MIT license
- `754e37b` — Document the implemented graph data model
- `13adaf8` — Document the implemented architecture and approval flow
- `45c38d5` — Add the README skeleton with verified repo references
- `063a81b` — Remove unused frontend packages and separate the toast store
- `6facfd7` — Record the documentation and frontend cleanup work

## Every remaining TODO(numbers)

All 12 occurrences are in `README.md`, section **9. Evaluation results**. Replace them only with measured engine/evaluation output.

| File and line | Section / item | Placeholder |
|---|---|---|
| `README.md:142` | 9. Evaluation results / B0: do nothing / Projected-late orders | `TODO(numbers)` |
| `README.md:142` | 9. Evaluation results / B0: do nothing / Spend | `TODO(numbers)` |
| `README.md:142` | 9. Evaluation results / B0: do nothing / Runtime | `TODO(numbers)` |
| `README.md:143` | 9. Evaluation results / B1: tier-1 greedy / Projected-late orders | `TODO(numbers)` |
| `README.md:143` | 9. Evaluation results / B1: tier-1 greedy / Spend | `TODO(numbers)` |
| `README.md:143` | 9. Evaluation results / B1: tier-1 greedy / Runtime | `TODO(numbers)` |
| `README.md:144` | 9. Evaluation results / B2: graph-aware greedy / Projected-late orders | `TODO(numbers)` |
| `README.md:144` | 9. Evaluation results / B2: graph-aware greedy / Spend | `TODO(numbers)` |
| `README.md:144` | 9. Evaluation results / B2: graph-aware greedy / Runtime | `TODO(numbers)` |
| `README.md:146` | 9. Evaluation results / Test count | `TODO(numbers)` |
| `README.md:146` | 9. Evaluation results / Query latency table | `TODO(numbers)` |
| `README.md:146` | 9. Evaluation results / Evidence validity and verification results | `TODO(numbers)` |

Other submission placeholders are in README section 1: `TODO(gif)`, `TODO(video)` and `TODO(url)`. The evaluation table is explicitly unmeasured. No result numbers were invented.

## Checks completed

- Query generator: all 94 `.cypher` files appear exactly once; two successive runs produce identical bytes and no Git diff.
- The exact Makefile recipe, `uv run --project backend python scripts/gen_queries_md.py`, passes under Python 3.12.13 and leaves `docs/QUERIES.md` unchanged.
- Data-model diagram: every node label and relationship type is present in query or seed code. Seeded properties were inspected with the pure generator; runtime and memory fields were checked against the writers.
- Architecture stages and tool names were extracted from `frontend/src/lib/store.ts`; verifier names were extracted from `backend/domino/engines/verifier.py`.
- README: exactly 13 numbered sections; every relative link resolves. Scenario titles and alerts, MCP names and environment variable names were read from source. There are 16 recovery tools plus `health`.
- No `xyflow`, `elkjs` or `lucide` matches in `frontend/src` before dependency removal.
- `pnpm --dir frontend lint`: passed, no warnings.
- `pnpm --dir frontend build`: passed.
- Toast store code is identical to the code moved from `motion.tsx`; the only change in `store.ts` is its import.
- All changed paths are authorized. New and rewritten files have LF endings; the existing disclosure and decisions bytes are preserved with append-only additions. `git diff --check` passes.

## Observations and work left to the owners

- **Local tooling:** `make queries-md` could not be launched because `make` is absent from the Codex PowerShell PATH. The recipe itself passed directly. Suggested action: install or expose the existing Make tool before using README Make commands. No repo configuration was changed for this environment issue.
- **`backend/domino/agent/memory.py` and `queries/memory/recall.cypher`:** recall reads entity reliability, but no current memory writer sets it. Suggested action: let the backend owner decide whether to implement reliability feedback or continue treating it as planned. Documentation marks the current behavior.
- **Planned graph features:** `Hold`, `EXPOSES`, `CITES`, memory `Decision` and `Outcome` nodes are not written by the current code. Current writers also do not advance POs to received or orders to shipped. Suggested action: review `docs/DATA_MODEL.md`’s differences list rather than presenting the old plan as implemented; any feature work belongs to the backend owner.
- **`backend/domino/seed/generator.py`:** the loader supports `ALLOWS_ALTERNATE`, but the current generator has no rows. Suggested action: backend owner reviews whether any alternate-approval data should be seeded; no seed or query changes were made.
- **Generated query references:** the requested exact-string scan can report “not referenced in code” for queries invoked through dynamically constructed names, especially seed edge loaders in `graph/lifecycle.py`. It is not proof a query is unused.
- **Submission readiness:** the README still needs measured evaluation results, media and the public URL. Routing, proactive risk scanning, real arrival tracking and per-visitor worlds are not claimed as implemented. The author and Claude Code own evaluation, backend fixes, deployment and the final submission.
- **Disclosure review wording:** the required supplied line says Claude Code and the author reviewed the work. An additional appended status line explicitly says that review is pending, so the supplied text does not stand as an unqualified claim. Confirm review before submission.

No paid API was called. `.env` was not read or changed. No deployment, push or backend test suite run was performed for these documentation and frontend-only tasks.

## Evaluation follow-up (M10 partial)

The user explicitly reassigned evaluation to Codex while keeping deployment with Claude. This authorizes the evaluation files beyond the earlier docs-only ownership list. No deployment implementation, engine or frontend behavior was changed.

Implemented for review:

- `eval/oracle.py`: independent raw-JSON exposure, shortage ledger, NetworkX max-flow, PO rationing and evidence checks; no production-engine imports.
- `scripts/export_world_json.py` and read-only `queries/eval/`: reproducible JSON/gzip snapshots with hashes. Query catalogue regenerated (now 96 files).
- `eval/run.py`: fixed seeds 42–61, both incident motifs, B0/B1/B2/S4, four hand-worked fixtures, two free scripted MCP repeats per scenario, isolated graphs, strict coverage, failure artifacts, query samples and provenance. The complete database matrix is not yet integration-validated.
- `eval/report.py`: deterministic Markdown from raw metrics, paired comparisons, verifier/trap diagnostics, nearest-rank query p50/p95 and explicit unmeasured real-model claims.
- `eval/offline.py` and `read_only.py`: narrower validations that can be reported honestly while database scoring is blocked.
- `make eval` now runs the harness. NetworkX 3.7 is pinned in dev dependencies only.

Completed checks:

- **46 tests passed**: eval oracle/harness tests, seed tests, five pure shortage tests and four pure allocator tests. Command: `uv run --project backend pytest eval backend/tests/test_seed_world.py` plus the named pure tests in `test_m3_engines.py` / `test_m5_execution.py`; see test collection or the current chat for exact selectors.
- **60/60** fixed-seed database-free projection checks pass, recorded in `eval/OFFLINE_CHECKS.md` and `offline_results.json`. These do not test graph extraction or recovery execution.
- **4/4** existing graph snapshot conformance checks passed before the Docker restart, recorded in `eval/READ_ONLY_CHECKS.md` and `read_only_results.json`. All recorded queries were read-only and before/after exports matched. Their scoped query timings are published separately.
- All **12 backup files** (JSON/gzip and Redis DUMP for six graphs) were read back and their SHA-256 hashes/counts verified. `eval/out/db-backup/manifest.json` records indexes, constraints, TTLs and file paths. This ignored private folder was not committed. Restore has not been tested.

Blocker and recovery status:

- Actual sandbox evaluation hit GRAPH.COPY fork errors, then Redis MISCONF after snapshot failure. Docker logs, image reads and container exec returned I/O errors.
- After explicit user approval and verified graph backups, normal Docker restart timed out. Targeted Docker-process/docker-desktop-instance restart then failed on WSL data-disk `/dev/sde` with no-such-device errors. The failed startup was stopped to avoid further automatic provisioning attempts. Other WSL distributions were not terminated. No factory reset, unregister, prune, volume deletion or filesystem-repair command was issued.
- **Docker/FalkorDB is currently unavailable.** `eval/ENVIRONMENT.md` records the incident and backup inventory. The main `eval/RESULTS.md` is intentionally incomplete/failing. No recovery numbers were filled in the README.
- After safe storage recovery and graph-state verification, run `uv run --project backend pytest backend/tests eval -q`, then `uv run --project backend python -m eval.run`. Main evaluation needs all 176 method rows and six scripted runs; real-model A and CP-SAT D remain unmeasured.

Nothing was pushed. No paid model API was called. The complete backend suite could not run while the database was unavailable. Deployment remains with Claude. The final evaluation implementation/blocked-run commit is discoverable with `git log -1 --oneline` after this handoff is committed.
