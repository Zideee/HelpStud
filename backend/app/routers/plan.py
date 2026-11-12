"""Routes du planning : générer une semaine, la lire, marquer une session, exporter en .ics (blocs 3 et 4).

Ce fichier fait le lien entre la base et les services purs : il lit SQLite, construit les
dataclasses du planificateur, appelle generer_planning / exporter_ics, puis enregistre.
"""

import json
import sqlite3
from datetime import date, datetime, time, timedelta

from fastapi import APIRouter, HTTPException, Response

from app.db import Connexion
from app.schemas import DemandePlanning, ModificationSession, Session
from app.services.ics_export import SessionIcs, exporter_ics
from app.services.planner import (
    FUSEAU,
    ChapitreAPlanifier,
    CoursAPlanifier,
    Disponibilites,
    EcheanceAPlanifier,
    Intervalle,
    generer_planning,
    lundi_de_la_semaine,
)

router = APIRouter(tags=["planning"])


# --- Lecture des sessions --------------------------------------------------------------

def bornes_de_la_semaine(semaine: str) -> Intervalle:
    """[lundi 00:00, lundi suivant 00:00) à Paris ; 422 si la semaine est invalide."""
    try:
        lundi = lundi_de_la_semaine(semaine)
    except ValueError as erreur:
        raise HTTPException(status_code=422, detail=str(erreur)) from erreur
    debut = datetime.combine(lundi, time(0, 0), tzinfo=FUSEAU)
    return Intervalle(debut, datetime.combine(lundi + timedelta(days=7), time(0, 0), tzinfo=FUSEAU))
    # Pourquoi « lundi suivant 00:00 » exclu : une session du dimanche 23:00 est dans la
    # semaine, une session du lundi suivant 00:00 n'y est pas.


def ligne_vers_session(ligne: sqlite3.Row) -> Session:
    """Convertit une ligne de la table sessions en modèle Session."""
    return Session(id=ligne["id"], course_id=ligne["course_id"], chapter_id=ligne["chapter_id"],
                   start=datetime.fromisoformat(ligne["start_at"]),
                   end=datetime.fromisoformat(ligne["end_at"]), done=bool(ligne["done"]))


def sessions_de_la_semaine(connexion: sqlite3.Connection, semaine: str) -> list[Session]:
    """Les sessions qui commencent dans la semaine, triées par début."""
    bornes = bornes_de_la_semaine(semaine)
    toutes = [ligne_vers_session(ligne) for ligne in connexion.execute("SELECT * FROM sessions")]
    dans_la_semaine = [s for s in toutes if bornes.debut <= s.start < bornes.fin]
    return sorted(dans_la_semaine, key=lambda session: session.start)
    # Pourquoi filtrer en Python et pas en SQL : les dates sont du texte avec décalage
    # (+01:00 l'hiver, +02:00 l'été) ; comparer ces textes donnerait des erreurs au
    # changement d'heure. Comparer des datetime, c'est toujours juste.


# --- Préparation des données du planificateur ---------------------------------------------

def lire_disponibilites(connexion: sqlite3.Connection) -> Disponibilites | None:
    """Les disponibilités enregistrées, au format du planificateur, ou None."""
    ligne = connexion.execute("SELECT * FROM availability WHERE id = 1").fetchone()
    if ligne is None:
        return None
    return Disponibilites(minutes_session=ligne["session_minutes"], creneaux=json.loads(ligne["slots_json"]))


def minutes_deja_placees(connexion: sqlite3.Connection) -> dict[int, int]:
    """Pour chaque chapitre, la durée (en minutes) de ses sessions restées en base."""
    minutes: dict[int, int] = {}
    for ligne in connexion.execute("SELECT chapter_id, start_at, end_at FROM sessions"):
        duree = datetime.fromisoformat(ligne["end_at"]) - datetime.fromisoformat(ligne["start_at"])
        minutes[ligne["chapter_id"]] = minutes.get(ligne["chapter_id"], 0) + int(duree.total_seconds() // 60)
    return minutes
    # Pourquoi compter aussi les sessions des autres semaines : un chapitre déjà planifié
    # la semaine dernière ne doit pas être replanifié en entier cette semaine.


def chapitres_a_planifier(connexion: sqlite3.Connection, cours_id: int,
                          deja_places: dict[int, int]) -> list[ChapitreAPlanifier]:
    """Les chapitres du cours, dans l'ordre, avec les minutes qu'il reste à placer."""
    chapitres: list[ChapitreAPlanifier] = []
    lignes = connexion.execute(
        "SELECT id, hours FROM chapters WHERE course_id = ? ORDER BY position", (cours_id,))
    for ligne in lignes:
        minutes_prevues = round(ligne["hours"] * 60)
        restantes = max(0, minutes_prevues - deja_places.get(ligne["id"], 0))
        chapitres.append(ChapitreAPlanifier(id=ligne["id"], minutes_restantes=restantes))
    return chapitres
    # Pourquoi max(0, …) : si l'étudiant a fait plus que prévu, il ne reste rien, pas « −30 min ».


def echeances_du_cours(connexion: sqlite3.Connection, cours_id: int) -> list[EcheanceAPlanifier]:
    """Les échéances du cours au format du planificateur."""
    lignes = connexion.execute("SELECT date, weight FROM deadlines WHERE course_id = ?", (cours_id,))
    return [EcheanceAPlanifier(date=date.fromisoformat(ligne["date"]), poids=ligne["weight"])
            for ligne in lignes]


def construire_cours(connexion: sqlite3.Connection) -> list[CoursAPlanifier]:
    """Tous les cours au format du planificateur : chapitres (dans l'ordre) et échéances."""
    deja_places = minutes_deja_placees(connexion)
    return [
        CoursAPlanifier(id=cours["id"], priorite=cours["priority"],
                        chapitres=chapitres_a_planifier(connexion, cours["id"], deja_places),
                        echeances=echeances_du_cours(connexion, cours["id"]))
        for cours in connexion.execute("SELECT id, priority FROM courses ORDER BY id").fetchall()
    ]
    # Pourquoi ce « traducteur » : le planificateur ne connaît pas SQLite (Python pur) ;
    # c'est la route qui lui prépare des données propres.


# --- Routes ------------------------------------------------------------------------------

@router.post("/plan/generate")
def generer_semaine(demande: DemandePlanning, connexion: Connexion) -> list[Session]:
    """Remplace les sessions non faites de la semaine par un nouveau planning."""
    for session in sessions_de_la_semaine(connexion, demande.week):
        if not session.done:
            connexion.execute("DELETE FROM sessions WHERE id = ?", (session.id,))
    disponibilites = lire_disponibilites(connexion)
    if disponibilites is None:
        return []
    faites = [Intervalle(s.start, s.end) for s in sessions_de_la_semaine(connexion, demande.week)]
    nouvelles = generer_planning(demande.week, construire_cours(connexion), disponibilites,
                                 faites, datetime.now(FUSEAU))
    for session in nouvelles:
        connexion.execute(
            "INSERT INTO sessions (course_id, chapter_id, start_at, end_at) VALUES (?, ?, ?, ?)",
            (session.cours_id, session.chapitre_id, session.debut.isoformat(), session.fin.isoformat()))
    return sessions_de_la_semaine(connexion, demande.week)
    # Pourquoi supprimer d'abord les sessions non faites : relancer « Générer » ne doit pas
    # empiler des doublons (CA3.7). Les sessions faites restent et occupent leur créneau.


@router.get("/plan")
def lire_semaine(week: str, connexion: Connexion) -> list[Session]:
    """Les sessions de la semaine demandée (?week=2026-W47)."""
    return sessions_de_la_semaine(connexion, week)


@router.patch("/sessions/{session_id}")
def marquer_session(session_id: int, modification: ModificationSession, connexion: Connexion) -> Session:
    """Marque une session comme faite (ou non faite) ; 404 si elle n'existe pas."""
    connexion.execute("UPDATE sessions SET done = ? WHERE id = ?", (int(modification.done), session_id))
    ligne = connexion.execute("SELECT * FROM sessions WHERE id = ?", (session_id,)).fetchone()
    if ligne is None:
        raise HTTPException(status_code=404, detail="Session inconnue")
    return ligne_vers_session(ligne)
    # Pourquoi accepter done = false : l'étudiant peut se tromper et revenir en arrière (CA5.3).


REQUETE_ICS = """
SELECT sessions.id, sessions.start_at, sessions.end_at, courses.name, chapters.title
FROM sessions
JOIN courses ON courses.id = sessions.course_id
JOIN chapters ON chapters.id = sessions.chapter_id
ORDER BY sessions.start_at
"""


@router.get("/plan.ics")
def exporter_calendrier(connexion: Connexion) -> Response:
    """Toutes les sessions au format iCalendar, à importer dans Google Agenda ou Outlook."""
    sessions = [
        SessionIcs(id=ligne["id"], cours=ligne["name"], chapitre=ligne["title"],
                   debut=datetime.fromisoformat(ligne["start_at"]), fin=datetime.fromisoformat(ligne["end_at"]))
        for ligne in connexion.execute(REQUETE_ICS)
    ]
    contenu = exporter_ics(sessions, datetime.now(FUSEAU))
    return Response(content=contenu, media_type="text/calendar",
                    headers={"Content-Disposition": 'attachment; filename="helpstud.ics"'})
    # Pourquoi Content-Disposition : le navigateur propose de télécharger « helpstud.ics »
    # au lieu d'afficher le texte brut. Pourquoi JOIN : le .ics affiche des noms, pas des id.
