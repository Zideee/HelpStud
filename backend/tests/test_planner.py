"""Tests du planificateur (services/planner.py) — partie créneaux (P0-04)."""

from datetime import date, datetime, time

import pytest

from app.services.planner import (
    FUSEAU,
    Disponibilites,
    Intervalle,
    decouper_en_sessions,
    lire_creneau,
    lister_sessions_candidates,
    lundi_de_la_semaine,
    retirer_intervalles,
)

SEMAINE = "2026-W47"  # lundi 16/11/2026, heure d'hiver (UTC+1)
MAINTENANT = datetime(2026, 11, 15, 12, 0, tzinfo=FUSEAU)  # le dimanche d'avant
DISPONIBILITES = Disponibilites(
    minutes_session=60,
    creneaux={"monday": ["18:00-20:00"], "wednesday": ["14:00-17:00"]},
)
# Pourquoi des données fixes : un test doit donner le même résultat aujourd'hui et
# dans un an ; on n'utilise donc jamais la vraie date du jour dans le planificateur.


def heure(jour: int, heures: int, minutes: int = 0) -> datetime:
    """Raccourci : une date-heure de novembre 2026 à Paris."""
    return datetime(2026, 11, jour, heures, minutes, tzinfo=FUSEAU)


CRENEAUX_ATTENDUS = [
    Intervalle(heure(16, 18), heure(16, 20)),  # lundi 16/11 18:00-20:00
    Intervalle(heure(18, 14), heure(18, 17)),  # mercredi 18/11 14:00-17:00
]
# Pourquoi les écrire à la main : le test compare le code à ce qu'un humain attend,
# au lieu de recalculer la même chose avec le même code (qui aurait le même bug).


# --- Fonctions de base -------------------------------------------------------------

def test_lundi_de_la_semaine() -> None:
    """« 2026-W47 » commence le lundi 16 novembre 2026."""
    assert lundi_de_la_semaine("2026-W47") == date(2026, 11, 16)


@pytest.mark.parametrize("semaine", ["2026-47", "2026-W4", "W47-2026", "2026-W60"])
def test_semaine_mal_formee(semaine: str) -> None:
    """Un format de semaine invalide lève ValueError (l'API renverra 422)."""
    with pytest.raises(ValueError):
        lundi_de_la_semaine(semaine)


def test_lire_creneau() -> None:
    """« 18:00-20:00 » donne l'heure de début et l'heure de fin."""
    assert lire_creneau("18:00-20:00") == (time(18, 0), time(20, 0))


@pytest.mark.parametrize("texte", ["20:00-18:00", "18:00-18:00", "18h-20h", "25:00-26:00", ""])
def test_creneau_mal_forme(texte: str) -> None:
    """Créneau illisible, ou fin <= début → ValueError."""
    with pytest.raises(ValueError):
        lire_creneau(texte)


def test_decouper_en_sessions_le_reste_est_perdu() -> None:
    """17:30-19:00 en sessions de 60 min → une seule session, les 30 min restantes sont perdues."""
    sessions = decouper_en_sessions(Intervalle(heure(16, 17, 30), heure(16, 19)), 60)
    assert sessions == [Intervalle(heure(16, 17, 30), heure(16, 18, 30))]


def test_retirer_intervalles_coupe_en_deux() -> None:
    """Un créneau 14:00-17:00 dont 15:00-16:00 est occupé donne 14:00-15:00 et 16:00-17:00."""
    libres = retirer_intervalles(
        [Intervalle(heure(18, 14), heure(18, 17))],
        [Intervalle(heure(18, 15), heure(18, 16))],
    )
    assert libres == [
        Intervalle(heure(18, 14), heure(18, 15)),
        Intervalle(heure(18, 16), heure(18, 17)),
    ]


# --- Tests numérotés de SPEC.md §8 ---------------------------------------------------

def test_sessions_uniquement_dans_creneaux_libres() -> None:
    """Test 1 : chaque session est dans un créneau de dispo et hors des créneaux occupés."""
    occupe = Intervalle(heure(18, 15), heure(18, 16))
    sessions = lister_sessions_candidates(SEMAINE, DISPONIBILITES, [occupe], MAINTENANT)
    assert len(sessions) == 4  # lundi : 2 ; mercredi : 14-15 et 16-17
    for session in sessions:
        assert any(c.debut <= session.debut and session.fin <= c.fin for c in CRENEAUX_ATTENDUS)
        assert session.fin <= occupe.debut or session.debut >= occupe.fin


def test_aucune_session_ne_se_chevauche() -> None:
    """Test 2 : triées par début, chaque session finit avant que la suivante commence."""
    sessions = lister_sessions_candidates(SEMAINE, DISPONIBILITES, [], MAINTENANT)
    for precedente, suivante in zip(sessions, sessions[1:]):
        assert precedente.fin <= suivante.debut


def test_sans_disponibilite_liste_vide() -> None:
    """Test 5 : aucune disponibilité → liste vide, sans exception."""
    vide = Disponibilites(minutes_session=60, creneaux={})
    assert lister_sessions_candidates(SEMAINE, vide, [], MAINTENANT) == []


def test_creneau_trop_court_ignore() -> None:
    """Test 6 : un créneau de 45 min ne reçoit aucune session de 60 min."""
    court = Disponibilites(minutes_session=60, creneaux={"friday": ["17:30-18:15"]})
    assert lister_sessions_candidates(SEMAINE, court, [], MAINTENANT) == []


def test_creneaux_deja_passes_ignores() -> None:
    """CA3.8 : le lundi à 19:00, 18:00-19:00 est passé ; seul 19:00-20:00 reste ce jour-là."""
    maintenant = heure(16, 19)
    sessions = lister_sessions_candidates(SEMAINE, DISPONIBILITES, [], maintenant)
    assert all(session.debut >= maintenant for session in sessions)
    assert sessions[0] == Intervalle(heure(16, 19), heure(16, 20))
