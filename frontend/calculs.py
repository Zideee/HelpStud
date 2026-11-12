"""Calculs purs du front : libellés français, conversions, indicateurs du dashboard.

PYTHON PUR : aucun import de Streamlit ni de httpx. Les pages appellent ces fonctions,
ce qui permet de les tester sans navigateur ni serveur (tests 11 et 12).
"""

PRIORITES = {"Haute": "high", "Moyenne": "medium", "Basse": "low"}
CATEGORIES = {"Examen": "exam", "Contrôle continu": "continuous", "Mixte": "mixed", "Non précisée": None}
TYPES_ECHEANCE = {"Examen": "exam", "Contrôle continu": "assignment"}
JOURS = {"monday": "Lundi", "tuesday": "Mardi", "wednesday": "Mercredi", "thursday": "Jeudi",
         "friday": "Vendredi", "saturday": "Samedi", "sunday": "Dimanche"}
# Pourquoi des dictionnaires « libellé → valeur API » : l'écran parle français, l'API parle
# le contrat (anglais). La traduction est écrite une seule fois, ici, pour toutes les pages.
# JOURS est dans l'autre sens (« clé API → libellé ») car la page parcourt les 7 clés du
# contrat dans l'ordre pour afficher un champ par jour.


def libelle(correspondances: dict[str, str | None], valeur: str | None) -> str:
    """Le libellé français d'une valeur de l'API (la valeur elle-même si elle est inconnue)."""
    for texte, valeur_api in correspondances.items():
        if valeur_api == valeur:
            return texte
    return str(valeur)
    # Pourquoi ne pas lever d'erreur pour une valeur inconnue : si l'API ajoute une valeur
    # un jour, la page l'affiche brute au lieu de planter devant l'étudiant.


def lire_creneaux_saisis(texte: str) -> list[str]:
    """« 18:00-20:00, 21:00-22:00 » → ["18:00-20:00", "21:00-22:00"] (vide → [])."""
    return [creneau.strip() for creneau in texte.split(",") if creneau.strip()]
    # Pourquoi une virgule : un seul champ texte par jour reste simple à remplir ; c'est
    # l'API qui vérifie ensuite le format exact de chaque créneau (422 sinon).


def ecrire_creneaux(creneaux: list[str]) -> str:
    """Le sens inverse : la liste du contrat → le texte à afficher dans le champ."""
    return ", ".join(creneaux)
