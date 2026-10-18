"""Exposure trace and shared-dependency explainer. Pure and deterministic; no LLM.

Returns the tier-1 view (what a tier-1-only tool sees) next to the multi-tier view
(variable-depth FEEDS paths), with numbered evidence paths and hop depth per node.
"""

from __future__ import annotations

from typing import Any

from domino.graph.run_query import run_query

DEFAULT_HORIZON = 42


def trace_exposure(graph: str, incident_id: str, horizon: int = DEFAULT_HORIZON) -> dict[str, Any]:
    tier1 = run_query("exposure/tier1_view", {"incident_id": incident_id}, graph=graph)[0]
    rows = run_query("exposure/exposure", {"incident_id": incident_id, "horizon": horizon}, graph=graph)
    shared = run_query("exposure/shared_upstream", {"incident_id": incident_id}, graph=graph)

    evidence: list[dict[str, Any]] = []
    orders: dict[str, set[str]] = {}          # order id -> evidence ids that reach it
    tier1_via: dict[str, set[str]] = {}       # exposed tier-1 site -> affected origins
    hop: dict[str, int] = {}                  # node id -> fewest hops from an affected site

    def note_hop(node: str, depth: int) -> None:
        hop[node] = min(hop.get(node, depth), depth)

    for r in rows:
        eid = f"E{len(evidence) + 1}"
        path = list(r["supply_path"]) + [r["plant"]]
        evidence.append({
            "id": eid, "origin": r["origin"], "path": path, "upstream_hops": r["upstream_hops"],
            "tier1": r["tier1"], "component": r["component"], "product": r["product"], "plant": r["plant"],
            "orders": sorted(r["orders"]), "value_cents": r["value_cents"],
        })
        tier1_via.setdefault(r["tier1"], set()).add(r["origin"])
        for depth, node in enumerate(path):
            note_hop(node, depth)
        for o in r["orders"]:
            note_hop(o, len(path))
            orders.setdefault(o, set()).add(eid)

    plants: dict[str, dict[str, Any]] = {}
    for ev in evidence:
        p = plants.setdefault(ev["plant"], {"plant": ev["plant"], "components": set(), "orders": set()})
        p["components"].add(ev["component"])
        p["orders"] |= set(ev["orders"])

    return {
        "incident_id": incident_id,
        "horizon": horizon,
        "tier1_view": {"directly_affected_tier1": tier1["directly_affected_tier1"], "sites": sorted(tier1["sites"])},
        "multi_tier": {
            "exposed_tier1": len(tier1_via),
            "tier1_sites": [{"site": s, "via": sorted(v)} for s, v in sorted(tier1_via.items())],
            "exposed_orders": len(orders),
            "plants": [{"plant": p["plant"], "components": sorted(p["components"]), "orders": len(p["orders"])}
                       for p in sorted(plants.values(), key=lambda x: x["plant"])],
        },
        "shared_upstream": [{"site": s["shared_upstream"], "operator": s["operator"],
                             "dependents": sorted(s["dependents"]), "fan_out": s["fan_out"]} for s in shared],
        "evidence": evidence,
        "order_evidence": {o: sorted(e, key=lambda x: int(x[1:])) for o, e in sorted(orders.items())},
        "hop_depth": dict(sorted(hop.items())),
    }
