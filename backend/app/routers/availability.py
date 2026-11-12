"""Routes des disponibilités hebdomadaires (bloc 2)."""

import json

from fastapi import APIRouter, HTTPException

from app.db import Connexion
from app.schemas import Disponibilite

router = APIRouter(tags=["disponibilités"])


@router.put("/availability")
def enregistrer_disponibilites(disponibilite: Disponibilite, connexion: Connexion) -> Disponibilite:
    """Remplace les disponibilités (une seule configuration : un seul utilisateur)."""
    connexion.execute(
        "INSERT OR REPLACE INTO availability (id, session_minutes, slots_json) VALUES (1, ?, ?)",
        (disponibilite.session_minutes, json.dumps(disponibilite.slots)),
    )
    return disponibilite
    # Pourquoi PUT et INSERT OR REPLACE : PUT veut dire « remplace tout » ; la ligne id = 1
    # est créée la 1re fois, puis écrasée. Pourquoi du JSON : les créneaux par jour sont
    # une structure souple qu'on relit telle quelle, sans table supplémentaire.


@router.get("/availability")
def lire_disponibilites(connexion: Connexion) -> Disponibilite:
    """Les disponibilités enregistrées ; 404 si rien n'a encore été saisi."""
    ligne = connexion.execute("SELECT * FROM availability WHERE id = 1").fetchone()
    if ligne is None:
        raise HTTPException(status_code=404, detail="Aucune disponibilité enregistrée")
    return Disponibilite(session_minutes=ligne["session_minutes"], slots=json.loads(ligne["slots_json"]))
    # Pourquoi cette route (extension du contrat) : le front pré-remplit le formulaire.
