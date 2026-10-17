"""The only way Cypher reaches FalkorDB (CLAUDE.md rule 1).

`run_query(name, params)` loads `backend/domino/queries/<name>.cypher`, runs it
(GRAPH.RO_QUERY by default), and records `{name, cypher, params, ms, rows}`.
Those records feed the UI's Cypher drawer and docs/QUERIES.md.

Two FalkorDB behaviours are handled here so callers never see them (SPIKE #14):
- The image's TIMEOUT 1000 kills slow reads, so every call passes an explicit timeout.
- Results are silently cut at RESULTSET_SIZE rows, so a full result raises instead.
"""

from __future__ import annotations

import contextlib
import contextvars
import logging
import re
import time
from collections import deque
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path
from typing import Any, Iterator

from domino.config import settings
from domino.graph.client import get_db

QUERIES_DIR = Path(__file__).resolve().parents[1] / "queries"
_NAME_RE = re.compile(r"^[a-z0-9_]+(/[a-z0-9_]+)?$")

READ_TIMEOUT_MS = 5_000
WRITE_TIMEOUT_MS = 30_000

log = logging.getLogger("domino.query")


class QueryError(RuntimeError):
    pass


class ResultTruncatedError(QueryError):
    """The result hit RESULTSET_SIZE, so rows may be missing. Never use it as is."""


@dataclass
class QueryRecord:
    name: str
    cypher: str
    params: dict[str, Any]
    ms: float
    rows: int
    graph: str
    ro: bool

    def as_dict(self) -> dict[str, Any]:
        return {"name": self.name, "cypher": self.cypher, "params": self.params,
                "ms": self.ms, "rows": self.rows, "graph": self.graph, "ro": self.ro}


@dataclass
class _Capture:
    records: list[QueryRecord] = field(default_factory=list)


# Last N queries in this process (for the Cypher drawer), plus an optional per-run capture.
recent_queries: deque[QueryRecord] = deque(maxlen=500)
_capture: contextvars.ContextVar[_Capture | None] = contextvars.ContextVar("query_capture", default=None)


@contextlib.contextmanager
def capture_queries() -> Iterator[list[QueryRecord]]:
    """Collect every run_query record made inside the block (e.g. one agent run)."""
    cap = _Capture()
    token = _capture.set(cap)
    try:
        yield cap.records
    finally:
        _capture.reset(token)


@lru_cache(maxsize=None)
def load_cypher(name: str) -> str:
    """Read a query file. `//` comment lines document the query and are not sent."""
    if not _NAME_RE.match(name):
        raise QueryError(f"bad query name {name!r}")
    path = QUERIES_DIR / f"{name}.cypher"
    if not path.is_file():
        raise QueryError(f"no query file {path}")
    lines = [ln for ln in path.read_text(encoding="utf-8").splitlines() if not ln.strip().startswith("//")]
    return "\n".join(lines).strip()


@lru_cache(maxsize=1)
def resultset_size() -> int:
    """The server's RESULTSET_SIZE (10000 in the pinned image). <= 0 means unlimited."""
    try:
        _, value = get_db().connection.execute_command("GRAPH.CONFIG", "GET", "RESULTSET_SIZE")
        return int(value)
    except Exception:  # noqa: BLE001 - fall back to the image default
        return 10_000


def _summarize(value: Any) -> Any:
    """Keep the log readable: long lists (seed batches) are shown by length only."""
    if isinstance(value, list) and len(value) > 20:
        return f"<list of {len(value)}>"
    if isinstance(value, dict):
        return {k: _summarize(v) for k, v in value.items()}
    return value


def run_query(
    name: str,
    params: dict[str, Any] | None = None,
    *,
    ro: bool = True,
    graph: str | None = None,
    timeout_ms: int | None = None,
) -> list[dict[str, Any]]:
    """Run queries/<name>.cypher on `graph` (default: the live world) and return rows as dicts."""
    params = params or {}
    graph_name = graph or settings.world_graph_live
    cypher = load_cypher(name)
    timeout = timeout_ms or (READ_TIMEOUT_MS if ro else WRITE_TIMEOUT_MS)
    g = get_db().select_graph(graph_name)

    t0 = time.perf_counter()
    try:
        res = g.ro_query(cypher, params, timeout=timeout) if ro else g.query(cypher, params, timeout=timeout)
    except Exception as exc:
        raise QueryError(f"{name} on {graph_name}: {exc}") from exc
    ms = round((time.perf_counter() - t0) * 1000, 2)

    columns = [h[1] for h in res.header]
    rows = [dict(zip(columns, r)) for r in res.result_set]

    rec = QueryRecord(name=name, cypher=cypher, params=_summarize(params), ms=ms,
                      rows=len(rows), graph=graph_name, ro=ro)
    recent_queries.append(rec)
    cap = _capture.get()
    if cap is not None:
        cap.records.append(rec)
    log.debug("%s %s rows=%d %.1fms", graph_name, name, len(rows), ms)

    limit = resultset_size()
    if limit > 0 and len(rows) >= limit:
        raise ResultTruncatedError(
            f"{name} returned {len(rows)} rows = RESULTSET_SIZE; the result may be truncated. "
            "Narrow the query or page it with SKIP/LIMIT."
        )
    return rows


def group_records(records: list[QueryRecord]) -> list[dict[str, Any]]:
    """One row per named query, in first-run order, for the Cypher drawer: the text, the first call's
    params, how many times it ran, total rows and ms, and the graphs it touched (sandboxes included)."""
    out: dict[str, dict[str, Any]] = {}
    for r in records:
        g = out.get(r.name)
        if g is None:
            out[r.name] = {"name": r.name, "cypher": r.cypher, "params": r.params, "ro": r.ro,
                           "calls": 1, "rows": r.rows, "ms": r.ms, "graphs": [r.graph]}
            continue
        g["calls"] += 1
        g["rows"] += r.rows
        g["ms"] = round(g["ms"] + r.ms, 2)
        if r.graph not in g["graphs"]:
            g["graphs"].append(r.graph)
    return list(out.values())


def run_script(name: str, *, graph: str | None = None, timeout_ms: int | None = None) -> int:
    """Run a multi-statement file (statements separated by `;`), one write per statement.

    Used only for schema DDL. Each statement is logged as `<name>#<i>`.
    """
    graph_name = graph or settings.world_graph_live
    statements = [s.strip() for s in load_cypher(name).split(";") if s.strip()]
    g = get_db().select_graph(graph_name)
    for i, stmt in enumerate(statements, 1):
        t0 = time.perf_counter()
        try:
            g.query(stmt, timeout=timeout_ms or WRITE_TIMEOUT_MS)
        except Exception as exc:
            raise QueryError(f"{name}#{i} on {graph_name}: {exc}") from exc
        rec = QueryRecord(name=f"{name}#{i}", cypher=stmt, params={},
                          ms=round((time.perf_counter() - t0) * 1000, 2), rows=0, graph=graph_name, ro=False)
        recent_queries.append(rec)
        cap = _capture.get()
        if cap is not None:
            cap.records.append(rec)
    return len(statements)
