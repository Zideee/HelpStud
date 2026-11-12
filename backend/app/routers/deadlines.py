"""Routes des échéances : créer, lister, supprimer (bloc 2)."""

import sqlite3
from datetime import date

from fastapi import APIRouter, HTTPException, Response

from app.db import Connexion
from app.schemas import Echeance, NouvelleEcheance

router = APIRouter(tags=["échéances"])


def ligne_vers_echeance(ligne: sqlite3.Row) -> Echeance:
    """Convertit une ligne de la table deadlines en modèle Echeance."""
    return Echeance(
        id=ligne["id"], course_id=ligne["course_id"], title=ligne["title"],
        type=ligne["type"], date=date.fromisoformat(ligne["date"]), weight=ligne["weight"],
    )
    # Pourquoi une fonction : la conversion texte → date est écrite une seule fois.


@router.post("/deadlines", status_code=201)
def creer_echeance(echeance: NouvelleEcheance, connexion: Connexion) -> Echeance:
    """Crée une échéance ; 404 si le cours n'existe pas."""
    cours = connexion.execute("SELECT id FROM courses WHERE id = ?", (echeance.course_id,))
    if cours.fetchone() is None:
        raise HTTPException(status_code=404, detail="Cours inconnu")
    curseur = connexion.execute(
        "INSERT INTO deadlines (course_id, title, type, date, weight) VALUES (?, ?, ?, ?, ?)",
        (echeance.course_id, echeance.title, echeance.type, echeance.date.isoformat(), echeance.weight),
    )
    return Echeance(id=curseur.lastrowid, **echeance.model_dump())
    # Pourquoi vérifier le cours nous-mêmes : la clé étrangère SQLite lèverait une erreur
    # technique (500) ; on préfère un 404 clair. La date passée, elle, est déjà refusée
    # par NouvelleEcheance (422) avant même d'entrer dans cette fonction.
    # Pourquoi « ? » dans le SQL : les valeurs ne sont jamais collées dans la requête,
    # ce qui empêche l'injection SQL.


@router.get("/deadlines")
def lister_echeances(connexion: Connexion) -> list[Echeance]:
    """Toutes les échéances, triées par date puis par id."""
    lignes = connexion.execute("SELECT * FROM deadlines ORDER BY date, id").fetchall()
    return [ligne_vers_echeance(ligne) for ligne in lignes]
    # Pourquoi trier en SQL sur du texte : le format AAAA-MM-JJ se trie dans l'ordre
    # alphabétique exactement comme dans l'ordre chronologique.


@router.delete("/deadlines/{echeance_id}", status_code=204)
def supprimer_echeance(echeance_id: int, connexion: Connexion) -> Response:
    """Supprime une échéance ; 404 si elle n'existe pas."""
    curseur = connexion.execute("DELETE FROM deadlines WHERE id = ?", (echeance_id,))
    if curseur.rowcount == 0:
        raise HTTPException(status_code=404, detail="Échéance inconnue")
    return Response(status_code=204)
    # Pourquoi rowcount : il dit combien de lignes ont été supprimées ; 0 = l'id n'existait pas.
