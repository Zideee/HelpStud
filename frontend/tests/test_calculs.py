"""Tests 11 et 12 (front) : calculs purs du front (frontend/calculs.py), sans Streamlit ni réseau."""

from calculs import CATEGORIES, JOURS, PRIORITES, TYPES_ECHEANCE, ecrire_creneaux, libelle, lire_creneaux_saisis


def test_semaine_iso_et_libelles() -> None:
    """Test 11 : libellés français ↔ valeurs de l'API (CA1.7, CA2.5).

    La partie « date → semaine AAAA-Wnn » sera ajoutée à ce test en P0-15 (page Planning).
    """
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
    # Pourquoi tester ces tables : une faute de frappe (« continous ») ferait renvoyer
    # un 422 par l'API à chaque import, alors que la page aurait l'air correcte.
