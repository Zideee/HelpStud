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

- [x] Bloc 1 — Import de cours (PDF / Markdown) avec priorité et catégorie
- [x] Bloc 2 — Échéances (examens, contrôle continu) et disponibilités
- [x] Bloc 3 — Planning hebdomadaire
- [x] Bloc 4 — Export `.ics`
- [ ] Bloc 5 — Front de suivi et dashboard
- [ ] Bonus 1 — Indisponibilités ponctuelles

## 3. Installation (une seule fois par ordinateur)

**Prérequis :** Python 3.11 ou plus (testé en 3.14.3) et Git.
Toutes les commandes se lancent **depuis la racine du dépôt** (le dossier `HelpStud`).

| Étape | Windows (PowerShell) | Linux / macOS |
|---|---|---|
| 1. Récupérer le projet | `git clone https://github.com/Zideee/HelpStud.git` puis `cd HelpStud` | idem |
| 2. Créer l'environnement virtuel | `python -m venv .venv` | `python3 -m venv .venv` |
| 3. L'activer | `.venv\Scripts\Activate.ps1` | `source .venv/bin/activate` |
| 4. Installer les dépendances | `pip install -r requirements.txt` | idem |
| 5. Vérifier que tout marche | `pytest` → **12 passed** | idem |

- Une fois activé, le terminal affiche `(.venv)` au début de la ligne.
- Chaque ordinateur a **son propre** `.venv` (il n'est pas dans Git) : un venv créé sous
  Windows ne marche pas sous Linux.
- Si PowerShell refuse d'activer le venv (« l'exécution de scripts est désactivée »), ne
  modifiez pas la sécurité de Windows : utilisez directement le Python du venv, par exemple
  `.venv\Scripts\python -m pytest`.

## 4. Lancer l'application web

L'application a **deux parties qui tournent en même temps**, chacune dans **son propre
terminal** :

- **le back** (l'API FastAPI, port 8000) : il calcule et enregistre tout ;
- **le front** (Streamlit, port 8501) : les écrans, dans le navigateur ; il ne fait que
  parler à l'API.

### Étape 1 — Terminal n° 1 : lancer le back

Activer le venv (voir §3), puis :

```bash
uvicorn app.main:app --reload --app-dir backend
```

C'est prêt quand le terminal affiche `Uvicorn running on http://127.0.0.1:8000`.
Pour vérifier : http://localhost:8000/health doit afficher `{"status":"ok"}`.
La documentation interactive de l'API est sur http://localhost:8000/docs.

### Étape 2 — Terminal n° 2 : lancer le front

Ouvrir un **deuxième** terminal, activer le venv, puis :

```bash
streamlit run frontend/app.py
```

Le navigateur s'ouvre tout seul sur **http://localhost:8501** (sinon, ouvrez cette adresse).
Laissez les deux terminaux ouverts pendant toute l'utilisation.

### Étape 3 — Utiliser l'application (parcours de démo)

Suivez les pages du menu de gauche, **dans l'ordre** :

1. **Import** — choisissez la priorité du cours, puis envoyez le fichier du cours
   (pour la démo : un fichier de `sample_data/`). Les chapitres et la charge en heures
   s'affichent.
2. **Echeances** — ajoutez vos dates d'examen ou de contrôle continu (optionnel, à tout
   moment), puis renseignez vos **disponibilités** de la semaine (ex. `18:00-20:00`) et
   cliquez sur « Enregistrer ».
3. **Planning** — choisissez une date de la semaine voulue, cliquez sur
   **« Générer le planning »**, cochez les sessions faites, et téléchargez le `.ics` pour
   l'importer dans Google Agenda ou Outlook.
4. **Dashboard** — l'avancement de chaque cours, les sessions faites / en retard et les
   3 prochaines échéances.

### Étape 4 — Arrêter

Dans chaque terminal : **Ctrl + C**. Vos données restent enregistrées dans le fichier
`helpstud.db` (à la racine du dépôt) et seront là au prochain lancement.

### Problèmes fréquents

| Ce que vous voyez | Cause | Solution |
|---|---|---|
| « API injoignable : lancez le back » | Le back ne tourne pas | Étape 1, dans un autre terminal |
| `ModuleNotFoundError` / `No module named …` | Le venv n'est pas activé | Activer le venv (§3, étape 3) |
| `ImportError` dans une page après une modification du code | Streamlit garde l'ancienne version en mémoire | Ctrl + C puis relancer `streamlit run frontend/app.py` |
| Les changements du back ne sont pas pris en compte | Back lancé sans `--reload` | Relancer avec la commande de l'étape 1 |
| `Address already in use` / port déjà utilisé | Une ancienne fenêtre tourne encore | Fermer l'autre terminal, ou ajouter `--port 8001` (back) / `--server.port 8502` (front) |
| Erreur de base de données après une mise à jour du code | Ancienne `helpstud.db` | Arrêter le back, supprimer `helpstud.db`, relancer (les données de test sont perdues) |
| `python` introuvable sous Linux | La commande s'appelle `python3` | Remplacer `python` par `python3` |

### Réglages avancés (facultatif)

| Variable d'environnement | Rôle | Par défaut |
|---|---|---|
| `HELPSTUD_DB` | Fichier de la base SQLite du back | `helpstud.db` |
| `HELPSTUD_API_URL` | Adresse de l'API utilisée par le front | `http://localhost:8000` |

Exemple pour lancer le front sur une autre adresse d'API :
Windows `$env:HELPSTUD_API_URL = "http://localhost:8001"` puis `streamlit run frontend/app.py` ;
Linux `HELPSTUD_API_URL=http://localhost:8001 streamlit run frontend/app.py`.

## 5. Tests

```
pytest
```

<!-- Sprint 3 : tableau des 12 tests (voir SPEC.md §8) avec leur résultat. -->

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
|     Johann, Ken-andrew, Johann |  Johann |  Seraphin      | ken-andrew| 
| | | | |
| | | | |
