# Overnight status and morning handover (Oct 16 → 17)

**State: Gate 1 passed. M2, M3 and (on your later go-ahead) M4 are done, committed and pushed. Stopped before M5.**

## Commits
- `04d9bf1` M2: world generator, loader and schema
- `0f86421` M3: exposure, tier-1 view and shortage projection
- `c604e91` M4: true capacity (max-flow, min cut) and alternatives

## What was checked (all on this machine, PowerShell + Git Bash)
- `make up`: FalkorDB healthy.
- `make seed`: about 1 s. Seed 42 gives 341 nodes and 966 edges. The loader receipt matches the generated world, there are no duplicate ids, and the constraint is OPERATIONAL.
- `make test`: **35 passed** (M1 health, 14 generator tests, 7 graph/loader tests, 14 M3 engine tests).
- `MATCH (s:Site {id:'S-VOLT-AYU'})-[f:FEEDS]->(t:Site) RETURN s, f, t` on `world:live` returns PowerCell (2,520 used), BatteryMax (4,800) and AmpereOne (0 used, cap 2,800).
- `make cli SCENARIO=monsoon` (exit 0):
  - Tier-1 view: **0** directly affected.
  - Multi-tier: **2 tier-1 sites (S-BMAX-PEN, S-PWRC-HPG) via S-VOLT-AYU**. Shared upstream: VoltCell feeds 3 (2 active + AmpereOne).
  - Guadalajara: 13 exposed, **0 late** (exposed but covered).
  - Penang: first stockout **day 11**, 10 late. Bac Ninh: first stockout **day 26**, 3 late, including the Meridian order SO-1000 (10 days late).
- `make cli SCENARIO=panel_fire` also works: tier-1 view 1 (Lumenvue), DSP-14 stockout day 17 at Bac Ninh.
- The pristine demo world projects **0 late and 0 exposed** orders (test).

## Deviations from the plan (all in docs/DECISIONS.md)
- Bac Ninh's first stockout is day 26, not the "~23" design target in §5.6. That is what the engine computes from the §5.6 numbers plus the generated order stream. Nothing was tuned to hit 23.
- Scarce Silicon (§5.7) is deferred. K7 is a plain filler part.
- EXPOSES edges are not written yet (planned for when the MCP tool needs them).

## Remaining issues / notes
- Under the plan's EDF-with-skip rule, a big strategic order can stay short while smaller orders behind it are served. For example, Penang's SO-1031 is still short at day 42 while SO-1043 is ready on day 30. That is the do-nothing projection behaving as specified. The allocator (M5) is what protects strategic orders.
- `world:cli:monsoon` and `world:cli:panel_fire` are left in FalkorDB so you can inspect them in the Browser. They are overwritten on each run.

## Commands to verify
```
make up
make seed
make test
make cli SCENARIO=monsoon
```
Then in FalkorDB Browser (http://localhost:3000), graph `world:live`:
`MATCH (s:Site {id:'S-VOLT-AYU'})-[f:FEEDS]->(t:Site) RETURN s, f, t` (screenshot for the README).

## Deferred learning questions (CLAUDE.md rule 12)
**M2**
1. Why does every seed loader query return `count(...) AS created`, and why does the loader compare it with the batch size? What would go wrong silently without it?
2. The schema is applied only to `world:pristine`. What makes that safe for `world:live` and future sandboxes, and which spike result proves it?
3. Why does the generator use a separate RNG stream per phase (`"42:orders"`, `"42:fill"`) instead of one `random.Random(42)`?

**M3**
1. In Q-EXPOSURE, why `[:FEEDS*0..4]` and not `*1..4`? Which scenario breaks with `*1..4`? (Hint: run Panel Fire.)
2. PowerCell gets 70% of its cells from VoltCell and 30% from Hanriver, so its availability is 30%. If PowerCell also needed a BMS controller from a healthy supplier, what would its availability be, and why is it the minimum and not an average?
3. Guadalajara and Penang both buy BAT-6S from BatteryMax, which is 100% VoltCell. Why is Guadalajara "exposed but covered" while Penang runs out on day 11? Name the two properties in the graph that make the difference.

## M4 (done after you said to keep going)
- `make test`: **44 passed** (9 new M4 tests: the docs example = 13, a network where every edge is saturated but only one is the min cut, the tiny world, Monsoon, Panel Fire, and scratch-graph cleanup).
- `make cli SCENARIO=monsoon` now also prints:
  - BAT-4S → Bac Ninh: naive **1,900/wk vs true 700/wk**. Bottleneck: Hanriver → PowerCell cell line (400) + Kanto spare (300) + VoltCell (0).
  - BAT-6S → Penang: naive 980 vs **true 650**. BAT-6S → Guadalajara: true 0 (no alternates in the graph).
  - **AmpereOne REJECTED**: no remaining clean capacity, path `S-VOLT-AYU -> S-AMPR-JHB`.
  - PowerCell extra ACCEPTED with an exposure warning, reduced to 400/wk clean of 900. Kanto accepted clean.
- `make cli SCENARIO=panel_fire`: Brightvale accepted, Novaglass REJECTED as incompatible (DSP-14-HB isn't approved for KB14).
- Deviation: the naive BAT-6S figure is 980 (per plant), not §5.6's "≈1,450". See DECISIONS.

### Node splitting and min cut, in one picture (BAT-4S → Bac Ninh after the flood)
```
             (site's own capacity, in packs/wk)
VoltCell:in --0--> VoltCell:out --700--> PowerCell:in --900--> PowerCell:out --900--> PLANT
                              \--700--> AmpereOne:in --700--> AmpereOne:out --700--/
Hanriver:in --1000-> Hanriver:out --400--> PowerCell:in            (1600 cells / 4)
KantoC:in  --600--> KantoC:out  --600--> KantoP:in --600--> KantoP:out --300--> PLANT
```
- Splitting every site into `in -> out` turns "VoltCell can only make so much" into an edge capacity. VoltCell's own edge is 0 after the flood, and both PowerCell and AmpereOne lose that input together.
- Max flow = 400 (Hanriver line) + 300 (Kanto spare) = **700**.
- Min cut: from the sources, follow edges that still have room. You reach VoltCell:in, Hanriver:in/out, KantoC and KantoP:in/out. The edges leaving that set are VoltCell's own edge (0), Hanriver→PowerCell (400) and KantoP→PLANT (300). Their sum, 700, equals the max flow, which proves this is the bottleneck.

### M4 learning questions
1. Why does each site become two nodes (`in`/`out`)? What would max-flow get wrong for VoltCell without that?
2. Why does the engine compute the min cut itself from residual reachability instead of taking "edges with flow = capacity"? (See `test_saturated_edges_are_not_all_bottlenecks`.)
3. AmpereOne and PowerCell are both downstream of VoltCell. Why is one rejected and the other accepted?

## Next step (when you're back)
- M5: greedy allocator (naive vs graph-aware), GRAPH.COPY sandboxes with joint rationing, executor, verifier. See START_HERE.md M5.
