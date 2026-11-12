# HelpStud

> Planning de révisions pour étudiants : import des cours, échéances, planning
> hebdomadaire, export `.ics` et suivi de l'avancement. **Sans IA dans le produit.**
>
> 🚧 Squelette — ce README sera complété au **Sprint 3**.

## 1. Présentation

<!-- Sprint 3 : le problème résolu, pour qui, captures d'écran des 4 écrans. -->

Projet d'examen MSc Data Engineering (sujet « StudyPlan »).
Spec officielle : [`docs/STUDYPLAN_SPEC.md`](docs/STUDYPLAN_SPEC.md) —
notre spec détaillée : [`SPEC.md`](SPEC.md).

## 2. Fonctionnalités

<!-- Sprint 3 : cocher au fur et à mesure, avec le test qui le prouve. -->

- [ ] Bloc 1 — Import de cours (PDF / Markdown) avec priorité et catégorie
- [ ] Bloc 2 — Échéances (examens, contrôle continu) et disponibilités
- [ ] Bloc 3 — Planning hebdomadaire
- [ ] Bloc 4 — Export `.ics`
- [ ] Bloc 5 — Front de suivi et dashboard
- [ ] Bonus 1 — Indisponibilités ponctuelles

## 3. Installation

Prérequis : Python 3.11 ou plus (testé en 3.14.3), Git.
Toutes les commandes se lancent depuis la racine du dépôt.

| Étape | Windows (PowerShell) | Linux / macOS |
|---|---|---|
| Récupérer le projet | `git clone https://github.com/Zideee/HelpStud.git` | idem |
| Créer le venv | `python -m venv .venv` | `python3 -m venv .venv` |
| Activer le venv | `.venv\Scripts\Activate.ps1` | `source .venv/bin/activate` |
| Installer | `pip install -r requirements.txt` | idem |

## 4. Lancement

Dans deux terminaux, venv activé :

| Quoi | Commande | Adresse |
|---|---|---|
| API (back) | `uvicorn app.main:app --reload --app-dir backend` | http://localhost:8000 (doc : `/docs`) |
| Front | `streamlit run frontend/app.py` | http://localhost:8501 |

<!-- Sprint 3 : comment charger les données de démo de sample_data/. -->

## 5. Tests

```
pytest
```

<!-- Sprint 3 : tableau des 16 tests (voir SPEC.md §8) avec leur résultat. -->

## 6. Architecture

<!-- Sprint 3 : schéma front → api_client → API → services / SQLite. -->

- `backend/` : API FastAPI, base SQLite, services métier (`planner.py` et
  `ics_export.py` en Python pur).
- `frontend/` : Streamlit ; seul `api_client.py` parle à l'API.
- Contrat d'API : voir [`AGENTS.md`](AGENTS.md) §3.

## 7. Choix techniques et règles métier

<!-- Sprint 3 : résumer et justifier (charge 200 mots/h, score de priorité, UTC dans le .ics…). -->

Voir [`SPEC.md`](SPEC.md) §5 et le journal des décisions (§11).

## 8. Usage de l'IA

<!-- Sprint 3 : comment l'IA a aidé à construire le projet, ce qu'on a rejeté et pourquoi. -->

L'IA sert à **construire** le produit, jamais à le faire tourner.
Règles : [`AGENTS.md`](AGENTS.md) — journal : [`AI_LOG.md`](AI_LOG.md).

## 9. Limites et pistes

<!-- Sprint 3 : ce qui ne marche pas, ce qu'on ferait avec plus de temps. -->

## 10. Équipe

<!-- Rôles tournants à chaque sprint : Product Owner, Driver, Navigator+Tester. -->

| Membre | Sprint 1 | Sprint 2 | Sprint 3 |
|---|---|---|---|
| Johann | | | |
| | | | |
| | | | |
