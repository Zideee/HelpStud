"""Écran 2 — Échéances (examens, contrôle continu) et disponibilités de la semaine (bloc 2)."""

from datetime import date

import streamlit as st

import api_client
from calculs import JOURS, TYPES_ECHEANCE, ecrire_creneaux, libelle, lire_creneaux_saisis

st.title("📅 Échéances et disponibilités")

try:
    cours = api_client.lister_cours()
except api_client.ErreurApi as erreur:
    st.error(erreur.message)
    st.stop()
if not cours:
    st.info("Aucun cours : commencez par la page Import.")
    st.stop()
noms_des_cours = {c["id"]: c["name"] for c in cours}
# Pourquoi st.stop() : sans cours (ou sans API), le reste de la page n'a pas de sens ;
# on affiche une consigne claire au lieu de formulaires vides.

# --- 1. Ajouter une échéance -------------------------------------------------------------
st.subheader("Ajouter une échéance")
st.caption("Les échéances sont optionnelles : un cours sans échéance est planifié après les autres.")
with st.form("nouvelle_echeance", clear_on_submit=True):
    cours_id = st.selectbox("Cours", list(noms_des_cours), format_func=noms_des_cours.get)
    titre = st.text_input("Titre", placeholder="Examen final, TP noté…")
    type_choisi = st.selectbox("Type", list(TYPES_ECHEANCE))
    date_choisie = st.date_input("Date", min_value=date.today(), format="DD/MM/YYYY")
    poids = st.slider("Poids (importance)", 0, 100, 50)
    if st.form_submit_button("Ajouter", type="primary"):
        try:
            api_client.creer_echeance(cours_id, titre, TYPES_ECHEANCE[type_choisi], date_choisie, poids)
            st.success("Échéance ajoutée.")
        except api_client.ErreurApi as erreur:
            st.error(erreur.message)
# Pourquoi st.form : Streamlit relance la page à chaque clic ; le formulaire n'envoie
# qu'une seule requête, au moment du bouton « Ajouter ».
# Pourquoi min_value=today : le calendrier empêche déjà de choisir une date passée (l'API
# la refuserait aussi, avec un 422).

# --- 2. Liste des échéances --------------------------------------------------------------
st.subheader("Mes échéances")
echeances = api_client.lister_echeances()
if not echeances:
    st.write("Aucune échéance pour l'instant.")
for echeance in echeances:
    date_texte, cours_texte, titre_texte, bouton = st.columns([2, 2, 4, 1])
    date_texte.write(date.fromisoformat(echeance["date"]).strftime("%d/%m/%Y"))
    cours_texte.write(noms_des_cours.get(echeance["course_id"], "?"))
    titre_texte.write(f"{echeance['title']} — {libelle(TYPES_ECHEANCE, echeance['type'])}, "
                      f"poids {echeance['weight']}")
    if bouton.button("🗑️", key=f"supprimer-{echeance['id']}", help="Supprimer cette échéance"):
        api_client.supprimer_echeance(echeance["id"])
        st.rerun()
# Pourquoi une clé par bouton : Streamlit doit distinguer les boutons « Supprimer » ;
# st.rerun() réaffiche la liste sans l'échéance supprimée. Pourquoi une icône : le mot
# « Supprimer » était tronqué (« Su… ») dans la colonne étroite ; l'info-bulle le précise.

# --- 3. Disponibilités -------------------------------------------------------------------
st.subheader("Mes disponibilités chaque semaine")
actuelles = api_client.lire_disponibilites() or {"session_minutes": 60, "slots": {}}
with st.form("disponibilites"):
    minutes = st.number_input("Durée d'une session (minutes)", min_value=15, step=15,
                              value=actuelles["session_minutes"])
    saisies = {jour: st.text_input(nom, value=ecrire_creneaux(actuelles["slots"].get(jour, [])),
                                   placeholder="18:00-20:00, 21:00-22:00")
               for jour, nom in JOURS.items()}
    if st.form_submit_button("Enregistrer", type="primary"):
        creneaux = {jour: lire_creneaux_saisis(texte) for jour, texte in saisies.items()
                    if lire_creneaux_saisis(texte)}
        try:
            api_client.enregistrer_disponibilites(int(minutes), creneaux)
            st.success("Disponibilités enregistrées.")
        except api_client.ErreurApi as erreur:
            st.error(erreur.message)
# Pourquoi pré-remplir avec lire_disponibilites : l'étudiant modifie ses créneaux au lieu
# de tout ressaisir à chaque fois.
