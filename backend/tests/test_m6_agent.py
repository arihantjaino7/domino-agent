"""M6: MCP tool catalogue, agent loop, approval pause/resume, report validation, memory, HTTP runs.

Everything here uses the scripted stand-in model (offline, $0) and test:m6:* graphs; no API calls.
"""

import asyncio
import json
import time

import pytest
from fastapi.testclient import TestClient
from mcp.client.client import Client

from domino.agent import memory
from domino.agent.context import get_context, new_context
from domino.agent.loop import approve, model_tools, new_run, reject, run_phase
from domino.agent.scenarios import SCENARIOS
from domino.agent.scripted import ScriptedClient
from domino.config import settings
from domino.graph.lifecycle import build_pristine, copy_graph, drop_graph
from domino.graph.run_query import run_query
from domino.mcp.server import mcp
from domino.seed.generator import generate

PRISTINE, WORLD, MEM = "test:m6:pristine", "test:m6:world", "test:m6:memory"


@pytest.fixture(scope="module", autouse=True)
def graphs():
    build_pristine(generate(42), PRISTINE)
    yield
    for g in (PRISTINE, WORLD, MEM, "test:m6:api"):
        drop_graph(g)


@pytest.fixture(autouse=True)
def isolated(monkeypatch):
    monkeypatch.setattr(settings, "memory_graph", MEM)
    copy_graph(PRISTINE, WORLD)


def _run(scenario, client=None):
    async def go():
        run = new_run(scenario, SCENARIOS[scenario]["alert"], WORLD)
        c = client or ScriptedClient(scenario)
        async with Client(mcp) as mc:
            await run_phase(run, c, mc)
        return run, c
    return asyncio.run(go())


def _resume(fn, run, client, arg):
    async def go():
        async with Client(mcp) as mc:
            await fn(run, arg, client, mc)
    asyncio.run(go())


# ---------------------------------------------------------------------------
# Tool catalogue
# ---------------------------------------------------------------------------

def test_model_sees_a_fixed_catalogue_without_run_id_or_cypher():
    async def go():
        async with Client(mcp) as mc:
            return await model_tools(mc)
    tools = asyncio.run(go())
    names = [t["name"] for t in tools]
    assert "execute_plan" not in names and not any("cypher" in n or "query" in n for n in names)
    assert {"trace_exposure", "compute_true_capacity", "find_alternatives", "simulate_strategies",
            "submit_plan_for_approval", "submit_incident_report"} <= set(names)
    for t in tools:
        assert "run_id" not in t["input_schema"].get("properties", {})
        assert "run_id" not in t["input_schema"].get("required", [])


def test_unknown_id_is_an_error_with_suggestions():
    new_context("t-unknown", WORLD)

    async def go():
        async with Client(mcp) as mc:
            return await mc.call_tool("find_alternatives", {"component_id": "BAT-4X", "plant_id": "PL-BAC",
                                                             "run_id": "t-unknown"})
    out = asyncio.run(go())
    assert out.is_error
    assert "unknown_entity" in out.content[0].text and "BAT-4S" in out.content[0].text


# ---------------------------------------------------------------------------
# The loop, end to end
# ---------------------------------------------------------------------------

def test_request_follows_the_api_guidance():
    run, client = _run("non_event")
    req = client.requests[0]
    assert req["model"] == settings.domino_model
    assert req["thinking"] == {"type": "adaptive"}
    assert req["output_config"] == {"effort": settings.domino_effort}
    assert "tool_choice" not in req                      # forced tool choice is a 400 on this model
    assert req["system"][0]["cache_control"] == {"type": "ephemeral"}
    assert req["fallbacks"] == "default" and "server-side-fallback-2026-07-01" in req["betas"]


def test_monsoon_pauses_for_approval_then_executes_verifies_and_reports():
    run, client = _run("monsoon")
    assert run.status == "awaiting_approval"
    ctx = get_context(run.id)
    assert ctx.pending["strategy"] == "S4" and ctx.receipt is None
    assert not run_query("upstream/purchase_orders", graph=WORLD)      # nothing committed before approval

    _resume(approve, run, client, "tester")
    assert run.status == "completed", run.error
    assert ctx.receipt["outcome"] == "executed" and ctx.receipt["receipt_matches_plan"]
    assert len(run_query("upstream/purchase_orders", graph=WORLD)) == len(ctx.pending["pos"])
    verify = next(r for r in ctx.results.values() if "all_pass" in r)
    assert verify["all_pass"]
    assert ctx.report["outcome"] == "answered_with_path"
    types = [e["type"] for e in run.events]
    assert types.index("approval.required") < types.index("action.executed") < types.index("run.completed")
    # Memory: the lesson is stored with the date it was learned.
    recalled = memory.recall_history(["S-VOLT-AYU"])
    assert recalled and recalled[0]["lessons"][0]["learned_on"]
    assert recalled[0]["name"] == "VoltCell Energy Ayutthaya"           # stored from the world, not the raw id


def test_a_later_run_recalls_the_earlier_runs_lesson_with_its_date():
    drop_graph(MEM)
    first, client = _run("monsoon")
    recall = next(r for r in get_context(first.id).results.values() if "memories" in r)
    assert recall["outcome"] == "nothing_remembered"              # nothing learned yet
    _resume(approve, first, client, "tester")
    assert first.status == "completed", first.error

    copy_graph(PRISTINE, WORLD)                                  # world reset; memory survives
    second, _ = _run("monsoon")
    recall = next(r for r in get_context(second.id).results.values() if "memories" in r)
    assert recall["outcome"] == "answered_from_memory"
    volt = next(m for m in recall["memories"] if m["entity"] == "S-VOLT-AYU")
    assert volt["lessons"] and all(l["learned_on"] for l in volt["lessons"])


def test_rejection_with_feedback_re_plans():
    run, client = _run("monsoon")
    first = get_context(run.id).pending["decision_id"]
    _resume(reject, run, client, "too slow, use the max-service plan")
    assert run.status == "awaiting_approval"
    assert get_context(run.id).pending["decision_id"] != first
    _resume(approve, run, client, "tester")
    assert run.status == "completed"


def test_non_event_says_not_in_graph_and_declares_nothing():
    run, _ = _run("non_event")
    ctx = get_context(run.id)
    assert run.status == "completed" and ctx.report["outcome"] == "not_in_graph"
    assert "not the same as safe" in ctx.report["claims"][0]["text"]
    assert run_query("agent/next_incident_id", graph=WORLD)[0]["n"] == 0


# ---------------------------------------------------------------------------
# Report validation (structured claims + entity guard)
# ---------------------------------------------------------------------------

def _report(run_id, **kw):
    async def go():
        async with Client(mcp) as mc:
            return await mc.call_tool("submit_incident_report", {"run_id": run_id, "headline": "h",
                                                                  "outcome": "answered_with_path", **kw})
    return asyncio.run(go())


def test_report_rejects_invented_evidence_unresolved_metrics_and_unseen_ids():
    run, client = _run("monsoon")
    ctx = get_context(run.id)
    e1 = next(iter(ctx.evidence))
    bad = _report(run.id, claims=[{"type": "exposed", "text": "x", "entities": [], "evidence_ids": ["E99"],
                                   "metric_refs": ["R-99.totals.late"]}])
    assert bad.is_error and "E99" in bad.content[0].text and "R-99" in bad.content[0].text
    off_path = _report(run.id, claims=[{"type": "depends_on", "text": "x", "entities": ["S-KANT-KUM-C"],
                                        "evidence_ids": [e1], "metric_refs": []}])
    assert off_path.is_error and "not on any cited evidence path" in off_path.content[0].text
    guard = _report(run.id, claims=[{"type": "late", "text": "S-NOPE-XYZ will fail", "entities": [],
                                     "evidence_ids": [], "metric_refs": []}])
    assert guard.is_error and "entity guard" in guard.content[0].text
    # Number guard: a valid metric_ref does not make any number in the prose true.
    ref = next(k for k, v in ctx.results.items() if isinstance(v, dict) and "projected_late" in v.get("totals", {}))
    late = ctx.results[ref]["totals"]["projected_late"]
    wrong = _report(run.id, claims=[{"type": "late", "text": f"{late + 986} orders will be late.", "entities": [],
                                     "evidence_ids": [], "metric_refs": [f"{ref}.totals.projected_late"]}])
    assert wrong.is_error and "number guard" in wrong.content[0].text and str(late + 986) in wrong.content[0].text
    right = _report(run.id, claims=[{"type": "late", "text": f"{late} orders will be late in tier 1 and tier-2 plants.",
                                     "entities": [], "evidence_ids": [], "metric_refs": [f"{ref}.totals.projected_late"]}])
    assert not right.is_error, right.content[0].text
    zero = _report(run.id, claims=[{"type": "late", "text": "0 orders will be late.", "entities": [],
                                    "evidence_ids": [], "metric_refs": [f"{ref}.totals.projected_late"]}])
    assert zero.is_error and "number guard" in zero.content[0].text


# ---------------------------------------------------------------------------
# HTTP API (dry run)
# ---------------------------------------------------------------------------

def test_http_run_streams_events_and_resumes_after_approval(monkeypatch):
    monkeypatch.setattr(settings, "world_graph_pristine", PRISTINE)
    monkeypatch.setattr(settings, "world_graph_live", "test:m6:api")
    from domino.api.main import app

    def wait(c, rid, statuses, timeout=60):
        t0 = time.time()
        while time.time() - t0 < timeout:
            s = c.get(f"/api/runs/{rid}").json()
            if s["status"] in statuses:
                return s
            time.sleep(0.2)
        raise AssertionError(f"run stuck in {s['status']}")

    with TestClient(app) as c:
        assert c.post("/api/world/reset").json()["graph"] == "test:m6:api"
        rid = c.post("/api/runs", json={"scenario": "monsoon", "dry_run": True}).json()["run_id"]
        snap = wait(c, rid, {"awaiting_approval", "failed"})
        assert snap["status"] == "awaiting_approval" and snap["pending_decision"]
        assert c.post(f"/api/runs/{rid}/approve", json={"approver": "web-test"}).status_code == 200
        assert c.post(f"/api/runs/{rid}/approve", json={"approver": "again"}).status_code == 409
        done = wait(c, rid, {"completed", "failed"})
        assert done["status"] == "completed" and done["report"]["outcome"] == "answered_with_path"
        with c.stream("GET", f"/api/runs/{rid}/events", headers={"Last-Event-ID": "0"}) as resp:
            body = "".join(resp.iter_text())
        events = [json.loads(line[6:]) for line in body.splitlines() if line.startswith("data: ")]
        kinds = [e["type"] for e in events]
        assert kinds[0] == "run.started" and "tool.called" in kinds and kinds[-1] == "run.completed"
        assert [e["seq"] for e in events] == sorted(e["seq"] for e in events)


def test_loop_stops_after_repeated_tool_errors():
    class Stubborn(ScriptedClient):
        def next_message(self, messages):
            self._absorb(messages)
            return self._call(("trace_exposure", {"incident_id": "INC-9999"}))

    run, _ = _run("monsoon", client=Stubborn("monsoon"))
    assert run.status == "failed" and "tool errors in a row" in run.error
    assert run.tool_calls == 3


def test_approval_on_a_changed_world_does_not_execute():
    run, client = _run("monsoon")
    copy_graph(PRISTINE, WORLD)  # someone resets the world while the plan waits for approval
    _resume(approve, run, client, "tester")
    assert get_context(run.id).receipt is None
    assert not run_query("upstream/purchase_orders", graph=WORLD)
    assert any(e["type"] == "approval.failed" for e in run.events)
