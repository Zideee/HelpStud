"""Petits éléments d'interface partagés par les pages : en-tête et badges de couleur.

Aucun appel HTTP ici (règle : seul api_client.py parle à l'API) ; uniquement de l'affichage.
"""

from datetime import date

import streamlit as st

COULEUR_PRIORITE = {"high": "red", "medium": "orange", "low": "gray"}
COULEUR_TYPE = {"exam": "violet", "assignment": "blue"}
JOURS_URGENT, JOURS_PROCHE = 3, 7
# Pourquoi des couleurs fixes par valeur : l'étudiant reconnaît une info d'un coup d'œil
# (rouge = priorité haute, violet = examen), sur toutes les pages de la même façon.


def entete(icone: str, titre: str, description: str) -> None:
    """Titre de page avec icône et une phrase qui dit à quoi sert l'écran."""
    st.title(f"{icone} {titre}")
    st.caption(description)
    # Pourquoi une phrase sous chaque titre : l'étudiant sait quoi faire sans lire de mode d'emploi.


def badge_priorite(texte: str, priorite: str) -> None:
    """Badge coloré « Priorité haute / moyenne / basse »."""
    st.badge(texte, color=COULEUR_PRIORITE.get(priorite, "gray"), icon=":material/flag:")


def badge_type(texte: str, type_echeance: str) -> None:
    """Badge coloré « Examen » ou « Contrôle continu »."""
    st.badge(texte, color=COULEUR_TYPE.get(type_echeance, "gray"), icon=":material/event:")


def badge_jours_restants(jour: date, aujourdhui: date) -> None:
    """Badge « dans N j » : rouge si urgent, orange si proche, vert sinon."""
    jours = (jour - aujourdhui).days
    couleur = "red" if jours <= JOURS_URGENT else "orange" if jours <= JOURS_PROCHE else "green"
    texte = "aujourd'hui" if jours == 0 else f"dans {jours} j"
    st.badge(texte, color=couleur, icon=":material/schedule:")
    # Pourquoi 3 couleurs : comme un feu tricolore, l'urgence se voit sans lire la date.
