"""Export des sessions en calendrier .ics — PYTHON PUR : aucun import de FastAPI, sqlite3 ou app.db."""

from dataclasses import dataclass
from datetime import datetime, timezone

from icalendar import Calendar, Event

IDENTIFIANT_PRODUIT = "-//HelpStud//FR"
VERSION_ICALENDAR = "2.0"
# Pourquoi ces deux champs : la norme iCalendar (RFC 5545) les rend obligatoires ;
# sans eux, Outlook refuse le fichier.


@dataclass(frozen=True)
class SessionIcs:
    """Une session prête à exporter : noms lisibles et heures avec fuseau."""

    id: int
    cours: str
    chapitre: str
    debut: datetime
    fin: datetime
    # Pourquoi le nom du cours et du chapitre plutôt que leurs id : l'export ne lit pas la
    # base (Python pur) ; c'est l'API qui lui donne des textes déjà prêts.


def creer_evenement(session: SessionIcs, maintenant: datetime) -> Event:
    """Un VEVENT pour une session, avec les heures converties en UTC."""
    evenement = Event()
    evenement.add("uid", f"session-{session.id}@helpstud")
    evenement.add("summary", f"{session.cours} — {session.chapitre}")
    evenement.add("dtstart", session.debut.astimezone(timezone.utc))
    evenement.add("dtend", session.fin.astimezone(timezone.utc))
    evenement.add("dtstamp", maintenant.astimezone(timezone.utc))
    return evenement
    # Pourquoi UTC : une heure en UTC (suffixe Z) est convertie sans ambiguïté par tous les
    # agendas, sans avoir à décrire les règles du fuseau Europe/Paris dans le fichier (SPEC §10).
    # Pourquoi un UID stable par session : réimporter le fichier met à jour au lieu de dupliquer.


def exporter_ics(sessions: list[SessionIcs], maintenant: datetime) -> bytes:
    """Calendrier iCalendar (RFC 5545) : un VEVENT par session, heures en UTC."""
    calendrier = Calendar()
    calendrier.add("prodid", IDENTIFIANT_PRODUIT)
    calendrier.add("version", VERSION_ICALENDAR)
    for session in sessions:
        calendrier.add_component(creer_evenement(session, maintenant))
    return calendrier.to_ical()
    # Pourquoi recevoir `maintenant` au lieu d'appeler datetime.now() : DTSTAMP (date de
    # création) devient prévisible, donc testable ; c'est l'API qui fournit l'heure réelle.
