from datetime import date, timedelta

import pandas as pd
import streamlit as st

from utils.ui import PAGE_ICON, inject_base_style, section_title, kpi_row, render_sidebar_footer
from utils.dossiers import (
    get_register, set_register, next_dossier_id, with_derived_columns,
    REGISTER_COLUMNS, TYPES_DOSSIER, STATUTS, PRIORITES,
)
from utils.orgchart import all_directions, sous_directions_for, services_for, DIRECTION_GENERALE

st.set_page_config(page_title="Registre des dossiers — AER", page_icon=PAGE_ICON, layout="wide")
inject_base_style()

st.title("📂 Registre des dossiers")
st.caption("Registre unique et centralisé — pensé pour remplacer les tableaux Excel/Word dispersés "
           "identifiés dans le diagnostic.")

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
    st.caption("Aucune sauvegarde automatique côté serveur : téléchargez votre registre avant de fermer "
               "la session, et rechargez-le à la reprise.")

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

    bc1, bc2, bc3 = st.columns(3)
    a_direction = bc1.selectbox("Direction concernée", all_directions(), key="add_direction")
    if a_direction == DIRECTION_GENERALE:
        a_service = bc2.selectbox("Service destinataire", services_for(a_direction), key="add_service")
    else:
        a_sous_dir = bc2.selectbox("Sous-direction", sous_directions_for(a_direction), key="add_sousdir")
        a_service = bc3.selectbox("Service destinataire", services_for(a_direction, a_sous_dir), key="add_service")

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
                "Service destinataire actuel": a_service,
                "Statut": a_statut,
                "Priorité": a_priorite,
                "Échéance prévue": pd.to_datetime(a_echeance),
                "Agent en charge": a_agent,
                "Notes": a_notes,
            }])
            set_register(pd.concat([reg, new_row], ignore_index=True))
            st.success(f"Dossier « {a_objet} » ajouté.")
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

    view = register.copy()
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
        },
        key="register_editor",
    )
    # Réintègre les lignes éditées dans le registre complet (la vue peut être filtrée)
    if f_statut or f_direction or f_type or f_search:
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
