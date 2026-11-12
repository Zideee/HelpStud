"""Test 4 (métier) : export .ics valide, heures correctes en Europe/Paris (CA4.1 à CA4.3)."""

from datetime import datetime, timezone

from icalendar import Calendar

from app.services.ics_export import SessionIcs, exporter_ics
from app.services.planner import FUSEAU


def test_ics_valide_et_heures_paris() -> None:
    """1 VEVENT par session, cours + chapitre dans le résumé, 18:00 Paris (hiver) = 17:00 UTC."""
    sessions = [
        SessionIcs(id=1, cours="SQL", chapitre="Jointures",
                   debut=datetime(2026, 11, 16, 18, 0, tzinfo=FUSEAU),
                   fin=datetime(2026, 11, 16, 19, 0, tzinfo=FUSEAU)),
        SessionIcs(id=2, cours="Python", chapitre="Fonctions",
                   debut=datetime(2026, 11, 18, 14, 0, tzinfo=FUSEAU),
                   fin=datetime(2026, 11, 18, 15, 0, tzinfo=FUSEAU)),
    ]
    contenu = exporter_ics(sessions, datetime(2026, 11, 15, 12, 0, tzinfo=FUSEAU))
    evenements = Calendar.from_ical(contenu).walk("VEVENT")

    # Le fichier se relit et contient un événement par session.
    assert len(evenements) == 2
    # Le résumé contient le cours et le chapitre.
    resume = str(evenements[0]["SUMMARY"])
    assert "SQL" in resume and "Jointures" in resume
    # 18:00 à Paris en novembre (UTC+1) = 17:00 UTC, écrit avec le suffixe Z.
    assert evenements[0]["DTSTART"].dt == datetime(2026, 11, 16, 17, 0, tzinfo=timezone.utc)
    assert b"DTSTART:20261116T170000Z" in contenu
    # Pourquoi relire avec Calendar.from_ical : c'est la preuve que le format est valide ;
    # chercher « VEVENT » dans le texte ne prouverait rien.
