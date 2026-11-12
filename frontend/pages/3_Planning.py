"""Écran 3 — Planning de la semaine : générer, cocher les sessions faites, exporter en .ics (blocs 3, 4, 5)."""

from datetime import date

import streamlit as st

import api_client
from calculs import jour_et_horaire, semaine_iso

st.title("🗓️ Planning de la semaine")

try:
    cours = api_client.lister_cours()
except api_client.ErreurApi as erreur:
    st.error(erreur.message)
    st.stop()
if not cours:
    st.info("Aucun cours : commencez par la page Import.")
    st.stop()
noms_des_cours = {c["id"]: c["name"] for c in cours}
titres_des_chapitres = {ch["id"]: ch["title"] for c in cours for ch in c.get("chapters", [])}
# Pourquoi ces deux dictionnaires : une session ne contient que des id ; on les traduit
# en noms lisibles une seule fois, avant d'afficher le tableau.

# --- 1. Choix de la semaine et génération --------------------------------------------------
jour_choisi = st.date_input("Semaine du", value=date.today(), format="DD/MM/YYYY")
semaine = semaine_iso(jour_choisi)
st.caption(f"Semaine {semaine}")
# Pourquoi choisir un jour plutôt que taper « 2026-W47 » : l'étudiant pense en dates,
# pas en numéros de semaine ; la conversion est faite par semaine_iso.

try:
    if st.button("Générer le planning", type="primary"):
        sessions = api_client.generer_planning(semaine)
        st.success(f"{len(sessions)} sessions placées.")
    else:
        sessions = api_client.lire_planning(semaine)
except api_client.ErreurApi as erreur:
    st.error(erreur.message)
    st.stop()
# Pourquoi lire le planning sans cliquer : en arrivant sur la page, on voit tout de suite
# la semaine déjà générée ; « Générer » ne sert qu'à la (re)calculer.

# --- 2. Les sessions, avec une case « Faite » ------------------------------------------------
if not sessions:
    st.info("Aucune session cette semaine : renseignez vos disponibilités, puis cliquez sur « Générer ».")
else:
    for colonne, titre in zip(st.columns([2, 2, 5, 1]), ["Jour", "Horaire", "Cours — chapitre", "Faite"]):
        colonne.caption(titre)
# Pourquoi une ligne d'en-tête : la case « Faite » n'a plus besoin de libellé sur chaque
# ligne (il était tronqué en « F… » dans la colonne étroite).
for session in sessions:
    jour, horaire = jour_et_horaire(session["start"], session["end"])
    col_jour, col_heure, col_cours, col_case = st.columns([2, 2, 5, 1])
    col_jour.write(jour)
    col_heure.write(horaire)
    col_cours.write(f"**{noms_des_cours.get(session['course_id'], '?')}** — "
                    f"{titres_des_chapitres.get(session['chapter_id'], '?')}")
    faite = col_case.checkbox("Faite", value=session["done"], key=f"faite-{session['id']}",
                              label_visibility="collapsed")
    if faite != session["done"]:
        api_client.marquer_session(session["id"], faite)
        st.rerun()
# Pourquoi comparer `faite` à session["done"] : on n'appelle l'API que si l'étudiant a
# vraiment changé la case ; st.rerun() réaffiche la page avec l'état à jour.

# --- 3. Export vers l'agenda -------------------------------------------------------------------
st.download_button("📤 Télécharger le planning (.ics)", data=api_client.telecharger_ics(),
                   file_name="helpstud.ics", mime="text/calendar",
                   help="À importer dans Google Agenda ou Outlook.")
