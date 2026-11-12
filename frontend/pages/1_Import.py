"""Écran 1 — Importer un cours : priorité et catégorie AVANT l'envoi du fichier (CA1.7, CA5.5)."""

import streamlit as st

import api_client
from calculs import CATEGORIES, PRIORITES

st.title("📥 Importer un cours")
st.write("Choisissez d'abord la priorité et la catégorie du cours, puis envoyez son fichier.")

# 1. Priorité et catégorie, choisies AVANT le fichier (demande de l'équipe, CA1.7).
priorite = st.selectbox("Priorité du cours", list(PRIORITES), index=1)
categorie = st.selectbox("Catégorie", list(CATEGORIES), index=3,
                         help="Examen, contrôle continu ou les deux. Sert à classer vos cours.")
# Pourquoi index=1 et index=3 : « Moyenne » et « Non précisée » sont les valeurs par défaut
# de l'API ; l'écran propose donc les mêmes.

# 2. Le fichier du cours.
fichier = st.file_uploader("Fichier du cours", type=["md", "pdf"],
                           help="Markdown : un chapitre par titre # ou ##. PDF : un chapitre par page.")

# 3. L'envoi : le bouton reste grisé tant qu'aucun fichier n'est choisi.
if st.button("Importer", type="primary", disabled=fichier is None):
    try:
        cours = api_client.importer_cours(fichier.name, fichier.getvalue(),
                                          PRIORITES[priorite], CATEGORIES[categorie])
    except api_client.ErreurApi as erreur:
        st.error(erreur.message)
    else:
        st.success(f"Cours « {cours['name']} » importé : {len(cours['chapters'])} chapitres, "
                   f"{cours['hours_total']} h de travail estimées.")
        st.dataframe([{"Chapitre": chapitre["title"], "Heures": chapitre["hours"]}
                      for chapitre in cours["chapters"]], hide_index=True)
# Pourquoi try / except / else : en cas d'erreur (mauvais format, API éteinte), l'étudiant
# lit un message clair ; le résultat ne s'affiche que si l'import a réussi.
