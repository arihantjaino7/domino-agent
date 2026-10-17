"""M8: the Cypher drawer groups every query a tool ran, so the war room can show the exact text and params."""
from domino.graph.run_query import QueryRecord, group_records


def rec(name: str, rows: int, ms: float, graph: str = "world:live", params: dict | None = None) -> QueryRecord:
    return QueryRecord(name=name, cypher=f"// {name}\nRETURN 1", params=params or {"x": 1}, ms=ms, rows=rows, graph=graph, ro=True)


def test_group_records_keeps_first_run_order_and_first_params():
    out = group_records([rec("a/one", 2, 1.5, params={"p": 1}), rec("b/two", 0, 0.5), rec("a/one", 3, 2.25, params={"p": 2})])
    assert [g["name"] for g in out] == ["a/one", "b/two"]
    first = out[0]
    assert first["calls"] == 2 and first["rows"] == 5 and first["ms"] == 3.75
    assert first["params"] == {"p": 1}  # the drawer shows the first call's params
    assert first["cypher"].startswith("// a/one")


def test_group_records_lists_each_graph_once():
    out = group_records([rec("s/x", 1, 1, "world:live"), rec("s/x", 1, 1, "sandbox:r:S1"), rec("s/x", 1, 1, "world:live")])
    assert out[0]["graphs"] == ["world:live", "sandbox:r:S1"]


def test_group_records_empty():
    assert group_records([]) == []
