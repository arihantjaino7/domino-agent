"""M11 hardening (overnight audit): rejection and re-planning, approval failures the agent can see,
metric refs by id, memory that adds instead of overwriting, and honest rejection reasons.

Uses test:m11:* graphs only (seed-42 world and the tiny world); no API calls.
"""

import pytest

from domino.agent import memory
from domino.agent import tools as T
from domino.agent.context import new_context
from domino.config import settings
from domino.engines.alternatives import find_alternatives
from domino.engines.executor import approve_decision, execute_plan
from domino.graph.lifecycle import build_pristine, copy_graph, drop_graph
from domino.graph.run_query import run_query
from domino.seed.generator import generate
from tests.fixtures.tiny_world import tiny_world

PRISTINE, WORLD, MEM, TINY = "test:m11:pristine", "test:m11:world", "test:m11:memory", "test:m11:tiny"


@pytest.fixture(scope="module", autouse=True)
def graphs():
    build_pristine(generate(42), PRISTINE)
    yield
    for g in (PRISTINE, WORLD, MEM, TINY):
        drop_graph(g)


@pytest.fixture
def ctx(monkeypatch, request):
    monkeypatch.setattr(settings, "memory_graph", MEM)
    copy_graph(PRISTINE, WORLD)
    c = new_context(f"t-m11-{request.node.name}"[:60], WORLD, alert_text="Monsoon flooding in the test")
    T.declare_incident(c, ["Z-CPB"], "flood", "Monsoon", 28)
    return c


def _status(decision_id):
    return run_query("decision/get", {"decision_id": decision_id}, graph=WORLD)[0]


# ---------------------------------------------------------------------------
# Rejection, then re-planning
# ---------------------------------------------------------------------------

def test_rejection_is_recorded_in_the_graph_and_a_new_plan_for_the_same_strategy_gets_a_revision(ctx):
    T.simulate_strategies(ctx)
    first = T.submit_plan_for_approval(ctx, "S4", "best in sandbox")
    assert first["decision_id"].endswith("-S4-v1")
    T.record_rejection(ctx, "too expensive, keep it under $120k", rejected_by="tester")
    row = _status(first["decision_id"])
    assert row["status"] == "rejected" and row["feedback"].startswith("too expensive")

    # The same purchases again are refused: the human already said no to exactly this plan.
    with pytest.raises(T.ToolInputError, match="already rejected exactly this plan"):
        T.submit_plan_for_approval(ctx, "S4", "same again")

    # A re-simulated S4 under the human's budget is a different plan: it gets its own decision id.
    T.simulate_strategies(ctx, budget_usd=120_000)
    second = T.submit_plan_for_approval(ctx, "S4", "within the budget the human gave")
    assert second["decision_id"] == first["decision_id"] + "-r2"
    assert second["spend_usd"] <= 120_000
    assert T.get_decision_status(ctx, first["decision_id"])["status"] == "rejected"
    assert T.get_decision_status(ctx, second["decision_id"])["status"] == "awaiting_approval"

    # The revision is a normal decision: a human can approve it and the executor commits it.
    plan = ctx.pending
    assert approve_decision(WORLD, plan, "tester")["outcome"] == "ok"
    receipt = execute_plan(WORLD, plan)
    assert receipt["outcome"] == "executed" and receipt["receipt_matches_plan"]
    assert {p["po_id"] for p in run_query("upstream/purchase_orders", graph=WORLD)} == {p["id"] for p in plan["pos"]}


def test_only_one_plan_is_open_at_a_time(ctx):
    T.simulate_strategies(ctx)
    T.submit_plan_for_approval(ctx, "S4", "x")
    with pytest.raises(T.ToolInputError, match="already waiting for the human"):
        T.submit_plan_for_approval(ctx, "S3", "y")


def test_a_failed_approval_is_reported_instead_of_still_waiting(ctx):
    T.simulate_strategies(ctx)
    sub = T.submit_plan_for_approval(ctx, "S4", "x")
    T.declare_incident(ctx, ["S-LMVU-SUZ"], "fire", "Second disruption", 14)  # the world moves on
    approval = approve_decision(WORLD, ctx.pending, "tester")
    assert approval["outcome"] == "stale_world"
    T.record_approval_failure(ctx, approval)
    status = T.get_decision_status(ctx, sub["decision_id"])
    assert status["status"] == "approval_failed" and "stale_world" in status["next"]
    assert not run_query("upstream/purchase_orders", graph=WORLD)


# ---------------------------------------------------------------------------
# Metric refs can name list items by id
# ---------------------------------------------------------------------------

def test_metric_refs_can_pick_a_strategy_by_its_id(ctx):
    sim = T.simulate_strategies(ctx)
    s4 = next(s for s in sim["strategies"] if s["strategy_id"] == "S4")
    ref = sim["result_ref"]
    claim = {"type": "protected", "text": f"S4 spends ${s4['spend_usd']:,} and leaves {s4['late']} order late.",
             "entities": [], "evidence_ids": [], "metric_refs": [f"{ref}.strategies.S4"]}
    T.submit_incident_report(ctx, "Plan S4 compared in the sandbox.", "answered_with_path", [claim])
    assert ctx.report is not None

    ctx.report = None
    bad = {**claim, "metric_refs": [f"{ref}.strategies.S9.spend_usd"]}
    with pytest.raises(T.ToolInputError, match=r"strategies is a list of 5 items"):
        T.submit_incident_report(ctx, "x", "answered_with_path", [bad])


# ---------------------------------------------------------------------------
# Memory adds; it does not overwrite
# ---------------------------------------------------------------------------

def test_two_runs_with_the_same_world_incident_id_are_both_remembered(ctx, monkeypatch):
    drop_graph(MEM)
    lesson = {"text": "VoltCell feeds both battery suppliers.", "entity_ids": ["S-VOLT-AYU"], "evidence_ids": []}
    first = T.record_lessons(ctx, "INC-0001", [lesson])
    again = T.record_lessons(ctx, "INC-0001", [lesson])          # the agent sends the same lesson twice
    assert first["memory_incident_id"] == again["memory_incident_id"] == "MI-0001"
    assert again["lesson_ids"] == []                             # stored once

    copy_graph(PRISTINE, WORLD)                                   # world reset: INC-0001 again
    later = new_context("t-m11-later", WORLD, alert_text="Monsoon flooding again")
    T.declare_incident(later, ["Z-CPB"], "flood", "Monsoon", 28)
    second = T.record_lessons(later, "INC-0001", [{**lesson, "text": "AmpereOne is not an independent backup."}])
    assert second["memory_incident_id"] == "MI-0002"

    incidents = memory.list_incidents(MEM)
    assert [(i["id"], i["incident_id"]) for i in incidents] == [("MI-0002", "INC-0001"), ("MI-0001", "INC-0001")]
    texts = sorted(l["text"] for l in memory.list_lessons(MEM))
    assert texts == ["AmpereOne is not an independent backup.", "VoltCell feeds both battery suppliers."]
    recalled = memory.recall_history(["S-VOLT-AYU"], graph=MEM)[0]
    assert recalled["name"] == "VoltCell Energy Ayutthaya" and len(recalled["incidents"]) == 2


def test_an_id_only_name_never_replaces_a_real_name_in_memory():
    drop_graph(MEM)
    memory.record_incident({"id": "MI-0001", "title": "a", "outcome": "recorded"},
                           [{"id": "S-X", "kind": "Site", "name": "Real Name", "role": "involved"}], graph=MEM)
    memory.record_incident({"id": "MI-0002", "title": "b", "outcome": "recorded"},
                           [{"id": "S-X", "kind": "entity", "name": "S-X", "role": "involved"}], graph=MEM)
    assert memory.recall_history(["S-X"], graph=MEM)[0]["name"] == "Real Name"


# ---------------------------------------------------------------------------
# Rejection reasons say which limit is at zero
# ---------------------------------------------------------------------------

def test_a_fully_reserved_backup_is_rejected_for_its_spare_not_for_its_inputs():
    w = tiny_world()
    w.edges_of("CAN_SUPPLY", src="S-ALT")[0]["props"]["reserved_wk"] = 50   # all 50/wk of spare already committed
    build_pristine(w, TINY)
    alts = find_alternatives(TINY, "C-PACK", "PL-X")
    r = next(x for x in alts["rejected"] if x["site"] == "S-ALT")
    assert r["reason"] == "no_remaining_capacity"
    assert "already reserved" in r["detail"] and "disrupted" not in r["detail"]


# ---------------------------------------------------------------------------
# HTTP: a rejection is bound to the decision the human saw
# ---------------------------------------------------------------------------

def test_http_reject_checks_the_decision_and_records_it(monkeypatch):
    import time

    from fastapi.testclient import TestClient

    monkeypatch.setattr(settings, "world_graph_pristine", PRISTINE)
    monkeypatch.setattr(settings, "world_graph_live", WORLD)
    monkeypatch.setattr(settings, "memory_graph_dryrun", MEM)
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
        c.post("/api/world/reset")
        rid = c.post("/api/runs", json={"scenario": "monsoon", "dry_run": True}).json()["run_id"]
        first = wait(c, rid, {"awaiting_approval", "failed"})["pending_decision"]
        stale = c.post(f"/api/runs/{rid}/reject", json={"feedback": "no", "decision_id": "DEC-SOMETHING-ELSE"})
        assert stale.status_code == 409
        assert c.post(f"/api/runs/{rid}/reject", json={"feedback": "use max service", "decision_id": first}).status_code == 200
        second = wait(c, rid, {"awaiting_approval", "failed"})
        assert second["status"] == "awaiting_approval" and second["pending_decision"] != first
        row = _status(first)
        assert row["status"] == "rejected" and row["feedback"] == "use max service"

def test_a_number_guard_error_says_where_the_value_is(ctx):
    sim = T.simulate_strategies(ctx)
    s4 = next(s for s in sim["strategies"] if s["strategy_id"] == "S4")
    claim = {"type": "protected", "text": "Plan S4 was compared in the sandbox.", "entities": [], "evidence_ids": [],
             "metric_refs": [f"{sim['result_ref']}.strategies.S4.spend_usd"]}
    headline = f"S4 protects {s4['protected_projected']} orders (projected)."
    with pytest.raises(T.ToolInputError) as err:
        T.submit_incident_report(ctx, headline, "answered_with_path", [claim])
    msg = str(err.value)
    hint = f"{sim['result_ref']}.strategies.S4.protected_projected"
    assert "headline states 12" in msg and hint in msg

    # Following the hint makes the same headline pass.
    T.submit_incident_report(ctx, headline, "answered_with_path", [{**claim, "metric_refs": claim["metric_refs"] + [hint]}])
    assert ctx.report["headline"] == headline


def test_a_number_no_tool_returned_is_called_out():
    c = new_context("t-m11-nowhere", WORLD)
    c.add_result("x", {"totals": {"late": 3}}, {})
    with pytest.raises(T.ToolInputError, match="no tool result in this run has that value"):
        T.submit_incident_report(c, "h", "answered_with_path", [{"type": "late", "text": "987 orders are late.",
                                                                 "entities": [], "evidence_ids": [],
                                                                 "metric_refs": ["R-01.totals.late"]}])

# ---------------------------------------------------------------------------
# SSE: two open tabs both get every event promptly
# ---------------------------------------------------------------------------

def test_two_sse_readers_both_get_new_events_without_waiting_for_the_timeout():
    import asyncio
    import time

    from domino.agent import external
    from domino.agent.loop import AgentRun, emit
    from domino.api.runs import run_events

    class Req:
        headers: dict = {}

        async def is_disconnected(self):
            return False

    async def go():
        run = external.register(AgentRun(id="t-m11-sse", scenario="x", alert_text="", graph=WORLD, status="running"))
        emit(run, "run.started", {})
        streams = [(await run_events(run.id, Req())).body_iterator for _ in range(2)]
        firsts = await asyncio.gather(*(s.__anext__() for s in streams))   # both drain the backlog
        assert all(f["event"] == "run.started" for f in firsts)
        waiting = [asyncio.ensure_future(s.__anext__()) for s in streams]  # both now wait for the next event
        await asyncio.sleep(0.05)
        t0 = time.monotonic()
        emit(run, "tool.called", {"tool": "trace_exposure"})
        got = await asyncio.wait_for(asyncio.gather(*waiting), timeout=2)  # far below the 15 s fallback
        assert [g["event"] for g in got] == ["tool.called", "tool.called"]
        assert time.monotonic() - t0 < 1
        run.status = "completed"
        emit(run, "run.completed", {})
        for s in streams:
            assert (await s.__anext__())["event"] == "run.completed"
            await s.aclose()
        assert run.listeners == [run.listeners[0]]                         # readers removed their listeners
        external.RUNS.pop(run.id, None)

    asyncio.run(go())

def test_a_lesson_without_entity_ids_is_refused(ctx):
    drop_graph(MEM)
    for bad in ({"entity_id": "S-VOLT-AYU", "text": "x"}, {"text": "x", "entity_ids": []}, "just text"):
        with pytest.raises(T.ToolInputError, match="never be recalled"):
            T.record_lessons(ctx, "INC-0001", [bad])
    assert memory.list_lessons(MEM) == []