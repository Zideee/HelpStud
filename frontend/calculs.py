"""Calculs purs du front : libellés français, conversions, indicateurs du dashboard.

PYTHON PUR : aucun import de Streamlit ni de httpx. Les pages appellent ces fonctions,
ce qui permet de les tester sans navigateur ni serveur (tests 11 et 12).
"""

PRIORITES = {"Haute": "high", "Moyenne": "medium", "Basse": "low"}
CATEGORIES = {"Examen": "exam", "Contrôle continu": "continuous", "Mixte": "mixed", "Non précisée": None}
TYPES_ECHEANCE = {"Examen": "exam", "Contrôle continu": "assignment"}
# Pourquoi des dictionnaires « libellé → valeur API » : l'écran parle français, l'API parle
# le contrat (anglais). La traduction est écrite une seule fois, ici, pour toutes les pages.


def libelle(correspondances: dict[str, str | None], valeur: str | None) -> str:
    """Le libellé français d'une valeur de l'API (la valeur elle-même si elle est inconnue)."""
    for texte, valeur_api in correspondances.items():
        if valeur_api == valeur:
            return texte
    return str(valeur)
    # Pourquoi ne pas lever d'erreur pour une valeur inconnue : si l'API ajoute une valeur
    # un jour, la page l'affiche brute au lieu de planter devant l'étudiant.
