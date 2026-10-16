"""Upstream bookkeeping shared by the allocator, the sandbox and the verifier (PLAN §0.1, §7.10, V8).

New purchase orders need input material (cells, panels...) from the source site's feeders. Existing
contracts keep priority: a feeder's room for new orders is `capacity_wk x factor - existing used out`.

One attribution rule is used everywhere, so the allocator, the sandbox and V8 agree:
  a PO at rate r for component k needs r x qty(k -> input) of each input (complementary inputs each
  need their own share). That demand is placed on the source's feeders, healthy feeders first
  (largest FEEDS headroom first, then id), each up to its FEEDS headroom (cap_wk - used_wk).
  Anything left over lands on the first feeder, so an impossible plan shows up as overload.

Joint rationing (sandbox): if the total new demand on a feeder exceeds its room, every PO drawing on
it gets the same proportional share. A PO's realized rate is the minimum over its inputs.
Only one tier of feeders is modelled; deeper tiers are a stated simplification.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any

from domino.graph.run_query import run_query


@dataclass
class Upstream:
    feeds: dict[str, list[dict[str, Any]]] = field(default_factory=dict)    # site -> its FEEDS rows
    feeder: dict[str, dict[str, Any]] = field(default_factory=dict)         # feeder -> capacity/factor/used_out/room
    source: dict[str, dict[str, Any]] = field(default_factory=dict)         # source site -> factor/status/reliability
    ratio: dict[tuple[str, str], int] = field(default_factory=dict)         # (component, input) -> qty

    def room(self, feeder_id: str) -> int:
        return self.feeder[feeder_id]["room"]


def load_upstream(graph: str, site_ids: list[str], component_ids: list[str]) -> Upstream:
    site_ids, component_ids = sorted(set(site_ids)), sorted(set(component_ids))
    up = Upstream()
    for r in run_query("upstream/site_feeders", {"site_ids": site_ids}, graph=graph):
        up.feeds.setdefault(r["site"], []).append(r)
    feeders = sorted({f["src"] for rows in up.feeds.values() for f in rows})
    for r in run_query("upstream/feeder_load", {"site_ids": feeders}, graph=graph):
        factor = 1.0 if r["factor"] is None else r["factor"]
        avail = math.floor(r["capacity_wk"] * factor)
        up.feeder[r["site"]] = {"capacity_wk": r["capacity_wk"], "factor": factor, "used_out": r["used_out"],
                                "available": avail, "room": max(0, avail - r["used_out"])}
    for r in run_query("upstream/sites", {"site_ids": site_ids}, graph=graph):
        up.source[r["site"]] = {"factor": 1.0 if r["factor"] is None else r["factor"], "status": r["status"],
                                "reliability": r["reliability"]}
    for r in run_query("upstream/bom_inputs", {"component_ids": component_ids}, graph=graph):
        up.ratio[(r["component"], r["input"])] = r["qty"]
    return up


def attribute(up: Upstream, site: str, component: str, rate_wk: int) -> dict[str, dict[str, int]]:
    """input component -> {feeder: units/week} needed for `rate_wk` more of `component` at `site`."""
    out: dict[str, dict[str, int]] = {}
    by_input: dict[str, list[dict[str, Any]]] = {}
    for f in up.feeds.get(site, []):
        if (component, f["component"]) in up.ratio:
            by_input.setdefault(f["component"], []).append(f)
    for inp, rows in sorted(by_input.items()):
        need = rate_wk * up.ratio[(component, inp)]
        rows = sorted(rows, key=lambda f: (up.feeder[f["src"]]["factor"] <= 0, -(f["cap_wk"] - f["used_wk"]), f["src"]))
        alloc: dict[str, int] = {}
        for f in rows:
            if need <= 0:
                break
            take = min(need, max(0, f["cap_wk"] - f["used_wk"]))
            if take:
                alloc[f["src"]] = alloc.get(f["src"], 0) + take
                need -= take
        if need > 0 and rows:
            alloc[rows[0]["src"]] = alloc.get(rows[0]["src"], 0) + need
        out[inp] = alloc
    return out


def feeder_demand(up: Upstream, commitments: list[dict[str, Any]]) -> dict[str, int]:
    """Total new demand per feeder from commitments [{site, component, rate_wk}]."""
    total: dict[str, int] = {}
    for c in commitments:
        for alloc in attribute(up, c["site"], c["component"], c["rate_wk"]).values():
            for u, q in alloc.items():
                total[u] = total.get(u, 0) + q
    return total


def overloads(up: Upstream, commitments: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Feeders where existing contracts + new commitments exceed capacity x factor (invariant V8)."""
    rows = []
    for u, q in sorted(feeder_demand(up, commitments).items()):
        f = up.feeder[u]
        if f["used_out"] + q > f["available"]:
            rows.append({"site": u, "existing_wk": f["used_out"], "new_wk": q, "available_wk": f["available"]})
    return rows


def realized_rates(up: Upstream, commitments: list[dict[str, Any]]) -> dict[str, int]:
    """Joint proportional rationing: commitment id -> rate it can actually deliver."""
    demand = feeder_demand(up, commitments)
    share = {u: (min(1.0, up.room(u) / d) if d else 1.0) for u, d in demand.items()}
    out: dict[str, int] = {}
    for c in commitments:
        src = up.source.get(c["site"], {"factor": 1.0})
        rate = c["rate_wk"] if src["factor"] > 0 else 0
        for inp, alloc in attribute(up, c["site"], c["component"], c["rate_wk"]).items():
            granted = sum(math.floor(q * share[u]) for u, q in alloc.items())
            rate = min(rate, granted // up.ratio[(c["component"], inp)])
        out[c["id"]] = rate
    return out
