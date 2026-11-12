"""Écran 3 — Planning de la semaine : générer, cocher les sessions faites, exporter en .ics (blocs 3, 4, 5)."""

from datetime import date, datetime, timedelta

import streamlit as st

import api_client
from calculs import JOURS, jour_et_horaire, semaine_iso
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

# --- 1. Navigation entre les semaines -----------------------------------------------------------
LUNDI_ACTUEL = date.today() - timedelta(days=date.today().weekday())
if "lundi_planning" not in st.session_state:
    st.session_state.lundi_planning = LUNDI_ACTUEL


def changer_semaine(nouveau_lundi: date) -> None:
    """Affiche une autre semaine (appelée par les boutons ◀ ▶ et « Cette semaine »)."""
    st.session_state.lundi_planning = nouveau_lundi
    # Pourquoi un « callback » (on_click) : la semaine change AVANT que la page se
    # réaffiche, donc tout ce qui suit utilise déjà la bonne semaine.


lundi = st.session_state.lundi_planning
semaine = semaine_iso(lundi)
col_prec, col_titre, col_suiv, col_aujourdhui = st.columns([1, 6, 1, 2], vertical_alignment="center")
col_prec.button("", icon=":material/chevron_left:", help="Semaine précédente", width="stretch",
                on_click=changer_semaine, args=(lundi - timedelta(days=7),))
col_titre.markdown(f"#### Semaine du {lundi:%d/%m} au {lundi + timedelta(days=6):%d/%m}")
col_suiv.button("", icon=":material/chevron_right:", help="Semaine suivante", width="stretch",
                on_click=changer_semaine, args=(lundi + timedelta(days=7),))
col_aujourdhui.button("Cette semaine", icon=":material/today:", width="stretch",
                      disabled=lundi == LUNDI_ACTUEL, on_click=changer_semaine, args=(LUNDI_ACTUEL,))
# Pourquoi des flèches plutôt qu'un calendrier : on passe d'une semaine à l'autre en un clic,
# comme dans un agenda ; « Cette semaine » ramène à aujourd'hui.

# --- 2. Actions : générer, exporter ---------------------------------------------------------------
col_generer, col_export = st.columns(2)
generer = col_generer.button("Générer mes sessions", type="primary", icon=":material/autorenew:",
                             width="stretch", help="Place vos sessions dans vos créneaux libres de la semaine.")
col_export.download_button("Ajouter à mon agenda (.ics)", data=api_client.telecharger_ics(),
                           file_name="helpstud.ics", mime="text/calendar", icon=":material/download:",
                           width="stretch", help="À importer dans Google Agenda ou Outlook.")
# Pourquoi des libellés qui disent le résultat (« Ajouter à mon agenda ») : l'étudiant
# comprend ce que fait le bouton sans savoir ce qu'est un fichier .ics.

try:
    sessions = api_client.generer_planning(semaine) if generer else api_client.lire_planning(semaine)
except api_client.ErreurApi as erreur:
    st.error(erreur.message, icon=":material/error:")
    st.stop()
if generer:
    st.toast(f"{len(sessions)} sessions placées.", icon=":material/check_circle:")
# Pourquoi lire le planning sans cliquer : on voit tout de suite la semaine déjà générée ;
# « Générer » ne sert qu'à la (re)calculer.

# --- 3. Les sessions, groupées par jour ---------------------------------------------------------
if not sessions:
    with st.container(border=True):
        st.markdown("**Aucune session cette semaine.**")
        st.caption("1. Renseignez vos créneaux libres. 2. Revenez ici et cliquez sur « Générer mes sessions ».")
        st.page_link("pages/2_Echeances.py", label="Renseigner mes disponibilités", icon=":material/schedule:")
    st.stop()
# Pourquoi un lien direct : l'étudiant bloqué va à la bonne page en un clic.
faites = sum(1 for session in sessions if session["done"])
st.progress(faites / len(sessions), text=f"{faites} session(s) faite(s) sur {len(sessions)}")

sessions_par_jour: dict[str, list[dict]] = {}
for session in sessions:
    debut = datetime.fromisoformat(session["start"])
    jour = f"{list(JOURS.values())[debut.weekday()]} {debut:%d/%m}"
    sessions_par_jour.setdefault(jour, []).append(session)
# Pourquoi regrouper par jour, avec le nom complet (« Lundi 16/11 ») : l'étudiant lit sa
# semaine comme un agenda, jour après jour.

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
            faite = col_case.toggle("Faite", value=session["done"], key=f"faite-{session['id']}")
            if faite != session["done"]:
                api_client.marquer_session(session["id"], faite)
                st.rerun()
# Pourquoi barrer une session faite : on voit d'un coup d'œil ce qui reste à faire.
# Pourquoi comparer `faite` à session["done"] : on n'appelle l'API que si l'étudiant a
# vraiment changé la case ; st.rerun() réaffiche la page avec l'état à jour.
