"""Institutional memory (PLAN §7.13) in the separate `memory` graph, which survives world resets.

Memory is more nodes, returned with the date it was learned (organizer guidance, §0.2).
"""

from __future__ import annotations

import datetime as dt
from typing import Any

from domino.config import settings
from domino.graph.run_query import run_query


def _today() -> str:
    return dt.date.today().isoformat()


def record_incident(incident: dict[str, Any], entities: list[dict[str, Any]], graph: str | None = None) -> int:
    """incident: {id, title, kind, outcome}; entities: [{id, kind, name, role}]."""
    rows = run_query("memory/write_incident", {"incident": {**incident, "learned_on": _today()},
                                                "entities": entities},
                     ro=False, graph=graph or settings.memory_graph)
    return rows[0]["linked"] if rows else 0


def record_lessons(incident_id: str, lessons: list[dict[str, Any]], graph: str | None = None) -> list[str]:
    """lessons: [{text, entity_ids, evidence}] -> lesson ids."""
    today = _today()
    rows = [{"id": f"L-{incident_id}-{i + 1}", "text": l["text"], "incident_id": incident_id, "learned_on": today,
             "entity_ids": sorted(set(l.get("entity_ids", []))), "evidence": l.get("evidence", "")}
            for i, l in enumerate(lessons)]
    if rows:
        run_query("memory/write_lessons", {"lessons": rows}, ro=False, graph=graph or settings.memory_graph)
    return [r["id"] for r in rows]


def recall_history(entity_ids: list[str], graph: str | None = None) -> list[dict[str, Any]]:
    out = []
    for r in run_query("memory/recall", {"entity_ids": sorted(set(entity_ids))}, graph=graph or settings.memory_graph):
        out.append({"entity": r["entity"], "name": r["name"], "reliability": r["reliability"],
                    "incidents": [i for i in r["incidents"] if i.get("id")],
                    "lessons": [l for l in r["lessons"] if l.get("text")]})
    return out


def list_incidents(graph: str | None = None) -> list[dict[str, Any]]:
    return run_query("memory/incidents", graph=graph or settings.memory_graph)
