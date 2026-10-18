"""Fast-forward to delivery, and what memory learned from it.

`POST /api/runs/{run_id}/deliver` is a war-room button, never an agent tool: once a run's plan was executed and
verified, the simulated clock runs until its purchase orders arrive (engines.delivery), the outcomes are written
to the world, and each supplier's performance is written to that run's memory graph (`memory`, or
`memory:dryrun` for scripted runs). The event it emits is returned too, so the war room applies it like any other.
"""

from __future__ import annotations

import asyncio
from typing import Any, Literal

from fastapi import APIRouter, HTTPException

from domino.agent import external
from domino.agent.context import CONTEXTS
from domino.agent.loop import emit
from domino.agent.tools import record_delivery
from domino.api.memory import _graph_for
from domino.config import settings
from domino.engines import delivery

router = APIRouter(prefix="/api")


@router.post("/runs/{run_id}/deliver")
async def deliver(run_id: str) -> dict[str, Any]:
    run, ctx = external.RUNS.get(run_id), CONTEXTS.get(run_id)
    if run is None or ctx is None:
        raise HTTPException(404, f"unknown run {run_id}")
    if run.status in ("awaiting_approval", "approving", "rejecting"):
        raise HTTPException(409, f"run is {run.status}")

    def work() -> dict[str, Any]:
        with ctx.lock:
            return record_delivery(ctx)

    try:
        res = await asyncio.to_thread(work)
    except ValueError as exc:
        raise HTTPException(409, str(exc)) from exc
    ev = emit(run, "delivery.completed", res)
    return {"run_id": run_id, "event": ev}


def _deliveries(source: str) -> dict[str, Any]:
    g = settings.world_graph_live
    mem = _graph_for(source)
    return {"graph": g, "memory_graph": mem, "pos": delivery.delivered(g),
            "learned_reliability": delivery.learned_for(g, mem)}


@router.get("/deliveries")
async def deliveries(source: Literal["real", "demo"] = "real") -> dict[str, Any]:
    return await asyncio.to_thread(_deliveries, source)
