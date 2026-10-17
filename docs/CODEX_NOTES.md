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

## Eval review notes for Claude

Added 2026-10-17; review basis: harness `aca3e3a` and current source. **Supersedes the outage/resume advice above:** Arihant reports the cause was a full C: drive, freeing space restored Docker, and all six graphs match the backup counts. He reports `make test`: 81 passed; `pytest eval`: 24 passed. I did not rerun these. Claude now owns evaluation/results/README numbers. No Docker/WSL restart, repair/prune or second evaluator should be started.

### Oracle assumptions and method definitions

Agreement checks implementation consistency, not the truth of shared supply-chain assumptions.

- **Schema:** global unique IDs, valid endpoints, a FEEDS DAG, one customer/product/plant per order, one stock balance per plant/component, positive integer BOM quantities. Duplicate functional links can collapse in dictionaries. Cycles anywhere in the export are rejected. Missing factors default to 1; explicit nulls/malformed properties are not generally normalized as production queries sometimes do.
- **Units/time:** integer days, units/week and cents; day 0 is the incident day. Horizon 42 includes 43 arrival ticks (0-42). Arrivals precede demand, including day 0. Normal supply uses exact fractional weekly rates / 7, with cumulative floors pooled by plant/component.
- **Incident/exposure:** Site/Region/HazardZone expansion uses IN_ZONE/LOCATED_IN. Each case overwrites affected factors/durations for one day-0 incident. Exposure follows any FEEDS edges for 0-4 hops, then matching SUPPLIES/BUILDS/REQUIRES links to open orders due within the horizon. Structural exposure is not actual shortage.
- **Availability/pipeline:** same-input suppliers use used_wk weights, or cap_wk if total use is zero; complementary input groups use their minimum share, times own factor. Earliest upstream onset plus destination buffer determines onset; own disruption starts at 0. Latest contributing restoration wins (unknown means indefinite), without a restoration buffer. One reduced-rate interval represents the site; SUPPLIES transit shifts it. Full-rate pipeline is assumed before that interval.
- **Demand/late counts:** open/protected_projected orders due by horizon use qty x immediate product REQUIRES quantities; no MADE_FROM expansion or alternate-part substitution in consumption. Queue: need_day, strategic first, ID. No early/partial completion or assembly lead time; all inputs must coexist, and an unavailable order can be skipped. Each late order counts once. Ready after due day is late; unresolved orders use horizon + 1 for censored late days. Customer penalty is cents/day per order, not per quantity.
- **PO delivery:** committed/in_transit only; cumulative floored arrivals start inclusively at first_arrival_day and stop at qty. PROTECTS units are earmarked by need_day/ID before leftovers enter shared stock; earmarks remain reserved. These are projected arrivals, not received/shipped status.
- **PO rationing:** immediate feeders/direct MADE_FROM only. Existing nominal used_wk has priority over new room = max(0, floor(capacity x factor) - used out). Per-PO attribution sorts nonzero-factor feeders first, then headroom and ID; leftover demand lands on the first feeder. All POs/components/plants share each feeder proportionally, flooring grants separately and taking the minimum across required inputs after BOM division. Source factor is only on/off here, not another proportional cap. Rates stay fixed despite recovery dates; no deeper-tier propagation.
- **Flow:** independent NetworkX node splitting, four-hop FEEDS/BOM bounds, floor-converted capacities, parallel-edge sums, current factors and SUPPLIES/CAN_SUPPLY potential (used + spare). No inventory/transit/restoration timing. Each component/plant and standalone site is solved separately; values are not jointly additive. Complementary inputs pool together: this is an upper bound. BOM paths must give equal ratios or the oracle raises; production keeps the first. Each upstream site assumes a consistent output unit.
- **Evidence/metrics:** checks path structure/hops, entities, listed order identities and summed value; order-set precision/recall does not certify all possible paths or narrative numbers. Projection comparisons cover ready days, total penalties and PO rates, not every UI field. Spend/revenue/net-benefit summaries use production score(), not a second financial oracle.

All recovery methods share build_problem's graph-derived late-order list, full quantities for reduced components, candidate catalogue, order priority and 25,000,000-cent budget. This is an allocation comparison, not tier-1-only detection. Full-component replacement rather than net shortage can overbuy; MOQ padding adds buffer.

| Runner label | Exact meaning |
|---|---|
| B0 / S0 | Do nothing: post-incident baseline projection, no recovery POs. |
| B1 / S1 | Same greedy allocator; cheapest unit price then site ID, sea only, nominal approved spare minus reservations. Includes candidates rejected solely for zero clean capacity; no clean-capacity filter/shared-feeder overload check. |
| B2 / S2 | Same price/sea/inputs/budget as B1; excludes naive-only candidates, caps by usable clean capacity and checks joint immediate-feeder overloads. |
| S4 | Graph-aware plus rounded cost x (2 - reliability) x taint multiplier (1.1 if tainted), then arrival/ID. Reliability is static supplier data, defaults to 0.9 when falsy. Sea if timely, otherwise air if timely. Its gains include changed ranking/shipping. |

Greedy is not proven optimal; S4 is a preset. B1 verifier/trap violations remain baseline outcomes; oracle mismatches and B2/S4 safety failures fail evaluation. B0 timing is projection only; other method timers include allocation, proposal/approval, execution, projection and verification, excluding common problem construction, copies/exports/oracle work. Setup is separate. Query percentiles cover successful logged calls, not request/deployment latency.

### Execution coverage

- Earlier completed checks: 60 database-free seed projections and four read-only existing-world checks (including existing PO rates/evidence where present). The former bypasses Cypher/allocation/execution; the latter does not run database max-flow or new recovery plans.
- An initial database smoke was interrupted by fork/persistence/storage failures. Final committed blocked results have zero method rows/scripted runs; earlier eval/out/smoke partial artifacts are not passing benchmark totals.
- I never completed the 176-row database matrix (20 seeds x 2 incidents x 4 methods + 4 adversarial worlds x 4 methods), full healthy-world checks, or all post-execution oracle/flow/safety/cleanup comparisons. The four adversarial worlds were hand-checked/unit-tested, not completed as database recovery trials by this runner.
- The six P-scripted MCP repeats were not completed. Real-model A was not evaluated; no paid API was called. D/CP-SAT is absent. Memory learning, second-disruption replanning and deployment/UI behavior are outside these measurements.
- Backup checksums/counts were verified; restore was never tested. Arihant's recovery/test results above are newer evidence, not a benchmark rerun by me.

### Uncertainties for the review

- Exact fractions versus production float/floor boundaries can disagree in capacity/rationing; inspect boundary failures without assuming either side is correct.
- Nullable/duplicate links, ambiguous BOM paths, mixed-output sites, alternate consumption and deeper shared inputs need review before broader claims. The implementation is separate, but seed families, fixture builders and model assumptions are shared.
- Full database integration, exception cleanup and peak disk/fork requirements remain unvalidated across the matrix. Unique graph names prevent ordinary name collisions, not resource contention; keep one evaluation owner/runner.
- The old outage status and incomplete totals are historical. Claude should update owned environment/results files and README from his reviewed run; I left those untouched.
