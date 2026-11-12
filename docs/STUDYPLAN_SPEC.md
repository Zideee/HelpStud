# StudyPlan — Project specification / Spécification du projet

One subject for all teams. / Un seul sujet pour toutes les équipes.

## 1. Product / Produit
A student imports their courses and deadlines. StudyPlan builds a weekly study plan, exports it to a calendar (.ics) and tracks progress on a dashboard. **The product makes no call to any AI API**: AI (Copilot) is used to build it, not to run it.

L'étudiant importe ses cours et ses échéances. StudyPlan construit un planning de révisions hebdomadaire, l'exporte en calendrier (.ics) et suit l'avancement dans un dashboard. **Le produit n'appelle aucune API d'IA** : l'IA (Copilot) sert à le construire, pas à le faire tourner.

## 2. The 5 blocks / Les 5 blocs (all required / tous obligatoires)

| # | Block / Bloc | Acceptance criteria / Critères d'acceptation |
|---|---|---|
| 1 | Import courses / Importer ses cours | Upload a PDF or Markdown file → course created with its chapters (from headings) and an estimated workload in hours (rule of your choice, documented, e.g. words / 200 per hour, min 1 h per chapter). |
| 2 | Deadlines / Échéances | Create, list, delete deadlines (course, title, type exam/assignment, date, weight 0–100). Weekly availability slots per weekday. A date in the past is rejected (422). |
| 3 | Weekly plan / Planning hebdo | `POST /plan/generate` places sessions of `session_minutes` in free slots only, never overlapping, never after the related deadline. Courses with the closest and heaviest deadlines get priority. Pure Python module with unit tests. |
| 4 | .ics export | `GET /plan.ics` returns `text/calendar`, one VEVENT per session with course + chapter in the summary, correct Europe/Paris times. Imports without error in Google Calendar or Outlook. |
| 5 | Tracking front / Front de suivi | Screens: upload, deadlines, weekly plan, dashboard. Dashboard shows progress % per course, sessions done / late, next 3 deadlines. A session can be marked done. |

## 3. API contract (minimum) / Contrat d'API (minimum)
Extend it freely, never break it. / Étendez-le librement, ne le cassez jamais.

```
POST   /courses              multipart file -> {id, name, chapters:[{id,title,hours}], hours_total}
GET    /courses              -> [{id, name, hours_total, hours_done, progress}]
POST   /deadlines            {course_id, title, type, date, weight} -> 201
GET    /deadlines            -> list sorted by date
DELETE /deadlines/{id}       -> 204
PUT    /availability         {session_minutes, slots:{monday:["18:00-20:00"], ...}}
POST   /plan/generate        {week: "2026-W47"} -> [{id, course_id, chapter_id, start, end, done}]
GET    /plan?week=2026-W47   -> sessions of the week
PATCH  /sessions/{id}        {done: true}
GET    /plan.ics             -> text/calendar
```

## 4. Recommended stack / Stack recommandée
- Back: FastAPI, SQLite (sqlite3 or SQLModel), `pypdf` for PDF text, `icalendar` for .ics.
- Front: Streamlit (fastest) or React/Vite if the team is fluent.
- No AI or LLM library in `requirements.txt`: chapters and workload come from simple rules (Markdown headings, PDF text, word count).
- Tests: pytest. Planner and .ics first.

## 5. Shared demo data / Données de démo communes
`sample_data/`: 3 courses (Markdown), `deadlines.csv`, `availability.json`.

## 6. Ideas for your twist / Idées pour votre touche (after the 5 blocks / après les 5 blocs)
Automatic re-planning of missed sessions, Pomodoro timer, streaks and badges, re-planning when a session is missed, spaced repetition quiz generated from a chapter, mobile layout, PDF export of the week, dark mode.
