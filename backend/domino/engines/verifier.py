"""Verifier (PLAN §7.12): nine invariants, each returning the violating rows (expected: none).

V1, V2, V4-V7 are read queries. V3 and V8 are computed here from the graph:
  V3: each committed PO's rate <= the source's remaining clean capacity (max-flow over healthy inputs);
  V8: material balance across the WHOLE plan: for every upstream site, existing contracts plus every
      committed PO's input demand (all components and plants together) <= capacity x factor.
V9: the execution receipt matches the plan's PO and allocation counts.
"""

from __future__ import annotations

from typing import Any

from domino.engines.capacity import compute_true_capacity
from domino.engines.upstream import load_upstream, overloads
from domino.graph.run_query import run_query

NAMES = {
    "V1": "alternate sources within approved spare",
    "V2": "every protected part is BOM-approved for the product",
    "V3": "PO rates within remaining clean capacity (max-flow)",
    "V4": "every allocation arrives by the order's need day",
    "V5": "spend within the decision budget",
    "V6": "one PO per decision, site, part and plant",
    "V7": "protected orders fully covered",
    "V8": "material balance at every upstream site, across the whole plan",
    "V9": "execution receipt matches the plan",
}


def _v3(graph: str, pos: list[dict[str, Any]], run_id: str) -> list[dict[str, Any]]:
    rows = []
    totals: dict[tuple[str, str, str], int] = {}
    for p in pos:
        key = (p["site"], p["component"], p["plant"])
        totals[key] = totals.get(key, 0) + p["rate_wk"]
    caps: dict[tuple[str, str], dict[str, Any]] = {}
    for (site, comp, plant), rate in sorted(totals.items()):
        if (comp, plant) not in caps:
            cap = compute_true_capacity(graph, comp, plant, run_id=run_id)
            caps[(comp, plant)] = {s["site"]: s for s in cap["sites"]}
        clean = caps[(comp, plant)].get(site, {}).get("site_clean_wk", 0)
        if rate > clean:
            rows.append({"site": site, "component": comp, "plant": plant, "committed_wk": rate, "clean_wk": clean})
    return rows


def verify_execution(graph: str, plan: dict[str, Any] | None = None, receipt: dict[str, Any] | None = None,
                     run_id: str = "verify") -> dict[str, Any]:
    pos = run_query("upstream/purchase_orders", graph=graph)
    results: dict[str, list[dict[str, Any]]] = {
        "V1": run_query("verify/v1_spare", graph=graph),
        "V2": run_query("verify/v2_bom", graph=graph),
        "V3": _v3(graph, pos, run_id),
        "V4": run_query("verify/v4_arrival", graph=graph),
        "V5": run_query("verify/v5_budget", graph=graph),
        "V6": run_query("verify/v6_unique", graph=graph),
        "V7": run_query("verify/v7_coverage", graph=graph),
    }
    if pos:
        up = load_upstream(graph, [p["site"] for p in pos], [p["component"] for p in pos])
        results["V8"] = overloads(up, [{"site": p["site"], "component": p["component"], "rate_wk": p["rate_wk"]}
                                       for p in pos])
    else:
        results["V8"] = []
    v9 = []
    if plan is not None and receipt is not None and receipt.get("outcome") == "executed":
        expected = (len(plan["pos"]), sum(len(p["allocations"]) for p in plan["pos"]))
        got = (receipt["pos_created"], receipt["protects_created"])
        if got != expected:
            v9.append({"expected_pos": expected[0], "expected_protects": expected[1],
                       "pos_created": got[0], "protects_created": got[1]})
    results["V9"] = v9
    checks = [{"id": k, "name": NAMES[k], "ok": not rows, "violations": rows} for k, rows in results.items()]
    return {"ok": all(c["ok"] for c in checks), "checks": checks,
            "failed": [c["id"] for c in checks if not c["ok"]]}
