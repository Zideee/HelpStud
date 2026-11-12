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


def prochaine_echeance(cours: CoursAPlanifier, jour: date) -> EcheanceAPlanifier | None:
    """L'échéance la plus proche strictement après `jour`, ou None."""
    a_venir = [echeance for echeance in cours.echeances if echeance.date > jour]
    if not a_venir:
        return None
    return min(a_venir, key=lambda echeance: echeance.date)
    # Pourquoi « strictement après » : le jour d'une échéance, on ne révise plus pour elle
    # (CA3.3 : une session doit finir avant ce jour). C'est donc la suivante qui compte.


def calculer_score(cours: CoursAPlanifier, jour: date) -> float | None:
    """weight × coef_priorité / jours_restants (min 1). None si aucune échéance à venir."""
    echeance = prochaine_echeance(cours, jour)
    if echeance is None:
        return None
    jours_restants = max(1, (echeance.date - jour).days)
    return echeance.poids * COEF_PRIORITE[cours.priorite] / jours_restants
    # Pourquoi max(1, …) : protège d'une division par zéro si la règle « strictement
    # après » change un jour ; avec la règle actuelle, jours_restants vaut déjà au moins 1.


def est_eligible(cours: CoursAPlanifier, session: Intervalle, minutes_restantes: int) -> bool:
    """Vrai s'il reste du travail et si la session finit avant le jour de l'échéance."""
    if minutes_restantes <= 0:
        return False
    if not cours.echeances:
        return True
    echeance = prochaine_echeance(cours, session.debut.date())
    if echeance is None:
        return False
    limite = datetime.combine(echeance.date, time(0, 0), tzinfo=FUSEAU)
    return session.fin <= limite
    # Pourquoi distinguer « aucune échéance » et « échéances toutes passées » : un cours
    # sans échéance est planifié en dernier (CA3.6) ; un cours dont l'examen est passé
    # est terminé, le réviser n'aurait plus de sens.


def cle_de_priorite(cours: CoursAPlanifier, jour: date) -> tuple[int, float, int]:
    """Clé de tri : le plus petit tuple passe en premier."""
    score = calculer_score(cours, jour)
    if score is not None:
        return (0, -score, cours.id)
    return (1, -COEF_PRIORITE[cours.priorite], cours.id)
    # Pourquoi un tuple : Python compare d'abord le 1er élément (0 = avec échéance, avant
    # 1 = sans), puis le 2e (score négatif → le plus grand score d'abord), puis l'id pour
    # départager. Ainsi le résultat est toujours le même pour les mêmes données.


def minutes_restantes_du_cours(cours: CoursAPlanifier, minutes: dict[int, int]) -> int:
    """Total des minutes encore à placer pour tous les chapitres du cours."""
    return sum(max(0, minutes[chapitre.id]) for chapitre in cours.chapitres)


def choisir_cours(liste_cours: list[CoursAPlanifier], session: Intervalle,
                  minutes: dict[int, int]) -> CoursAPlanifier | None:
    """Le cours éligible le plus prioritaire pour cette session, ou None."""
    eligibles = [
        cours for cours in liste_cours
        if est_eligible(cours, session, minutes_restantes_du_cours(cours, minutes))
    ]
    if not eligibles:
        return None
    jour = session.debut.date()
    return min(eligibles, key=lambda cours: cle_de_priorite(cours, jour))
    # Pourquoi recalculer à chaque session : le score dépend du jour (jours_restants
    # diminue au fil de la semaine) et des minutes déjà placées.


def premier_chapitre_a_placer(cours: CoursAPlanifier, minutes: dict[int, int]) -> ChapitreAPlanifier:
    """Le premier chapitre du cours (dans l'ordre) qui a encore des minutes à placer."""
    return next(chapitre for chapitre in cours.chapitres if minutes[chapitre.id] > 0)
    # Pourquoi next() sans valeur par défaut : on n'appelle cette fonction que pour un cours
    # éligible, qui a donc forcément un chapitre avec des minutes restantes.


def generer_planning(semaine: str, cours: list[CoursAPlanifier],
                     disponibilites: Disponibilites,
                     creneaux_occupes: list[Intervalle],
                     maintenant: datetime) -> list[SessionPlanifiee]:
    """Place les sessions de la semaine, de façon gloutonne, par score décroissant."""
    candidates = lister_sessions_candidates(semaine, disponibilites, creneaux_occupes, maintenant)
    minutes = {chapitre.id: chapitre.minutes_restantes for c in cours for chapitre in c.chapitres}
    sessions: list[SessionPlanifiee] = []
    for creneau in candidates:
        choisi = choisir_cours(cours, creneau, minutes)
        if choisi is None:
            continue
        chapitre = premier_chapitre_a_placer(choisi, minutes)
        sessions.append(SessionPlanifiee(choisi.id, chapitre.id, creneau.debut, creneau.fin))
        minutes[chapitre.id] -= disponibilites.minutes_session
    return sessions
    # Pourquoi « glouton » : chaque session va au meilleur cours du moment, sans revenir en
    # arrière. Ce n'est pas optimal en théorie, mais c'est simple, rapide et explicable (SPEC §5.2).
    # Pourquoi une copie des minutes dans un dict : les dataclasses sont figées, et on ne veut
    # pas modifier les données reçues.
