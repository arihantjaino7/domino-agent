"""True capacity with `algo.maxFlow`. Pure and deterministic; no LLM.

1. Extract the upstream network for (component k, plant p) with Cypher (Q-FLOW-EXTRACT).
2. Project it, in units of k per week, into a scratch graph `scratch:flow:<run>:<k>:<p>`:
   - node splitting: every site becomes `<site>:in -> <site>:out` with its own capacity
     floor(capacity_wk x factor / BOM ratio), so a cell fab's output is shared by every line it feeds;
   - FEEDS edges get floor(cap_wk / BOM ratio) (cells -> packs via MADE_FROM.qty);
   - supply edges into the plant get contracted used_wk + approved spare_wk (potential).
3. Run algo.maxFlow from the in-nodes of the most upstream sites to the plant.
4. Min cut from residual reachability on the full network held here in Python (FalkorDB
   returns only edges that carry flow). Check: total cut capacity == max flow.
5. Also: the naive tier-1 sum, and each tier-1 site's standalone capacity (max-flow to its out-node).
6. Drop the scratch graph in `finally`.

Single-commodity: each (component, plant) network is solved on its own. Contention for the same
upstream site across components (Hanriver cells for 4S and 6S) is handled jointly later (M5).
"""

from __future__ import annotations

import math
from collections import deque
from dataclasses import dataclass, field
from typing import Any

from domino.graph.lifecycle import drop_graph
from domino.graph.run_query import run_query

PLANT_NODE = "PLANT"


@dataclass
class FlowNetwork:
    component: str
    plant: str
    edges: dict[tuple[str, str], dict[str, Any]] = field(default_factory=dict)
    sources: list[str] = field(default_factory=list)
    supply_sites: dict[str, dict[str, Any]] = field(default_factory=dict)
    warnings: list[str] = field(default_factory=list)

    @property
    def nodes(self) -> list[str]:
        return sorted({n for e in self.edges for n in e})


# ---------------------------------------------------------------------------
# Build the projected network (pure)
# ---------------------------------------------------------------------------

def _ratios(component: str, rows: list[dict[str, Any]]) -> dict[str, int]:
    ratios = {component: 1}
    for r in rows:
        ratios.setdefault(r["component"], math.prod(r["qtys"]))
    return ratios


def build_network(component: str, plant: str, supply: list[dict[str, Any]], feeds: list[dict[str, Any]],
                  ratio_rows: list[dict[str, Any]]) -> FlowNetwork:
    net = FlowNetwork(component=component, plant=plant)
    ratios = _ratios(component, ratio_rows)

    def add(src: str, dst: str, cap: int, nominal: int, kind: str, **info: Any) -> None:
        e = net.edges.get((src, dst))
        if e:  # merge parallel edges (e.g. two FEEDS of the same pair) so flows map back uniquely
            e["cap"] += cap
            e["cap_nominal"] += nominal
        else:
            net.edges[(src, dst)] = {"cap": cap, "cap_nominal": nominal, "kind": kind, **info}

    # Tier-1 sites: own capacity in units of k, and one potential edge into the plant.
    for r in supply:
        s = net.supply_sites.setdefault(r["site"], {"site": r["site"], "kinds": [], "supply_cap": 0,
                                                    "site_cap": r["site_cap"], "factor": r["factor"],
                                                    "status": r["status"]})
        s["kinds"].append(r["kind"])
        s["supply_cap"] += r["used_wk"] + r["spare_wk"]
    for sid, s in sorted(net.supply_sites.items()):
        factor = 1.0 if s["factor"] is None else s["factor"]
        add(f"{sid}:in", f"{sid}:out", math.floor(s["site_cap"] * factor), s["site_cap"], "site", site=sid)
        add(f"{sid}:out", PLANT_NODE, s["supply_cap"], s["supply_cap"], "supply", site=sid)

    # Upstream sites and FEEDS edges, converted with BOM ratios.
    has_input: dict[str, set[str]] = {}
    upstream_sites: dict[str, tuple[int, float, str]] = {}
    for f in feeds:
        ratio = ratios.get(f["component"])
        if ratio is None:
            net.warnings.append(f"{f['src']}->{f['dst']} feeds {f['component']}, which is not in the BOM of "
                                f"{component}; edge ignored")
            continue
        add(f"{f['src']}:out", f"{f['dst']}:in", f["cap_wk"] // ratio, f["cap_wk"] // ratio, "feeds",
            src_site=f["src"], dst_site=f["dst"], feeds_component=f["component"])
        has_input.setdefault(f["dst"], set()).add(f["component"])
        upstream_sites.setdefault(f["src"], (f["src_cap"], f["src_factor"], f["component"]))
    for sid, (cap, factor, comp) in sorted(upstream_sites.items()):
        if sid in net.supply_sites:
            continue
        factor = 1.0 if factor is None else factor
        add(f"{sid}:in", f"{sid}:out", math.floor(cap * factor / ratios[comp]), cap // ratios[comp], "site", site=sid)

    for sid, comps in sorted(has_input.items()):
        if len(comps) > 1:
            net.warnings.append(f"{sid} needs complementary inputs {sorted(comps)}; max-flow treats them as "
                                "one pool, so its capacity is an upper bound")
    all_sites = sorted(set(net.supply_sites) | set(upstream_sites))
    net.sources = [f"{s}:in" for s in all_sites if s not in has_input]
    return net


def min_cut(net: FlowNetwork, flows: dict[tuple[str, str], int], cap_key: str) -> list[tuple[str, str]]:
    """Edges leaving the set of nodes reachable from the sources in the residual network."""
    adj: dict[str, list[str]] = {}
    for (u, v), e in net.edges.items():
        f = flows.get((u, v), 0)
        if f < e[cap_key]:
            adj.setdefault(u, []).append(v)
        if f > 0:
            adj.setdefault(v, []).append(u)
    seen = set(net.sources)
    todo = deque(sorted(net.sources))
    while todo:
        u = todo.popleft()
        for v in adj.get(u, []):
            if v not in seen:
                seen.add(v)
                todo.append(v)
    return sorted((u, v) for (u, v) in net.edges if u in seen and v not in seen)


def describe_edge(net: FlowNetwork, edge: tuple[str, str], cap_key: str) -> dict[str, Any]:
    e = net.edges[edge]
    if e["kind"] == "site":
        what = f"{e['site']} own capacity"
    elif e["kind"] == "feeds":
        what = f"{e['src_site']} -> {e['dst_site']} {e['feeds_component']} supply line"
    else:
        what = f"{e['site']} -> {net.plant} contract + approved spare"
    return {"from": edge[0], "to": edge[1], "kind": e["kind"], "cap": e[cap_key], "what": what}


# ---------------------------------------------------------------------------
# Run on FalkorDB
# ---------------------------------------------------------------------------

def _load_scratch(net: FlowNetwork, graph: str) -> None:
    rows = [{"id": n} for n in net.nodes]
    if run_query("flow/load_nodes", {"rows": rows}, ro=False, graph=graph)[0]["created"] != len(rows):
        raise RuntimeError("scratch flow nodes not all created")
    erows = [{"src": u, "dst": v, "cap": e["cap"], "cap_nominal": e["cap_nominal"]}
             for (u, v), e in sorted(net.edges.items())]
    if run_query("flow/load_edges", {"rows": erows}, ro=False, graph=graph)[0]["created"] != len(erows):
        raise RuntimeError("scratch flow edges not all created")


def _max_flow(net: FlowNetwork, graph: str, sink: str, cap_key: str) -> tuple[int, dict[tuple[str, str], int]]:
    if not net.sources:
        return 0, {}
    rows = run_query("flow/maxflow", {"source_ids": net.sources, "sink_id": sink, "capacity_property": cap_key},
                     graph=graph)
    if not rows:
        return 0, {}
    flows = {(r["src"], r["dst"]): int(round(r["flow"])) for r in rows}
    return int(round(rows[0]["max_flow"])), flows


def solve(net: FlowNetwork, graph: str, sink: str, cap_key: str) -> dict[str, Any]:
    """Max flow to `sink`, plus the min cut and its correctness check."""
    value, flows = _max_flow(net, graph, sink, cap_key)
    cut = min_cut(net, flows, cap_key) if sink == PLANT_NODE else []
    if sink == PLANT_NODE:
        cut_cap = sum(net.edges[e][cap_key] for e in cut)
        if cut_cap != value:
            raise RuntimeError(f"min cut {cut_cap} != max flow {value} for {net.component}@{net.plant} ({cap_key})")
    return {"max_flow": value, "flows": flows, "cut": [describe_edge(net, e, cap_key) for e in cut]}


def compute_true_capacity(graph: str, component_id: str, plant_id: str, run_id: str = "local") -> dict[str, Any]:
    supply = run_query("flow/supply_edges", {"component_id": component_id, "plant_id": plant_id}, graph=graph)
    feeds = run_query("flow/upstream_feeds", {"component_id": component_id, "plant_id": plant_id}, graph=graph)
    ratios = run_query("flow/bom_ratios", {"component_id": component_id}, graph=graph)
    net = build_network(component_id, plant_id, supply, feeds, ratios)

    scratch = f"scratch:flow:{run_id}:{component_id}:{plant_id}"
    drop_graph(scratch)
    try:
        if net.edges:
            _load_scratch(net, scratch)
            now = solve(net, scratch, PLANT_NODE, "cap")
            nominal = solve(net, scratch, PLANT_NODE, "cap_nominal")
        else:
            now = nominal = {"max_flow": 0, "flows": {}, "cut": []}
        sites = []
        for sid, s in sorted(net.supply_sites.items()):
            clean = solve(net, scratch, f"{sid}:out", "cap")["max_flow"]
            nom = solve(net, scratch, f"{sid}:out", "cap_nominal")["max_flow"]
            sites.append({"site": sid, "kinds": sorted(s["kinds"]), "status": s["status"],
                          "supply_cap": s["supply_cap"],
                          "clean_wk": min(clean, s["supply_cap"]), "nominal_wk": min(nom, s["supply_cap"]),
                          "site_clean_wk": clean, "site_nominal_wk": nom})
    finally:
        drop_graph(scratch)

    return {
        "component": component_id, "plant": plant_id,
        "naive_wk": sum(s["supply_cap"] for s in net.supply_sites.values()),
        "contracted_wk": sum(r["used_wk"] for r in supply),
        "true_wk": now["max_flow"], "nominal_wk": nominal["max_flow"],
        "bottleneck": now["cut"], "nominal_bottleneck": nominal["cut"],
        "sites": sites,
        "network": {"nodes": len(net.nodes), "edges": len(net.edges), "sources": net.sources},
        "warnings": net.warnings,
    }
