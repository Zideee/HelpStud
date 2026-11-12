"""Tests 2 et 3 (métier) : le planificateur respecte les créneaux, les échéances et la priorité."""

from datetime import date, datetime

from app.services.planner import (
    FUSEAU,
    ChapitreAPlanifier,
    CoursAPlanifier,
    Disponibilites,
    EcheanceAPlanifier,
    Intervalle,
    SessionPlanifiee,
    generer_planning,
)

SEMAINE = "2026-W47"  # lundi 16/11/2026, heure d'hiver (UTC+1)
MAINTENANT = datetime(2026, 11, 15, 12, 0, tzinfo=FUSEAU)  # le dimanche d'avant
DISPONIBILITES = Disponibilites(
    minutes_session=60,
    creneaux={"monday": ["18:00-20:00"], "wednesday": ["14:00-17:00"]},
)
# Pourquoi des données fixes : le test donne le même résultat aujourd'hui et dans un an.


def heure(jour: int, heures: int) -> datetime:
    """Raccourci : une date-heure de novembre 2026 à Paris."""
    return datetime(2026, 11, jour, heures, 0, tzinfo=FUSEAU)


def cours(identifiant: int, priorite: str, minutes: int,
          echeances: list[tuple[date, int]]) -> CoursAPlanifier:
    """Un cours d'un seul chapitre (id = 10 × id du cours) avec ses échéances (date, poids)."""
    return CoursAPlanifier(
        id=identifiant,
        priorite=priorite,
        chapitres=[ChapitreAPlanifier(id=identifiant * 10, minutes_restantes=minutes)],
        echeances=[EcheanceAPlanifier(date=jour, poids=poids) for jour, poids in echeances],
    )
    # Pourquoi ce raccourci : chaque cas ne montre que ce qui compte (priorité, minutes, échéances).


def planifier(liste_cours: list[CoursAPlanifier], disponibilites: Disponibilites = DISPONIBILITES,
              occupes: list[Intervalle] | None = None) -> list[SessionPlanifiee]:
    """Appelle generer_planning avec la semaine et le « maintenant » fixes des tests."""
    return generer_planning(SEMAINE, liste_cours, disponibilites, occupes or [], MAINTENANT)


def test_planning_respecte_les_creneaux() -> None:
    """Créneaux libres uniquement, sans chevauchement, avant l'échéance (CA3.1 à CA3.3)."""
    dispos = [Intervalle(heure(16, 18), heure(16, 20)), Intervalle(heure(18, 14), heure(18, 17))]
    occupe = Intervalle(heure(18, 15), heure(18, 16))

    # 1. Dans les dispos, hors du créneau occupé, sans chevauchement.
    sessions = planifier([cours(1, "medium", 600, [(date(2026, 12, 18), 50)])], occupes=[occupe])
    assert len(sessions) == 4  # lundi 18h et 19h ; mercredi 14h et 16h
    for session in sessions:
        assert any(c.debut <= session.debut and session.fin <= c.fin for c in dispos)
        assert session.fin <= occupe.debut or session.debut >= occupe.fin
    for precedente, suivante in zip(sessions, sessions[1:]):
        assert precedente.fin <= suivante.debut

    # 2. Échéance le mercredi 18/11 → seulement les 2 sessions du lundi.
    avant_mercredi = planifier([cours(1, "medium", 600, [(date(2026, 11, 18), 50)])])
    assert [session.debut for session in avant_mercredi] == [heure(16, 18), heure(16, 19)]

    # 3. Créneau de 45 min pour des sessions de 60 min, ou aucune dispo → liste vide, sans erreur.
    court = Disponibilites(minutes_session=60, creneaux={"friday": ["17:30-18:15"]})
    assert planifier([cours(1, "medium", 600, [])], disponibilites=court) == []
    assert planifier([cours(1, "medium", 600, [])], Disponibilites(60, {})) == []
    # Pourquoi regrouper ces cas : ensemble, ils prouvent la règle « jamais de session à un
    # moment interdit » ; chaque bloc numéroté correspond à un critère CA.


def test_planning_respecte_la_priorite() -> None:
    """Score = poids × coef / jours ; cours sans échéance en dernier ; examen passé ignoré (§5.2)."""
    # 1. Exemple 1 de SPEC §5.2 : A (haute, J+10, poids 60 → 12) passe avant
    #    B (moyenne, J+4, poids 30 → 7,5), même donnés dans l'ordre [B, A].
    a = cours(1, "high", 600, [(date(2026, 11, 26), 60)])
    b = cours(2, "medium", 600, [(date(2026, 11, 20), 30)])
    assert planifier([b, a])[0].cours_id == 1

    # 2. Y (avec échéance, 120 min) prend les 2 premières sessions, puis X (sans échéance).
    x = cours(1, "high", 600, [])
    y = cours(2, "low", 120, [(date(2026, 12, 18), 10)])
    assert [session.cours_id for session in planifier([x, y])] == [2, 2, 1, 1, 1]

    # 3. Un cours dont l'examen est passé n'est plus planifié.
    assert planifier([cours(1, "high", 600, [(date(2026, 11, 10), 50)])]) == []
    # Pourquoi l'ordre [B, A] : si le code prenait simplement le premier de la liste,
    # le test échouerait ; c'est bien le score qui doit décider.
