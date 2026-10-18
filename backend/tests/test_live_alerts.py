"""Live-alert screening: fixed coordinates, stubbed feeds, and the read-only graph query."""

import io
import json
from unittest.mock import Mock
from urllib.error import HTTPError

import pytest
from fastapi.testclient import TestClient

from domino.api import live
from domino.api.main import app
from domino.graph.lifecycle import build_pristine, drop_graph
from domino.graph.run_query import capture_queries, run_query
from domino.seed.generator import generate


def feature(code="FL", event_id=1, lat=0, lng=0, **properties):
    return {"type": "Feature", "geometry": {"type": "Point", "coordinates": [lng, lat]},
            "properties": {"eventtype": code, "eventid": event_id, "name": "Flood in Testland",
                           "country": "Testland", "alertlevel": "Orange", "iscurrent": "true",
                           "fromdate": "2026-10-17T00:00:00", "todate": "2026-10-18T00:00:00",
                           "datemodified": "2026-10-18T06:00:00", **properties}}


def payload(*features):
    return {"type": "FeatureCollection", "features": list(features)}


def place(id="S-NEAR", lat=0, lng=1, kind="Site", tier=2):
    return {"id": id, "name": id, "lat": lat, "lng": lng, "kind": kind, "tier": tier}


@pytest.fixture(autouse=True)
def clear_cache(monkeypatch):
    monkeypatch.setattr(live, "_cache", None)


def test_haversine_hand_computed_equator_and_antimeridian():
    # One degree on a sphere of radius 6371 km is pi * 6371 / 180 = 111.19492664 km.
    assert live.haversine_km(0, 0, 0, 1) == pytest.approx(111.19492664)
    assert live.haversine_km(0, 179, 0, -179) == pytest.approx(222.38985329)
    assert live.haversine_km(45, 80, 45, 80) == 0
    assert live.haversine_km(0, 0, 0, 180) == pytest.approx(20015.086796)


def test_fixed_distances_match_only_nearby_places_and_sites():
    places = [place(), place("S-FAR", lng=2), place("PL-NEAR", lng=0.5, kind="Plant", tier=None),
              place("PORT-NEAR", lng=0.25, kind="Port", tier=None),
              place("R-NEAR", lng=0, kind="Region", tier=None)]
    event, = live.match_events(payload(feature()), places)
    assert event["in_graph"] is True
    assert event["site_ids"] == ["S-NEAR"]
    assert event["sites"] == [{"id": "S-NEAR", "name": "S-NEAR", "kind": "Site", "tier": 2, "distance_km": 111.19}]
    assert {p["kind"] for p in event["places"]} == {"Site", "Plant", "Port", "Region"}
    assert event["lat"] == 0 and event["lng"] == 0
    assert event["updated_at"] == "2026-10-18T06:00:00+00:00"
    assert "S-NEAR" in event["alert_text"] and "S-FAR" not in event["alert_text"]


@pytest.mark.parametrize(("code", "radius", "inside", "outside"), [
    ("FL", 150, 1, 1.35), ("EQ", 150, 1, 1.35), ("TC", 400, 3.5, 4),
    ("DR", 300, 2.5, 3), ("VO", 100, 0.8, 1), ("WF", 100, 0.8, 1),
])
def test_event_radius_rules(code, radius, inside, outside):
    event, = live.match_events(payload(feature(code)), [place(lng=inside), place("S-OUT", lng=outside)])
    assert event["radius_km"] == radius
    assert event["site_ids"] == ["S-NEAR"]


def test_radius_boundary_uses_full_precision(monkeypatch):
    monkeypatch.setitem(live.RADII_KM, "FL", live.haversine_km(0, 0, 0, 1))
    event, = live.match_events(payload(feature()), [place(), place("S-OUT", lng=1.000001)])
    assert event["site_ids"] == ["S-NEAR"]


def test_no_nearby_place_is_explicitly_not_in_graph():
    event, = live.match_events(payload(feature()), [place(lng=2)])
    assert event["in_graph"] is False
    assert event["sites"] == event["places"] == event["site_ids"] == []
    assert "Not in the graph. Not being in the graph does not mean safe." in event["alert_text"]
    assert "no impact" not in event["alert_text"].lower()


def test_non_supplier_match_does_not_become_a_stoppable_site():
    event, = live.match_events(payload(feature()), [place("PL-NEAR", kind="Plant", tier=None)])
    assert event["in_graph"] is True
    assert event["site_ids"] == []
    assert event["places"][0]["kind"] == "Plant"
    assert "No supplier sites within the screening radius" in event["alert_text"]


def test_bad_individual_features_and_coordinates_do_not_hide_valid_events():
    bad_geometry = feature(event_id=3)
    bad_geometry["geometry"]["type"] = "Polygon"
    events = live.match_events(payload(None, {}, feature(lat=91), feature(lng=float("nan")),
                                       feature(iscurrent="false"), feature("UNKNOWN"), bad_geometry,
                                       feature(event_id=9)), [place(), place("BAD", lat=None)])
    assert [e["id"] for e in events] == ["FL-9"]


def test_latest_episode_wins_and_missing_dates_remain_unknown():
    old = feature(name="Old episode", datemodified="2026-10-17T06:00:00")
    current = feature(name="New episode")
    missing = feature(event_id=2, datemodified="invalid", fromdate=None, todate=None, country=None)
    events = live.match_events(payload(current, old, missing), [])
    by_id = {e["id"]: e for e in events}
    assert by_id["FL-1"]["title"] == "New episode"
    assert by_id["FL-2"]["updated_at"] is None
    assert by_id["FL-2"]["country"] == "Country not provided"


def test_endpoint_success_uses_named_read_and_rechecks_graph(monkeypatch):
    fetch = Mock(return_value=payload(feature()))
    query = Mock(side_effect=[[place()], []])
    monkeypatch.setattr(live, "_fetch_feed", fetch)
    monkeypatch.setattr(live, "run_query", query)
    client = TestClient(app)
    first, second = client.get("/api/live-alerts"), client.get("/api/live-alerts")
    assert first.status_code == second.status_code == 200
    assert first.json()["events"][0]["in_graph"] is True
    assert second.json()["events"][0]["in_graph"] is False
    assert first.json()["updated_at"] == second.json()["updated_at"]
    assert first.json()["source"] == "gdacs"
    fetch.assert_called_once()
    assert query.call_count == 2
    query.assert_called_with("graph/place_coords", graph=live.settings.world_graph_live)


def test_feed_cache_expires_after_ten_minutes(monkeypatch):
    now = [100.0]
    fetch = Mock(return_value=payload(feature()))
    monkeypatch.setattr(live.time, "monotonic", lambda: now[0])
    monkeypatch.setattr(live, "_fetch_feed", fetch)
    live._feed()
    now[0] += 599
    live._feed()
    assert fetch.call_count == 1
    now[0] += 1
    live._feed()
    assert fetch.call_count == 2


def test_feed_failure_returns_empty_200_then_recovers(monkeypatch):
    fetch = Mock(side_effect=[TimeoutError("upstream timeout"), payload(feature())])
    query = Mock(return_value=[])
    monkeypatch.setattr(live, "_fetch_feed", fetch)
    monkeypatch.setattr(live, "run_query", query)
    client = TestClient(app)
    response = client.get("/api/live-alerts")
    assert response.status_code == 200
    assert response.json()["events"] == [] and response.json()["source"] == "gdacs"
    assert response.json()["error"] and response.json()["updated_at"] is None
    query.assert_not_called()
    assert "error" not in client.get("/api/live-alerts").json()


def test_graph_failure_returns_empty_200_without_claiming_no_matches(monkeypatch):
    monkeypatch.setattr(live, "_fetch_feed", lambda: payload(feature()))
    monkeypatch.setattr(live, "run_query", Mock(side_effect=RuntimeError("database unavailable")))
    response = TestClient(app).get("/api/live-alerts")
    assert response.status_code == 200
    assert response.json()["events"] == []
    assert "locations" in response.json()["error"]


def test_fetch_covers_every_hazard_with_eight_second_timeout(monkeypatch):
    calls = []
    def opened(request, timeout):
        code = request.full_url.split("=")[-1]
        calls.append((code, timeout))
        return io.BytesIO(json.dumps(payload(feature(code))).encode())
    monkeypatch.setattr(live, "urlopen", opened)
    feed = live._fetch_feed()
    assert {f["properties"]["eventtype"] for f in feed["features"]} == set(live.EVENT_TYPES)
    assert set(calls) == {(code, 8) for code in live.EVENT_TYPES}


def test_malformed_feed_returns_empty_200(monkeypatch):
    monkeypatch.setattr(live, "urlopen", lambda *a, **kw: io.BytesIO(b'{"unexpected":true}'))
    response = TestClient(app).get("/api/live-alerts")
    assert response.status_code == 200
    assert response.json()["events"] == [] and response.json()["error"]


def test_empty_feed_stays_empty_without_error(monkeypatch):
    monkeypatch.setattr(live, "_fetch_feed", lambda: payload())
    monkeypatch.setattr(live, "run_query", lambda *a, **kw: [])
    response = TestClient(app).get("/api/live-alerts")
    assert response.json()["events"] == [] and "error" not in response.json()


def test_place_coords_query_on_falkordb_is_read_only_and_covers_all_place_kinds():
    graph = "test:live-alerts:coords"
    world = generate(42)
    try:
        build_pristine(world, graph)
        with capture_queries() as queries:
            places = run_query("graph/place_coords", graph=graph)
        assert {p["kind"] for p in places} == {"Site", "Plant", "Port", "Region"}
        assert len(places) == sum(len(world.nodes[kind]) for kind in ("Site", "Plant", "Port", "Region"))
        assert all(p["lat"] is not None and p["lng"] is not None for p in places)
        assert all(q.ro for q in queries)
        event, = live.match_events(payload(feature(lat=14.35, lng=100.57)), places)
        assert "S-VOLT-AYU" in event["site_ids"]
    finally:
        drop_graph(graph)


def test_cyclone_track_positions_are_not_separate_event_centroids():
    track = feature("TC", lat=0, lng=0, Class="Point_Polygon_Point_0")
    centroid = feature("TC", lat=0, lng=20, Class="Point_Centroid")
    event, = live.match_events(payload(track, centroid), [place()])
    assert event["lng"] == 20
    assert event["in_graph"] is False


def test_map_404_uses_search_within_the_same_timeout_budget(monkeypatch):
    calls = []
    def opened(request, timeout):
        calls.append((request.full_url, timeout))
        if "MAP?" in request.full_url:
            raise HTTPError(request.full_url, 404, "Not Found", {}, None)
        return io.BytesIO(json.dumps(payload(feature("VO"))).encode())
    monkeypatch.setattr(live, "urlopen", opened)
    assert live._fetch_type("VO")[0]["properties"]["eventtype"] == "VO"
    assert "/SEARCH?eventlist=VO" in calls[1][0]
    assert "fromdate=" in calls[1][0] and "alertlevel=" in calls[1][0]
    assert 0 < calls[1][1] <= 8


def test_upstream_errors_other_than_missing_map_do_not_look_like_empty_feeds(monkeypatch):
    monkeypatch.setattr(live, "urlopen", Mock(side_effect=HTTPError("https://gdacs.org", 503, "Unavailable", {}, None)))
    response = TestClient(app).get("/api/live-alerts")
    assert response.json()["events"] == [] and response.json()["error"]
