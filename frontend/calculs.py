"""Calculs purs du front : libellés français, conversions, indicateurs du dashboard.

PYTHON PUR : aucun import de Streamlit ni de httpx. Les pages appellent ces fonctions,
ce qui permet de les tester sans navigateur ni serveur (tests 11 et 12).
"""

import calendar
import re
from datetime import date, datetime, time, timedelta
from zoneinfo import ZoneInfo

FUSEAU = ZoneInfo("Europe/Paris")
SEMAINES_SANS_ECHEANCE = 4   # semaines planifiées quand aucune échéance n'est à venir
SEMAINES_MAX = 8             # jamais plus : au-delà, les disponibilités auront sûrement changé
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


MOTIF_HEURE = re.compile(r"^\s*(\d{1,2})\s*(?:[h:]\s*(\d{2})?)?\s*$", re.IGNORECASE)


def lire_heure(texte: object) -> time | None:
    """Heure tapée par l'étudiant → time : « 18:30 », « 18h », « 9h15 », « 18 » ; None si illisible."""
    correspondance = MOTIF_HEURE.match(texte) if isinstance(texte, str) else None
    if correspondance is None:
        return None
    heures, minutes = int(correspondance.group(1)), int(correspondance.group(2) or 0)
    return time(heures, minutes) if heures < 24 and minutes < 60 else None
    # Pourquoi accepter plusieurs écritures : chacun tape l'heure à sa façon (« 18h », « 18:00 ») ;
    # c'est au programme de comprendre, pas à l'étudiant de deviner le bon format.
    # Pourquoi `object` : une case vide du tableau peut valoir None ou NaN, pas seulement du texte.


def ligne_creneau(jour: str, debut: str, fin: str) -> dict:
    """Une ligne du tableau des disponibilités : {"Jour": "Lundi", "Début": "18:00", "Fin": "20:00"}."""
    return {"Jour": JOURS[jour], "Début": debut, "Fin": fin}
    # Pourquoi du texte et pas un objet time : la case reste un simple champ où l'on tape.


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
        jour, debut, fin = ligne.get("Jour"), lire_heure(ligne.get("Début")), lire_heure(ligne.get("Fin"))
        if jour in cle_du_jour and debut and fin:
            creneaux.setdefault(cle_du_jour[jour], []).append(f"{debut:%H:%M}-{fin:%H:%M}")
    return {jour: sorted(set(liste)) for jour, liste in creneaux.items()}
    # Pourquoi lire_heure : « 9h » devient « 09:00 », le format exact du contrat. Une case vide
    # ou illisible donne None : on n'envoie pas de créneau à moitié rempli. Pourquoi set() : une
    # suggestion cliquée deux fois ne crée pas de doublon. Une fin avant le début, elle, est
    # refusée par l'API (422) avec un message clair.


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


def semaines_a_generer(aujourdhui: date, echeances: list[dict]) -> list[str]:
    """Semaines « AAAA-Wnn » à planifier, dans l'ordre : de cette semaine à celle de la dernière échéance à venir."""
    lundi = aujourdhui - timedelta(days=aujourdhui.weekday())
    a_venir = [date.fromisoformat(echeance["date"]) for echeance in echeances
               if date.fromisoformat(echeance["date"]) >= aujourdhui]
    derniere = max(a_venir) if a_venir else lundi + timedelta(weeks=SEMAINES_SANS_ECHEANCE - 1)
    nombre = min((derniere - lundi).days // 7 + 1, SEMAINES_MAX)
    return [semaine_iso(lundi + timedelta(weeks=numero)) for numero in range(nombre)]
    # Pourquoi toutes les semaines d'un coup, dans l'ordre : l'API génère une semaine à la fois
    # et compte ce qui est déjà placé ; générer seulement une semaine lointaine oubliait les
    # cours dont l'examen tombe avant (bug vu avec 2 cours).


def grille_du_mois(annee: int, mois: int) -> list[list[date]]:
    """Les semaines du mois, du lundi au dimanche, en débordant sur les mois voisins (comme un agenda)."""
    return calendar.Calendar(firstweekday=0).monthdatescalendar(annee, mois)
    # Pourquoi le module calendar (bibliothèque standard) : il sait déjà découper un mois en
    # semaines complètes ; inutile de réécrire ce calcul (et ses pièges) nous-mêmes.


def sessions_par_date(sessions: list[dict]) -> dict[date, list[dict]]:
    """Range les sessions par jour, dans l'ordre des heures, pour les poser dans les cases du calendrier."""
    rangees: dict[date, list[dict]] = {}
    for session in sorted(sessions, key=lambda session: session["start"]):
        rangees.setdefault(datetime.fromisoformat(session["start"]).date(), []).append(session)
    return rangees
    # Pourquoi trier d'abord : dans chaque case, les sessions apparaissent de la plus tôt à la plus tard.


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
