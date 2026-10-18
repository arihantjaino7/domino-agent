"""Memory tab: what DOMINO remembers from past incidents and deliveries, each item with the date it was learned.

Real runs write to `memory`; scripted Demo runs write to `memory:dryrun`, so the caller picks which one to read.
Only those two graphs can be read here; the name is never taken from the request.
"""

from __future__ import annotations

import asyncio
from typing import Any, Literal

from fastapi import APIRouter

from domino.agent import memory
from domino.config import settings
from domino.engines.delivery import learned_for

router = APIRouter(prefix="/api")


def _graph_for(source: str) -> str:
    return settings.memory_graph_dryrun if source == "demo" else settings.memory_graph


def _memory(source: str) -> dict[str, Any]:
    g = _graph_for(source)
    incidents = memory.list_incidents(graph=g)   # both return [] while the graph does not exist yet
    lessons = memory.list_lessons(graph=g)
    ids = {e for row in incidents + lessons for e in row["entities"] if e}
    names = memory.entity_names(sorted(ids), settings.world_graph_live)

    def ents(row: dict[str, Any]) -> list[dict[str, Any]]:
        # in_world=False means the current world has no node with that id. It is not a claim that it is safe.
        return [{"id": e, "name": (names.get(e) or {}).get("name") or e, "kind": (names.get(e) or {}).get("kind"),
                 "in_world": e in names} for e in sorted(set(row["entities"])) if e]

    return {
        "source": source, "graph": g,
        "incidents": [{**r, "entities": ents(r)} for r in incidents],
        "lessons": [{**r, "entities": ents(r)} for r in lessons],
        "counts": {"incidents": len(incidents), "lessons": len(lessons)},
        # Supplier reliability learned from delivery facts, against the current world's seeded value.
        "reliability": learned_for(settings.world_graph_live, g),
    }


@router.get("/memory")
async def get_memory(source: Literal["real", "demo"] = "real") -> dict[str, Any]:
    return await asyncio.to_thread(_memory, source)
