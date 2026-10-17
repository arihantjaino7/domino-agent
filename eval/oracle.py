"""Independent JSON-only oracle. No domino imports, query helpers or production algorithms.

NetworkX supplies traversal, topological ordering and maximum-flow. Simulation is an
integer inventory ledger using exact fractions. It implements the documented model,
including its bounded traversal, pipeline timing and one-tier PO rationing assumptions.
This checks implementation agreement, not truth about real supply chains.
"""

from __future__ import annotations

import copy
import gzip
import json
import math
from collections import defaultdict
from fractions import Fraction
from pathlib import Path

import networkx as nx


class World:
    def __init__(self, data: dict):
        self.data = copy.deepcopy(data)
        self.nodes = {r["props"]["id"]: r["props"] for r in self.data["nodes"]}
        self.labels = {r["props"]["id"]: set(r["labels"]) for r in self.data["nodes"]}
        if len(self.nodes) != len(self.data["nodes"]):
            raise ValueError("Export contains duplicate node IDs")
        self.edges = self.data["edges"]
        self.by_type = defaultdict(list)
        for e in self.edges:
            if e["src"] not in self.nodes or e["dst"] not in self.nodes:
                raise ValueError("Export contains dangling edge")
            self.by_type[e["type"]].append(e)
        self.feeds = nx.DiGraph()
        self.feeds.add_nodes_from(n for n, labels in self.labels.items() if "Site" in labels)
        self.feeds.add_edges_from((e["src"], e["dst"]) for e in self.by_type["FEEDS"])
        if not nx.is_directed_acyclic_graph(self.feeds):
            raise ValueError("FEEDS must be a DAG")

    @classmethod
    def read(cls, path: Path) -> World:
        raw = path.read_bytes()
        return cls(json.loads(gzip.decompress(raw) if path.suffix == ".gz" else raw))

    def outgoing(self, rel: str, node: str) -> list[dict]:
        return [e for e in self.by_type[rel] if e["src"] == node]

    def expand(self, entities: list[str]) -> list[str]:
        result = set()
        for entity in entities:
            if entity not in self.nodes:
                raise ValueError(f"unknown_entity: {entity}")
            labels = self.labels[entity]
            if "Site" in labels:
                result.add(entity)
            elif "Region" in labels or "HazardZone" in labels:
                regions = {entity} if "Region" in labels else {
                    e["src"] for e in self.by_type["IN_ZONE"] if e["dst"] == entity}
                result.update(e["src"] for e in self.by_type["LOCATED_IN"]
                              if e["dst"] in regions and "Site" in self.labels[e["src"]])
            else:
                raise ValueError(f"unsupported_entity: {entity}")
        return sorted(result)

    def disrupted(self, entities: list[str], factor: float, duration: int) -> World:
        data = copy.deepcopy(self.data)
        affected = set(self.expand(entities))
        for r in data["nodes"]:
            if r["props"]["id"] in affected:
                r["props"].update(capacity_factor=factor, disrupted_until=duration, status="disrupted")
        return World(data)

    def demand(self, horizon: int, open_only: bool = False) -> list[dict]:
        links = {rel: {e["src"]: e["dst"] for e in self.by_type[rel]}
                 for rel in ("FOR_PRODUCT", "FULFILLED_AT")}
        customer = {e["dst"]: e["src"] for e in self.by_type["PLACED"]}
        result = []
        for oid, labels in self.labels.items():
            o = self.nodes[oid]
            allowed = {"open"} if open_only else {"open", "protected_projected"}
            if "Order" not in labels or o.get("status") not in allowed or o["need_day"] > horizon:
                continue
            prod, plant = links["FOR_PRODUCT"][oid], links["FULFILLED_AT"][oid]
            cu = self.nodes[customer[oid]]
            needs = defaultdict(int)
            for e in self.outgoing("REQUIRES", prod):
                needs[e["dst"]] += o["qty"] * e["props"]["qty"]
            if needs:
                result.append({"id": oid, "plant": plant, "product": prod, "needs": dict(needs),
                               "need_day": o["need_day"], "tier": cu["tier"], "qty": o["qty"],
                               "penalty_per_day": cu["penalty_per_day_cents"], "value_cents": o["value_cents"]})
        return sorted(result, key=lambda o: (o["need_day"], o["tier"] != "strategic", o["id"]))

    def exposure(self, affected: list[str], horizon: int = 42) -> set[str]:
        reachable = set()
        for origin in affected:
            reachable.update(nx.single_source_shortest_path_length(self.feeds, origin, cutoff=4))
        builds = {(e["src"], e["dst"]) for e in self.by_type["BUILDS"]}
        contracts = {(e["dst"], e["props"]["component_id"]) for e in self.by_type["SUPPLIES"]
                     if e["src"] in reachable}
        return {o["id"] for o in self.demand(horizon, open_only=True)
                if (o["plant"], o["product"]) in builds
                and any((o["plant"], k) in contracts for k in o["needs"])}

    def availability(self) -> dict[str, tuple[Fraction, int | None, int | None]]:
        result = {}
        for sid in nx.lexicographical_topological_sort(self.feeds):
            props = self.nodes[sid]
            own = Fraction(str(props.get("capacity_factor", 1)))
            groups = defaultdict(list)
            for e in self.by_type["FEEDS"]:
                if e["dst"] == sid:
                    groups[e["props"]["component_id"]].append(e)
            fractions, onsets, restorations = [Fraction(1)], [], []
            if own < 1:
                onsets.append(0)
                restorations.append(props.get("disrupted_until"))
            for edges in groups.values():
                weights = [e["props"]["used_wk"] for e in edges]
                if not sum(weights):
                    weights = [e["props"]["cap_wk"] for e in edges]
                if not sum(weights):
                    continue
                fractions.append(sum((weight * result[e["src"]][0] for e, weight in zip(edges, weights)),
                                     Fraction(0)) / sum(weights))
                for e, weight in zip(edges, weights):
                    share, onset, end = result[e["src"]]
                    if weight and share < 1:
                        onsets.append((onset or 0) + props.get("input_buffer_days", 0))
                        restorations.append(end)
            fraction = own * min(fractions)
            if fraction >= 1:
                result[sid] = (Fraction(1), None, None)
            else:
                restore = max(restorations) if restorations and None not in restorations else None
                result[sid] = (fraction, min(onsets, default=0), restore)
        return result

    def purchase_orders(self) -> list[dict]:
        result = []
        for pid in sorted(self.nodes):
            p = self.nodes[pid]
            if "PurchaseOrder" not in self.labels[pid] or p.get("status") not in {"committed", "in_transit"}:
                continue
            q = dict(p)
            for rel, key in [("FROM_SITE", "site"), ("FOR_COMPONENT", "component"), ("DELIVERS_TO", "plant")]:
                q[key] = self.outgoing(rel, pid)[0]["dst"]
            q["allocations"] = sorted(self.outgoing("PROTECTS", pid),
                                      key=lambda e: (self.nodes[e["dst"]]["need_day"], e["dst"]))
            result.append(q)
        return result

    def realized_rates(self, pos: list[dict]) -> dict[str, int]:
        # Reconstruct each PO's immediate-input demand from raw edges, then ration
        # shared feeders jointly. Exact fractions avoid dependence on engine floats.
        assigned, total = {}, defaultdict(int)
        ratios = {(e["src"], e["dst"]): e["props"]["qty"] for e in self.by_type["MADE_FROM"]}
        for p in pos:
            groups = defaultdict(list)
            for e in self.by_type["FEEDS"]:
                if e["dst"] == p["site"] and (p["component"], e["props"]["component_id"]) in ratios:
                    groups[e["props"]["component_id"]].append(e)
            assigned[p["id"]] = {}
            for part, edges in groups.items():
                need = p["rate_wk"] * ratios[p["component"], part]
                edges.sort(key=lambda e: (self.nodes[e["src"]].get("capacity_factor", 1) <= 0,
                                         -(e["props"]["cap_wk"] - e["props"]["used_wk"]), e["src"]))
                quantities = defaultdict(int)
                for e in edges:
                    take = min(need, max(0, e["props"]["cap_wk"] - e["props"]["used_wk"]))
                    quantities[e["src"]] += take
                    need -= take
                quantities[edges[0]["src"]] += need
                assigned[p["id"]][part] = dict(quantities)
                for feeder, qty in quantities.items():
                    total[feeder] += qty
        shares = {}
        for feeder, requested in total.items():
            props = self.nodes[feeder]
            capacity = int(Fraction(str(props.get("capacity_factor", 1))) * props["capacity_wk"])
            used = sum(e["props"]["used_wk"] for e in self.outgoing("FEEDS", feeder))
            shares[feeder] = min(Fraction(1), Fraction(max(0, capacity - used), requested)) if requested else Fraction(1)
        rates = {}
        for p in pos:
            options = [p["rate_wk"] if self.nodes[p["site"]].get("capacity_factor", 1) > 0 else 0]
            for part, quantities in assigned[p["id"]].items():
                granted = sum(int(q * shares[f]) for f, q in quantities.items())
                options.append(granted // ratios[p["component"], part])
            rates[p["id"]] = min(options)
        return rates

    def project(self, horizon: int = 42) -> dict:
        orders, health = self.demand(horizon), self.availability()
        stocks = defaultdict(int)
        for e in self.by_type["STOCKS"]:
            stocks[e["src"], e["dst"]] = e["props"]["on_hand"]
        contracts = self.by_type["SUPPLIES"]
        cumulative = defaultdict(Fraction)
        reservations, delivered = defaultdict(int), defaultdict(int)
        pos = self.purchase_orders()
        rates = self.realized_rates(pos)
        ready = {}
        for day in range(horizon + 1):
            new_cumulative = cumulative.copy()
            for e in contracts:
                fraction, onset, restore = health[e["src"]]
                transit = e["props"]["transit_days"]
                reduced = onset is not None and day >= onset + transit and (restore is None or day < restore + transit)
                key = e["dst"], e["props"]["component_id"]
                new_cumulative[key] += Fraction(e["props"]["used_wk"], 7) * (fraction if reduced else 1)
            for key, total in new_cumulative.items():
                stocks[key] += int(total) - int(cumulative[key])
            cumulative = new_cumulative
            for p in pos:
                through_today = min(p["qty"], rates[p["id"]] * max(0, day - p["first_arrival_day"] + 1) // 7)
                before_today = min(p["qty"], rates[p["id"]] * max(0, day - p["first_arrival_day"]) // 7)
                units = through_today - before_today
                for index, edge in enumerate(p["allocations"]):
                    key = p["id"], index
                    take = min(units, edge["props"]["qty"] - delivered[key])
                    delivered[key] += take
                    reservations[edge["dst"], p["component"]] += take
                    units -= take
                stocks[p["plant"], p["component"]] += units
            for order in orders:
                oid = order["id"]
                if oid in ready or day < order["need_day"]:
                    continue
                if any(stocks[order["plant"], c] + reservations[oid, c] < q for c, q in order["needs"].items()):
                    continue
                for c, qty in order["needs"].items():
                    reserved = min(qty, reservations[oid, c])
                    reservations[oid, c] -= reserved
                    stocks[order["plant"], c] -= qty - reserved
                ready[oid] = day
        late_days = {o["id"]: max(0, ready.get(o["id"], horizon + 1) - o["need_day"]) for o in orders}
        return {"ready": {o["id"]: ready.get(o["id"]) for o in orders}, "late_days": late_days,
                "late": {o for o, days in late_days.items() if days}, "rates": rates,
                "penalty_cents": sum(late_days[o["id"]] * o["penalty_per_day"] for o in orders),
                "orders": len(orders)}

    def capacity(self, component: str, plant: str, nominal: bool = False) -> dict:
        contracts = [e for rel in ("SUPPLIES", "CAN_SUPPLY") for e in self.by_type[rel]
                     if e["dst"] == plant and e["props"]["component_id"] == component]
        tier1 = {e["src"] for e in contracts}
        # Find raw upstream edges within the same documented four-hop boundary.
        selected = []
        for e in self.by_type["FEEDS"]:
            if any(e["dst"] == s or (nx.has_path(self.feeds, e["dst"], s)
                                     and nx.shortest_path_length(self.feeds, e["dst"], s) < 4) for s in tier1):
                selected.append(e)
        bom = nx.DiGraph()
        for e in self.by_type["MADE_FROM"]:
            bom.add_edge(e["src"], e["dst"], qty=e["props"]["qty"])
        ratios = {component: 1}
        if component in bom:
            for target in nx.descendants(bom, component):
                paths = list(nx.all_simple_paths(bom, component, target, cutoff=4))
                if paths:
                    values = {math.prod(bom[a][b]['qty'] for a, b in zip(path, path[1:])) for path in paths}
                    if len(values) != 1:
                        raise ValueError("Ambiguous multi-path BOM ratio")
                    ratios[target] = values.pop()
        network = nx.DiGraph()
        inputs, units = set(), {s: 1 for s in tier1}
        def add(a, b, cap):
            network.add_edge(a, b, capacity=cap + network.get_edge_data(a, b, {}).get("capacity", 0))
        for e in contracts:
            add((e["src"], "out"), "sink", e["props"].get("used_wk", 0) + e["props"].get("spare_wk", 0))
        for e in selected:
            part = e["props"]["component_id"]
            if part not in ratios:
                continue
            units.setdefault(e["src"], ratios[part])
            inputs.add(e["dst"])
            add((e["src"], "out"), (e["dst"], "in"), e["props"]["cap_wk"] // ratios[part])
        for site, ratio in units.items():
            props = self.nodes[site]
            factor = Fraction(1) if nominal else Fraction(str(props.get("capacity_factor", 1)))
            add((site, "in"), (site, "out"), int(props["capacity_wk"] * factor / ratio))
        big = 1 + sum(d["capacity"] for _, _, d in network.edges(data=True))
        for site in units.keys() - inputs:
            add("source", (site, "in"), big)
        def solve(target):
            return int(nx.maximum_flow_value(network, "source", target)) if "source" in network and target in network else 0
        return {"true_wk": solve("sink"), "sites": {s: solve((s, "out")) for s in sorted(tier1)}}

    def validate_evidence(self, trace: dict, affected: list[str], horizon: int = 42) -> dict:
        demands = {o["id"]: o for o in self.demand(horizon, open_only=True)}
        valid, invalid = [], []
        for ev in trace["evidence"]:
            path = ev["path"]
            chain = path[:-1]
            ok = bool(chain) and ev["origin"] in affected and chain[0] == ev["origin"]
            ok &= len(chain) - 1 == ev["upstream_hops"] and len(chain) - 1 <= 4
            ok &= all(self.feeds.has_edge(a, b) for a, b in zip(chain, chain[1:]))
            ok &= ev["tier1"] == chain[-1] and path[-1] == ev["plant"]
            ok &= any(e["src"] == chain[-1] and e["dst"] == ev["plant"]
                      and e["props"]["component_id"] == ev["component"] for e in self.by_type["SUPPLIES"])
            ok &= any(e["src"] == ev["plant"] and e["dst"] == ev["product"] for e in self.by_type["BUILDS"])
            ok &= all(o in demands and demands[o]["product"] == ev["product"]
                      and demands[o]["plant"] == ev["plant"] and ev["component"] in demands[o]["needs"]
                      for o in ev["orders"])
            ok &= bool(ev["orders"])
            ok &= ev["value_cents"] == sum(self.nodes[o]["value_cents"] for o in ev["orders"] if o in self.nodes)
            (valid if ok else invalid).append(ev["id"])
        return {"valid": len(valid), "total": len(valid) + len(invalid), "invalid": invalid}
