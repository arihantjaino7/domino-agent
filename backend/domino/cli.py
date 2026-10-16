"""`make cli SCENARIO=monsoon`: declare a scenario's incident on a fresh copy of the world and
print the tier-1 view, the multi-tier exposure with evidence paths, and the shortage projection.

Every number printed comes from an engine. The scenario file only says what happened
(which zone or site, how badly, for how long).
"""

from __future__ import annotations

import argparse
import sys

from domino.config import settings
from domino.engines.exposure import trace_exposure
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
    return 0


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("scenario", nargs="?", default="monsoon", choices=sorted(MOTIFS))
    return run(ap.parse_args().scenario)


if __name__ == "__main__":
    raise SystemExit(main())
