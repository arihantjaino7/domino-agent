"""Delivery: fast-forward the simulated clock until committed purchase orders arrive, and learn from it.
Pure and deterministic; no LLM.

Outcome model (one rule per PO, exact fractions):
  surge     = share of the source edge's approved spare that is now reserved (reserved_wk / spare_wk)
  risk      = (1 - reliability) + max(0, surge - SURGE_FROM)
  days_late = floor(first_arrival_day x risk + jitter),  jitter in [0, 1) from sha256(WORLD_SEED | PO id)
So a reliable company slips a little on long lead times, and any source asked for most of its spare
capacity at once slips more. The same world, seed and plan always give the same outcomes.

Orders: the projection is re-run with every PO's arrival shifted by its days_late, up to the day the last
PO is fully received. An order a PO protected is then 'fulfilled' (ready by its need day),
'fulfilled_late' or 'unfulfilled' (still short on the fast-forward day). Only then is anything "fulfilled".

Learned reliability (memory): each delivery scores max(0, 1 - days_late / LATE_SCALE_DAYS); the seeded
reliability counts as PRIOR_WEIGHT deliveries; learned = their mean, rounded to 2 decimals.
"""

from __future__ import annotations

import hashlib
import json
import math
from fractions import Fraction
from typing import Any

from domino.engines.executor import _locks
from domino.engines.shortage import DEFAULT_HORIZON, fetch_inputs, project
from domino.graph.client import get_db
from domino.graph.run_query import run_query

SURGE_FROM = Fraction(3, 5)   # above 60% of a source's approved spare, a surge order starts to slip
LATE_SCALE_DAYS = 14          # a delivery two weeks late scores 0
PRIOR_WEIGHT = 1              # the seeded reliability counts as one delivery
DEFAULT_RELIABILITY = 0.9     # the allocator's fallback when a site has no operator reliability
MAX_DAY = 120


def _jitter(seed: int, po_id: str) -> Fraction:
    return Fraction(int(hashlib.sha256(f"{seed}|{po_id}".encode()).hexdigest()[:8], 16), 2 ** 32)


def po_outcome(po: dict[str, Any], seed: int) -> dict[str, Any]:
    """days_late for one committed PO (see the module docstring)."""
    reliability = Fraction(str(po["reliability"] if po["reliability"] is not None else DEFAULT_RELIABILITY))
    surge = Fraction(po["reserved_wk"], po["spare_wk"]) if po["spare_wk"] else Fraction(1)
    risk = (1 - reliability) + max(Fraction(0), surge - SURGE_FROM)
    days_late = math.floor(po["first_arrival_day"] * risk + _jitter(seed, po["po_id"]))
    return {"days_late": days_late, "surge_pct": round(float(surge) * 100), "risk": round(float(risk), 3)}


def _received_day(arrival: int, qty: int, rate_wk: int) -> int | None:
    """Day the last unit arrives at `rate_wk` from `arrival` (None if the rate is 0)."""
    if rate_wk <= 0:
        return None
    return arrival - 1 + math.ceil(7 * qty / rate_wk)


def plan_outcomes(graph: str, seed: int) -> dict[str, Any]:
    """Read-only: what fast-forwarding would deliver, without writing anything."""
    pos = run_query("delivery/committed", graph=graph)
    if not pos:
        return {"outcome": "nothing_to_deliver", "pos": [], "orders": []}
    out_pos = []
    for p in pos:
        o = po_outcome(p, seed)
        out_pos.append({**p, **o, "arrived_day": p["first_arrival_day"] + o["days_late"],
                        "status": "delayed" if o["days_late"] > 0 else "received"})
    # The projection at the delivery day, with every PO shifted by its delay.
    inputs = fetch_inputs(graph, DEFAULT_HORIZON)
    by_id = {p["po_id"]: p for p in out_pos}
    ends = []
    for p in inputs["pos"]:
        if p["po_id"] in by_id:
            p["first_arrival_day"] = by_id[p["po_id"]]["arrived_day"]
            end = _received_day(p["first_arrival_day"], p["qty"], p["realized_rate_wk"])
            by_id[p["po_id"]]["received_day"] = end
            ends.append(end if end is not None else MAX_DAY)
    day = min(MAX_DAY, max([DEFAULT_HORIZON, *ends]))
    inputs = {**inputs, "horizon": day, "order_rows": run_query("shortage/orders", {"horizon": day}, graph=graph)}
    proj = project(inputs)
    projected = {o["order_id"]: o for o in proj["orders"]}
    protected = sorted({a["order_id"] for p in inputs["pos"] if p["po_id"] in by_id for a in p["allocations"]})
    orders = []
    for oid in protected:
        o = projected.get(oid)
        if o is None:
            continue
        ready = o["ready_day"]
        status = "unfulfilled" if ready is None else ("fulfilled" if ready <= o["need_day"] else "fulfilled_late")
        orders.append({"id": oid, "status": status, "delivered_day": ready, "need_day": o["need_day"],
                       "late_days": o["late_days"], "customer": o["customer"], "tier": o["tier"]})
    for p in out_pos:
        p.setdefault("received_day", None)
    return {"outcome": "ok", "day": day, "pos": out_pos, "orders": orders}


def fast_forward(graph: str, seed: int) -> dict[str, Any]:
    """Advance the simulated clock to delivery: compute outcomes, then one atomic write, then a receipt."""
    with _locks[graph]:
        version = run_query("decision/get", {"decision_id": ""}, graph=graph)[0]["world_version"]
        res = plan_outcomes(graph, seed)
        if res["outcome"] != "ok":
            return res
        if not res["orders"]:
            return {"outcome": "nothing_to_deliver", "pos": [], "orders": [],
                    "detail": "the committed purchase orders protect no open orders"}
        payload = json.dumps({"pos": {p["po_id"]: p["days_late"] for p in res["pos"]}}, sort_keys=True)
        rows = run_query("delivery/write", {
            "world_version": version, "day": res["day"], "action_id": f"ACT-DELIVER-v{version}",
            "payload_json": payload,
            "pos": [{"id": p["po_id"], "site": p["site"], "plant": p["plant"], "component": p["component"],
                     "status": p["status"], "days_late": p["days_late"], "arrived_day": p["arrived_day"],
                     "received_day": p["received_day"]} for p in res["pos"]],
            "orders": [{"id": o["id"], "status": o["status"], "delivered_day": o["delivered_day"],
                        "late_days": o["late_days"]} for o in res["orders"]]}, ro=False, graph=graph)
    if not rows:
        return {"outcome": "write_matched_nothing", "detail": "the world changed while delivering; try again"}
    r = rows[0]
    late = [p for p in res["pos"] if p["days_late"] > 0]
    counts = {s: sum(o["status"] == s for o in res["orders"]) for s in ("fulfilled", "fulfilled_late", "unfulfilled")}
    return {
        "outcome": "delivered", "day": r["day"], "world_version": r["world_version"],
        "pos": res["pos"], "orders": res["orders"], "counts": counts,
        "receipt_matches": r["pos_updated"] == len(res["pos"]) and r["orders_updated"] == len(res["orders"]),
        "summary": (f"day {r['day']}: {len(res['pos']) - len(late)} of {len(res['pos'])} purchase orders on time; "
                    f"{counts['fulfilled']} orders fulfilled, {counts['fulfilled_late']} fulfilled late, "
                    f"{counts['unfulfilled']} unfulfilled"),
    }


def delivered(graph: str) -> list[dict[str, Any]]:
    """Purchase orders already delivered in this world, with the orders they protected."""
    return [{**r, "orders": [o for o in r["orders"] if o.get("order_id")]}
            for r in run_query("delivery/outcomes", graph=graph)]


# ---------------------------------------------------------------------------
# Learned reliability
# ---------------------------------------------------------------------------

def learned_reliability(prior: float | None, deliveries: list[dict[str, Any]]) -> float:
    """Mean of the prior (weight PRIOR_WEIGHT) and each delivery's score, rounded to 2 decimals."""
    p = Fraction(str(prior if prior is not None else DEFAULT_RELIABILITY))
    scores = [max(Fraction(0), 1 - Fraction(d["days_late"], LATE_SCALE_DAYS)) for d in deliveries]
    value = (PRIOR_WEIGHT * p + sum(scores, Fraction(0))) / (PRIOR_WEIGHT + len(scores))
    return round(float(value), 2)


def explain(site: str, prior: float | None, learned: float, deliveries: list[dict[str, Any]]) -> str:
    """'S-X reliability 0.98 -> 0.71, learned on 2026-10-18 from 2 deliveries: PO-A 9 days late, PO-B 3 days late'.
    Newest facts first, at most three named."""
    seeded = prior if prior is not None else DEFAULT_RELIABILITY
    newest = sorted(deliveries, key=lambda d: (d["learned_on"], d["id"]), reverse=True)
    facts = ", ".join(f"{d['po_id']} {_late(d['days_late'])}" for d in newest[:3])
    more = f" and {len(newest) - 3} more" if len(newest) > 3 else ""
    runs = len({d["run_id"] for d in deliveries})
    n = len(deliveries)
    return (f"{site} reliability {seeded:.2f} -> {learned:.2f}, learned on {newest[0]['learned_on']} from "
            f"{n} deliver{'y' if n == 1 else 'ies'}{f' in {runs} runs' if runs > 1 else ''}: {facts}{more}")


def _late(days: int) -> str:
    return "on time" if days <= 0 else f"{days} day{'s' if days != 1 else ''} late"


def memory_deliveries(memory_graph: str | None, site_ids: list[str] | None = None) -> dict[str, list[dict[str, Any]]]:
    """site -> its delivery facts in `memory_graph` ({} if the graph does not exist yet)."""
    if not memory_graph or memory_graph not in get_db().list_graphs():
        return {}
    out: dict[str, list[dict[str, Any]]] = {}
    for r in run_query("memory/deliveries", {"site_ids": sorted(set(site_ids or []))}, graph=memory_graph):
        out.setdefault(r["site"], []).append(r)
    return out


def learned_for(world_graph: str, memory_graph: str | None, site_ids: list[str] | None = None,
                priors: dict[str, float | None] | None = None) -> list[dict[str, Any]]:
    """Learned reliability for every site (of `site_ids`, or all) that memory has deliveries for.
    The prior is the seeded reliability in `world_graph` unless `priors` gives it."""
    facts = memory_deliveries(memory_graph, site_ids)
    if not facts:
        return []
    if priors is None:
        priors = {r["site"]: r["reliability"] for r in run_query("delivery/priors", {"site_ids": sorted(facts)},
                                                                 graph=world_graph)}
    out = []
    for site in sorted(facts):
        if site not in priors:  # the site is not in this world; nothing to apply it to
            continue
        ds = facts[site]
        value = learned_reliability(priors[site], ds)
        seeded = priors[site] if priors[site] is not None else DEFAULT_RELIABILITY
        out.append({"site": site, "name": ds[0]["name"], "seeded": seeded, "learned": value,
                    "deliveries": len(ds), "on_time": sum(d["days_late"] <= 0 for d in ds),
                    "learned_on": max(d["learned_on"] for d in ds),
                    "evidence": [{"po_id": d["po_id"], "days_late": d["days_late"], "learned_on": d["learned_on"],
                                  "run_id": d["run_id"]} for d in ds],
                    "text": explain(site, priors[site], value, ds)})
    return out
