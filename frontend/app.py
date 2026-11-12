"""Point d'entrée du front HelpStud (Streamlit) : configuration, navigation et page d'accueil."""

import streamlit as st

st.set_page_config(page_title="HelpStud", page_icon="📚", layout="wide")
# Pourquoi en premier : Streamlit exige que la configuration de la page soit le tout
# premier appel. Pourquoi « wide » : le planning et le dashboard ont besoin de largeur.


def accueil() -> None:
    """Page d'accueil : le parcours en 4 étapes, chacune avec un lien direct."""
    st.title("📚 HelpStud")
    st.markdown("#### Votre planning de révisions, construit à partir de vos cours et de vos échéances.")
    st.space("medium")
    etapes = [
        (PAGE_IMPORT, "1", "Importez vos cours", "Envoyez le PDF : chapitres et temps de travail sont calculés."),
        (PAGE_ECHEANCES, "2", "Ajoutez vos échéances", "Examens, contrôles continus et vos créneaux libres."),
        (PAGE_PLANNING, "3", "Générez le planning", "Les sessions se placent seules. Cochez celles faites."),
        (PAGE_DASHBOARD, "4", "Suivez vos progrès", "Avancement par cours et prochaines échéances."),
    ]
    for colonne, (page, numero, titre, texte) in zip(st.columns(4), etapes):
        with colonne.container(border=True, height="stretch"):
            st.markdown(f"### {numero}")
            st.markdown(f"**{titre}**")
            st.caption(texte)
            st.page_link(page, label="Ouvrir", icon=":material/arrow_forward:")
    # Pourquoi 4 cartes cliquables : le jury et l'étudiant voient le parcours d'un coup
    # d'œil, et chaque carte mène directement à son écran.


PAGE_IMPORT = st.Page("ecrans/1_Import.py", title="Importer un cours", icon=":material/upload_file:")
PAGE_ECHEANCES = st.Page("ecrans/2_Echeances.py", title="Échéances", icon=":material/event:")
PAGE_PLANNING = st.Page("ecrans/3_Planning.py", title="Planning", icon=":material/calendar_month:")
PAGE_DASHBOARD = st.Page("ecrans/4_Dashboard.py", title="Tableau de bord", icon=":material/insights:")
PAGE_ACCUEIL = st.Page(accueil, title="Accueil", icon=":material/home:", default=True)
# Pourquoi le dossier s'appelle « ecrans » et pas « pages » : Streamlit lit automatiquement
# un dossier « pages/ » avec son ancien menu (noms de fichiers) ; après un F5, ce menu
# remplaçait le nôtre. Avec un autre nom, seul st.navigation décide du menu.

navigation = st.navigation({
    "": [PAGE_ACCUEIL],
    "Mes révisions": [PAGE_IMPORT, PAGE_ECHEANCES, PAGE_PLANNING],
    "Suivi": [PAGE_DASHBOARD],
})
st.sidebar.caption("📚 HelpStud — planning de révisions")
navigation.run()
# Pourquoi st.navigation : un menu avec des noms clairs et des icônes, regroupé par usage,
# au lieu des noms de fichiers (« 1_Import ») affichés par défaut.
