"""Point d'entrée — remplace l'ancienne navigation automatique par dossier
`pages/` (dépréciée) par `st.navigation`/`st.Page`, organisée en sections,
comme recommandé par la compétence developing-with-streamlit pour une
application à plusieurs pages. Toute la logique métier de chaque page est
inchangée ; seule la mécanique de navigation et le point d'entrée unique
(thème, logo, configuration de page) ont changé.
"""
from __future__ import annotations

import streamlit as st

from utils.ui import APP_TITLE, PAGE_ICON, inject_base_style, render_brand_logo
from utils.demo_data import seed_demo_data_if_empty

st.set_page_config(page_title=APP_TITLE, page_icon=PAGE_ICON, layout="wide",
                    initial_sidebar_state="expanded")

# Charge les 300 dossiers / 620 transmissions de démonstration fournis au
# tout premier démarrage (base vide) — voir utils/demo_data.py. Sans effet
# si la base contient déjà des données (ne restaure jamais par-dessus un
# usage réel en cours).
seed_demo_data_if_empty()

inject_base_style()
render_brand_logo()

PAGES = {
    "Vue d'ensemble": [
        st.Page("app_pages/accueil.py", title="Accueil", icon=":material/home:", default=True),
    ],
    "Dossiers": [
        st.Page("app_pages/registre.py", title="Registre des dossiers", icon=":material/folder_managed:"),
        st.Page("app_pages/transmissions.py", title="Transmissions & traçabilité", icon=":material/sync_alt:"),
        st.Page("app_pages/recherche.py", title="Recherche & registre courrier", icon=":material/search:"),
    ],
    "Pilotage": [
        st.Page("app_pages/tableau_de_bord.py", title="Tableau de bord", icon=":material/monitoring:"),
        st.Page("app_pages/organigramme.py", title="Organigramme", icon=":material/account_tree:"),
    ],
    "Assistance": [
        st.Page("app_pages/aide_assistant.py", title="Aide & guide", icon=":material/support_agent:"),
        st.Page("app_pages/parametres_theme.py", title="Paramètres & thème", icon=":material/tune:"),
    ],
}

nav = st.navigation(PAGES)
nav.run()
