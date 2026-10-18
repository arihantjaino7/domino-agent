"""Alternatives. Pure and deterministic; no LLM.

For one (component, plant):
  - acceptable parts come from BOM edges (REQUIRES plus ALLOWS_ALTERNATE {for_component}), per product;
  - candidates are CAN_SUPPLY edges for acceptable parts, plus same-family look-alikes so the BOM
    check can reject them explicitly (the Panel Fire trap);
  - each candidate gets a taint check (disrupted site 1-4 FEEDS hops upstream, path as evidence).
    **Exposure is not rejection**: a candidate is rejected only when its remaining
    clean capacity, from max-flow over its healthy inputs, is 0.
"""

from __future__ import annotations

from typing import Any

from domino.engines.capacity import compute_true_capacity
from domino.graph.run_query import run_query

DEFAULT_HORIZON = 42


def find_alternatives(graph: str, component_id: str, plant_id: str, horizon: int = DEFAULT_HORIZON,
                      run_id: str = "local") -> dict[str, Any]:
    products = run_query("alternatives/acceptable", {"component_id": component_id, "plant_id": plant_id}, graph=graph)
    accepts: dict[str, list[str]] = {}  # acceptable part -> products that accept it
    for p in products:
        for part in [component_id, *p["alternates"]]:
            accepts.setdefault(part, []).append(p["product"])
    lookalikes = [r["component"] for r in run_query("alternatives/lookalikes", {"component_id": component_id},
                                                     graph=graph)]
    candidate_parts = sorted(set(accepts) | set(lookalikes))
    rows = run_query("alternatives/candidates", {"component_ids": candidate_parts, "plant_id": plant_id}, graph=graph)

    # Remaining clean capacity per candidate site, one max-flow network per acceptable part.
    capacity: dict[str, dict[str, Any]] = {}
    for part in sorted({r["component"] for r in rows if r["component"] in accepts}):
        cap = compute_true_capacity(graph, part, plant_id, run_id=run_id)
        capacity[part] = {s["site"]: s for s in cap["sites"]}

    accepted, rejected = [], []
    for r in rows:
        paths = [p for p in r["tainted_paths"] if p]
        base = {"site": r["site"], "component": r["component"], "price_cents": r["price_cents"],
                "spare_wk": r["spare_wk"], "reserved_wk": r["reserved_wk"], "lead_days": r["lead_days"], "transit_days": r["transit_days"],
                "air_transit_days": r["air_transit_days"], "air_surcharge_cents": r["air_surcharge_cents"],
                "moq": r["moq"], "tainted_paths": paths}
        if r["component"] not in accepts:
            rejected.append({**base, "reason": "incompatible",
                             "detail": f"{r['component']} is not approved for "
                                       f"{', '.join(p['product'] for p in products)} (needs {component_id})"})
            continue
        if not r["qualified"]:
            requal = r["requal_days"]
            reason = "requalification_exceeds_horizon" if requal is not None and requal > horizon else "not_qualified"
            rejected.append({**base, "reason": reason, "detail": f"requalification takes {requal} days"})
            continue
        if r["site_status"] == "disrupted":
            rejected.append({**base, "reason": "site_disrupted", "detail": f"{r['site']} is itself disrupted"})
            continue
        site_cap = capacity[r["component"]][r["site"]]
        clean = min(r["spare_wk"] - r["reserved_wk"], site_cap["site_clean_wk"])
        if clean <= 0:
            # Say which limit is at zero: the inputs (all paths through a disrupted site) or the approved spare.
            why = ("every input path runs through a disrupted site" if site_cap["site_clean_wk"] <= 0 else
                   f"its approved spare ({r['spare_wk']}/wk) is already reserved by committed purchase orders")
            rejected.append({**base, "reason": "no_remaining_capacity", "remaining_clean_wk": 0,
                             "nominal_wk": min(r["spare_wk"], site_cap["site_nominal_wk"]), "detail": why})
            continue
        # Extra volume from a site that already holds a contract here shares that site's clean capacity;
        # the joint allocation (M5) decides how it is split.
        contract = site_cap["supply_cap"] - r["spare_wk"] if "SUPPLIES" in site_cap["kinds"] else 0
        accepted.append({**base, "compatible_products": sorted(accepts[r["component"]]),
                         "shares_site_with_contract_wk": contract,
                         "usable_wk": clean, "site_clean_wk": site_cap["site_clean_wk"],
                         "site_nominal_wk": site_cap["site_nominal_wk"],
                         "reduced": site_cap["site_clean_wk"] < site_cap["site_nominal_wk"],
                         "exposure_warning": bool(paths)})

    return {"component": component_id, "plant": plant_id,
            "acceptable_parts": {k: sorted(v) for k, v in sorted(accepts.items())},
            "accepted": accepted, "rejected": rejected}
