# HelpStud — notre spécification

> Écrite **avant** de coder. Elle précise la spec officielle
> [`docs/STUDYPLAN_SPEC.md`](docs/STUDYPLAN_SPEC.md), qui fait foi en cas de conflit.
> Toute modification de ce fichier passe par le Product Owner du sprint.

## 1. Le produit en une phrase

L'étudiant importe ses cours et ses échéances ; HelpStud construit un planning de
révisions hebdomadaire, l'exporte en `.ics` et suit l'avancement dans un dashboard.
**Aucun appel à une API d'IA dans le produit** : les chapitres et la charge viennent
de règles simples (titres, nombre de mots).

## 2. Définition de « fini » (pour chaque tâche)

Une tâche est finie quand **toutes** ces cases sont cochées :

- [ ] les critères d'acceptation du bloc concerné sont vérifiés par un test qui passe ;
- [ ] `pytest` passe en entier sur la branche (pas seulement le nouveau test) ;
- [ ] le contrat d'API (section 4) n'est pas cassé ;
- [ ] chaque fonction a une docstring courte et un commentaire « pourquoi » ;
- [ ] le Navigator+Tester a relu le diff et sait l'expliquer ligne par ligne ;
- [ ] l'usage de l'IA est noté dans `AI_LOG.md` ;
- [ ] la PR est relue par un autre membre puis fusionnée dans `main`.

## 3. MVP — les 5 blocs (tous obligatoires)

### Bloc 1 — Importer ses cours
- **CA1.1** Upload d'un fichier `.md` ou `.pdf` → un cours est créé avec ses chapitres.
  Le nom du cours = le nom du fichier sans extension.
- **CA1.2** Markdown : chaque titre `#` ou `##` devient un chapitre, dans l'ordre du
  fichier. Un fichier sans titre donne un seul chapitre, nommé comme le cours.
- **CA1.3** PDF : le texte est extrait avec `pypdf`. Chaque ligne du type
  « Chapitre N … » ou « 1. Titre » commence un chapitre ; s'il n'y en a aucune,
  on crée **un chapitre par page**.
- **CA1.4** Chaque chapitre a une charge estimée en heures (règle de charge, §5.1).
- **CA1.5** La réponse contient `hours_total` = somme des charges des chapitres.
- **CA1.6** Un autre format de fichier est refusé avec `415` ; un fichier vide avec `422`.
- **CA1.7** *(ajout HelpStud)* **Avant** d'envoyer le fichier, l'étudiant choisit :
  - la **priorité** du cours : haute, moyenne ou basse (par défaut moyenne) ;
  - la **catégorie** du cours : examen, contrôle continu ou mixte (§5.4).

  Les deux sont enregistrées avec le cours et modifiables ensuite.

### Bloc 2 — Échéances et disponibilités
- **CA2.1** Créer (`201`), lister (triées par date), supprimer (`204`) une échéance.
- **CA2.2** Une échéance = cours, titre, type (`exam` ou `assignment`), date, poids 0–100.
- **CA2.3** Une date passée est refusée avec `422` (la date du jour est acceptée).
- **CA2.4** Disponibilités hebdomadaires : créneaux par jour de la semaine
  (`monday` … `sunday`) au format `"HH:MM-HH:MM"`, plus `session_minutes`.
- **CA2.5** *(ajout HelpStud)* L'étudiant fixe **lui-même** ses dates d'examen et de
  contrôle continu, en choisissant la date dans un calendrier. Le type `exam` = examen,
  le type `assignment` = contrôle continu.
- **CA2.6** *(ajout HelpStud)* Les échéances sont **optionnelles** : un cours sans
  examen ni contrôle continu daté reste utilisable et peut être planifié (§5.2).

### Bloc 3 — Planning hebdo
- **CA3.1** `POST /plan/generate` place des sessions de `session_minutes`
  **uniquement** dans les créneaux libres.
- **CA3.2** Aucune session ne chevauche une autre.
- **CA3.3** Aucune session ne finit après l'échéance du cours concerné : une session
  doit finir **avant le jour** de l'échéance (avant 00:00), car on ne connaît pas
  l'heure de l'examen.
- **CA3.4** Les cours à l'échéance la plus proche et la plus lourde passent en premier,
  pondérés par la priorité choisie par l'étudiant (§5.2).
- **CA3.5** Le planificateur est un module **Python pur** (`services/planner.py`),
  sans import FastAPI ni SQLite, couvert par des tests unitaires.
- **CA3.6** *(ajout HelpStud)* Les cours sans échéance sont planifiés **après** tous
  les cours qui en ont une, du plus prioritaire au moins prioritaire.
- **CA3.7** Relancer `generate` sur une semaine **remplace** ses sessions non faites ;
  les sessions faites restent et occupent leur créneau.
- **CA3.8** Pour la semaine en cours, les créneaux déjà passés sont ignorés.

### Bloc 4 — Export .ics
- **CA4.1** `GET /plan.ics` renvoie le type `text/calendar`, avec **toutes** les
  sessions (extension : paramètre optionnel `?week=2026-W47`).
- **CA4.2** Un `VEVENT` par session ; le résumé contient le nom du cours et du chapitre.
- **CA4.3** Les heures sont correctes en Europe/Paris (heure d'hiver comme d'été).
- **CA4.4** Le fichier s'importe sans erreur dans Google Agenda ou Outlook
  (vérification **manuelle**, notée dans le README).

### Bloc 5 — Front de suivi (Streamlit)
- **CA5.1** Quatre écrans : Import, Échéances, Planning, Dashboard.
- **CA5.2** Le dashboard affiche le % d'avancement par cours (§5.5), les sessions
  faites / en retard et les 3 prochaines échéances. Une session **en retard** est
  une session finie dans le passé et pas marquée faite.
- **CA5.3** On peut marquer une session comme faite (et revenir en arrière).
- **CA5.4** Le front n'appelle **que** l'API HTTP, via le seul module `frontend/api_client.py`.
- **CA5.5** *(ajout HelpStud)* L'écran Import demande la priorité et la catégorie
  **avant** l'upload ; le dashboard affiche et permet de filtrer par catégorie.

## 4. Contrat d'API

Le contrat minimum est celui de `docs/STUDYPLAN_SPEC.md` §3 (recopié dans `AGENTS.md`).
**On peut l'étendre, jamais le casser.** Les noms de routes et de champs JSON restent
donc en anglais ; tout le reste du code est en français.

Précisions que nous ajoutons (codes d'erreur) :

| Route | Succès | Erreurs prévues |
|---|---|---|
| `POST /courses` | `201` | `415` format non supporté, `422` fichier vide ou priorité / catégorie inconnue |
| `POST /deadlines` | `201` | `422` date passée / type inconnu / poids hors 0–100, `404` cours inconnu |
| `DELETE /deadlines/{id}` | `204` | `404` échéance inconnue |
| `PUT /availability` | `200` + l'objet enregistré | `422` créneau mal formé ou fin ≤ début |
| `POST /plan/generate` | `200` + liste des sessions | `422` semaine mal formée |
| `PATCH /sessions/{id}` | `200` + la session | `404` session inconnue |

Extensions HelpStud (elles **ajoutent** des champs ou des routes, sans rien retirer) :

| Ajout | Détail | Bloc |
|---|---|---|
| `POST /courses` : champs de formulaire optionnels `priority` et `category` | `priority` ∈ `high` / `medium` / `low` (défaut `medium`) ; `category` ∈ `exam` / `continuous` / `mixed` (défaut `null` = non précisée). Sans ces champs, la route marche comme avant. | MVP |
| `POST /courses` et `GET /courses` : champs de réponse `priority` et `category` | Mêmes valeurs que ci-dessus | MVP |
| `PATCH /courses/{id}` `{priority, category}` | Modifier l'un ou l'autre après l'import → `200`, `404`, `422` | MVP |
| `GET /plan.ics?week=2026-W47` | Paramètre optionnel : n'exporter qu'une semaine | MVP |
| `POST /unavailability` `{start, end, reason}` → `201` | Créneau occupé ponctuel ; replanifie la semaine concernée | Bonus 1 |
| `GET /unavailability`, `DELETE /unavailability/{id}` → `204` | Lister / supprimer les indisponibilités | Bonus 1 |

Les **valeurs** JSON restent en anglais (`high`, `exam`…) pour rester cohérentes avec le
contrat ; c'est le front qui les affiche en français (« haute », « examen »…).

## 5. Règles métier

### 5.1 Règle de charge (import)
- On compte les **mots du contenu** du chapitre (le texte sous son titre).
- `heures = mots / 200` (200 mots étudiés par heure).
- **Arrondi au 0,5 h supérieur**, puis **minimum 1 h** par chapitre.
  Pourquoi au supérieur : mieux vaut surestimer le travail que le sous-estimer.
- Exemples : 120 mots → 0,6 h → 1 h (minimum) ; 450 mots → 2,25 h → 2,5 h ;
  600 mots → 3 h.

### 5.2 Règle de priorité (planificateur)
- `score = weight × coef_priorité / jours_restants_avant_échéance`, **le plus haut d'abord**.
- `coef_priorité` : haute = **2**, moyenne = **1**, basse = **0,5** (choisi à l'import).
- `jours_restants` = nombre de jours entre la date de la session et la date de
  l'échéance, **minimum 1** (pour éviter une division par zéro).
- Si un cours a plusieurs échéances, on utilise sa **prochaine** échéance à venir.
- Exemple 1 : cours A, examen dans 10 jours, poids 60, priorité haute → 60 × 2 / 10 = **12** ;
  cours B, contrôle continu dans 4 jours, poids 30, priorité moyenne → 30 × 1 / 4 = **7,5**.
  A passe avant B : la priorité de l'étudiant peut l'emporter sur la proximité.
- Exemple 2 : priorité basse, examen demain, poids 50 → 50 × 0,5 / 1 = **25** ;
  priorité haute, examen dans 20 jours, poids 50 → 50 × 2 / 20 = **5**.
  L'examen de demain passe d'abord : l'urgence l'emporte (choix validé par l'équipe).
- **Cours sans échéance** : pas de score ; ils sont servis **après** tous les cours
  avec échéance, triés par `coef_priorité` décroissant. Ils n'ont pas de date limite.
- Algorithme simple (glouton) : on parcourt les créneaux libres dans l'ordre
  chronologique, on les découpe en sessions de `session_minutes`, et chaque session
  va au cours éligible qui a le meilleur score.
- Un cours est éligible si la session finit avant son échéance (CA3.3) et s'il lui
  reste des heures à planifier. Les chapitres sont planifiés dans l'ordre du cours.

### 5.3 Formats
- Semaine au format **ISO 8601** : `"2026-W47"` (du lundi 00:00 au dimanche 23:59).
- Toutes les heures sont en **Europe/Paris** ; les dates-heures de l'API sont en
  ISO 8601 avec décalage, ex. `2026-11-16T18:00:00+01:00`.
- Dates d'échéance au format `YYYY-MM-DD`.

### 5.4 Catégorie d'un cours (choisie par l'étudiant)
- Valeurs : examen (`exam`), contrôle continu (`continuous`), mixte (`mixed`).
- Elle est choisie **à l'import**, car l'étudiant connaît souvent le mode d'évaluation
  avant les dates (qui sont optionnelles, CA2.6).
- Elle **ne change pas** le calcul du planning : elle sert à classer et filtrer les
  cours dans le dashboard.
- Elle est indépendante du type des échéances : aucun contrôle de cohérence
  (un cours « examen » peut avoir une échéance `assignment`), pour rester simple.

### 5.5 Avancement d'un cours
- `hours_done` = somme des durées des sessions **faites** du cours, plafonnée à `hours_total`.
- `progress` = `hours_done / hours_total × 100`, de **0 à 100**, arrondi à 1 décimale.

## 6. Hors périmètre

- Comptes utilisateurs et authentification (une seule personne utilise l'app).
- Tout LLM ou appel à une API d'IA, et toute lib LLM dans `requirements.txt`.
- Déploiement cloud : l'app tourne en local.

## 7. Bonus (seulement après les 5 blocs, validés par le PO)

1. **Calendrier qui bouge — indisponibilités ponctuelles** *(demandé par l'équipe, prioritaire)* :
   l'étudiant déclare un créneau occupé (ex. mardi 18/11, 18:00–20:00). Les sessions
   **non faites** qui le touchent sont replacées en relançant le planificateur sur la
   semaine concernée : les sessions faites ne bougent pas, et l'indisponibilité est
   traitée comme un créneau déjà pris.
2. Replanification automatique des sessions ratées.
3. Quiz de révision généré par règles à partir d'un chapitre (sans IA).
4. Profil de l'étudiant (préférences, durée de session par défaut).
5. Mode sombre.

## 8. Les tests

« Technique » = teste un module isolé (fonction Python pure).
« Fonctionnel » = teste un comportement visible par l'utilisateur, à travers l'API.

| # | Fichier | Nom du test | Type | Ce qu'il prouve |
|---|---|---|---|---|
| 1 | `test_planner.py` | `test_sessions_uniquement_dans_creneaux_libres` | Technique | Chaque session est entièrement contenue dans un créneau de disponibilité (CA3.1). |
| 2 | `test_planner.py` | `test_aucune_session_ne_se_chevauche` | Technique | Deux sessions n'ont jamais d'intervalle commun (CA3.2). |
| 3 | `test_planner.py` | `test_aucune_session_apres_echeance` | Technique | Chaque session finit avant le jour de l'échéance de son cours (CA3.3). |
| 4 | `test_planner.py` | `test_cours_prioritaire_place_en_premier` | Technique | À priorité égale, le cours au meilleur score `weight / jours_restants` reçoit la première session (CA3.4). |
| 5 | `test_planner.py` | `test_sans_disponibilite_liste_vide` | Technique | Sans créneau, le planificateur renvoie `[]` sans lever d'exception. |
| 6 | `test_planner.py` | `test_creneau_trop_court_ignore` | Technique | Un créneau plus court que `session_minutes` ne reçoit aucune session. |
| 7 | `test_importer.py` | `test_titres_markdown_deviennent_chapitres` | Technique | Les titres `#` et `##` donnent les bons chapitres, dans l'ordre (CA1.2). |
| 8 | `test_importer.py` | `test_regle_de_charge` | Technique | 200 mots/h, arrondi au 0,5 h supérieur et minimum 1 h sont respectés (CA1.4, §5.1). |
| 9 | `test_ics_export.py` | `test_ics_valide_un_vevent_par_session` | Technique | Le calendrier se relit, contient 1 `VEVENT` par session, et le résumé contient cours + chapitre (CA4.2). |
| 10 | `test_ics_export.py` | `test_ics_heures_europe_paris_hiver` | Technique | Une session à 18:00 en novembre (UTC+1) est exportée à 17:00 UTC (CA4.3). |
| 11 | `test_api.py` | `test_post_echeance_date_passee_renvoie_422` | Fonctionnel | L'API refuse une échéance dans le passé (CA2.3). |
| 12 | `test_parcours.py` | `test_parcours_complet_progression` | Fonctionnel | De bout en bout : upload → échéance → disponibilités → generate → `PATCH done` → `GET /courses` montre une progression > 0 (blocs 1 à 5). |

Tests ajoutés pour les demandes de l'équipe :

| # | Fichier | Nom du test | Type | Ce qu'il prouve |
|---|---|---|---|---|
| 13 | `test_planner.py` | `test_priorite_haute_multiplie_le_score` | Technique | Avec l'exemple 1 du §5.2, le cours A (priorité haute, plus loin) passe avant le cours B (CA1.7, CA3.4). |
| 14 | `test_planner.py` | `test_cours_sans_echeance_planifie_en_dernier` | Technique | Un cours sans échéance est planifié, mais seulement après les cours qui en ont une (CA2.6, CA3.6). |
| 15 | `test_api.py` | `test_post_cours_avec_priorite_et_categorie` | Fonctionnel | La priorité et la catégorie envoyées à l'import sont renvoyées par `GET /courses` ; sans elles, les valeurs par défaut s'appliquent (CA1.7). |
| 16 | `test_api.py` | `test_indisponibilite_deplace_les_sessions` | Fonctionnel | *(bonus 1)* Après `POST /unavailability`, aucune session non faite ne touche le créneau occupé, et les sessions faites n'ont pas bougé. |

## 9. Jalons

| Jalon | Contenu | Tests visés |
|---|---|---|
| Sprint 1 | **MVP complet** : métier, API et front (blocs 1 à 5), tâches P0 de [`docs/sprint1/P0.md`](docs/sprint1/P0.md) | 1 à 15 |
| Sprint 2 | Compléments P1 de [`docs/sprint1/P1.md`](docs/sprint1/P1.md) (PDF, erreurs, dashboard, vérification .ics) | 1 à 15 + tests P1 |
| Sprint 3 | Bonus 1 (indisponibilités), README, démo, AI_LOG relu | 16 + tous |
| Gel | Plus aucune fonctionnalité : corrections seulement | tous verts |

Rôles tournants à chaque sprint : **Product Owner**, **Driver**, **Navigator+Tester**.
**Une seule personne code** (le Driver) ; les deux autres écrivent les tests, relisent et valident.
Dates des sprints et du gel : **à fixer** (seule question encore ouverte).

## 10. Risques et plan B

| Risque | Impact | Plan B |
|---|---|---|
| Les titres d'un PDF ne sont pas détectables | Bloc 1 incomplet | Un chapitre par page (CA1.3). |
| Une dépendance n'a pas de version compatible Python 3.14 | Installation bloquée | Installer Python 3.12 en parallèle et créer le venv avec. |
| L'import `.ics` est faux dans Outlook (fuseau horaire) | Bloc 4 KO | Exporter les heures en UTC (`Z`), que tous les agendas convertissent. |
| Le front attend le back | Retard Sprint 2 | Le front avance avec `fake_data.py`, le même format que l'API. |
| Planificateur trop complexe | Retard, code inexplicable | Algorithme glouton simple (§5.2) : pas d'optimisation. |
| Conflits Git | Temps perdu | Petits commits, `git pull --rebase` avant chaque push, une PR par tâche. |
| Un membre absent | Personne ne connaît sa partie | Rotation des rôles + règle « chacun explique chaque ligne ». |
| Code généré par l'IA qu'on ne sait pas expliquer | Échec à l'oral | On ne le livre pas : on le réécrit plus simplement, et on le note dans `AI_LOG.md`. |
| SQLite partagé entre tests | Tests qui s'influencent | Une base temporaire par test (fixture dans `conftest.py`). |
| Le score avec priorité devient difficile à expliquer | Échec à l'oral, bugs | Formule unique sur une ligne + exemples chiffrés du §5.2 repris dans le test 13. |
| Le bonus « indisponibilités » déborde sur les 5 blocs | Blocs obligatoires pas finis | Il n'est commencé qu'au Sprint 3, une fois les tests 1 à 15 verts. |

## 11. Journal des décisions

| # | Question | Décision | Où |
|---|---|---|---|
| Q1 | Sens de l'arrondi à 0,5 h | Au supérieur | §5.1 |
| Q2 | « Jamais après l'échéance » | Finir avant le jour de l'échéance | CA3.3 |
| Q3 | `#` = chapitre ou nom du cours ? | `#` et `##` = chapitres ; nom = nom du fichier | CA1.1, CA1.2 |
| Q4 | Chapitres d'un PDF | « Chapitre N » / « 1. Titre », sinon une page = un chapitre | CA1.3 |
| Q5 | Plusieurs échéances pour un cours | La prochaine à venir | §5.2 |
| Q6 | Cours sans échéance | Planifié en dernier, par priorité | CA3.6 |
| Q7 | Relancer `generate` | Remplace les sessions non faites | CA3.7 |
| Q8 | Créneaux déjà passés | Ignorés | CA3.8 |
| Q9 | Format non supporté | `415` | CA1.6 |
| Q10 | `progress` et `hours_done` | 0–100, sessions faites, plafonné | §5.5 |
| Q11 | Session en retard | Finie dans le passé, pas faite | CA5.2 |
| Q12 | Contenu de `plan.ics` | Toutes les sessions, `?week=` optionnel | CA4.1 |
| — | Priorité des cours | Multiplicateur ×2 / ×1 / ×0,5, choisi avant l'upload | CA1.7, §5.2 |
| — | Examen / contrôle continu | Champ choisi par l'étudiant à l'import, sans effet sur le planning | CA1.7, §5.4 |
| — | Échéances | Fixées par l'étudiant, optionnelles | CA2.5, CA2.6 |
| — | Calendrier qui bouge | Indisponibilités ponctuelles, bonus 1 | §7 |
| **Q13** | **Dates des sprints et du gel** | **Ouverte** | §9 |
