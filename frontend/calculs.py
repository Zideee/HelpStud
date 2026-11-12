"""Calculs purs du front : libellés français, conversions, indicateurs du dashboard.

PYTHON PUR : aucun import de Streamlit ni de httpx. Les pages appellent ces fonctions,
ce qui permet de les tester sans navigateur ni serveur (tests 11 et 12).
"""

from datetime import date, datetime, time
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


def ligne_creneau(jour: str, debut: str, fin: str) -> dict:
    """Une ligne du tableau des disponibilités : {"Jour": "Lundi", "Début": time, "Fin": time}."""
    return {"Jour": JOURS[jour], "Début": time.fromisoformat(debut), "Fin": time.fromisoformat(fin)}


SUGGESTIONS_CRENEAUX = {
    "Soirs en semaine (18h–20h)": [ligne_creneau(jour, "18:00", "20:00")
                                   for jour in ("monday", "tuesday", "wednesday", "thursday", "friday")],
    "Mercredi après-midi (14h–17h)": [ligne_creneau("wednesday", "14:00", "17:00")],
    "Week-end matin (10h–12h)": [ligne_creneau(jour, "10:00", "12:00") for jour in ("saturday", "sunday")],
    "Week-end après-midi (14h–18h)": [ligne_creneau(jour, "14:00", "18:00") for jour in ("saturday", "sunday")],
}
# Pourquoi des suggestions : l'étudiant clique au lieu de taper des heures ; les lignes
# ajoutées restent modifiables dans le tableau (demande de l'équipe).


def creneaux_vers_lignes(creneaux: dict[str, list[str]]) -> list[dict]:
    """Créneaux du contrat ({"monday": ["18:00-20:00"]}) → lignes du tableau, triées par jour puis heure."""
    lignes = []
    for jour in JOURS:
        for creneau in sorted(creneaux.get(jour, [])):
            debut, fin = creneau.split("-")
            lignes.append(ligne_creneau(jour, debut, fin))
    return lignes
    # Pourquoi parcourir JOURS : l'ordre lundi → dimanche vient du dictionnaire, pas de l'API.


def lignes_vers_creneaux(lignes: list[dict]) -> dict[str, list[str]]:
    """Le sens inverse : lignes du tableau → créneaux du contrat ; les lignes incomplètes sont ignorées."""
    cle_du_jour = {libelle_jour: cle for cle, libelle_jour in JOURS.items()}
    creneaux: dict[str, list[str]] = {}
    for ligne in lignes:
        jour, debut, fin = ligne.get("Jour"), ligne.get("Début"), ligne.get("Fin")
        if jour in cle_du_jour and isinstance(debut, time) and isinstance(fin, time):
            creneaux.setdefault(cle_du_jour[jour], []).append(f"{debut:%H:%M}-{fin:%H:%M}")
    return {jour: sorted(set(liste)) for jour, liste in creneaux.items()}
    # Pourquoi isinstance(…, time) : une case vide du tableau vaut None ou « NaN », jamais
    # une heure ; on n'envoie pas de créneau à moitié rempli. Pourquoi set() : une suggestion
    # cliquée deux fois ne crée pas de doublon. Une fin avant le début, elle, est refusée par
    # l'API (422) avec un message clair.


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


def prochaine_session(sessions: list[dict], maintenant: datetime) -> dict | None:
    """La 1re session pas faite et pas encore finie (celle en cours compte), ou None."""
    a_faire = [session for session in sessions
               if not session["done"] and datetime.fromisoformat(session["end"]) > maintenant]
    return min(a_faire, key=lambda session: session["start"], default=None)
    # Pourquoi la FIN et pas le début : une session commencée il y a 10 minutes est
    # encore « à faire maintenant » ; c'est elle que l'étudiant doit voir en premier.


def prochaines_echeances(echeances: list[dict], aujourdhui: date, nombre: int = 3) -> list[dict]:
    """Les `nombre` prochaines échéances (aujourd'hui inclus), de la plus proche à la plus lointaine."""
    a_venir = [echeance for echeance in echeances if date.fromisoformat(echeance["date"]) >= aujourdhui]
    return sorted(a_venir, key=lambda echeance: echeance["date"])[:nombre]
    # Pourquoi trier ici alors que l'API trie déjà : la fonction ne dépend pas d'un détail
    # de l'API ; elle reste juste même si on lui donne une liste dans le désordre.
