"""Tests du planificateur (services/planner.py) — créneaux (P0-04), priorité et échéances (P0-05)."""

from datetime import date, datetime, time

import pytest

from app.services.planner import (
    FUSEAU,
    ChapitreAPlanifier,
    CoursAPlanifier,
    Disponibilites,
    EcheanceAPlanifier,
    Intervalle,
    SessionPlanifiee,
    calculer_score,
    decouper_en_sessions,
    generer_planning,
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


def test_creneaux_deja_passes_ignores() -> None:
    """CA3.8 : le lundi à 19:00, 18:00-19:00 est passé ; seul 19:00-20:00 reste ce jour-là."""
    maintenant = heure(16, 19)
    sessions = lister_sessions_candidates(SEMAINE, DISPONIBILITES, [], maintenant)
    assert all(session.debut >= maintenant for session in sessions)
    assert sessions[0] == Intervalle(heure(16, 19), heure(16, 20))


# --- Construction des cours de test --------------------------------------------------

def cours(identifiant: int, priorite: str, minutes: int,
          echeances: list[tuple[date, int]]) -> CoursAPlanifier:
    """Un cours d'un seul chapitre (id = 10 × id du cours) avec ses échéances (date, poids)."""
    return CoursAPlanifier(
        id=identifiant,
        priorite=priorite,
        chapitres=[ChapitreAPlanifier(id=identifiant * 10, minutes_restantes=minutes)],
        echeances=[EcheanceAPlanifier(date=jour, poids=poids) for jour, poids in echeances],
    )
    # Pourquoi un constructeur : chaque test ne montre que ce qui compte pour lui
    # (priorité, minutes, échéances), sans 6 lignes de dataclasses à chaque fois.


COURS_SIMPLE = [cours(1, "medium", 600, [(date(2026, 12, 18), 50)])]


def planifier(liste_cours: list[CoursAPlanifier], disponibilites: Disponibilites = DISPONIBILITES,
              occupes: list[Intervalle] | None = None) -> list[SessionPlanifiee]:
    """Appelle generer_planning avec la semaine et le « maintenant » fixes des tests."""
    return generer_planning(SEMAINE, liste_cours, disponibilites, occupes or [], MAINTENANT)


# --- Tests numérotés de SPEC.md §8 ---------------------------------------------------

def test_sessions_uniquement_dans_creneaux_libres() -> None:
    """Test 1 : chaque session est dans un créneau de dispo et hors des créneaux occupés."""
    occupe = Intervalle(heure(18, 15), heure(18, 16))
    sessions = planifier(COURS_SIMPLE, occupes=[occupe])
    assert len(sessions) == 4  # lundi : 2 ; mercredi : 14-15 et 16-17
    for session in sessions:
        assert any(c.debut <= session.debut and session.fin <= c.fin for c in CRENEAUX_ATTENDUS)
        assert session.fin <= occupe.debut or session.debut >= occupe.fin


def test_aucune_session_ne_se_chevauche() -> None:
    """Test 2 : triées par début, chaque session finit avant que la suivante commence."""
    sessions = planifier(COURS_SIMPLE)
    for precedente, suivante in zip(sessions, sessions[1:]):
        assert precedente.fin <= suivante.debut


def test_aucune_session_apres_echeance() -> None:
    """Test 3 : échéance le mercredi 18/11 → sessions le lundi, aucune le mercredi."""
    sessions = planifier([cours(1, "medium", 600, [(date(2026, 11, 18), 50)])])
    limite = datetime(2026, 11, 18, 0, 0, tzinfo=FUSEAU)
    assert len(sessions) == 2
    assert all(session.fin <= limite for session in sessions)


def test_cours_prioritaire_place_en_premier() -> None:
    """Test 4 : à priorité égale, A (J+5, score 10) passe avant B (J+10, score 5)."""
    a = cours(1, "medium", 600, [(date(2026, 11, 21), 50)])
    b = cours(2, "medium", 600, [(date(2026, 11, 26), 50)])
    sessions = planifier([b, a])
    assert sessions[0].cours_id == 1
    # Pourquoi passer [b, a] dans cet ordre : si le code prenait juste le premier de la
    # liste, le test le verrait ; c'est bien le score qui doit décider.


def test_sans_disponibilite_liste_vide() -> None:
    """Test 5 : aucune disponibilité → liste vide, sans exception."""
    vide = Disponibilites(minutes_session=60, creneaux={})
    assert planifier(COURS_SIMPLE, disponibilites=vide) == []


def test_creneau_trop_court_ignore() -> None:
    """Test 6 : un créneau de 45 min ne reçoit aucune session de 60 min."""
    court = Disponibilites(minutes_session=60, creneaux={"friday": ["17:30-18:15"]})
    assert planifier(COURS_SIMPLE, disponibilites=court) == []


def test_priorite_haute_multiplie_le_score() -> None:
    """Test 13 : A haute J+10 poids 60 (score 12) passe avant B moyenne J+4 poids 30 (7,5)."""
    a = cours(1, "high", 600, [(date(2026, 11, 26), 60)])
    b = cours(2, "medium", 600, [(date(2026, 11, 20), 30)])
    sessions = planifier([b, a])
    assert sessions[0].cours_id == 1


def test_cours_sans_echeance_planifie_en_dernier() -> None:
    """Test 14 : Y (avec échéance, 120 min) prend les 2 premières sessions, puis X (sans)."""
    x = cours(1, "high", 600, [])
    y = cours(2, "low", 120, [(date(2026, 12, 18), 10)])
    sessions = planifier([x, y])
    assert [session.cours_id for session in sessions] == [2, 2, 1, 1, 1]


# --- Autres règles de P0-05 ----------------------------------------------------------

def test_chapitres_planifies_dans_l_ordre() -> None:
    """Le 1er chapitre est terminé avant de passer au 2e."""
    deux_chapitres = CoursAPlanifier(
        id=1, priorite="medium",
        chapitres=[ChapitreAPlanifier(id=10, minutes_restantes=60),
                   ChapitreAPlanifier(id=11, minutes_restantes=600)],
        echeances=[EcheanceAPlanifier(date=date(2026, 12, 18), poids=50)],
    )
    sessions = planifier([deux_chapitres])
    assert [session.chapitre_id for session in sessions] == [10, 11, 11, 11, 11]


def test_cours_termine_plus_planifie() -> None:
    """Quand toutes les minutes d'un cours sont placées, il ne reçoit plus de session."""
    sessions = planifier([cours(1, "medium", 60, [(date(2026, 12, 18), 50)])])
    assert len(sessions) == 1


def test_cours_aux_echeances_passees_non_planifie() -> None:
    """Un cours dont toutes les échéances sont passées n'est plus planifié (examen fini)."""
    sessions = planifier([cours(1, "high", 600, [(date(2026, 11, 10), 50)])])
    assert sessions == []


def test_calculer_score() -> None:
    """Exemple 2 de SPEC §5.2 : basse J+1 poids 50 → 25 ; haute J+20 poids 50 → 5."""
    jour = date(2026, 11, 16)
    assert calculer_score(cours(1, "low", 60, [(date(2026, 11, 17), 50)]), jour) == 25
    assert calculer_score(cours(2, "high", 60, [(date(2026, 12, 6), 50)]), jour) == 5
    assert calculer_score(cours(3, "high", 60, []), jour) is None
