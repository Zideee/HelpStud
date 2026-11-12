"""Écran 4 — Tableau de bord : avancement par cours, sessions faites / en retard, prochaines échéances (CA5.2)."""

from datetime import date, datetime, timedelta

import streamlit as st

import api_client
from calculs import (
    CATEGORIES,
    FUSEAU,
    PRIORITES,
    TYPES_ECHEANCE,
    compter_sessions,
    jour_et_horaire,
    libelle,
    prochaine_session,
    prochaines_echeances,
    semaine_iso,
)
from ui import badge_jours_restants, badge_priorite, badge_type, entete

entete("📊", "Tableau de bord", f"Votre avancement et vos prochaines échéances — semaine {semaine_iso(date.today())}.")

try:
    cours = api_client.lister_cours()
    echeances = api_client.lister_echeances()
    sessions = api_client.lire_planning(semaine_iso(date.today()))
    sessions_suivantes = api_client.lire_planning(semaine_iso(date.today() + timedelta(days=7)))
except api_client.ErreurApi as erreur:
    st.error(erreur.message, icon=":material/error:")
    st.stop()
if not cours:
    st.info("Aucun cours : commencez par importer un PDF.", icon=":material/info:")
    st.page_link("pages/1_Import.py", label="Importer un cours", icon=":material/upload_file:")
    st.stop()
noms_des_cours = {c["id"]: c["name"] for c in cours}
titres_des_chapitres = {ch["id"]: ch["title"] for c in cours for ch in c.get("chapters", [])}
# Pourquoi charger toutes les données en haut : une seule série d'appels à l'API par
# affichage, puis la page ne fait plus que des calculs (dans calculs.py, testés).

# --- 1. Les chiffres de la semaine ----------------------------------------------------------------
faites, en_retard = compter_sessions(sessions, datetime.now(FUSEAU))
heures_faites = sum(c["hours_done"] for c in cours)
heures_totales = sum(c["hours_total"] for c in cours)
for colonne, (titre, valeur, aide) in zip(st.columns(4), [
    ("Faites", faites, "Sessions cochées cette semaine."),
    ("En retard", en_retard, "Sessions passées et pas cochées."),
    ("Prévues", len(sessions), "Sessions planifiées cette semaine."),
    ("Heures", f"{heures_faites:g} h", f"Heures révisées sur {heures_totales:g} h au total."),
]):
    colonne.metric(titre, valeur, help=aide, border=True)

# --- 2. Ce qu'il faut faire maintenant : la prochaine session ---------------------------------------
suivante = prochaine_session(sessions + sessions_suivantes, datetime.now(FUSEAU))
with st.container(border=True):
    col_texte, col_lien = st.columns([4, 1], vertical_alignment="center")
    if suivante:
        jour, horaire = jour_et_horaire(suivante["start"], suivante["end"])
        col_texte.markdown(f"**:material/play_circle: Prochaine session · {jour}, {horaire}**  \n"
                           f"{noms_des_cours.get(suivante['course_id'], '?')} — "
                           f"{titres_des_chapitres.get(suivante['chapter_id'], '?')}")
    else:
        col_texte.markdown("**Aucune session prévue.** Générez votre planning pour commencer.")
    col_lien.page_link("pages/3_Planning.py", label="Ouvrir le planning", icon=":material/calendar_month:")
if en_retard:
    st.warning(f"{en_retard} session(s) en retard : cochez-les dans le Planning si vous les avez faites.",
               icon=":material/warning:")
# Pourquoi une carte « Prochaine session » : c'est la question que se pose l'étudiant en
# ouvrant l'appli (« qu'est-ce que je révise maintenant ? »), avec un lien pour y aller.
# Pourquoi des cartes encadrées en haut : ce sont les 4 chiffres que l'étudiant regarde en premier.
# Pourquoi des titres courts + une aide (« ? ») : les titres longs étaient tronqués sur un petit écran.

avancement, a_venir = st.columns([3, 2], gap="large")

# --- 3. L’avancement de chaque cours ----------------------------------------------------------------
with avancement:
    st.subheader("Avancement par cours")
    for un_cours in cours:
        with st.container(border=True):
            st.markdown(f"**{un_cours['name']}**")
            with st.container(horizontal=True):
                badge_priorite(f"Priorité {libelle(PRIORITES, un_cours['priority']).lower()}", un_cours["priority"])
                st.badge(libelle(CATEGORIES, un_cours["category"]), color="gray", icon=":material/label:")
            st.progress(un_cours["progress"] / 100,
                        text=f"{un_cours['progress']} % — {un_cours['hours_done']} h sur {un_cours['hours_total']} h")
# Pourquoi diviser par 100 : l'API renvoie un pourcentage (0 à 100), st.progress attend 0 à 1.

# --- 4. Les 3 prochaines échéances ----------------------------------------------------------------
with a_venir:
    st.subheader("Prochaines échéances")
    prochaines = prochaines_echeances(echeances, date.today())
    if not prochaines:
        st.info("Aucune échéance à venir.", icon=":material/info:")
        st.page_link("pages/2_Echeances.py", label="Ajouter une échéance", icon=":material/add:")
    for echeance in prochaines:
        jour = date.fromisoformat(echeance["date"])
        with st.container(border=True):
            st.markdown(f"**{echeance['title']}**  \n{noms_des_cours.get(echeance['course_id'], '?')}"
                        f" · {jour:%d/%m/%Y} · poids {echeance['weight']}")
            with st.container(horizontal=True):
                badge_type(libelle(TYPES_ECHEANCE, echeance["type"]), echeance["type"])
                badge_jours_restants(jour, date.today())
# Pourquoi le badge « dans N j » coloré : l'urgence se voit avant même de lire la date.
