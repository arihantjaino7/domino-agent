"""Risk X-ray: the single-point-of-failure scan.

TINY WORLD (tests/fixtures/tiny_world.py), healthy, every site alone at 0% for 14 days:

  Healthy: C-PACK arrives 10/day, stock 30; every order is on time. Five sites are scanned
  (S-UP, S-UP2 feed; S-T1, S-T2 supply; S-ALT holds only a CAN_SUPPLY contract).

  S-T1 (the only active C-PACK line): the plant gets no C-PACK from day 0 + 2 transit = 2 until 14 + 2 = 16.
    Stock 30 + 10 + 10 = 50 by day 1. SO-A1 20 @ day 3 -> ready, 30 left. SO-A2 40 @ day 6 short -> stockout
    day 6. Day 16: 40 -> SO-A2 ready, 10 days late (CU-N, $1/day -> 1,000 cents). Days 17-20 bring 40:
    SO-A3 (50) is still short, SO-A4 (30 @ day 20) takes 30, 10 left. Day 24: 50 -> SO-A3 ready,
    14 days late (CU-S strategic, $10/day -> 14,000 cents).
    => 2 late, 15,000 cents, 4 PR-A orders exposed, first stockout day 6.
  S-UP (tier 2, no contract): S-T1 keeps 120 / 400 = 3/10 of its cells (the M3 hand calculation):
    SO-A3 is 4 days late -> 1 late, 4,000 cents, stockout day 10. A hidden single point of failure.
  S-UP2: S-T1 keeps 7/10, so 49/wk = 7/day from day 5 to 16; stock never runs short -> 0 late, 4 exposed.
  S-T2: no C-BRD from day 1 to 15, but 100 + 10 in stock covers SO-B1 (50 @ day 5) -> 0 late, 1 exposed.
  S-ALT: nothing flows from it today -> no damage.

  Rank: S-T1 (2 late) > S-UP (1 late) > S-UP2 (4 exposed) > S-T2 (1 exposed) > S-ALT.
  S-T1 ranks first because it carries 100% of the C-PACK flow; S-UP removes only 70% of S-T1's cells.

  Max-flow in the sandbox (healthy C-PACK at PL-X is 95/wk, as in test_m4_capacity):
    S-T1 out -> only S-ALT's 25/wk is left (drop 70); S-UP out -> S-T1 keeps S-UP2's 200/4 = 50/wk (drop 45).
"""

import pytest

from domino.agent.context import new_context
from domino.agent.tools import scan_single_points_of_failure
from domino.engines import xray
from domino.engines.sandbox import world_version
from domino.engines.shortage import fetch_inputs, project
from domino.graph.client import get_db
from domino.engines.incident import declare_incident
from domino.graph.lifecycle import build_pristine, copy_graph, drop_graph, graph_counts
from domino.seed.generator import generate
from tests.fixtures.tiny_world import tiny_world

TINY, DEMO = "test:xray:tiny", "test:xray:demo"


@pytest.fixture(scope="module")
def graphs():
    build_pristine(tiny_world(), TINY)
    build_pristine(generate(42), DEMO)
    yield
    for g in (TINY, DEMO):
        drop_graph(g)


@pytest.fixture(scope="module")
def tiny(graphs):
    xray._cache.clear()
    return xray.scan(TINY, duration_days=14)


def _by_site(res):
    return {r["site"]: r for r in res["sites"]}


def test_tiny_ranking_and_hand_computed_damage(tiny):
    assert [r["site"] for r in tiny["sites"]] == ["S-T1", "S-UP", "S-UP2", "S-T2", "S-ALT"]
    assert tiny["scanned"] == 5 and tiny["baseline"]["projected_late"] == 0
    s = _by_site(tiny)
    t1 = s["S-T1"]
    assert (t1["orders_late"], t1["penalty_cents"], t1["orders_exposed"], t1["first_stockout_day"]) == (2, 15_000, 4, 6)
    assert t1["late_order_ids"] == ["SO-A2", "SO-A3"] and t1["strategic_late"] == 1
    assert t1["tier1_hit"] == ["S-T1"] and t1["plants_hit"] == ["PL-X"]
    up = s["S-UP"]
    assert (up["orders_late"], up["penalty_cents"], up["orders_exposed"], up["first_stockout_day"]) == (1, 4_000, 4, 10)
    assert up["late_order_ids"] == ["SO-A3"] and up["tier1_hit"] == ["S-T1"]
    assert (s["S-UP2"]["orders_late"], s["S-UP2"]["orders_exposed"]) == (0, 4)
    assert (s["S-T2"]["orders_late"], s["S-T2"]["orders_exposed"]) == (0, 1)
    assert (s["S-ALT"]["orders_late"], s["S-ALT"]["orders_exposed"]) == (0, 0)


def test_tiny_hidden_flag_and_single_points_of_failure(tiny):
    s = _by_site(tiny)
    assert {k for k, r in s.items() if r["hidden"]} == {"S-UP", "S-UP2"}  # no SUPPLIES / CAN_SUPPLY edge
    assert {k for k, r in s.items() if r["single_point_of_failure"]} == {"S-T1", "S-UP"}
    assert (tiny["single_points_of_failure"], tiny["hidden_single_points_of_failure"]) == (2, 1)
    # S-UP feeds the active line S-T1 and the backup S-ALT: the backup is not independent of it.
    assert s["S-UP"]["dependents"] == {"tier1_active": ["S-T1"], "tier1_backup": ["S-ALT"], "plants": ["PL-X"]}
    assert ["S-UP", "S-T1", "PL-X"] in [p["path"] for p in s["S-UP"]["paths"]]


def test_tiny_sandbox_confirms_and_measures_the_capacity_drop(tiny):
    s = _by_site(tiny)
    assert tiny["confirmed"] == ["S-T1", "S-UP"]
    for site, (healthy, during) in {"S-T1": (95, 25), "S-UP": (95, 50)}.items():
        c = s[site]["confirmed"]
        assert c["matches_fast_pass"] is True
        assert c["capacity"][0]["component"] == "C-PACK" and c["capacity"][0]["plant"] == "PL-X"
        assert (c["capacity"][0]["healthy_wk"], c["capacity"][0]["during_outage_wk"]) == (healthy, during)
        assert c["capacity"][0]["drop_wk"] == healthy - during


def test_scan_never_writes_to_the_scanned_graph(graphs):
    before = (world_version(TINY), graph_counts(TINY))
    xray._cache.clear()
    xray.scan(TINY, duration_days=10)
    assert (world_version(TINY), graph_counts(TINY)) == before
    assert not [g for g in get_db().list_graphs() if g.startswith(("sandbox:xray:", "scratch:flow:xray"))]


def test_scan_is_cached_until_the_world_changes(graphs):
    run = TINY + ":run"
    copy_graph(TINY, run)
    try:
        first, again = xray.scan(run, duration_days=14), xray.scan(run, duration_days=14)
        assert first["cached"] is False and again["cached"] is True and again["sites"] == first["sites"]
        declare_incident(run, incident_id="INC-T", kind="flood", title="t", alert_text="t", entity_ids=["S-UP"],
                         capacity_factor=0.0, duration_days=14)
        changed = xray.scan(run, duration_days=14)
        assert changed["cached"] is False and changed["baseline"]["projected_late"] == 1  # SO-A3, as in M3
    finally:
        drop_graph(run)


def test_coupled_fast_pass_equals_full_projection_on_the_seed_world(graphs):
    # The fast pass projects only the stock pools an outage can reach; it must agree with a full projection.
    inputs = fetch_inputs(DEMO)
    base, fast, projected = xray.fast_pass(inputs, sorted(inputs["sites"]), 21)
    supply = {e["site"] for e in inputs["supply"]}
    assert projected > 0
    for site in sorted(inputs["sites"]):
        full = xray.damage(base, project(xray.outage_inputs(inputs, site, 21)), supply)
        assert fast[site] == full, site


def test_seed_world_flags_voltcell_as_a_hidden_single_point_of_failure(graphs):
    xray._cache.clear()
    res = xray.scan(DEMO)
    s = _by_site(res)
    volt = s["S-VOLT-AYU"]
    assert volt["hidden"] and not volt["direct_contract"] and volt["single_point_of_failure"]
    assert volt["tier"] == 2 and volt["orders_late"] > 0 and volt["penalty_cents"] > 0
    # Its cells reach two active pack lines, and AmpereOne's backup line is built on the same cells.
    assert {"S-BMAX-PEN", "S-PWRC-HPG"} <= set(volt["tier1_hit"])
    assert "S-AMPR-JHB" in volt["dependents"]["tier1_backup"]
    hidden = [r for r in res["sites"] if r["hidden"] and r["single_point_of_failure"]]
    assert hidden[0]["site"] == "S-VOLT-AYU"  # the worst hidden weak point in the seeded world
    # The worst hidden site is always re-checked in a sandbox, next to the top three.
    assert len(res["confirmed"]) == 4 and "S-VOLT-AYU" in res["confirmed"]
    assert volt["confirmed"]["matches_fast_pass"] is True


def test_tool_returns_a_compact_ranked_list_with_evidence(graphs):
    ctx = new_context("t-xray", DEMO)
    out = scan_single_points_of_failure(ctx, top=5)
    assert out["result_ref"] == "R-01" and len(out["sites"]) == 5
    assert [r["rank"] for r in out["sites"]] == [1, 2, 3, 4, 5]
    for r in out["sites"]:
        assert r["evidence_ids"] and all(ctx.evidence[e][0] == r["site"] for e in r["evidence_ids"])
    assert ctx.ui["R-01"]["tool"] == "scan_single_points_of_failure"
