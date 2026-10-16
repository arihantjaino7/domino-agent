from fastapi.testclient import TestClient

from domino.api.main import app


def test_health_pings_falkordb():
    with TestClient(app) as client:
        resp = client.get("/api/health")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "ok"
    assert body["falkordb"] == "ok"
