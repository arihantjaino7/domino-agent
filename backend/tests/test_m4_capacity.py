"""M4 engines: true capacity (max-flow + min cut) and alternatives.

Hand calculations are in the comments next to each assertion.
DB tests use test:m4:* graphs only and drop them afterwards.
"""

import pytest

from domino.engines.alternatives import find_alternatives
from domino.engines.capacity import PLANT_NODE, FlowNetwork, _load_scratch, compute_true_capacity, solve
from domino.engines.incident import declare_incident
from domino.graph.client import get_db
from domino.graph.lifecycle import build_pristine, copy_graph, drop_graph
from domino.seed.generator import generate
from domino.seed.motifs import MONSOON, PANEL_FIRE
from tests.fixtures.tiny_world import tiny_world

TINY, DEMO, SCRATCH = "test:m4:tiny", "test:m4:demo", "test:m4:scratch"


def _net(edges, sources):
    net = FlowNetwork(component="X", plant="P")
    for (u, v), cap in edges.items():
        net.edges[(u, v)] = {"cap": cap, "cap_nominal": cap, "kind": "site", "site": u}
    net.sources = sources
    return net


def _solve(net):
    drop_graph(SCRATCH)
    try:
        _load_scratch(net, SCRATCH)
        return solve(net, SCRATCH, PLANT_NODE, "cap")
    finally:
        drop_graph(SCRATCH)


def _declare(graph, incident):
    ents = [incident["zone_id"]] if "zone_id" in incident else incident["site_ids"]
    return declare_incident(graph, incident_id=incident["id"], kind=incident["kind"], title=incident["title"],
                            alert_text=incident["alert_text"], entity_ids=ents,
                            capacity_factor=incident["capacity_factor"], duration_days=incident["duration_days"])


@pytest.fixture(scope="module")
def graphs():
    build_pristine(tiny_world(), TINY)
    build_pristine(generate(42), DEMO)
    yield
    for g in (TINY, DEMO):
        drop_graph(g)
        drop_graph(g + ":run")


@pytest.fixture
def fresh(graphs):
    def make(src):
        copy_graph(src, src + ":run")
        return src + ":run"
    return make


# ---------------------------------------------------------------------------
# Max flow and min cut on hand-made networks
# ---------------------------------------------------------------------------

def test_docs_example_max_flow_is_13():
    # A->B 10, A->C 5, B->C 8 (C is the plant): 5 direct + min(10, 8) via B = 13.
    res = _solve(_net({("A", "B"): 10, ("A", PLANT_NODE): 5, ("B", PLANT_NODE): 8}, ["A"]))
    assert res["max_flow"] == 13
    assert sorted((c["from"], c["to"]) for c in res["cut"]) == [("A", PLANT_NODE), ("B", PLANT_NODE)]


def test_saturated_edges_are_not_all_bottlenecks():
    # s->a 5 feeds a->b 2 -> b->P 2 and a->P 3. Every edge is saturated (flow 5), but only s->a is the
    # min cut found by residual reachability: raising a->b alone changes nothing because b->P is also 2.
    edges = {("s", "a"): 5, ("a", "b"): 2, ("b", PLANT_NODE): 2, ("a", PLANT_NODE): 3}
    res = _solve(_net(edges, ["s"]))
    assert res["max_flow"] == 5
    saturated = {e for e, cap in edges.items() if res["flows"].get(e, 0) == cap}
    assert saturated == set(edges)
    assert [(c["from"], c["to"]) for c in res["cut"]] == [("s", "a")]


def test_zero_flow_network_returns_zero_and_cuts_the_dead_source():
    res = _solve(_net({("s", "a"): 0, ("a", PLANT_NODE): 9}, ["s"]))
    assert res["max_flow"] == 0 and [(c["from"], c["to"]) for c in res["cut"]] == [("s", "a")]


# ---------------------------------------------------------------------------
# Tiny world
# ---------------------------------------------------------------------------

def test_tiny_pristine_capacity(graphs):
    # In C-PACK units (4 cells per pack): S-UP->S-T1 300/4 = 75, S-UP2->S-T1 200/4 = 50, S-UP->S-ALT 100/4 = 25.
    # S-T1 can make 125 but its plant edge is 70; S-ALT delivers 25 of its 50 spare. True = 95, naive = 70 + 50.
    cap = compute_true_capacity(TINY, "C-PACK", "PL-X", run_id="t")
    assert (cap["true_wk"], cap["naive_wk"], cap["contracted_wk"]) == (95, 120, 70)


def test_tiny_capacity_after_incident(fresh):
    g = fresh(TINY)
    declare_incident(g, incident_id="INC-T", kind="flood", title="t", alert_text="t", entity_ids=["Z-T"],
                     capacity_factor=0.0, duration_days=14)
    cap = compute_true_capacity(g, "C-PACK", "PL-X", run_id="t")
    # Only S-UP2's 50 packs/wk of cells survive. Cut = S-UP's own capacity (0) + S-UP2->S-T1 (50).
    assert cap["true_wk"] == 50 and cap["nominal_wk"] == 95
    assert sorted(c["what"] for c in cap["bottleneck"]) == ["S-UP own capacity", "S-UP2 -> S-T1 C-CELL supply line"]
    sites = {s["site"]: s for s in cap["sites"]}
    assert (sites["S-T1"]["clean_wk"], sites["S-T1"]["nominal_wk"]) == (50, 70)
    assert (sites["S-ALT"]["clean_wk"], sites["S-ALT"]["nominal_wk"]) == (0, 25)

    alts = find_alternatives(g, "C-PACK", "PL-X", run_id="t")
    assert alts["accepted"] == []
    rej = alts["rejected"][0]
    assert (rej["site"], rej["reason"], rej["tainted_paths"]) == ("S-ALT", "no_remaining_capacity", [["S-UP", "S-ALT"]])


# ---------------------------------------------------------------------------
# Demo world: Monsoon and Panel Fire
# ---------------------------------------------------------------------------

def test_monsoon_true_vs_naive_capacity(fresh):
    g = fresh(DEMO)
    _declare(g, MONSOON["incident"])
    four = compute_true_capacity(g, "BAT-4S", "PL-BAC", run_id="t")
    # Naive = 700 contract + 700 AmpereOne + 300 Kanto + 200 PowerCell extra = 1900.
    # True: VoltCell is 0, so PowerCell is capped by Hanriver's line 1600/4 = 400, plus Kanto 300 = 700.
    assert (four["naive_wk"], four["true_wk"]) == (1900, 700)
    assert "S-HANR-CJU -> S-PWRC-HPG CELL-21700 supply line" in {c["what"] for c in four["bottleneck"]}
    six = compute_true_capacity(g, "BAT-6S", "PL-PEN", run_id="t")
    # BatteryMax 0 (all VoltCell) + ElectroHub spare 400 + Kanto spare 250 = 650. Naive 330 + 400 + 250.
    assert (six["naive_wk"], six["true_wk"]) == (980, 650)


def test_monsoon_alternatives_exposure_is_not_rejection(fresh):
    g = fresh(DEMO)
    _declare(g, MONSOON["incident"])
    alts = find_alternatives(g, "BAT-4S", "PL-BAC", run_id="t")
    rejected = {r["site"]: r for r in alts["rejected"]}
    accepted = {a["site"]: a for a in alts["accepted"]}
    # AmpereOne: cheapest, but 100% VoltCell -> remaining clean capacity 0 -> rejected with its path.
    assert rejected["S-AMPR-JHB"]["reason"] == "no_remaining_capacity"
    assert rejected["S-AMPR-JHB"]["tainted_paths"] == [["S-VOLT-AYU", "S-AMPR-JHB"]]
    # PowerCell extra: exposed (VoltCell is upstream) but Hanriver keeps it alive -> accepted at reduced capacity.
    pwrc = accepted["S-PWRC-HPG"]
    assert pwrc["exposure_warning"] and pwrc["reduced"] and pwrc["site_clean_wk"] == 400
    assert pwrc["tainted_paths"] == [["S-VOLT-AYU", "S-PWRC-HPG"]]
    assert pwrc["shares_site_with_contract_wk"] == 700
    # Kanto: clean.
    assert not accepted["S-KANT-KUM-P"]["exposure_warning"] and accepted["S-KANT-KUM-P"]["usable_wk"] == 300


def test_panel_fire_compatibility_trap(fresh):
    g = fresh(DEMO)
    _declare(g, PANEL_FIRE["incident"])
    alts = find_alternatives(g, "DSP-14", "PL-BAC", run_id="t")
    assert [a["site"] for a in alts["accepted"]] == ["S-BRVL-TXG"]
    assert [(r["site"], r["reason"]) for r in alts["rejected"]] == [("S-NOVA-GUM", "incompatible")]


def test_scratch_graphs_are_always_dropped(graphs):
    compute_true_capacity(DEMO, "BAT-4S", "PL-BAC", run_id="t")
    assert not [g for g in get_db().list_graphs() if g.startswith("scratch:flow:")]
