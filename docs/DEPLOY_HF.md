# Deploying DOMINO on Hugging Face Spaces

> Since mid-2026 Hugging Face requires a PRO plan for Docker Spaces. For a free host, use
> [DEPLOY_RENDER.md](DEPLOY_RENDER.md) (the same image). These steps still apply to a PRO account.

One container runs everything: FalkorDB (the pinned image from the spike, listening only inside the container),
the FastAPI app and the built war room. The Space builds the code straight from GitHub, so it needs just two files
from `deploy/huggingface/`.

What visitors can do there: **Replay** (a recorded real Claude Code run; no API key, nothing in the graph changes)
and **Demo** (the free scripted run, with the real tools, approval, execution and verification). **Claude API** mode
needs an API key and is off unless you add one. **Claude Code over MCP** is closed unless you set `MCP_API_KEY`
(without it the container generates a random key, so nobody can drive the shared world through `/mcp`).

## Steps (about 10 minutes, most of it the first build)

1. The GitHub repo must be **public** (the Space clones it while building).
2. Sign in at https://huggingface.co (create a free account if needed).
3. Top right: your avatar → **New Space**.
   - Owner: you. Space name: `domino`.
   - License: MIT.
   - SDK: **Docker**, template **Blank**.
   - Hardware: **CPU basic (free)**.
   - Visibility: **Public**.
   - Press **Create Space**.
4. In the new Space: **Files** → **Add file** → **Upload files**. Upload both files from `deploy/huggingface/`:
   `Dockerfile` and `README.md` (replace the README the Space created). Press **Commit changes to main**.
5. The Space starts building (**Building** badge; the logs are under **Logs**). The first build takes 5–10 minutes.
   When the badge says **Running**, the app shows on the Space page. The direct address is
   `https://<your-user>-domino.hf.space`.
6. Check it: open the address in a private window, choose **Replay**, press **Play the recording**, and press
   **Approve** when it pauses. Then try **Demo** → **Run the demo**.
7. Optional secrets (Space → **Settings** → **Variables and secrets** → **New secret**):
   - `MCP_API_KEY`: a long random string, if you want Claude Code to drive this public copy over MCP
     (`https://<your-user>-domino.hf.space/mcp/` with `Authorization: Bearer <key>`; also set the variable
     `DOMINO_PUBLIC_HOST` to `<your-user>-domino.hf.space`).
   - `ANTHROPIC_API_KEY`: only with a spend limit set in the Anthropic Console. Runs are capped per visitor and per day.

## Good to know

- **Free Spaces sleep** after about 48 hours without visitors, and the disk is not kept: on wake-up the world is
  built again from `WORLD_SEED`, and the memory graph starts empty. The published replays are part of the image.
- **Everyone shares one world.** A visitor's run or reset changes what the others see.
- **New commits** reach the Space only after a rebuild: Space → **Settings** → **Factory rebuild**.
- The same image runs anywhere Docker runs: `docker build -f deploy/single/Dockerfile -t domino-single .`
  then `docker run --rm -p 7860:7860 domino-single` and open http://localhost:7860.
