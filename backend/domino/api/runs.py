"""Agent runs over HTTP (PLAN §10): start, stream events (SSE with Last-Event-ID), approve, reject.

The agent reaches its tools through the same MCP server that is mounted at /mcp (in-process client).
`dry_run: true` uses the scripted stand-in model: free, for UI work and tests.
"""

from __future__ import annotations

import asyncio
import time
from collections import deque
from typing import Any

from fastapi import APIRouter, HTTPException, Request
from mcp.client.client import Client
from pydantic import BaseModel
from sse_starlette.sse import EventSourceResponse

from domino.agent import external
from domino.agent.context import get_context
from domino.agent.loop import AgentRun, approve, new_run, reject, run_phase
from domino.agent.scenarios import SCENARIOS
from domino.config import settings
from domino.graph.lifecycle import reset_live
from domino.mcp.server import mcp

router = APIRouter(prefix="/api")
RUNS = external.RUNS  # DOMINO's own runs and the external (MCP client) run share one registry
CLIENTS: dict[str, Any] = {}
_tasks: set[asyncio.Task] = set()
_live_by_ip: dict[str, deque[float]] = {}
_live_all: deque[float] = deque()


def _check_live_quota(ip: str) -> None:
    """Real agent runs cost API credit: cap them per IP per hour and globally per day (PLAN §14.4)."""
    now = time.time()
    mine = _live_by_ip.setdefault(ip, deque())
    while mine and now - mine[0] > 3600:
        mine.popleft()
    while _live_all and now - _live_all[0] > 86400:
        _live_all.popleft()
    if len(mine) >= settings.live_runs_per_hour_per_ip:
        raise HTTPException(429, f"live run limit: {settings.live_runs_per_hour_per_ip} per hour per visitor; "
                                 "try again later or use dry_run")
    if len(_live_all) >= settings.live_runs_per_day:
        raise HTTPException(429, "the demo's daily live-run budget is used up; use dry_run")
    mine.append(now)
    _live_all.append(now)


class StartRun(BaseModel):
    scenario: str | None = None
    alert_text: str | None = None
    budget_usd: int | None = None
    dry_run: bool = False


class Approval(BaseModel):
    approver: str = "web"
    decision_id: str | None = None


class Rejection(BaseModel):
    feedback: str
    decision_id: str | None = None


def _client(scenario: str, dry_run: bool) -> Any:
    if dry_run:
        from domino.agent.scripted import ScriptedClient
        return ScriptedClient(scenario)
    if not settings.anthropic_api_key:
        raise HTTPException(400, "ANTHROPIC_API_KEY is not configured; use dry_run for the scripted model")
    from anthropic import AsyncAnthropic
    return AsyncAnthropic(api_key=settings.anthropic_api_key)


def _background(run: AgentRun, step) -> None:
    async def go() -> None:
        try:
            async with Client(mcp) as mc:
                await step(mc)
        except Exception as exc:  # noqa: BLE001 - surface any failure as a run.error event
            from domino.agent.loop import _fail
            _fail(run, f"{type(exc).__name__}: {exc}")
    task = asyncio.create_task(go())
    _tasks.add(task)
    task.add_done_callback(_tasks.discard)


def _get(run_id: str) -> AgentRun:
    run = RUNS.get(run_id)
    if run is None:
        raise HTTPException(404, f"unknown run {run_id}")
    return run


@router.get("/scenarios")
async def scenarios() -> dict:
    return {"scenarios": [{"id": k, **v} for k, v in SCENARIOS.items()]}


@router.post("/world/reset")
async def world_reset() -> dict:
    live = await asyncio.to_thread(reset_live)
    if external.EXTERNAL_ID in RUNS:
        external.reset_external()
    return {"graph": live, "status": "reset from pristine"}


@router.post("/external/watch")
async def watch_external() -> dict:
    """Reset the live world and open a fresh external run for an MCP client (Claude Code) to drive."""
    await asyncio.to_thread(reset_live)
    run = external.reset_external()
    return {"run_id": run.id, "graph": run.graph}


@router.post("/runs")
async def start_run(body: StartRun, request: Request) -> dict:
    scenario = body.scenario or "custom"
    alert = body.alert_text or (SCENARIOS[scenario]["alert"] if scenario in SCENARIOS else None)
    if not alert:
        raise HTTPException(400, "give a known scenario or alert_text")
    if body.alert_text and len(body.alert_text) > 2000:
        raise HTTPException(400, "alert_text is limited to 2000 characters")
    client = _client(scenario, body.dry_run)
    if not body.dry_run:
        _check_live_quota(request.client.host if request.client else "unknown")
    run = new_run(scenario, alert, settings.world_graph_live, budget_cents=(body.budget_usd or 0) * 100 or None,
                  scripted=body.dry_run)
    external.register(run)
    CLIENTS[run.id] = client
    from domino.agent.loop import emit
    emit(run, "run.started", {"scenario": scenario, "alert": alert, "dry_run": body.dry_run,
                              "model": "scripted" if body.dry_run else settings.domino_model})
    _background(run, lambda mc: run_phase(run, client, mc))
    return {"run_id": run.id}


@router.get("/runs/{run_id}")
async def get_run(run_id: str) -> dict:
    run = _get(run_id)
    ctx = get_context(run_id)
    return {"run_id": run.id, "status": run.status, "scenario": run.scenario, "error": run.error,
            "tool_calls": run.tool_calls, "usage": run.usage, "cost_usd": run.cost_usd,
            "pending_decision": ctx.pending["decision_id"] if ctx.pending and run.status == "awaiting_approval" else None,
            "report": ctx.report, "receipt": ctx.receipt, "events": len(run.events)}


@router.get("/runs/{run_id}/events")
async def run_events(run_id: str, request: Request) -> EventSourceResponse:
    run = _get(run_id)
    start = int(request.headers.get("last-event-id") or 0)

    async def stream():
        sent = start
        while True:
            while sent < len(run.events):
                ev = run.events[sent]
                sent += 1
                yield {"id": str(ev["seq"]), "event": ev["type"], "data": _json(ev)}
            if run.status in ("completed", "failed") and sent >= len(run.events):
                return
            if await request.is_disconnected():
                return
            signal = external.signal(run_id)
            signal.clear()
            try:
                await asyncio.wait_for(signal.wait(), timeout=15)
            except asyncio.TimeoutError:
                pass

    return EventSourceResponse(stream(), ping=10, headers={"X-Accel-Buffering": "no"})


def _json(ev: dict) -> str:
    import json
    return json.dumps(ev, default=str)


@router.post("/runs/{run_id}/approve")
async def approve_run(run_id: str, body: Approval) -> dict:
    run = _get(run_id)
    pending = get_context(run_id).pending
    if run.status != "awaiting_approval" or pending is None:
        raise HTTPException(409, f"run is {run.status}")
    if body.decision_id and body.decision_id != pending["decision_id"]:
        raise HTTPException(409, f"pending decision is {pending['decision_id']}")
    run.status = "approving"  # a second click now gets 409 instead of a second execution
    if run_id == external.EXTERNAL_ID:  # the external client is the agent; only the executor runs here
        try:
            receipt = await external.approve_external(body.approver)
        except ValueError as exc:
            raise HTTPException(409, str(exc)) from exc
        return {"run_id": run_id, "decision_id": pending["decision_id"], "status": receipt.get("outcome")}
    _background(run, lambda mc: approve(run, body.approver, CLIENTS[run_id], mc))
    return {"run_id": run_id, "decision_id": pending["decision_id"], "status": "executing"}


@router.post("/runs/{run_id}/reject")
async def reject_run(run_id: str, body: Rejection) -> dict:
    run = _get(run_id)
    if run.status != "awaiting_approval":
        raise HTTPException(409, f"run is {run.status}")
    if run_id == external.EXTERNAL_ID:
        external.reject_external(body.feedback)
        return {"run_id": run_id, "status": "rejected; tell the agent in your MCP client"}
    _background(run, lambda mc: reject(run, body.feedback, CLIENTS[run_id], mc))
    return {"run_id": run_id, "status": "re-planning"}
