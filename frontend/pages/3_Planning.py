"""Écran 3 — Planning de la semaine : générer, cocher les sessions faites, exporter en .ics (blocs 3, 4, 5)."""

from datetime import date

import streamlit as st

import api_client
from calculs import jour_et_horaire, semaine_iso
from ui import entete

entete("🗓️", "Planning de la semaine",
       "Générez vos sessions de révision, cochez celles que vous avez faites, exportez vers votre agenda.")

try:
    cours = api_client.lister_cours()
except api_client.ErreurApi as erreur:
    st.error(erreur.message, icon=":material/error:")
    st.stop()
if not cours:
    st.info("Aucun cours : commencez par la page « Importer un cours ».", icon=":material/info:")
    st.stop()
noms_des_cours = {c["id"]: c["name"] for c in cours}
titres_des_chapitres = {ch["id"]: ch["title"] for c in cours for ch in c.get("chapters", [])}
# Pourquoi ces deux dictionnaires : une session ne contient que des id ; on les traduit
# en noms lisibles une seule fois, avant d'afficher les sessions.

# --- 1. Barre d'actions : semaine, générer, exporter -------------------------------------------
col_date, col_generer, col_export = st.columns([2, 1, 1], vertical_alignment="bottom")
jour_choisi = col_date.date_input("Semaine du", value=date.today(), format="DD/MM/YYYY")
semaine = semaine_iso(jour_choisi)
generer = col_generer.button("Générer", type="primary", icon=":material/autorenew:",
                             width="stretch")
col_export.download_button(".ics", data=api_client.telecharger_ics(), file_name="helpstud.ics",
                           mime="text/calendar", icon=":material/download:", width="stretch",
                           help="Télécharger le planning, à importer dans Google Agenda ou Outlook.")
st.caption(f"Semaine {semaine}")
# Pourquoi tout sur une ligne : les 3 actions de la page sont visibles sans défiler.
# Pourquoi des libellés courts : les longs étaient tronqués sur un petit écran ; l'icône
# et l'info-bulle complètent le sens.
# Pourquoi choisir un jour plutôt que taper « 2026-W47 » : l'étudiant pense en dates.

try:
    sessions = api_client.generer_planning(semaine) if generer else api_client.lire_planning(semaine)
except api_client.ErreurApi as erreur:
    st.error(erreur.message, icon=":material/error:")
    st.stop()
if generer:
    st.toast(f"{len(sessions)} sessions placées.", icon=":material/check_circle:")
# Pourquoi lire le planning sans cliquer : on voit tout de suite la semaine déjà générée ;
# « Générer » ne sert qu'à la (re)calculer.

# --- 2. Les sessions, groupées par jour ---------------------------------------------------------
if not sessions:
    st.info("Aucune session cette semaine : renseignez vos disponibilités, puis cliquez sur "
            "« Générer ».", icon=":material/info:")
faites = sum(1 for session in sessions if session["done"])
if sessions:
    st.progress(faites / len(sessions), text=f"{faites} session(s) faite(s) sur {len(sessions)}")

sessions_par_jour: dict[str, list[dict]] = {}
for session in sessions:
    jour, _ = jour_et_horaire(session["start"], session["end"])
    sessions_par_jour.setdefault(jour, []).append(session)
# Pourquoi regrouper par jour : l'étudiant lit sa semaine comme un agenda, jour après jour.

for jour, sessions_du_jour in sessions_par_jour.items():
    st.markdown(f"##### {jour}")
    for session in sessions_du_jour:
        _, horaire = jour_et_horaire(session["start"], session["end"])
        with st.container(border=True):
            col_heure, col_cours, col_case = st.columns([1, 5, 1], vertical_alignment="center")
            col_heure.markdown(f"**{horaire}**")
            texte = (f"**{noms_des_cours.get(session['course_id'], '?')}** — "
                     f"{titres_des_chapitres.get(session['chapter_id'], '?')}")
            col_cours.markdown(f"~~{texte}~~" if session["done"] else texte)
            faite = col_case.checkbox("Faite", value=session["done"], key=f"faite-{session['id']}")
            if faite != session["done"]:
                api_client.marquer_session(session["id"], faite)
                st.rerun()
# Pourquoi barrer une session faite : on voit d'un coup d'œil ce qui reste à faire.
# Pourquoi comparer `faite` à session["done"] : on n'appelle l'API que si l'étudiant a
# vraiment changé la case ; st.rerun() réaffiche la page avec l'état à jour.
