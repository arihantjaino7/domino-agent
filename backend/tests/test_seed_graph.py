"""Loader, schema and lifecycle tests against the running FalkorDB (uses test:* graphs only)."""

import pytest

from domino.graph.lifecycle import build_pristine, drop_graph, graph_counts, reset_live
from domino.graph.run_query import ResultTruncatedError, run_query
from domino.seed.generator import generate

PRISTINE, LIVE = "test:m2:pristine", "test:m2:live"


@pytest.fixture(scope="module")
def world():
    w = generate(42)
    build_pristine(w, PRISTINE)
    reset_live(PRISTINE, LIVE)
    yield w
    drop_graph(PRISTINE)
    drop_graph(LIVE)


def test_live_copy_matches_generated_counts(world):
    counts = graph_counts(LIVE)
    expected = {k: v for k, v in world.counts().items() if v}
    expected["Meta"] = 1
    assert counts == expected


def test_voltcell_feeds_three_tier1_sites_on_live(world):
    rows = run_query("checks/feeds_from", {"site_id": "S-VOLT-AYU"}, graph=LIVE)
    assert [r["target"] for r in rows] == ["S-AMPR-JHB", "S-BMAX-PEN", "S-PWRC-HPG"]
    assert all(r["tier"] == 1 and r["component"] == "CELL-21700" for r in rows)
    assert {r["target"]: r["used_wk"] for r in rows} == {"S-AMPR-JHB": 0, "S-BMAX-PEN": 4800, "S-PWRC-HPG": 2520}


def test_no_duplicate_ids_in_graph(world):
    assert run_query("checks/duplicate_ids", graph=LIVE) == []


def test_copy_carries_indexes_and_constraint(world):
    assert run_query("schema/indexes_list", graph=LIVE) == run_query("schema/indexes_list", graph=PRISTINE)
    cons = run_query("schema/constraints", graph=LIVE)
    assert [(c["label"], c["properties"], c["status"]) for c in cons] == [("PurchaseOrder", ["id"], "OPERATIONAL")]


def test_fulltext_finds_places_by_name_alias_and_typo(world):
    assert "S-VOLT-AYU" in [r["id"] for r in run_query("checks/fulltext_place", {"term": "Ayutthaya"}, graph=LIVE)]
    assert "Z-CPB" in [r["id"] for r in run_query("checks/fulltext_place", {"term": "Chao Phraya"}, graph=LIVE)]
    assert "R-AYU" in [r["id"] for r in run_query("checks/fulltext_place", {"term": "%Ayuthaya%"}, graph=LIVE)]


def test_reads_are_read_only(world):
    from domino.graph.run_query import QueryError
    with pytest.raises(QueryError):
        run_query("seed/meta", {"seed": 1, "fingerprint": "x"}, graph=LIVE)  # a write sent as ro


def test_full_result_raises_instead_of_truncating(monkeypatch, world):
    import domino.graph.run_query as rq
    monkeypatch.setattr(rq, "resultset_size", lambda: 5)
    with pytest.raises(ResultTruncatedError):
        run_query("checks/count_edges", graph=LIVE)  # 17 edge types > 5
