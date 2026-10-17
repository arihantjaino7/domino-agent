"""An external MCP client (Claude Code / Desktop) as the agent: its calls are recorded as the "external"
run, a human approves in the war room (HTTP), and only the executor commits. No LLM or API calls here:
this test plays the client's tool calls itself."""

import asyncio
import json

import pytest
from fastapi.testclient import TestClient
from mcp.client.client import Client

from domino.agent import external
from domino.agent.context import get_context
from domino.config import settings
from domino.graph.lifecycle import build_pristine, drop_graph
from domino.graph.run_query import run_query
from domino.mcp.server import mcp
from domino.seed.generator import generate

PRISTINE, LIVE, MEM = "test:ext:pristine", "test:ext:live", "test:ext:memory"


@pytest.fixture(scope="module")
def world():
    build_pristine(generate(42), PRISTINE)
    yield
    for g in (PRISTINE, LIVE, MEM):
        drop_graph(g)


async def _calls(*calls):
    out = []
    async with Client(mcp) as c:
        for name, args in calls:
            r = await c.call_tool(name, args)  # no run_id: an external client
            out.append((r.is_error, json.loads(r.content[0].text) if not r.is_error else r.content[0].text))
    return out


def test_external_client_flow_with_human_approval(world, monkeypatch):
    monkeypatch.setattr(settings, "world_graph_pristine", PRISTINE)
    monkeypatch.setattr(settings, "world_graph_live", LIVE)
    monkeypatch.setattr(settings, "memory_graph", MEM)
    from domino.api.main import app

    with TestClient(app) as http:
        assert http.post("/api/external/watch").json()["run_id"] == "external"

        res = asyncio.run(_calls(
            ("declare_incident", {"entity_ids": ["Z-CPB"], "kind": "flood", "title": "Monsoon", "duration_days": 28}),
            ("trace_exposure", {"incident_id": "INC-0001"}),
            ("project_shortages", {}),
            ("simulate_strategies", {}),
            ("submit_plan_for_approval", {"strategy_id": "S4", "rationale": "best in sandbox"}),
        ))
        assert all(not err for err, _ in res), res
        decision = res[-1][1]["decision_id"]
        snap = http.get("/api/runs/external").json()
        assert snap["status"] == "awaiting_approval" and snap["pending_decision"] == decision
        assert not run_query("upstream/purchase_orders", graph=LIVE)  # nothing bought before a human says yes

        status = asyncio.run(_calls(("get_decision_status", {"decision_id": decision})))[0][1]
        assert status["status"] == "awaiting_approval"

        assert http.post("/api/runs/external/approve", json={"approver": "test"}).json()["status"] == "executed"
        assert len(run_query("upstream/purchase_orders", graph=LIVE)) == 4

        after = asyncio.run(_calls(
            ("get_decision_status", {"decision_id": decision}),
            ("verify_execution", {"decision_id": decision}),
        ))
        assert after[0][1]["status"] == "executed"
        assert after[1][1]["all_pass"] is True

        kinds = [e["type"] for e in external.RUNS["external"].events]
        assert kinds[0] == "run.started"
        assert kinds.index("approval.required") < kinds.index("action.executed")
        assert kinds.count("tool.called") == kinds.count("tool.result") == 8


def test_external_rejection_is_reported_to_the_agent(world, monkeypatch):
    monkeypatch.setattr(settings, "world_graph_pristine", PRISTINE)
    monkeypatch.setattr(settings, "world_graph_live", LIVE)
    from domino.api.main import app

    with TestClient(app) as http:
        http.post("/api/external/watch")
        res = asyncio.run(_calls(
            ("declare_incident", {"entity_ids": ["Z-CPB"], "kind": "flood", "title": "Monsoon", "duration_days": 28}),
            ("simulate_strategies", {}),
            ("submit_plan_for_approval", {"strategy_id": "S4", "rationale": "x"}),
        ))
        decision = res[-1][1]["decision_id"]
        http.post("/api/runs/external/reject", json={"feedback": "too expensive"})
        status = asyncio.run(_calls(("get_decision_status", {"decision_id": decision})))[0][1]
        assert status["status"] == "rejected" and status["feedback"] == "too expensive"
        assert get_context("external").pending is None
        assert not run_query("upstream/purchase_orders", graph=LIVE)
