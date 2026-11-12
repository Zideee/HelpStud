"""Routes des cours : import d'un fichier, liste avec avancement, modification (bloc 1)."""

import sqlite3
from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Form, HTTPException, UploadFile

from app.db import Connexion
from app.schemas import Categorie, Chapitre, CoursCree, CoursResume, ModificationCours, Priorite
from app.services.importer import ChapitreImporte, FichierVide, FormatNonSupporte, importer_cours

router = APIRouter(tags=["cours"])


@router.post("/courses", status_code=201)
def importer_un_cours(
    file: UploadFile,
    connexion: Connexion,
    priority: Annotated[Priorite, Form()] = "medium",
    category: Annotated[Categorie | None, Form()] = None,
) -> CoursCree:
    """Importe un .md ou un .pdf : 415 si autre format, 422 si fichier vide."""
    try:
        nom, chapitres = importer_cours(file.filename or "", file.file.read())
    except FormatNonSupporte as erreur:
        raise HTTPException(status_code=415, detail=str(erreur)) from erreur
    except FichierVide as erreur:
        raise HTTPException(status_code=422, detail=str(erreur)) from erreur
    return enregistrer_cours(connexion, nom, chapitres, priority, category)
    # Pourquoi Form() : le fichier arrive en « multipart » (comme un formulaire web), donc
    # priority et category sont des champs de formulaire, pas du JSON. Leurs valeurs par
    # défaut gardent le contrat intact : un envoi avec le fichier seul marche toujours.
    # Pourquoi traduire les exceptions ici : le service ne connaît pas HTTP, c'est la route
    # qui décide du code (415 / 422).


def enregistrer_cours(connexion: sqlite3.Connection, nom: str, chapitres: list[ChapitreImporte],
                      priorite: str, categorie: str | None) -> CoursCree:
    """Insère le cours et ses chapitres (dans l'ordre), puis renvoie la réponse du contrat."""
    curseur = connexion.execute(
        "INSERT INTO courses (name, priority, category) VALUES (?, ?, ?)", (nom, priorite, categorie))
    cours_id = curseur.lastrowid
    chapitres_crees: list[Chapitre] = []
    for position, chapitre in enumerate(chapitres):
        curseur = connexion.execute(
            "INSERT INTO chapters (course_id, position, title, hours) VALUES (?, ?, ?, ?)",
            (cours_id, position, chapitre.titre, chapitre.heures))
        chapitres_crees.append(Chapitre(id=curseur.lastrowid, title=chapitre.titre, hours=chapitre.heures))
    return CoursCree(id=cours_id, name=nom, chapters=chapitres_crees,
                     hours_total=sum(chapitre.heures for chapitre in chapitres),
                     priority=priorite, category=categorie)
    # Pourquoi enregistrer `position` : SQLite ne garantit aucun ordre de lecture ; sans cette
    # colonne, le planificateur pourrait faire réviser le chapitre 3 avant le chapitre 1.


def heures_faites_par_cours(connexion: sqlite3.Connection) -> dict[int, float]:
    """Pour chaque cours, la durée totale (en heures) de ses sessions faites."""
    heures: dict[int, float] = {}
    lignes = connexion.execute("SELECT course_id, start_at, end_at FROM sessions WHERE done = 1")
    for ligne in lignes:
        duree = datetime.fromisoformat(ligne["end_at"]) - datetime.fromisoformat(ligne["start_at"])
        heures[ligne["course_id"]] = heures.get(ligne["course_id"], 0.0) + duree.total_seconds() / 3600
    return heures
    # Pourquoi calculer en Python : les dates sont du texte ISO avec fuseau, que SQLite
    # ne sait pas soustraire correctement ; datetime, si.


def resumer_cours(ligne: sqlite3.Row, heures_faites: dict[int, float]) -> CoursResume:
    """Construit le résumé d'un cours : charge, heures faites (plafonnées) et % d'avancement."""
    total = ligne["hours_total"]
    faites = min(heures_faites.get(ligne["id"], 0.0), total)
    progression = round(faites / total * 100, 1) if total > 0 else 0.0
    return CoursResume(id=ligne["id"], name=ligne["name"], hours_total=total, hours_done=faites,
                       progress=progression, priority=ligne["priority"], category=ligne["category"])
    # Pourquoi plafonner à hours_total : si l'étudiant fait plus de sessions que prévu,
    # l'avancement s'arrête à 100 % au lieu d'afficher 130 % (SPEC §5.5).


REQUETE_COURS = """
SELECT courses.id, courses.name, courses.priority, courses.category,
       COALESCE(SUM(chapters.hours), 0) AS hours_total
FROM courses LEFT JOIN chapters ON chapters.course_id = courses.id
"""
# Pourquoi LEFT JOIN + COALESCE : un cours sans chapitre apparaît quand même, avec 0 h,
# au lieu de disparaître de la liste (voir le cours SQL, chapitre « Jointures »).


@router.get("/courses")
def lister_cours(connexion: Connexion) -> list[CoursResume]:
    """Tous les cours, avec leur avancement, dans l'ordre d'import."""
    lignes = connexion.execute(REQUETE_COURS + " GROUP BY courses.id ORDER BY courses.id").fetchall()
    heures_faites = heures_faites_par_cours(connexion)
    return [resumer_cours(ligne, heures_faites) for ligne in lignes]


@router.patch("/courses/{cours_id}")
def modifier_cours(cours_id: int, modification: ModificationCours, connexion: Connexion) -> CoursResume:
    """Change la priorité et/ou la catégorie ; seuls les champs envoyés sont modifiés."""
    champs = modification.model_dump(exclude_unset=True)
    for colonne, valeur in champs.items():
        connexion.execute(f"UPDATE courses SET {colonne} = ? WHERE id = ?", (valeur, cours_id))
    ligne = connexion.execute(
        REQUETE_COURS + " WHERE courses.id = ? GROUP BY courses.id", (cours_id,)).fetchone()
    if ligne is None:
        raise HTTPException(status_code=404, detail="Cours inconnu")
    return resumer_cours(ligne, heures_faites_par_cours(connexion))
    # Pourquoi exclude_unset : on distingue « champ absent » (ne rien changer) de
    # « champ envoyé à null » (effacer la catégorie).
    # Pourquoi le nom de colonne dans une f-string est sans danger ici : il vient des champs
    # du modèle Pydantic (priority, category), jamais de ce que tape l'utilisateur ;
    # les valeurs, elles, passent toujours par « ? ».
