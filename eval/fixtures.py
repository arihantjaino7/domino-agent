"""Small worlds with fixed hand-worked expectations; no engine-derived labels."""

from __future__ import annotations

from domino.seed.world import World
from tests.fixtures.tiny_world import _base, _order, _product, _site, shared_line_world, tiny_world


def snapshot(world: World) -> dict:
    places = {"Site", "Region", "HazardZone", "Port", "Plant"}
    return {"format": 1,
            "nodes": [{"labels": sorted([group, "Place"] if group in places else [group]), "props": dict(row)}
                      for group, rows in world.nodes.items() for row in rows],
            "edges": [{"type": rel, **row} for rel, rows in world.edges.items() for row in rows]}


def complementary_world() -> World:
    """70 packs/wk need cells AND a controller; losing controllers means zero packs.

    No stock/transit/buffer. 10 packs needed day 1, restore day 10: first full
    day's 10 packs arrive on day 10, so ready=10 and lateness=9 days.
    """
    w = World(seed=0)
    _base(w, "PL-C", ["CELL", "BMS", "PACK"])
    _site(w, "S-CELL", "R-T2", 2, "CELL", cap=280)
    _site(w, "S-BMS", "R-T1", 2, "BMS", cap=70)
    _site(w, "S-PACK", "R-T2", 1, "PACK", cap=70)
    w.add_edge("MADE_FROM", "PACK", "CELL", qty=4)
    w.add_edge("MADE_FROM", "PACK", "BMS", qty=1)
    w.add_edge("FEEDS", "S-CELL", "S-PACK", component_id="CELL", used_wk=280, cap_wk=280)
    w.add_edge("FEEDS", "S-BMS", "S-PACK", component_id="BMS", used_wk=70, cap_wk=70)
    w.add_edge("SUPPLIES", "S-PACK", "PL-C", component_id="PACK", used_wk=70,
               unit_price_cents=100, transit_days=0)
    _product(w, "PR-C", "PL-C", {"PACK": 1})
    _order(w, "SO-C", "CU-N", "PR-C", "PL-C", 10, 1)
    return w


def cases() -> list[dict]:
    return [
        {"name": "tiny_pipeline", "world": tiny_world(), "entity_ids": ["Z-T"], "factor": 0.0, "duration": 14,
         "ready": {"SO-A1": 3, "SO-A2": 6, "SO-A3": 14, "SO-A4": 20, "SO-B1": 5}},
        {"name": "shared_line", "world": shared_line_world(), "entity_ids": ["S-FAB"], "factor": 0.5, "duration": 20,
         "ready": {"SO-41": 9, "SO-61": 11}},
        {"name": "complementary", "world": complementary_world(), "entity_ids": ["S-BMS"], "factor": 0.0, "duration": 10,
         "ready": {"SO-C": 10}},
        {"name": "partly_exposed", "world": tiny_world(), "entity_ids": ["S-UP"], "factor": 0.5, "duration": 14,
         "ready": {"SO-A1": 3, "SO-A2": 6, "SO-A3": 10, "SO-A4": 20, "SO-B1": 5}},
    ]
