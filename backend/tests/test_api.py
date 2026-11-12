"""Tests de l'API (tests 5 à 7 de SPEC.md §8)."""

from contextlib import closing
from datetime import datetime, timedelta
from pathlib import Path

from fastapi.testclient import TestClient

from app.db import chemin_base, ouvrir_connexion
from app.services.planner import FUSEAU

DONNEES_DEMO = Path(__file__).parents[2] / "sample_data"
# Pourquoi un chemin calculé depuis ce fichier : le test marche quel que soit le dossier
# d'où l'on lance pytest.


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


def envoyer_cours(client: TestClient, nom_fichier: str, contenu: bytes, **champs: str):
    """Envoie un fichier à POST /courses, avec d'éventuels champs priority / category."""
    return client.post("/courses", files={"file": (nom_fichier, contenu)}, data=champs)


def test_api_import_cours(client: TestClient) -> None:
    """Test 6 : upload .md → 201 avec chapitres et charge ; priorité et catégorie enregistrées
    (défauts sinon) et modifiables ; .docx → 415 (CA1.1, CA1.6, CA1.7)."""
    # 1. Import avec priorité et catégorie choisies avant l'upload.
    sql = envoyer_cours(client, "SQL.md", (DONNEES_DEMO / "SQL.md").read_bytes(),
                        priority="high", category="mixed")
    assert sql.status_code == 201
    corps = sql.json()
    assert corps["name"] == "SQL"
    assert len(corps["chapters"]) == 5 and corps["hours_total"] == 6.0
    assert corps["priority"] == "high" and corps["category"] == "mixed"

    # 2. Sans ces champs : valeurs par défaut (moyenne, catégorie non précisée).
    python = envoyer_cours(client, "Python.md", (DONNEES_DEMO / "Python.md").read_bytes()).json()
    assert python["priority"] == "medium" and python["category"] is None

    # 3. GET /courses : les deux cours, avancement à 0 tant qu'aucune session n'est faite.
    liste = client.get("/courses").json()
    assert [(c["name"], c["priority"], c["progress"]) for c in liste] == [
        ("SQL", "high", 0.0), ("Python", "medium", 0.0)]

    # 4. Priorité modifiable après l'import ; la catégorie non envoyée ne change pas.
    modifie = client.patch(f"/courses/{python['id']}", json={"priority": "low"})
    assert modifie.status_code == 200
    assert modifie.json()["priority"] == "low" and modifie.json()["category"] is None

    # 5. Erreurs : mauvais format → 415 ; priorité inconnue → 422 ; cours inconnu → 404.
    assert envoyer_cours(client, "notes.docx", b"x").status_code == 415
    assert envoyer_cours(client, "a.md", b"# A texte", priority="urgent").status_code == 422
    assert client.patch("/courses/999", json={"priority": "low"}).status_code == 404
    # Pourquoi les vrais fichiers de sample_data : on teste avec les données de la démo,
    # donc la démo est garantie de fonctionner (SQL.md = 5 chapitres, 6 h).
