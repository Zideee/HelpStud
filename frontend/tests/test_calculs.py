"""Tests 11 et 12 (front) : calculs purs du front (frontend/calculs.py), sans Streamlit ni réseau."""

from calculs import CATEGORIES, PRIORITES, TYPES_ECHEANCE, libelle


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
    # Pourquoi tester ces tables : une faute de frappe (« continous ») ferait renvoyer
    # un 422 par l'API à chaque import, alors que la page aurait l'air correcte.
