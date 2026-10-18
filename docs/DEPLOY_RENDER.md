# Deploying DOMINO on Render (free web service)

One container runs everything: FalkorDB (the pinned image from the spike, listening only inside the container),
the FastAPI app and the built war room. Render builds `deploy/single/Dockerfile` straight from the GitHub repo.

Tested locally under the free plan's limits (`docker run --memory=512m --cpus=0.1`): the container starts in about
50 s and uses about 100 MB idle. A full scripted run reaches approval in about 50 s, executes and completes, and
peaks at about 160 MB of the 512 MB.

What visitors can do there: **Replay** (a recorded real Claude Code run; no API key, nothing in the graph changes)
and **Demo** (the free scripted run, with the real tools, approval, execution and verification). **Claude API** mode
needs an API key and is off unless you add one. **Claude Code over MCP** needs the `MCP_API_KEY` that Render
generates.

## Steps (about 15 minutes, most of it the first build)

1. The GitHub repo must be **public**, or connect your GitHub account to Render.
2. Sign in at https://render.com with GitHub. The free plan needs no card.
3. Choose **New** → **Blueprint**, pick the `domino-agent` repo and press **Apply**. Render reads `render.yaml`
   (a free Docker web service named `domino`).
   - If Blueprint asks for a card, use **New** → **Web Service** instead. Pick the repo, then set:
     - Language: **Docker**
     - Instance type: **Free**
     - Dockerfile path: `./deploy/single/Dockerfile`
     - Docker build context: `.` (the default)
     - Health check path (under Advanced): `/api/health`
4. The first build takes about 10 minutes (the logs are on the service page). When it says **Live**, open the address
   at the top (`https://domino-xxxx.onrender.com`).
5. Check it: open the address in a private window, choose **Replay**, press **Play the recording**, and press
   **Approve** when it pauses. Then try **Demo** → **Run the demo**.
6. Optional, under **Environment**:
   - `ANTHROPIC_API_KEY`: only with a spend limit set in the Anthropic Console. Runs are capped per visitor and per day.
   - `MCP_API_KEY` shows the generated key. Claude Code on any computer can drive this copy with it:
     [MCP_REMOTE.md](MCP_REMOTE.md). The public host name is picked up automatically from Render.
   - `MCP_OPEN` = `true` opens `/mcp` to anyone with the address (no key). Buying still needs Approve in the war room.

## Good to know

- **Free services sleep** after 15 minutes without visitors. The next visit wakes the service in about a minute,
  and the world is built again from `WORLD_SEED` (the disk is not kept, so the memory graph starts empty). Open the
  address a few minutes before a judge or a demo looks at it.
- The free plan gives 750 instance hours a month, enough for one service that runs all month.
- **Everyone shares one world.** A visitor's run or reset changes what the others see.
- **New commits** to `main` deploy automatically (`autoDeploy` in `render.yaml`).
- The same image runs anywhere Docker runs: `docker build -f deploy/single/Dockerfile -t domino-single .`
  then `docker run --rm -p 7860:7860 domino-single` and open http://localhost:7860.
