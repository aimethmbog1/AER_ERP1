"""Simulation de poste courant — l'application n'a pas de vrai système
d'authentification (c'est un prototype Streamlit), mais on peut simuler
« je me positionne comme tel poste » pour restreindre l'affichage aux
dossiers arrivés à ce poste et pré-remplir la source des transmissions.
C'est une commodité d'usage, pas un contrôle d'accès réel : rien n'empêche
techniquement de changer de poste à tout moment dans la barre latérale.

Affiche aussi, juste en dessous, le centre de notifications personnel du
poste sélectionné (voir `utils/notifications.py`) — inspiré de la cloche de
notifications d'Oracle Cloud ERP. Posé ici plutôt que dans chaque page :
`current_post_selector()` est déjà appelé en tête de toutes les pages, donc
la cloche apparaît partout sans dupliquer son appel."""
from __future__ import annotations

import streamlit as st

from . import orgchart as og
from . import notifications as notif
from .dossiers import get_register, with_derived_columns


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
        poste = None if choice == options[0] else choice
        _render_notifications_bell(poste)
    return poste


def _render_notifications_bell(poste: str | None) -> None:
    if not poste:
        return
    register = with_derived_columns(get_register())
    items = notif.worklist_for(poste, register)
    if not items:
        st.caption("🔔 Aucune notification pour ce poste pour l'instant.")
        return
    icone_gravite = {"approbation": "✅", "retard": "⚠️", "echeance": "⏳"}
    with st.expander(f"🔔 {len(items)} notification(s) pour ce poste", expanded=False):
        for i, n in enumerate(items[:12]):
            st.markdown(f"{icone_gravite.get(n.gravite, '🔔')} **{n.titre}**  \n"
                        f"<span style='font-size:0.82rem;opacity:0.85;'>{n.detail}</span>",
                        unsafe_allow_html=True)
            if n.numero_dossier and st.button("Ouvrir la fiche →", key=f"notif_open_{i}_{n.numero_dossier}"):
                st.session_state["_fiche_dossier_numero"] = n.numero_dossier
                st.switch_page("app_pages/fiche_dossier.py")
        if len(items) > 12:
            st.caption(f"… et {len(items) - 12} de plus.")
