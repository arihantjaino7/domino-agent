"""Graph lifecycle (PLAN §5.10): build `world:pristine`, then GRAPH.COPY it to `world:live`.

The schema is applied once to pristine; GRAPH.COPY carries indexes, the full-text
index and the unique constraint to every copy (SPIKE #5), so copies never re-apply it.
"""

from __future__ import annotations

from typing import Any

from domino.config import settings
from domino.graph.client import get_db
from domino.graph.run_query import run_query
from domino.graph.schema import apply_schema
from domino.seed.world import NODE_GROUPS, World

BATCH_SIZE = 500


def drop_graph(name: str) -> bool:
    db = get_db()
    if name in db.list_graphs():
        db.select_graph(name).delete()
        return True
    return False


def copy_graph(src: str, dst: str) -> None:
    """Replace `dst` with a copy of `src` (GRAPH.COPY)."""
    drop_graph(dst)
    get_db().select_graph(src).copy(dst)


def _load_batches(query: str, rows: list[dict[str, Any]], graph: str) -> int:
    created = 0
    for i in range(0, len(rows), BATCH_SIZE):
        batch = rows[i:i + BATCH_SIZE]
        got = run_query(query, {"rows": batch}, ro=False, graph=graph)[0]["created"]
        # MATCH drops a row whose endpoint is missing without any error, so check the receipt.
        if got != len(batch):
            raise RuntimeError(f"{query}: created {got} of {len(batch)} rows")
        created += got
    return created


def load_world(world: World, graph: str) -> dict[str, int]:
    """Write every node group, then every edge type, in batched UNWIND queries."""
    receipt: dict[str, int] = {}
    for group, query in NODE_GROUPS.items():
        receipt[group] = _load_batches(query, world.nodes[group], graph)
    for rel, rows in world.edges.items():
        receipt[rel] = _load_batches(f"seed/edges_{rel.lower()}", rows, graph)
    run_query("seed/meta", {"seed": world.seed, "fingerprint": world.fingerprint()}, ro=False, graph=graph)
    return receipt


def graph_counts(graph: str) -> dict[str, int]:
    """Node count per primary label and edge count per type, read back from the graph."""
    counts: dict[str, int] = {}
    for row in run_query("checks/count_labels", graph=graph):
        labels = row["labels"]
        primary = next((g for g in NODE_GROUPS if g in labels), labels[0])
        counts[primary] = counts.get(primary, 0) + row["n"]
    for row in run_query("checks/count_edges", graph=graph):
        counts[row["type"]] = row["n"]
    return counts


def build_pristine(world: World, graph: str | None = None) -> dict[str, Any]:
    """Drop and rebuild the pristine graph: schema first, then data, then checks."""
    graph = graph or settings.world_graph_pristine
    drop_graph(graph)
    schema = apply_schema(graph)
    receipt = load_world(world, graph)

    counts = graph_counts(graph)
    expected = {k: v for k, v in world.counts().items() if v}
    expected["Meta"] = 1
    if counts != expected:
        diff = {k: (expected.get(k), counts.get(k)) for k in sorted(set(counts) | set(expected))
                if expected.get(k) != counts.get(k)}
        raise RuntimeError(f"graph counts differ from the generated world (expected, got): {diff}")
    dups = run_query("checks/duplicate_ids", graph=graph)
    if dups:
        raise RuntimeError(f"duplicate ids in {graph}: {dups[:5]}")
    return {"graph": graph, "schema": schema, "receipt": receipt, "counts": counts}


def reset_live(pristine: str | None = None, live: str | None = None) -> str:
    """Make `live` a fresh copy of `pristine`."""
    live = live or settings.world_graph_live
    copy_graph(pristine or settings.world_graph_pristine, live)
    return live
