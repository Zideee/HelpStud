"""Test trivial : l'API démarre et répond sur /health."""

from fastapi.testclient import TestClient

from app.main import app


def test_health_repond_ok() -> None:
    """GET /health renvoie 200 et {"status": "ok"}."""
    client = TestClient(app)
    reponse = client.get("/health")
    assert reponse.status_code == 200
    assert reponse.json() == {"status": "ok"}
    # Pourquoi : premier test qui prouve que la chaîne pytest + FastAPI + imports
    # fonctionne ; tous les tests suivants reposent sur elle.
