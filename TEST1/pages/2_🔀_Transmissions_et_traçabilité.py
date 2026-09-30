from datetime import date

import pandas as pd
import plotly.express as px
import streamlit as st

from utils.ui import PAGE_ICON, inject_base_style, section_title, kpi_row, plotly_base_layout, NAVY, render_sidebar_footer
from utils.dossiers import get_register
from utils.transmissions import get_log, set_log, add_transmission, history_for, temps_par_service, LOG_COLUMNS
from utils.orgchart import flat_entities, DIRECTION_GENERALE

st.set_page_config(page_title="Transmissions & traçabilité — AER", page_icon=PAGE_ICON, layout="wide")
inject_base_style()

st.title("🔀 Transmissions & traçabilité")
st.caption("Le journal des mouvements d'un dossier entre services — la traçabilité que le diagnostic "
           "identifie comme manquante dans le fonctionnement actuel de l'AER.")

register = get_register()
entities = [DIRECTION_GENERALE] + [e for e in flat_entities() if e != DIRECTION_GENERALE] + ["Externe (hors AER)"]

if register.empty:
    st.info("Enregistrez d'abord au moins un dossier sur la page **📂 Registre des dossiers** avant de "
            "pouvoir tracer ses transmissions.")
else:
    st.markdown("**➕ Enregistrer une transmission**")
    with st.container(border=True):
        dossier_options = (register["N° dossier"] + " — " + register["Objet"].astype(str)).tolist()
        choix = st.selectbox("Dossier concerné", dossier_options, key="trans_dossier")
        dossier_id = choix.split(" — ")[0]

        tc1, tc2, tc3 = st.columns(3)
        t_source = tc1.selectbox("Service source", entities, key="trans_source")
        t_dest = tc2.selectbox("Service destination", entities, key="trans_dest")
        t_date = tc3.date_input("Date de la transmission", value=date.today(), key="trans_date")
        t_commentaire = st.text_input("Commentaire (motif, pièce jointe, instruction...)", key="trans_commentaire")

        if st.button("Enregistrer la transmission", type="primary"):
            add_transmission(dossier_id, t_date, t_source, t_dest, t_commentaire)
            st.success(f"Transmission enregistrée pour {dossier_id} : {t_source} → {t_dest}.")
            st.rerun()

    st.write("")
    section_title("HISTORIQUE D'UN DOSSIER")
    hist_choice = st.selectbox("Voir l'historique de :", dossier_options, key="hist_dossier")
    hist_id = hist_choice.split(" — ")[0]
    hist = history_for(hist_id)
    if hist.empty:
        st.info("Aucune transmission enregistrée pour ce dossier pour l'instant.")
    else:
        st.dataframe(hist, use_container_width=True, hide_index=True)

st.write("")
section_title("JOURNAL COMPLET DES TRANSMISSIONS")
log = get_log()
if log.empty:
    st.info("Le journal est vide pour l'instant.")
else:
    lc1, rc1 = st.columns([1.3, 1])
    with lc1:
        edited_log = st.data_editor(
            log, use_container_width=True, hide_index=True, num_rows="dynamic",
            height=min(60 + 36 * (len(log) + 1), 420),
            column_config={"Date": st.column_config.DateColumn("Date")},
            key="log_editor",
        )
        set_log(edited_log)
        st.download_button("⬇️ Télécharger le journal (CSV)",
                            get_log().to_csv(index=False).encode("utf-8"),
                            f"journal_transmissions_aer_{date.today().isoformat()}.csv", "text/csv")
    with rc1:
        by_service = get_log()["Service destination"].value_counts().reset_index()
        by_service.columns = ["Service", "Nombre de transmissions reçues"]
        fig = px.bar(by_service.sort_values("Nombre de transmissions reçues", ascending=False).head(15),
                     x="Service", y="Nombre de transmissions reçues", color_discrete_sequence=[NAVY],
                     title="Services les plus sollicités (nombre de dossiers reçus)")
        fig = plotly_base_layout(fig, legend=False)
        fig.update_xaxes(tickangle=-35)
        st.plotly_chart(fig, use_container_width=True)

    st.write("")
    section_title("TEMPS PASSÉ PAR SERVICE — CALCULÉ À PARTIR DES DATES SAISIES")
    tps = temps_par_service(get_log())
    if tps.empty:
        st.info("Pas encore assez de mouvements pour calculer un temps de passage.")
    else:
        moy = tps.groupby("Service", as_index=False)["Jours passés"].mean().sort_values(
            "Jours passés", ascending=False)
        moy.columns = ["Service", "Jours passés en moyenne"]
        c1, c2 = st.columns(2)
        with c1:
            fig = px.bar(moy.head(15), x="Service", y="Jours passés en moyenne",
                         color_discrete_sequence=["#C77800"], title="Délai moyen de traitement par service (jours)")
            fig = plotly_base_layout(fig, legend=False)
            fig.update_xaxes(tickangle=-35)
            st.plotly_chart(fig, use_container_width=True)
        with c2:
            st.dataframe(tps.sort_values("Jours passés", ascending=False), use_container_width=True,
                         hide_index=True, height=380)

render_sidebar_footer()
