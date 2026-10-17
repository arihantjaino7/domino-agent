# Cue sheet: which picture goes with which words

The voiceover decides the timing. Transcribe it (word timestamps), find each **anchor phrase** below, and start the visual on that exact word.
Numbers come only from `facts.json`. "Clip" names refer to the capture list in the prompt (`docs/CODEX_VIDEO_PROMPT.md`).

| # | Anchor phrase (first word starts it) | Visual | Source |
|---|---|---|---|
| 1 | "In 2011, floods in Thailand" | Black screen, huge kinetic words: **WHEN ONE LINK BREAKS**, then small: *Thailand floods, 2011*. Text only, no photo. | text |
| 2 | "This is DOMINO" | Clip A1 (healthy world, map). Title tag DOMINO + FalkorDB. | clip A1 |
| 2b | "one hundred seventeen customer orders" | Counter 0 → 117, label *orders due in the next 6 weeks*. | facts.world.orders_in_horizon |
| 3 | "An alert arrives" | The alert text types out (kinetic), then a tool-call list builds line by line (`resolve_entities`, `declare_incident`, `trace_exposure`, ...) from the Claude Code replay events. Tag: *Claude Code, real run*. If `video/inputs/claude-code-terminal.*` exists, use that footage instead. | replay events |
| 4 | "A tier-one view says" | Split card: **TIER-1 VIEW: 0 suppliers affected** (grey). | facts.tier1_view_affected_suppliers |
| 4b | "But DOMINO follows the graph" | Clip A2 (Overview, toggle Tier-1 view → DOMINO, path to VoltCell lights up). | clip A2 |
| 4c | "Thirty-eight orders" / "Thirteen will be late" | Counters 38 and 13 beside the map. Then *late fees if nobody acts $536,370*. | facts.multi_tier / if_nobody_acts |
| 5 | "the max-flow algorithm" | Clip A3 (capacity view) with a bar that shrinks. On "nineteen hundred" show 1,900/week, on "seven hundred" show 700/week. | clip A3, facts.capacity |
| 6 | "AmpereOne" | Clip A4 (alternatives). Red stamp **REJECTED** on AmpereOne Johor Bahru and the line *no remaining clean capacity*. | clip A4 |
| 6b | "five plans" | Five bars, late orders: 13, 7, 3, 1, 1 with the plan names and spend from `facts.plans_tested_seed42_monsoon`. Highlight the recommended one. | clip A5 + facts |
| 7 | "I approve" | Clip A6: the approval card, then the click on **Approve plan** (pause 1 s on the card before the click). | clip A6 |
| 7b | "four purchase orders" | Counter 4. Shipments view clip A7. | facts.after_approval |
| 7c | "nine checks out of nine" | Nine ticks appear one by one (kit sfx `tick`), then the chime. | facts.after_approval |
| 7d | "protected on paper" | Overview "Plan approved" headline with the label **protected (projected)**. Never write "fulfilled" or "delivered". | clip A8 |
| 8 | "exact Cypher query" | Clip A9: AI agent view, step opened, Cypher drawer showing a query. | clip A9 |
| 9 | "DOMINO also remembers" | Clip A10: *What DOMINO remembers*, with the date visible. | clip A10 |
| 10 | "forty made-up disruptions" | Four horizontal bars grow: 383, 130, 71, 57 (late orders out of 4,766). Labels: *Do nothing*, *Tier-1 view plan*, *Graph-aware plan*, *DOMINO plan*. Counters roll up with the kit sfx `counter`. | facts.evaluation |
| 10b | "no mismatch" | Small text: *0 of 176 mismatches against an independent checker*. | facts.evaluation |
| 11 | "DOMINO, built on FalkorDB" | End card: DOMINO · Track 1 · the GitHub URL from `facts.github_url`. Hold 3 seconds after the voice ends. | facts |

Rules for every scene
- Only the numbers listed above. If a number is not in `facts.json`, do not show it.
- Anything sped up gets a small **2×** label.
- Clips from Replay mode carry a small corner tag *Recorded run*. The Claude Code replay is a real model run; the scripted replay is not, so never tag the scripted one as Claude.
- Captions: burn in word-level captions from the transcript, inside the middle 80% of the width, away from the clip's own text.
