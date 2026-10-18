"""Risk X-ray endpoint: the single-point-of-failure scan of the live world. Read-only."""

from __future__ import annotations

import asyncio
from typing import Any

from fastapi import APIRouter, Query

from domino.config import settings
from domino.engines.xray import DEFAULT_DURATION, scan
from domino.graph.run_query import QueryError

router = APIRouter(prefix="/api")


@router.get("/xray")
async def xray(duration_days: int = Query(DEFAULT_DURATION, ge=1, le=120)) -> dict[str, Any]:
    # A reset replaces the live world for a moment; reading it then fails, so wait briefly and read again.
    for _ in range(4):
        try:
            return await asyncio.to_thread(scan, settings.world_graph_live, duration_days)
        except QueryError:
            await asyncio.sleep(0.5)
    return await asyncio.to_thread(scan, settings.world_graph_live, duration_days)
