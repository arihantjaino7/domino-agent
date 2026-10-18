"""Memory that changes plans: delivery outcomes -> memory facts -> learned reliability -> the next plan.

Hand-computed on tests/fixtures/tiny_world.py:learning_world (every value is worked out in its docstring).
Uses test:m12:* graphs, so the real `memory` and `memory:dryrun` graphs are never touched.
"""

import datetime as dt

import pytest
from fastapi.testclient import TestClient

from domino.agent import tools as T
from domino.agent.context import new_context
from domino.config import settings
from domino.engines import delivery
from domino.engines.executor import approve_decision, execute_plan
from domino.graph.lifecycle import build_pristine, copy_graph, drop_graph
from domino.graph.run_query import run_query
from tests.fixtures.tiny_world import learning_world

PRISTINE, WORLD, MEM, DEMO = "test:m12:pristine", "test:m12:world", "test:m12:memory", "test:m12:dryrun"
TODAY = dt.date.today().isoformat()


@pytest.fixture(scope="module", autouse=True)
def graphs():
    build_pristine(learning_world(), PRISTINE)
    yield
    for g in (PRISTINE, WORLD, MEM, DEMO):
        drop_graph(g)


@pytest.fixture(autouse=True)
def fresh(monkeypatch):
    for g in (MEM, DEMO):
        drop_graph(g)
    copy_graph(PRISTINE, WORLD)
    monkeypatch.setattr(settings, "world_graph_live", WORLD)
    monkeypatch.setattr(settings, "memory_graph", MEM)
    monkeypatch.setattr(settings, "memory_graph_dryrun", DEMO)


def _incident_and_plan(run_id: str, memory_graph: str = MEM):
    ctx = new_context(run_id, WORLD)
    ctx.memory_graph = memory_graph
    T.declare_incident(ctx, ["Z-T"], "flood", "Test basin flood", duration_days=28)
    sim = T.simulate_strategies(ctx)
    return ctx, sim


def _execute_and_verify(ctx, strategy: str = "S4"):
    sub = T.submit_plan_for_approval(ctx, strategy, "test plan")
    assert approve_decision(WORLD, ctx.pending, "tester")["outcome"] == "ok"
    ctx.receipt = execute_plan(WORLD, ctx.pending)
    assert ctx.receipt["outcome"] == "executed"
    T.verify_execution(ctx, sub["decision_id"])
    return sub


# ---------------------------------------------------------------------------
# The outcome model and the learning rule (pure)
# ---------------------------------------------------------------------------

def test_po_outcome_hand_computed():
    full = {"po_id": "PO-1", "reliability": 0.95, "reserved_wk": 70, "spare_wk": 70, "first_arrival_day": 20}
    # (1 - 0.95) + (70/70 - 0.6) = 0.45; 20 x 0.45 = 9 exactly, so the seeded jitter in [0, 1) cannot change it
    assert [delivery.po_outcome(full, seed)["days_late"] for seed in (0, 1, 42, 99)] == [9, 9, 9, 9]
    assert delivery.po_outcome(full, 42)["surge_pct"] == 100
    calm = {"po_id": "PO-2", "reliability": 0.9, "reserved_wk": 60, "spare_wk": 100, "first_arrival_day": 30}
    assert delivery.po_outcome(calm, 7)["days_late"] == 3  # surge 60% adds nothing: 30 x 0.10 = 3
    # Same PO and seed, same answer; the jitter only rounds the fractional part.
    odd = {**calm, "first_arrival_day": 5}  # 5 x 0.10 = 0.5 -> 0 or 1 day
    assert delivery.po_outcome(odd, 42) == delivery.po_outcome(odd, 42)
    assert delivery.po_outcome(odd, 42)["days_late"] in (0, 1)


def test_learned_reliability_hand_computed():
    assert delivery.learned_reliability(0.95, [{"days_late": 9}]) == 0.65          # (0.95 + 5/14) / 2
    assert delivery.learned_reliability(0.98, [{"days_late": 9}, {"days_late": 3}]) == 0.71  # (0.98 + 5/14 + 11/14) / 3
    assert delivery.learned_reliability(0.9, [{"days_late": 0}]) == 0.95            # on time pulls it up
    assert delivery.learned_reliability(0.9, [{"days_late": 30}]) == 0.45           # two weeks or more scores 0
    assert delivery.learned_reliability(None, [{"days_late": 0}]) == 0.95           # no operator: the 0.9 fallback


# ---------------------------------------------------------------------------
# Fast-forward: outcomes written to the world, then to memory
# ---------------------------------------------------------------------------

def test_first_plan_uses_the_seeded_favourite():
    ctx, sim = _incident_and_plan("t12-first")
    s4 = ctx.plans["S4"]
    assert [(p["site_id"], p["rate_wk"], p["qty"], p["first_arrival_day"]) for p in s4["pos"]] == [("S-A", 70, 110, 20)]
    assert "learned_reliability" not in sim and "learned_reliability" not in s4  # nothing learned yet


def test_fast_forward_writes_outcomes_and_memory_facts():
    ctx, _ = _incident_and_plan("t12-ff")
    _execute_and_verify(ctx)
    po_id = ctx.pending["pos"][0]["id"]
    res = T.record_delivery(ctx)
    assert res["outcome"] == "delivered" and res["receipt_matches"]
    assert res["day"] == 42  # the last unit arrives on day 39, before the 42-day horizon
    [po] = res["pos"]
    assert (po["po_id"], po["status"], po["days_late"], po["arrived_day"], po["received_day"], po["surge_pct"]) == \
        (po_id, "delayed", 9, 29, 39, 100)
    assert res["orders"] == [{"id": "SO-L1", "status": "fulfilled_late", "delivered_day": 33, "need_day": 30,
                              "late_days": 3, "customer": "CU-N", "tier": "standard"}]
    # The world: PO delayed, order fulfilled (late), spare released, world version bumped.
    rows = T.get_delivery_outcomes(ctx)["delivered_pos"]
    assert rows[0]["status"] == "delayed" and rows[0]["days_late"] == 9 and rows[0]["orders"]["fulfilled_late"] == 1
    assert run_query("upstream/purchase_orders", graph=WORLD) == []  # nothing is still on its way
    # Memory: one dated fact on S-A, with the PO as evidence, and the reliability learned from it.
    facts = delivery.memory_deliveries(MEM)
    assert list(facts) == ["S-A"]
    assert (facts["S-A"][0]["po_id"], facts["S-A"][0]["days_late"], facts["S-A"][0]["learned_on"]) == (po_id, 9, TODAY)
    [learned] = res["learned_reliability"]
    assert (learned["seeded"], learned["learned"], learned["deliveries"], learned["on_time"]) == (0.95, 0.65, 1, 0)
    assert learned["text"] == f"S-A reliability 0.95 -> 0.65, learned on {TODAY} from 1 delivery: {po_id} 9 days late"
    with pytest.raises(ValueError, match="already delivered"):
        T.record_delivery(ctx)


def test_fast_forward_needs_an_executed_and_verified_plan():
    ctx, _ = _incident_and_plan("t12-early")
    with pytest.raises(ValueError, match="nothing was executed"):
        T.record_delivery(ctx)
    T.submit_plan_for_approval(ctx, "S4", "test plan")
    approve_decision(WORLD, ctx.pending, "tester")
    ctx.receipt = execute_plan(WORLD, ctx.pending)
    with pytest.raises(ValueError, match="verify the execution first"):
        T.record_delivery(ctx)


# ---------------------------------------------------------------------------
# The key loop: incident -> execute -> fast-forward -> reset -> the next plan picks differently
# ---------------------------------------------------------------------------

def test_after_a_reset_the_next_plan_prefers_the_other_source_and_says_why():
    ctx, _ = _incident_and_plan("t12-loop-1")
    _execute_and_verify(ctx)
    po_id = ctx.pending["pos"][0]["id"]
    T.record_delivery(ctx)

    copy_graph(PRISTINE, WORLD)  # world reset: memory is a separate graph and survives it
    ctx2, sim = _incident_and_plan("t12-loop-2")
    s4 = ctx2.plans["S4"]
    assert [(p["site_id"], p["rate_wk"], p["qty"]) for p in s4["pos"]] == [("S-B", 70, 110)]
    why = f"S-A reliability 0.95 -> 0.65, learned on {TODAY} from 1 delivery: {po_id} 9 days late"
    assert [r["text"] for r in s4["learned_reliability"]] == [why]
    assert s4["learned_reliability"][0]["in_plan"] is False
    assert [c["text"] for c in s4["ranking_changes"]] == [
        "C-MOD for PL-L: S-B is now tried first (reliability-weighted cost $1.16 vs $1.35 per unit for S-A, "
        "which came first with seeded reliability)"]
    # The tool results say it too: simulate_strategies, the plan sent for approval, and recall_history.
    assert sim["learned_reliability"][0]["why"] == why and sim["ranking_changes"] == [c["text"] for c in s4["ranking_changes"]]
    assert T.submit_plan_for_approval(ctx2, "S4", "learned plan")["learned_reliability"] == [why]
    recalled = T.recall_history(ctx2, ["S-A"])
    assert recalled["outcome"] == "answered_from_memory"
    assert recalled["learned_reliability"][0]["learned"] == 0.65
    # Only the reliability-ranked preset changes; the price-only plan still buys from S-A.
    assert [p["site_id"] for p in ctx2.plans["S2"]["pos"]] == ["S-A"]


def test_simulation_is_deterministic_given_world_and_memory():
    ctx, _ = _incident_and_plan("t12-det-1")
    _execute_and_verify(ctx)
    T.record_delivery(ctx)
    hashes = []
    for i in range(2):
        copy_graph(PRISTINE, WORLD)
        c, _ = _incident_and_plan(f"t12-det-{i + 2}")
        hashes.append(c.plans["S4"]["plan_hash"])
    assert hashes[0] == hashes[1]


def test_scripted_runs_learn_in_their_own_memory_graph():
    ctx, _ = _incident_and_plan("t12-demo", memory_graph=DEMO)
    _execute_and_verify(ctx)
    T.record_delivery(ctx)
    assert list(delivery.memory_deliveries(DEMO)) == ["S-A"] and delivery.memory_deliveries(MEM) == {}
    copy_graph(PRISTINE, WORLD)
    real, _ = _incident_and_plan("t12-real")  # a real run reads `memory`, which learned nothing
    assert [p["site_id"] for p in real.plans["S4"]["pos"]] == ["S-A"]


# ---------------------------------------------------------------------------
# HTTP: the war room's button and what the views read
# ---------------------------------------------------------------------------

def test_http_deliver_and_memory_and_deliveries():
    from domino.agent import external
    from domino.agent.loop import AgentRun
    from domino.api.main import app

    ctx, _ = _incident_and_plan("t12-http")
    _execute_and_verify(ctx)
    run = external.register(AgentRun(id="t12-http", scenario="custom", alert_text="", graph=WORLD, status="completed"))
    with TestClient(app) as c:
        r = c.post("/api/runs/t12-http/deliver")
        assert r.status_code == 200, r.text
        ev = r.json()["event"]
        assert ev["type"] == "delivery.completed" and ev["data"]["counts"] == \
            {"fulfilled": 0, "fulfilled_late": 1, "unfulfilled": 0}
        assert run.events[-1]["seq"] == ev["seq"]
        assert c.post("/api/runs/t12-http/deliver").status_code == 409  # delivered once
        assert c.post("/api/runs/nope/deliver").status_code == 404
        mem = c.get("/api/memory").json()
        assert [(r["site"], r["seeded"], r["learned"]) for r in mem["reliability"]] == [("S-A", 0.95, 0.65)]
        assert c.get("/api/memory", params={"source": "demo"}).json()["reliability"] == []
        d = c.get("/api/deliveries").json()
        assert [(p["po_id"], p["status"], p["days_late"]) for p in d["pos"]] == [(ctx.pending["pos"][0]["id"], "delayed", 9)]
        assert d["pos"][0]["orders"][0]["status"] == "fulfilled_late"
    external.RUNS.pop("t12-http", None)
