"""Hand-checkable fixture worlds for the M3 engines.

TINY WORLD (24 nodes). Every expected value in test_m3_engines.py is worked out by hand below.

    Z-T (flood) <- R-T1 <- S-UP ----280/wk--+                       (S-UP also feeds S-ALT, used 0)
                                            v
                   R-T2 <- S-UP2 --120/wk-> S-T1 --C-PACK 70/wk, transit 2--> PL-X  (stock C-PACK 30)
                                            S-T2 --C-BRD  70/wk, transit 1--> PL-X  (stock C-BRD 100)
                                            S-ALT ..CAN_SUPPLY C-PACK..> PL-X

Incident: zone Z-T, factor 0, 14 days -> S-UP disrupted until day 14.
  S-T1 availability = 120 / (280 + 120) = 3/10, felt after its 3-day input buffer (day 3),
  so the plant sees 70 * 3/10 = 21/wk = 3/day from day 3 + 2 = 5 until day 14 + 2 = 16.
  C-PACK arrivals: 10/day on days 0-4, 3/day on days 5-15, 10/day from day 16.

Orders (PR-A needs 1 C-PACK, PR-B needs 1 C-BRD; build_days 1, so need_day = due_day - 1):
  SO-A1 20 @ day 3   stock 30+40 = 70  -> ready 3, left 50
  SO-B1 50 @ day 5   C-BRD 100+60      -> ready 5 (not exposed)
  SO-A2 40 @ day 6   50+10+3+3 = 66    -> ready 6, left 26
  SO-A3 50 @ day 10  26+4*3 = 38 < 50  -> C-PACK stockout day 10; 50 on day 14 -> 4 days late (strategic)
  SO-A4 30 @ day 20  0+3+5*10 = 53     -> ready 20, exposed but covered
"""

from __future__ import annotations

from domino.seed.world import World


def _site(w: World, sid: str, region: str, tier: int, makes: str, buffer_days: int = 0, cap: int = 1000,
          operator: str = "SUP-X") -> None:
    w.add_node("Site", id=sid, name=f"Site {sid}", kind="line", tier=tier, capacity_wk=cap, unit="pcs",
               capacity_factor=1.0, status="active", input_buffer_days=buffer_days, lat=0.0, lng=0.0, aliases=sid)
    w.add_edge("OPERATES", operator, sid)
    w.add_edge("LOCATED_IN", sid, region)
    w.add_edge("MAKES", sid, makes, unit_price_cents=100)


def _base(w: World, plant: str, components: list[str]) -> None:
    w.add_node("HazardZone", id="Z-T", name="Test Basin", hazard="flood", aliases="test flood zone")
    w.add_node("Region", id="R-T1", name="Lowland", country="XX", lat=0.0, lng=0.0, aliases="lowland")
    w.add_node("Region", id="R-T2", name="Highland", country="XX", lat=1.0, lng=1.0, aliases="highland")
    w.add_edge("IN_ZONE", "R-T1", "Z-T")
    w.add_node("Supplier", id="SUP-X", name="Test Supplier", hq_country="XX", reliability=0.9)
    w.add_node("Plant", id=plant, name=f"Plant {plant}", country="XX", lat=1.0, lng=1.0, aliases=plant)
    w.add_edge("LOCATED_IN", plant, "R-T2")
    for c in components:
        w.add_node("Component", id=c, name=c, family="part", unit="pcs", unit_cost_cents=100)
    w.add_node("Customer", id="CU-S", name="Strategic Co", country="XX", tier="strategic", penalty_per_day_cents=1_000)
    w.add_node("Customer", id="CU-N", name="Normal Co", country="XX", tier="standard", penalty_per_day_cents=100)


def _product(w: World, pid: str, plant: str, needs: dict[str, int]) -> None:
    w.add_node("Product", id=pid, name=pid, unit_price_cents=1_000, build_days=1)
    w.add_edge("BUILDS", plant, pid, cap_day=1_000)
    for c, q in needs.items():
        w.add_edge("REQUIRES", pid, c, qty=q)


def _order(w: World, oid: str, customer: str, product: str, plant: str, qty: int, need_day: int) -> None:
    w.add_node("Order", id=oid, qty=qty, due_day=need_day + 1, need_day=need_day, value_cents=qty * 1_000,
               status="open", risk_flag=False)
    w.add_edge("PLACED", customer, oid)
    w.add_edge("FOR_PRODUCT", oid, product)
    w.add_edge("FULFILLED_AT", oid, plant)


def tiny_world() -> World:
    w = World(seed=0)
    _base(w, "PL-X", ["C-CELL", "C-PACK", "C-BRD"])
    _site(w, "S-UP", "R-T1", 2, "C-CELL")
    _site(w, "S-UP2", "R-T2", 2, "C-CELL")
    _site(w, "S-T1", "R-T2", 1, "C-PACK", buffer_days=3)
    _site(w, "S-T2", "R-T2", 1, "C-BRD", buffer_days=2)
    _site(w, "S-ALT", "R-T2", 1, "C-PACK", buffer_days=2)
    w.add_edge("MADE_FROM", "C-PACK", "C-CELL", qty=4)
    w.add_edge("FEEDS", "S-UP", "S-T1", component_id="C-CELL", cap_wk=300, used_wk=280)
    w.add_edge("FEEDS", "S-UP2", "S-T1", component_id="C-CELL", cap_wk=200, used_wk=120)
    w.add_edge("FEEDS", "S-UP", "S-ALT", component_id="C-CELL", cap_wk=100, used_wk=0)
    w.add_edge("SUPPLIES", "S-T1", "PL-X", component_id="C-PACK", used_wk=70, unit_price_cents=100, transit_days=2)
    w.add_edge("SUPPLIES", "S-T2", "PL-X", component_id="C-BRD", used_wk=70, unit_price_cents=100, transit_days=1)
    w.add_edge("CAN_SUPPLY", "S-ALT", "PL-X", component_id="C-PACK", spare_wk=50, unit_price_cents=120,
               lead_days=3, transit_days=2, moq=10, qualified=True, air_transit_days=1, air_surcharge_cents=10)
    w.add_edge("STOCKS", "PL-X", "C-PACK", on_hand=30, safety=10)
    w.add_edge("STOCKS", "PL-X", "C-BRD", on_hand=100, safety=10)
    _product(w, "PR-A", "PL-X", {"C-PACK": 1})
    _product(w, "PR-B", "PL-X", {"C-BRD": 1})
    _order(w, "SO-A1", "CU-N", "PR-A", "PL-X", 20, 3)
    _order(w, "SO-A2", "CU-N", "PR-A", "PL-X", 40, 6)
    _order(w, "SO-A3", "CU-S", "PR-A", "PL-X", 50, 10)
    _order(w, "SO-A4", "CU-N", "PR-A", "PL-X", 30, 20)
    _order(w, "SO-B1", "CU-N", "PR-B", "PL-X", 50, 5)
    return w


def shared_line_world() -> World:
    """Adversarial: one cell line (S-FAB) feeds two tier-1 lines making DIFFERENT components (4S, 6S)
    for the same plant. Disrupting S-FAB at factor 0.5 must expose both components, and the shared
    upstream query must name S-FAB with fan-out 2. Each line is 100% S-FAB, so availability = 1/2.

    Plant PL-Y: P4 needs 1 C-4S, P6 needs 1 C-6S. Each line ships 70/wk (10/day), transit 0, buffer 0,
    so from day 0 each component arrives at 5/day. Stock 0 of each.
      SO-41 qty 50 @ day 9: 5/day on days 0-9 = 50 -> ready day 9, on time but exposed.
      SO-61 qty 60 @ day 9: 50 < 60 -> stockout day 9; 60 on day 11 -> 2 days late.
    """
    w = World(seed=0)
    _base(w, "PL-Y", ["C-CELL", "C-4S", "C-6S"])
    _site(w, "S-FAB", "R-T1", 2, "C-CELL")
    _site(w, "S-L4", "R-T2", 1, "C-4S")
    _site(w, "S-L6", "R-T2", 1, "C-6S")
    w.add_edge("FEEDS", "S-FAB", "S-L4", component_id="C-CELL", cap_wk=400, used_wk=280)
    w.add_edge("FEEDS", "S-FAB", "S-L6", component_id="C-CELL", cap_wk=600, used_wk=420)
    w.add_edge("SUPPLIES", "S-L4", "PL-Y", component_id="C-4S", used_wk=70, unit_price_cents=100, transit_days=0)
    w.add_edge("SUPPLIES", "S-L6", "PL-Y", component_id="C-6S", used_wk=70, unit_price_cents=100, transit_days=0)
    w.add_edge("STOCKS", "PL-Y", "C-4S", on_hand=0, safety=0)
    w.add_edge("STOCKS", "PL-Y", "C-6S", on_hand=0, safety=0)
    _product(w, "P4", "PL-Y", {"C-4S": 1})
    _product(w, "P6", "PL-Y", {"C-6S": 1})
    _order(w, "SO-41", "CU-N", "P4", "PL-Y", 50, 9)
    _order(w, "SO-61", "CU-N", "P6", "PL-Y", 60, 9)
    return w


def learning_world() -> World:
    """Memory that changes plans: two clean alternates, and the seeded favourite is the one that slips.

    Z-T (flood, 28 days) <- R-T1 <- S-MAIN --C-MOD 70/wk (10/day), transit 0--> PL-L   (stock C-MOD 0)
    Alternates for C-MOD at PL-L, no inputs (clean), lead 18 + sea 2 = arrival day 20:
      S-A  (SUP-A, reliability 0.95)  $1.00/unit, spare 70/wk
      S-B  (SUP-B, reliability 0.90)  $1.05/unit, spare 140/wk
    Order SO-L1: 110 x PR-L (1 C-MOD each), need day 30. Do nothing: S-MAIN is back on day 28,
      10/day -> 110 on day 38 -> 8 days late.

    Balanced ranking, cost x (2 - reliability), seeded: S-A 100 x 1.05 = 105 < S-B 105 x 1.10 = 115.5 -> 116.
      Rate for 110 by day 30 from day 20: ceil(7 x 110 / 11) = 70/wk = all of S-A's spare -> surge 100%.
    Delivery: risk = (1 - 0.95) + (1 - 0.6) = 0.45; 20 x 0.45 = 9 exactly, so 9 days late for any seed.
      The PO now arrives day 29 (10/day); with S-MAIN's 10/day from day 28 the order is ready on day 33:
      10 x (33 - 28) + 10 x (33 - 27) = 110 -> fulfilled 3 days late. Last PO unit: 29 - 1 + ceil(770/70) = day 39.
    Learned: S-A (0.95 + (1 - 9/14)) / 2 = 0.6536 -> 0.65. Ranking now: S-A 100 x 1.35 = 135 > S-B 116 -> S-B first.
    """
    w = World(seed=0)
    _base(w, "PL-L", ["C-MOD"])
    w.add_node("Supplier", id="SUP-A", name="Alpha Parts", hq_country="XX", reliability=0.95)
    w.add_node("Supplier", id="SUP-B", name="Beta Parts", hq_country="XX", reliability=0.9)
    _site(w, "S-MAIN", "R-T1", 1, "C-MOD")
    _site(w, "S-A", "R-T2", 1, "C-MOD", operator="SUP-A")
    _site(w, "S-B", "R-T2", 1, "C-MOD", operator="SUP-B")
    w.add_edge("SUPPLIES", "S-MAIN", "PL-L", component_id="C-MOD", used_wk=70, unit_price_cents=100, transit_days=0)
    w.add_edge("CAN_SUPPLY", "S-A", "PL-L", component_id="C-MOD", spare_wk=70, unit_price_cents=100,
               lead_days=18, transit_days=2, moq=10, qualified=True, air_transit_days=1, air_surcharge_cents=50)
    w.add_edge("CAN_SUPPLY", "S-B", "PL-L", component_id="C-MOD", spare_wk=140, unit_price_cents=105,
               lead_days=18, transit_days=2, moq=10, qualified=True, air_transit_days=1, air_surcharge_cents=50)
    w.add_edge("STOCKS", "PL-L", "C-MOD", on_hand=0, safety=0)
    _product(w, "PR-L", "PL-L", {"C-MOD": 1})
    _order(w, "SO-L1", "CU-N", "PR-L", "PL-L", 110, 30)
    return w
