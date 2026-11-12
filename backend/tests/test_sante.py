"""Test provisoire : l'API démarre sur une base neuve et répond sur /health.

Il ne fait pas partie des 12 tests (SPEC.md §8) : il sera supprimé en P0-08,
quand le test 5 (échéances) vérifiera l'API pour de vrai.
"""

from fastapi.testclient import TestClient


def test_health_repond_ok(client: TestClient) -> None:
    """GET /health renvoie 200 et {"status": "ok"}."""
    reponse = client.get("/health")
    assert reponse.status_code == 200
    assert reponse.json() == {"status": "ok"}
    # Pourquoi passer par la fixture `client` : on vérifie au passage que la base
    # temporaire et la création des tables au démarrage fonctionnent.
