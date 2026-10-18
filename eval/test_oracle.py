"""Hand-worked oracle checks, including failures that an aggregate score could hide."""

import ast
import copy
from fractions import Fraction
from pathlib import Path

import pytest

from eval.fixtures import cases, snapshot
from eval.oracle import World


@pytest.mark.parametrize("case", cases(), ids=lambda c: c["name"])
def test_hand_worked_ready_days(case):
    world = World(snapshot(case["world"])).disrupted(case["entity_ids"], case["factor"], case["duration"])
    assert world.project()["ready"] == case["ready"]


def test_partial_supplier_retains_healthy_share():
    data = snapshot(cases()[0]["world"])
    world = World(data).disrupted(["S-UP"], 0.5, 14)
    # (280 * 1/2 + 120) / 400 = 13/20, rather than rejecting the whole source.
    assert world.availability()["S-T1"] == (Fraction(13, 20), 3, 14)


def test_exposure_and_lateness_are_different_sets():
    case = cases()[0]
    world = World(snapshot(case["world"])).disrupted(["Z-T"], 0, 14)
    assert world.exposure(["S-UP"]) == {"SO-A1", "SO-A2", "SO-A3", "SO-A4"}
    assert world.project()["late"] == {"SO-A3"}


def test_capacity_uses_shared_fab_once():
    data = snapshot(cases()[0]["world"])
    world = World(data).disrupted(["S-UP"], 0, 14)
    cap = world.capacity("C-PACK", "PL-X")
    # Healthy feeder: min(1000/4, FEEDS 200/4) = 50 packs/wk. Alternate has zero.
    assert cap["true_wk"] == 50
    assert cap["sites"]["S-ALT"] == 0
    # 70 contracted packs plus min(50 spare, 100/4 input) = 95.
    assert world.capacity("C-PACK", "PL-X", nominal=True)["true_wk"] == 95


def test_complementary_inputs_bind_shortage_but_flow_is_only_upper_bound():
    case = cases()[2]
    world = World(snapshot(case["world"])).disrupted(["S-BMS"], 0, 10)
    assert world.availability()["S-PACK"][0] == 0
    assert world.project()["late_days"]["SO-C"] == 9
    assert world.capacity("PACK", "PL-C")["true_wk"] == 70  # stated single-commodity limitation


def test_cycle_and_unknown_entity_fail_explicitly():
    data = snapshot(cases()[0]["world"])
    data["edges"].append({"type": "FEEDS", "src": "S-T1", "dst": "S-UP", "props": {}})
    with pytest.raises(ValueError, match="DAG"):
        World(data)
    with pytest.raises(ValueError, match="unknown_entity"):
        World(snapshot(cases()[0]["world"])).expand(["UNKNOWN"])


def test_day_zero_arrivals_and_horizon_boundary():
    data = snapshot(cases()[0]["world"])
    for row in data["nodes"]:
        if row["props"]["id"] == "SO-A1":
            row["props"].update(qty=41, need_day=0)
    # C-PACK 30 stock + 10 day-zero arrivals = 40; order needs 41 and has no future day.
    result = World(data).project(horizon=0)
    assert result["ready"] == {"SO-A1": None}
    assert result["late_days"] == {"SO-A1": 1}


def test_oracle_does_not_import_product_engines():
    tree = ast.parse(Path(__file__).with_name("oracle.py").read_text(encoding="utf-8"))
    imports = [n.module or "" for n in ast.walk(tree) if isinstance(n, ast.ImportFrom)]
    imports += [a.name for n in ast.walk(tree) if isinstance(n, ast.Import) for a in n.names]
    assert not any(name.startswith(("domino", "tests")) for name in imports)


def test_oracle_does_not_mutate_export():
    data = snapshot(cases()[0]["world"])
    original = copy.deepcopy(data)
    world = World(data).disrupted(["Z-T"], 0, 14)
    world.project()
    assert data == original


def test_joint_rationing_cannot_spend_shared_cells_twice():
    case = cases()[1]
    data = snapshot(case["world"])
    for n in data["nodes"]:
        if n["props"]["id"] == "S-FAB":
            n["props"]["capacity_wk"] = 400
    for e in data["edges"]:
        if e["type"] == "FEEDS":
            e["props"]["used_wk"] = 0
    data["edges"] += [{"type": "MADE_FROM", "src": "C-4S", "dst": "C-CELL", "props": {"qty": 4}},
                      {"type": "MADE_FROM", "src": "C-6S", "dst": "C-CELL", "props": {"qty": 6}}]
    pos = [{"id": "A", "site": "S-L4", "component": "C-4S", "rate_wk": 100},
           {"id": "B", "site": "S-L6", "component": "C-6S", "rate_wk": 100}]
    # Requested inputs: 400 + 600 = 1000 cells; only 400 exist. Both get 40%.
    assert World(data).realized_rates(pos) == {"A": 40, "B": 40}


def test_evidence_checks_order_identity_and_value_not_only_edge_existence():
    case = cases()[0]
    world = World(snapshot(case["world"])).disrupted(["Z-T"], 0, 14)
    evidence = {"id": "E1", "origin": "S-UP", "path": ["S-UP", "S-T1", "PL-X"],
                "tier1": "S-T1", "plant": "PL-X", "component": "C-PACK", "product": "PR-A",
                "orders": ["SO-A1"], "value_cents": 20_000, "upstream_hops": 1}
    assert world.validate_evidence({"evidence": [evidence]}, ["S-UP"])["valid"] == 1
    evidence["value_cents"] = 99
    assert world.validate_evidence({"evidence": [evidence]}, ["S-UP"])["invalid"] == ["E1"]
    evidence["value_cents"] = 50_000
    evidence["orders"] = ["SO-B1"]  # wrong product, even though the plant is the same
    assert world.validate_evidence({"evidence": [evidence]}, ["S-UP"])["invalid"] == ["E1"]


def test_single_point_scan_matches_the_hand_worked_tiny_world():
    # Each site alone at 0% for 14 days (worked out in backend/tests/test_xray.py): S-T1 makes SO-A2 10 days and
    # SO-A3 14 days late; S-UP, which Kestrel has no contract with, makes SO-A3 4 days late.
    scan = World(snapshot(cases()[0]["world"])).single_points(14)
    assert {s: (sorted(r["late"]), r["penalty_cents"]) for s, r in scan.items()} == {
        "S-ALT": ([], 0), "S-T1": (["SO-A2", "SO-A3"], 15_000), "S-T2": ([], 0),
        "S-UP": (["SO-A3"], 4_000), "S-UP2": ([], 0)}
    assert {s for s, r in scan.items() if r["hidden"]} == {"S-UP", "S-UP2"}


def test_single_point_scan_flags_voltcell_in_the_seeded_world():
    from domino.seed.generator import generate
    scan = World(snapshot(generate(42))).single_points(21)
    hidden = sorted((s for s, r in scan.items() if r["hidden"] and r["late"]),
                    key=lambda s: (-len(scan[s]["late"]), -scan[s]["penalty_cents"], s))
    assert hidden[0] == "S-VOLT-AYU"
