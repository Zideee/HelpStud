"""Écran 2 — Échéances (examens, contrôle continu) et disponibilités de la semaine (bloc 2)."""

from datetime import date

import streamlit as st

import api_client
from calculs import JOURS, TYPES_ECHEANCE, ecrire_creneaux, libelle, lire_creneaux_saisis
from ui import badge_jours_restants, badge_type, entete

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
    actuelles = api_client.lire_disponibilites() or {"session_minutes": 60, "slots": {}}
    with st.form("disponibilites"):
        st.markdown("**Mes créneaux libres, chaque semaine**")
        minutes = st.number_input("Durée d'une session (minutes)", min_value=15, step=15,
                                  value=actuelles["session_minutes"])
        colonnes = st.columns(2)
        saisies = {}
        for numero, (jour, nom) in enumerate(JOURS.items()):
            saisies[jour] = colonnes[numero % 2].text_input(
                nom, value=ecrire_creneaux(actuelles["slots"].get(jour, [])),
                placeholder="18:00-20:00, 21:00-22:00")
        if st.form_submit_button("Enregistrer", type="primary", icon=":material/save:"):
            creneaux = {jour: lire_creneaux_saisis(texte) for jour, texte in saisies.items()
                        if lire_creneaux_saisis(texte)}
            try:
                api_client.enregistrer_disponibilites(int(minutes), creneaux)
                st.toast("Disponibilités enregistrées.", icon=":material/check_circle:")
            except api_client.ErreurApi as erreur:
                st.error(erreur.message, icon=":material/error:")
    # Pourquoi pré-remplir avec lire_disponibilites : l'étudiant modifie ses créneaux au lieu
    # de tout ressaisir. Pourquoi 2 colonnes : les 7 jours tiennent sur un écran sans défiler.
