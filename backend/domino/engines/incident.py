"""Incident declaration (PLAN §7.2). Pure and deterministic; no LLM.

Recording an observed fact is a safe write: resolve every entity id against the graph,
expand zones and regions to their sites, then one atomic write (Q-DECLARE).
"""

from __future__ import annotations

from typing import Any

from domino.graph.run_query import run_query


def expand_sites(graph: str, entity_ids: list[str]) -> dict[str, Any]:
    """Resolve ids and expand them to site ids. Unknown ids give the outcome `unknown_entity`."""
    rows = run_query("incident/resolve_places", {"ids": sorted(set(entity_ids))}, graph=graph)
    unknown = [r["id"] for r in rows if not r["labels"]]
    if unknown:
        return {"outcome": "unknown_entity", "unknown": unknown, "site_ids": []}
    sites: set[str] = set()
    for r in rows:
        labels = r["labels"]
        if "Site" in labels:
            sites.add(r["id"])
        elif "Region" in labels:
            sites |= {x["site"] for x in run_query("incident/region_sites", {"region_id": r["id"]}, graph=graph)}
        elif "HazardZone" in labels:
            for x in run_query("incident/zone_sites", {"zone_id": r["id"]}, graph=graph):
                sites |= set(x["sites"])
        else:
            return {"outcome": "unsupported_entity", "unsupported": [r["id"]], "site_ids": []}
    return {"outcome": "ok", "site_ids": sorted(sites)}


def declare_incident(
    graph: str,
    *,
    incident_id: str,
    kind: str,
    title: str,
    alert_text: str,
    entity_ids: list[str],
    capacity_factor: float,
    duration_days: int,
    day: int = 0,
) -> dict[str, Any]:
    """Mark the affected sites disrupted until day + duration and create the Incident with AFFECTS edges."""
    expanded = expand_sites(graph, entity_ids)
    if expanded["outcome"] != "ok":
        return expanded
    site_ids = expanded["site_ids"]
    if not site_ids:
        return {"outcome": "no_sites_in_footprint", "site_ids": []}
    end_day = day + duration_days
    rows = run_query("incident/declare", {
        "incident_id": incident_id, "kind": kind, "title": title, "alert": alert_text,
        "day": day, "end_day": end_day, "factor": float(capacity_factor), "site_ids": site_ids,
    }, ro=False, graph=graph)
    affected = rows[0]["sites_affected"] if rows else 0
    if affected != len(site_ids):
        raise RuntimeError(f"Q-DECLARE affected {affected} of {len(site_ids)} sites")
    return {"outcome": "ok", "incident_id": incident_id, "site_ids": site_ids, "end_day": end_day,
            "capacity_factor": capacity_factor, "world_version": rows[0]["world_version"]}
