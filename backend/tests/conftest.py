"""Fixtures partagées par les tests de l'API."""

from collections.abc import Iterator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture
def client(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Iterator[TestClient]:
    """Client de test branché sur une base SQLite neuve dans un dossier temporaire."""
    monkeypatch.setenv("HELPSTUD_DB", str(tmp_path / "test.db"))
    with TestClient(app) as client_de_test:
        yield client_de_test
    # Pourquoi une base neuve par test : les tests ne s'influencent pas (SPEC §10).
    # Pourquoi « with » : il déclenche le démarrage de l'app, donc la création des tables.
    # monkeypatch remet la variable d'environnement d'origine après le test.
