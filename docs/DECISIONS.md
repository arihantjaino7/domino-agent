# Decisions log

One line per decision: date, milestone, what we decided, and why. Newest last.

- **2026-10-16 · M1** · Native Windows dev (not WSL). The Makefile's recipes are plain commands that run under cmd.exe, bash and zsh, and anything fancier goes in `scripts/*.py`. *Why:* the dev machine is native Windows, and `make` there uses cmd.exe because `sh` isn't on the PATH.
- **2026-10-16 · M1** · FalkorDB image pinned by digest `falkordb/falkordb@sha256:b0bdcac2…ae7a` (graph module 42201). Compose reuses the container name `falkordb` and keeps data on the `domino_falkordb_data` volume at `/var/lib/falkordb/data`. *Why:* the spike passed on exactly this build.
- **2026-10-16 · M1** · We keep the image defaults `TIMEOUT 1000` and `RESULTSET_SIZE 10000`. *Why:* they protect the public demo, and every engine query is small. `run_query` will pass an explicit per-query timeout and raise on a result of exactly RESULTSET_SIZE rows, because truncation is otherwise silent (SPIKE #14).
- **2026-10-16 · M1** · MCP SDK 2.x: `MCPServer` (formerly `FastMCP`) is mounted in the FastAPI app at `/mcp`, with its session manager started in the lifespan. No separate process is needed (SPIKE #16). We'll set the deploy hostname in `allowed_hosts`, because the SDK rejects foreign `Host` headers with 421.
- **2026-10-16 · M1** · `algo.betweenness` is not used for port chokepoints (P1). We'll use `algo.maxFlow` knockouts or exact betweenness in Python instead. *Why:* its scores are sample estimates that don't match hand-computed values, and unseeded calls vary between runs (SPIKE #4).
- **2026-10-16 · M1** · We don't re-apply the schema after `GRAPH.COPY`. *Why:* indexes, the full-text index and the unique constraint are all copied (SPIKE #5).
- **2026-10-16 · M1** · Q-EXECUTE stays a single write query, with the preflight read before it. *Why:* a constraint violation rolls back the whole query, including nodes, edges and SETs (SPIKE #11).
