"""Écran 1 — Importer un cours : priorité AVANT l'envoi du PDF (CA1.1, CA1.7, CA5.5)."""

import streamlit as st

import api_client
from calculs import PRIORITES, libelle
from ui import badge_priorite, entete

entete("📥", "Importer un cours",
       "Ajoutez le PDF d'un cours : HelpStud repère les chapitres et estime le temps de travail.")

formulaire, mes_cours = st.columns([3, 2], gap="large")

# --- 1. Le formulaire d'import : priorité, puis PDF --------------------------------------------
with formulaire.container(border=True):
    st.markdown("**1. Priorité du cours**")
    priorite = st.segmented_control("Priorité du cours", list(PRIORITES), default="Moyenne",
                                    label_visibility="collapsed")
    st.markdown("**2. PDF de votre cours**")
    fichier = st.file_uploader("PDF de votre cours", type=["pdf"], label_visibility="collapsed",
                               help="Un chapitre par titre « Chapitre 1 … », « Partie II … » ou « 1. … » ; "
                                    "sans titre reconnu, un chapitre par page.")
    envoyer = st.button("Importer le cours", type="primary", icon=":material/upload:", width="stretch",
                        disabled=fichier is None or priorite is None)
    st.caption("Vos dates d'examen s'ajoutent ensuite dans « Échéances » : elles classent le cours.")
# Pourquoi des boutons de priorité (segmented_control) au lieu d'une liste déroulante :
# les 3 choix sont visibles d'un coup, un seul clic suffit.
# Pourquoi PDF seul : les étudiants ont leurs cours en PDF (décision de l'équipe, CA1.1).
# Pourquoi le bouton grisé : impossible d'envoyer sans fichier ni priorité.

if envoyer:
    try:
        cours = api_client.importer_cours(fichier.name, fichier.getvalue(), PRIORITES[priorite])
    except api_client.ErreurApi as erreur:
        formulaire.error(erreur.message, icon=":material/error:")
    else:
        with formulaire.container(border=True):
            st.success(f"Cours « {cours['name']} » importé.", icon=":material/check_circle:")
            col_chapitres, col_heures = st.columns(2)
            col_chapitres.metric("Chapitres", len(cours["chapters"]))
            col_heures.metric("Travail estimé", f"{cours['hours_total']} h")
            st.dataframe([{"Chapitre": chapitre["title"], "Heures": chapitre["hours"]}
                          for chapitre in cours["chapters"]], hide_index=True, width="stretch")
# Pourquoi try / except / else : en cas d'erreur (mauvais format, API éteinte), l'étudiant
# lit un message clair ; le résultat ne s'affiche que si l'import a réussi.

# --- 2. Les cours déjà importés ----------------------------------------------------------------
with mes_cours:
    st.subheader("Mes cours")
    try:
        liste_cours = api_client.lister_cours()
    except api_client.ErreurApi as erreur:
        st.error(erreur.message, icon=":material/error:")
        liste_cours = []
    if not liste_cours:
        st.info("Aucun cours pour l'instant : importez votre premier PDF.", icon=":material/info:")
    for un_cours in liste_cours:
        with st.container(border=True):
            st.markdown(f"**{un_cours['name']}** · {len(un_cours.get('chapters', []))} chapitres · "
                        f"{un_cours['hours_total']} h")
            badge_priorite(f"Priorité {libelle(PRIORITES, un_cours['priority']).lower()}", un_cours["priority"])
# Pourquoi montrer les cours déjà importés : l'étudiant voit tout de suite que l'import a
# marché, et évite d'importer deux fois le même cours.
