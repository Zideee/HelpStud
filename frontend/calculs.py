"""Calculs purs du front : libellés français, conversions, indicateurs du dashboard.

PYTHON PUR : aucun import de Streamlit ni de httpx. Les pages appellent ces fonctions,
ce qui permet de les tester sans navigateur ni serveur (tests 11 et 12).
"""

from datetime import date, datetime
from zoneinfo import ZoneInfo

FUSEAU = ZoneInfo("Europe/Paris")
PRIORITES = {"Haute": "high", "Moyenne": "medium", "Basse": "low"}
CATEGORIES = {"Examen": "exam", "Contrôle continu": "continuous", "Mixte": "mixed", "Sans échéance": None}
# CATEGORIES ne sert plus qu'à l'AFFICHAGE : la catégorie est calculée par l'API (CA2.7).
TYPES_ECHEANCE = {"Examen": "exam", "Contrôle continu": "assignment"}
JOURS_COURTS = ["Lun", "Mar", "Mer", "Jeu", "Ven", "Sam", "Dim"]
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


def semaine_iso(jour: date) -> str:
    """La semaine ISO d'une date, au format de l'API : « AAAA-Wnn »."""
    annee, numero, _ = jour.isocalendar()
    return f"{annee}-W{numero:02d}"
    # Pourquoi l'année ISO et pas jour.year : le 1er janvier 2027 appartient à la semaine 53
    # de 2026 ; avec jour.year, on enverrait « 2027-W53 », une semaine qui n'existe pas.


def jour_et_horaire(debut_iso: str, fin_iso: str) -> tuple[str, str]:
    """« 2026-11-16T18:00:00+01:00 » → (« Lun 16/11 », « 18:00–19:00 »)."""
    debut, fin = datetime.fromisoformat(debut_iso), datetime.fromisoformat(fin_iso)
    jour = f"{JOURS_COURTS[debut.weekday()]} {debut:%d/%m}"
    return jour, f"{debut:%H:%M}–{fin:%H:%M}"
    # Pourquoi nos propres noms de jours : strftime(« %a ») dépend de la langue de
    # l'ordinateur (« Mon » sur un poste en anglais) ; ici, c'est toujours en français.


def compter_sessions(sessions: list[dict], maintenant: datetime) -> tuple[int, int]:
    """(sessions faites, sessions en retard) : en retard = finie avant maintenant et pas faite."""
    faites = sum(1 for session in sessions if session["done"])
    en_retard = sum(1 for session in sessions
                    if not session["done"] and datetime.fromisoformat(session["end"]) < maintenant)
    return faites, en_retard
    # Pourquoi comparer la FIN de la session : une session commencée mais pas terminée
    # n'est pas encore « en retard » (CA5.2, décision Q11 de SPEC.md).


def prochaines_echeances(echeances: list[dict], aujourdhui: date, nombre: int = 3) -> list[dict]:
    """Les `nombre` prochaines échéances (aujourd'hui inclus), de la plus proche à la plus lointaine."""
    a_venir = [echeance for echeance in echeances if date.fromisoformat(echeance["date"]) >= aujourdhui]
    return sorted(a_venir, key=lambda echeance: echeance["date"])[:nombre]
    # Pourquoi trier ici alors que l'API trie déjà : la fonction ne dépend pas d'un détail
    # de l'API ; elle reste juste même si on lui donne une liste dans le désordre.
