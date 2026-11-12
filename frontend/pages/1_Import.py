"""Écran 1 — Importer un cours : priorité AVANT l'envoi du fichier (CA1.7, CA5.5)."""

import streamlit as st

import api_client
from calculs import PRIORITES

st.title("📥 Importer un cours")
st.write("Choisissez d'abord la priorité du cours, puis envoyez le PDF de votre cours.")
st.caption("Vos dates d'examen et de contrôle continu s'ajoutent plus tard, dans « Échéances », "
           "quand vous les connaissez : elles classent le cours automatiquement.")

# 1. La priorité, choisie AVANT le fichier (demande de l'équipe, CA1.7).
priorite = st.selectbox("Priorité du cours", list(PRIORITES), index=1)
# Pourquoi index=1 : « Moyenne » est la valeur par défaut de l'API ; l'écran propose la même.
# Pourquoi plus de catégorie : elle est déduite des échéances (CA2.7, décision de l'équipe).

# 2. Le fichier du cours : PDF uniquement à l'écran (C-04).
fichier = st.file_uploader("PDF de votre cours", type=["pdf"],
                           help="Un chapitre par titre « Chapitre 1 … », « Partie II … » ou « 1. … » ; "
                                "sans titre reconnu, un chapitre par page.")
# Pourquoi PDF seul : les étudiants ont leurs cours en PDF, pas en Markdown (décision de
# l'équipe, CA1.1). L'API accepte toujours le .md (spec officielle, données de démo).

# 3. L'envoi : le bouton reste grisé tant qu'aucun fichier n'est choisi.
if st.button("Importer", type="primary", disabled=fichier is None):
    try:
        cours = api_client.importer_cours(fichier.name, fichier.getvalue(), PRIORITES[priorite])
    except api_client.ErreurApi as erreur:
        st.error(erreur.message)
    else:
        st.success(f"Cours « {cours['name']} » importé : {len(cours['chapters'])} chapitres, "
                   f"{cours['hours_total']} h de travail estimées.")
        st.dataframe([{"Chapitre": chapitre["title"], "Heures": chapitre["hours"]}
                      for chapitre in cours["chapters"]], hide_index=True)
# Pourquoi try / except / else : en cas d'erreur (mauvais format, API éteinte), l'étudiant
# lit un message clair ; le résultat ne s'affiche que si l'import a réussi.
