"""Client de l'API HelpStud : le SEUL module du front qui fait des requêtes HTTP.

Les pages Streamlit appellent ces fonctions ; elles ne connaissent ni httpx, ni les routes,
ni la base de données (règle absolue n° 2 d'AGENTS.md).
"""

import os
from datetime import date

import httpx

URL_API = os.environ.get("HELPSTUD_API_URL", "http://localhost:8000")
DELAI_SECONDES = 10
# Pourquoi une variable d'environnement : en démo ou sur un autre poste, on change l'adresse
# de l'API sans toucher au code.


class ErreurApi(Exception):
    """Erreur renvoyée par l'API, avec un message lisible et le code HTTP (s'il y en a un)."""

    def __init__(self, message: str, code: int | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.code = code
    # Pourquoi une exception à nous : les pages n'ont qu'un seul type d'erreur à attraper,
    # et elles affichent directement erreur.message à l'étudiant.


def creer_client() -> httpx.Client:
    """Un client HTTP vers l'API (remplacé par un faux serveur dans les tests)."""
    return httpx.Client(base_url=URL_API, timeout=DELAI_SECONDES)
    # Pourquoi une fonction : les tests la remplacent pour parler à un faux serveur.


def message_erreur(reponse: httpx.Response) -> str:
    """Le message lisible d'une réponse d'erreur FastAPI."""
    try:
        detail = reponse.json().get("detail")
    except ValueError:
        detail = None
    if isinstance(detail, list):
        return " ; ".join(str(erreur.get("msg", erreur)) for erreur in detail)
    if isinstance(detail, str):
        return detail
    return f"Erreur {reponse.status_code} de l'API"
    # Pourquoi deux cas : nos HTTPException renvoient un texte ; les erreurs de validation
    # Pydantic (422) renvoient une liste d'objets, dont on ne garde que les messages.


def envoyer(methode: str, chemin: str, **options) -> httpx.Response:
    """Envoie une requête à l'API ; lève ErreurApi si l'API est injoignable ou répond une erreur."""
    try:
        with creer_client() as client:
            reponse = client.request(methode, chemin, **options)
    except httpx.ConnectError as erreur:
        raise ErreurApi("API injoignable : lancez le back (uvicorn app.main:app --app-dir backend)") from erreur
    except httpx.TimeoutException as erreur:
        raise ErreurApi("L'API ne répond pas (délai dépassé)") from erreur
    if reponse.status_code >= 400:
        raise ErreurApi(message_erreur(reponse), reponse.status_code)
    return reponse
    # Pourquoi tout passer par cette fonction : la gestion des erreurs est écrite une seule
    # fois, et chaque fonction ci-dessous tient en une ou deux lignes.


# --- Cours -------------------------------------------------------------------------------

def lister_cours() -> list[dict]:
    """GET /courses : les cours avec leur avancement."""
    return envoyer("GET", "/courses").json()


def importer_cours(nom_fichier: str, contenu: bytes, priorite: str, categorie: str | None) -> dict:
    """POST /courses : envoie le fichier, avec la priorité et la catégorie choisies avant."""
    champs = {"priority": priorite}
    if categorie is not None:
        champs["category"] = categorie
    return envoyer("POST", "/courses", files={"file": (nom_fichier, contenu)}, data=champs).json()
    # Pourquoi ne pas envoyer category quand elle vaut None : un champ de formulaire ne peut
    # pas valoir « null » ; l'absence du champ donne la valeur par défaut (non précisée).


def modifier_cours(cours_id: int, priorite: str | None = None, categorie: str | None = None) -> dict:
    """PATCH /courses/{id} : change la priorité et/ou la catégorie."""
    corps = {cle: valeur for cle, valeur in (("priority", priorite), ("category", categorie))
             if valeur is not None}
    return envoyer("PATCH", f"/courses/{cours_id}", json=corps).json()


# --- Échéances et disponibilités ------------------------------------------------------------

def lister_echeances() -> list[dict]:
    """GET /deadlines : les échéances triées par date."""
    return envoyer("GET", "/deadlines").json()


def creer_echeance(cours_id: int, titre: str, type_echeance: str, date_echeance: date, poids: int) -> dict:
    """POST /deadlines : crée une échéance (type exam = examen, assignment = contrôle continu)."""
    corps = {"course_id": cours_id, "title": titre, "type": type_echeance,
             "date": date_echeance.isoformat(), "weight": poids}
    return envoyer("POST", "/deadlines", json=corps).json()


def supprimer_echeance(echeance_id: int) -> None:
    """DELETE /deadlines/{id}."""
    envoyer("DELETE", f"/deadlines/{echeance_id}")


def lire_disponibilites() -> dict | None:
    """GET /availability : les disponibilités enregistrées, ou None si rien n'est saisi."""
    try:
        return envoyer("GET", "/availability").json()
    except ErreurApi as erreur:
        if erreur.code == 404:
            return None
        raise
    # Pourquoi transformer ce 404 en None : pour cette route, 404 veut dire « pas encore
    # saisi », une situation normale au premier lancement, pas une panne.


def enregistrer_disponibilites(minutes_session: int, creneaux: dict[str, list[str]]) -> dict:
    """PUT /availability : remplace les disponibilités."""
    return envoyer("PUT", "/availability", json={"session_minutes": minutes_session, "slots": creneaux}).json()


# --- Planning ------------------------------------------------------------------------------

def generer_planning(semaine: str) -> list[dict]:
    """POST /plan/generate : (re)génère la semaine « AAAA-Wnn »."""
    return envoyer("POST", "/plan/generate", json={"week": semaine}).json()


def lire_planning(semaine: str) -> list[dict]:
    """GET /plan?week=… : les sessions de la semaine."""
    return envoyer("GET", "/plan", params={"week": semaine}).json()


def marquer_session(session_id: int, faite: bool) -> dict:
    """PATCH /sessions/{id} : marque une session comme faite (ou non faite)."""
    return envoyer("PATCH", f"/sessions/{session_id}", json={"done": faite}).json()


def telecharger_ics() -> bytes:
    """GET /plan.ics : le calendrier à importer dans Google Agenda ou Outlook."""
    return envoyer("GET", "/plan.ics").content
