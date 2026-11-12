"""Planificateur de révisions — PYTHON PUR : aucun import de FastAPI, sqlite3 ou app.db.

Il reçoit des données (cours, disponibilités, créneaux occupés) et renvoie des sessions.
"""

import re
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta
from zoneinfo import ZoneInfo

FUSEAU = ZoneInfo("Europe/Paris")
COEF_PRIORITE = {"high": 2.0, "medium": 1.0, "low": 0.5}
JOURS = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]
MOTIF_SEMAINE = re.compile(r"^(\d{4})-W(\d{2})$")
MOTIF_CRENEAU = re.compile(r"^(\d{2}:\d{2})-(\d{2}:\d{2})$")
# Pourquoi JOURS dans cet ordre : l'indice correspond à date.weekday() (lundi = 0),
# ce qui permet de passer du nom du jour à sa date sans table de correspondance.


@dataclass(frozen=True)
class Intervalle:
    """Une plage de temps [debut, fin) avec fuseau horaire."""

    debut: datetime
    fin: datetime


@dataclass(frozen=True)
class ChapitreAPlanifier:
    """Un chapitre et le nombre de minutes qu'il reste à placer."""

    id: int
    minutes_restantes: int


@dataclass(frozen=True)
class EcheanceAPlanifier:
    """Une échéance vue par le planificateur : sa date et son poids (0 à 100)."""

    date: date
    poids: int


@dataclass(frozen=True)
class CoursAPlanifier:
    """Un cours à planifier, avec ses chapitres (dans l'ordre) et ses échéances."""

    id: int
    priorite: str
    chapitres: list[ChapitreAPlanifier]
    echeances: list[EcheanceAPlanifier]


@dataclass(frozen=True)
class Disponibilites:
    """La durée d'une session et les créneaux libres de chaque jour de la semaine."""

    minutes_session: int
    creneaux: dict[str, list[str]]


@dataclass(frozen=True)
class SessionPlanifiee:
    """Une session placée : quel cours, quel chapitre, quand."""

    cours_id: int
    chapitre_id: int
    debut: datetime
    fin: datetime
# Pourquoi des dataclasses plutôt que des dictionnaires : les champs sont nommés et typés,
# une faute de frappe est détectée tout de suite, et le planificateur ne dépend pas du format
# de la base ni de celui du JSON.


def lundi_de_la_semaine(semaine: str) -> date:
    """« 2026-W47 » → date du lundi (2026-11-16). Lève ValueError si le format est faux."""
    correspondance = MOTIF_SEMAINE.match(semaine)
    if correspondance is None:
        raise ValueError(f"Semaine mal formée : {semaine!r} (attendu AAAA-Wnn)")
    annee, numero = int(correspondance.group(1)), int(correspondance.group(2))
    return date.fromisocalendar(annee, numero, 1)
    # Pourquoi fromisocalendar : la semaine ISO 1 n'est pas « la semaine du 1er janvier » ;
    # Python connaît la vraie règle et lève ValueError pour une semaine qui n'existe pas (W60).


def lire_creneau(texte: str) -> tuple[time, time]:
    """« 18:00-20:00 » → (18:00, 20:00). Lève ValueError si mal formé ou fin <= début."""
    correspondance = MOTIF_CRENEAU.match(texte)
    if correspondance is None:
        raise ValueError(f"Créneau mal formé : {texte!r} (attendu HH:MM-HH:MM)")
    debut = time.fromisoformat(correspondance.group(1))
    fin = time.fromisoformat(correspondance.group(2))
    if fin <= debut:
        raise ValueError(f"Créneau {texte!r} : la fin doit être après le début")
    return debut, fin
    # Pourquoi une regex avant fromisoformat : fromisoformat accepte aussi « 18 » ou
    # « 18:00:00 » ; on veut exactement le format du contrat. 25:00 est refusé par fromisoformat.


def creneaux_de_la_semaine(semaine: str, disponibilites: Disponibilites) -> list[Intervalle]:
    """Les créneaux datés (fuseau Europe/Paris) de la semaine, triés chronologiquement."""
    lundi = lundi_de_la_semaine(semaine)
    creneaux: list[Intervalle] = []
    for indice, nom_jour in enumerate(JOURS):
        jour = lundi + timedelta(days=indice)
        for texte in disponibilites.creneaux.get(nom_jour, []):
            debut, fin = lire_creneau(texte)
            creneaux.append(Intervalle(
                datetime.combine(jour, debut, tzinfo=FUSEAU),
                datetime.combine(jour, fin, tzinfo=FUSEAU),
            ))
    return sorted(creneaux, key=lambda creneau: creneau.debut)
    # Pourquoi trier : deux créneaux d'un même jour peuvent être saisis dans le désordre,
    # et tout le reste du planificateur suppose l'ordre chronologique.


def soustraire(creneau: Intervalle, occupe: Intervalle) -> list[Intervalle]:
    """Ce qui reste de `creneau` une fois `occupe` retiré : 0, 1 ou 2 morceaux."""
    if occupe.fin <= creneau.debut or occupe.debut >= creneau.fin:
        return [creneau]
    morceaux: list[Intervalle] = []
    if occupe.debut > creneau.debut:
        morceaux.append(Intervalle(creneau.debut, occupe.debut))
    if occupe.fin < creneau.fin:
        morceaux.append(Intervalle(occupe.fin, creneau.fin))
    return morceaux
    # Pourquoi 3 cas : pas de contact (on garde tout), occupé au milieu (2 morceaux),
    # occupé sur un bord ou sur tout le créneau (1 ou 0 morceau).


def retirer_intervalles(creneaux: list[Intervalle], occupes: list[Intervalle]) -> list[Intervalle]:
    """Retire des créneaux les parties occupées ; renvoie les morceaux libres restants."""
    libres = list(creneaux)
    for occupe in occupes:
        nouveaux_libres: list[Intervalle] = []
        for creneau in libres:
            nouveaux_libres.extend(soustraire(creneau, occupe))
        libres = nouveaux_libres
    return sorted(libres, key=lambda creneau: creneau.debut)
    # Pourquoi retirer les occupés un par un : chaque passage applique la règle simple de
    # `soustraire`, même quand plusieurs occupations touchent le même créneau.


def decouper_en_sessions(creneau: Intervalle, minutes_session: int) -> list[Intervalle]:
    """Découpe un créneau libre en sessions consécutives de minutes_session ; le reste est perdu."""
    if minutes_session <= 0:
        raise ValueError("minutes_session doit être positif")
    duree = timedelta(minutes=minutes_session)
    sessions: list[Intervalle] = []
    debut = creneau.debut
    while debut + duree <= creneau.fin:
        sessions.append(Intervalle(debut, debut + duree))
        debut += duree
    return sessions
    # Pourquoi refuser 0 : avec une durée nulle, `debut` n'avance jamais et la boucle
    # tournerait à l'infini. Pourquoi « <= » : une session peut finir pile à la fin du créneau.


def lister_sessions_candidates(semaine: str, disponibilites: Disponibilites,
                               creneaux_occupes: list[Intervalle],
                               maintenant: datetime) -> list[Intervalle]:
    """Toutes les sessions possibles de la semaine : libres, futures, de la bonne durée."""
    creneaux = creneaux_de_la_semaine(semaine, disponibilites)
    debut_semaine = datetime.combine(lundi_de_la_semaine(semaine), time(0, 0), tzinfo=FUSEAU)
    deja_passe = Intervalle(debut_semaine, maintenant)
    libres = retirer_intervalles(creneaux, [*creneaux_occupes, deja_passe])
    sessions: list[Intervalle] = []
    for creneau in libres:
        sessions.extend(decouper_en_sessions(creneau, disponibilites.minutes_session))
    return sessions
    # Pourquoi traiter « le passé » comme un créneau occupé : on réutilise la même règle
    # au lieu d'écrire un deuxième filtre (CA3.8). Si maintenant est avant la semaine,
    # l'intervalle est « à l'envers » et soustraire() ne retire rien.
