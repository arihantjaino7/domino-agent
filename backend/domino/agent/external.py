"""Runs driven from outside DOMINO, by an MCP client such as Claude Code or Claude Desktop.

The external client is the agent: it reads the alert and chooses DOMINO's tools over /mcp. DOMINO
records each call as the same event stream its own loop produces, so the war room can watch it live.
Purchase commitments still need a human: `submit_plan_for_approval` pauses, a person approves in the
war room, and only then does the executor run. The LLM never executes anything.

All runs (DOMINO's own and the external one) share this registry, so the HTTP API serves both.
"""

from __future__ import annotations

import asyncio
import json
from typing import Any

from domino.agent.context import CONTEXTS, get_context, new_context
from domino.agent.loop import AgentRun, emit, save
from domino.agent.tools import record_approval_failure, record_rejection
from domino.config import settings
from domino.engines.executor import approve_decision, execute_plan

EXTERNAL_ID = "external"
RUNS: dict[str, AgentRun] = {}
SIGNALS: dict[str, asyncio.Event] = {}


def signal(run_id: str) -> asyncio.Event:
    return SIGNALS.setdefault(run_id, asyncio.Event())


def register(run: AgentRun) -> AgentRun:
    """Track a run and wake its SSE readers on every event."""
    RUNS[run.id] = run
    ev = signal(run.id)
    run.listeners.append(lambda _e: ev.set())
    return run


def external_run() -> AgentRun:
    """The single external run on the live world (created on first use)."""
    run = RUNS.get(EXTERNAL_ID)
    if run is None:
        run = register(AgentRun(id=EXTERNAL_ID, scenario="mcp", alert_text="", graph=settings.world_graph_live,
                                status="running"))
        if EXTERNAL_ID not in CONTEXTS:
            new_context(EXTERNAL_ID, settings.world_graph_live)
        emit(run, "run.started", {"scenario": "mcp", "model": "external MCP client", "dry_run": False})
    return run


def reset_external() -> AgentRun:
    """Fresh external run and context, e.g. after the world is reset."""
    RUNS.pop(EXTERNAL_ID, None)
    new_context(EXTERNAL_ID, settings.world_graph_live)
    return external_run()


def before_call(tool: str, args: dict[str, Any]) -> AgentRun:
    run = external_run()
    run.tool_calls += 1
    emit(run, "tool.called", {"tool": tool, "args": args, "step": run.tool_calls})
    return run


def after_call(run: AgentRun, tool: str, out: dict[str, Any] | None, error: str | None, ms: int) -> None:
    ctx = get_context(EXTERNAL_ID)
    ref = out.get("result_ref") if out else None
    emit(run, "tool.result", {"tool": tool, "is_error": error is not None, "result_ref": ref, "duration_ms": ms,
                              "summary": (error or json.dumps(out, default=str))[:400],
                              "ui": ctx.ui.get(ref) if ref else None,
                              "queries": ctx.queries.get(ref) if ref else None})
    if error:
        return
    if tool == "submit_plan_for_approval" and ctx.pending:
        plan = ctx.pending
        run.status = "awaiting_approval"
        emit(run, "plan.proposed", {"decision_id": plan["decision_id"], "strategy": plan["strategy"],
                                    "plan_hash": plan["plan_hash"], "spend_cents": plan["spend_cents"], "pos": plan["pos"]})
        emit(run, "approval.required", {"decision_id": plan["decision_id"]})
    if tool == "submit_incident_report" and ctx.report:
        run.status = "completed"
        emit(run, "run.completed", {"report": ctx.report, "usage": run.usage, "cost_usd": 0})
        save(run)


async def approve_external(approver: str) -> dict[str, Any]:
    """A human approved in the war room: run the executor (never the LLM) and record the receipt."""
    run, ctx = external_run(), get_context(EXTERNAL_ID)
    plan = ctx.pending
    if run.status not in ("awaiting_approval", "approving") or plan is None:
        raise ValueError(f"nothing awaits approval (run is {run.status})")
    approval = await asyncio.to_thread(approve_decision, run.graph, plan, approver)
    if approval["outcome"] != "ok":
        record_approval_failure(ctx, approval)  # get_decision_status now tells the agent why
        run.status = "running"
        emit(run, "approval.failed", approval)
        return approval
    receipt = await asyncio.to_thread(execute_plan, run.graph, plan)
    ctx.receipt = receipt
    run.status = "running"
    emit(run, "action.executed", {"decision_id": plan["decision_id"], "receipt": receipt})
    return receipt


async def reject_external(feedback: str) -> None:
    run, ctx = external_run(), get_context(EXTERNAL_ID)
    if ctx.pending is None:
        raise ValueError("nothing awaits approval")
    decision = await asyncio.to_thread(record_rejection, ctx, feedback)
    run.status = "running"
    emit(run, "plan.rejected", {"decision_id": decision, "feedback": feedback})
