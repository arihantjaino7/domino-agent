# Database evaluation environment incident

Database recovery scoring is incomplete. This is an environment blocker, not a passing evaluation.

1. The local FalkorDB initially answered reads, but an isolated evaluation smoke run hit `GRAPH.COPY failed, could not fork`.
2. Redis then reported `rdb_last_bgsave_status=err` and rejected writes with `MISCONF`. Docker could not read the container log or image metadata (`input/output error`); even `docker exec` could not execute the container shell.
3. Read-only exports and Redis DUMP backups were saved for all six original graphs. The user explicitly approved trying a Docker restart after those backups.
4. The normal Docker Desktop restart timed out while stopping. Only processes verified to come from the Docker installation and the `docker-desktop` WSL instance were stopped before relaunching Docker.
5. Docker then failed to start its WSL data disk: `preparing block device /dev/sde`, `No such device or address while trying to determine filesystem size`. Its bootstrap also logged `detected no file system. Formatting`; that automatic attempt failed. No format, reset, unregister, prune, volume deletion or filesystem-repair command was issued by Codex.
6. The failed Docker startup and only the `docker-desktop` instance were stopped to avoid further provisioning attempts. Docker/FalkorDB is currently unavailable. Other WSL distributions were not terminated.

## Backups

Private, ignored backup folder: `eval/out/db-backup/`. Its `manifest.json` records the raw JSON export, Redis DUMP, SHA-256 hashes, TTL, indexes and constraints for each graph:

| Graph | Nodes | Relationships |
|---|---:|---:|
| memory | 7 | 9 |
| memory:dryrun | 5 | 6 |
| world:cli:monsoon | 348 | 1004 |
| world:cli:panel_fire | 345 | 981 |
| world:live | 343 | 968 |
| world:pristine | 341 | 966 |

All six backups completed without errors. They are not committed or pushed. Backups have not been restore-tested because the database is unavailable; their counts and checksums are verified. Do not assume the Docker disk or its saved snapshots contain the newest in-memory state.

## Validations that completed

- [Database-free projection checks](OFFLINE_CHECKS.md): 60/60 checks on fixed seeds 42–61, with healthy, Monsoon and Panel Fire inputs.
- [Read-only snapshot checks](READ_ONLY_CHECKS.md): 4/4 existing worlds matched the independent oracle and were unchanged by all recorded read-only queries. These checks include existing committed POs where present.
- Oracle, harness and seed unit checks passed. Exact commands and counts are in `docs/CODEX_NOTES.md`.
- The failed initial smoke metrics remain locally under `eval/out/smoke/`; they are not promoted as recovery benchmark results.

## Resume

First recover Docker/WSL storage without resetting other project data, then validate the saved graph backups against the running instance. Restoring or repairing storage needs separate review; the evaluation command does not do either.

After FalkorDB is healthy, run from the repo root:

```powershell
uv sync --project backend
uv run --project backend pytest backend/tests eval -q
uv run --project backend python -m eval.run
```

The runner uses seeds 42–61, both disruption motifs, four hand-worked fixtures and two free scripted repeats of each scenario. It fails nonzero on incomplete coverage, oracle mismatches, graph-aware safety failures or scripted smoke failures, while retaining baseline violations. It never calls a paid API. `make eval` runs the same default recipe.

The independent oracle and runner are not yet integration-validated across the complete database trial matrix. Do not fill README recovery numbers from the partial or offline checks.
