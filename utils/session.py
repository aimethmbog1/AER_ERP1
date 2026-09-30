"""Simulation de poste courant — l'application n'a pas de vrai système
d'authentification (c'est un prototype Streamlit), mais on peut simuler
« je me positionne comme tel poste » pour restreindre l'affichage aux
dossiers arrivés à ce poste et pré-remplir la source des transmissions.
C'est une commodité d'usage, pas un contrôle d'accès réel : rien n'empêche
techniquement de changer de poste à tout moment dans la barre latérale."""
from __future__ import annotations

import streamlit as st

from . import orgchart as og


def current_post_selector() -> str | None:
    with st.sidebar:
        st.markdown("### 👤 Se positionner comme poste")
        options = ["(Vue globale — tous postes)"] + og.all_node_ids()
        choice = st.selectbox(
            "Poste courant (simulation)", options,
            index=options.index(st.session_state.get("poste_courant", options[0]))
            if st.session_state.get("poste_courant") in options else 0,
            key="poste_courant_select",
            help="Filtre l'affichage sur les dossiers actuellement à ce poste, et pré-remplit "
                 "la source lors d'une nouvelle transmission. Simulation d'usage, pas une "
                 "authentification réelle.",
        )
        st.session_state["poste_courant"] = choice
        if choice != options[0]:
            st.caption(f"Rang : {og.node_rang(choice)}")
    return None if choice == options[0] else choice
