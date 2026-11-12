"""Page d'accueil du front HelpStud (Streamlit)."""

import streamlit as st

st.set_page_config(page_title="HelpStud", page_icon="📚")
# Pourquoi en premier : Streamlit exige que la configuration de la page
# soit le tout premier appel, avant tout affichage.

st.title("HelpStud")
st.write("Planning de révisions — squelette : les écrans arrivent au Sprint 2.")
# Pourquoi une page presque vide : vérifier que Streamlit se lance,
# sans écrire de logique avant d'avoir l'API et api_client.py.
