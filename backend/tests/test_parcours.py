"""Test 8 : parcours complet d'un étudiant, de l'import du cours au fichier .ics (blocs 1 à 4)."""

import json
from datetime import datetime, timedelta
from pathlib import Path

from fastapi.testclient import TestClient
from icalendar import Calendar

from app.services.planner import FUSEAU

DONNEES_DEMO = Path(__file__).parents[2] / "sample_data"


def test_parcours_complet_progression(client: TestClient) -> None:
    """Upload → échéance → disponibilités → generate → session faite → progression → .ics."""
    aujourdhui = datetime.now(FUSEAU).date()

    # 1. L'étudiant importe son cours de SQL (priorité haute, catégorie mixte).
    cours = client.post("/courses", files={"file": ("SQL.md", (DONNEES_DEMO / "SQL.md").read_bytes())},
                        data={"priority": "high", "category": "mixed"})
    assert cours.status_code == 201
    cours_id = cours.json()["id"]

    # 2. Il ajoute son examen dans 30 jours.
    examen = {"course_id": cours_id, "title": "Examen final", "type": "exam",
              "date": str(aujourdhui + timedelta(days=30)), "weight": 60}
    assert client.post("/deadlines", json=examen).status_code == 201

    # 3. Il saisit ses disponibilités (celles de la démo).
    disponibilites = json.loads((DONNEES_DEMO / "availability.json").read_text(encoding="utf-8"))
    assert client.put("/availability", json=disponibilites).status_code == 200

    # 4. Il génère la semaine prochaine (toujours entièrement dans le futur).
    annee, numero, _ = (aujourdhui + timedelta(days=7)).isocalendar()
    sessions = client.post("/plan/generate", json={"week": f"{annee}-W{numero:02d}"}).json()
    assert len(sessions) >= 1

    # 5. Il fait sa première session et la coche.
    faite = client.patch(f"/sessions/{sessions[0]['id']}", json={"done": True})
    assert faite.status_code == 200 and faite.json()["done"] is True

    # 6. Le suivi montre l'avancement : 1 h faite sur 6 h.
    suivi = client.get("/courses").json()[0]
    assert suivi["hours_done"] == 1.0
    assert suivi["progress"] > 0

    # 7. Il exporte son planning vers son agenda : un événement par session.
    ics = client.get("/plan.ics")
    assert ics.status_code == 200
    assert ics.headers["content-type"].startswith("text/calendar")
    assert len(Calendar.from_ical(ics.content).walk("VEVENT")) == len(sessions)
    # Pourquoi un test « de bout en bout » : chaque morceau peut marcher seul et l'ensemble
    # échouer (un id mal transmis, une date mal relue). Ce test suit l'utilisateur réel,
    # étape par étape, exactement comme la démo devant le jury.
