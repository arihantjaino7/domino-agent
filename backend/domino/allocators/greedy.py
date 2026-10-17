"""Graph-aware greedy allocator (PLAN §0.1). Pure and deterministic; no LLM.

    for order in late orders, sorted by (need_day, not strategic, id):
        for each part the order is short of:
            for source in feasible sources, ranked by the preset:
                room = what the source can deliver by need_day at its remaining rate
                graph-aware: also capped by upstream bookkeeping (feeder room after existing contracts)
                take = min(need, room, budget left)

An order is protected only if every part it is short of is fully covered; otherwise its tentative
allocations are rolled back, so "protected (projected)" never means half-covered (invariant V7).

Naive and graph-aware modes run this same code; only the candidate list and the capacity checks
differ. That keeps the baseline-vs-DOMINO comparison fair. Greedy is not guaranteed optimal.
"""

from __future__ import annotations

import hashlib
import json
import math
from typing import Any

from domino.allocators.strategies import DEFAULT_BUDGET_CENTS, PRESETS
from domino.engines.alternatives import find_alternatives
from domino.engines.shortage import project_shortages
from domino.engines.upstream import Upstream, load_upstream, overloads

Key = tuple[str, str, str]  # (site, component, plant)


# ---------------------------------------------------------------------------
# Problem (read from the graph)
# ---------------------------------------------------------------------------

def build_problem(graph: str, horizon: int = 42, budget_cents: int = DEFAULT_BUDGET_CENTS,
                  run_id: str = "local") -> dict[str, Any]:
    baseline = project_shortages(graph, horizon)
    reduced = {(c["plant"], c["component"]) for c in baseline["components"] if c["reduced"]}
    orders = []
    for o in baseline["orders"]:
        if o["status"] != "projected_late":
            continue
        needs = {k: u for k, u in o["needs"].items() if (o["plant"], k) in reduced}
        if needs:
            orders.append({"order_id": o["order_id"], "plant": o["plant"], "need_day": o["need_day"],
                           "tier": o["tier"], "needs": needs})
    candidates: dict[str, list[dict[str, Any]]] = {}
    for plant, comp in sorted({(o["plant"], k) for o in orders for k in o["needs"]}):
        alts = find_alternatives(graph, comp, plant, horizon, run_id=run_id)
        rows = [{**a, "naive_only": False} for a in alts["accepted"]]
        # The naive tool still sees sources the graph rejects for capacity: it has no upstream view.
        rows += [{**r, "naive_only": True, "usable_wk": 0} for r in alts["rejected"]
                 if r["reason"] == "no_remaining_capacity"]
        candidates[f"{comp}|{plant}"] = sorted(rows, key=lambda r: r["site"])
    sites = sorted({c["site"] for rows in candidates.values() for c in rows})
    comps = sorted({c["component"] for rows in candidates.values() for c in rows})
    return {"graph": graph, "horizon": horizon, "budget_cents": budget_cents, "baseline": baseline,
            "orders": orders, "candidates": candidates, "upstream": load_upstream(graph, sites, comps)}


# ---------------------------------------------------------------------------
# Allocation (pure)
# ---------------------------------------------------------------------------

def rate_needed(allocs: list[tuple[int, int]], arrival: int) -> int:
    """Smallest weekly rate that delivers each cumulative allocation by its need day.

    allocs = [(need_day, qty)]; a PO at rate r has delivered r x (t - arrival + 1) / 7 by day t.
    """
    rate, cum = 0, 0
    for need_day, qty in sorted(allocs):
        cum += qty
        rate = max(rate, math.ceil(7 * cum / (need_day - arrival + 1)))
    return rate


def _arrival(c: dict[str, Any], mode: str) -> int:
    return c["lead_days"] + (c["air_transit_days"] if mode == "air" else c["transit_days"])


def _unit_cost(c: dict[str, Any], mode: str) -> int:
    return c["price_cents"] + (c["air_surcharge_cents"] if mode == "air" else 0)


def _pick_mode(c: dict[str, Any], need_day: int, air: str) -> str | None:
    sea_ok = _arrival(c, "sea") <= need_day
    air_ok = c.get("air_transit_days") is not None and _arrival(c, "air") <= need_day
    if air == "always":
        return "air" if air_ok else ("sea" if sea_ok else None)
    if sea_ok:
        return "sea"
    return "air" if air == "when_needed" and air_ok else None


def _rank(c: dict[str, Any], mode: str, key: str, up: Upstream) -> tuple:
    cost = _unit_cost(c, mode)
    if key == "speed":
        return (_arrival(c, mode), cost, c["site"])
    if key == "balanced":
        reliability = up.source.get(c["site"], {}).get("reliability") or 0.9
        score = cost * (2 - reliability) * (1.1 if c["tainted_paths"] else 1.0)
        return (round(score), _arrival(c, mode), c["site"])
    return (cost, c["site"])


def allocate(problem: dict[str, Any], strategy: str, decision_id: str, world_version: int) -> dict[str, Any]:
    preset = PRESETS[strategy]
    mode = preset["mode"]
    up: Upstream = problem["upstream"]
    budget = problem["budget_cents"]
    allocs: dict[Key, list[tuple[int, int, str]]] = {}      # key -> [(need_day, qty, order_id)]
    src_mode: dict[Key, str] = {}
    cand_of: dict[Key, dict[str, Any]] = {}
    spend = 0
    protected: list[str] = []

    def rate_of(key: Key, extra: tuple[int, int] | None = None) -> int:
        rows = [(d, q) for d, q, _ in allocs.get(key, [])] + ([extra] if extra else [])
        return rate_needed(rows, _arrival(cand_of[key], src_mode[key])) if rows else 0

    def commitments(override: tuple[Key, int] | None = None) -> list[dict[str, Any]]:
        out = []
        for key in sorted(set(allocs) | ({override[0]} if override else set())):
            rate = override[1] if override and key == override[0] else rate_of(key)
            if rate:
                out.append({"site": key[0], "component": key[1], "rate_wk": rate})
        return out

    def fits(key: Key, c: dict[str, Any], need_day: int, qty: int) -> bool:
        rate = rate_of(key, (need_day, qty))
        cap = c["spare_wk"] - c.get("reserved_wk", 0)
        if mode == "graph":
            cap = min(cap, c["usable_wk"])
        if rate > cap:
            return False
        return mode != "graph" or not overloads(up, commitments((key, rate)))

    if mode is not None:
        for o in sorted(problem["orders"], key=lambda o: (o["need_day"], o["tier"] != "strategic", o["order_id"])):
            tentative: list[tuple[Key, int]] = []
            new_modes: list[Key] = []
            cost = 0
            covered = True
            for comp, need in sorted(o["needs"].items()):
                cands = problem["candidates"].get(f"{comp}|{o['plant']}", [])
                if mode == "graph":
                    cands = [c for c in cands if not c["naive_only"]]
                options = []
                for c in cands:
                    key = (c["site"], c["component"], o["plant"])
                    m = src_mode.get(key) or _pick_mode(c, o["need_day"], preset["air"])
                    if m and _arrival(c, m) <= o["need_day"]:
                        options.append((_rank(c, m, preset["key"], up), key, c, m))
                for _, key, c, m in sorted(options, key=lambda x: x[0]):
                    if need <= 0:
                        break
                    cand_of[key] = c
                    if key not in src_mode:
                        src_mode[key] = m
                        new_modes.append(key)
                    unit = _unit_cost(c, src_mode[key])
                    hi = min(need, max(0, (budget - spend - cost) // unit))
                    lo = 0
                    while lo < hi:  # largest qty that still fits (all checks are monotone in qty)
                        mid = (lo + hi + 1) // 2
                        if fits(key, c, o["need_day"], mid):
                            lo = mid
                        else:
                            hi = mid - 1
                    if lo > 0:
                        allocs.setdefault(key, []).append((o["need_day"], lo, o["order_id"]))
                        tentative.append((key, lo))
                        cost += lo * unit
                        need -= lo
                if need > 0:
                    covered = False
                    break
            if covered:
                spend += cost
                protected.append(o["order_id"])
            else:  # roll back: never protect an order halfway
                for key, qty in tentative:
                    allocs[key].remove(next(a for a in allocs[key] if a[2] == o["order_id"] and a[1] == qty))
                    if not allocs[key]:
                        del allocs[key]
                for key in new_modes:
                    if key not in allocs:
                        src_mode.pop(key, None)

    pos = _build_pos(allocs, src_mode, cand_of, decision_id, problem["budget_cents"], spend)
    plan = {"strategy": strategy, "name": preset["name"], "decision_id": decision_id,
            "world_version": world_version, "budget_cents": problem["budget_cents"], "pos": pos}
    plan["spend_cents"] = sum(p["qty"] * p["unit_price_cents"] for p in pos)
    plan["protected_orders"] = sorted({a["order_id"] for p in pos for a in p["allocations"]})
    plan["plan_hash"] = plan_hash(plan)
    return plan


def _build_pos(allocs, src_mode, cand_of, decision_id, budget, spend) -> list[dict[str, Any]]:
    pos = []
    for key in sorted(allocs):
        site, comp, plant = key
        c, m = cand_of[key], src_mode[key]
        arrival = _arrival(c, m)
        qty = sum(q for _, q, _ in allocs[key])
        rate = rate_needed([(d, q) for d, q, _ in allocs[key]], arrival)
        unit = _unit_cost(c, m)
        if qty < c["moq"]:  # minimum order quantity: pad if the budget allows (extra units are buffer)
            pad = c["moq"] - qty
            if spend + pad * unit <= budget:
                spend += pad * unit
                qty = c["moq"]
        pos.append({
            "id": po_id(decision_id, site, comp, plant), "site_id": site, "component_id": comp, "plant_id": plant,
            "rate_wk": rate, "qty": qty, "mode": m, "first_arrival_day": arrival, "unit_price_cents": unit,
            "allocations": [{"order_id": o, "qty": q, "arrival_day": arrival}
                            for d, q, o in sorted(allocs[key], key=lambda a: (a[0], a[2]))],
        })
    return pos


def po_id(decision_id: str, site: str, component: str, plant: str) -> str:
    """Deterministic id: the same decision, site, part and plant always give the same PO id."""
    return "PO-" + hashlib.sha256(f"{decision_id}|{site}|{component}|{plant}".encode()).hexdigest()[:10].upper()


def plan_hash(plan: dict[str, Any]) -> str:
    core = {k: plan[k] for k in ("strategy", "decision_id", "world_version", "budget_cents", "pos")}
    return hashlib.sha256(json.dumps(core, sort_keys=True, separators=(",", ":")).encode()).hexdigest()[:16]


def content_hash(plan: dict[str, Any]) -> str:
    """What the plan buys, without its ids: the same purchases under a new decision id hash the same."""
    pos = [{k: v for k, v in p.items() if k != "id"} for p in plan["pos"]]
    core = {"strategy": plan["strategy"], "world_version": plan["world_version"], "pos": pos}
    return hashlib.sha256(json.dumps(core, sort_keys=True, separators=(",", ":")).encode()).hexdigest()[:16]


def rekey(plan: dict[str, Any], decision_id: str) -> dict[str, Any]:
    """The same plan under another decision id (a revision after a rejection): new PO ids and plan_hash."""
    out = {**plan, "decision_id": decision_id,
           "pos": [{**p, "id": po_id(decision_id, p["site_id"], p["component_id"], p["plant_id"])} for p in plan["pos"]]}
    out["plan_hash"] = plan_hash(out)
    return out
