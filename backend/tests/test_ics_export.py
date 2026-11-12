"""Tests de l'export iCalendar (services/ics_export.py)."""

from datetime import datetime, timezone

from icalendar import Calendar

from app.services.ics_export import SessionIcs, exporter_ics
from app.services.planner import FUSEAU

MAINTENANT = datetime(2026, 11, 15, 12, 0, tzinfo=FUSEAU)
SESSIONS = [
    SessionIcs(id=1, cours="SQL", chapitre="Jointures",
               debut=datetime(2026, 11, 16, 18, 0, tzinfo=FUSEAU),
               fin=datetime(2026, 11, 16, 19, 0, tzinfo=FUSEAU)),
    SessionIcs(id=2, cours="Python", chapitre="Fonctions",
               debut=datetime(2026, 11, 18, 14, 0, tzinfo=FUSEAU),
               fin=datetime(2026, 11, 18, 15, 0, tzinfo=FUSEAU)),
]


def test_ics_valide_un_vevent_par_session() -> None:
    """Test 9 : le fichier se relit, contient 1 VEVENT par session, avec cours + chapitre."""
    calendrier = Calendar.from_ical(exporter_ics(SESSIONS, MAINTENANT))
    evenements = calendrier.walk("VEVENT")
    assert len(evenements) == 2
    resumes = [str(evenement["SUMMARY"]) for evenement in evenements]
    assert "SQL" in resumes[0] and "Jointures" in resumes[0]
    assert "Python" in resumes[1] and "Fonctions" in resumes[1]
    assert len({str(evenement["UID"]) for evenement in evenements}) == 2
    # Pourquoi relire avec Calendar.from_ical : c'est la preuve que le fichier respecte le
    # format ; vérifier seulement que le texte contient « VEVENT » ne prouverait rien.
    # Pourquoi des UID différents : un agenda qui réimporte le fichier remplace l'événement
    # de même UID au lieu de créer un doublon.


def test_ics_heures_europe_paris_hiver() -> None:
    """Test 10 : 18:00 à Paris le 16/11 (UTC+1) est exporté à 17:00 UTC."""
    contenu = exporter_ics(SESSIONS[:1], MAINTENANT)
    evenement = Calendar.from_ical(contenu).walk("VEVENT")[0]
    assert evenement["DTSTART"].dt == datetime(2026, 11, 16, 17, 0, tzinfo=timezone.utc)
    assert evenement["DTEND"].dt == datetime(2026, 11, 16, 18, 0, tzinfo=timezone.utc)
    assert b"DTSTART:20261116T170000Z" in contenu
    # Pourquoi vérifier aussi le texte brut : le « Z » final prouve que l'heure est écrite
    # en UTC, le format que Google Agenda et Outlook convertissent sans se tromper.


def test_ics_sans_session_calendrier_vide_valide() -> None:
    """Aucune session → un calendrier valide, sans VEVENT (pas d'erreur)."""
    calendrier = Calendar.from_ical(exporter_ics([], MAINTENANT))
    assert calendrier.walk("VEVENT") == []
    assert str(calendrier["VERSION"]) == "2.0"
