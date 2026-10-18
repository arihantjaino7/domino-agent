"""Risk X-ray endpoint: the single-point-of-failure scan of the live world. Read-only."""

from __future__ import annotations

import asyncio
from typing import Any

from fastapi import APIRouter, Query

from domino.config import settings
from domino.engines.xray import DEFAULT_DURATION, scan

router = APIRouter(prefix="/api")


@router.get("/xray")
async def xray(duration_days: int = Query(DEFAULT_DURATION, ge=1, le=120)) -> dict[str, Any]:
    return await asyncio.to_thread(scan, settings.world_graph_live, duration_days)
