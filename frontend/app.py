"""Page d'accueil du front HelpStud (Streamlit) : présente les 4 écrans dans l'ordre d'utilisation."""

import streamlit as st

st.set_page_config(page_title="HelpStud", page_icon="📚")
# Pourquoi en premier : Streamlit exige que la configuration de la page
# soit le tout premier appel, avant tout affichage.

st.title("📚 HelpStud")
st.write("Votre planning de révisions, construit à partir de vos cours et de vos échéances.")

st.markdown("""
Suivez les étapes dans l'ordre, avec le menu de gauche :

1. **Import** — choisissez la priorité et la catégorie, puis envoyez votre cours (`.md` ou `.pdf`).
2. **Échéances** — ajoutez vos examens et contrôles continus (optionnel), et vos disponibilités.
3. **Planning** — générez la semaine, cochez les sessions faites, exportez le `.ics`.
4. **Dashboard** — suivez votre avancement et vos prochaines échéances.
""")
# Pourquoi une page d'accueil qui guide : à la démo, le jury comprend le parcours en un
# coup d'œil ; et l'étudiant sait par où commencer.
