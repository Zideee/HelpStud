"""Écran 4 — Tableau de bord : avancement par cours, sessions faites / en retard, prochaines échéances (CA5.2)."""

from datetime import date, datetime

import streamlit as st

import api_client
from calculs import (
    CATEGORIES,
    FUSEAU,
    PRIORITES,
    TYPES_ECHEANCE,
    compter_sessions,
    libelle,
    prochaines_echeances,
    semaine_iso,
)

st.title("📊 Tableau de bord")

try:
    cours = api_client.lister_cours()
    echeances = api_client.lister_echeances()
    sessions = api_client.lire_planning(semaine_iso(date.today()))
except api_client.ErreurApi as erreur:
    st.error(erreur.message)
    st.stop()
if not cours:
    st.info("Aucun cours : commencez par la page Import.")
    st.stop()
noms_des_cours = {c["id"]: c["name"] for c in cours}
# Pourquoi charger toutes les données en haut : une seule série d'appels à l'API par
# affichage, puis la page ne fait plus que des calculs (dans calculs.py, testés).

# --- 1. Les chiffres de la semaine ------------------------------------------------------------
faites, en_retard = compter_sessions(sessions, datetime.now(FUSEAU))
st.caption(f"Cette semaine ({semaine_iso(date.today())})")
col_faites, col_retard, col_total = st.columns(3)
col_faites.metric("Faites", faites)
col_retard.metric("En retard", en_retard)
col_total.metric("Prévues", len(sessions))
# Pourquoi des libellés courts : les titres longs étaient tronqués (« Sessions faites
# cette sem… ») ; la semaine est précisée une seule fois, au-dessus.
if en_retard:
    st.warning(f"{en_retard} session(s) en retard : cochez-les dans le Planning si vous les avez faites.")

# --- 2. L'avancement de chaque cours ------------------------------------------------------------
st.subheader("Avancement par cours")
for un_cours in cours:
    st.markdown(f"**{un_cours['name']}** · priorité {libelle(PRIORITES, un_cours['priority']).lower()}"
                f" · {libelle(CATEGORIES, un_cours['category'])}")
    st.progress(un_cours["progress"] / 100,
                text=f"{un_cours['progress']} % — {un_cours['hours_done']} h sur {un_cours['hours_total']} h")
# Pourquoi diviser par 100 : l'API renvoie un pourcentage (0 à 100), st.progress attend 0 à 1.

# --- 3. Les 3 prochaines échéances ----------------------------------------------------------------
st.subheader("Prochaines échéances")
prochaines = prochaines_echeances(echeances, date.today())
if not prochaines:
    st.write("Aucune échéance à venir.")
for echeance in prochaines:
    jours_restants = (date.fromisoformat(echeance["date"]) - date.today()).days
    st.write(f"**{date.fromisoformat(echeance['date']):%d/%m/%Y}** (dans {jours_restants} j) — "
             f"{noms_des_cours.get(echeance['course_id'], '?')} : {echeance['title']} "
             f"({libelle(TYPES_ECHEANCE, echeance['type'])}, poids {echeance['weight']})")
