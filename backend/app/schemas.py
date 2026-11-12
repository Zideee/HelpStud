"""Modèles Pydantic : la forme exacte des données échangées par l'API (= le contrat)."""

from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, Field, field_validator

from app.services.planner import FUSEAU, lire_creneau, lundi_de_la_semaine

Priorite = Literal["high", "medium", "low"]
Categorie = Literal["exam", "continuous", "mixed"]
TypeEcheance = Literal["exam", "assignment"]
Jour = Literal["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]
# Pourquoi Literal : FastAPI refuse tout seul (422) une valeur hors de la liste,
# sans qu'on écrive une seule ligne de vérification.


# --- Cours ---------------------------------------------------------------------------

class Chapitre(BaseModel):
    """Un chapitre d'un cours importé."""

    id: int
    title: str
    hours: float


class CoursCree(BaseModel):
    """Réponse de POST /courses."""

    id: int
    name: str
    chapters: list[Chapitre]
    hours_total: float
    priority: Priorite
    category: Categorie | None


class CoursResume(BaseModel):
    """Un élément de GET /courses (avec l'avancement)."""

    id: int
    name: str
    hours_total: float
    hours_done: float
    progress: float
    priority: Priorite
    category: Categorie | None


class ModificationCours(BaseModel):
    """Corps de PATCH /courses/{id} : on n'envoie que ce qui change."""

    priority: Priorite | None = None
    category: Categorie | None = None


# --- Échéances -----------------------------------------------------------------------

class EcheanceBase(BaseModel):
    """Champs communs d'une échéance."""

    course_id: int
    title: str = Field(min_length=1)
    type: TypeEcheance
    date: date
    weight: int = Field(ge=0, le=100)


class NouvelleEcheance(EcheanceBase):
    """Corps de POST /deadlines : la date ne peut pas être dans le passé."""

    @field_validator("date")
    @classmethod
    def refuser_date_passee(cls, valeur: date) -> date:
        """Une date avant aujourd'hui (heure de Paris) est refusée → 422."""
        if valeur < datetime.now(FUSEAU).date():
            raise ValueError("La date de l'échéance est déjà passée")
        return valeur
    # Pourquoi « aujourd'hui à Paris » : à 0 h 30 en France, il est encore la veille en UTC ;
    # on juge la date dans le fuseau de l'étudiant.


class Echeance(EcheanceBase):
    """Une échéance enregistrée (réponse de l'API)."""

    id: int
# Pourquoi deux classes séparées : la règle « pas dans le passé » ne vaut qu'à la création.
# Si Echeance l'héritait, GET /deadlines planterait le lendemain d'un examen.


# --- Disponibilités et planning ------------------------------------------------------

class Disponibilite(BaseModel):
    """Corps et réponse de PUT /availability."""

    session_minutes: int = Field(gt=0)
    slots: dict[Jour, list[str]]

    @field_validator("slots")
    @classmethod
    def verifier_creneaux(cls, valeur: dict[str, list[str]]) -> dict[str, list[str]]:
        """Chaque créneau doit être « HH:MM-HH:MM » avec fin > début → sinon 422."""
        for creneaux in valeur.values():
            for texte in creneaux:
                lire_creneau(texte)
        return valeur
    # Pourquoi réutiliser lire_creneau du planificateur : une seule définition de ce
    # qu'est un créneau valide ; l'API et le planificateur ne peuvent pas diverger.


class DemandePlanning(BaseModel):
    """Corps de POST /plan/generate."""

    week: str

    @field_validator("week")
    @classmethod
    def verifier_semaine(cls, valeur: str) -> str:
        """Format « AAAA-Wnn » et semaine qui existe vraiment → sinon 422."""
        lundi_de_la_semaine(valeur)
        return valeur


class Session(BaseModel):
    """Une session de révision (réponse de l'API)."""

    id: int
    course_id: int
    chapter_id: int
    start: datetime
    end: datetime
    done: bool


class ModificationSession(BaseModel):
    """Corps de PATCH /sessions/{id}."""

    done: bool
