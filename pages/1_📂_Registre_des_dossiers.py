from datetime import date, timedelta

import pandas as pd
import streamlit as st

from utils.ui import PAGE_ICON, inject_base_style, section_title, kpi_row, render_sidebar_footer
from utils.dossiers import (
    get_register, set_register, next_dossier_id, with_derived_columns,
    REGISTER_COLUMNS, TYPES_DOSSIER, STATUTS, PRIORITES,
)
from utils.orgchart import all_node_ids, depth_of, direction_of, NODES
from utils.session import current_post_selector

st.set_page_config(page_title="Registre des dossiers — AER", page_icon=PAGE_ICON, layout="wide")
inject_base_style()

poste_courant = current_post_selector()

st.title("📂 Registre des dossiers")
st.caption("Registre unique et centralisé — pensé pour remplacer les tableaux Excel/Word dispersés "
           "identifiés dans le diagnostic.")

POSTE_OPTIONS = all_node_ids()
POSTE_LABELS = {p: ("— " * depth_of(p)) + p + f"  ·  {NODES[p].rang}" for p in POSTE_OPTIONS}

# =====================================================================
# Import / export
# =====================================================================
lc, rc = st.columns([1, 1])
with lc:
    uploaded = st.file_uploader("📤 Charger un registre existant (CSV)", type=["csv"], key="reg_upload")
    if uploaded is not None:
        try:
            loaded = pd.read_csv(uploaded).reindex(columns=REGISTER_COLUMNS)
            loaded["Date de réception"] = pd.to_datetime(loaded["Date de réception"], errors="coerce")
            loaded["Échéance prévue"] = pd.to_datetime(loaded["Échéance prévue"], errors="coerce")
            if st.button("Remplacer le registre courant par ce fichier"):
                set_register(loaded)
                st.success(f"{len(loaded)} dossier(s) chargé(s).")
                st.rerun()
        except Exception as exc:  # noqa: BLE001
            st.error(f"Fichier illisible : {exc}")
with rc:
    st.caption("Pour une sauvegarde complète (registre + transmissions en un seul fichier), utilisez la "
               "section dédiée sur la page d'accueil.")

st.write("")

# =====================================================================
# Ajouter un dossier
# =====================================================================
st.markdown("**➕ Nouveau dossier**")
with st.container(border=True):
    ac1, ac2, ac3 = st.columns(3)
    a_objet = ac1.text_input("Objet du dossier", key="add_objet")
    a_type = ac2.selectbox("Type de dossier", TYPES_DOSSIER, key="add_type")
    a_priorite = ac3.selectbox("Priorité", PRIORITES, key="add_priorite")

    default_poste = poste_courant if poste_courant else POSTE_OPTIONS[0]
    a_poste = st.selectbox(
        "Poste destinataire actuel (référentiel réel de l'AER)",
        POSTE_OPTIONS, index=POSTE_OPTIONS.index(default_poste),
        format_func=lambda p: POSTE_LABELS[p], key="add_poste",
        help="La direction concernée est déduite automatiquement de ce poste pour les statistiques.",
    )
    a_direction = direction_of(a_poste)
    st.caption(f"Direction concernée (déduite) : **{a_direction}**")

    cc1, cc2, cc3 = st.columns(3)
    a_date_reception = cc1.date_input("Date de réception", value=date.today(), key="add_date_reception")
    a_echeance = cc2.date_input("Échéance prévue", value=date.today() + timedelta(days=15), key="add_echeance")
    a_agent = cc3.text_input("Agent en charge", key="add_agent")

    a_statut = st.selectbox("Statut initial", STATUTS, key="add_statut")
    a_notes = st.text_area("Notes", key="add_notes", height=68)

    if st.button("Ajouter au registre", type="primary"):
        if not a_objet:
            st.warning("Renseignez au moins l'objet du dossier avant de l'ajouter.")
        else:
            reg = get_register()
            new_row = pd.DataFrame([{
                "N° dossier": next_dossier_id(reg),
                "Date de réception": pd.to_datetime(a_date_reception),
                "Objet": a_objet,
                "Type de dossier": a_type,
                "Direction concernée": a_direction,
                "Service destinataire actuel": a_poste,
                "Statut": a_statut,
                "Priorité": a_priorite,
                "Échéance prévue": pd.to_datetime(a_echeance),
                "Agent en charge": a_agent,
                "Notes": a_notes,
            }])
            set_register(pd.concat([reg, new_row], ignore_index=True))
            st.success(f"Dossier « {a_objet} » ajouté, arrivé à : {a_poste}.")
            st.rerun()

st.write("")

# =====================================================================
# Registre — filtres + édition
# =====================================================================
section_title("DOSSIERS ENREGISTRÉS")
register = get_register()

if register.empty:
    st.info("Aucun dossier enregistré pour l'instant.")
else:
    fc1, fc2, fc3, fc4 = st.columns(4)
    f_statut = fc1.multiselect("Statut", STATUTS, default=[])
    f_direction = fc2.multiselect("Direction", sorted(register["Direction concernée"].dropna().unique()), default=[])
    f_type = fc3.multiselect("Type de dossier", TYPES_DOSSIER, default=[])
    f_search = fc4.text_input("Rechercher (objet / agent)")
    f_mon_poste = st.checkbox(
        f"N'afficher que les dossiers actuellement à mon poste ({poste_courant})" if poste_courant else
        "N'afficher que les dossiers à mon poste (sélectionnez un poste dans la barre latérale)",
        value=False, disabled=(poste_courant is None), key="reg_filter_mon_poste",
    )

    view = register.copy()
    if f_mon_poste and poste_courant:
        view = view[view["Service destinataire actuel"] == poste_courant]
    if f_statut:
        view = view[view["Statut"].isin(f_statut)]
    if f_direction:
        view = view[view["Direction concernée"].isin(f_direction)]
    if f_type:
        view = view[view["Type de dossier"].isin(f_type)]
    if f_search:
        mask = (view["Objet"].astype(str).str.contains(f_search, case=False, na=False) |
                view["Agent en charge"].astype(str).str.contains(f_search, case=False, na=False))
        view = view[mask]

    kpi_row([
        ("Dossiers affichés", str(len(view)), None),
        ("Total registre", str(len(register)), None),
    ])

    edited = st.data_editor(
        view,
        use_container_width=True,
        hide_index=True,
        num_rows="dynamic",
        height=min(60 + 36 * (len(view) + 1), 480),
        column_config={
            "Date de réception": st.column_config.DateColumn("Date de réception"),
            "Échéance prévue": st.column_config.DateColumn("Échéance prévue"),
            "Statut": st.column_config.SelectboxColumn("Statut", options=STATUTS),
            "Type de dossier": st.column_config.SelectboxColumn("Type de dossier", options=TYPES_DOSSIER),
            "Priorité": st.column_config.SelectboxColumn("Priorité", options=PRIORITES),
            "Service destinataire actuel": st.column_config.SelectboxColumn(
                "Service destinataire actuel", options=POSTE_OPTIONS,
                help="Pour déplacer un dossier vers un autre poste dans le respect de l'organigramme, "
                     "utilisez plutôt la page Transmissions & traçabilité — cette édition directe ne "
                     "vérifie pas le routage hiérarchique.",
            ),
        },
        key="register_editor",
    )
    if f_statut or f_direction or f_type or f_search or (f_mon_poste and poste_courant):
        st.caption("⚠️ Un filtre est actif : les modifications ci-dessus ne portent que sur les lignes "
                   "affichées. Retirez les filtres pour éditer l'ensemble du registre en une fois.")
        others = register[~register["N° dossier"].isin(view["N° dossier"])]
        set_register(pd.concat([others, edited], ignore_index=True))
    else:
        set_register(edited)

    st.download_button("⬇️ Télécharger le registre (CSV)",
                        get_register().to_csv(index=False).encode("utf-8"),
                        f"registre_dossiers_aer_{date.today().isoformat()}.csv", "text/csv")

render_sidebar_footer()
