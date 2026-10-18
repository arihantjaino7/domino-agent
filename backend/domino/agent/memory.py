"""Institutional memory in the separate `memory` graph, which survives world resets.

Memory is more nodes, returned with the date it was learned.
"""

from __future__ import annotations

import datetime as dt
from typing import Any

from domino.config import settings
from domino.graph.client import get_db
from domino.graph.run_query import run_query


def _today() -> str:
    return dt.date.today().isoformat()


def new_incident_id(graph: str | None = None) -> str:
    """The next free memory incident id (MI-0001, MI-0002...). Unlike world incident ids, it never restarts."""
    g = graph or settings.memory_graph
    n = run_query("memory/incident_count", graph=g)[0]["n"] if _exists(g) else 0
    taken = {r["id"] for r in list_incidents(g)}
    while f"MI-{n + 1:04d}" in taken:
        n += 1
    return f"MI-{n + 1:04d}"


def record_incident(incident: dict[str, Any], entities: list[dict[str, Any]], graph: str | None = None) -> int:
    """incident: {id, incident_id (the world's), title, kind, outcome}; entities: [{id, kind, name, role}]."""
    rows = run_query("memory/write_incident", {"incident": {**incident, "learned_on": _today()},
                                                "entities": entities},
                     ro=False, graph=graph or settings.memory_graph)
    return rows[0]["linked"] if rows else 0


def record_lessons(incident_id: str, lessons: list[dict[str, Any]], graph: str | None = None) -> list[str]:
    """lessons: [{text, entity_ids, evidence}] -> lesson ids. A second call for the same incident adds lessons
    (L-<incident>-3, -4...) instead of overwriting the first ones."""
    today = _today()
    g = graph or settings.memory_graph
    have = run_query("memory/incident_lessons", {"incident_id": incident_id}, graph=g)[0] if _exists(g) else \
        {"n": 0, "texts": []}
    known = set(have["texts"])
    new = [l for l in lessons if l["text"] not in known]  # the same lesson sent twice is stored once
    rows = [{"id": f"L-{incident_id}-{have['n'] + i + 1}", "text": l["text"], "incident_id": incident_id,
             "learned_on": today, "entity_ids": sorted(set(l.get("entity_ids", []))), "evidence": l.get("evidence", "")}
            for i, l in enumerate(new)]
    if rows:
        run_query("memory/write_lessons", {"lessons": rows}, ro=False, graph=g)
    return [r["id"] for r in rows]


def _exists(graph: str) -> bool:
    """Nothing learned yet (fresh deploy): FalkorDB has no key for the graph, and querying it errors."""
    return graph in get_db().list_graphs()


def recall_history(entity_ids: list[str], graph: str | None = None) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    g = graph or settings.memory_graph
    if not _exists(g):
        return out
    for r in run_query("memory/recall", {"entity_ids": sorted(set(entity_ids))}, graph=g):
        out.append({"entity": r["entity"], "name": r["name"], "reliability": r["reliability"],
                    "incidents": [i for i in r["incidents"] if i.get("id")],
                    "lessons": [l for l in r["lessons"] if l.get("text")]})
    return out


def list_incidents(graph: str | None = None) -> list[dict[str, Any]]:
    g = graph or settings.memory_graph
    return run_query("memory/incidents", graph=g) if _exists(g) else []


def list_lessons(graph: str | None = None) -> list[dict[str, Any]]:
    """Every lesson, newest first; `evidence` is split back into the evidence ids it cited."""
    g = graph or settings.memory_graph
    rows = run_query("memory/lessons", graph=g) if _exists(g) else []
    return [{**r, "evidence": [e for e in (r["evidence"] or "").split(",") if e]} for r in rows]


def entity_names(ids: list[str], world_graph: str) -> dict[str, dict[str, Any]]:
    """{id: {name, kind}} for the ids that exist in `world_graph`; ids not in that world are left out."""
    if not ids:
        return {}
    rows = run_query("memory/entity_names", {"ids": sorted(set(ids))}, graph=world_graph)
    return {r["id"]: {"name": r["name"], "kind": r["kind"]} for r in rows if r["kind"] is not None}
