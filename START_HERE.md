# DOMINO: Start Here (setup guide for the other laptop)

This kit has everything needed to build DOMINO on any laptop:

| File | What it is |
|---|---|
| `START_HERE.md` | This guide: setup, the order of work, the exact prompts to paste into Claude Code, and how to check each step yourself |
| `docs/PLAN.md` | The full master plan. **§0.1 (crunch timeline) and §0.2 (fixes + organizer guidance) come first** |
| `CLAUDE.md` | Rules Claude Code reads automatically in this repo |
| `.env.example` | Config template. Copy it to `.env` and add your API key |
| `.gitignore` | Keeps `.env`, `node_modules`, etc. out of git |

> **Deadline:** Oct 18, 23:59 IST. **Submit by 21:00 IST.** The hours after that are buffer only.
> **Track:** Track 1, *Agents That Act on Connected Data* (only this one).

---

## Part A: One-time setup (≈45 min)

### A1. Install the tools

Follow the section for the laptop's operating system.

**macOS**
1. Install Docker Desktop from docker.com and start it once.
2. Install Homebrew (brew.sh) if you don't have it, then run:
   ```bash
   brew install git gh node pnpm
   ```
3. Install `uv` (the Python manager):
   ```bash
   curl -LsSf https://astral.sh/uv/install.sh | sh
   ```
4. Install Python 3.12 through uv:
   ```bash
   uv python install 3.12
   ```

**Windows** (recommended: do everything inside WSL2 Ubuntu)
1. Open PowerShell as admin and run `wsl --install`, then reboot. Open the "Ubuntu" app.
2. Install Docker Desktop. In Settings → Resources → WSL Integration, enable it for Ubuntu.
3. Inside Ubuntu:
   ```bash
   sudo apt update && sudo apt install -y git make curl unzip
   ```
4. Install `uv` and Python 3.12:
   ```bash
   curl -LsSf https://astral.sh/uv/install.sh | sh && source ~/.bashrc && uv python install 3.12
   ```
5. Install Node 22 LTS (via nvm or nodejs.org), then turn on pnpm:
   ```bash
   corepack enable
   ```
6. Install the GitHub CLI by following cli.github.com. **Keep the project inside the Ubuntu home folder** (`~/domino`), not on `C:\`, because it's much faster.

**Linux:** same as the Windows/Ubuntu steps, but without WSL.

**Claude Code:** install the Claude desktop app and use its Code tab, or install the Claude Code CLI using the official docs (code.claude.com). Sign in with your account.

### A2. Check the installs
```bash
docker --version && git --version && node --version && pnpm --version && uv --version && gh --version
```
Every command should print a version. If one fails, reinstall that tool before going on.

### A3. Accounts and keys
- **Anthropic Console:** create an API key and **set a monthly spend limit first** (for example $30–50).
- **GitHub:** run `gh auth login` and follow the prompts.
- **FalkorDB Discord** (linked on the hackathon page): ask whether `algo.maxFlow` exists in the `falkordb/falkordb:latest` image. It takes 5 minutes and removes your biggest unknown.

---

## Part B: Create the repo (≈10 min)

1. Make the project folder and copy this kit's contents into it, including the hidden files `.env.example` and `.gitignore`:
   ```bash
   mkdir -p ~/domino && cd ~/domino
   ```
   If you copied the kit as `domino-starter.zip` into Downloads (on Windows/WSL, Downloads is `/mnt/c/Users/<your-name>/Downloads`):
   ```bash
   unzip ~/Downloads/domino-starter.zip -d /tmp/kit && cp -R /tmp/kit/domino-starter/. ~/domino/
   ```
2. Create your local `.env` and paste your API key into it (never commit this file):
   ```bash
   cp .env.example .env
   ```
3. Make the first commit:
   ```bash
   git init && git add . && git commit -m "Start DOMINO: plan, Claude rules, config template"
   ```
4. Create the GitHub repo. Keep it private for now; make it **public before submitting**:
   ```bash
   gh repo create domino-agent --private --source . --push
   ```

> The plan was written on Oct 14, before the start, as planning notes (rule 8 allows that). All code is written after the start, and the commit history shows it. The README will say this openly.

---

## Part C: Start FalkorDB and check it works (≈5 min)

1. Start FalkorDB:
   ```bash
   docker run -d --name falkordb -p 6379:6379 -p 3000:3000 falkordb/falkordb:latest
   ```
2. Open **http://localhost:3000** (FalkorDB Browser), connect with the defaults, and run the official max-flow example:
   ```cypher
   CREATE (a:Node {name:'A'}), (b:Node {name:'B'}), (c:Node {name:'C'}),
          (a)-[:PIPE {cap:10}]->(b), (a)-[:PIPE {cap:5}]->(c), (b)-[:PIPE {cap:8}]->(c)
   ```
   ```cypher
   MATCH (s:Node {name:'A'}), (t:Node {name:'C'})
   CALL algo.maxFlow({sourceNodes:[s], targetNodes:[t], capacityProperty:'cap', relationshipTypes:['PIPE']})
   YIELD maxFlow RETURN maxFlow
   ```
   **You should see `13`.** If you get "procedure not found", stop and tell Claude Code; the spike (M1) will pick a fallback.
3. Later, if `docker run` says the name is already in use:
   ```bash
   docker start falkordb
   ```

---

## Part D: Build it with Claude Code, milestone by milestone

**How to work:**
- Open Claude Code **inside `~/domino`**.
- For each milestone below, paste the prompt and let it work, then **check the "You verify" commands yourself.**
- Commit after each milestone:
  ```bash
  git add -A && git commit -m "M<number>: <what>" && git push
  ```
- Start a fresh session (or `/clear`) between milestones so the context stays clean.
- After each milestone, Claude asks you 2–3 questions. **Answer them out loud.** You'll need this for the judges (rule 12).

### 🌙 Tonight (Fri): get the graph working

**M1: scaffold and capability spike** (≈1 h)
> Read CLAUDE.md, then docs/PLAN.md §0.1, §0.2, §5, §6, §14. Create the repo skeleton from §14.2: a uv + FastAPI backend with `GET /api/health` (it pings FalkorDB), a placeholder Vite + React + TS frontend using pnpm, and a docker-compose.yml with FalkorDB (image from `.env`, ports 6379 and 3000). Add a Makefile with targets `up`, `down`, `seed`, `test`, `dev`, `cli`, `demo-headless`, `eval` (stubs are fine for the ones not built yet). Then write `scripts/spike.py` that tests every capability in §15.2 M1 (including the three new checks: rollback on constraint error, inline maps with UNWIND variables, FastMCP mounted in FastAPI's lifespan) against the running FalkorDB, and writes a ✓/✗ table with fallbacks to `docs/SPIKE.md`. Don't build engines yet. Explain every spike result to me in plain language.

**You verify:**
```bash
make up && make test && curl -s localhost:8000/api/health
```
Then open `docs/SPIKE.md`. Every row should be ✓ or have a fallback written down.

**M2: world generator** (≈2.5 h)
> Read docs/PLAN.md §5 completely, plus §0.1. Implement `backend/domino/seed/generator.py` and `motifs.py`. The world must be fully determined by WORLD_SEED: the hand-built Monsoon motif (§5.6) and Panel Fire motif (§5.8), Scarce Silicon (§5.7) only if it's quick, plus random fill (~300 nodes tonight is fine). Load it with batched UNWIND queries stored in `queries/*.cypher`, apply the §5.9 schema (indexes, full-text index on `:Place`, unique constraint on PurchaseOrder.id), and create `world:pristine` → `world:live` with GRAPH.COPY (§5.10). `make seed` should print entity counts. Show me where each motif number lives in the code.

**You verify:**
```bash
make seed
```
Then in the FalkorDB Browser, select graph `world:live` and run:
```cypher
MATCH (s:Site {id:'S-VOLT-AYU'})-[f:FEEDS]->(t:Site) RETURN s, f, t
```
VoltCell should feed PowerCell, BatteryMax and AmpereOne. **Take a screenshot** for the README.

**M3: exposure and shortage** (≈3 h)
> Read docs/PLAN.md §7.3, §7.5 (including the complementary-inputs fix), §8 (Q-TIER1-VIEW, Q-EXPOSURE, Q-SHORTAGE-ORDERS) and §0.2. Create `tests/fixtures/tiny_world.py` (~15 nodes) with expected results I can check by hand, plus the adversarial fixtures from CLAUDE.md. Implement `engines/exposure.py` and `engines/shortage.py` with tests. Add a test that the pristine demo world has 0 projected-late orders. Add `make cli SCENARIO=monsoon`, which declares the Monsoon incident on a fresh copy of the world and prints: tier-1 view, multi-tier exposure with evidence paths, and exposed vs projected-late orders with stockout days per plant. Then ask me 3 questions about the queries.

**You verify:**
```bash
make test && make cli SCENARIO=monsoon
```
Expected: tier-1 view = **0** directly affected. Multi-tier = **2 tier-1 sites via S-VOLT-AYU**. Guadalajara is exposed but covered. Penang and Bac Ninh have projected-late orders.

🚦 **Gate 1 (before sleeping):** M3 passes. If not, finish M3 first thing tomorrow and shift the rest of the day by the same amount.

### ☀️ Saturday: the agent acts, and the UI

**M4: true capacity and alternatives** (≈2 h)
> Read docs/PLAN.md §7.6 (including the min-cut fix), §7.7 (exposure ≠ rejection), §8 (Q-FLOW-EXTRACT, Q-MAXFLOW, Q-ALTERNATIVES) and §0.2. Implement `engines/capacity.py`: extract → scratch graph with node splitting → algo.maxFlow → min cut from residual reachability on the full network held in Python → standalone, remaining-clean and naive capacities → cleanup in `finally`. Test it on the docs example (max flow 13) and on a hand-checked network where a saturated edge is NOT in the min cut. Then implement `engines/alternatives.py`: AmpereOne must be rejected (remaining capacity 0, with its path); PowerCell-extra must be accepted at reduced capacity with an exposure warning. Explain node splitting and the min cut to me with an ASCII drawing.

**You verify:**
```bash
make test && make cli SCENARIO=monsoon
```
Naive vs true capacity is printed for BAT-4S and BAT-6S. AmpereOne is rejected with its path.

**M5: allocator, sandboxes, executor, verifier** (≈2.5 h)
> Read docs/PLAN.md §0.1 (the graph-aware greedy allocator), §7.9–§7.12, Q-EXECUTE-PREFLIGHT, Q-EXECUTE and §0.2. Implement in order, with tests after each: the greedy allocator (naive mode = baseline B1, graph-aware mode = DOMINO, same code, with cell bookkeeping), the strategy presets, GRAPH.COPY sandbox simulation with **joint proportional rationing**, the executor (preflight, then one atomic write, then the receipt), and verifier V1–V9 (V8 = material balance across the whole plan) with negative tests where bad plans must be caught. Add the net-benefit line and graph-diff receipt. Print the sandbox comparison table for Monsoon.

**You verify:**
```bash
make test && make cli SCENARIO=monsoon
```
In the comparison table the baseline must protect fewer orders than DOMINO, and its shortfall must be visible. Running the same execution twice must create 0 duplicates. Every V check on DOMINO's plan should pass.

**M6: MCP server, agent, approval, memory** (≈3.5 h)
> Load the claude-api skill first. Read docs/PLAN.md §7.13, §9 (all of it), §10 and §0.2. Implement the memory-graph functions (recall returns dates), the FastMCP server mounted at /mcp with the P0 tools from §9.4 (no Cypher-writing tool; IDs validated against the graph; compact summaries go to the LLM, full payloads go to the UI; run_id injected and hidden from the schema), and the manual agent loop from §9.2 with the §9.3 settings. Add SSE events (§10), approval pause/resume bound to plan_hash + world_version, run persistence, structured-claim validation and the entity guard. Add `make demo-headless SCENARIO=monsoon`, which runs the whole thing in the terminal, asks me to approve, then verifies and prints the report. Print tokens and $ cost per run.

**You verify:**
```bash
make demo-headless SCENARIO=monsoon
```
The tool calls print as they happen. It stops for your approval, then verifies and prints a report. Note the $ cost. Now try the non-event scenario: it must say "not in the graph" and **not** "safe".

**M7: deploy the skeleton** (≈45 min)
> Read docs/PLAN.md §14.4. Write the production docker-compose (falkordb with a volume, app serving the built frontend, Caddy with automatic HTTPS) and a short `docs/DEPLOY.md` for a fresh Ubuntu VPS. SSE must work through Caddy (no buffering). Give me the exact commands to run on the VPS.

**You verify:** on the VPS, `https://<your-domain-or-ip>.sslip.io/api/health` works, and a test SSE stream arrives live.

**M8: the war-room UI** (≈6–7 h, in two or three prompts)
> Read docs/PLAN.md §11 completely and use the impeccable or ui-ux-pro-max skill. Build the single war-room screen in steps, checking with me after each: (1) layout, React Flow + elkjs tiered canvas, API client, SSE store, timeline, KPI strip, inject menu, alert ticker; (2) hop-by-hop propagation animation, cascade bar, status colors, evidence-chip highlighting, Cypher drawer; (3) plan comparison with net benefit, approval card, execution animation, verification panel with the graph-diff receipt, tier-1 ↔ DOMINO toggle, Memory tab. Nothing on screen may show a number that didn't come from the API.

**You verify:**
```bash
make dev
```
Open the frontend. Run Monsoon from the alert ticker → watch the propagation → plan comparison → Approve → verification.

🚦 **Gate 2 (Saturday night):** the full Monsoon loop is clickable locally. **P1 features may start only after this gate.**

### 🏁 Sunday: prove it and ship

| Milestone | Prompt (short) | You verify |
|---|---|---|
| **M9** Panel Fire + rehearsal (08:30–10:30) | "Make the Panel Fire scenario (§5.8, §12) work end to end in the UI. Then help me rehearse: list everything that looked wrong in 3 runs of each scenario and fix the prompt or tool descriptions." | 6/6 runs complete. **Record backup video take #1** |
| **M10** Evaluation (10:30–12:00) | "Read §13 and §0.2. Build eval/: deterministic methods B0/B1/B2 on ~20 generated worlds (no LLM), the agent on 3 scenarios × 2 runs, the networkx oracle, adversarial fixtures, query-performance table, and a script-generated RESULTS.md with failures included." | `make eval` writes RESULTS.md. Don't edit numbers by hand |
| **M11** Final deploy (12:00–13:00) | "Deploy the final build. Add replay mode (recorded runs) and per-IP rate limits (§14.4)." | Open the URL on your phone in a private tab |
| **M12** Docs (13:00–14:30) | "Write the README (§17.2), docs/DATA_MODEL.md, docs/QUERIES.md (generated from queries/), docs/ARCHITECTURE.md, docs/AI_DISCLOSURE.md, and the transparency note about the pre-event plan." | §17.1 checklist all ✓ |
| **M13** Video (14:30–17:00) | Use §16 as the script. Record the screen and your voice separately; add captions; ≤3:00 | Link plays when logged out |
| **M14** Blog post + MCP clip (17:00–18:30) | "Draft the blog post from §17.3 using our real RESULTS.md numbers." Then connect Claude Code/Desktop to `/mcp` and record 10 seconds | Published (skip if behind) |
| **M15** Submit (18:30–21:00) | — | Repo public · README · QUERIES.md · video · live URL + local setup · **Track 1** · AI disclosure |

### ⭐ P1 features: only after Gate 2, in this order (see §0.2)

1. **Second disruption → repair → remember** (3–4 h):
   > Read docs/PLAN.md §0.2 item 1 and §7.13–§7.15. After a plan is executed, add an event "Day 7: ElectroHub reports a 50% shortfall". Verification must flag which protected orders are now threatened. The agent re-plans with still-valid POs locked (smallest change) and shows old plan → changed fact → affected orders → revised plan (+$). Write the Outcome to memory; the next Monsoon run must cite it and change its recommendation.
2. **Stress-test this plan** (2 h):
   > Read §0.2 item 2. Score every strategy in sandboxes against 5–6 futures generated from the graph (correlated by shared region, hazard zone, port or upstream site), and show base-case vs worst-case orders protected and which assumption breaks each plan. Report "passed N of M tested futures", never a probability.
3. **"What would save this order?"** (2 h):
   > Read §0.2 item 3. Clicking an unprotected order re-runs the allocator with one relaxation at a time and shows only options that are feasible in the sandbox, with their side effects. If none work, name the binding constraint.

---

## Part E: If something breaks

| Problem | Fix |
|---|---|
| `Cannot connect to the Docker daemon` | Start Docker Desktop and wait until it says "running" |
| Port 6379 or 3000 already in use | `docker ps` to find what's using it → `docker stop <id>` (or change the port in `.env`) |
| `procedure algo.maxFlow not found` | Check the image tag; ask in the FalkorDB Discord. Fallback in PLAN §18: run max-flow in Python on the same Cypher-extracted network (documented as a fallback) |
| `uv: command not found` | Open a new terminal, or `source ~/.bashrc` (or `~/.zshrc`) |
| The agent loops or makes too many tool calls | Check the run cap (30) in `.env`, tighten the tool descriptions, re-run the scenario |
| API cost is climbing | Lower `DOMINO_EFFORT`, check prompt caching is hitting (`cache_read_input_tokens > 0`), use replay mode for UI work |
| SSE events arrive all at once | Engines must run through `asyncio.to_thread`; behind a proxy, set `X-Accel-Buffering: no` |
| Claude Code drifts beyond the milestone | Say: "Stop. Re-read CLAUDE.md and only do the current milestone." |

---

## Part F: Daily routine
- **Start of the day:** re-read today's gate in PLAN §0.1.
- **After every milestone:** commit and push; add one line to `docs/DECISIONS.md` (what you decided and why).
- **End of the day:** record a 60-second screen capture of progress (for the video and blog) and spend 20 minutes explaining the day's queries out loud.
- **Sleep at least 6 hours.** A tired demo loses.

**Never cut:**
- Monsoon end to end.
- The tier-1 ↔ multi-tier contrast.
- `algo.maxFlow`.
- AmpereOne rejected with its path.
- Baseline vs DOMINO compared in GRAPH.COPY sandboxes.
- The agent working over MCP.
- Approve → atomic execute → verify.
- README with the data model, plus QUERIES.md.
- The video.

All the best. Bring the iPhone home 🎯
