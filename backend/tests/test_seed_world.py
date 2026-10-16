"""Generator tests (pure Python, no database)."""

from domino.seed import motifs
from domino.seed.generator import generate, pristine_cover_gaps, validate
from domino.seed.world import World

SEED = 42


def test_same_seed_gives_identical_world():
    a, b = generate(SEED), generate(SEED)
    assert a == b
    assert a.fingerprint() == b.fingerprint()


def test_different_seed_changes_the_random_fill_only():
    a, b = generate(SEED), generate(SEED + 1)
    assert a.fingerprint() != b.fingerprint()
    # The hand-built motif sites are identical in every world.
    motif_ids = {s[0] for m in motifs.MOTIFS.values() for s in m["sites"]}
    pick = lambda w: sorted((s["id"], s["capacity_wk"]) for s in w.nodes["Site"] if s["id"] in motif_ids)  # noqa: E731
    assert pick(a) == pick(b)


def test_every_id_is_unique():
    w = generate(SEED)
    ids = [r["id"] for rows in w.nodes.values() for r in rows]
    assert len(ids) == len(set(ids))


def test_size_is_about_300_nodes():
    w = generate(SEED)
    assert 250 <= w.n_nodes <= 450
    assert w.n_edges >= 2 * w.n_nodes


def test_ids_use_prefixes():
    w = generate(SEED)
    prefixes = {"Site": "S-", "Supplier": "SUP-", "Region": "R-", "HazardZone": "Z-", "Plant": "PL-",
                "Customer": "CU-", "Order": "SO-"}
    for group, prefix in prefixes.items():
        assert all(r["id"].startswith(prefix) for r in w.nodes[group]), group
    assert all(r["id"][:2] in ("P-", "A-") for r in w.nodes["Port"])


def test_monsoon_voltcell_feeds_two_active_and_one_alternate_tier1():
    w = generate(SEED)
    feeds = {e["dst"]: e["props"] for e in w.edges_of("FEEDS", src="S-VOLT-AYU")}
    assert sorted(feeds) == ["S-AMPR-JHB", "S-BMAX-PEN", "S-PWRC-HPG"]
    assert feeds["S-PWRC-HPG"] == {"component_id": "CELL-21700", "cap_wk": 2800, "used_wk": 2520}
    assert feeds["S-BMAX-PEN"]["used_wk"] == 4800
    assert feeds["S-AMPR-JHB"]["cap_wk"] == 2800
    active = {e["src"] for e in w.edges["SUPPLIES"]}
    alternate = {e["src"] for e in w.edges["CAN_SUPPLY"]}
    assert {"S-PWRC-HPG", "S-BMAX-PEN"} <= active
    assert "S-AMPR-JHB" in alternate and "S-AMPR-JHB" not in active
    assert w.node("S-VOLT-AYU")["tier"] == 2
    assert {w.node(t)["tier"] for t in feeds} == {1}


def test_voltcell_is_the_only_site_in_the_flood_zone():
    w = generate(SEED)
    zone_regions = {e["src"] for e in w.edges_of("IN_ZONE", dst="Z-CPB")}
    site_ids = {s["id"] for s in w.nodes["Site"]}
    in_zone = {e["src"] for e in w.edges["LOCATED_IN"] if e["dst"] in zone_regions and e["src"] in site_ids}
    assert in_zone == {"S-VOLT-AYU"}


def test_panel_fire_structure_and_compatibility_trap():
    w = generate(SEED)
    assert [e["dst"] for e in w.edges_of("SUPPLIES", src="S-LMVU-SUZ")] == ["PL-BAC"]
    kb14_parts = {e["dst"] for e in w.edges_of("REQUIRES", src="KB14")} | {
        e["dst"] for e in w.edges_of("ALLOWS_ALTERNATE", src="KB14")}
    assert "DSP-14" in kb14_parts and "DSP-14-HB" not in kb14_parts
    nova = w.edges_of("CAN_SUPPLY", src="S-NOVA-GUM")
    assert [e["props"]["component_id"] for e in nova] == ["DSP-14-HB"]


def test_meridian_strategic_order_due_around_day_28():
    w = generate(SEED)
    order = w.node("SO-1000")
    assert order["due_day"] == 28 and order["qty"] == 450
    assert w.edges_of("PLACED", dst="SO-1000")[0]["src"] == "CU-MER"
    assert w.node("CU-MER")["tier"] == "strategic"


def test_pristine_world_covers_every_order():
    assert pristine_cover_gaps(generate(SEED)) == []


def test_units_are_integers():
    w = generate(SEED)
    validate(w)  # raises on floats outside capacity_factor/reliability/lat/lng
    for e in w.edges["SUPPLIES"] + w.edges["CAN_SUPPLY"] + w.edges["FEEDS"]:
        assert all(isinstance(v, (int, str, bool)) for v in e["props"].values())


def test_validate_catches_a_dangling_edge():
    w = generate(SEED)
    w.add_edge("FEEDS", "S-NOPE", "S-PWRC-HPG", component_id="CELL-21700", cap_wk=1, used_wk=1)
    try:
        validate(w)
    except ValueError as exc:
        assert "S-NOPE" in str(exc)
    else:
        raise AssertionError("validate accepted a dangling edge")


def test_world_type():
    assert isinstance(generate(SEED), World)
