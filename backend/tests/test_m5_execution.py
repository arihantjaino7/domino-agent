"""M5: greedy allocator, sandboxes, executor and verifier V1-V9 (with negative tests).

DB tests use test:m5:* graphs only and drop them afterwards.
"""

import pytest

from domino.allocators.greedy import allocate, plan_hash, po_id, rate_needed
from domino.engines.executor import approve_decision, execute_plan, preflight, propose_decision
from domino.engines.incident import declare_incident
from domino.engines.sandbox import simulate_strategies
from domino.engines.upstream import Upstream
from domino.engines.verifier import verify_execution
from domino.graph.lifecycle import build_pristine, copy_graph, drop_graph
from domino.graph.run_query import run_query
from domino.seed.generator import generate
from domino.seed.motifs import MONSOON

BASE, MONS = "test:m5:demo", "test:m5:monsoon"
INC = MONSOON["incident"]["id"]


@pytest.fixture(scope="module")
def graphs():
    build_pristine(generate(42), BASE)
    copy_graph(BASE, MONS)
    inc = MONSOON["incident"]
    declare_incident(MONS, incident_id=inc["id"], kind=inc["kind"], title=inc["title"], alert_text=inc["alert_text"],
                     entity_ids=[inc["zone_id"]], capacity_factor=inc["capacity_factor"],
                     duration_days=inc["duration_days"])
    yield
    for g in (BASE, MONS, MONS + ":run"):
        drop_graph(g)


@pytest.fixture
def fresh(graphs):
    copy_graph(MONS, MONS + ":run")
    return MONS + ":run"


@pytest.fixture(scope="module")
def sim(graphs):
    return simulate_strategies(MONS, INC, run_id="t5")


# ---------------------------------------------------------------------------
# Allocator (pure)
# ---------------------------------------------------------------------------

def test_rate_needed_covers_every_checkpoint():
    # Arrival day 4: 70 units by day 10 needs 7*70/7 = 70/wk; 140 by day 17 needs 7*140/14 = 70/wk.
    assert rate_needed([(10, 70), (17, 70)], 4) == 70
    # 70 by day 6 (3 delivery days) needs ceil(7*70/3) = 164/wk.
    assert rate_needed([(6, 70), (17, 10)], 4) == 164


def _toy_problem(mode_rows):
    """Two sources (A, B) share one feeder F with room for 400 cells/wk; each pack needs 4 cells."""
    up = Upstream(
        feeds={"A": [{"site": "A", "src": "F", "component": "CELL", "cap_wk": 2000, "used_wk": 0}],
               "B": [{"site": "B", "src": "F", "component": "CELL", "cap_wk": 2000, "used_wk": 0}]},
        feeder={"F": {"capacity_wk": 400, "factor": 1.0, "used_out": 0, "available": 400, "room": 400}},
        source={"A": {"factor": 1.0, "reliability": 0.9}, "B": {"factor": 1.0, "reliability": 0.9}},
        ratio={("PACK", "CELL"): 4})
    cand = lambda site, price: {"site": site, "component": "PACK", "price_cents": price, "spare_wk": 100,  # noqa: E731
                                "reserved_wk": 0, "usable_wk": 100, "lead_days": 0, "transit_days": 0,
                                "air_transit_days": 1, "air_surcharge_cents": 1, "moq": 0, "tainted_paths": [],
                                "naive_only": False}
    orders = [{"order_id": f"O{i}", "plant": "P", "need_day": 6, "tier": "standard", "needs": {"PACK": 100}}
              for i in range(1, 3)]
    return {"budget_cents": 10**9, "orders": orders, "upstream": up,
            "candidates": {"PACK|P": [cand("A", 10), cand("B", 20)]}}


def test_graph_aware_mode_does_not_promise_shared_cells_twice():
    # Each order needs 100 packs by day 6 (7 delivery days) = 100/wk = 400 cells/wk. F has room for 400.
    p = _toy_problem(None)
    naive = allocate(p, "S1", "D-N", 0)
    domino = allocate(p, "S2", "D-G", 0)
    assert naive["protected_orders"] == ["O1", "O2"]        # A and B each take 100/wk: 800 cells promised
    assert domino["protected_orders"] == ["O1"]             # only 400 cells exist; O2 is rolled back
    assert [po["site_id"] for po in domino["pos"]] == ["A"]


def test_partly_coverable_order_is_rolled_back():
    p = _toy_problem(None)
    p["orders"] = [{"order_id": "BIG", "plant": "P", "need_day": 6, "tier": "standard", "needs": {"PACK": 250}}]
    plan = allocate(p, "S2", "D", 0)
    assert plan["pos"] == [] and plan["protected_orders"] == []


def test_po_ids_and_plan_hash_are_deterministic():
    assert po_id("D1", "S", "K", "P") == po_id("D1", "S", "K", "P") != po_id("D2", "S", "K", "P")
    p = _toy_problem(None)
    assert allocate(p, "S2", "D", 0)["plan_hash"] == allocate(p, "S2", "D", 0)["plan_hash"]


# ---------------------------------------------------------------------------
# Sandboxes on Monsoon
# ---------------------------------------------------------------------------

def test_baseline_protects_fewer_orders_than_domino_and_its_shortfall_shows(sim):
    by = {r["strategy"]: r for r in sim["strategies"]}
    assert by["S1"]["on_time"] < by["S4"]["on_time"]
    assert by["S0"]["on_time"] < by["S4"]["on_time"]
    assert by["S1"]["realized_rate_wk"] < by["S1"]["planned_rate_wk"]   # AmpereOne realizes 0
    assert by["S1"]["protected_but_late"]                                 # promised, but still late
    assert set(by["S1"]["verification"]["failed"]) >= {"V3", "V8"}
    assert "S-AMPR-JHB" in by["S1"]["suppliers"] and "S-AMPR-JHB" not in by["S4"]["suppliers"]


def test_domino_plan_passes_every_check_and_keeps_its_promises(sim):
    s4 = next(r for r in sim["strategies"] if r["strategy"] == "S4")
    assert s4["verification"]["ok"], s4["verification"]["failed"]
    assert s4["protected_but_late"] == []
    assert s4["realized_rate_wk"] == s4["planned_rate_wk"]
    assert "SO-1000" in sim["plans"]["S4"]["protected_orders"]           # Meridian, strategic
    assert s4["net_benefit_cents"] == s4["avoided_penalty_cents"] - s4["spend_cents"]


def test_sandboxes_leave_no_graphs_behind(sim):
    from domino.graph.client import get_db
    assert not [g for g in get_db().list_graphs() if g.startswith(("sandbox:", "scratch:flow:"))]


# ---------------------------------------------------------------------------
# Executor
# ---------------------------------------------------------------------------

def test_execute_twice_creates_no_duplicates(sim, fresh):
    plan = sim["plans"]["S4"]
    propose_decision(fresh, INC, plan)
    assert approve_decision(fresh, plan, "tester")["outcome"] == "ok"
    first = execute_plan(fresh, plan)
    assert first["outcome"] == "executed" and first["receipt_matches_plan"]
    count = lambda: len(run_query("upstream/purchase_orders", graph=fresh))  # noqa: E731
    n = count()
    assert n == len(plan["pos"])
    second = execute_plan(fresh, plan)
    assert second["outcome"] == "already_executed" and count() == n
    assert verify_execution(fresh, plan, first)["ok"]


def test_execution_requires_approval_of_the_same_plan(sim, fresh):
    plan = sim["plans"]["S4"]
    propose_decision(fresh, INC, plan)
    assert execute_plan(fresh, plan)["outcome"] == "not_approved"
    tampered = {**plan, "plan_hash": "0" * 16}
    assert approve_decision(fresh, tampered, "tester")["outcome"] == "not_approvable"


def test_approval_is_refused_when_the_world_moved(sim, fresh):
    plan = sim["plans"]["S4"]
    propose_decision(fresh, INC, plan)
    declare_incident(fresh, incident_id="INC-9", kind="fire", title="t", alert_text="t",
                     entity_ids=["S-BRVL-TXG"], capacity_factor=0.0, duration_days=3)  # bumps world_version
    assert approve_decision(fresh, plan, "tester")["outcome"] == "stale_world"


def test_preflight_rejects_unknown_order_and_wrong_edge(fresh):
    bad = _plan("D-BAD", [_po("D-BAD", "S-KANT-KUM-P", "BAT-4S", "PL-BAC", 10, [("SO-NOPE", 10, 22)]),
                          _po("D-BAD", "S-AMPR-JHB", "BAT-6S", "PL-PEN", 10, [("SO-1000", 10, 13)])])
    pf = preflight(fresh, bad)
    assert not pf["ok"]
    assert any("not in the graph" in p for p in pf["problems"])
    assert any("no approved CAN_SUPPLY" in p for p in pf["problems"])


# ---------------------------------------------------------------------------
# Verifier: bad plans must be caught (written straight to the graph, skipping the preflight)
# ---------------------------------------------------------------------------

def _po(decision, site, comp, plant, rate, allocs, mode="sea", price=4600, pid=None, first=None, qty=None):
    first = first if first is not None else min(a[2] for a in allocs)
    return {"id": pid or po_id(decision, site, comp, plant), "site_id": site, "component_id": comp, "plant_id": plant,
            "rate_wk": rate, "qty": qty if qty is not None else sum(a[1] for a in allocs), "mode": mode,
            "first_arrival_day": first, "unit_price_cents": price,
            "allocations": [{"order_id": o, "qty": q, "arrival_day": d} for o, q, d in allocs]}


def _plan(decision, pos, budget=10**9):
    plan = {"strategy": "SX", "name": "test", "decision_id": decision, "world_version": 1, "budget_cents": budget,
            "pos": pos}
    plan["plan_hash"] = plan_hash(plan)
    return plan


def _force(graph, plan):
    propose_decision(graph, INC, plan)
    approve_decision(graph, plan, "tester")
    rows = run_query("execute/write", {
        "decision_id": plan["decision_id"], "plan_hash": plan["plan_hash"], "world_version": plan["world_version"],
        "pos": [{**p, "order_ids": [a["order_id"] for a in p["allocations"]]} for p in plan["pos"]], "day": 0,
        "action_id": "ACT-T", "payload_json": "{}"}, ro=False, graph=graph)
    return verify_execution(graph, plan, None)["failed"], rows


# SO-1000: KB14 x450 at PL-BAC, need day 26 (Meridian).
def test_v1_over_spare(fresh):
    failed, _ = _force(fresh, _plan("D1", [_po("D1", "S-KANT-KUM-P", "BAT-4S", "PL-BAC", 400, [("SO-1000", 450, 22)])]))
    assert "V1" in failed


def test_v2_incompatible_part(fresh):
    failed, _ = _force(fresh, _plan("D2", [_po("D2", "S-NOVA-GUM", "DSP-14-HB", "PL-BAC", 100, [("SO-1000", 450, 9)])]))
    assert "V2" in failed


def test_v3_and_v8_tainted_source(fresh):
    failed, _ = _force(fresh, _plan("D3", [_po("D3", "S-AMPR-JHB", "BAT-4S", "PL-BAC", 300, [("SO-1000", 450, 13)])]))
    assert {"V3", "V8"} <= set(failed)


def test_v4_late_arrival(fresh):
    failed, _ = _force(fresh, _plan("D4", [_po("D4", "S-KANT-KUM-P", "BAT-4S", "PL-BAC", 100, [("SO-1000", 450, 30)])]))
    assert "V4" in failed


def test_v5_over_budget(fresh):
    failed, _ = _force(fresh, _plan("D5", [_po("D5", "S-KANT-KUM-P", "BAT-4S", "PL-BAC", 200, [("SO-1000", 450, 22)])],
                                    budget=100))
    assert "V5" in failed


def test_v6_duplicate_po_for_same_source(fresh):
    a = _po("D6", "S-KANT-KUM-P", "BAT-4S", "PL-BAC", 100, [("SO-1000", 200, 22)], pid="PO-DUP-A")
    b = _po("D6", "S-KANT-KUM-P", "BAT-4S", "PL-BAC", 100, [("SO-1000", 250, 22)], pid="PO-DUP-B")
    failed, _ = _force(fresh, _plan("D6", [a, b]))
    assert "V6" in failed


def test_v7_half_covered_order(fresh):
    failed, _ = _force(fresh, _plan("D7", [_po("D7", "S-KANT-KUM-P", "BAT-4S", "PL-BAC", 100, [("SO-1000", 100, 22)])]))
    assert "V7" in failed


def test_v9_receipt_mismatch(sim, fresh):
    plan = sim["plans"]["S4"]
    fake = {"outcome": "executed", "pos_created": len(plan["pos"]), "protects_created": 1}
    assert "V9" in verify_execution(fresh, plan, fake)["failed"]
