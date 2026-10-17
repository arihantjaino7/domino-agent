"""Replay mode: watch a recorded run without an API key, a Claude subscription or any write to the graph.

Recording: every run started from the war room gets a recorder. It keeps the run's events exactly as the
war room received them, plus a snapshot of the world view (`/api/graph` and `/api/world/summary`) at the
start and whenever the live war room would refresh it (incident declared, orders flagged, plan executed,
verified, run finished). When the run ends, the recording is written to `backend/runs/replays/` (ignored
by Git). A recording is published by copying it to `demo/replays/` and giving it a title.

Playback: `GET /api/replays` lists the published recordings and `GET /api/replays/{id}` returns one.
The browser plays the events back through the same code that handles live events, and swaps in the
recorded world snapshots at the same points. Every number shown is the engines' output at recording time.
"""

from __future__ import annotations

import datetime as dt
import json
import re
from pathlib import Path
from typing import Any

from fastapi import APIRouter, HTTPException

from domino.agent.loop import AgentRun
from domino.agent.scenarios import SCENARIOS
from domino.api.world import _graph, _summary
from domino.config import REPO_ROOT

router = APIRouter(prefix="/api")
RECORD_DIR = REPO_ROOT / "backend" / "runs" / "replays"
PUBLISHED_DIR = REPO_ROOT / "demo" / "replays"
FORMAT = 1
_ID = re.compile(r"^[a-z0-9][a-z0-9-]{0,63}$")

# The same moments at which the live war room re-reads /api/graph and /api/world/summary (store.ts).
_REFRESH_TOOLS = {"declare_incident", "flag_orders_at_risk", "verify_execution"}
_REFRESH_EVENTS = {"action.executed", "run.completed"}
_END_EVENTS = {"run.completed", "run.error"}


def _snapshot(after_seq: int) -> dict[str, Any]:
    return {"after_seq": after_seq, "graph": _graph(), "summary": _summary()}


def _wants_snapshot(ev: dict[str, Any]) -> bool:
    if ev["type"] in _REFRESH_EVENTS:
        return True
    return ev["type"] == "tool.result" and not ev["data"].get("is_error") and ev["data"].get("tool") in _REFRESH_TOOLS


def _agent(run: AgentRun) -> tuple[str, bool]:
    """(who drove the run, whether a real model chose the tools)."""
    started = next((e["data"] for e in run.events if e["type"] == "run.started"), {})
    if started.get("dry_run"):
        return "Scripted stand-in (no model)", False
    if run.scenario == "mcp":
        return "Claude Code over MCP", True
    return f"Claude API ({started.get('model', 'model')})", True


def build_recording(run: AgentRun, frames: list[dict[str, Any]]) -> dict[str, Any]:
    agent, real = _agent(run)
    title = SCENARIOS.get(run.scenario, {}).get("title") or next(
        (e["data"]["args"].get("title") for e in run.events
         if e["type"] == "tool.called" and e["data"].get("tool") == "declare_incident"), None) or "Recorded run"
    return {"format": FORMAT, "id": run.id, "title": title, "scenario": run.scenario, "agent": agent,
            "real_model": real, "recorded_utc": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
            "status": run.status, "tool_calls": run.tool_calls, "cost_usd": run.cost_usd,
            "frames": frames, "events": list(run.events)}


def attach_recorder(run: AgentRun, directory: Path | None = None) -> None:
    """Record `run` from now on. A failed snapshot is skipped; it never breaks the run itself."""
    frames: list[dict[str, Any]] = []

    def take(after_seq: int) -> None:
        try:
            frames.append(_snapshot(after_seq))
        except Exception:  # noqa: BLE001 - the world view is optional for a recording, the run is not
            pass

    def on_event(ev: dict[str, Any]) -> None:
        if _wants_snapshot(ev):
            take(ev["seq"])
        if ev["type"] in _END_EVENTS:
            try:
                out = directory or RECORD_DIR
                out.mkdir(parents=True, exist_ok=True)
                (out / f"{run.id}.json").write_text(json.dumps(build_recording(run, frames), default=str),
                                                    encoding="utf-8", newline="\n")
            except Exception:  # noqa: BLE001
                pass

    take(len(run.events))  # the world as the run begins
    run.listeners.append(on_event)


def _published() -> dict[str, Path]:
    if not PUBLISHED_DIR.is_dir():
        return {}
    return {p.stem: p for p in sorted(PUBLISHED_DIR.glob("*.json")) if _ID.match(p.stem)}


@router.get("/replays")
async def list_replays() -> dict[str, Any]:
    out = []
    for rid, path in _published().items():
        rec = json.loads(path.read_text(encoding="utf-8"))
        out.append({"id": rid, "title": rec.get("title"), "scenario": rec.get("scenario"), "agent": rec.get("agent"),
                    "real_model": rec.get("real_model", False), "recorded_utc": rec.get("recorded_utc"),
                    "note": rec.get("note"), "tool_calls": rec.get("tool_calls"), "events": len(rec.get("events", []))})
    # Real-model recordings first, then by title.
    out.sort(key=lambda r: (not r["real_model"], r["title"] or ""))
    return {"replays": out}


@router.get("/replays/{replay_id}")
async def get_replay(replay_id: str) -> dict[str, Any]:
    path = _published().get(replay_id)  # only names that are listed: no path from the request reaches the disk
    if path is None:
        raise HTTPException(404, f"unknown replay {replay_id}")
    return json.loads(path.read_text(encoding="utf-8"))
