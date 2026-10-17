# Demo video: step-by-step guide

Target: **3:00 or less**. Language of the video: English (judges). Every number below comes from the seed-42 world (the one the war room runs) and was checked against the recorded run on Oct 17. PLAN §16 has older planning numbers (45 exposed, 27 late, 600 nodes): **do not use those.**

Numbers to say:

| What | Number |
|---|---|
| Graph size | 341 nodes (world:pristine), 117 open orders in the 6-week horizon |
| Tier-1 view after the flood | 0 suppliers affected |
| DOMINO multi-tier view | 2 tier-1 suppliers exposed (via VoltCell Ayutthaya), 38 orders exposed |
| Projected late if nobody acts | 13 orders |
| True capacity, battery packs (BAT-4S) at Bac Ninh | tier-1 view 1,900/week → true 700/week |
| Cheapest backup | AmpereOne Johor Bahru, rejected: no remaining clean capacity (its cells come from the flooded VoltCell) |
| Plans tested in sandboxes | 5: do nothing 13 late; naive 7 late; lowest cost 3 late; max service 1 late for $162,569; DOMINO balanced 1 late for $142,475 |
| After approval | 4 purchase orders, 12 orders protected (projected), 1 still late, 9 of 9 checks pass |
| Evaluation (20 worlds, 40 disruptions) | late orders: do nothing 383, tier-1 view 130, graph-aware 71, DOMINO 57 |

---

## Part A: Prepare (15 minutes)

1. Free disk space: keep at least 10 GB free on C: (video files are big).
2. Start everything: `make up`, then `make dev`. Open `http://localhost:5173`.
3. Browser: full screen (`F11`), zoom 110–125% so text is readable. Dark theme.
4. Terminal for Claude Code: font size large (`Ctrl` + `+` three or four times).
5. Turn on Focus / Do not disturb. Close WhatsApp, mail, anything with notifications.
6. Make sure no `.env`, API key or personal tab is visible anywhere.
7. Open the FalkorDB Browser once at `http://localhost:3000` (you need 3 seconds of it in the video as proof the graph is real).

## Part B: Record the raw footage (2 takes)

**Take 1: the real agent (this is the proof).** Split screen: Claude Code terminal on the left, war room on the right.

1. Start the screen recording (Snipping Tool → Record → whole screen, or OBS).
2. War room: mode **Claude Code** → **Watch Claude Code**.
3. In `C:\dev\domino-agent`, run `claude` and paste:
   `New alert: Severe monsoon flooding across Ayutthaya and the Chao Phraya Basin; industrial estates closed, recovery expected in 3-5 weeks. Handle it as DOMINO.`
4. Let it work. Do not touch anything. When it asks for approval, wait 3 seconds so the plan card is visible, then press **Approve plan** in the war room and tell Claude Code: `I approved it in the war room. Continue.`
5. Stop recording when the report is accepted.

Do not worry if this take is long or slow. You will speed it up (with a "2×" label) and only use pieces of it.

**Take 2: the war room, calmly (replay).** Full screen browser only. Use **Replay** mode and play the recording of Take 1 (Claude will publish it for you). Replay pauses at the approval, so you can take your time.

Record each of these as a separate short clip (5–15 seconds each):
1. Overview before the alert (healthy world).
2. The alert and the step headline changing.
3. Overview: toggle **Tier-1 view** (0 problems) → **DOMINO** (the path to VoltCell lights up).
4. Supply chain view: the path VoltCell → BatteryMax / PowerCell → our plants.
5. Factories view: the plant with orders turning late.
6. AI agent view: "The plans it tested" (5 strategies) and the AmpereOne rejection.
7. AI agent view: click a step → **Show a database query** (the Cypher drawer).
8. Approve → Shipments view (the purchase orders) → "9 of 9 safety checks passed".
9. AI agent view: **What DOMINO remembers** with the date.
10. FalkorDB Browser (3 seconds).
11. `eval/RESULTS.md` or the README results table on GitHub.

## Part C: The script (shots + voiceover)

Read the voiceover slowly. Record your voice separately (phone in a quiet room is fine), then put it under the footage.

| Time | On screen | Voiceover |
|---|---|---|
| 0:00–0:12 | Black title card: "When one link breaks." (text only, no photo needed) | "In 2011, floods in Thailand stopped factories around the world. Many companies didn't know they depended on them, because the dependency was two tiers down." |
| 0:12–0:25 | Take 2, clip 1: the healthy world | "This is a supply chain in FalkorDB: suppliers, their suppliers, parts, plants and a hundred and seventeen customer orders." |
| 0:25–0:45 | Take 1: Claude Code reads the alert and starts calling tools (2× label) | "An alert comes in. Claude Code is the agent here. It can only use DOMINO's fixed graph tools, and it never writes database queries itself." |
| 0:45–1:05 | Take 2, clip 3: Tier-1 view shows 0 → DOMINO view lights the path | "A tier-1 view says nothing is wrong. DOMINO walks the graph: VoltCell, a cell factory in the flood zone, feeds two of our battery suppliers. Thirty-eight orders are exposed, and thirteen will be late." |
| 1:05–1:20 | Take 2, clip 6 or the capacity card | "FalkorDB's max-flow algorithm computes the real capacity through the whole network: seven hundred packs a week, not the nineteen hundred the tier-1 view promises." |
| 1:20–1:40 | Take 2, clip 6: AmpereOne rejected, then the five plans | "The cheapest backup, AmpereOne, buys its cells from the same flooded factory, so DOMINO rejects it. Then it copies the graph and tests five recovery plans side by side." |
| 1:40–2:05 | Take 1: the approval pause in the terminal + war room; you press Approve (2× label if needed) | "Nothing is bought without a human. I approve. DOMINO writes four purchase orders in one atomic transaction, and the agent checks the result: nine of nine checks pass. Twelve orders are protected on paper; the parts haven't arrived yet, and it says so." |
| 2:05–2:20 | Take 2, clip 7: the Cypher drawer | "Every step shows the exact Cypher it ran, and the final report is rejected if it cites a number that no tool returned." |
| 2:20–2:35 | Take 2, clip 9: What DOMINO remembers | "DOMINO keeps what it learned in a memory graph, with the date. The next time VoltCell shows up, the agent recalls it." |
| 2:35–2:50 | Take 2, clip 11: results table | "Across forty test disruptions, a tier-1 plan left a hundred and thirty orders late. DOMINO left fifty-seven, and an independent checker agrees with every number." |
| 2:50–3:00 | End card: DOMINO, Track 1, GitHub URL | "DOMINO, on FalkorDB. When one link breaks, it finds the chain." |

Do not say: "optimal", "fulfilled", "delivered", "the scripted demo shows the AI thinking", or "risk scan" (not built).

## Part D: Edit (free tools)

Use **Clipchamp** (comes with Windows 11) or CapCut.

1. Make a new 16:9 project. Drop in the clips in the order of Part C.
2. Put the voiceover track under them. Cut each clip to match its line.
3. Wherever you sped a clip up, add a small text label **"2×"** in a corner (honesty rule).
4. Add captions: Clipchamp → Captions → Auto-generate (English). Check the numbers in the captions by hand.
5. Add the end card with the GitHub URL.
6. Check the length is 3:00 or less. Export at 1080p.

## Part E: Upload and link

1. Upload to YouTube as **Public** or **Unlisted** (both can be watched with the link).
2. Open the link in a private/incognito window to check it plays when logged out.
3. Send Claude the link: it goes into the README (`TODO(video)`) and `docs/SUBMISSION.md`.
4. Keep the raw files of Take 1 as a backup.
