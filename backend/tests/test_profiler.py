from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_profiling_health():
    response = client.get("/api/v1/profiling/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_profiling_placeholder():
    response = client.get("/api/v1/profiling/")
    assert response.status_code == 200
    assert "Phase 1" in response.json()["message"]
