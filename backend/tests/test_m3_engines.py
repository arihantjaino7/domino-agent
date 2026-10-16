"""M3 engines: incident declaration, exposure trace, shortage projection.

Expected values are worked out by hand in tests/fixtures/tiny_world.py.
DB tests use test:m3:* graphs only and drop them afterwards.
"""

from fractions import Fraction

import pytest

from domino.engines.exposure import trace_exposure
from domino.engines.incident import declare_incident
from domino.engines.shortage import Availability, project, project_shortages, site_availability
from domino.graph.lifecycle import build_pristine, copy_graph, drop_graph
from domino.seed.generator import generate
from domino.seed.motifs import MONSOON
from tests.fixtures.tiny_world import shared_line_world, tiny_world

TINY, SHARED, DEMO = "test:m3:tiny", "test:m3:shared", "test:m3:demo"


def _declare(graph, entity, factor=0.0, days=14, incident_id="INC-T"):
    return declare_incident(graph, incident_id=incident_id, kind="flood", title="t", alert_text="t",
                            entity_ids=[entity], capacity_factor=factor, duration_days=days)


@pytest.fixture(scope="module")
def pristine_graphs():
    build_pristine(tiny_world(), TINY)
    build_pristine(shared_line_world(), SHARED)
    build_pristine(generate(42), DEMO)
    yield
    for g in (TINY, SHARED, DEMO):
        drop_graph(g)
        drop_graph(g + ":run")


@pytest.fixture
def fresh(pristine_graphs):
    """Return a function giving a fresh writable copy of a pristine test graph."""
    def make(src):
        copy_graph(src, src + ":run")
        return src + ":run"
    return make


# ---------------------------------------------------------------------------
# Availability (pure): the adversarial cases
# ---------------------------------------------------------------------------

def _sites(**factors):
    return {s: {"factor": f, "disrupted_until": 20 if f < 1 else None, "input_buffer_days": 0}
            for s, f in factors.items()}


def test_interchangeable_sources_share_by_used_volume():
    sites = _sites(F1=0.0, F2=1.0, T=1.0)
    feeds = [{"src": "F1", "dst": "T", "component": "CELL", "used_wk": 100, "cap_wk": 100},
             {"src": "F2", "dst": "T", "component": "CELL", "used_wk": 100, "cap_wk": 100}]
    assert site_availability(sites, feeds)["T"].fraction == Fraction(1, 2)


def test_complementary_inputs_take_the_minimum_not_the_average():
    # Two healthy cell fabs cannot make up for the only BMS source being down.
    sites = _sites(F1=1.0, F2=1.0, B1=0.0, T=1.0)
    feeds = [{"src": "F1", "dst": "T", "component": "CELL", "used_wk": 100, "cap_wk": 100},
             {"src": "F2", "dst": "T", "component": "CELL", "used_wk": 100, "cap_wk": 100},
             {"src": "B1", "dst": "T", "component": "BMS", "used_wk": 50, "cap_wk": 50}]
    assert site_availability(sites, feeds)["T"].fraction == 0  # a weighted average would say 0.8


def test_partly_exposed_supplier_keeps_its_healthy_share():
    # F1 runs at half rate (factor 0.5) and carries 3/4 of T's cells: (300*0.5 + 100) / 400 = 5/8.
    sites = _sites(F1=0.5, F2=1.0, T=1.0)
    feeds = [{"src": "F1", "dst": "T", "component": "CELL", "used_wk": 300, "cap_wk": 300},
             {"src": "F2", "dst": "T", "component": "CELL", "used_wk": 100, "cap_wk": 100}]
    assert site_availability(sites, feeds)["T"].fraction == Fraction(5, 8)


def test_input_buffers_add_up_tier_by_tier():
    sites = {"R": {"factor": 0.0, "disrupted_until": 10, "input_buffer_days": 0},
             "M": {"factor": 1.0, "input_buffer_days": 4},
             "T": {"factor": 1.0, "input_buffer_days": 3}}
    feeds = [{"src": "R", "dst": "M", "component": "RAW", "used_wk": 10, "cap_wk": 10},
             {"src": "M", "dst": "T", "component": "SUB", "used_wk": 10, "cap_wk": 10}]
    av = site_availability(sites, feeds)
    assert av["T"] == Availability(Fraction(0), onset=7, restore=10)


def test_order_needing_two_parts_consumes_nothing_while_one_is_short():
    inputs = {
        "horizon": 3, "sites": {}, "feeds": [],
        "supply": [],
        "stock": [{"plant": "P", "component": "X", "on_hand": 10}, {"plant": "P", "component": "Y", "on_hand": 1}],
        "order_rows": [
            {"order_id": "O1", "plant": "P", "product": "PR", "need_day": 1, "qty": 5, "component": c, "units": 5,
             "customer": "C", "tier": "standard", "penalty_cents": 1, "value_cents": 1} for c in ("X", "Y")],
    }
    res = project(inputs)
    x = next(c for c in res["components"] if c["component"] == "X")
    assert x["stock_curve"] == [10, 10, 10, 10]
    assert res["orders"][0]["beyond_horizon"] is True and res["orders"][0]["late_days"] == 3


# ---------------------------------------------------------------------------
# Tiny world through the graph
# ---------------------------------------------------------------------------

def test_tiny_pristine_has_no_exposure_and_no_late(pristine_graphs):
    res = project_shortages(TINY)
    assert res["totals"]["exposed"] == 0 and res["totals"]["projected_late"] == 0


def test_unknown_entity_is_refused(fresh):
    g = fresh(TINY)
    assert _declare(g, "Z-NOPE")["outcome"] == "unknown_entity"


def test_tiny_incident_expands_zone_to_its_site(fresh):
    g = fresh(TINY)
    d = _declare(g, "Z-T")
    assert d["outcome"] == "ok" and d["site_ids"] == ["S-UP"] and d["end_day"] == 14 and d["world_version"] == 1


def test_tiny_exposure_tier1_view_vs_multi_tier(fresh):
    g = fresh(TINY)
    _declare(g, "Z-T")
    exp = trace_exposure(g, "INC-T")
    assert exp["tier1_view"]["directly_affected_tier1"] == 0
    assert exp["multi_tier"]["tier1_sites"] == [{"site": "S-T1", "via": ["S-UP"]}]
    assert [e["path"] for e in exp["evidence"]] == [["S-UP", "S-T1", "PL-X"]]
    assert exp["evidence"][0]["orders"] == ["SO-A1", "SO-A2", "SO-A3", "SO-A4"]
    assert exp["hop_depth"]["S-UP"] == 0 and exp["hop_depth"]["S-T1"] == 1 and exp["hop_depth"]["PL-X"] == 2
    assert exp["hop_depth"]["SO-A3"] == 3
    assert exp["shared_upstream"] == [{"site": "S-UP", "operator": "Test Supplier",
                                       "dependents": ["S-ALT", "S-T1"], "fan_out": 2}]


def test_tiny_shortage_matches_hand_calculation(fresh):
    g = fresh(TINY)
    _declare(g, "Z-T")
    res = project_shortages(g)
    by = {o["order_id"]: o for o in res["orders"]}
    assert res["sites"]["S-T1"] == {"fraction": "3/10", "onset": 3, "restore": 14}
    assert (by["SO-A1"]["ready_day"], by["SO-A1"]["status"]) == (3, "exposed_covered")
    assert (by["SO-A2"]["ready_day"], by["SO-A2"]["status"]) == (6, "exposed_covered")
    assert (by["SO-A3"]["ready_day"], by["SO-A3"]["late_days"], by["SO-A3"]["status"]) == (14, 4, "projected_late")
    assert by["SO-A3"]["penalty_cents"] == 4 * 1_000
    assert (by["SO-A4"]["ready_day"], by["SO-A4"]["status"]) == (20, "exposed_covered")
    assert (by["SO-B1"]["exposed"], by["SO-B1"]["status"]) == (False, "on_time")
    pack = next(c for c in res["components"] if c["component"] == "C-PACK")
    assert pack["stockout_day"] == 10
    assert pack["stock_curve"][:6] == [40, 50, 60, 50, 60, 63]
    assert res["totals"] == {"orders": 5, "exposed": 4, "exposed_covered": 3, "projected_late": 1,
                             "late_beyond_horizon": 0, "revenue_at_risk_cents": 50_000,
                             "penalty_exposure_cents": 4_000}


def test_tiny_short_horizon_marks_late_beyond_horizon(fresh):
    g = fresh(TINY)
    _declare(g, "Z-T")
    res = project_shortages(g, horizon=12)
    by = {o["order_id"]: o for o in res["orders"]}
    assert "SO-A4" not in by  # need day 20 is outside the horizon
    assert by["SO-A3"]["beyond_horizon"] is True and by["SO-A3"]["late_days"] == 3  # at least 13 - 10


def test_shared_cell_line_exposes_both_components(fresh):
    g = fresh(SHARED)
    _declare(g, "Z-T", factor=0.5, days=30)
    exp = trace_exposure(g, "INC-T")
    assert exp["shared_upstream"][0]["site"] == "S-FAB" and exp["shared_upstream"][0]["fan_out"] == 2
    assert sorted(p["components"] for p in exp["multi_tier"]["plants"]) == [["C-4S", "C-6S"]]
    res = project_shortages(g)
    by = {o["order_id"]: o for o in res["orders"]}
    assert res["sites"]["S-L4"]["fraction"] == "1/2" and res["sites"]["S-L6"]["fraction"] == "1/2"
    assert (by["SO-41"]["ready_day"], by["SO-41"]["status"]) == (9, "exposed_covered")
    assert (by["SO-61"]["ready_day"], by["SO-61"]["late_days"]) == (11, 2)


# ---------------------------------------------------------------------------
# The generated demo world
# ---------------------------------------------------------------------------

def test_pristine_demo_world_has_zero_projected_late_orders(pristine_graphs):
    res = project_shortages(DEMO)
    assert res["totals"]["orders"] > 100
    assert res["totals"]["projected_late"] == 0
    assert res["totals"]["exposed"] == 0


def test_monsoon_outcomes_on_demo_world(fresh):
    g = fresh(DEMO)
    inc = MONSOON["incident"]
    d = declare_incident(g, incident_id=inc["id"], kind=inc["kind"], title=inc["title"],
                         alert_text=inc["alert_text"], entity_ids=[inc["zone_id"]],
                         capacity_factor=inc["capacity_factor"], duration_days=inc["duration_days"])
    assert d["site_ids"] == ["S-VOLT-AYU"]
    exp = trace_exposure(g, inc["id"])
    assert exp["tier1_view"]["directly_affected_tier1"] == 0
    assert exp["multi_tier"]["tier1_sites"] == [{"site": "S-BMAX-PEN", "via": ["S-VOLT-AYU"]},
                                                {"site": "S-PWRC-HPG", "via": ["S-VOLT-AYU"]}]
    assert exp["shared_upstream"][0]["dependents"] == ["S-AMPR-JHB", "S-BMAX-PEN", "S-PWRC-HPG"]

    res = project_shortages(g)
    plants = {p["plant"]: p for p in res["plants"]}
    assert plants["PL-GDL"]["exposed"] > 0 and plants["PL-GDL"]["projected_late"] == 0  # exposed but covered
    assert plants["PL-PEN"]["projected_late"] > 0 and plants["PL-BAC"]["projected_late"] > 0
    assert plants["PL-PEN"]["stockout_day"] < plants["PL-BAC"]["stockout_day"]
    # The graph trace and the projection agree on which orders are exposed.
    assert set(exp["order_evidence"]) == {o["order_id"] for o in res["orders"] if o["exposed"]}
