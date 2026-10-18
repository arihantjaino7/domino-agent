from fastapi.testclient import TestClient

from domino.api.main import app


def test_health_pings_falkordb():
    with TestClient(app) as client:
        resp = client.get("/api/health")
        head = client.head("/api/health")  # uptime monitors use HEAD
    assert resp.status_code == 200 and head.status_code == 200
    body = resp.json()
    assert body["status"] == "ok"
    assert body["falkordb"] == "ok"
