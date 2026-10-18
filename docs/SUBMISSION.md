# Submission text

Ready to paste into the WeMakeDevs × FalkorDB Graph Hacks 2026 form. **Track 1: Agents That Act on Connected Data.**

Every number here comes from `make eval` ([eval/RESULTS.md](../eval/RESULTS.md), 0 failures) or the demo world (seed 42). If the code changes, rerun `make eval` and check these numbers again before you submit.

## One-liner

DOMINO is a FalkorDB agent that finds the hidden supplier a disaster really hit, tests recovery plans on graph copies, and acts only after a human approves.

## 50 words

A flood stops a supplier you never buy from directly. DOMINO traces that hidden dependency through FalkorDB, measures true capacity with max-flow, tests five recovery plans on graph copies and waits for human approval. Across 40 evaluated disruptions, graph-aware plans left 71 orders late versus 130 for a tier-1 view.

## 200 words

Most supply-chain tools only watch the suppliers you buy from directly. When a flood shuts a tier-2 cell factory, they report zero problems while two of your tier-1 suppliers are about to run dry, and the "backup" supplier turns out to depend on the same flooded factory.

DOMINO is an agent that acts on that connected data. An LLM (Claude Code over MCP, or the Claude API) chooses from 16 fixed, parameterised tools; it never writes Cypher. Deterministic engines do the work in FalkorDB: multi-hop `FEEDS` traversal for exposure, `algo.maxFlow` with node splitting for true capacity, `GRAPH.COPY` sandboxes to test five recovery strategies, and an atomic executor bound to the approved plan's hash and world version. A human approves before any purchase order is placed. Nine verifier checks run afterwards, and the final report is rejected if it cites an id, evidence path or number that no tool returned. Lessons go to a memory graph and come back, dated, in later runs.

In 40 generated disruptions, late orders fell from 383 (do nothing) to 130 (tier-1 view), 71 (graph-aware) and 57 (DOMINO balanced). An independent NetworkX oracle agrees on every exposed order, late order and capacity.

## Why Track 1

| Track 1 focus | How DOMINO does it | Where to look |
|---|---|---|
| Multi-hop reasoning over connected data | `FEEDS*0..4` paths from the disrupted site to tier-1 suppliers, plants, products and orders, plus the shared-upstream check that rejects AmpereOne as a backup. Tier-1 view: 0 affected suppliers. Multi-tier: 2. | `queries/exposure/`, `engines/exposure.py`, `engines/alternatives.py` |
| Graph queries and algorithms in the decision | `algo.maxFlow` with node splitting for clean capacity and the min cut; full-text search to resolve alert places; `GRAPH.COPY` for what-if sandboxes; `GRAPH.RO_QUERY` for every read. | `queries/flow/`, `engines/capacity.py`, `engines/sandbox.py`, `docs/QUERIES.md` |
| An agent that chooses tools | The model picks from a fixed MCP catalogue (16 recovery tools plus `health`). Claude Code can drive it over MCP at no API cost; the war room watches each call live, with the Cypher it ran. | `mcp/server.py`, `mcp/playbook.md`, `agent/tools.py`, [MCP_REMOTE.md](MCP_REMOTE.md) |
| Acting on the graph, safely | After human approval, one atomic write creates the decision, purchase orders, allocations and audit actions. Preflight first, receipt counts compared with the plan, approval tied to `plan_hash` and `world_version`, unique PO ids. | `engines/executor.py`, `queries/execute/` |
| Explainable, checkable results | Evidence paths (E1, E2, …), result references (R-04.totals.projected_late), nine verifier checks (V1–V9) and a report validator that rejects unknown ids and numbers. Memory returns earlier lessons with the date they were learned. | `engines/verifier.py`, `agent/tools.py`, `api/memory.py` |

## Measured results to quote

From `eval/RESULTS.md` (seeds 42–61, Monsoon and Panel Fire, 40 cases, 4,766 orders):

| Method | Late orders | Spend |
|---|---:|---:|
| B0: do nothing | 383 | $0 |
| B1: tier-1 view | 130 | $5,027,357 |
| B2: graph-aware | 71 | $4,904,084 |
| S4: DOMINO balanced | 57 | $5,112,242 |

- B1 chose a zero-clean-capacity source in 20 of 40 cases and failed 40 verifier checks; 88 of its "protected" orders are still late. B2 and S4: 0 of each.
- B2 beats B1 with the same allocator and budget in 19 cases, ties in 21 and is worse in 0.
- In the Panel Fire cases all three recovery methods reach 0 late orders, because the backup supplier is clean. The graph helps when the backup shares an upstream site.
- Demo world, Monsoon: 13 late orders with no action → 1 late after the approved S4 plan, for $142,475.
- Oracle agreement: exposure 998/998, projected-late 386/386, max-flow 85/85, evidence paths 85/85, 0 of 176 projection mismatches, 20/20 healthy worlds with 0 late.
- Tests: 106 backend and 24 evaluation tests passing.

## Do not claim

- That the plan is optimal. The allocator is greedy and S4 is a preset.
- That parts were delivered. Covered orders are **protected (projected)**.
- That the scripted demo shows a model's judgment. It is a free, scripted stand-in; real-model behaviour is shown with Claude Code over MCP.
- That a place not in the graph is safe.
- That memory changes future plans. It is recalled and shown with its date; it does not change the allocator.
- That the report check proves every sentence. It checks ids, evidence and numbers.

## Still to do before submitting

- [x] Push `main`. Still to do: make the repo public and open it in a logged-out window.
- [x] Hero GIF and the local Replay line in the README.
- [x] Live demo: https://domino-jiie.onrender.com/ (Render free; Replay, Demo with approval, all views, reset and the Cypher drawer checked on the live copy on Oct 18). Open it a minute before judging: it sleeps after 15 idle minutes.
- [x] Demo video: https://youtu.be/H7s2jJbKR4Y (unlisted, checked in a logged-out window; also in the README).
- [x] Video made from a real Claude Code run (`video/renders/domino-demo-v2.mp4`, 2:40, AI voice): tool calls, tier-1 vs multi-tier, the approval pause, verification and a dated memory recall.
- [x] Review wording in `docs/AI_DISCLOSURE.md` confirmed by the author (Oct 18).
- [ ] Blog post link (optional side prize).
