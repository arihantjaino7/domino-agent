"""World endpoints for the war-room canvas (PLAN §10): graph, summary, places, manual incident injection.

Every number returned comes from a named query or an engine (CLAUDE.md rule 8).
"""

from __future__ import annotations

import asyncio
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from domino.config import settings
from domino.engines.incident import declare_incident
from domino.engines.shortage import project_shortages
from domino.graph.run_query import run_query

router = APIRouter(prefix="/api")


def _graph() -> dict[str, Any]:
    g = settings.world_graph_live
    sites = run_query("graph/sites", graph=g)
    nodes: list[dict[str, Any]] = []
    for s in sites:
        nodes.append({"id": s["id"], "kind": "site", "column": f"tier{min(s['tier'], 3)}", "label": s["name"],
                      "data": s})
    for p in run_query("graph/plants", graph=g):
        nodes.append({"id": p["id"], "kind": "plant", "column": "plant", "label": p["name"], "data": p})
    for p in run_query("graph/products", graph=g):
        nodes.append({"id": p["id"], "kind": "product", "column": "product", "label": p["name"], "data": p})
    edges: list[dict[str, Any]] = []
    for f in run_query("graph/feeds", graph=g):
        edges.append({"id": f"F:{f['src']}>{f['dst']}:{f['component']}", "source": f["src"], "target": f["dst"],
                      "kind": "feeds", "data": f})
    for e in run_query("graph/supply", graph=g):
        kind = "supplies" if e["kind"] == "SUPPLIES" else "can_supply"
        edges.append({"id": f"S:{e['src']}>{e['dst']}:{e['component']}:{kind}", "source": e["src"], "target": e["dst"],
                      "kind": kind, "data": e})
    for p in run_query("graph/plants", graph=g):
        for prod in p["products"]:
            edges.append({"id": f"B:{p['id']}>{prod}", "source": p["id"], "target": prod, "kind": "builds", "data": {}})
    customers: dict[str, dict[str, Any]] = {}
    demand: dict[tuple[str, str], dict[str, Any]] = {}
    for d in run_query("graph/demand", graph=g):
        c = customers.setdefault(d["customer"], {"id": d["customer"], "name": d["customer_name"], "tier": d["tier"],
                                                 "orders": 0, "order_ids": []})
        c["orders"] += d["orders"]
        c["order_ids"] += d["order_ids"]
        key = (d["product"], d["customer"])
        e = demand.setdefault(key, {"orders": 0, "order_ids": [], "plants": set()})
        e["orders"] += d["orders"]
        e["order_ids"] += d["order_ids"]
        e["plants"].add(d["plant"])
    for c in customers.values():
        nodes.append({"id": c["id"], "kind": "customer", "column": "customer", "label": c["name"], "data": c})
    for (prod, cust), e in sorted(demand.items()):
        edges.append({"id": f"D:{prod}>{cust}", "source": prod, "target": cust, "kind": "demand",
                      "data": {"orders": e["orders"], "order_ids": sorted(e["order_ids"]), "plants": sorted(e["plants"])}})
    return {"graph": g, "nodes": nodes, "edges": edges}


@router.get("/graph")
async def graph() -> dict[str, Any]:
    return await asyncio.to_thread(_graph)


def _summary() -> dict[str, Any]:
    g = settings.world_graph_live
    meta = run_query("decision/get", {"decision_id": ""}, graph=g)[0]
    incidents = run_query("graph/incidents", graph=g)
    proj = project_shortages(g)
    return {"graph": g, "world_version": meta["world_version"], "incidents": incidents,
            "totals": proj["totals"], "plants": proj["plants"]}


@router.get("/world/summary")
async def summary() -> dict[str, Any]:
    return await asyncio.to_thread(_summary)


@router.get("/world/places")
async def places() -> dict[str, Any]:
    rows = await asyncio.to_thread(run_query, "graph/places", None, graph=settings.world_graph_live)
    zones: dict[str, dict[str, Any]] = {}
    for r in rows:
        if r["zone"]:
            z = zones.setdefault(r["zone"], {"id": r["zone"], "name": r["zone_name"], "hazard": r["hazard"],
                                             "regions": [], "sites": 0})
            z["regions"].append(r["region_name"])
            z["sites"] += r["sites"]
    return {"zones": list(zones.values()),
            "regions": [{"id": r["region"], "name": r["region_name"], "country": r["country"], "sites": r["sites"]}
                        for r in rows]}


class Inject(BaseModel):
    entity_ids: list[str] = Field(min_length=1)
    kind: str = "disruption"
    title: str = "Manual disruption"
    capacity_factor: float = Field(0.0, ge=0, lt=1)
    duration_days: int = Field(14, ge=1, le=120)


def _inject(body: Inject) -> dict[str, Any]:
    g = settings.world_graph_live
    n = run_query("agent/next_incident_id", graph=g)[0]["n"]
    res = declare_incident(g, incident_id=f"INC-{n + 1:04d}", kind=body.kind, title=body.title,
                           alert_text=f"Manual injection: {body.title}", entity_ids=body.entity_ids,
                           capacity_factor=body.capacity_factor, duration_days=body.duration_days)
    if res["outcome"] != "ok":
        raise HTTPException(400, res)
    return res


@router.post("/incidents")
async def inject(body: Inject) -> dict[str, Any]:
    return await asyncio.to_thread(_inject, body)
