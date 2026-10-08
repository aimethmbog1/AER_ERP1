"""Paramètres & thème — état du thème actif, rappel de la palette, et les
actions globales « dangereuses » de l'application (réinitialisation), qui
n'avaient jusqu'ici pas d'emplacement dédié."""
from __future__ import annotations

import streamlit as st

from utils.ui import (
    inject_base_style, render_sidebar_footer, render_page_header, section_title,
    theme_palette, is_dark_theme, categorical_colors, status_colors,
)
from utils.demo_data import reset_all_data, seed_demo_data_if_empty
from utils.dossiers import get_register
from utils.transmissions import get_log
from utils import db

inject_base_style()

render_page_header("⚙️", "Paramètres & thème",
                    "Thème actif, palette appliquée, et actions globales sur les données.")

section_title("THÈME")
c1, c2 = st.columns([1, 2])
with c1:
    st.metric("Thème détecté en ce moment", "Sombre" if is_dark_theme() else "Clair", border=True)
with c2:
    st.caption(
        "Changez de thème depuis le menu **⋮** (coin supérieur droit) → *Settings* → *Choose app "
        "theme*. Les couleurs des graphiques et des badges s'adaptent automatiquement — elles sont "
        "recalculées à chaque rendu à partir du thème actif (`utils.ui.theme_palette()`), pas figées "
        "dans une feuille de style séparée."
    )

st.write("")
section_title("PALETTE APPLIQUÉE")
p = theme_palette()
swatches = ["navy", "accent", "gold", "green", "red", "amber", "grey", "blue"]
cols = st.columns(len(swatches))
for col, key in zip(cols, swatches):
    with col:
        st.markdown(
            f"""<div style="height:46px;border-radius:8px;background:{p[key]};
            border:1px solid {p['border']};"></div>
            <div style="font-size:0.72rem;text-align:center;margin-top:0.25rem;color:{p['text_muted']};">
            {key}</div>""",
            unsafe_allow_html=True,
        )
st.caption("Couleurs catégorielles des graphiques (ordre fixe, jamais aléatoire) : "
           + " → ".join(categorical_colors()))

st.write("")
st.markdown("**Badges de statut**")
badge_cols = st.columns(len(status_colors()))
for col, (statut, couleur) in zip(badge_cols, status_colors().items()):
    with col:
        st.markdown(
            f'<span class="aer-badge" style="background:{couleur}">{statut}</span>',
            unsafe_allow_html=True,
        )

st.write("")
section_title("DONNÉES")
nb_dossiers = len(get_register())
nb_transmissions = len(get_log())
nb_audit = len(db.fetch_audit_log(limit=100000))
d1, d2, d3 = st.columns(3)
d1.metric("Dossiers", nb_dossiers, border=True)
d2.metric("Transmissions", nb_transmissions, border=True)
d3.metric("Entrées du journal d'audit", nb_audit, border=True)

with st.expander("⚠️ Actions globales (irréversibles)", expanded=False):
    rc1, rc2 = st.columns(2)
    with rc1:
        st.markdown("**Réinitialiser les données**")
        st.caption("Supprime tous les dossiers, transmissions et pièces jointes. Le journal d'audit "
                   "garde une trace de cette réinitialisation elle-même.")
        if st.button("Réinitialiser les données", key="btn_reset"):
            st.session_state["_confirm_reset"] = True
            st.rerun()
    with rc2:
        st.markdown("**Recharger le jeu de démonstration**")
        st.caption("Recharge les 300 dossiers / 620 transmissions de démonstration — uniquement si la "
                   "base est actuellement vide (par sécurité, ne remplace jamais des données réelles).")
        if st.button("Recharger la démonstration (si base vide)", key="btn_reseed"):
            result = seed_demo_data_if_empty()
            if result:
                st.toast(f"Rechargé : {result[0]} dossier(s), {result[1]} transmission(s).", icon="✅")
                st.rerun()
            else:
                st.warning("La base contient déjà des données — rien n'a été rechargé (réinitialisez "
                           "d'abord si vous voulez repartir du jeu de démonstration).")

if st.session_state.get("_confirm_reset"):
    @st.dialog("Confirmer la réinitialisation")
    def _confirm_reset():
        st.error(f"Vous êtes sur le point de supprimer **{nb_dossiers} dossier(s)** et "
                 f"**{nb_transmissions} transmission(s)**, ainsi que toutes les pièces jointes. Cette "
                 "action est **irréversible**. Téléchargez une sauvegarde JSON (page Accueil) avant de "
                 "continuer si vous n'êtes pas certain.")
        cc1, cc2 = st.columns(2)
        if cc1.button("Oui, tout supprimer", type="primary", width='stretch'):
            reset_all_data()
            st.session_state.pop("_confirm_reset", None)
            st.toast("Données réinitialisées.", icon="🗑️")
            st.rerun()
        if cc2.button("Annuler", width='stretch'):
            st.session_state.pop("_confirm_reset", None)
            st.rerun()

    _confirm_reset()

render_sidebar_footer()
