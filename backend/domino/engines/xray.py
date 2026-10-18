"""Risk X-ray: a proactive single-point-of-failure scan. Pure and deterministic; no LLM.

For every site that feeds another site or holds a contract with a plant (tier 1 included), ask: what if this
one site stopped completely (capacity 0) for `duration_days`? Two passes:

1. Fast pass, in memory: fetch the projection inputs ONCE (`shortage.fetch_inputs`), then for each site set its
   capacity_factor to 0 until day `duration_days` and run `shortage.project` on the modified inputs, restricted to
   the stock pools the outage can reach (`coupled`). A site whose outage reduces no supply edge gives the baseline
   result and is not projected at all.
2. Confirm pass, for the top `confirm_top` sites and the worst hidden one: the real path on a `GRAPH.COPY`
   sandbox. Declare the outage there with `declare_incident`, project from the sandbox graph (committed purchase
   orders re-rationed against the reduced upstream), and run `compute_true_capacity` (`algo.maxFlow`) for the
   worst-hit part and plant to measure the capacity drop. The sandbox is dropped in `finally`; the live graph is
   only read.

Every count is the damage this one outage ADDS to the current world (a world that already has a disruption keeps
it in the baseline). Ranking: orders newly projected late, then added late penalties, then orders newly exposed.
A site is a single point of failure when its outage alone makes at least one order late; it is hidden when
Kestrel holds no direct contract with it (no SUPPLIES or CAN_SUPPLY edge to a plant).

Results are cached per graph, content of the scanned inputs, duration, horizon and confirm_top.
"""

from __future__ import annotations

import hashlib
import json
import threading
import time
from typing import Any

from domino.engines.capacity import compute_true_capacity
from domino.engines.incident import declare_incident
from domino.engines.sandbox import world_version
from domino.engines.shortage import DEFAULT_HORIZON, fetch_inputs, project, project_shortages, site_availability
from domino.graph.lifecycle import copy_graph, drop_graph
from domino.graph.run_query import run_query

DEFAULT_DURATION = 21  # the same length as the war room's manual stop, so a rehearsal reproduces the scan
DEFAULT_CONFIRM_TOP = 3
SCOPE = "every site that feeds another site or holds a contract with a plant, tier 1 included"

_cache: dict[tuple[Any, ...], dict[str, Any]] = {}
_lock = threading.Lock()  # one scan at a time: sandbox and scratch graph names are fixed per site


def outage_inputs(inputs: dict[str, Any], site: str, duration_days: int) -> dict[str, Any]:
    """A shallow copy of the projection inputs with `site` at capacity 0 from day 0 until `duration_days`."""
    s = dict(inputs["sites"][site])
    until = s.get("disrupted_until") if (s.get("factor") is not None and s["factor"] < 1) else None
    s.update(factor=0.0, status="disrupted", disrupted_until=max(duration_days, until or 0))
    return {**inputs, "sites": {**inputs["sites"], site: s}}


def _late(proj: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {o["order_id"]: o for o in proj["orders"] if o["status"] == "projected_late"}


def damage(base: dict[str, Any], scen: dict[str, Any], supply_sites: set[str]) -> dict[str, Any]:
    """What the scenario projection adds to the baseline projection."""
    late_b, late_s = _late(base), _late(scen)
    exp_b = {o["order_id"] for o in base["orders"] if o["exposed"]}
    exp_s = {o["order_id"] for o in scen["orders"] if o["exposed"]}
    new_late = sorted(set(late_s) - set(late_b))
    comps_b = {(c["plant"], c["component"]): c for c in base["components"]}
    hit = [c for c in scen["components"]
           if c["reduced"] and (not comps_b.get((c["plant"], c["component"]), {}).get("reduced")
                                or c["stockout_day"] != comps_b[(c["plant"], c["component"])]["stockout_day"])]
    stockouts = [c["stockout_day"] for c in hit if c["stockout_day"] is not None]
    tier1 = sorted(s for s, a in scen["sites"].items()
                   if s in supply_sites and base["sites"].get(s, {}).get("fraction") != a["fraction"])
    return {
        "orders_exposed": len(exp_s - exp_b),
        "orders_late": len(new_late),
        "late_order_ids": new_late,
        "strategic_late": sum(late_s[o]["tier"] == "strategic" for o in new_late),
        "penalty_cents": scen["totals"]["penalty_exposure_cents"] - base["totals"]["penalty_exposure_cents"],
        "revenue_at_risk_cents": scen["totals"]["revenue_at_risk_cents"] - base["totals"]["revenue_at_risk_cents"],
        "tier1_hit": tier1,
        "plants_hit": sorted({c["plant"] for c in hit}),
        "parts_hit": [{"plant": c["plant"], "component": c["component"], "stockout_day": c["stockout_day"],
                       "unmet_units_at_horizon": c["unmet_units_at_horizon"]}
                      for c in sorted(hit, key=lambda c: (c["stockout_day"] is None, c["stockout_day"] or 0,
                                                          c["plant"], c["component"]))],
        "first_stockout_day": min(stockouts) if stockouts else None,
    }


NO_DAMAGE = {"orders_exposed": 0, "orders_late": 0, "late_order_ids": [], "strategic_late": 0, "penalty_cents": 0,
             "revenue_at_risk_cents": 0, "tier1_hit": [], "plants_hit": [], "parts_hit": [], "first_stockout_day": None}


def rank_key(row: dict[str, Any]) -> tuple[Any, ...]:
    return (-row["orders_late"], -row["penalty_cents"], -row["orders_exposed"], -len(row["tier1_hit"]), row["site"])


def coupled(inputs: dict[str, Any], keys: set[tuple[str, str]]) -> dict[str, Any]:
    """The projection inputs restricted to the (plant, component) pools coupled to `keys`.

    Orders only draw on the stock pools of their own plant and parts, so an outage that reduces the pools in
    `keys` can only change orders needing one of them, and through those orders' other parts, the pools they
    share. This closure is projected on its own; every order outside it projects exactly as in the baseline.
    """
    needs: dict[str, set[tuple[str, str]]] = {}
    for r in inputs["order_rows"]:
        needs.setdefault(r["order_id"], set()).add((r["plant"], r["component"]))
    keys, orders = set(keys), set()
    while True:
        more = {o for o, ks in needs.items() if o not in orders and ks & keys}
        if not more:
            break
        orders |= more
        for o in more:
            keys |= needs[o]
    return {**inputs,
            "supply": [e for e in inputs["supply"] if (e["plant"], e["component"]) in keys],
            "stock": [r for r in inputs["stock"] if (r["plant"], r["component"]) in keys],
            "pos": [p for p in inputs.get("pos", []) if (p["plant"], p["component"]) in keys],
            "order_rows": [r for r in inputs["order_rows"] if r["order_id"] in orders]}


def fast_pass(inputs: dict[str, Any], candidates: list[str],
              duration_days: int) -> tuple[dict[str, Any], dict[str, dict[str, Any]], int]:
    """Baseline projection plus the added damage of each candidate's full outage, all in memory."""
    base = project(inputs)
    supply_sites = {e["site"] for e in inputs["supply"]}
    base_avail = site_availability(inputs["sites"], inputs["feeds"])
    base_sub: dict[frozenset[tuple[str, str]], dict[str, Any]] = {}
    out: dict[str, dict[str, Any]] = {}
    projected = 0
    for site in candidates:
        if site not in inputs["sites"]:  # feeds only backup lines: nothing flows from it today
            out[site] = dict(NO_DAMAGE)
            continue
        mod = outage_inputs(inputs, site, duration_days)
        avail = site_availability(mod["sites"], mod["feeds"])
        keys = frozenset((e["plant"], e["component"]) for e in inputs["supply"]
                         if avail[e["site"]] != base_avail[e["site"]])
        if not keys:
            out[site] = dict(NO_DAMAGE)  # no supply edge into a plant changes, so the projection cannot change
            continue
        if keys not in base_sub:
            base_sub[keys] = project(coupled(inputs, keys))
        out[site] = damage(base_sub[keys], project(coupled(mod, keys)), supply_sites)
        projected += 1
    return base, out, projected


def _paths(graph: str, site_ids: list[str]) -> dict[str, list[dict[str, Any]]]:
    out: dict[str, list[dict[str, Any]]] = {}
    for r in run_query("xray/paths", {"site_ids": site_ids}, graph=graph):
        out.setdefault(r["origin"], []).append({
            "path": list(r["path"]), "tier1": r["tier1"], "plant": r["plant"],
            "component": r["component"], "active": r["contract"] == "SUPPLIES"})
    return out


def confirm(live: str, site: str, duration_days: int, horizon: int, base: dict[str, Any],
            supply_sites: set[str], parts: list[dict[str, Any]]) -> dict[str, Any]:
    """Replay one outage on a GRAPH.COPY sandbox with the real incident and projection code, plus max-flow."""
    fork = f"sandbox:xray:{live}:{site}"
    t0 = time.monotonic()
    copy_graph(live, fork)
    try:
        res = declare_incident(fork, incident_id="INC-XRAY", kind="outage", title=f"X-ray: {site} stops",
                               alert_text="Risk X-ray rehearsal in a sandbox", entity_ids=[site],
                               capacity_factor=0.0, duration_days=duration_days)
        if res["outcome"] != "ok":
            raise RuntimeError(f"X-ray sandbox could not declare the outage of {site}: {res}")
        dmg = damage(base, project_shortages(fork, horizon), supply_sites)
        capacity = []
        for p in parts[:1]:  # the worst-hit part and plant (earliest stockout)
            cap = compute_true_capacity(fork, p["component"], p["plant"], run_id=f"xray-{site}")
            capacity.append({"component": p["component"], "plant": p["plant"], "healthy_wk": cap["nominal_wk"],
                             "during_outage_wk": cap["true_wk"], "drop_wk": cap["nominal_wk"] - cap["true_wk"],
                             "bottleneck": [b["what"] + f" ({b['cap']}/wk)" for b in cap["bottleneck"]]})
    finally:
        drop_graph(fork)
    return {"method": "GRAPH.COPY sandbox + declare_incident + project_shortages + algo.maxFlow",
            "damage": dmg, "capacity": capacity, "ms": round((time.monotonic() - t0) * 1000)}


def scan(live: str, duration_days: int = DEFAULT_DURATION, horizon: int = DEFAULT_HORIZON,
         confirm_top: int = DEFAULT_CONFIRM_TOP) -> dict[str, Any]:
    """Rank every upstream site by the damage its full outage would add. Cached while the inputs are unchanged."""
    with _lock:
        t0 = time.monotonic()
        version = world_version(live)
        sites = run_query("xray/sites", graph=live)
        inputs = fetch_inputs(live, horizon)
        t_fetch = time.monotonic()
        # world_version restarts after a reset, so the key is the content the scan depends on, not the version.
        digest = hashlib.sha256(json.dumps([sites, inputs], sort_keys=True, default=str).encode()).hexdigest()
        key = (live, digest, duration_days, horizon, confirm_top)
        if key in _cache:
            return {**_cache[key], "world_version": version, "cached": True}
        candidates = [s["site"] for s in sites]
        base, dmg, projected = fast_pass(inputs, candidates, duration_days)
        t_fast = time.monotonic()
        paths = _paths(live, candidates)
        contract_ops = {s["operator_id"] for s in sites if s["direct_contract"]}

        rows = []
        for s in sites:
            d = dmg[s["site"]]
            ps = paths.get(s["site"], [])
            rows.append({
                "site": s["site"], "name": s["name"], "tier": s["tier"], "kind": s["kind"], "status": s["status"],
                "operator_id": s["operator_id"], "operator": s["operator"], "region": s["region"],
                "region_name": s["region_name"], "country": s["country"],
                "direct_contract": s["direct_contract"], "hidden": not s["direct_contract"],
                "operator_has_contract": s["operator_id"] in contract_ops,
                "single_point_of_failure": d["orders_late"] > 0,
                **d,
                "dependents": {"tier1_active": sorted({p["tier1"] for p in ps if p["active"]}),
                               "tier1_backup": sorted({p["tier1"] for p in ps if not p["active"]}),
                               "plants": sorted({p["plant"] for p in ps if p["active"]})},
                "paths": ps, "confirmed": None,
            })
        rows.sort(key=rank_key)
        for i, r in enumerate(rows):
            r["rank"] = i + 1

        supply_sites = {e["site"] for e in inputs["supply"]}
        spofs = [r for r in rows if r["single_point_of_failure"]]
        to_confirm = spofs[:confirm_top]
        worst_hidden = next((r for r in spofs if r["hidden"]), None)
        if confirm_top and worst_hidden is not None and worst_hidden not in to_confirm:
            to_confirm.append(worst_hidden)
        for r in to_confirm:
            c = confirm(live, r["site"], duration_days, horizon, base, supply_sites, r["parts_hit"])
            same = all(c["damage"][k] == r[k] for k in ("orders_late", "orders_exposed", "penalty_cents"))
            r["confirmed"] = {**c, "matches_fast_pass": same}
            if not same:  # the sandbox re-rations committed purchase orders, so it is the authority
                r.update({k: v for k, v in c["damage"].items()})
                r["single_point_of_failure"] = r["orders_late"] > 0
        rows.sort(key=rank_key)
        for i, r in enumerate(rows):
            r["rank"] = i + 1
        t_end = time.monotonic()

        spof = [r for r in rows if r["single_point_of_failure"]]
        result = {
            "graph": live, "world_version": version, "duration_days": duration_days, "horizon": horizon,
            "capacity_factor": 0.0, "scope": SCOPE,
            "baseline": {k: base["totals"][k] for k in ("orders", "exposed", "projected_late",
                                                       "penalty_exposure_cents", "revenue_at_risk_cents")},
            "scanned": len(rows), "projected": projected,
            "single_points_of_failure": len(spof), "hidden_single_points_of_failure": sum(r["hidden"] for r in spof),
            "confirmed": [r["site"] for r in rows if r["confirmed"]],
            "sites": rows,
            "timing_ms": {"fetch": round((t_fetch - t0) * 1000), "fast_pass": round((t_fast - t_fetch) * 1000),
                          "confirm": round((t_end - t_fast) * 1000), "total": round((t_end - t0) * 1000)},
            "cached": False,
        }
        _cache.clear()  # only the current world matters
        _cache[key] = result
        return result
