"""M7: public-demo protections. The /mcp API key and the live-run quota (no API calls are made)."""

import pytest
from fastapi.testclient import TestClient

from domino.agent.scripted import ScriptedClient
from domino.api import runs
from domino.config import settings
from domino.graph.lifecycle import build_pristine, drop_graph
from domino.seed.generator import generate

PRISTINE, LIVE = "test:m7:pristine", "test:m7:live"


@pytest.fixture(scope="module")
def app():
    build_pristine(generate(42), PRISTINE)
    from domino.api.main import app
    yield app
    drop_graph(PRISTINE)
    drop_graph(LIVE)


def test_mcp_requires_the_key_when_one_is_set(app, monkeypatch):
    monkeypatch.setattr(settings, "mcp_api_key", "s3cret")
    # raise_server_exceptions=False: past the key check, the MCP SDK may refuse a second session manager
    # start in this pytest process; only the key check's answer matters here.
    with TestClient(app, raise_server_exceptions=False) as c:
        assert c.post("/mcp/", json={}).status_code == 401
        assert c.post("/mcp/", json={}, headers={"X-API-Key": "wrong"}).status_code == 401
        assert c.post("/mcp/", json={}, headers={"Authorization": "Bearer s3cret"}).status_code != 401
        assert c.get("/api/health").status_code == 200        # the REST API is not behind the MCP key


def test_live_runs_are_rate_limited_per_visitor(app, monkeypatch):
    # A "live" run here still uses the scripted model, so no API credit is spent by this test.
    monkeypatch.setattr(runs, "_client", lambda scenario, dry_run: ScriptedClient(scenario))
    monkeypatch.setattr(settings, "live_runs_per_hour_per_ip", 2)
    monkeypatch.setattr(settings, "world_graph_pristine", PRISTINE)
    monkeypatch.setattr(settings, "world_graph_live", LIVE)
    runs._live_by_ip.clear()
    runs._live_all.clear()
    with TestClient(app) as c:
        c.post("/api/world/reset")
        codes = [c.post("/api/runs", json={"scenario": "non_event"}).status_code for _ in range(3)]
        assert codes == [200, 200, 429]
        assert c.post("/api/runs", json={"scenario": "non_event", "dry_run": True}).status_code == 200
        assert c.post("/api/runs", json={"alert_text": "x" * 2001, "dry_run": True}).status_code == 400
