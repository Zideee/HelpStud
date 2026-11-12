"""Écran 3 — Planning en calendrier (semaine ou mois) : générer, cocher les sessions faites, exporter en .ics."""

from datetime import date, timedelta

import streamlit as st

import api_client
from calculs import JOURS_COURTS, grille_du_mois, jour_et_horaire, semaine_iso, sessions_par_date
from ui import entete

NOMS_DES_MOIS = ["janvier", "février", "mars", "avril", "mai", "juin", "juillet", "août",
                 "septembre", "octobre", "novembre", "décembre"]
SESSIONS_VISIBLES_PAR_CASE = 3
# Pourquoi limiter à 3 par case dans la vue Mois : les cases gardent la même taille ;
# « +2 » indique qu'il y en a d'autres (visibles dans la vue Semaine).

entete("🗓️", "Planning",
       "Vos sessions de révision et vos échéances dans un calendrier. Cochez les sessions faites.")

try:
    cours = api_client.lister_cours()
    echeances = api_client.lister_echeances()
except api_client.ErreurApi as erreur:
    st.error(erreur.message, icon=":material/error:")
    st.stop()
if not cours:
    st.info("Aucun cours : commencez par la page « Importer un cours ».", icon=":material/info:")
    st.stop()
noms_des_cours = {c["id"]: c["name"] for c in cours}
titres_des_chapitres = {ch["id"]: ch["title"] for c in cours for ch in c.get("chapters", [])}
echeances_par_date: dict[date, list[dict]] = {}
for echeance in echeances:
    echeances_par_date.setdefault(date.fromisoformat(echeance["date"]), []).append(echeance)
# Pourquoi ces dictionnaires : une session ne contient que des id, une échéance qu'une date ;
# on les prépare une fois pour remplir chaque case du calendrier sans recalculer.

# --- 1. Vue (semaine / mois) et navigation ------------------------------------------------------
if "jour_reference" not in st.session_state:
    st.session_state.jour_reference = date.today()


def deplacer(nouveau_jour: date) -> None:
    """Change la période affichée (boutons ◀ ▶ et « Aujourd'hui »)."""
    st.session_state.jour_reference = nouveau_jour
    # Pourquoi un « callback » (on_click) : la date change AVANT que la page se réaffiche.


vue = st.segmented_control("Vue", ["Semaine", "Mois"], default="Semaine", key="vue_planning",
                           label_visibility="collapsed") or "Semaine"
jour = st.session_state.jour_reference
if vue == "Semaine":
    lundi = jour - timedelta(days=jour.weekday())
    titre = f"Semaine du {lundi:%d/%m} au {lundi + timedelta(days=6):%d/%m/%Y}"
    precedent, suivant = jour - timedelta(days=7), jour + timedelta(days=7)
    semaines = [[lundi + timedelta(days=numero) for numero in range(7)]]
else:
    titre = f"{NOMS_DES_MOIS[jour.month - 1].capitalize()} {jour.year}"
    precedent = (jour.replace(day=1) - timedelta(days=1)).replace(day=1)
    suivant = (jour.replace(day=28) + timedelta(days=4)).replace(day=1)
    semaines = grille_du_mois(jour.year, jour.month)
# Pourquoi `replace(day=28) + 4 jours` : on tombe toujours dans le mois suivant, quel que
# soit le nombre de jours du mois (28, 30 ou 31).

col_prec, col_titre, col_suiv, col_aujourdhui = st.columns([1, 6, 1, 2], vertical_alignment="center")
col_prec.button("", icon=":material/chevron_left:", help="Période précédente", width="stretch",
                on_click=deplacer, args=(precedent,))
col_titre.markdown(f"#### {titre}")
col_suiv.button("", icon=":material/chevron_right:", help="Période suivante", width="stretch",
                on_click=deplacer, args=(suivant,))
col_aujourdhui.button("Aujourd'hui", icon=":material/today:", width="stretch",
                      on_click=deplacer, args=(date.today(),))

# --- 2. Actions : générer (vue Semaine), exporter --------------------------------------------------
col_generer, col_export = st.columns(2)
generer = col_generer.button("Générer les sessions de la semaine", type="primary", icon=":material/autorenew:",
                             width="stretch", disabled=vue != "Semaine",
                             help="Place vos sessions dans vos créneaux libres de la semaine affichée.")
col_export.download_button("Ajouter à mon agenda (.ics)", data=api_client.telecharger_ics(),
                           file_name="helpstud.ics", mime="text/calendar", icon=":material/download:",
                           width="stretch", help="À importer dans Google Agenda ou Outlook.")
# Pourquoi générer seulement en vue Semaine : l'API génère une semaine à la fois (contrat) ;
# on évite qu'un clic en vue Mois recalcule une semaine que l'étudiant ne voit pas.

try:
    if generer:
        sessions = api_client.generer_planning(semaine_iso(semaines[0][0]))
        st.toast(f"{len(sessions)} sessions placées.", icon=":material/check_circle:")
    else:
        sessions = [session for semaine in semaines for session in api_client.lire_planning(semaine_iso(semaine[0]))]
except api_client.ErreurApi as erreur:
    st.error(erreur.message, icon=":material/error:")
    st.stop()
rangees = sessions_par_date(sessions)
# Pourquoi une requête par semaine : l'API lit le planning semaine par semaine (GET /plan?week=).

if sessions:
    faites = sum(1 for session in sessions if session["done"])
    st.progress(faites / len(sessions), text=f"{faites} session(s) faite(s) sur {len(sessions)} sur la période")
elif vue == "Semaine":
    st.info("Aucune session cette semaine : renseignez vos créneaux libres, puis cliquez sur "
            "« Générer les sessions de la semaine ».", icon=":material/info:")
    st.page_link("ecrans/2_Echeances.py", label="Renseigner mes disponibilités", icon=":material/schedule:")


# --- 3. Le calendrier ------------------------------------------------------------------------------
def titre_du_jour(jour_case: date, mois_affiche: int | None) -> str:
    """En-tête d'une case : numéro du jour, en couleur si c'est aujourd'hui, grisé hors du mois."""
    texte = f"{JOURS_COURTS[jour_case.weekday()]} {jour_case.day}" if mois_affiche is None else f"{jour_case.day}"
    if jour_case == date.today():
        return f":violet-background[**{texte}**]"
    if mois_affiche is not None and jour_case.month != mois_affiche:
        return f":gray[{texte}]"
    return f"**{texte}**"
    # Pourquoi surligner aujourd'hui : on se repère tout de suite dans le calendrier.


def afficher_echeances(jour_case: date) -> None:
    """Les échéances du jour, en rouge et en petit : on les voit avant les sessions."""
    for echeance in echeances_par_date.get(jour_case, []):
        st.caption(f":red[:material/flag: **{echeance['title']}**]")


def afficher_session_detaillee(session: dict) -> None:
    """Une session en vue Semaine : horaire, cours, chapitre et interrupteur « Faite »."""
    _, horaire = jour_et_horaire(session["start"], session["end"])
    chapitre = titres_des_chapitres.get(session["chapter_id"], "?")
    with st.container(border=True):
        st.markdown(f"**{horaire[:5]}** · {noms_des_cours.get(session['course_id'], '?')}")
        st.caption(chapitre.split(" — ", 1)[-1], help=f"{horaire} — {chapitre}")
        faite = st.checkbox("Faite", value=session["done"], key=f"faite-{session['id']}")
        if faite != session["done"]:
            api_client.marquer_session(session["id"], faite)
            st.rerun()
    # Pourquoi un texte court (« 18:00 · SQL », chapitre sans « Chapitre N — ») : une colonne
    # du calendrier est étroite ; l'horaire et le titre complets sont dans l'info-bulle (?).
    # Pourquoi comparer `faite` à session["done"] : on n'appelle l'API que si l'étudiant a
    # vraiment changé la case ; st.rerun() réaffiche le calendrier à jour.


def afficher_session_resumee(session: dict) -> None:
    """Une session en vue Mois : une ligne courte « 18:00 SQL », cochée si faite."""
    _, horaire = jour_et_horaire(session["start"], session["end"])
    marque = ":green[:material/check_circle:]" if session["done"] else ":material/radio_button_unchecked:"
    st.caption(f"{marque} {horaire[:5]} {noms_des_cours.get(session['course_id'], '?')}")
    # Pourquoi st.caption (petit texte) : plusieurs lignes tiennent dans une case du mois.


if vue == "Semaine":
    for colonne, jour_case in zip(st.columns(7, gap="small"), semaines[0]):
        with colonne:
            st.markdown(titre_du_jour(jour_case, None))
            afficher_echeances(jour_case)
            for session in rangees.get(jour_case, []):
                afficher_session_detaillee(session)
else:
    for colonne, nom in zip(st.columns(7, gap="small"), JOURS_COURTS):
        colonne.caption(nom)
    for semaine in semaines:
        for colonne, jour_case in zip(st.columns(7, gap="small"), semaine):
            with colonne.container(border=True, height=150):
                st.markdown(titre_du_jour(jour_case, jour.month))
                afficher_echeances(jour_case)
                sessions_du_jour = rangees.get(jour_case, [])
                for session in sessions_du_jour[:SESSIONS_VISIBLES_PAR_CASE]:
                    afficher_session_resumee(session)
                if len(sessions_du_jour) > SESSIONS_VISIBLES_PAR_CASE:
                    st.caption(f"+{len(sessions_du_jour) - SESSIONS_VISIBLES_PAR_CASE} autre(s)")
    st.caption("Passez en vue Semaine pour cocher vos sessions.")
# Pourquoi deux vues : la semaine pour agir (cocher), le mois pour voir loin (échéances,
# charge de travail) — comme un agenda papier.
