"""Tests 11 et 12 (front) : calculs purs du front (frontend/calculs.py), sans Streamlit ni réseau."""

from datetime import date, datetime
from zoneinfo import ZoneInfo

from calculs import (
    CATEGORIES,
    FUSEAU,
    JOURS,
    PRIORITES,
    TYPES_ECHEANCE,
    compter_sessions,
    ecrire_creneaux,
    jour_et_horaire,
    libelle,
    lire_creneaux_saisis,
    prochaines_echeances,
    semaine_iso,
)


def test_semaine_iso_et_libelles() -> None:
    """Test 11 : date → semaine « AAAA-Wnn » ; libellés français ↔ valeurs de l'API (CA1.7, CA2.5)."""
    # Date choisie dans le calendrier → semaine envoyée à l'API (P0-15).
    assert semaine_iso(date(2026, 11, 18)) == "2026-W47"
    assert semaine_iso(date(2027, 1, 1)) == "2026-W53"  # le 1er janvier peut être en semaine 53 !
    # Affichage d'une session : jour court et horaire, à l'heure de Paris.
    assert jour_et_horaire("2026-11-16T18:00:00+01:00", "2026-11-16T19:00:00+01:00") == (
        "Lun 16/11", "18:00–19:00")

    # Ce que l'étudiant choisit à l'écran → ce que l'API attend.
    assert PRIORITES["Haute"] == "high" and PRIORITES["Basse"] == "low"
    assert CATEGORIES["Contrôle continu"] == "continuous" and CATEGORIES["Sans échéance"] is None
    assert TYPES_ECHEANCE["Contrôle continu"] == "assignment"
    # Ce que l'API renvoie → ce qu'on affiche (sens inverse).
    assert libelle(PRIORITES, "medium") == "Moyenne"
    assert libelle(CATEGORIES, None) == "Sans échéance"  # catégorie calculée, aucune date
    assert libelle(TYPES_ECHEANCE, "exam") == "Examen"
    # Une valeur inconnue s'affiche telle quelle au lieu de faire planter la page.
    assert libelle(PRIORITES, "urgent") == "urgent"
    # Saisie des disponibilités : « 18:00-20:00, 21:00-22:00 » ↔ liste du contrat (P0-14).
    assert lire_creneaux_saisis(" 18:00-20:00 , 21:00-22:00, ") == ["18:00-20:00", "21:00-22:00"]
    assert lire_creneaux_saisis("") == []
    assert ecrire_creneaux(["18:00-20:00", "21:00-22:00"]) == "18:00-20:00, 21:00-22:00"
    assert JOURS["monday"] == "Lundi" and len(JOURS) == 7
    # Pourquoi tester ces conversions : une semaine mal calculée (fin décembre) ou une faute
    # de frappe (« continous ») ferait échouer l'API alors que la page aurait l'air correcte.


def test_indicateurs_dashboard() -> None:
    """Test 12 : sessions faites / en retard et 3 prochaines échéances (CA5.2)."""
    maintenant = datetime(2026, 11, 18, 12, 0, tzinfo=FUSEAU)  # mercredi midi
    sessions = [
        {"start": "2026-11-16T18:00:00+01:00", "end": "2026-11-16T19:00:00+01:00", "done": True},   # faite
        {"start": "2026-11-16T19:00:00+01:00", "end": "2026-11-16T20:00:00+01:00", "done": False},  # en retard
        {"start": "2026-11-18T11:30:00+01:00", "end": "2026-11-18T12:30:00+01:00", "done": False},  # en cours
        {"start": "2026-11-19T18:00:00+01:00", "end": "2026-11-19T19:00:00+01:00", "done": False},  # à venir
    ]
    # 1 faite ; 1 seule en retard : celle en cours n'est pas finie, celle de jeudi est à venir.
    assert compter_sessions(sessions, maintenant) == (1, 1)

    echeances = [
        {"title": "Partiel", "date": "2026-12-08"}, {"title": "Passée", "date": "2026-11-10"},
        {"title": "Projet", "date": "2026-11-27"}, {"title": "Examen", "date": "2026-12-18"},
        {"title": "Aujourd'hui", "date": "2026-11-18"},
    ]
    # Les 3 plus proches à partir d'aujourd'hui (inclus), triées ; la passée est ignorée.
    assert [e["title"] for e in prochaines_echeances(echeances, date(2026, 11, 18))] == [
        "Aujourd'hui", "Projet", "Partiel"]
    # Pourquoi « maintenant » est un paramètre : le test choisit l'heure, donc le résultat
    # ne dépend pas du jour où l'on lance pytest.
    assert FUSEAU == ZoneInfo("Europe/Paris")
