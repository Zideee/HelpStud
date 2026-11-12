"""Écran 2 — Échéances (examens, contrôle continu) et disponibilités de la semaine (bloc 2)."""

from datetime import date, datetime

import pandas as pd
import streamlit as st

import api_client
from calculs import (
    JOURS,
    SUGGESTIONS_CRENEAUX,
    TYPES_ECHEANCE,
    creneaux_vers_lignes,
    libelle,
    lignes_vers_creneaux,
)
from ui import badge_jours_restants, badge_type, entete

DUREES_SESSION = [30, 45, 60, 90, 120]
COLONNES_TABLEAU = {
    "Jour": st.column_config.SelectboxColumn("Jour", options=list(JOURS.values()), required=True),
    "Début": st.column_config.TimeColumn("Début", format="HH:mm", step=900, required=True),
    "Fin": st.column_config.TimeColumn("Fin", format="HH:mm", step=900, required=True),
}
# Pourquoi des colonnes typées : le jour se choisit dans une liste, l'heure dans un sélecteur
# (pas de 15 min) ; l'étudiant ne tape plus « 18:00-20:00, … » à la main.

entete("📅", "Échéances et disponibilités",
       "Ajoutez vos examens et contrôles continus, puis vos créneaux libres de la semaine.")

try:
    cours = api_client.lister_cours()
except api_client.ErreurApi as erreur:
    st.error(erreur.message, icon=":material/error:")
    st.stop()
if not cours:
    st.info("Aucun cours : commencez par la page « Importer un cours ».", icon=":material/info:")
    st.stop()
noms_des_cours = {c["id"]: c["name"] for c in cours}
# Pourquoi st.stop() : sans cours (ou sans API), le reste de la page n'a pas de sens ;
# on affiche une consigne claire au lieu de formulaires vides.

onglet_echeances, onglet_dispos = st.tabs([":material/event: Échéances", ":material/schedule: Disponibilités"])
# Pourquoi deux onglets : deux tâches différentes ; la page reste courte et lisible.

# --- 1. Ajouter une échéance -------------------------------------------------------------------
with onglet_echeances:
    ajout, liste = st.columns([2, 3], gap="large")
    with ajout.form("nouvelle_echeance", clear_on_submit=True):
        st.markdown("**Nouvelle échéance**")
        cours_id = st.selectbox("Cours", list(noms_des_cours), format_func=noms_des_cours.get)
        titre = st.text_input("Titre", placeholder="Examen final, TP noté…")
        type_choisi = st.segmented_control("Type", list(TYPES_ECHEANCE), default="Examen")
        date_choisie = st.date_input("Date", min_value=date.today(), format="DD/MM/YYYY")
        poids = st.slider("Importance (poids)", 0, 100, 50, help="Part de la note finale, de 0 à 100.")
        if st.form_submit_button("Ajouter", type="primary", icon=":material/add:", width="stretch"):
            if type_choisi is None:
                st.error("Choisissez un type : Examen ou Contrôle continu.", icon=":material/error:")
                st.stop()
            try:
                api_client.creer_echeance(cours_id, titre, TYPES_ECHEANCE[type_choisi], date_choisie, poids)
                st.toast("Échéance ajoutée.", icon=":material/check_circle:")
            except api_client.ErreurApi as erreur:
                st.error(erreur.message, icon=":material/error:")
    ajout.caption("Les échéances sont optionnelles : un cours sans échéance est planifié après les autres.")
    # Pourquoi st.form : Streamlit relance la page à chaque clic ; le formulaire n'envoie
    # qu'une seule requête, au moment du bouton « Ajouter ».
    # Pourquoi min_value=today : le calendrier empêche déjà une date passée (l'API la refuse aussi, 422).
    # Pourquoi vérifier type_choisi : un clic sur le bouton déjà choisi le désélectionne (None).

    # --- 2. Liste des échéances ----------------------------------------------------------------
    with liste:
        st.markdown("**Mes échéances**")
        echeances = api_client.lister_echeances()
        if not echeances:
            st.info("Aucune échéance pour l'instant.", icon=":material/info:")
        for echeance in echeances:
            jour = date.fromisoformat(echeance["date"])
            with st.container(border=True):
                col_texte, col_bouton = st.columns([6, 1], vertical_alignment="center")
                col_texte.markdown(f"**{echeance['title']}** · {noms_des_cours.get(echeance['course_id'], '?')}"
                                   f" · {jour:%d/%m/%Y} · poids {echeance['weight']}")
                with col_texte.container(horizontal=True):
                    badge_type(libelle(TYPES_ECHEANCE, echeance["type"]), echeance["type"])
                    badge_jours_restants(jour, date.today())
                if col_bouton.button("", icon=":material/delete:", key=f"supprimer-{echeance['id']}",
                                     help="Supprimer cette échéance"):
                    api_client.supprimer_echeance(echeance["id"])
                    st.rerun()
    # Pourquoi une carte par échéance : date, type et urgence sont lisibles d'un coup d'œil.
    # Pourquoi une clé par bouton : Streamlit doit distinguer les boutons « Supprimer » ;
    # st.rerun() réaffiche la liste sans l'échéance supprimée.

# --- 3. Disponibilités ---------------------------------------------------------------------------
with onglet_dispos:
    if "creneaux_enregistres" not in st.session_state:
        actuelles = api_client.lire_disponibilites() or {"session_minutes": 60, "slots": {}}
        st.session_state.creneaux_enregistres = actuelles["slots"]
        st.session_state.lignes_dispos = creneaux_vers_lignes(actuelles["slots"])
        st.session_state.minutes_session = actuelles["session_minutes"]
        st.session_state.version_tableau = 0
    # Pourquoi st.session_state : Streamlit relance la page à chaque clic ; le tableau en
    # cours de modification doit survivre à ces relances. On ne lit l'API qu'une fois.

    # 1. Durée d'une session : un clic, pas de saisie.
    st.markdown("**Durée d'une session de révision**")
    durees = sorted(set(DUREES_SESSION + [st.session_state.minutes_session]))
    minutes = st.segmented_control("Durée d'une session", durees, default=st.session_state.minutes_session,
                                   format_func=lambda valeur: f"{valeur} min", label_visibility="collapsed")

    # 2. Suggestions : un clic ajoute des lignes au tableau, modifiables ensuite.
    st.markdown("**Mes créneaux libres, chaque semaine**")
    st.caption("Cliquez sur une suggestion pour remplir le tableau, puis ajustez les heures si besoin. "
               "Le « + » en bas du tableau ajoute une ligne ; cochez une ligne pour la supprimer.")
    zone_suggestions = st.container(horizontal=True)

    # 3. Le tableau des créneaux : une ligne = un jour, une heure de début, une heure de fin.
    tableau = st.data_editor(
        pd.DataFrame(st.session_state.lignes_dispos, columns=list(COLONNES_TABLEAU)),
        column_config=COLONNES_TABLEAU, num_rows="dynamic", hide_index=True, width="stretch",
        key=f"tableau_dispos_{st.session_state.version_tableau}")
    lignes = tableau.to_dict("records")
    creneaux = lignes_vers_creneaux(lignes)
    # Pourquoi une clé qui change (version) : quand une suggestion remplace les données,
    # Streamlit doit repartir d'un tableau neuf au lieu de rejouer les anciennes modifications.

    for nom, lignes_suggerees in SUGGESTIONS_CRENEAUX.items():
        if zone_suggestions.button(nom, icon=":material/add:"):
            st.session_state.lignes_dispos = lignes + lignes_suggerees
            st.session_state.version_tableau += 1
            st.rerun()
    if zone_suggestions.button("Tout effacer", icon=":material/delete_sweep:"):
        st.session_state.lignes_dispos = []
        st.session_state.version_tableau += 1
        st.rerun()
    # Pourquoi `lignes + lignes_suggerees` : on garde ce que l'étudiant a déjà modifié à la main.

    # 4. Résumé et enregistrement.
    heures_libres = sum((datetime.combine(date.today(), ligne["Fin"]) -
                         datetime.combine(date.today(), ligne["Début"])).total_seconds() / 3600
                        for ligne in creneaux_vers_lignes(creneaux))
    nombre_creneaux = sum(len(liste) for liste in creneaux.values())
    col_resume, col_bouton = st.columns([3, 1], vertical_alignment="center")
    col_resume.markdown(f"**{nombre_creneaux} créneau(x)** · {heures_libres:g} h libres par semaine")
    modifie = creneaux != st.session_state.creneaux_enregistres or minutes != st.session_state.minutes_session
    if modifie:
        col_resume.caption(":orange[Modifications non enregistrées]")
    if col_bouton.button("Enregistrer", type="primary", icon=":material/save:", width="stretch",
                         disabled=not modifie or minutes is None):
        try:
            api_client.enregistrer_disponibilites(minutes, creneaux)
        except api_client.ErreurApi as erreur:
            st.error(erreur.message, icon=":material/error:")
        else:
            st.session_state.creneaux_enregistres = creneaux
            st.session_state.minutes_session = minutes
            st.toast("Disponibilités enregistrées.", icon=":material/check_circle:")
            st.rerun()
    # Pourquoi « Modifications non enregistrées » et un bouton grisé sinon : l'étudiant sait
    # toujours si ce qu'il voit est sauvegardé, et ne clique pas pour rien.
