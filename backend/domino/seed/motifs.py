"""Hand-built story motifs (PLAN §5.6 Monsoon, §5.8 Panel Fire).

These are design inputs for the generator, not answers. Engines compute every
result (exposure, stockout days, capacity) from the graph at runtime, and the UI
never shows a number from this file.

Each motif is plain data, so every design number has exactly one home:
  sites, FEEDS, SUPPLIES, CAN_SUPPLY, plant stock, fixed demand, and the incident
  the scenario declares. `add_motif()` writes one motif into the world.

Units (§5.2): integer units/week, integer cents, integer days.
"""

from __future__ import annotations

from typing import Any

from domino.seed.world import World

# Monsoon (§5.6): the battery chain with a hidden shared cell fab in the flood zone.
MONSOON: dict[str, Any] = {
    "suppliers": [
        # (id, name, hq_country, reliability)
        ("SUP-VOLT", "VoltCell Energy", "TH", 0.97),
        ("SUP-HANR", "Hanriver Cells", "KR", 0.95),
        ("SUP-KANT", "Kanto Energy", "JP", 0.98),
        ("SUP-PWRC", "PowerCell Packs", "VN", 0.93),
        ("SUP-BMAX", "BatteryMax", "MY", 0.94),
        ("SUP-AMPR", "AmpereOne", "MY", 0.90),
        ("SUP-EHUB", "ElectroHub", "KR", 0.95),
    ],
    "sites": [
        # (id, name, supplier, kind, tier, region, capacity_wk, unit, input_buffer_days, {component: unit_price_cents})
        ("S-VOLT-AYU", "VoltCell Energy Ayutthaya", "SUP-VOLT", "cell_fab", 2, "R-AYU", 10_500, "cells", 6, {"CELL-21700": 350}),
        ("S-HANR-CJU", "Hanriver Cells Cheongju", "SUP-HANR", "cell_fab", 2, "R-CJU", 4_000, "cells", 6, {"CELL-21700": 360}),
        ("S-KANT-KUM-C", "Kanto Energy Kumamoto cell line", "SUP-KANT", "cell_fab", 2, "R-KUM", 2_400, "cells", 5, {"CELL-21700": 380}),
        ("S-PWRC-HPG", "PowerCell Packs Hai Phong", "SUP-PWRC", "pack_line", 1, "R-HPG", 900, "packs", 5, {"BAT-4S": 3_800}),
        ("S-BMAX-PEN", "BatteryMax Penang", "SUP-BMAX", "pack_line", 1, "R-PEN", 800, "packs", 3, {"BAT-6S": 5_200}),
        ("S-AMPR-JHB", "AmpereOne Johor Bahru", "SUP-AMPR", "pack_line", 1, "R-JHB", 700, "packs", 5, {"BAT-4S": 3_100}),
        ("S-KANT-KUM-P", "Kanto Energy Kumamoto packs", "SUP-KANT", "pack_line", 1, "R-KUM", 600, "packs", 4, {"BAT-4S": 4_600, "BAT-6S": 6_300}),
        ("S-EHUB-SWN", "ElectroHub Suwon", "SUP-EHUB", "pack_line", 1, "R-SWN", 600, "packs", 4, {"BAT-6S": 5_800}),
    ],
    "feeds": [
        # (src, dst, component, cap_wk, used_wk) in cells/week.
        # Tier-1 lines buy cells for their full line rate (PowerCell 900 packs x 4 = 3,600 cells).
        ("S-VOLT-AYU", "S-PWRC-HPG", "CELL-21700", 2_800, 2_520),
        ("S-HANR-CJU", "S-PWRC-HPG", "CELL-21700", 1_600, 1_080),  # 520 cells/wk of headroom: the "PowerCell extra" source
        ("S-VOLT-AYU", "S-BMAX-PEN", "CELL-21700", 4_800, 4_800),  # BatteryMax is 100% VoltCell
        ("S-VOLT-AYU", "S-AMPR-JHB", "CELL-21700", 2_800, 0),      # the trap: AmpereOne's only cells are VoltCell's
        ("S-KANT-KUM-C", "S-KANT-KUM-P", "CELL-21700", 2_400, 0),  # one line shared by Kanto's 4S and 6S packs
        ("S-HANR-CJU", "S-EHUB-SWN", "CELL-21700", 3_600, 1_200),  # 1,200 used for other buyers, 2,400 headroom (contested)
    ],
    "supplies": [
        # (site, plant, component, used_wk, unit_price_cents, transit_days)
        ("S-PWRC-HPG", "PL-BAC", "BAT-4S", 700, 3_800, 2),
        ("S-BMAX-PEN", "PL-PEN", "BAT-6S", 330, 5_200, 1),
        ("S-BMAX-PEN", "PL-GDL", "BAT-6S", 200, 5_200, 24),  # ~24 days of packs already on the water
    ],
    "can_supply": [
        # (site, plant, component, spare_wk, unit_price_cents, lead_days, transit_days, moq, air_transit_days, air_surcharge_cents)
        ("S-AMPR-JHB", "PL-BAC", "BAT-4S", 700, 3_100, 7, 6, 500, 2, 900),     # cheapest, and tainted
        ("S-KANT-KUM-P", "PL-BAC", "BAT-4S", 300, 4_600, 10, 12, 200, 2, 900),
        ("S-KANT-KUM-P", "PL-PEN", "BAT-6S", 250, 6_300, 10, 10, 200, 2, 1_200),
        ("S-EHUB-SWN", "PL-PEN", "BAT-6S", 400, 5_800, 7, 9, 300, 2, 1_200),
        ("S-PWRC-HPG", "PL-BAC", "BAT-4S", 200, 4_000, 3, 2, 100, 1, 300),     # PowerCell extra volume
    ],
    "stock": [
        # (plant, component, on_hand, safety)
        ("PL-BAC", "BAT-4S", 1_000, 300),
        ("PL-PEN", "BAT-6S", 300, 150),
        ("PL-GDL", "BAT-6S", 700, 100),
    ],
    "demand": [
        # (plant, product, units/week) for the regular order stream
        ("PL-BAC", "KB14", 600),
        ("PL-PEN", "KBP16", 300),
        ("PL-GDL", "KBP16", 190),
    ],
    "orders": [
        # Fixed orders: (id, customer, plant, product, qty, due_day)
        ("SO-1000", "CU-MER", "PL-BAC", "KB14", 450, 28),  # Meridian Schools Consortium, strategic
    ],
    "incident": {
        "id": "INC-0001",
        "kind": "flood",
        "title": "Monsoon flooding in the Chao Phraya Basin",
        "alert_text": "Severe monsoon flooding across Ayutthaya and the Chao Phraya Basin; "
                      "industrial estates closed, recovery expected in 3-5 weeks.",
        "zone_id": "Z-CPB",
        "capacity_factor": 0.0,
        "duration_days": 28,
    },
}

# Panel Fire (§5.8): a single tier-1 failure, with a compatibility trap among the alternates.
PANEL_FIRE: dict[str, Any] = {
    "suppliers": [
        ("SUP-LMVU", "Lumenvue Display", "CN", 0.96),
        ("SUP-BRVL", "Brightvale Optics", "TW", 0.97),
        ("SUP-NOVA", "Novaglass", "KR", 0.92),
        ("SUP-CLRV", "ClearView Panels", "CN", 0.94),
    ],
    "sites": [
        ("S-LMVU-SUZ", "Lumenvue Display Suzhou", "SUP-LMVU", "module_line", 1, "R-SUZ", 900, "modules", 2, {"DSP-14": 6_200}),
        ("S-BRVL-TXG", "Brightvale Optics Taichung", "SUP-BRVL", "module_line", 1, "R-TXG", 800, "modules", 3, {"DSP-14": 7_000}),
        ("S-NOVA-GUM", "Novaglass Gumi", "SUP-NOVA", "module_line", 1, "R-GUM", 900, "modules", 3, {"DSP-14-HB": 5_900}),
        ("S-CLRV-WUH", "ClearView Panels Wuhan", "SUP-CLRV", "panel_fab", 2, "R-WUH", 1_400, "panels", 4, {"PNL-14": 2_900}),
    ],
    "feeds": [
        ("S-CLRV-WUH", "S-LMVU-SUZ", "PNL-14", 1_000, 900),
    ],
    "supplies": [
        ("S-LMVU-SUZ", "PL-BAC", "DSP-14", 760, 6_200, 5),
    ],
    "can_supply": [
        ("S-BRVL-TXG", "PL-BAC", "DSP-14", 500, 7_000, 2, 4, 200, 1, 400),     # +$8, fast, compatible
        ("S-NOVA-GUM", "PL-BAC", "DSP-14-HB", 600, 5_900, 4, 5, 300, 1, 400),  # DSP-14-HB is not approved for KB14
    ],
    "stock": [
        ("PL-BAC", "DSP-14", 700, 150),
    ],
    "demand": [],
    "orders": [],
    "incident": {
        "id": "INC-0002",
        "kind": "fire",
        "title": "Fire at Lumenvue Display, Suzhou",
        "alert_text": "Fire at Lumenvue Display's Suzhou module plant; production halted for about two weeks.",
        "site_ids": ["S-LMVU-SUZ"],
        "capacity_factor": 0.0,
        "duration_days": 14,
    },
}

MOTIFS = {"monsoon": MONSOON, "panel_fire": PANEL_FIRE}


def add_motif(w: World, motif: dict[str, Any], regions: dict[str, dict[str, Any]]) -> set[tuple[str, str]]:
    """Write a motif's suppliers, sites and edges. Returns the (plant, component) pairs it supplies and stocks."""
    for sup_id, name, country, reliability in motif["suppliers"]:
        w.add_node("Supplier", id=sup_id, name=name, hq_country=country, reliability=reliability)
    for (site_id, name, sup_id, kind, tier, region, cap, unit, buffer_days, makes) in motif["sites"]:
        r = regions[region]
        w.add_node("Site", id=site_id, name=name, kind=kind, tier=tier, capacity_wk=cap, unit=unit,
                   capacity_factor=1.0, status="active", input_buffer_days=buffer_days,
                   lat=r["lat"], lng=r["lng"], aliases=f"{name}, {r['name']}, {sup_id[4:]}")
        w.add_edge("OPERATES", sup_id, site_id)
        w.add_edge("LOCATED_IN", site_id, region)
        for comp, price in makes.items():
            w.add_edge("MAKES", site_id, comp, unit_price_cents=price)
    for src, dst, comp, cap, used in motif["feeds"]:
        w.add_edge("FEEDS", src, dst, component_id=comp, cap_wk=cap, used_wk=used)
    for site, plant, comp, used, price, transit in motif["supplies"]:
        w.add_edge("SUPPLIES", site, plant, component_id=comp, used_wk=used, unit_price_cents=price,
                   transit_days=transit)
    for (site, plant, comp, spare, price, lead, transit, moq, air_days, air_cents) in motif["can_supply"]:
        w.add_edge("CAN_SUPPLY", site, plant, component_id=comp, spare_wk=spare, unit_price_cents=price,
                   lead_days=lead, transit_days=transit, moq=moq, qualified=True,
                   air_transit_days=air_days, air_surcharge_cents=air_cents)
    covered: set[tuple[str, str]] = set()
    for plant, comp, on_hand, safety in motif["stock"]:
        w.add_edge("STOCKS", plant, comp, on_hand=on_hand, safety=safety)
        covered.add((plant, comp))
    return covered
