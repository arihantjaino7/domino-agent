"""Memory tab: GET /api/memory reads past incidents and lessons, each with the date it was learned.

Uses test:m9:* graphs and the tiny world, so the real `memory` graph is never touched.
"""

import datetime as dt

import pytest
from fastapi.testclient import TestClient

from domino.agent import memory
from domino.api.main import app
from domino.config import settings
from domino.graph.lifecycle import build_pristine, drop_graph
from tests.fixtures.tiny_world import tiny_world

WORLD, REAL, DEMO, EMPTY = "test:m9:world", "test:m9:memory", "test:m9:dryrun", "test:m9:empty"


@pytest.fixture(scope="module", autouse=True)
def graphs():
    build_pristine(tiny_world(), WORLD)
    memory.record_incident({"id": "INC-0007", "title": "Flood in the test basin", "outcome": "recorded"},
                           [{"id": "S-UP", "kind": "Site", "name": "Site S-UP", "role": "involved"},
                            {"id": "S-GONE", "kind": "Site", "name": "S-GONE", "role": "involved"}], graph=REAL)
    memory.record_lessons("INC-0007", [
        {"text": "S-UP feeds S-T1 and S-ALT; the backup is not independent.", "entity_ids": ["S-UP", "S-ALT"],
         "evidence": "E2,E5"},
        {"text": "Check tier-2 before trusting a tier-1 list.", "entity_ids": ["S-GONE"], "evidence": ""}],
        graph=REAL)
    memory.record_incident({"id": "INC-0001", "title": "Scripted demo flood", "outcome": "recorded"},
                           [{"id": "S-T1", "kind": "Site", "name": "S-T1", "role": "involved"}], graph=DEMO)
    memory.record_lessons("INC-0001", [{"text": "Scripted lesson.", "entity_ids": ["S-T1"]}], graph=DEMO)
    yield
    for g in (WORLD, REAL, DEMO, EMPTY):
        drop_graph(g)


@pytest.fixture(autouse=True)
def point_at_test_graphs(monkeypatch):
    monkeypatch.setattr(settings, "world_graph_live", WORLD)
    monkeypatch.setattr(settings, "memory_graph", REAL)
    monkeypatch.setattr(settings, "memory_graph_dryrun", DEMO)


def _get(**params):
    with TestClient(app) as c:
        r = c.get("/api/memory", params=params)
    assert r.status_code == 200, r.text
    return r.json()


def test_real_memory_lists_incidents_and_lessons_with_learned_on():
    body = _get()                                          # source defaults to "real"
    assert body["source"] == "real" and body["graph"] == REAL
    assert body["counts"] == {"incidents": 1, "lessons": 2}
    today = dt.date.today().isoformat()
    inc = body["incidents"][0]
    assert (inc["id"], inc["title"], inc["learned_on"]) == ("INC-0007", "Flood in the test basin", today)
    les = {l["id"]: l for l in body["lessons"]}
    assert set(les) == {"L-INC-0007-1", "L-INC-0007-2"}
    assert all(l["learned_on"] == today and l["incident_id"] == "INC-0007" for l in les.values())
    assert les["L-INC-0007-1"]["evidence"] == ["E2", "E5"]  # stored "E2,E5", returned as ids
    assert les["L-INC-0007-2"]["evidence"] == []


def test_entity_names_come_from_the_world_and_unknown_ids_are_flagged_not_hidden():
    body = _get(source="real")
    ents = {e["id"]: e for e in body["incidents"][0]["entities"]}
    assert ents["S-UP"] == {"id": "S-UP", "name": "Site S-UP", "kind": "Site", "in_world": True}
    # Not in this world: still listed, marked in_world=False (not in the graph is not the same as safe).
    assert ents["S-GONE"] == {"id": "S-GONE", "name": "S-GONE", "kind": None, "in_world": False}
    les = next(l for l in body["lessons"] if l["id"] == "L-INC-0007-1")
    assert [e["id"] for e in les["entities"]] == ["S-ALT", "S-UP"]


def test_demo_memory_is_a_separate_graph():
    body = _get(source="demo")
    assert body["graph"] == DEMO and body["counts"] == {"incidents": 1, "lessons": 1}
    assert body["incidents"][0]["id"] == "INC-0001"
    assert body["lessons"][0]["text"] == "Scripted lesson."


def test_empty_memory_returns_empty_lists(monkeypatch):
    monkeypatch.setattr(settings, "memory_graph", EMPTY)   # graph key does not exist yet (fresh deploy)
    body = _get()
    assert body["incidents"] == [] and body["lessons"] == []
    assert body["counts"] == {"incidents": 0, "lessons": 0}


def test_only_the_two_memory_graphs_can_be_read():
    with TestClient(app) as c:
        assert c.get("/api/memory", params={"source": "world:live"}).status_code == 422
