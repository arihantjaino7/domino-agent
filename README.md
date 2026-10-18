# DOMINO

**Track 1, Agents That Act on Connected Data**

## 1. Hero GIF and one-liner

![DOMINO war room during a real Claude Code run: the tier-1 view sees 0 affected suppliers, DOMINO finds 2 suppliers, 38 exposed orders and 13 projected late](docs/media/domino-hero.gif)

*A real Claude Code run, recorded live: the flood stops VoltCell, a tier-1 view sees nothing, and DOMINO follows the graph to 2 suppliers and 38 exposed orders.*

DOMINO follows supply-chain dependencies, tests recovery plans in FalkorDB copies and executes the plan a human approves.

Live demo: **[domino-jiie.onrender.com](https://domino-jiie.onrender.com/)** (free Render instance, kept awake by an UptimeRobot health check every 5 minutes; if it ever sleeps, the first visit takes about a minute). Choose **Replay** to watch a recorded real Claude Code run, with no API key and no change to the graph, or **Demo** for the free scripted run with the real tools, approval and verification. All visitors share one world; **Reset the world** puts it back. Demo video: [youtu.be/H7s2jJbKR4Y](https://youtu.be/H7s2jJbKR4Y) (2:40, AI voiceover, real Claude Code run). Write-up: [My ERP Said Everything Was Fine. A Flood Three Tiers Away Said Otherwise.](https://arihantt.hashnode.dev/my-erp-said-everything-was-fine-a-flood-three-tiers-away-said-otherwise)

## 2. The problem

A flood can stop a supplier you do not buy from directly. PowerCell and BatteryMax buy cells from VoltCell in Ayutthaya. Looking only at direct suppliers misses that shared dependency. An alternate supplier, AmpereOne, also depends on VoltCell, so a cheap backup may fail for the same reason.

This is a synthetic world for Kestrel Devices. The seed generator and checked-in queries let a reader inspect the assumptions.

## 3. What DOMINO does (6 phases)

1. Detect and trace: match an alert to known places, record the incident, follow upstream dependencies and recall dated lessons about the same sites from earlier runs.
2. Measure impact and options: project shortages, compute clean capacity and check alternate suppliers.
3. Simulate: fork the live graph and score recovery strategies with the same engines.
4. Approve: show the proposed plan and wait for a human decision.
5. Execute: check the approved plan and commit purchase orders and allocations atomically.
6. Verify and remember: check the result, store lessons and produce a report with evidence references.

**Risk X-ray** works before anything happens. It stops each site that feeds a supplier or sells to a plant (tier 1 included), alone, at 0% for 21 days, on an in-memory copy of today's projection inputs, and ranks the sites by the orders that would become late, then by late fees. Sites Kestrel has no direct contract with are flagged as hidden. The top three, plus the worst hidden site, are re-run on a `GRAPH.COPY` sandbox with `declare_incident`, the projection and `algo.maxFlow`, which also measures the capacity drop. The live graph is only read, and results are cached until the world changes. In the seed-42 world the worst hidden weak point is VoltCell's Ayutthaya cell fab, the site behind the Monsoon scenario. The war room's Risk X-ray view shows the ranking, lights up the map by damage and can rehearse any stop as a manual disruption. Agents call it as `scan_single_points_of_failure`; the API is `GET /api/xray`.

The UI groups tool calls into seven stages: Detect, Trace, Impact, Options, Simulate, Approve and Verify. The [architecture](docs/ARCHITECTURE.md) maps each stage to its tools.

## 4. Why a graph

Planned capabilities are marked so this table does not claim they already work.

| Capability | FalkorDB feature | What breaks without it | Current scope |
|---|---|---|---|
| Multi-tier exposure | Variable-length `FEEDS*0..4` paths | Dependency tracing and path evidence need another implementation. SQL can express recursive traversals too. | Implemented; traversal depth is bounded. |
| Hidden shared dependencies | Paths meeting at an upstream site | Backups sharing a failure point are missed. | Implemented. |
| Capacity and bottlenecks | `algo.maxFlow` on a projected network | Nominal tier-1 sums miss upstream limits and the min cut. | Implemented. |
| Single-point-of-failure scan | `FEEDS*0..4` evidence paths, `GRAPH.COPY` sandboxes and `algo.maxFlow` knockouts | No advance warning from hypothetical site failures. | Implemented (Risk X-ray): every upstream site is stopped alone and ranked by the late orders it causes; the worst are re-checked in sandboxes. |
| Port chokepoints | `algo.betweenness` | No graph-based port criticality ranking. | Planned; not a current tool. |
| Logistics rerouting | `algo.SPpaths` | No route search over the logistics network. | Planned; current engines use fixed transit days. |
| Alert-to-entity resolution | Full-text search on `Place` | Alerts cannot be resolved through the current tools. | Implemented. |
| What-if sandboxes | `GRAPH.COPY` | Strategies lose their isolated world copies. | Implemented. |
| Reset and per-visitor worlds | `GRAPH.COPY` and multiple graphs | A fresh live world needs another reset mechanism. | Reset implemented; current browser runs share the live world. |
| Memory across runs | Separate persistent memory graph | Remembered incidents and lessons disappear. | Implemented; scripted memory is separate. |
| Read-only queries | `GRAPH.RO_QUERY` | Reads lose the database-enforced read-only path. | Implemented. |
| Idempotent execution | Unique constraint on `PurchaseOrder.id` | Duplicate PO IDs lose their database guard. | Implemented with executor checks. |
| Provenance | Linked incidents, decisions, POs and actions | Graph links behind the execution audit disappear. | Implemented links; evidence is in run results, without planned `CITES` links. |

FalkorDB is part of the calculation and execution path. The graph-aware and tier-1 baseline allocators share code; the comparison tests the value of deeper supply-chain data, not a claim that a relational database cannot model it.

## 5. Data model

The world contains companies, physical sites, geography, parts, products, plants, customers and orders. Recovery adds incidents, decisions, purchase orders and audit actions. Memory lives in a separate graph. Days, weekly units and cents are integers.

```mermaid
graph LR
  SUP[Supplier] -->|OPERATES| S2[Site upstream]
  SUP -->|OPERATES| S1[Site tier 1]
  S2 -->|FEEDS| S1
  S2 -->|LOCATED_IN| R[Region]
  S1 -->|LOCATED_IN| R
  R -->|IN_ZONE| Z[HazardZone]
  S2 -->|MAKES| SUB[Component input]
  S1 -->|MAKES| C[Component output]
  C -->|MADE_FROM| SUB
  S1 -->|SUPPLIES| PL[Plant]
  ALT[Site alternate] -->|CAN_SUPPLY| PL
  P[Product] -->|REQUIRES| C
  PL -->|BUILDS| P
  PL -->|STOCKS| C
  CU[Customer] -->|PLACED| O[Order]
  O -->|FOR_PRODUCT| P
  O -->|FULFILLED_AT| PL
  S1 -->|SHIPS_VIA| PORT[Port origin]
  PORT -->|LANE| DEST[Port destination]
  DEST -->|DELIVERS_TO| PL
  INC[Incident] -->|AFFECTS| S2
  INC -->|RESOLVED_BY| D[Decision]
  D -->|CREATED| PO[PurchaseOrder]
  PO -->|FROM_SITE| ALT
  PO -->|FOR_COMPONENT| C
  PO -->|DELIVERS_TO| PL
  PO -->|PROTECTS| O
  D -->|LOGGED| ACT[Action]
  META[Meta: version and seed]
```

See [DATA_MODEL.md](docs/DATA_MODEL.md) for node properties, relationship tables, indexes and constraints. The [generated query reference](docs/QUERIES.md) contains the Cypher and its code references. Regenerate it with `make queries-md`.

## 6. Architecture diagram

```mermaid
flowchart LR
  B[Browser: React war room] -->|REST and SSE| API[FastAPI: /api]
  API --> A[Agent loop: Claude API or free scripted model]
  A -->|in-process MCP client| MCP[MCP server: /mcp]
  X[External MCP client: Claude Code] -->|streamable HTTP| MCP
  MCP --> T[Tool catalogue: backend/domino/agent/tools.py]
  T --> E[Deterministic engines and allocators]
  API -->|human approval invokes executor| E
  E --> Q[run_query]
  Q --> G["FalkorDB: world:pristine, world:live, sandbox:*, memory, memory:dryrun"]
  E -->|GRAPH.COPY and deletion via lifecycle helpers| G
```

The model chooses tools. Deterministic Python engines calculate results. A human approves the plan before the executor commits it. See [ARCHITECTURE.md](docs/ARCHITECTURE.md) for the files and run flow.

## 7. Agent and MCP tools

The server is mounted at `/mcp`. It exposes these names from `backend/domino/mcp/server.py`:

`health`, `resolve_entities`, `declare_incident`, `get_entity_context`, `recall_history`, `trace_exposure`, `explain_shared_dependencies`, `project_shortages`, `scan_single_points_of_failure`, `compute_true_capacity`, `find_alternatives`, `simulate_strategies`, `flag_orders_at_risk`, `submit_plan_for_approval`, `get_decision_status`, `verify_execution`, `record_lessons`, `submit_incident_report`.

`health` checks connectivity. The recovery tools validate IDs and return engine results. `execute_plan` is not exposed as an MCP tool. External clients propose a plan, wait for the human in the war room, then read its status.

| Mode | How it runs | Cost and requirements |
|---|---|---|
| Demo | Choose a scenario and press **Run the demo**. `agent/scripted.py` supplies model responses. | Free, scripted and offline after setup; still needs the local backend and FalkorDB. |
| Replay | Choose **Replay**, pick a recording and press **Play the recording**. The war room plays back a recorded run: its events and the world as it was at each step. Your Approve only continues the recording. | Free, needs no API key or Claude subscription, and changes nothing in the graph. Recordings live in `demo/replays/`. |
| Claude Code over MCP | Locally: run `make agent-workspace`, then use the generated workspace with Claude Code and watch the war room. Against the live site, from any computer: one `claude mcp add` command, then `/mcp__domino__monsoon` ([MCP_REMOTE.md](docs/MCP_REMOTE.md)). | Free with a Claude subscription; no Anthropic API key needed for this mode. |
| Claude API | Use the API mode with `ANTHROPIC_API_KEY` configured. | Paid and rate-limited by the application. **Implemented but not run against the real API:** the author has no API budget, so this path is tested only with the scripted stand-in model. The real-model evidence in this repo is the Claude Code run. |

## 8. Safety and verification

- The LLM never writes Cypher. Tools call fixed, parameterised queries through deterministic engines.
- Approval is bound to `plan_hash` and `world_version`. A changed world requires simulation again, and the agent is told the approval could not run.
- A rejection is recorded on the decision in the graph, with the human's feedback. The agent cannot resubmit the plan that was refused; a re-planned plan for the same strategy gets a revision id.
- Execution runs preflight, writes atomically and compares its receipt with the plan. A unique PO-ID constraint guards against duplicates.
- The final report is checked: every entity id, evidence id, result reference and stated number must come from this run's tool results, or the report is rejected.
- Verification checks approved spare, BOM compatibility, clean capacity, arrival deadlines, budget, PO uniqueness, complete order coverage, joint material balance and receipt counts.
- Orders covered by POs are **protected (projected)**. Parts have not yet arrived.
- **Not in the graph** does not mean **safe**.

See the verifier names and approval path in [ARCHITECTURE.md](docs/ARCHITECTURE.md).

## 9. Evaluation results

All numbers below come from one run of `make eval` (0 failures) and from the test suites; the full generated report, with every query timing and the raw rows, is [eval/RESULTS.md](eval/RESULTS.md) and [eval/results.json](eval/results.json).

**Setup.** 20 generated worlds (seeds 42–61), each hit by two disruptions (the Monsoon flood and the Panel Fire): 40 cases and 4,766 orders in total. Every method runs on its own copy of the graph and is scored by the same projection. No LLM is called.

| Method | Projected-late orders (of 4,766) | Spend | Runtime per case, p50 |
|---|---:|---:|---:|
| B0: do nothing | 383 | $0 | 77 ms (projection only) |
| B1: tier-1 view (same greedy allocator, nominal tier-1 capacity) | 130 | $5,027,357 | 236 ms |
| B2: graph-aware greedy (clean capacity and shared-upstream checks) | 71 | $4,904,084 | 240 ms |
| S4: DOMINO balanced (graph-aware, reliability-weighted, air when needed) | 57 | $5,112,242 | 245 ms |

What the numbers say:
- **The tier-1 view's plans break.** B1 picked a source with zero clean capacity in 20 of 40 cases, failed 40 verifier checks, and 88 of the orders it marked "protected" are still late. B2 and S4: 0 traps, 0 failed checks.
- **B2 beats B1 using the same allocator and the same budget:** fewer late orders in 19 of 40 cases, a tie in 21, worse in 0 (59 fewer late orders in total).
- **The gain only appears when an alternative shares an upstream site.** In the Monsoon cases late orders go 248 → 130 (B1) → 71 (B2) → 57 (S4). In the Panel Fire cases the backup supplier is clean, so B1, B2 and S4 all choose it and all reach 0 late orders (B0: 135).
- **Demo world (seed 42), Monsoon:** 13 late orders with no action; S4 leaves 1 late for $142,475 (116 of 117 on time); B1 leaves 7 late and fails verifier checks V3 and V8.
- S4's extra gain over B2 is not only graph visibility: it also ranks by reliability and allows air freight.

**Independent oracle.** `eval/oracle.py` imports no DOMINO code. It reads a raw export of the graph and recomputes everything with NetworkX and exact fractions. It agrees on exposed orders (998/998, no false positives or negatives), projected-late orders (386/386), max-flow capacities (85/85 component/plant checks) and evidence paths (85/85 structurally valid). Projection mismatches: 0 of 176 method runs. All 20 undisturbed worlds have 0 projected-late orders.

**Scripted agent runs (free, plumbing only).** Monsoon, Panel Fire and the Antwerp non-event, 2 runs each: 6/6 pass. Disruptions paused for approval, placed no PO before approval and passed verification afterwards; the non-event answered `not_in_graph` and left the world unchanged. This proves the tool path, not the intelligence of a real model; real-model runs are not part of this evaluation.

**Tests:** 106 backend tests (`make test`) and 24 evaluation tests (`uv run --project backend pytest eval`), all passing.

**Query latency** (local FalkorDB, `run_query` log, during evaluation; p50 / p95 in ms): multi-tier exposure `exposure/exposure` 18.97 / 22.95; tier-1 view `exposure/tier1_view` 3.95 / 5.29; max-flow `flow/maxflow` 5.80 / 12.45 (2,294 calls); order projection `shortage/orders` 32.71 / 46.26; execution preflight 5.21 / 6.60 and atomic write 6.26 / 7.62. These are local measurements, not deployment latency. The full table is in [RESULTS.md](eval/RESULTS.md#named-query-performance).

The allocator is greedy and makes no optimality claim. Recovery is **protected (projected)**: purchase orders are committed in the graph, no parts have physically arrived.

## 10. Setup

Install Python 3.12, `uv`, `pnpm`, Node.js, Docker Compose and `make`. Python requirements are in `backend/pyproject.toml`; frontend commands and dependencies are in `frontend/package.json`.

From the repo root, using PowerShell:

```powershell
Copy-Item .env.example .env
uv sync --project backend
pnpm --dir frontend install --frozen-lockfile
make up
make seed
make dev
```

Set local configuration in `.env`. Keep secrets out of commits. Open the frontend at `http://localhost:5173`; the backend runs at `http://localhost:8000`. These addresses are defined in the existing development commands.

Environment variable names from `.env.example`:

`ANTHROPIC_API_KEY`, `DOMINO_MODEL`, `DOMINO_EFFORT`, `DOMINO_MAX_TOOL_CALLS`, `FALKORDB_HOST`, `FALKORDB_PORT`, `FALKORDB_IMAGE`, `WORLD_SEED`, `WORLD_GRAPH_PRISTINE`, `WORLD_GRAPH_LIVE`, `MEMORY_GRAPH`, `MCP_API_KEY`, `LIVE_RUNS_PER_HOUR_PER_IP`, `LIVE_RUNS_PER_DAY`, `DOMINO_DOMAIN`, `DOMINO_PUBLIC_HOST`.

### Run a scenario

The UI offers the following synthetic alerts from `backend/domino/agent/scenarios.py` and its seed motifs:

| Scenario | Title | Synthetic alert |
|---|---|---|
| `monsoon` | Monsoon flooding in the Chao Phraya Basin | Severe monsoon flooding across Ayutthaya and the Chao Phraya Basin; industrial estates closed, recovery expected in 3-5 weeks. |
| `panel_fire` | Fire at Lumenvue Display, Suzhou | Fire at Lumenvue Display's Suzhou module plant; production halted for about two weeks. |
| `non_event` | Port strike in Antwerp | Dock workers' strike closes the Port of Antwerp for about a week. |

The Antwerp case tests whether the agent reports an unknown location honestly.

For a free headless scripted run:

```powershell
make demo-headless SCENARIO=monsoon DRY_RUN=1
```

Run `make test` for backend tests and `make eval` for the evaluation. Run `pnpm --dir frontend lint` and `pnpm --dir frontend build` for frontend checks. To use Claude Code as the agent locally, keep the app running and run `make agent-workspace`; against a hosted copy, see [MCP_REMOTE.md](docs/MCP_REMOTE.md).

### Deploy (one container, free on Render)

`deploy/single/Dockerfile` builds one image with FalkorDB (pinned image, listening only inside the container), the API and the built war room; `deploy/single/start.sh` starts FalkorDB, builds the world if it is missing and serves on `$PORT`. `render.yaml` describes it as a free Render web service (512 MB, 0.1 CPU; a full run peaks at about 160 MB).

1. Sign in at render.com with GitHub and give Render access to this repo.
2. **New** → **Blueprint** → pick the repo → **Apply**. (Or **New** → **Web Service**: language Docker, instance Free, Dockerfile path `./deploy/single/Dockerfile`, health check `/api/health`.)
3. The first build takes about 10 minutes. New commits to `main` deploy automatically.
4. Environment: `MCP_API_KEY` is generated (Claude Code needs it to connect); `MCP_OPEN=true` drops the key; `ANTHROPIC_API_KEY` turns on Claude API mode.
5. Keep it awake: a free instance sleeps after 15 idle minutes and then builds the world again on the next visit (memory starts empty). An [UptimeRobot](https://uptimerobot.com) HTTP monitor on `https://<your-service>.onrender.com/api/health` every 5 minutes keeps it running; one always-on service fits in Render's 750 free hours a month.

The same image runs anywhere: `docker build -f deploy/single/Dockerfile -t domino .` then `docker run --rm -p 7860:7860 domino` and open http://localhost:7860. For a VPS with automatic HTTPS, `docker-compose.prod.yml` runs FalkorDB, the app and Caddy.

## 11. Limitations and assumptions

- All data and alerts are synthetic. There is no real ERP or supplier integration.
- Max-flow is a single-commodity bound for each component/plant pair. The allocator and verifier account for shared upstream inputs across the plan.
- Greedy allocation is deterministic but not guaranteed optimal. Weekly rates and integer simulation days simplify operations.
- The sandbox uses a deterministic reality model, not a forecast of a real supplier’s behaviour.
- Dependency traversal is bounded. Unknown or unmodelled entities do not establish safety.
- The browser currently shares a live world. Resets and changes can invalidate another plan.
- Routing, proactive risk scans, live arrival tracking and memory-driven supplier reliability updates are not implemented. Memory is recalled and shown to the agent; it does not change the allocator.
- New purchase orders are checked against the capacity of the immediate upstream feeders only, not every deeper tier.
- The allocator buys the full quantity of a reduced component, not only the net shortage, so a plan can overbuy (visible in the Panel Fire spend).
- The report check verifies ids, evidence and numbers, not the meaning of every sentence.
- The REST approve, reject, reset and inject endpoints are not authenticated; in a public demo anyone with the URL can use them on the shared synthetic world.
- Purchase orders are records in a synthetic graph. No real supplier is contacted.

## 12. AI disclosure

Read the [AI assistance disclosure](docs/AI_DISCLOSURE.md) for what the author did and what Claude Code and Codex assisted with.

## 13. Credits

Built by Arihant Jain for WeMakeDevs × FalkorDB Graph Hacks 2026. **Track 1, Agents That Act on Connected Data**.

FalkorDB provides graph storage and algorithms. The app uses Python, FastAPI, the MCP SDK, React, Zustand and Vite. Claude Code and Codex assisted with implementation, documentation and cleanup as recorded in the [disclosure](docs/AI_DISCLOSURE.md).

Licensed under the [MIT License](LICENSE).
