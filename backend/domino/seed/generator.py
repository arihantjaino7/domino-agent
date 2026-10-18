"""Generate the Kestrel Devices world from one seed.

generate(seed) -> World is pure: no I/O, no clock, no global RNG. Each phase draws
from its own `random.Random(f"{seed}:{phase}")`, so changing one phase never shifts
another phase's numbers. Same seed, same world, byte for byte (see World.fingerprint).

Order of work:
  reference data -> demand and orders -> motifs (Monsoon, Panel Fire)
  -> filler supply chains for every other (plant, component) -> logistics -> validation.
"""

from __future__ import annotations

import math
import random
from collections import defaultdict
from typing import Any

from domino.seed import catalog, motifs
from domino.seed.world import EDGE_TYPES, World

HORIZON_WEEKS = 8
LAST_DUE_DAY = HORIZON_WEEKS * 7  # orders are due on days 1..56

FLOAT_PROPS = {"capacity_factor", "reliability", "lat", "lng"}


def generate(seed: int) -> World:
    w = World(seed=seed)
    regions = _reference(w, random.Random(f"{seed}:customers"))
    demand = _demand(random.Random(f"{seed}:demand"))
    _orders(w, demand, random.Random(f"{seed}:orders"))
    covered: set[tuple[str, str]] = set()
    for motif in motifs.MOTIFS.values():
        covered |= motifs.add_motif(w, motif, regions)
    _fill(w, covered, regions, random.Random(f"{seed}:fill"))
    _builds(w, demand)
    _made_from(w)
    _logistics(w, regions)
    validate(w)
    return w


# ---------------------------------------------------------------------------
# Reference data
# ---------------------------------------------------------------------------

def _reference(w: World, rng: random.Random) -> dict[str, dict[str, Any]]:
    for zid, name, hazard, aliases in catalog.HAZARD_ZONES:
        w.add_node("HazardZone", id=zid, name=name, hazard=hazard, aliases=aliases)
    regions = {}
    for rid, name, country, lat, lng, zone, aliases in catalog.REGIONS:
        regions[rid] = w.add_node("Region", id=rid, name=name, country=country, lat=lat, lng=lng, aliases=aliases)
        if zone:
            w.add_edge("IN_ZONE", rid, zone)
    for pid, name, country, kind, region, aliases in catalog.PORTS:
        r = regions[region]
        w.add_node("Port", id=pid, name=name, country=country, kind=kind, status="open",
                   lat=r["lat"], lng=r["lng"], aliases=aliases)
        w.add_edge("LOCATED_IN", pid, region)
    for plid, name, country, region, aliases, _sea, _air in catalog.PLANTS:
        r = regions[region]
        w.add_node("Plant", id=plid, name=name, country=country, lat=r["lat"], lng=r["lng"], aliases=aliases)
        w.add_edge("LOCATED_IN", plid, region)
    for cid, name, family, unit, cost in catalog.COMPONENTS:
        w.add_node("Component", id=cid, name=name, family=family, unit=unit, unit_cost_cents=cost)
    for pid, name, price, build_days, bom in catalog.PRODUCTS:
        w.add_node("Product", id=pid, name=name, unit_price_cents=price, build_days=build_days)
        for comp, qty in bom.items():
            w.add_edge("REQUIRES", pid, comp, qty=qty)
    lo, hi = catalog.STANDARD_PENALTY_RANGE
    for cid, name, country, tier, penalty in catalog.CUSTOMERS:
        if tier == "standard":
            penalty = rng.randrange(lo, hi + 1, 1_000)
        w.add_node("Customer", id=cid, name=name, country=country, tier=tier, penalty_per_day_cents=penalty)
    return regions


# ---------------------------------------------------------------------------
# Demand and orders
# ---------------------------------------------------------------------------

def _demand(rng: random.Random) -> dict[tuple[str, str], int]:
    """Weekly demand per (plant, product): fixed for motif products, drawn for fillers."""
    demand: dict[tuple[str, str], int] = {}
    for motif in motifs.MOTIFS.values():
        for plant, product, wk in motif["demand"]:
            demand[(plant, product)] = wk
    for plant, product, lo, hi in catalog.FILLER_DEMAND:
        demand[(plant, product)] = rng.randint(lo, hi)
    return demand


def _orders(w: World, demand: dict[tuple[str, str], int], rng: random.Random) -> None:
    build_days = {p[0]: p[3] for p in catalog.PRODUCTS}
    price = {p[0]: p[2] for p in catalog.PRODUCTS}
    strategic = [c[0] for c in catalog.CUSTOMERS if c[3] == "strategic" and c[0] != "CU-MER"]
    standard = [c[0] for c in catalog.CUSTOMERS if c[3] == "standard"]

    drafts = []
    for (plant, product) in sorted(demand):
        wk = demand[(plant, product)]
        due = rng.randint(4, 6)
        while due <= LAST_DUE_DAY:
            gap = rng.randint(2, 5)
            qty = max(1, round(wk * gap / 7 * rng.uniform(0.75, 1.25)))
            customer = rng.choice(strategic) if rng.random() < 0.2 else rng.choice(standard)
            drafts.append((due, plant, product, customer, qty))
            due += gap

    def add(order_id: str, customer: str, plant: str, product: str, qty: int, due: int) -> None:
        w.add_node("Order", id=order_id, qty=qty, due_day=due, need_day=due - build_days[product],
                   value_cents=qty * price[product], status="open", risk_flag=False)
        w.add_edge("PLACED", customer, order_id)
        w.add_edge("FOR_PRODUCT", order_id, product)
        w.add_edge("FULFILLED_AT", order_id, plant)

    for motif in motifs.MOTIFS.values():
        for order_id, customer, plant, product, qty, due in motif["orders"]:
            add(order_id, customer, plant, product, qty, due)
    for i, (due, plant, product, customer, qty) in enumerate(sorted(drafts)):
        add(f"SO-{1001 + i}", customer, plant, product, qty, due)


def component_orders(w: World) -> dict[tuple[str, str], list[tuple[int, int]]]:
    """(plant, component) -> [(need_day, units)] over every open order, sorted by need day."""
    bom: dict[str, list[tuple[str, int]]] = defaultdict(list)
    for e in w.edges["REQUIRES"]:
        bom[e["src"]].append((e["dst"], e["props"]["qty"]))
    product_of = {e["src"]: e["dst"] for e in w.edges["FOR_PRODUCT"]}
    plant_of = {e["src"]: e["dst"] for e in w.edges["FULFILLED_AT"]}
    out: dict[tuple[str, str], list[tuple[int, int]]] = defaultdict(list)
    for o in w.nodes["Order"]:
        for comp, qty in bom[product_of[o["id"]]]:
            out[(plant_of[o["id"]], comp)].append((o["need_day"], o["qty"] * qty))
    for v in out.values():
        v.sort()
    return dict(out)


# ---------------------------------------------------------------------------
# Filler supply chains
# ---------------------------------------------------------------------------

def _fill(w: World, covered: set[tuple[str, str]], regions: dict[str, dict[str, Any]], rng: random.Random) -> None:
    comp_info = {c[0]: c for c in catalog.COMPONENTS}
    plants = {p[0]: p for p in catalog.PLANTS}
    demand_orders = component_orders(w)
    need: dict[str, dict[str, list[tuple[int, int]]]] = defaultdict(dict)  # component -> plant -> orders
    for (plant, comp), orders in sorted(demand_orders.items()):
        if (plant, comp) not in covered:
            need[comp][plant] = orders

    suppliers_used: dict[str, tuple[str, str, str]] = {}
    site_region: dict[str, str] = {}
    site_ids = {s["id"] for s in w.nodes["Site"]}

    def new_site(family: str, tier: int, unit: str) -> dict[str, Any]:
        code, sname, country = rng.choice(catalog.FILL_SUPPLIERS)
        region = rng.choice(catalog.FILL_REGIONS[family])
        r = regions[region]
        base = f"S-{code}-{region[2:]}"
        site_id, n = base, 2
        while site_id in site_ids:
            site_id, n = f"{base}-{n}", n + 1
        site_ids.add(site_id)
        site_region[site_id] = region
        suppliers_used[code] = (code, sname, country)
        name = f"{sname} {r['name']}"
        w.add_edge("OPERATES", f"SUP-{code}", site_id)
        w.add_edge("LOCATED_IN", site_id, region)
        return w.add_node("Site", id=site_id, name=name, kind=catalog.FILL_SITE_KIND[family], tier=tier,
                          capacity_wk=0, unit=unit, capacity_factor=1.0, status="active",
                          input_buffer_days=rng.randint(3, 8),
                          lat=round(r["lat"] + rng.uniform(-0.2, 0.2), 3),
                          lng=round(r["lng"] + rng.uniform(-0.2, 0.2), 3),
                          aliases=f"{name}, {r['name']}, {code}")

    # Tier 1: one active site per filler component (supplying every plant that needs it), maybe one alternate.
    tier1: list[tuple[dict[str, Any], str, bool]] = []  # (site, component, is_active)
    for comp in sorted(need):
        _cid, _name, family, unit, cost = comp_info[comp]
        active = new_site(family, 1, unit)
        w.add_edge("MAKES", active["id"], comp, unit_price_cents=cost)
        total = 0
        for plant, orders in sorted(need[comp].items()):
            wk = math.ceil(sum(u for _, u in orders) / HORIZON_WEEKS)
            on_hand = math.ceil(wk * rng.uniform(1.5, 2.5))
            rate = max(math.ceil(wk * rng.uniform(1.10, 1.25)), _min_cover_rate(orders, on_hand))
            transit = _transit_days(regions[site_region[active["id"]]], plants[plant], regions)
            w.add_edge("SUPPLIES", active["id"], plant, component_id=comp, used_wk=rate,
                       unit_price_cents=round(cost * rng.uniform(0.95, 1.05)), transit_days=transit)
            w.add_edge("STOCKS", plant, comp, on_hand=on_hand, safety=wk // 2)
            total += rate
        active["capacity_wk"] = math.ceil(total * rng.uniform(1.15, 1.35))
        tier1.append((active, comp, True))

        if rng.random() < 0.6:
            alt = new_site(family, 1, unit)
            w.add_edge("MAKES", alt["id"], comp, unit_price_cents=round(cost * 1.1))
            spare_total = 0
            for plant, orders in sorted(need[comp].items()):
                wk = math.ceil(sum(u for _, u in orders) / HORIZON_WEEKS)
                spare = math.ceil(wk * rng.uniform(0.3, 0.8))
                w.add_edge("CAN_SUPPLY", alt["id"], plant, component_id=comp, spare_wk=spare,
                           unit_price_cents=round(cost * rng.uniform(1.05, 1.35)), lead_days=rng.randint(5, 14),
                           transit_days=_transit_days(regions[site_region[alt["id"]]], plants[plant], regions),
                           moq=max(50, round(spare * rng.uniform(0.3, 0.6) / 50) * 50), qualified=True,
                           air_transit_days=rng.randint(1, 3), air_surcharge_cents=max(50, cost // 10))
                spare_total += spare
            alt["capacity_wk"] = math.ceil(spare_total * rng.uniform(1.3, 1.8))
            tier1.append((alt, comp, False))

    # Tier 2: a small pool of sub-part makers per sub-part. Tier-1 sites draw from the pool,
    # so some "independent" suppliers share an upstream site, as in real networks.
    users: dict[str, list[tuple[dict[str, Any], str, bool]]] = defaultdict(list)
    for site, comp, is_active in tier1:
        users[catalog.FILL_SUBPART[comp][0]].append((site, comp, is_active))
    tier2: list[tuple[dict[str, Any], str]] = []
    for sub in sorted(users):
        _cid, _n, family, unit, cost = comp_info[sub]
        n_users = len(users[sub])
        pool = [new_site(family, 2, unit) for _ in range(1 + (n_users >= 2) + (n_users >= 4))]
        used_by: dict[str, int] = defaultdict(int)
        for site in pool:
            w.add_edge("MAKES", site["id"], sub, unit_price_cents=cost)
        for i, (t1, comp, is_active) in enumerate(users[sub]):
            qty = catalog.FILL_SUBPART[comp][1]
            n_feed = 2 if len(pool) >= 2 and rng.random() < 0.4 else 1
            # The first users take the pool in turn, so every pool site feeds someone.
            first = pool[i % len(pool)]
            feeders = [first] + rng.sample([p for p in pool if p is not first], n_feed - 1)
            for feeder in feeders:
                target = math.ceil(t1["capacity_wk"] * qty / n_feed)
                used = target if is_active else math.ceil(target * rng.uniform(0.3, 0.6))
                w.add_edge("FEEDS", feeder["id"], t1["id"], component_id=sub,
                           cap_wk=math.ceil(target * rng.uniform(1.1, 1.4)), used_wk=used)
                used_by[feeder["id"]] += used
        for site in pool:
            site["capacity_wk"] = max(100, math.ceil(used_by[site["id"]] * rng.uniform(1.15, 1.4)))
            tier2.append((site, sub))

    # Tier 3: raw inputs for the sub-parts that have one.
    raw_users: dict[str, list[tuple[dict[str, Any], str]]] = defaultdict(list)
    for site, sub in tier2:
        if sub in catalog.FILL_RAW:
            raw_users[catalog.FILL_RAW[sub][0]].append((site, sub))
    for raw in sorted(raw_users):
        _cid, _n, family, unit, cost = comp_info[raw]
        pool = [new_site(family, 3, unit) for _ in range(1 + (len(raw_users[raw]) >= 2))]
        used_by = defaultdict(int)
        for site in pool:
            w.add_edge("MAKES", site["id"], raw, unit_price_cents=cost)
        for i, (t2, sub) in enumerate(raw_users[raw]):
            feeder = pool[i] if i < len(pool) else rng.choice(pool)
            used = math.ceil(t2["capacity_wk"] * catalog.FILL_RAW[sub][1] * rng.uniform(0.8, 1.0))
            w.add_edge("FEEDS", feeder["id"], t2["id"], component_id=raw,
                       cap_wk=math.ceil(used * rng.uniform(1.1, 1.3)), used_wk=used)
            used_by[feeder["id"]] += used
        for site in pool:
            site["capacity_wk"] = max(100, math.ceil(used_by[site["id"]] * rng.uniform(1.15, 1.4)))

    for code in sorted(suppliers_used):
        _c, sname, country = suppliers_used[code]
        w.add_node("Supplier", id=f"SUP-{code}", name=sname, hq_country=country,
                   reliability=round(rng.uniform(0.85, 0.99), 2))


def _min_cover_rate(orders: list[tuple[int, int]], on_hand: int) -> int:
    """Smallest weekly rate (plus 5%) at which stock + steady inflow covers every order by its need day."""
    rate, cum = 0.0, 0
    for need_day, units in orders:
        cum += units
        if cum > on_hand:
            rate = max(rate, 7 * (cum - on_hand) / max(need_day, 1))
    return math.ceil(rate * 1.05)


# ---------------------------------------------------------------------------
# Plants, BOM depth, logistics
# ---------------------------------------------------------------------------

def _builds(w: World, demand: dict[tuple[str, str], int]) -> None:
    for (plant, product) in sorted(demand):
        w.add_edge("BUILDS", plant, product, cap_day=math.ceil(demand[(plant, product)] / 7 * 2))


def _made_from(w: World) -> None:
    w.add_edge("MADE_FROM", "BAT-4S", "CELL-21700", qty=4)
    w.add_edge("MADE_FROM", "BAT-6S", "CELL-21700", qty=6)
    w.add_edge("MADE_FROM", "DSP-14", "PNL-14", qty=1)
    w.add_edge("MADE_FROM", "DSP-14-HB", "PNL-14", qty=1)
    for comp, (sub, qty) in sorted(catalog.FILL_SUBPART.items()):
        w.add_edge("MADE_FROM", comp, sub, qty=qty)
    for sub, (raw, qty) in sorted(catalog.FILL_RAW.items()):
        w.add_edge("MADE_FROM", sub, raw, qty=qty)


def _km(a: dict[str, Any], b: dict[str, Any]) -> float:
    la1, lo1, la2, lo2 = map(math.radians, (a["lat"], a["lng"], b["lat"], b["lng"]))
    h = math.sin((la2 - la1) / 2) ** 2 + math.cos(la1) * math.cos(la2) * math.sin((lo2 - lo1) / 2) ** 2
    return 6371 * 2 * math.asin(math.sqrt(h))


def _transit_days(origin: dict[str, Any], plant: tuple, regions: dict[str, dict[str, Any]]) -> int:
    """Door-to-door days by surface from a site's region: trucking inside a country, sea otherwise."""
    km = _km(origin, regions[plant[3]])
    return 1 + int(km // 300) if origin["country"] == plant[2] else 3 + int(km // 600)


def _logistics(w: World, regions: dict[str, dict[str, Any]]) -> None:
    ports = {p["id"]: p for p in w.nodes["Port"]}
    sea = sorted(pid for pid, p in ports.items() if p["kind"] == "sea")
    air = sorted(pid for pid, p in ports.items() if p["kind"] == "air")
    for site in w.nodes["Site"]:
        for kind, ids in (("sea", sea), ("air", air)):
            pid = min(ids, key=lambda i: (_km(site, ports[i]), i))
            km = _km(site, ports[pid])
            w.add_edge("SHIPS_VIA", site["id"], pid, days=1 + int(km // 300), cost_cents=20 + int(km // 10), mode=kind)
    for plid, _n, _c, _r, _a, sea_port, air_port in catalog.PLANTS:
        w.add_edge("DELIVERS_TO", sea_port, plid, days=1, cost_cents=30, mode="sea")
        w.add_edge("DELIVERS_TO", air_port, plid, days=1, cost_cents=30, mode="air")
        for src in sea:
            if src != sea_port:
                km = _km(ports[src], ports[sea_port])
                days = 2 + int(km // 550)
                w.add_edge("LANE", src, sea_port, days=days, eff_days=days, cost_cents=40 + int(km // 40),
                           mode="sea", cap_wk=100_000)
        for src in air:
            if src != air_port:
                km = _km(ports[src], ports[air_port])
                days = 1 + int(km // 6000)
                w.add_edge("LANE", src, air_port, days=days, eff_days=days, cost_cents=300 + int(km // 8),
                           mode="air", cap_wk=20_000)


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------

def pristine_cover_gaps(w: World) -> list[dict[str, Any]]:
    """(plant, component) pairs where stock + steady supply misses an order's need day. Expected: none.

    This is a generator self-check on the healthy world, not the shortage engine (M3).
    """
    on_hand = {(e["src"], e["dst"]): e["props"]["on_hand"] for e in w.edges["STOCKS"]}
    rate: dict[tuple[str, str], int] = defaultdict(int)
    for e in w.edges["SUPPLIES"]:
        rate[(e["dst"], e["props"]["component_id"])] += e["props"]["used_wk"]
    gaps = []
    for key, orders in sorted(component_orders(w).items()):
        cum = 0
        for need_day, units in orders:
            cum += units
            have = on_hand.get(key, 0) + rate[key] * need_day // 7
            if cum > have:
                gaps.append({"plant": key[0], "component": key[1], "need_day": need_day, "short": cum - have})
                break
    return gaps


def validate(w: World) -> None:
    """Raise ValueError if the world breaks a structural rule."""
    ids: dict[str, str] = {}
    problems: list[str] = []
    for group, rows in w.nodes.items():
        for r in rows:
            if r["id"] in ids:
                problems.append(f"duplicate id {r['id']} ({ids[r['id']]} and {group})")
            ids[r["id"]] = group
            for k, v in r.items():
                if isinstance(v, float) and k not in FLOAT_PROPS:
                    problems.append(f"{r['id']}.{k} is a float; units must be integers")
    for rel, (src_groups, dst_groups) in EDGE_TYPES.items():
        for e in w.edges[rel]:
            if ids.get(e["src"]) not in src_groups:
                problems.append(f"{rel} source {e['src']} is not a {src_groups}")
            if ids.get(e["dst"]) not in dst_groups:
                problems.append(f"{rel} target {e['dst']} is not a {dst_groups}")
            for k, v in e["props"].items():
                if isinstance(v, float):
                    problems.append(f"{rel} {e['src']}->{e['dst']}.{k} is a float")
    # The Monsoon flood zone must hold only VoltCell, so the tier-1 view really sees 0 sites.
    zone_regions = {e["src"] for e in w.edges["IN_ZONE"] if e["dst"] == "Z-CPB"}
    in_zone = sorted(e["src"] for e in w.edges["LOCATED_IN"] if e["dst"] in zone_regions and ids[e["src"]] == "Site")
    if in_zone != ["S-VOLT-AYU"]:
        problems.append(f"sites in the Chao Phraya Basin should be only S-VOLT-AYU, got {in_zone}")
    for gap in pristine_cover_gaps(w):
        problems.append(f"pristine world short: {gap}")
    if problems:
        raise ValueError("invalid world:\n  " + "\n  ".join(problems[:30]))
