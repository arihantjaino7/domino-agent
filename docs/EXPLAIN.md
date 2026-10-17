# Explaining DOMINO to the judges

This is a study sheet for the author. It explains every part of DOMINO in plain words, with the real numbers
from the demo world and the file where each thing lives, followed by the questions judges are likely to ask.
Every number here was produced by the engines on the seed-42 world (the one the war room runs), on Oct 18,
with the Monsoon flood declared for 28 days unless it says otherwise.

---

## 1. The 30-second version

> A flood in Thailand stops a cell factory called VoltCell. We don't buy from VoltCell, so a tier-1 view says
> nothing is wrong. But two of our battery suppliers buy their cells from it. DOMINO walks the supply graph in
> FalkorDB, finds that hidden link, measures how much the network can really still make with max-flow, rejects
> a cheap backup that secretly depends on the same flooded factory, tests five recovery plans in copies of the
> graph, and asks a human to approve one. After approval it writes the purchase orders in one atomic transaction
> and checks nine rules against the graph. The AI agent picks the steps; it never writes database queries and
> never computes a number itself.

---

## 2. The demo world (seed 42)

- A fictional electronics maker, Kestrel Devices, with 3 plants: Bac Ninh (PL-BAC), Penang (PL-PEN), Guadalajara (PL-GDL).
- `world:pristine` has 341 nodes (340 generated plus one `Meta` node holding the world version) and 966 relationships.
- 117 open customer orders fall in the 6-week horizon (42 days).
- The battery chain (from `backend/domino/seed/motifs.py`, `MONSOON`):

| Site | Tier | Makes | Gets cells from |
|---|---|---|---|
| VoltCell Ayutthaya (S-VOLT-AYU) | 2 | cells, 10,500/wk | (flood zone: Chao Phraya Basin) |
| Hanriver Cheongju (S-HANR-CJU) | 2 | cells, 4,000/wk | — |
| PowerCell Hai Phong (S-PWRC-HPG) | 1 | BAT-4S packs → Bac Ninh | VoltCell (2,520/wk used) + Hanriver (1,080/wk used) |
| BatteryMax Penang (S-BMAX-PEN) | 1 | BAT-6S packs → Penang, Guadalajara | VoltCell only |
| AmpereOne Johor Bahru (S-AMPR-JHB) | 1 | BAT-4S, **backup** for Bac Ninh, cheapest ($31) | VoltCell only (the trap) |
| Kanto Kumamoto packs (S-KANT-KUM-P) | 1 | BAT-4S and BAT-6S, backup | Kanto's own cell line |
| ElectroHub Suwon (S-EHUB-SWN) | 1 | BAT-6S, backup for Penang | Hanriver |

A BAT-4S pack needs 4 cells (`MADE_FROM {qty: 4}`). This ratio is how cells per week become packs per week.

The data is synthetic. The motif is hand-designed so the story is interesting; every result shown in the UI is
computed by the engines from the graph at run time, never read from the motif file.

---

## 3. What happens in a Monsoon run, step by step

### Step 1. Detect: `resolve_entities`, `declare_incident`
- Full-text search on the `Place` index turns "Ayutthaya" and "Chao Phraya Basin" into graph ids
  (`R-AYU`, zone `Z-CPB`).
- `declare_incident` expands the zone to its regions and their sites: only VoltCell is in it. One atomic write
  marks the site `disrupted`, sets `capacity_factor = 0` and `disrupted_until = 28`, creates the `Incident` and
  `AFFECTS` edge, and bumps `world_version` in the `Meta` node from 0 to 1.
- The alert says "3–5 weeks". The scripted run uses 28 days. The real Claude Code run chose 35 days (the worst
  case), which is why its numbers differ a little (section 9).

### Step 2. Trace: `trace_exposure`, `explain_shared_dependencies`, `recall_history`
- **Tier-1 view:** affected sites that themselves supply a plant → **0**. A tier-1 system sees nothing.
- **Multi-tier view:** `MATCH chain = (d)-[:FEEDS*0..4]->(t1:Site)` from the affected site to every tier-1
  site within 4 hops, then to plants, products and open orders (`queries/exposure/exposure.cypher`).
  Result: **2 tier-1 suppliers exposed** (BatteryMax, PowerCell), **38 orders exposed**, in 3 plants.
- **Shared dependency:** VoltCell feeds 3 tier-1 sites: BatteryMax, PowerCell **and AmpereOne**, the backup.
- Every path becomes an evidence id (E1, E2, ...). The report must cite them.
- `recall_history` asks the memory graph about these sites (section 6).

### Step 3. Impact: `project_shortages`
A day-by-day simulation for 42 days (`engines/shortage.py`, exact fractions, no LLM):
- **How much a site can still make.** For one input from several sources, it is the share weighted by today's
  volume. PowerCell gets 2,520 cells/week from VoltCell and 1,080 from Hanriver, so it keeps 1,080/3,600 = **3/10**.
  For different inputs the product needs together, it is the **minimum** (plenty of cells can't replace a
  missing controller). BatteryMax is 100% VoltCell, so it keeps **0**.
- **Timing.** A site feels a cut in its inputs after its input buffer (PowerCell 5 days, BatteryMax 3 days).
  The plant feels it after the shipping time. Full supply returns after `disrupted_until` + transit.
- Each day, stock arrives and orders are served by need day (strategic customers first on the same day).
- **Exposed is not late.** Of 38 exposed orders, **25 are still on time** (stock and buffers cover them) and
  **13 are projected late**, 6 of them beyond the horizon. Penalties for the 13: **$536,370**.
- Guadalajara is exposed but has no late order: about 24 days of packs are already on the water.

### Step 4. Options: `compute_true_capacity`, `find_alternatives`
**True capacity with max-flow** (`engines/capacity.py`, FalkorDB `algo.maxFlow`):
1. Read the upstream network for one part and plant (supply edges and `FEEDS` up to 4 hops).
2. Build a temporary graph `scratch:flow:...` in **units of packs per week**:
   - **node splitting:** each site becomes `site:in → site:out` with its own capacity, so a cell factory that
     feeds several lines is counted once, not once per line;
   - cells are divided by the BOM ratio (4 cells per BAT-4S pack);
   - the edge into the plant is the contract plus the approved spare.
3. Run `algo.maxFlow` from the most upstream sites to the plant.
4. Find the **bottleneck (min cut)** from the residual network in Python, and check that the cut's capacity
   equals the max flow (it must; otherwise the engine raises an error).
5. Drop the scratch graph.

For BAT-4S at Bac Ninh:

| | packs/week |
|---|---|
| Tier-1 view (sum of contracts and spare: PowerCell 900 + AmpereOne 700 + Kanto 300) | **1,900** |
| True capacity now (max-flow) | **700** |

The 700 is PowerCell 400 (only Hanriver's 1,600 cells/week ÷ 4 can reach it) + Kanto 300 + AmpereOne **0**.
The min cut names exactly those three limits: the Hanriver → PowerCell line (400), Kanto's contract + spare (300)
and VoltCell's own capacity (0). For BAT-6S at Penang it is 980 → 650.

**Alternatives** (`engines/alternatives.py`):
- Candidates are approved backup sources (`CAN_SUPPLY`) for parts the product accepts, plus same-family
  look-alikes, so a wrong part can be rejected explicitly (the Panel Fire trap).
- Each candidate gets a **taint check**: is there a disrupted site 1–4 `FEEDS` hops upstream? That is a
  **warning**, not a rejection (CLAUDE.md rule 7).
- A source is **rejected only if its remaining clean capacity is 0**, from max-flow over its healthy inputs.
- **AmpereOne is rejected**: its only cells come from VoltCell, so its clean capacity is 0
  (`no_remaining_capacity`, evidence path VoltCell → AmpereOne). It is the cheapest option, which is why a
  tier-1 tool picks it.
- **PowerCell's extra volume is accepted with a warning**: it is exposed to VoltCell, but its Hanriver cells
  still give 200 packs/week of usable extra.

### Step 5. Simulate: `simulate_strategies`
Five strategies (`allocators/strategies.py`), all built by the same greedy code (`allocators/greedy.py`):

| | Strategy | How it chooses | Late orders | Spend | Verifier |
|---|---|---|---:|---:|---|
| S0 | Do nothing | — | 13 | $0 | — |
| S1 | Naive baseline (tier-1 view) | cheapest, nominal capacity, no taint check | 7 | $108,169 | **fails V3 and V8** |
| S2 | Lowest cost | cheapest, graph-aware | 3 | $114,982 | 9/9 |
| S3 | Max service | fastest, always air, graph-aware | 1 | $162,569 | 9/9 |
| S4 | **DOMINO balanced** | cost × reliability, air only when sea is too late, graph-aware | **1** | **$142,475** | 9/9 |

- The greedy loop: late orders by need day (strategic first). For each part the order is short of, try sources
  in the preset's order and take the largest quantity that still fits (binary search on quantity) the source's
  spare, its clean capacity and the upstream feeders' room. If any part of an order cannot be fully covered,
  everything given to that order is rolled back: an order is never "half protected".
- **Graph-aware** means: only sources with clean capacity, and upstream bookkeeping so two plans do not
  promise the same cells twice (`engines/upstream.py`).
- **Each plan is executed in its own copy of the graph** (`GRAPH.COPY` to `sandbox:<run>:<S>`), using the
  same executor as real execution. Then the projection runs again in that copy, the verifier checks it, and
  the copy is dropped. In the copy, new POs arrive at the rate the upstream can really support: if several
  POs need the same feeder, they share its room proportionally (**joint rationing**).
- S1 looks fine on paper (it "protects" 11 orders), but in its sandbox 5 of those are still late, because it
  bought from AmpereOne, which has no cells. The verifier catches it (V3: rate above clean capacity, V8:
  upstream material balance).
- S4 is recommended: the same 1 late order as S3 for $20,094 less. It is a preset, not a proven optimum.

### Step 6. Approve: `submit_plan_for_approval`, then a human
- The agent submits S4. A `Decision` node is created with the plan's `plan_hash` and the `world_version` it
  was simulated on. The run stops. **Nothing is bought yet.**
- The human sees the plan card in the war room and approves or rejects it.
- **Approve** is accepted only if the decision is still `proposed`, the `plan_hash` matches and the world has
  not changed since the simulation. If the world changed, the approval fails ("stale world") and the agent is
  told to simulate again.
- **Reject** records `rejected`, who rejected and their feedback on the `Decision`. The agent re-plans. The exact
  plan that was refused is refused again; a new plan for the same strategy gets a revision id (`...-v1-r2`).

### Step 7. Execute (the executor, never the AI)
`engines/executor.py` + `queries/execute/*`:
1. **Preflight read:** one row per planned PO: the backup edge exists, the part exists, the PO id is new, the
   PO has allocations, all allocated orders exist and the rate fits the free spare.
2. **One atomic write:** matches only if the decision is approved with this hash and the world version is
   unchanged; bumps the world version; creates 4 `PurchaseOrder`s with their links and `PROTECTS` edges;
   marks orders `protected_projected`; logs an `Action`. A unique constraint on `PurchaseOrder.id` rolls the
   whole query back on a duplicate, so running it twice creates nothing the second time.
3. **Receipt check (V9):** the counts written must equal the plan. In the scripted Monsoon run: 4 POs, 19 `PROTECTS`
   allocations, 12 orders; the world version goes from 1 to 2.

### Step 8. Verify, remember, report
- `verify_execution` runs **9 checks** against the graph (`engines/verifier.py`): V1 spare not exceeded,
  V2 every protected part is BOM-approved, V3 rates within clean capacity (max-flow), V4 arrivals by need day,
  V5 within budget, V6 one PO per decision/site/part/plant, V7 protected orders fully covered, V8 material
  balance at every upstream site across the whole plan, V9 receipt matches plan. All 9 pass. 1 order is still
  projected late.
- `record_lessons` writes dated lessons to the memory graph.
- `submit_incident_report` is **checked before it is accepted** (section 5).

**Wording.** 12 orders are **protected (projected)**: the POs exist in the graph, but no part has arrived.
DOMINO never says "fulfilled" or "delivered".

---

## 4. Why a graph, and which FalkorDB features

| Need | FalkorDB feature | Where |
|---|---|---|
| Follow dependencies of unknown depth, with the path as proof | variable-length paths `FEEDS*0..4` | `queries/exposure/exposure.cypher` |
| Real capacity through a network | `algo.maxFlow` | `queries/flow/maxflow.cypher` |
| Test 5 plans without touching the real world | `GRAPH.COPY` sandboxes | `engines/sandbox.py` |
| Reset the demo world in a second | `GRAPH.COPY` from `world:pristine` | `graph/lifecycle.py` |
| Reads that cannot write | `GRAPH.RO_QUERY` | `graph/run_query.py` |
| Turn "Ayutthaya" into an id | full-text index on `Place` | `queries/agent/resolve_places.cypher` |
| Never create a PO twice | unique constraint on `PurchaseOrder.id` | `graph/schema.py` |
| Memory that survives a reset | a separate `memory` graph | `agent/memory.py` |

Honest answer to "couldn't SQL do this?": SQL can do recursive queries too. The point is that here the graph is
the calculation: paths are the evidence, max-flow runs inside the database, and copies of the whole graph are
the sandboxes. The baseline and DOMINO use the same allocator code; the only difference is whether it sees the
deeper graph.

---

## 5. How the AI is kept honest

1. **The LLM never writes Cypher.** It can only call 16 fixed recovery tools (plus `health`) (`agent/tools.py`); every query is a
   checked-in file in `backend/domino/queries/` run through `run_query`.
2. **Every id is checked before anything runs.** Unknown ids return `unknown_entity` with "did you mean"
   suggestions.
3. **Engines compute every number.** They are plain Python and Cypher, deterministic, and never call the LLM.
4. **No purchase without a human.** `execute_plan` is not a tool. Only the approval path calls the executor.
5. **The report is checked:**
   - every evidence id must have been returned by a tool in this run;
   - for "depends on / exposed / rejected" claims, every named entity must be on a cited evidence path;
   - any site, supplier, order or plant id in the text must have appeared in a tool result (entity guard);
   - every `metric_ref` (like `R-04.totals.projected_late` or `R-10.strategies.S4.spend_usd`) must resolve;
   - **number guard:** every number in a claim's text must be a value found at its `metric_refs` (dollars for
     cent fields, and only the rounding the text shows: "$289K" matches 288,500–289,499). A claim that cites
     13 but says 999 is rejected.
   In the real Claude Code run, the first report was rejected by this check and the agent fixed it.
6. **Words have fixed meanings:** exposed ≠ projected late ≠ protected (projected) ≠ fulfilled.
   "Not in the graph" ≠ safe.

---

## 6. Memory

- A separate graph, `memory`, that is never reset with the world (scripted demo runs use `memory:dryrun`).
- `Incident` (own id `MI-0001`, ...; it also keeps the world id like `INC-0001`), `Entity` (a site, with its
  real name), `Lesson` (text, evidence ids, `learned_on` date), linked by `INVOLVED` and `ABOUT`.
- After tracing exposure, the agent calls `recall_history` with the sites on the paths. If an earlier lesson
  exists, it must say what it was and the **date it was learned**, and check it against this run instead of
  trusting it.
- Memory is shown to the agent and in the Memory tab. It does **not** change the allocator (a stated limitation).

---

## 7. The two ways an AI drives it

| Mode | Who chooses the tools | Cost |
|---|---|---|
| Claude Code over MCP | Claude Code itself, calling DOMINO's MCP server at `/mcp` | free with a Claude subscription |
| Claude API | DOMINO's own agent loop (`agent/loop.py`) calling the Anthropic API | paid; **built but never run against the real API** |
| Demo (scripted) | a fixed script that plays the model's part (`agent/scripted.py`) | free; tests the plumbing, not intelligence |
| Replay | nobody: a recording of a real run is played back | free; changes nothing |

The real-model evidence is the Claude Code run, published as the replay `monsoon-claude-code`.

---

## 8. Evaluation

`make eval` (`eval/run.py`), no LLM involved:
- 20 generated worlds (seeds 42–61) × 2 disruptions (Monsoon, Panel Fire) = 40 cases, 4,766 orders.
- Methods: B0 do nothing, B1 tier-1 view, B2 graph-aware greedy (same allocator and settings as B1, plus the
  graph checks), S4 DOMINO.
- Late orders: **B0 383, B1 130, B2 71, S4 57.** B1 chose a zero-clean-capacity source in 20 of 40 cases and
  failed 40 verifier checks; B2 and S4 0.
- The gain appears only when a backup shares an upstream site (Monsoon). In Panel Fire the backup is clean, so
  B1, B2 and S4 all reach 0 late.
- **Independent oracle** (`eval/oracle.py`): imports no DOMINO code, reads a raw export of the graph and
  recomputes exposure, projections and max-flow with NetworkX and exact fractions. 0 mismatches in 176
  method runs; all 20 undisturbed worlds have 0 late orders.

---

## 9. Why the real Claude Code run shows slightly different numbers

The alert says "recovery expected in 3–5 weeks". The agent decides the outage length.

| | Scripted run (28 days) | Real Claude Code run (35 days) |
|---|---:|---:|
| Exposed orders | 38 | 38 |
| Projected late if nobody acts | 13 | 14 |
| S1 / S2 / S3 / S4 late | 7 / 3 / 1 / 1 | 11 / 4 / 1 / 1 |
| S4 spend | $142,475 | $137,427 |
| True capacity BAT-4S at Bac Ninh | 700 of 1,900 | 700 of 1,900 |
| After approval | 4 POs, 12 protected (projected), 1 late, 9/9 | 4 POs, 12 protected (projected), 1 late, 9/9 |

Both are correct for their input. A longer outage makes more orders late. The agent prompts now ask the agent to
say which duration it chose and why.

---

## 10. Limitations to state before a judge finds them

- Synthetic data; no real ERP or supplier.
- Max-flow is solved per part and plant (single commodity); shared cells across parts are handled by the
  allocator's upstream bookkeeping and the verifier's V8, not by one multi-commodity flow.
- New POs are checked one feeder tier up, not every deeper tier.
- Greedy allocation; no optimality claim. It can overbuy (it buys the full need of a reduced part).
- The war room shares one live world; the REST approve/reject/reset endpoints are not authenticated.
- The report check verifies ids, evidence and numbers, not the meaning of every sentence.
- The Claude API mode has never been run against the real API.
- Routing, proactive risk scans and memory-driven reliability updates are planned, not built.

---

## 11. Questions judges may ask, with short answers

**What does the agent actually decide?** Which tools to call and in what order, which places the alert means,
how long the outage is, which strategy to submit and why, how to re-plan after a rejection, and what to put in
the report. It decides nothing numeric.

**Why not let the LLM write Cypher?** A wrong query could buy the wrong thing or report a wrong number with
confidence. Fixed tools make every number reproducible and every write go through the executor's checks.

**What if the LLM invents a number?** The report is rejected: the number guard checks every number in a claim
against the values at its metric refs.

**What stops it from buying without permission?** There is no tool that executes. Only a human's approval calls
the executor, and the approval must match the plan hash and the world version.

**What happens if two people act at once?** Approval is bound to the world version. If the world changed
(another incident, a reset), the approval fails and nothing is written. The atomic write also checks the
version, and a unique constraint stops duplicate POs.

**Why max-flow and not just add up suppliers?** Adding up tier-1 capacity says 1,900 packs/week. But PowerCell
and AmpereOne get cells from the same flooded factory. Max-flow with node splitting counts each factory once
and gives 700; the min cut names the limits.

**How do you know your max-flow is right?** The engine checks that the min cut's capacity equals the max flow
on every call, and the independent NetworkX oracle agrees on 85 of 85 capacity checks.

**Why is AmpereOne rejected but PowerCell's extra accepted, if both are exposed?** Exposure is a warning.
Rejection needs zero clean capacity. AmpereOne has no healthy input; PowerCell still has Hanriver's cells.

**What is "protected (projected)"?** POs are committed in the graph and the projection says they arrive in time.
No part has physically arrived, so we don't say fulfilled.

**Why S4 and not S3?** Same late count (1); S4 costs $142,475 vs $162,569 because it uses air only when sea is too
late. It is a preset that balances cost, reliability and speed, not a proof of optimality.

**What is a sandbox here?** A full copy of the live graph made with `GRAPH.COPY`. The plan is executed in it with
the real executor, the projection runs there, the verifier checks it, and the copy is deleted.

**What is joint rationing?** If several POs need cells from the same feeder and together ask for more than it
has room for, each gets the same proportional share. A PO's real rate is the minimum over its inputs.

**What does the verifier check that the allocator doesn't?** It re-reads everything from the graph after the
write: if the allocator had a bug, the verifier would still catch an overcommitted spare (V1), a wrong part (V2),
a rate above clean capacity (V3), a late arrival (V4), overspending (V5), duplicates (V6), half-covered orders
(V7), an overloaded upstream site (V8) or a write that does not match the plan (V9). The naive plan fails V3 and V8.

**Is the memory just a log?** It is a graph keyed by entity. The next run asks it about the sites on its evidence
paths and must report the lesson with its date and check it against the new results.

**What does "not in the graph" mean?** The Antwerp alert names a port we don't model. DOMINO says it is not in
the graph and that this is not the same as safe, declares nothing and stops.

**How did you evaluate it?** 40 disruption cases across 20 worlds, four methods on separate graph copies,
scored by the same projection, plus an oracle that shares no code with DOMINO.

**Why does B2 beat B1 if they use the same allocator?** The only difference is the graph checks: B2 cannot pick
a source with zero clean capacity and cannot promise the same upstream cells twice.

**Why do Panel Fire results tie?** The backup for the burned panel plant is clean, so every method picks it.
The graph only helps when a backup shares a hidden upstream site, and we say so.

**What would you build next?** A proactive single-point-of-failure scan (max-flow with each site knocked out),
port chokepoints with betweenness, rerouting with shortest paths, and multi-commodity flow for shared lines.

**How much of this did AI write?** Claude Code wrote most of the code from the author's plan; Codex wrote the
evaluation oracle, docs and the video edit. All of it is disclosed in `docs/AI_DISCLOSURE.md`, with decisions
in `docs/DECISIONS.md`. (Be ready to explain any file in this sheet in your own words.)

---

## 12. Where to look in the code

| Topic | File |
|---|---|
| Tool catalogue and report checks | `backend/domino/agent/tools.py` |
| MCP server | `backend/domino/mcp/server.py` |
| Agent loop (Claude API) | `backend/domino/agent/loop.py` |
| Claude Code runs | `backend/domino/agent/external.py` |
| Exposure | `backend/domino/engines/exposure.py`, `queries/exposure/` |
| Shortage projection | `backend/domino/engines/shortage.py` |
| Max-flow | `backend/domino/engines/capacity.py`, `queries/flow/maxflow.cypher` |
| Alternatives | `backend/domino/engines/alternatives.py` |
| Allocator and strategies | `backend/domino/allocators/` |
| Sandboxes | `backend/domino/engines/sandbox.py` |
| Approval and execution | `backend/domino/engines/executor.py`, `queries/decision/`, `queries/execute/` |
| Verifier | `backend/domino/engines/verifier.py`, `queries/verify/` |
| Memory | `backend/domino/agent/memory.py`, `queries/memory/` |
| Evaluation and oracle | `eval/` |
