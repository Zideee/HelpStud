"""Tests de l'API (tests 5 à 7 de SPEC.md §8)."""

import json
from contextlib import closing
from datetime import date, datetime, timedelta
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
    """Envoie un fichier à POST /courses, avec un éventuel champ priority."""
    return client.post("/courses", files={"file": (nom_fichier, contenu)}, data=champs)


def test_api_import_cours(client: TestClient) -> None:
    """Test 6 : upload → 201 avec chapitres et charge ; priorité enregistrée (défaut sinon) et
    modifiable ; catégorie calculée depuis les échéances ; .docx → 415 (CA1.1, CA1.6, CA1.7, CA2.7)."""
    # 1. Import avec la priorité choisie avant l'upload (plus de catégorie à saisir).
    sql = envoyer_cours(client, "SQL.md", (DONNEES_DEMO / "SQL.md").read_bytes(), priority="high")
    assert sql.status_code == 201
    corps = sql.json()
    assert corps["name"] == "SQL"
    assert len(corps["chapters"]) == 5
    assert corps["hours_total"] == sum(chapitre["hours"] for chapitre in corps["chapters"])  # CA1.5
    assert corps["priority"] == "high" and corps["category"] is None  # pas encore d'échéance
    # GET /courses renvoie aussi les chapitres (extension : le Planning affiche leurs titres).
    assert client.get("/courses").json()[0]["chapters"] == corps["chapters"]

    # 2. Sans priorité : moyenne par défaut.
    python = envoyer_cours(client, "Python.md", (DONNEES_DEMO / "Python.md").read_bytes()).json()
    assert python["priority"] == "medium"

    # 3. GET /courses : les deux cours, avancement à 0 tant qu'aucune session n'est faite.
    liste = client.get("/courses").json()
    assert [(c["name"], c["priority"], c["progress"]) for c in liste] == [
        ("SQL", "high", 0.0), ("Python", "medium", 0.0)]

    # 4. Priorité modifiable après l'import.
    modifie = client.patch(f"/courses/{python['id']}", json={"priority": "low"})
    assert modifie.status_code == 200 and modifie.json()["priority"] == "low"

    # 5. Catégorie calculée (CA2.7) : un examen → « exam » ; + un contrôle continu → « mixed ».
    dans_un_mois = str(datetime.now(FUSEAU).date() + timedelta(days=30))
    examen = {"course_id": corps["id"], "title": "Examen", "type": "exam",
              "date": dans_un_mois, "weight": 60}
    client.post("/deadlines", json=examen)
    assert client.get("/courses").json()[0]["category"] == "exam"
    client.post("/deadlines", json={**examen, "title": "TP noté", "type": "assignment"})
    assert client.get("/courses").json()[0]["category"] == "mixed"
    assert client.get("/courses").json()[1]["category"] is None  # Python : toujours aucune date
    client.post("/deadlines", json={**examen, "course_id": python["id"], "type": "assignment"})
    assert client.get("/courses").json()[1]["category"] == "continuous"  # contrôle continu seul

    # 6. Erreurs : mauvais format → 415 ; priorité inconnue → 422 ; cours inconnu → 404.
    assert envoyer_cours(client, "notes.docx", b"x").status_code == 415
    assert envoyer_cours(client, "a.md", b"# A texte", priority="urgent").status_code == 422
    assert client.patch("/courses/999", json={"priority": "low"}).status_code == 404
    # Pourquoi les vrais fichiers de sample_data : on teste avec les données de la démo,
    # donc la démo est garantie de fonctionner (SQL.md = 5 chapitres).


def semaine_iso(jour: date) -> str:
    """La semaine ISO d'une date, au format « AAAA-Wnn »."""
    annee, numero, _ = jour.isocalendar()
    return f"{annee}-W{numero:02d}"


def test_api_regeneration_garde_les_sessions_faites(client: TestClient) -> None:
    """Test 7 : relancer generate remplace les sessions non faites (sans doublon) et ne
    déplace pas une session faite (CA3.7, CA5.3)."""
    aujourdhui = datetime.now(FUSEAU).date()
    cours = envoyer_cours(client, "SQL.md", (DONNEES_DEMO / "SQL.md").read_bytes()).json()
    client.post("/deadlines", json={"course_id": cours["id"], "title": "Examen", "type": "exam",
                                    "date": str(aujourdhui + timedelta(days=30)), "weight": 60})
    client.put("/availability", json=json.loads((DONNEES_DEMO / "availability.json").read_text()))
    semaine = semaine_iso(aujourdhui + timedelta(days=7))  # toujours entièrement dans le futur

    # 1. Première génération, puis on marque la 1re session comme faite.
    premiere = client.post("/plan/generate", json={"week": semaine}).json()
    assert len(premiere) > 0
    faite = client.patch(f"/sessions/{premiere[0]['id']}", json={"done": True}).json()
    assert faite["done"] is True

    # 2. L'étudiant n'est plus libre que le jeudi, puis relance « Générer ».
    client.put("/availability", json={"session_minutes": 60, "slots": {"thursday": ["14:00-20:00"]}})
    seconde = client.post("/plan/generate", json={"week": semaine}).json()

    # 3. La session faite n'a pas bougé ; toutes les autres sont replacées le jeudi ;
    #    et il n'y a pas de doublon (même nombre de sessions qu'avant).
    assert [s for s in seconde if s["done"]] == [faite]
    non_faites = [s for s in seconde if not s["done"]]
    assert all(datetime.fromisoformat(s["start"]).weekday() == 3 for s in non_faites)
    assert len(seconde) == len(premiere)

    # 4. GET /plan renvoie exactement les sessions de la semaine ; erreurs 422 et 404.
    assert client.get("/plan", params={"week": semaine}).json() == seconde
    assert client.post("/plan/generate", json={"week": "2026-47"}).status_code == 422
    assert client.patch("/sessions/999", json={"done": True}).status_code == 404
    # 5. Une session de révision dure entre 1 h et 2 h (décision de l'équipe) : 30 ou 150 min → 422.
    for minutes, code in ((30, 422), (59, 422), (60, 200), (120, 200), (121, 422), (150, 422)):
        assert client.put("/availability", json={"session_minutes": minutes, "slots": {}}).status_code == code
    # Pourquoi changer les disponibilités entre les deux générations : sans ça, le test
    # passait même si les anciennes sessions n'étaient pas supprimées (vérifié en cassant
    # le code). Il faut que l'ancien planning devienne faux pour prouver qu'il est remplacé.
