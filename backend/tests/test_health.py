from fastapi.testclient import TestClient
from app.main import app
from app.api.routes import health as health_module

client = TestClient(app)


def test_ping():
    response = client.get("/api/ping")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_health_database_connected(monkeypatch):
    monkeypatch.setattr(health_module, "database_is_available", lambda: True)
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json()["database"] == "connected"
    assert response.json()["smtp"]["status"] == "configured_not_tested"


def test_health_database_unavailable(monkeypatch):
    monkeypatch.setattr(health_module, "database_is_available", lambda: False)
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json()["status"] == "degraded"
