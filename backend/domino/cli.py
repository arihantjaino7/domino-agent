"""`make cli SCENARIO=monsoon`: declare a scenario's incident on a fresh copy of the world and
print the tier-1 view, the multi-tier exposure with evidence paths, and the shortage projection.

Every number printed comes from an engine. The scenario file only says what happened
(which zone or site, how badly, for how long).
"""

from __future__ import annotations

import argparse
import sys

from domino.config import settings
from domino.engines.alternatives import find_alternatives
from domino.engines.capacity import compute_true_capacity
from domino.engines.executor import approve_decision, execute_plan, propose_decision
from domino.engines.exposure import trace_exposure
from domino.engines.sandbox import simulate_strategies
from domino.engines.verifier import verify_execution
from domino.engines.incident import declare_incident
from domino.engines.shortage import project_shortages
from domino.graph.lifecycle import copy_graph
from domino.seed.motifs import MOTIFS

HORIZON = 42


def _usd(cents: int) -> str:
    return f"${cents / 100:,.0f}"


def run(scenario: str) -> int:
    motif = MOTIFS[scenario]
    inc = motif["incident"]
    graph = f"world:cli:{scenario}"
    copy_graph(settings.world_graph_pristine, graph)

    declared = declare_incident(
        graph, incident_id=inc["id"], kind=inc["kind"], title=inc["title"], alert_text=inc["alert_text"],
        entity_ids=[inc["zone_id"]] if "zone_id" in inc else inc["site_ids"],
        capacity_factor=inc["capacity_factor"], duration_days=inc["duration_days"])
    if declared["outcome"] != "ok":
        print(f"✗ incident not declared: {declared}")
        return 1

    exp = trace_exposure(graph, inc["id"], HORIZON)
    short = project_shortages(graph, HORIZON)

    print(f"DOMINO  scenario={scenario}  graph={graph} (fresh GRAPH.COPY of {settings.world_graph_pristine})")
    print(f"{inc['id']}: {inc['title']}")
    print(f"  footprint: {', '.join(declared['site_ids'])}  factor={declared['capacity_factor']}  "
          f"until day {declared['end_day']}  world_version={declared['world_version']}")
    print()

    t1 = exp["tier1_view"]
    print("1. Tier-1 view (what a tier-1-only system sees)")
    print(f"   directly affected tier-1 suppliers: {t1['directly_affected_tier1']}"
          + (f"  ({', '.join(t1['sites'])})" if t1["sites"] else ""))
    print()

    mt = exp["multi_tier"]
    print("2. Multi-tier exposure (FEEDS*0..4)")
    print(f"   exposed tier-1 suppliers: {mt['exposed_tier1']}")
    for s in mt["tier1_sites"]:
        print(f"     {s['site']}  via {', '.join(s['via'])}")
    for s in exp["shared_upstream"]:
        print(f"   shared upstream: {s['site']} ({s['operator']}) feeds {s['fan_out']} tier-1 sites "
              f"(active or alternate): {', '.join(s['dependents'])}")
    print(f"   exposed open orders (need day <= {HORIZON}): {mt['exposed_orders']}")
    print("   evidence:")
    for ev in exp["evidence"]:
        print(f"     {ev['id']}: {' -> '.join(ev['path'])}  [{ev['component']} for {ev['product']}]  "
              f"{len(ev['orders'])} orders, {_usd(ev['value_cents'])}")
    print()

    tot = short["totals"]
    print(f"3. Shortage projection, do nothing, days 0-{HORIZON}")
    print(f"   orders in horizon {tot['orders']}  |  exposed {tot['exposed']}  |  exposed but covered "
          f"{tot['exposed_covered']}  |  projected late {tot['projected_late']} "
          f"({tot['late_beyond_horizon']} still late at day {HORIZON})")
    print(f"   revenue at risk {_usd(tot['revenue_at_risk_cents'])}  |  late penalties (at least) "
          f"{_usd(tot['penalty_exposure_cents'])}")
    print("   per plant:")
    for p in short["plants"]:
        if not p["exposed"]:
            continue
        if p["projected_late"]:
            state = f"PROJECTED LATE, first stockout day {p['stockout_day']}"
        else:
            state = "exposed but covered (stock + pipeline)"
        print(f"     {p['plant']}: {p['exposed']} exposed, {p['projected_late']} late  -> {state}")
    print("   reduced supply:")
    for c in short["components"]:
        if c["reduced"]:
            so = f"stockout day {c['stockout_day']}" if c["stockout_day"] is not None else "no stockout"
            print(f"     {c['plant']} {c['component']}: {so}, unmet at day {HORIZON}: {c['unmet_units_at_horizon']} units")
    late = [o for o in short["orders"] if o["status"] == "projected_late"]
    if late:
        print("   projected-late orders:")
        for o in late:
            when = f"still short at day {HORIZON}" if o["beyond_horizon"] else f"ready day {o['ready_day']}"
            flag = "  STRATEGIC" if o["tier"] == "strategic" else ""
            print(f"     {o['order_id']} {o['plant']} {o['product']} x{o['qty']}  need day {o['need_day']}, "
                  f"{when}, {o['late_days']}d late{flag}")
    print()

    reduced = [(c["component"], c["plant"]) for c in short["components"] if c["reduced"]]
    print("4. True capacity (algo.maxFlow on a scratch graph; min cut from residual reachability)")
    for comp, plant in reduced:
        cap = compute_true_capacity(graph, comp, plant, run_id="cli")
        print(f"   {comp} -> {plant}: naive {cap['naive_wk']}/wk (tier-1 contracts + approved spare)  vs  "
              f"true {cap['true_wk']}/wk  (healthy network {cap['nominal_wk']}/wk)")
        for b in cap["bottleneck"]:
            print(f"     bottleneck: {b['what']} ({b['cap']}/wk)")
        for w in cap["warnings"]:
            print(f"     note: {w}")
    print()

    print("5. Alternatives (exposure is a warning; rejection only when remaining clean capacity is 0)")
    for comp, plant in reduced:
        alts = find_alternatives(graph, comp, plant, HORIZON, run_id="cli")
        print(f"   {comp} -> {plant}:")
        for a in alts["accepted"]:
            notes = []
            if a["exposure_warning"]:
                notes.append("EXPOSED via " + "; ".join(" -> ".join(p) for p in a["tainted_paths"]))
            if a["reduced"]:
                notes.append(f"reduced: site clean {a['site_clean_wk']}/wk of {a['site_nominal_wk']}/wk")
            if a["shares_site_with_contract_wk"]:
                notes.append(f"shares the site with a {a['shares_site_with_contract_wk']}/wk contract")
            print(f"     ACCEPT {a['site']} {a['component']} {_usd(a['price_cents'])}/unit, usable "
                  f"{a['usable_wk']}/wk, lead {a['lead_days']}d + {a['transit_days']}d sea "
                  f"/ {a['air_transit_days']}d air" + (f"  [{'; '.join(notes)}]" if notes else ""))
        for r in alts["rejected"]:
            ev = ("  path: " + "; ".join(" -> ".join(p) for p in r["tainted_paths"])) if r["tainted_paths"] else ""
            print(f"     REJECT {r['site']} {r['component']} {_usd(r['price_cents'])}/unit: {r['reason']} "
                  f"({r['detail']}){ev}")
        if not alts["accepted"] and not alts["rejected"]:
            print("     no approved alternate sources in the graph")
    print()

    sim = simulate_strategies(graph, inc["id"], run_id="cli", horizon=HORIZON)
    print(f"6. Strategies compared in GRAPH.COPY sandboxes (same executor; joint upstream rationing; "
          f"budget {_usd(sim['budget_cents'])})")
    print(f"   {'':3}{'strategy':<17}{'on time':>9}{'late':>6}{'days late':>11}{'penalty':>11}{'spend':>10}"
          f"{'protected':>11}{'prot. but late':>16}{'rate plan/real':>16}  verify")
    for r in sim["strategies"]:
        star = "★" if r["strategy"] == sim["recommended"] else " "
        rate = f"{r['planned_rate_wk']}/{r['realized_rate_wk']}" if r["planned_rate_wk"] else "-"
        ver = "all pass" if r["verification"]["ok"] else "FAIL " + ",".join(r["verification"]["failed"])
        print(f"   {star} {r['strategy']} {r['name']:<14}{r['on_time']:>5}/{r['orders']:<3}{r['late']:>6}"
              f"{r['days_late']:>11}{_usd(r['penalty_cents']):>11}{_usd(r['spend_cents']):>10}"
              f"{r['protected_projected']:>11}{len(r['protected_but_late']):>16}{rate:>16}  {ver}")
    best = next(r for r in sim["strategies"] if r["strategy"] == sim["recommended"])
    print(f"   net benefit ({best['strategy']}): spend {_usd(best['spend_cents'])} -> avoid "
          f"{_usd(best['avoided_penalty_cents'])} in late penalties and protect "
          f"{_usd(best['revenue_protected_cents'])} of revenue -> net {_usd(best['net_benefit_cents'])}")
    base = next((r for r in sim["strategies"] if r["strategy"] == "S1"), None)
    if base and base["protected_but_late"]:
        print(f"   baseline shortfall: it promised {base['protected_projected']} orders, but "
              f"{len(base['protected_but_late'])} are still late once upstream capacity is shared "
              f"({base['planned_rate_wk']}/wk planned, {base['realized_rate_wk']}/wk realized)")
    print()

    plan = sim["plans"].get(sim["recommended"])
    if not plan or not plan["pos"]:
        print("7. Nothing to execute.")
        return 0
    print(f"7. Execute {plan['strategy']} on {graph} (approval: cli, automatic for this check)")
    propose_decision(graph, inc["id"], plan, rationale=plan["name"])
    print(f"   approve: {approve_decision(graph, plan, approved_by='cli')['outcome']}  "
          f"(plan_hash {plan['plan_hash']}, world v{plan['world_version']})")
    receipt = execute_plan(graph, plan)
    print(f"   receipt: {receipt.get('summary', receipt['outcome'])}  "
          f"(matches plan: {receipt.get('receipt_matches_plan')})")
    for p in plan["pos"]:
        print(f"     {p['id']}: {p['site_id']} {p['component_id']} -> {p['plant_id']} {p['rate_wk']}/wk x "
              f"{p['qty']} by {p['mode']}, first arrival day {p['first_arrival_day']}, "
              f"{len(p['allocations'])} orders")
    ver = verify_execution(graph, plan, receipt, run_id="cli")
    for c in ver["checks"]:
        print(f"   {'✓' if c['ok'] else '✗'} {c['id']} {c['name']}" + ("" if c["ok"] else f": {c['violations'][:2]}"))
    again = execute_plan(graph, plan)
    print(f"   execute again: {again['outcome']}, {again.get('pos_created', 0)} new purchase orders")
    after = project_shortages(graph, HORIZON)["totals"]
    print(f"   after execution: {after['orders'] - after['projected_late']}/{after['orders']} orders on time "
          f"(protected = projected; POs committed, parts not yet received)")
    return 0


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("scenario", nargs="?", default="monsoon", choices=sorted(MOTIFS))
    return run(ap.parse_args().scenario)


if __name__ == "__main__":
    raise SystemExit(main())
