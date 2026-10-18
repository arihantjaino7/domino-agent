"""Shortage projection: exposed vs projected-late. Pure and deterministic; no LLM.

Two parts:
  fetch_inputs(graph)   -> plain dicts pulled with named Cypher queries
  project(inputs)       -> the day-by-day do-nothing simulation (pure Python, exact fractions)

Availability of a site (share of its normal output it can still make):
  - interchangeable sources of the SAME input component: used-weighted share still available;
  - complementary inputs (DIFFERENT components the BOM needs together): the MINIMUM share,
    because plenty of cells can't make up for missing controllers;
  - times the site's own capacity_factor. Computed recursively up the FEEDS DAG.

Timing: a site whose inputs are reduced feels it `input_buffer_days` later; a disrupted site
feels it on day 0 (the incident day). A supply edge delivers the reduced rate to the plant
from onset + transit_days, and the full rate again from restore + transit_days, where restore
is the latest `disrupted_until` among the reduced sources.
"""

from __future__ import annotations

import copy
import math
from dataclasses import dataclass
from fractions import Fraction
from typing import Any

from domino.engines.upstream import load_upstream, realized_rates
from domino.graph.run_query import run_query

DEFAULT_HORIZON = 42


@dataclass(frozen=True)
class Availability:
    fraction: Fraction          # 1 = healthy
    onset: int | None           # first day the site's output is reduced (None if never)
    restore: int | None         # first day it is back to full (None if never within the data)


# ---------------------------------------------------------------------------
# Inputs
# ---------------------------------------------------------------------------

def fetch_inputs(graph: str, horizon: int = DEFAULT_HORIZON) -> dict[str, Any]:
    supply = run_query("shortage/supply_edges", graph=graph)
    feeds = run_query("shortage/upstream_feeds", graph=graph)
    site_ids = sorted({r["site"] for r in supply} | {f["src"] for f in feeds} | {f["dst"] for f in feeds})
    sites = run_query("shortage/sites", {"site_ids": site_ids}, graph=graph)
    # Committed purchase orders arrive at the rate the upstream can really support (joint rationing).
    pos = run_query("upstream/purchase_orders", graph=graph)
    if pos:
        up = load_upstream(graph, [p["site"] for p in pos], [p["component"] for p in pos])
        real = realized_rates(up, [{"id": p["po_id"], "site": p["site"], "component": p["component"],
                                    "rate_wk": p["rate_wk"]} for p in pos])
        alloc: dict[str, list[dict[str, Any]]] = {}
        for a in run_query("upstream/protects", graph=graph):
            alloc.setdefault(a["po_id"], []).append({"order_id": a["order_id"], "qty": a["qty"]})
        for p in pos:
            p["realized_rate_wk"] = real[p["po_id"]]
            p["allocations"] = alloc.get(p["po_id"], [])
    return {
        "horizon": horizon,
        "pos": pos,
        "sites": {s["site"]: s for s in sites},
        "feeds": feeds,
        "supply": supply,
        "stock": run_query("shortage/stock", graph=graph),
        "order_rows": run_query("shortage/orders", {"horizon": horizon}, graph=graph),
    }


def project_shortages(graph: str, horizon: int = DEFAULT_HORIZON) -> dict[str, Any]:
    return project(fetch_inputs(graph, horizon))


# ---------------------------------------------------------------------------
# Availability up the FEEDS DAG
# ---------------------------------------------------------------------------

def site_availability(sites: dict[str, dict[str, Any]], feeds: list[dict[str, Any]]) -> dict[str, Availability]:
    """Availability for every site in `sites`, using the FEEDS rows (src, dst, component, used_wk, cap_wk)."""
    inputs: dict[str, dict[str, list[dict[str, Any]]]] = {}
    for f in feeds:
        inputs.setdefault(f["dst"], {}).setdefault(f["component"], []).append(f)
    memo: dict[str, Availability] = {}

    def own(site_id: str) -> tuple[Fraction, int | None, int | None]:
        s = sites.get(site_id, {})
        factor = Fraction(str(s.get("factor", 1.0) if s.get("factor") is not None else 1.0))
        if factor >= 1:
            return Fraction(1), None, None
        return factor, 0, s.get("disrupted_until")

    def visit(site_id: str, stack: tuple[str, ...]) -> Availability:
        if site_id in memo:
            return memo[site_id]
        if site_id in stack:
            raise ValueError(f"FEEDS cycle through {site_id}")
        factor, onset, restore = own(site_id)
        buffer_days = int(sites.get(site_id, {}).get("input_buffer_days") or 0)
        worst = Fraction(1)
        restores: list[int | None] = [restore] if onset is not None else []
        for comp in sorted(inputs.get(site_id, {})):
            rows = inputs[site_id][comp]
            weights = [r["used_wk"] for r in rows]
            if sum(weights) == 0:  # nothing flowing today: weigh by contracted capacity instead
                weights = [r["cap_wk"] for r in rows]
            total = sum(weights)
            if total == 0:
                continue
            share = Fraction(0)
            for r, w in zip(rows, weights):
                up = visit(r["src"], stack + (site_id,))
                share += Fraction(w) * up.fraction
                if up.fraction < 1 and w > 0:
                    upstream_onset = up.onset + buffer_days if up.onset is not None else None
                    if upstream_onset is not None:
                        onset = upstream_onset if onset is None else min(onset, upstream_onset)
                    restores.append(up.restore)
            worst = min(worst, share / total)  # complementary inputs: the scarcest one binds
        fraction = factor * worst
        if fraction >= 1:
            result = Availability(Fraction(1), None, None)
        else:
            restore_day = None if (not restores or any(r is None for r in restores)) else max(restores)
            result = Availability(fraction, onset if onset is not None else 0, restore_day)
        memo[site_id] = result
        return result

    for sid in sorted(sites):
        visit(sid, ())
    return memo


# ---------------------------------------------------------------------------
# Day-by-day projection
# ---------------------------------------------------------------------------

def _daily_rate(used_wk: int, avail: Availability, transit: int, day: int) -> Fraction:
    if avail.onset is None:
        return Fraction(used_wk, 7)
    start = avail.onset + transit
    end = math.inf if avail.restore is None else avail.restore + transit
    factor = avail.fraction if start <= day < end else Fraction(1)
    return Fraction(used_wk, 7) * factor


def _po_cumulative(po: dict[str, Any], day: int) -> int:
    """Units of a purchase order delivered by the end of `day`, at its realized rate, capped at its qty."""
    days = day - po["first_arrival_day"] + 1
    if days <= 0:
        return 0
    return min(po["qty"], po.get("realized_rate_wk", po["rate_wk"]) * days // 7)


def project(inputs: dict[str, Any]) -> dict[str, Any]:
    # The simulation tracks deliveries on the PO rows, so only those are copied; everything else is read-only.
    inputs = {**inputs, "pos": copy.deepcopy(inputs.get("pos", []))}
    horizon = inputs["horizon"]
    avail = site_availability(inputs["sites"], inputs["feeds"])

    # Supply edges per (plant, component), with their availability.
    edges: dict[tuple[str, str], list[dict[str, Any]]] = {}
    for e in inputs["supply"]:
        edges.setdefault((e["plant"], e["component"]), []).append(
            {**e, "avail": avail.get(e["site"], Availability(Fraction(1), None, None))})

    # Orders: one entry per order with all its component needs.
    orders: dict[str, dict[str, Any]] = {}
    for r in inputs["order_rows"]:
        o = orders.setdefault(r["order_id"], {
            "order_id": r["order_id"], "plant": r["plant"], "product": r["product"], "need_day": r["need_day"],
            "qty": r["qty"], "customer": r["customer"], "tier": r["tier"], "penalty_cents": r["penalty_cents"],
            "value_cents": r["value_cents"], "needs": {}})
        o["needs"][r["component"]] = o["needs"].get(r["component"], 0) + r["units"]

    pos_by_key: dict[tuple[str, str], list[dict[str, Any]]] = {}
    for p in inputs.get("pos", []):
        pos_by_key.setdefault((p["plant"], p["component"]), []).append(p)
    keys = sorted({(o["plant"], k) for o in orders.values() for k in o["needs"]} | set(edges) | set(pos_by_key))
    stock = {k: 0 for k in keys}
    for s in inputs["stock"]:
        if (s["plant"], s["component"]) in stock:
            stock[(s["plant"], s["component"])] = s["on_hand"]

    # An order is exposed when any supply edge for a component it needs runs below full rate.
    reduced = {k for k, es in edges.items() if any(e["avail"].fraction < 1 for e in es)}
    for o in orders.values():
        o["exposed"] = any((o["plant"], k) in reduced for k in o["needs"])
        o["ready_day"] = None

    cum: dict[tuple[str, str], Fraction] = {k: Fraction(0) for k in keys}
    earmark: dict[tuple[str, str], int] = {}  # (order, component) -> PO units delivered for that order
    stockout: dict[tuple[str, str], int] = {}
    curve: dict[tuple[str, str], list[int]] = {k: [] for k in keys}
    queue = sorted(orders.values(), key=lambda o: (o["need_day"], o["tier"] != "strategic", o["order_id"]))

    for day in range(horizon + 1):
        for k in keys:  # arrivals: whole units only, from the exact cumulative inflow
            before = cum[k]
            cum[k] += sum((_daily_rate(e["used_wk"], e["avail"], e["transit_days"], day) for e in edges.get(k, [])),
                          Fraction(0))
            stock[k] += math.floor(cum[k]) - math.floor(before)
            for p in pos_by_key.get(k, []):  # purchase orders: from first arrival, until qty is delivered
                units = _po_cumulative(p, day) - _po_cumulative(p, day - 1)
                for a in p.get("allocations", []):  # PROTECTS units are earmarked for their order first
                    owed = a["qty"] - a.setdefault("delivered", 0)
                    take = min(units, owed)
                    if take > 0:
                        a["delivered"] += take
                        earmark[(a["order_id"], k[1])] = earmark.get((a["order_id"], k[1]), 0) + take
                        units -= take
                stock[k] += units
        for o in queue:  # earliest need day first, strategic first, then id; backlog included
            if o["ready_day"] is not None or o["need_day"] > day:
                continue
            short = [c for c, u in o["needs"].items()
                     if earmark.get((o["order_id"], c), 0) + stock[(o["plant"], c)] < u]
            if short:
                for c in short:
                    stockout.setdefault((o["plant"], c), day)
                continue
            for c, u in o["needs"].items():
                mine = min(u, earmark.get((o["order_id"], c), 0))
                earmark[(o["order_id"], c)] = earmark.get((o["order_id"], c), 0) - mine
                stock[(o["plant"], c)] -= u - mine
            o["ready_day"] = day
        for k in keys:
            curve[k].append(stock[k])

    out_orders = []
    for o in queue:
        beyond = o["ready_day"] is None
        late = (horizon + 1 - o["need_day"]) if beyond else max(0, o["ready_day"] - o["need_day"])
        status = "projected_late" if late > 0 else ("exposed_covered" if o["exposed"] else "on_time")
        out_orders.append({
            "order_id": o["order_id"], "plant": o["plant"], "product": o["product"], "need_day": o["need_day"],
            "qty": o["qty"], "customer": o["customer"], "tier": o["tier"], "exposed": o["exposed"],
            "ready_day": o["ready_day"], "late_days": late, "beyond_horizon": beyond, "status": status,
            "value_cents": o["value_cents"], "penalty_cents": late * o["penalty_cents"],
            "penalty_per_day_cents": o["penalty_cents"], "needs": dict(sorted(o["needs"].items())),
        })

    components = []
    for k in keys:
        unmet = sum(o["needs"].get(k[1], 0) for o in queue if o["plant"] == k[0] and o["ready_day"] is None)
        components.append({"plant": k[0], "component": k[1], "reduced": k in reduced,
                           "stockout_day": stockout.get(k), "unmet_units_at_horizon": unmet,
                           "stock_curve": curve[k]})

    plants = []
    for plant in sorted({o["plant"] for o in out_orders}):
        po = [o for o in out_orders if o["plant"] == plant]
        days = [c["stockout_day"] for c in components if c["plant"] == plant and c["stockout_day"] is not None]
        plants.append({
            "plant": plant, "orders": len(po),
            "exposed": sum(o["exposed"] for o in po),
            "projected_late": sum(o["status"] == "projected_late" for o in po),
            "stockout_day": min(days) if days else None,
        })

    late = [o for o in out_orders if o["status"] == "projected_late"]
    return {
        "horizon": horizon,
        "pos": [{"po_id": p["po_id"], "site": p["site"], "component": p["component"], "plant": p["plant"],
                 "rate_wk": p["rate_wk"], "realized_rate_wk": p.get("realized_rate_wk", p["rate_wk"])}
                for p in inputs.get("pos", [])],
        "orders": out_orders,
        "components": components,
        "plants": plants,
        "sites": {s: {"fraction": str(a.fraction), "onset": a.onset, "restore": a.restore}
                  for s, a in sorted(avail.items()) if a.fraction < 1},
        "totals": {
            "orders": len(out_orders),
            "exposed": sum(o["exposed"] for o in out_orders),
            "exposed_covered": sum(o["status"] == "exposed_covered" for o in out_orders),
            "projected_late": len(late),
            "late_beyond_horizon": sum(o["beyond_horizon"] for o in late),
            "revenue_at_risk_cents": sum(o["value_cents"] for o in late),
            "penalty_exposure_cents": sum(o["penalty_cents"] for o in late),
        },
    }
