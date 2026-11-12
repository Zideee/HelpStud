"""Tests 11 et 12 (front) : calculs purs du front (frontend/calculs.py), sans Streamlit ni réseau."""

from datetime import date

from calculs import (
    CATEGORIES,
    JOURS,
    PRIORITES,
    TYPES_ECHEANCE,
    ecrire_creneaux,
    jour_et_horaire,
    libelle,
    lire_creneaux_saisis,
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
    assert CATEGORIES["Contrôle continu"] == "continuous" and CATEGORIES["Non précisée"] is None
    assert TYPES_ECHEANCE["Contrôle continu"] == "assignment"
    # Ce que l'API renvoie → ce qu'on affiche (sens inverse).
    assert libelle(PRIORITES, "medium") == "Moyenne"
    assert libelle(CATEGORIES, None) == "Non précisée"
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
