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
- **CA1.2** Markdown : chaque titre `#` ou `##` devient un chapitre (voir Q3).
- **CA1.3** PDF : le texte est extrait avec `pypdf`, puis découpé en chapitres (voir Q4).
- **CA1.4** Chaque chapitre a une charge estimée en heures (règle de charge, §5.1).
- **CA1.5** La réponse contient `hours_total` = somme des charges des chapitres.
- **CA1.6** Un autre format de fichier est refusé (code d'erreur, voir Q9).
- **CA1.7** *(ajout HelpStud)* **Avant** d'envoyer le fichier, l'étudiant choisit la
  priorité du cours : `haute`, `moyenne` ou `basse` (par défaut `moyenne`). Elle est
  enregistrée avec le cours et modifiable ensuite.

### Bloc 2 — Échéances et disponibilités
- **CA2.1** Créer (`201`), lister (triées par date), supprimer (`204`) une échéance.
- **CA2.2** Une échéance = cours, titre, type (`exam` ou `assignment`), date, poids 0–100.
- **CA2.3** Une date passée est refusée avec `422`.
- **CA2.4** Disponibilités hebdomadaires : créneaux par jour de la semaine
  (`monday` … `sunday`) au format `"HH:MM-HH:MM"`, plus `session_minutes`.
- **CA2.5** *(ajout HelpStud)* L'étudiant fixe **lui-même** ses dates d'examen et de
  contrôle continu, en choisissant la date dans un calendrier. Le type `exam` = examen,
  le type `assignment` = contrôle continu.
- **CA2.6** *(ajout HelpStud)* Les échéances sont **optionnelles** : un cours sans
  examen ni contrôle continu reste utilisable et peut être planifié (§5.2).
- **CA2.7** *(ajout HelpStud)* Chaque cours est classé automatiquement d'après ses
  échéances : examen, contrôle continu, mixte, ou sans échéance (§5.4).

### Bloc 3 — Planning hebdo
- **CA3.1** `POST /plan/generate` place des sessions de `session_minutes`
  **uniquement** dans les créneaux libres.
- **CA3.2** Aucune session ne chevauche une autre.
- **CA3.3** Aucune session ne finit après l'échéance du cours concerné.
- **CA3.4** Les cours à l'échéance la plus proche et la plus lourde passent en premier,
  pondérés par la priorité choisie par l'étudiant (§5.2).
- **CA3.5** Le planificateur est un module **Python pur** (`services/planner.py`),
  sans import FastAPI ni SQLite, couvert par des tests unitaires.
- **CA3.6** *(ajout HelpStud)* Les cours sans échéance sont planifiés **après** tous
  les cours qui en ont une, du plus prioritaire au moins prioritaire.

### Bloc 4 — Export .ics
- **CA4.1** `GET /plan.ics` renvoie le type `text/calendar`.
- **CA4.2** Un `VEVENT` par session ; le résumé contient le nom du cours et du chapitre.
- **CA4.3** Les heures sont correctes en Europe/Paris (heure d'hiver comme d'été).
- **CA4.4** Le fichier s'importe sans erreur dans Google Agenda ou Outlook
  (vérification **manuelle**, notée dans le README).

### Bloc 5 — Front de suivi (Streamlit)
- **CA5.1** Quatre écrans : Import, Échéances, Planning, Dashboard.
- **CA5.2** Le dashboard affiche le % d'avancement par cours, les sessions
  faites / en retard et les 3 prochaines échéances.
- **CA5.3** On peut marquer une session comme faite.
- **CA5.4** Le front n'appelle **que** l'API HTTP, via le seul module `frontend/api_client.py`.
- **CA5.5** *(ajout HelpStud)* L'écran Import demande la priorité **avant** l'upload ;
  le dashboard affiche la priorité et la catégorie (examen / contrôle continu) de chaque cours.

## 4. Contrat d'API

Le contrat minimum est celui de `docs/STUDYPLAN_SPEC.md` §3 (recopié dans `AGENTS.md`).
**On peut l'étendre, jamais le casser.** Les noms de routes et de champs JSON restent
donc en anglais ; tout le reste du code est en français.

Précisions que nous ajoutons (codes d'erreur) :

| Route | Succès | Erreurs prévues |
|---|---|---|
| `POST /courses` | `201` | `415` format non supporté (Q9), `422` fichier vide |
| `POST /deadlines` | `201` | `422` date passée / type inconnu / poids hors 0–100, `404` cours inconnu |
| `DELETE /deadlines/{id}` | `204` | `404` échéance inconnue |
| `PUT /availability` | `200` + l'objet enregistré | `422` créneau mal formé ou fin ≤ début |
| `POST /plan/generate` | `200` + liste des sessions | `422` semaine mal formée |
| `PATCH /sessions/{id}` | `200` + la session | `404` session inconnue |

Extensions HelpStud (elles **ajoutent** des champs ou des routes, sans rien retirer) :

| Ajout | Détail | Bloc |
|---|---|---|
| `POST /courses` : champ de formulaire optionnel `priority` | `high` / `medium` / `low`, par défaut `medium`. Sans ce champ, la route marche comme avant. | MVP |
| `POST /courses` et `GET /courses` : champs de réponse `priority` et `category` | `category` ∈ `exam`, `continuous`, `mixed`, `none` (calculée, §5.4) | MVP |
| `PATCH /courses/{id}` `{priority}` | Changer la priorité après l'import → `200`, `404`, `422` | MVP |
| `POST /unavailability` `{start, end, reason}` → `201` | Créneau occupé ponctuel ; replanifie la semaine concernée | Bonus 1 |
| `GET /unavailability`, `DELETE /unavailability/{id}` → `204` | Lister / supprimer les indisponibilités | Bonus 1 |

Les **valeurs** JSON restent en anglais (`high`, `exam`…) pour rester cohérentes avec le
contrat ; c'est le front qui les affiche en français (« haute », « examen »…).

## 5. Règles métier

### 5.1 Règle de charge (import)
- On compte les **mots du contenu** du chapitre (le texte sous son titre).
- `heures = mots / 200` (200 mots étudiés par heure).
- **Arrondi à 0,5 h** (sens de l'arrondi : voir Q1), puis **minimum 1 h** par chapitre.
- Exemples (si arrondi au 0,5 h supérieur) : 120 mots → 0,6 h → 1 h (minimum) ;
  450 mots → 2,25 h → 2,5 h ; 600 mots → 3 h.

### 5.2 Règle de priorité (planificateur)
- `score = weight × coef_priorité / jours_restants_avant_échéance`, **le plus haut d'abord**.
- `coef_priorité` : haute = **2**, moyenne = **1**, basse = **0,5** (choisi à l'import).
- `jours_restants` = nombre de jours entre la date de la session et la date de
  l'échéance, **minimum 1** (pour éviter une division par zéro).
- L'échéance utilisée est la **prochaine** échéance à venir du cours (voir Q5).
- Exemple : cours A, examen dans 10 jours, poids 60, priorité haute → 60 × 2 / 10 = **12** ;
  cours B, contrôle continu dans 4 jours, poids 30, priorité moyenne → 30 × 1 / 4 = **7,5**.
  A passe avant B : la priorité de l'étudiant peut l'emporter sur la proximité.
- **Cours sans échéance** : pas de score ; ils sont servis **après** tous les cours
  avec échéance, triés par `coef_priorité` décroissant. Ils n'ont pas de date limite.
- Algorithme simple (glouton) : on parcourt les créneaux libres dans l'ordre
  chronologique, on les découpe en sessions de `session_minutes`, et chaque session
  va au cours éligible qui a le meilleur score.
- Un cours est éligible si la session finit avant son échéance et s'il lui reste
  des heures à planifier. Les chapitres sont planifiés dans l'ordre du cours.

### 5.3 Formats
- Semaine au format **ISO 8601** : `"2026-W47"` (du lundi 00:00 au dimanche 23:59).
- Toutes les heures sont en **Europe/Paris** ; les dates-heures de l'API sont en
  ISO 8601 avec décalage, ex. `2026-11-16T18:00:00+01:00`.
- Dates d'échéance au format `YYYY-MM-DD`.

### 5.4 Catégorie d'un cours (calculée, jamais saisie)
On ne la stocke pas : elle se déduit des échéances, donc elle ne peut pas être fausse.

| Échéances du cours | Catégorie |
|---|---|
| au moins un `exam`, aucun `assignment` | `exam` (examen) |
| au moins un `assignment`, aucun `exam` | `continuous` (contrôle continu) |
| les deux | `mixed` (mixte) |
| aucune | `none` (sans échéance) |

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

## 8. Les 12 tests

« Technique » = teste un module isolé (fonction Python pure).
« Fonctionnel » = teste un comportement visible par l'utilisateur, à travers l'API.

| # | Fichier | Nom du test | Type | Ce qu'il prouve |
|---|---|---|---|---|
| 1 | `test_planner.py` | `test_sessions_uniquement_dans_creneaux_libres` | Technique | Chaque session est entièrement contenue dans un créneau de disponibilité (CA3.1). |
| 2 | `test_planner.py` | `test_aucune_session_ne_se_chevauche` | Technique | Deux sessions n'ont jamais d'intervalle commun (CA3.2). |
| 3 | `test_planner.py` | `test_aucune_session_apres_echeance` | Technique | Chaque session finit avant l'échéance de son cours (CA3.3). |
| 4 | `test_planner.py` | `test_cours_prioritaire_place_en_premier` | Technique | À priorité égale, le cours au meilleur score `weight / jours_restants` reçoit la première session (CA3.4). |
| 5 | `test_planner.py` | `test_sans_disponibilite_liste_vide` | Technique | Sans créneau, le planificateur renvoie `[]` sans lever d'exception. |
| 6 | `test_planner.py` | `test_creneau_trop_court_ignore` | Technique | Un créneau plus court que `session_minutes` ne reçoit aucune session. |
| 7 | `test_importer.py` | `test_titres_markdown_deviennent_chapitres` | Technique | Les titres `#` et `##` donnent les bons chapitres, dans l'ordre (CA1.2). |
| 8 | `test_importer.py` | `test_regle_de_charge` | Technique | 200 mots/h, arrondi à 0,5 h et minimum 1 h sont respectés (CA1.4). |
| 9 | `test_ics_export.py` | `test_ics_valide_un_vevent_par_session` | Technique | Le calendrier se relit, contient 1 `VEVENT` par session, et le résumé contient cours + chapitre (CA4.2). |
| 10 | `test_ics_export.py` | `test_ics_heures_europe_paris_hiver` | Technique | Une session à 18:00 en novembre (UTC+1) est exportée à 17:00 UTC (CA4.3). |
| 11 | `test_api.py` | `test_post_echeance_date_passee_renvoie_422` | Fonctionnel | L'API refuse une échéance dans le passé (CA2.3). |
| 12 | `test_parcours.py` | `test_parcours_complet_progression` | Fonctionnel | De bout en bout : upload → échéance → disponibilités → generate → `PATCH done` → `GET /courses` montre une progression > 0 (blocs 1 à 5). |

Tests ajoutés pour les demandes de l'équipe :

| # | Fichier | Nom du test | Type | Ce qu'il prouve |
|---|---|---|---|---|
| 13 | `test_planner.py` | `test_priorite_haute_multiplie_le_score` | Technique | Avec l'exemple du §5.2, le cours A (priorité haute, plus loin) passe avant le cours B (CA1.7, CA3.4). |
| 14 | `test_planner.py` | `test_cours_sans_echeance_planifie_en_dernier` | Technique | Un cours sans échéance est planifié, mais seulement après les cours qui en ont une (CA2.6, CA3.6). |
| 15 | `test_api.py` | `test_indisponibilite_deplace_les_sessions` | Fonctionnel | *(bonus 1)* Après `POST /unavailability`, aucune session non faite ne touche le créneau occupé, et les sessions faites n'ont pas bougé. |

## 9. Jalons

| Jalon | Contenu | Tests visés |
|---|---|---|
| Sprint 1 | Back + planificateur + .ics (blocs 1 à 4 côté back), priorité et catégorie | 1 à 11, 13, 14 |
| Sprint 2 | Front + dashboard (bloc 5), branchement sur l'API | 12 |
| Sprint 3 | Bonus 1 (indisponibilités), README, démo, AI_LOG relu | 15 + tous |
| Gel | Plus aucune fonctionnalité : corrections seulement | tous verts |

Rôles tournants à chaque sprint : **Product Owner**, **Driver**, **Navigator+Tester**.

## 10. Risques et plan B

| Risque | Impact | Plan B |
|---|---|---|
| Les titres d'un PDF ne sont pas détectables (pas de `#`) | Bloc 1 incomplet | Repérer les lignes « Chapitre N » / « 1. Titre » ; sinon un chapitre par page. |
| Une dépendance n'a pas de version compatible Python 3.14 | Installation bloquée | Installer Python 3.12 en parallèle et créer le venv avec. |
| L'import `.ics` est faux dans Outlook (fuseau horaire) | Bloc 4 KO | Exporter les heures en UTC (`Z`), que tous les agendas convertissent. |
| Le front attend le back | Retard Sprint 2 | Le front avance avec `fake_data.py`, le même format que l'API. |
| Planificateur trop complexe | Retard, code inexplicable | Algorithme glouton simple (§5.2) : pas d'optimisation. |
| Conflits Git | Temps perdu | Petits commits, `git pull --rebase` avant chaque push, une PR par tâche. |
| Un membre absent | Personne ne connaît sa partie | Rotation des rôles + règle « chacun explique chaque ligne ». |
| Code généré par l'IA qu'on ne sait pas expliquer | Échec à l'oral | On ne le livre pas : on le réécrit plus simplement, et on le note dans `AI_LOG.md`. |
| SQLite partagé entre tests | Tests qui s'influencent | Une base temporaire par test (fixture dans `conftest.py`). |
| Le score avec priorité devient difficile à expliquer | Échec à l'oral, bugs | Formule unique sur une ligne + exemple chiffré du §5.2 repris dans le test 13. |
| Le bonus « indisponibilités » déborde sur les 5 blocs | Blocs obligatoires pas finis | Il n'est commencé qu'au Sprint 3, une fois les tests 1 à 14 verts. |

## 11. Questions ouvertes (à trancher avant le Sprint 1)

Voir le mode « challenge » : chaque réponse sera reportée ici puis la question supprimée.

- **Q1** Arrondi à 0,5 h : au plus proche ou au supérieur ?
- **Q2** « Jamais après l'échéance » : la session doit finir avant le jour de
  l'échéance, ou avant 23:59 ce jour-là ?
- **Q3** Markdown : le `#` est-il un chapitre ou le nom du cours ?
- **Q4** PDF : comment repérer les chapitres ?
- **Q5** Un cours a plusieurs échéances : laquelle compte pour le score ?
- **Q7** Relancer `POST /plan/generate` sur la même semaine : on remplace les sessions ?
- **Q8** Semaine en cours : on ignore les créneaux déjà passés ?
- **Q9** Fichier ni `.md` ni `.pdf` : `415` ou `422` ?
- **Q10** `progress` : de 0 à 100 ou de 0 à 1 ? Comment calculer `hours_done` ?
- **Q11** Une session « en retard » = finie dans le passé et pas faite ?
- **Q12** `GET /plan.ics` exporte toutes les sessions ou une seule semaine ?
- **Q13** Dates des sprints et du gel ?

Questions déjà tranchées par l'équipe :
- **Q6** Cours sans échéance → planifié **après** les cours avec échéance, par priorité (§5.2, CA3.6).
- Priorité du cours → multiplicateur ×2 / ×1 / ×0,5, choisi avant l'upload (CA1.7, §5.2).
- Examen / contrôle continu → l'étudiant fixe lui-même ses dates, échéances optionnelles,
  catégorie calculée (CA2.5 à CA2.7, §5.4).
- Calendrier qui bouge → indisponibilités ponctuelles, en bonus 1 (§7).
