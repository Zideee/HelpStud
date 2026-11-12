@./AGENTS.md

# Consignes propres à Gemini

- Les règles du projet sont **toutes** dans `AGENTS.md` (importé ci-dessus) : contrat
  d'API, conventions, commandes, workflow Git. Ne les recopie pas ici, modifie AGENTS.md.
- Au début de chaque session : lis `SPEC.md` et `git log --oneline -15`, dis où on en
  est et propose la prochaine petite étape.
- Après chaque fonction, ajoute un commentaire court « pourquoi » (pas « quoi »).
- Code simple > code malin : pas de one-liner obscur, pas de lib inutile.
- À la fin de chaque étape : résumé, explication de chaque fichier en 3 à 5 lignes,
  message de commit proposé (Conventional Commits, en français), 2 questions de
  vérification, puis **attendre le « ok »** de l'équipe.
