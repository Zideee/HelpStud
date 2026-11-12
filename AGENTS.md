# AGENTS.md — règles communes à toutes les IA (et à l'équipe)

> **Source unique de vérité** pour Claude, Gemini, Copilot et les humains.
> `CLAUDE.md` et `GEMINI.md` importent ce fichier ; `.github/copilot-instructions.md` en
> est un résumé. Si une règle change, on la change **ici d'abord**.

## 1. Contexte du projet

- **HelpStud** : projet d'examen de 3 étudiants en MSc Data Engineering (sujet « StudyPlan »).
- L'étudiant importe ses cours (PDF / Markdown) et ses échéances ; l'app construit un
  planning de révisions hebdomadaire, l'exporte en `.ics` et suit l'avancement.
- Spec officielle : [`docs/STUDYPLAN_SPEC.md`](docs/STUDYPLAN_SPEC.md) (fait foi).
  Notre spec détaillée : [`SPEC.md`](SPEC.md) (règles métier, tests, décisions).
- **Plan de travail du Sprint 1** : [`docs/sprint1/P0.md`](docs/sprint1/P0.md) (16 tâches
  obligatoires, dans l'ordre, avec signatures exactes) puis
  [`docs/sprint1/P1.md`](docs/sprint1/P1.md). **Avant de coder, une IA lit la tâche
  concernée** et en respecte les signatures ; elle ne code pas la tâche suivante en avance.
- Objectif double : une app **qui marche** et une équipe qui sait **expliquer chaque ligne**.

## 2. Règles absolues (ne jamais enfreindre)

1. **Aucune IA dans le produit** : aucun appel à une API d'IA, aucune lib LLM
   (`openai`, `anthropic`, `langchain`, `transformers`, `google-generativeai`, `ollama`…)
   dans le code ni dans `requirements.txt`. Chapitres et charge = règles simples.
2. **Le front ne touche jamais la base** : `frontend/` n'importe ni `sqlite3`, ni
   `backend`, ni aucune logique métier. Toutes les requêtes HTTP passent par
   **`frontend/api_client.py`, et seulement lui**.
3. **Ne jamais casser le contrat d'API** (§3) : on peut ajouter des routes ou des champs
   optionnels ; on ne renomme, ne supprime, ni ne rend obligatoire rien d'existant.
4. **`planner.py` et `ics_export.py` sont en Python pur** : aucun import de FastAPI,
   de `sqlite3` ou de `app.db`. Ils reçoivent des données, ils renvoient des données.
5. **Pas de code qu'on ne sait pas expliquer** : sinon on le réécrit plus simplement.

## 3. Contrat d'API complet

### 3.1 Contrat minimum (copié de la spec officielle — intouchable)

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

### 3.2 Codes de réponse et d'erreur

| Route | Succès | Erreurs |
|---|---|---|
| `POST /courses` | `201` | `415` format non supporté, `422` fichier vide ou priorité / catégorie inconnue |
| `POST /deadlines` | `201` | `422` date passée, type inconnu, poids hors 0–100 ; `404` cours inconnu |
| `DELETE /deadlines/{id}` | `204` | `404` |
| `PUT /availability` | `200` + l'objet enregistré | `422` créneau mal formé ou fin ≤ début |
| `POST /plan/generate` | `200` + sessions | `422` semaine mal formée |
| `PATCH /sessions/{id}` | `200` + la session | `404` |

### 3.3 Extensions HelpStud (ajouts, rien n'est retiré)

```
POST   /courses              + champ de formulaire optionnel :
                               priority = high | medium | low   (défaut medium)
                             + réponse : priority, category (CALCULÉE, voir ci-dessous)
GET    /courses              + champs de réponse : priority, category, chapters [{id, title, hours}]
PATCH  /courses/{id}         {priority} -> 200 | 404 | 422
POST   /deadlines            réponse inchangée ; effet en plus : replanifie les semaines déjà planifiées
DELETE /deadlines/{id}       réponse inchangée ; effet en plus : replanifie les semaines déjà planifiées
GET    /plan.ics?week=...    paramètre optionnel : une seule semaine
POST   /unavailability       {start, end, reason} -> 201          (bonus 1)
GET    /unavailability       -> liste                              (bonus 1)
DELETE /unavailability/{id}  -> 204                                (bonus 1)
```

`category` n'est **jamais saisie** : elle est calculée à partir des échéances du cours
(`exam` seul → `exam`, `assignment` seul → `continuous`, les deux → `mixed`, aucune → `null`).
L'écran Import n'accepte que les PDF ; l'API accepte aussi `.md` (spec officielle, démo).

### 3.4 Formats

- `type` d'échéance : `exam` (examen) ou `assignment` (contrôle continu). `weight` : entier 0–100.
- `date` d'échéance : `YYYY-MM-DD`. Dates-heures : ISO 8601 avec décalage,
  ex. `2026-11-16T18:00:00+01:00`, fuseau **Europe/Paris**.
- Semaine : ISO 8601, `"2026-W47"`. Créneaux : `"HH:MM-HH:MM"`.
- `progress` : de 0 à 100, une décimale.
- Les **valeurs** JSON restent en anglais ; le front les traduit à l'affichage.

## 4. Arborescence

```
backend/app/main.py              app FastAPI + inclusion des routers
backend/app/db.py                connexion SQLite, création des tables
backend/app/schemas.py           modèles Pydantic = le contrat
backend/app/routers/             courses.py, deadlines.py, availability.py, plan.py
backend/app/services/importer.py   PDF/MD -> chapitres + heures
backend/app/services/planner.py    PYTHON PUR : placement des sessions
backend/app/services/ics_export.py PYTHON PUR : sessions -> .ics
backend/tests/                   conftest.py + test_*.py
frontend/app.py                  Streamlit, navigation
frontend/api_client.py           SEUL module qui fait des requêtes HTTP
frontend/fake_data.py            données factices au format exact de l'API
frontend/ecrans/                  1_Import.py, 2_Echeances.py, 3_Planning.py, 4_Dashboard.py
sample_data/                     3 cours .md, deadlines.csv, availability.json
docs/                            spec officielle
docs/sprint1/                    P0.md (tâches obligatoires), P1.md (compléments)
SPEC.md, AGENTS.md, README.md, requirements.txt
```

## 5. Conventions de code

- **Langue** : tout en français (fonctions, variables, docstrings, commentaires, commits),
  **sauf** les routes et champs JSON du contrat, et les noms de fichiers imposés
  (`planner.py`, `importer.py`…). Ex. : `def calculer_charge(nombre_mots: int) -> float:`.
- **Type hints** partout (paramètres et retour).
- **Docstring courte** (1 à 3 lignes) : ce que fait la fonction.
- **Commentaire « pourquoi »** juste après chaque fonction ou décision non évidente :
  la raison, pas la paraphrase du code.
- **Fonctions < 30 lignes**, une seule responsabilité ; au-delà, on découpe.
- **Noms explicites** : `jours_restants`, pas `jr` ; `sessions_placees`, pas `res`.
- **Code simple > code malin** : pas de one-liner obscur, pas de lib inutile, pas de magie.
- Les règles métier (200 mots/h, coefficients de priorité…) sont des **constantes
  nommées** en haut du module, jamais des nombres en dur au milieu du code.

## 6. Commandes

Toutes les commandes se lancent **depuis la racine du dépôt**, venv activé.

| Action | Windows (PowerShell) | Linux / macOS |
|---|---|---|
| Créer le venv | `python -m venv .venv` | `python3 -m venv .venv` |
| Activer le venv | `.venv\Scripts\Activate.ps1` | `source .venv/bin/activate` |
| Installer | `pip install -r requirements.txt` | `pip install -r requirements.txt` |
| Lancer le back | `uvicorn app.main:app --reload --app-dir backend` | idem |
| Lancer le front | `streamlit run frontend/app.py` | idem |
| Lancer les tests | `pytest` | `pytest` |

- API : http://localhost:8000 — documentation interactive : http://localhost:8000/docs
- Front : http://localhost:8501 — l'URL de l'API se règle avec la variable
  `HELPSTUD_API_URL` (défaut `http://localhost:8000`).

## 7. Workflow Git

- `main` = toujours stable : **jamais de commit direct**, uniquement des PR fusionnées.
- Une branche par tâche : `feat/…`, `fix/…`, `test/…`, `docs/…`, `chore/…`
  (ex. `feat/planificateur-glouton`).
- **Commits** : Conventional Commits, en français, au présent :
  `feat: ajoute le calcul de charge`, `test: couvre le créneau trop court`.
- **Petits pas** : une étape → `pytest` → un commit. Jamais de commit avec des tests rouges.
- Avant chaque push : `git pull --rebase origin main` pour rejouer ses commits
  par-dessus le travail des autres (historique linéaire, conflits traités tôt).
- **PR** : description = ce qui change + critères (CA) couverts + tests lancés.
  Relue et approuvée par **un autre membre** avant fusion.
- Interdits : `git push --force` sur `main`, commiter `.venv/`, `*.db`, `.env`, `CLAUDE.local.md`.

## 8. Rôles (rotation à chaque sprint)

| Rôle | Responsabilité |
|---|---|
| **Product Owner** | Porte `SPEC.md` et les priorités, dit non aux dérives. |
| **Driver** | Au clavier, pilote l'IA, enchaîne les étapes. |
| **Navigator + Tester** | Relit chaque diff et chaque commande, écrit les tests d'abord, chasse les cas limites. |

**Une seule personne code** : le Driver. Les deux autres ne commitent pas sur la branche
en cours (ils écrivent les tests avec le Driver, relisent et valident).

## 9. Usage de l'IA

- L'IA propose, **les tests tranchent** : plausible ≠ correct.
