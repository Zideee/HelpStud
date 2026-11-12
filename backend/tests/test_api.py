"""Tests de l'API (tests 5 à 7 de SPEC.md §8)."""

from contextlib import closing
from datetime import datetime, timedelta

from fastapi.testclient import TestClient

from app.db import chemin_base, ouvrir_connexion
from app.services.planner import FUSEAU


def creer_cours_en_base(nom: str) -> int:
    """Insère un cours directement en base et renvoie son id."""
    with closing(ouvrir_connexion(chemin_base())) as connexion:
        curseur = connexion.execute("INSERT INTO courses (name) VALUES (?)", (nom,))
        connexion.commit()
        return curseur.lastrowid
    # Pourquoi passer par la base : POST /courses n'existe pas encore (P0-09) ; le test 5
    # vérifie les échéances, il a seulement besoin qu'un cours existe.


def test_api_echeances(client: TestClient) -> None:
    """Test 5 : créer (201), lister triées par date, supprimer (204) ; date passée → 422,
    cours inconnu → 404 (CA2.1 à CA2.3)."""
    cours_id = creer_cours_en_base("SQL")
    aujourdhui = datetime.now(FUSEAU).date()
    echeance = {"course_id": cours_id, "type": "exam", "weight": 70}

    # 1. Création : 201 + l'échéance avec son id. La plus lointaine est créée en premier.
    examen = client.post("/deadlines", json={**echeance, "title": "Examen final",
                                             "date": str(aujourdhui + timedelta(days=10))})
    assert examen.status_code == 201
    assert examen.json()["id"] > 0 and examen.json()["title"] == "Examen final"
    projet = client.post("/deadlines", json={**echeance, "title": "Projet", "type": "assignment",
                                             "date": str(aujourdhui + timedelta(days=1))})
    assert projet.status_code == 201

    # 2. Liste triée par date (et non par ordre de création).
    assert [e["title"] for e in client.get("/deadlines").json()] == ["Projet", "Examen final"]

    # 3. Date passée → 422 ; cours inconnu → 404.
    hier = {**echeance, "title": "Trop tard", "date": str(aujourdhui - timedelta(days=1))}
    assert client.post("/deadlines", json=hier).status_code == 422
    inconnu = {**echeance, "course_id": 999, "title": "X", "date": str(aujourdhui)}
    assert client.post("/deadlines", json=inconnu).status_code == 404

    # 4. Suppression : 204, puis 404 si on recommence.
    assert client.delete(f"/deadlines/{projet.json()['id']}").status_code == 204
    assert len(client.get("/deadlines").json()) == 1
    assert client.delete(f"/deadlines/{projet.json()['id']}").status_code == 404
    # Pourquoi calculer les dates à partir d'aujourd'hui : une date écrite en dur
    # (« 2026-12-01 ») deviendrait « passée » un jour et le test casserait tout seul.
