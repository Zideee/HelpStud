# Instructions Copilot — HelpStud

> Résumé de [`AGENTS.md`](../AGENTS.md), qui reste la source de vérité.
> Copilot ne suit pas les imports de fichiers : le contrat d'API est donc recopié ici.

## Projet
HelpStud (sujet « StudyPlan ») : l'étudiant importe ses cours (PDF / Markdown) et ses
échéances ; l'app génère un planning de révisions hebdomadaire, l'exporte en `.ics`
et suit l'avancement. Back FastAPI + SQLite (`sqlite3`), front Streamlit, tests pytest.
Spec détaillée : `SPEC.md`. Plan de travail : `docs/sprint1/P0.md` (tâches obligatoires,
dans l'ordre, signatures exactes) puis `docs/sprint1/P1.md` — lire la tâche avant de coder.

## Règles absolues
1. **Aucune IA dans le produit** : aucune API d'IA, aucune lib LLM dans le code ou
   dans `requirements.txt`.
2. **Le front ne touche jamais la base** : `frontend/` n'importe ni `sqlite3` ni
   `backend`. Toutes les requêtes HTTP passent par `frontend/api_client.py` uniquement.
3. **Ne jamais casser le contrat d'API** : on ajoute, on ne renomme ni ne supprime rien.
4. `backend/app/services/planner.py` et `ics_export.py` : **Python pur**, sans FastAPI ni SQLite.

## Contrat d'API minimum (intouchable)

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

Erreurs : `POST /courses` → `415` format non supporté, `422` fichier vide ;
`POST /deadlines` → `422` date passée / type inconnu / poids hors 0–100, `404` cours inconnu ;
`DELETE /deadlines/{id}`, `PATCH /sessions/{id}` → `404` si inconnu ;
`PUT /availability` → `422` créneau mal formé ; `POST /plan/generate` → `422` semaine mal formée.

## Extensions HelpStud

```
POST   /courses              + form field optionnel priority (high|medium|low, défaut medium) ;
                               réponse + priority, category (calculée depuis les échéances)
GET    /courses              + priority, category (calculée), chapters [{id, title, hours}]
PATCH  /courses/{id}         {priority} -> 200 | 404 | 422
POST / DELETE /deadlines     réponses inchangées ; replanifient les semaines déjà planifiées
GET    /plan.ics?week=...    optionnel : une seule semaine
POST   /unavailability       {start, end, reason} -> 201   (bonus)
GET    /unavailability ; DELETE /unavailability/{id} -> 204 (bonus)
```

Formats : type d'échéance `exam` | `assignment` ; dates `YYYY-MM-DD` ; dates-heures ISO 8601
avec décalage, fuseau Europe/Paris ; semaine `"2026-W47"` ; `progress` de 0 à 100.

## Règles métier clés
- Charge : `lignes non vides / 40` h, arrondi au 0,5 h supérieur, minimum 1 h par chapitre.
- Catégorie d'un cours : jamais saisie, calculée depuis ses échéances (exam / continuous / mixed / null).
- L'écran Import n'accepte que les PDF (l'API garde aussi le Markdown).
- Priorité : `score = weight × coef / jours_restants` (coef haute 2, moyenne 1, basse 0,5 ;
  `jours_restants` ≥ 1) ; cours sans échéance planifiés en dernier.
- Une session finit avant le jour de l'échéance, jamais dans un créneau occupé ou passé.

## Conventions
- Noms de fonctions, variables, docstrings et commentaires **en français** ; routes et
  champs JSON du contrat en anglais.
- Type hints partout, docstring courte, fonctions < 30 lignes, noms explicites,
  constantes nommées pour les règles métier, commentaire « pourquoi » après chaque fonction.
- Code simple, pas de one-liner obscur ni de dépendance inutile.
- Commits Conventional Commits en français ; branches `feat/…`, `fix/…` ; PR relue par un autre membre.
