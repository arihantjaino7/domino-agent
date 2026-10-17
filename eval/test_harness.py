"""Harness checks without a database: metrics, export preservation and fail-closed behavior."""

import json
from types import SimpleNamespace

import pytest

from eval.offline import check_seed
from eval.report import percentile, render
from eval.run import Evaluation, classification, compare_projection
from scripts.export_world_json import write_export
from eval.oracle import World
from eval.fixtures import snapshot, cases


def test_confusion_counts_do_not_hide_false_positives_or_empty_sets():
    assert classification({"A", "B"}, {"A", "C"}) == {
        "tp": 1, "fp": 1, "fn": 1, "false_positive_ids": ["B"], "false_negative_ids": ["C"]}
    assert classification(set(), set())["tp"] == 0


def test_percentiles_are_nearest_rank_not_interpolated():
    assert percentile([1, 2, 3, 4], .5) == 2
    assert percentile([1, 2, 3, 4], .95) == 4
    assert percentile([], .95) is None


def test_projection_comparison_catches_wrong_order_even_if_totals_match():
    actual = {"orders": [{"order_id": "A", "ready_day": 2}, {"order_id": "B", "ready_day": 1}],
              "totals": {"penalty_exposure_cents": 0}, "pos": []}
    expected = {"ready": {"A": 1, "B": 2}, "penalty_cents": 0, "rates": {}}
    assert len(compare_projection(actual, expected)) == 2


def test_export_is_deterministic_and_round_trips(tmp_path):
    data = snapshot(cases()[0]["world"])
    a, b = tmp_path / "a.json.gz", tmp_path / "b.json.gz"
    assert write_export(data, a) == write_export(data, b)
    assert a.read_bytes() == b.read_bytes()
    assert World.read(a).data == data


def test_cleanup_refuses_live_graphs(tmp_path):
    ev = Evaluation(tmp_path / "results.json")
    for graph in ["world:live", "world:pristine", "memory", "memory:dryrun", "eval:someone-else:base"]:
        with pytest.raises(ValueError, match="Refusing"):
            ev.drop(graph)


@pytest.mark.parametrize("seed", [42, 43, 61])
def test_independent_generated_projection_regression(seed):
    checks = check_seed(seed)
    assert all(r["ok"] for r in checks), checks


def test_blocked_report_does_not_claim_success_or_real_model_measurement():
    data = {"cases": [], "failures": [{"case": "run", "kind": "environment", "details": "unavailable"}],
            "seeds": [42], "scripted_repeats": 0, "budget_cents": 25_000_000, "horizon_days": 42,
            "healthy": [], "scripted": [], "query_samples_ms": {}, "generated_utc": "fixed",
            "elapsed_seconds": 0, "provenance": {"git_head": "test", "source_sha256": "test",
            "python": "3.12", "networkx": "3.7", "graph_module_ver": None, "platform": "test"}}
    report = render(data)
    assert "INCOMPLETE / FAIL" in report
    assert "No database recovery scores were collected" in report
    assert "A/real-model agency is **not measured**" in report


def test_persistence_failure_saves_report_and_never_starts_graph_writes(tmp_path, monkeypatch):
    import eval.run as runner
    output = tmp_path / "results.json"
    monkeypatch.setattr("sys.argv", ["eval.run", "--seed-count", "1", "--scripted-repeats", "0", "--output", str(output)])
    connection = SimpleNamespace(info=lambda name: {"rdb_last_bgsave_status": "err"})
    monkeypatch.setattr(runner, "bound_connection", lambda: None)
    monkeypatch.setattr(runner, "get_db", lambda: SimpleNamespace(connection=connection))
    monkeypatch.setattr(runner, "provenance", lambda: {"git_head": "test", "source_sha256": "test",
        "python": "3.12", "networkx": "3.7", "graph_module_ver": None, "platform": "test"})
    def forbidden(*args, **kwargs):
        pytest.fail("Unhealthy persistence must prevent graph writes")
    monkeypatch.setattr(runner, "build_pristine", forbidden)
    with pytest.raises(SystemExit) as exc:
        runner.main()
    assert exc.value.code == 1
    data = json.loads(output.read_text(encoding="utf-8"))
    assert not data["cases"]
    assert {r["kind"] for r in data["failures"]} == {"environment_or_runner", "incomplete_coverage"}
    assert "INCOMPLETE / FAIL" in output.with_name("RESULTS.md").read_text(encoding="utf-8")
