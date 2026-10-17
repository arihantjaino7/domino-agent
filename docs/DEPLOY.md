# Deploying DOMINO on a fresh Ubuntu VPS

One small VPS runs three containers from `docker-compose.prod.yml`:

- **falkordb**: the graph database. It has no public ports, and its data lives on a Docker volume.
- **app**: FastAPI. It serves the built React frontend at `/`, the REST/SSE API at `/api` and MCP at `/mcp`.
- **caddy**: automatic HTTPS, streaming SSE through without buffering.

Tested locally with the same files (2026-10-17): health and frontend through Caddy, SSE events arriving live while the stream stays open, world seeded on first start.

## 0. What you need

- An Ubuntu 22.04/24.04 VPS with **2 GB RAM or more** (the image build runs `pnpm build`) and a public IPv4 address.
- No domain needed. `sslip.io` turns the IP into a hostname. Example: IP `203.0.113.7` becomes `203-0-113-7.sslip.io`.
- The GitHub repo must be cloneable from the VPS: make it public, or use `gh auth login` on the VPS.

## 1. Install Docker and open the firewall (on the VPS, as root)

```bash
apt update && apt install -y git curl ufw
```

```bash
curl -fsSL https://get.docker.com | sh
```

```bash
ufw allow OpenSSH && ufw allow 80/tcp && ufw allow 443/tcp && ufw --force enable
```

## 2. Get the code and configure it

```bash
git clone https://github.com/arihantjaino7/domino-agent.git domino && cd domino
```

```bash
cp .env.example .env
```

Edit `.env` (`nano .env`) and set:

| Variable | Value |
|---|---|
| `ANTHROPIC_API_KEY` | your key (**set a spend limit in the Anthropic Console first**) |
| `DOMINO_DOMAIN` | `203-0-113-7.sslip.io` (your IP with dashes) |
| `DOMINO_PUBLIC_HOST` | the same host name |
| `MCP_API_KEY` | output of `openssl rand -hex 24`. Without it, anyone could call the tools |
| `LIVE_RUNS_PER_HOUR_PER_IP`, `LIVE_RUNS_PER_DAY` | caps on real (paid) agent runs; defaults are 5 and 40 |

Leave `FALKORDB_IMAGE` as it is. It is pinned to the digest the spike passed on.

## 3. Start

```bash
docker compose -f docker-compose.prod.yml up -d --build
```

The first start builds the image (a few minutes), builds `world:pristine` from `WORLD_SEED` and copies it to `world:live`. Caddy fetches the HTTPS certificate on the first request.

## 4. Check it

```bash
curl -s https://203-0-113-7.sslip.io/api/health
```

Expected: `{"status":"ok","falkordb":"ok","graph_module_ver":42201}`. Open the same address in a browser to see the frontend.

**SSE through the proxy.** This starts a free scripted run that pauses at approval. Events must print immediately while the stream stays open:

```bash
RID=$(curl -s -X POST https://203-0-113-7.sslip.io/api/runs -H 'content-type: application/json' -d '{"scenario":"monsoon","dry_run":true}' | sed 's/.*"run_id":"\([^"]*\)".*/\1/')
```

```bash
curl -N --max-time 15 https://203-0-113-7.sslip.io/api/runs/$RID/events
```

**MCP with the key** (Claude Desktop / Claude Code): use the server URL `https://203-0-113-7.sslip.io/mcp/` with the header `Authorization: Bearer <MCP_API_KEY>`. Requests without the key get 401.

## 5. Day-to-day

| Task | Command |
|---|---|
| Deploy a new version | `git pull && docker compose -f docker-compose.prod.yml up -d --build` |
| Reset the demo world | `curl -X POST https://203-0-113-7.sslip.io/api/world/reset` |
| Logs | `docker compose -f docker-compose.prod.yml logs -f app` |
| Snapshot the memory graph | `docker compose -f docker-compose.prod.yml exec falkordb redis-cli BGSAVE` |
| Stop | `docker compose -f docker-compose.prod.yml down` (data volumes are kept) |

## Notes

- **Restarts keep the live world and memory.** `domino.seed.ensure` only builds what is missing. To regenerate the world on purpose: `docker compose -f docker-compose.prod.yml exec app python -m domino.seed`.
- **Real agent runs are capped** per visitor per hour and globally per day (HTTP 429 after that). `dry_run` runs use the scripted model and cost nothing.
- Replay mode for recorded runs, and per-visitor worlds, come in M11.
