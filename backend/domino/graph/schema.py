"""Indexes, the Place full-text index and the PurchaseOrder.id unique constraint.

Applied once to `world:pristine`. GRAPH.COPY carries all of it to `world:live` and to
sandboxes, so copies never re-apply the schema.
"""

from __future__ import annotations

import time

from domino.graph.client import get_db
from domino.graph.run_query import run_query, run_script

CONSTRAINT_POLL_S = 10.0


def apply_schema(graph: str) -> dict:
    """Create indexes, then the unique constraint, and wait until the constraint is OPERATIONAL."""
    n_statements = run_script("schema/indexes", graph=graph)
    # Not Cypher: a Redis command. It needs the PurchaseOrder.id exact-match index created above.
    get_db().connection.execute_command(
        "GRAPH.CONSTRAINT", "CREATE", graph, "UNIQUE", "NODE", "PurchaseOrder", "PROPERTIES", 1, "id"
    )
    status = wait_constraint_operational(graph)
    return {"index_statements": n_statements, "constraint": status}


def wait_constraint_operational(graph: str, timeout_s: float = CONSTRAINT_POLL_S) -> str:
    t0 = time.perf_counter()
    status = "MISSING"
    while time.perf_counter() - t0 < timeout_s:
        rows = run_query("schema/constraints", graph=graph)
        po = [r for r in rows if r["label"] == "PurchaseOrder" and list(r["properties"]) == ["id"]]
        if po:
            status = po[0]["status"]
            if status == "OPERATIONAL":
                return status
            if status == "FAILED":
                break
        time.sleep(0.05)
    raise RuntimeError(f"PurchaseOrder.id unique constraint on {graph} is {status}, not OPERATIONAL")
