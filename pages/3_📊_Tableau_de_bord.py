from datetime import date

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from utils.ui import PAGE_ICON, inject_base_style, section_title, kpi_row, plotly_base_layout, STATUT_COLORS, render_sidebar_footer
from utils.dossiers import get_register, with_derived_columns, STATUTS_CLOS
from utils.transmissions import get_log, temps_par_service

st.set_page_config(page_title="Tableau de bord — AER", page_icon=PAGE_ICON, layout="wide")
inject_base_style()

st.title("📊 Tableau de bord")
st.caption("Indicateurs calculés uniquement à partir des dossiers et transmissions saisis.")

register = with_derived_columns(get_register())

if register.empty:
    st.info("Le tableau de bord se remplira dès que des dossiers seront saisis sur la page "
            "**📂 Registre des dossiers**.")
    st.stop()

nb_actifs = int((~register["Statut"].isin(STATUTS_CLOS)).sum())
nb_retard = int(register["En retard"].sum())
nb_proche = int(register["Échéance proche"].sum())
delai_moyen = register.loc[register["Statut"].isin(STATUTS_CLOS), "Jours depuis réception"].mean()
taux_retard = (nb_retard / nb_actifs * 100) if nb_actifs else 0

kpi_row([
    ("Dossiers au total", str(len(register)), None),
    ("Dossiers actifs", str(nb_actifs), None),
    ("En retard", str(nb_retard), None),
    ("Échéance proche (≤3j)", str(nb_proche), None),
    ("Taux de retard (parmi actifs)", f"{taux_retard:,.1f} %", None),
])
kpi_row([
    ("Délai moyen de clôture (jours)", f"{delai_moyen:,.1f}" if pd.notna(delai_moyen) else "—", None),
])

st.write("")
c1, c2 = st.columns(2)
with c1:
    counts = register["Statut"].value_counts()
    fig = go.Figure(data=[go.Pie(
        labels=counts.index, values=counts.values, hole=0.45,
        marker=dict(colors=[STATUT_COLORS.get(s, "#8A8A8A") for s in counts.index]),
        textinfo="label+percent",
    )])
    fig.update_layout(title="Répartition des dossiers par statut")
    fig = plotly_base_layout(fig, legend=False)
    st.plotly_chart(fig, use_container_width=True)
with c2:
    by_dir = register.groupby("Direction concernée", as_index=False).size().sort_values("size", ascending=False)
    by_dir.columns = ["Direction", "Nombre de dossiers"]
    fig = px.bar(by_dir, x="Direction", y="Nombre de dossiers", color_discrete_sequence=["#1F3864"],
                 title="Dossiers par direction")
    fig = plotly_base_layout(fig, legend=False)
    fig.update_xaxes(tickangle=-25)
    st.plotly_chart(fig, use_container_width=True)

c3, c4 = st.columns(2)
with c3:
    by_type = register.groupby("Type de dossier", as_index=False).size().sort_values("size", ascending=False)
    by_type.columns = ["Type", "Nombre de dossiers"]
    fig = px.bar(by_type, x="Type", y="Nombre de dossiers", color_discrete_sequence=["#C9A24B"],
                 title="Dossiers par type")
    fig = plotly_base_layout(fig, legend=False)
    st.plotly_chart(fig, use_container_width=True)
with c4:
    by_service = register.groupby("Service destinataire actuel", as_index=False).size().sort_values(
        "size", ascending=False).head(15)
    by_service.columns = ["Service", "Nombre de dossiers"]
    fig = px.bar(by_service, x="Service", y="Nombre de dossiers", color_discrete_sequence=["#2E5C99"],
                 title="Charge actuelle par service (top 15)")
    fig = plotly_base_layout(fig, legend=False)
    fig.update_xaxes(tickangle=-35)
    st.plotly_chart(fig, use_container_width=True)

st.write("")
section_title("BENCHMARKING DES SERVICES — DISTRIBUTION DES DÉLAIS DE TRAITEMENT")
tps = temps_par_service(get_log())
if tps.empty:
    st.info("Enregistrez des transmissions (page Transmissions & traçabilité) pour voir apparaître la "
            "distribution des délais par service ici.")
else:
    top_services = tps.groupby("Service")["Jours passés"].mean().sort_values(ascending=False).head(12).index
    fig = px.box(tps[tps["Service"].isin(top_services)], x="Service", y="Jours passés",
                 color_discrete_sequence=["#2E5C99"],
                 title="Distribution du temps passé par service (jours) — identifie les goulots d'étranglement")
    fig = plotly_base_layout(fig, legend=False, height=420)
    fig.update_xaxes(tickangle=-35)
    st.plotly_chart(fig, use_container_width=True)
    nb_depassements = int(tps["Dépassement"].sum())
    if nb_depassements:
        st.warning(f"{nb_depassements} étape(s) de transmission ont dépassé le délai imparti fixé — "
                   "détail sur la page Transmissions & traçabilité.")

st.write("")
section_title("DOSSIERS PRIORITAIRES / EN RETARD")
retard_view = register[register["En retard"]].sort_values("Jours de retard", ascending=False)
if retard_view.empty:
    st.success("Aucun dossier en retard parmi ceux enregistrés.")
else:
    st.dataframe(
        retard_view[["N° dossier", "Objet", "Direction concernée", "Service destinataire actuel",
                     "Priorité", "Statut", "Échéance prévue", "Jours de retard", "Agent en charge"]],
        use_container_width=True, hide_index=True,
    )

with st.expander("📄 Détail complet avec colonnes calculées"):
    st.dataframe(register, use_container_width=True, hide_index=True, height=420)

st.write("")
section_title("RAPPORT DE SYNTHÈSE")
rapport = f"""# Rapport de synthèse — Suivi des dossiers AER
Généré le {date.today().strftime('%d/%m/%Y')}

## Indicateurs clés
- Dossiers au total : {len(register)}
- Dossiers actifs : {nb_actifs}
- Dossiers en retard : {nb_retard} ({taux_retard:.1f} % des dossiers actifs)
- Dossiers à échéance proche (≤ 3 jours) : {nb_proche}
- Délai moyen de clôture : {f"{delai_moyen:.1f} jours" if pd.notna(delai_moyen) else "non calculable (aucun dossier clôturé)"}

## Répartition par direction
{register.groupby("Direction concernée").size().sort_values(ascending=False).to_string()}

## Dossiers en retard
{retard_view[["N° dossier", "Objet", "Service destinataire actuel", "Jours de retard"]].to_string(index=False) if not retard_view.empty else "Aucun."}
"""
st.download_button("📥 Exporter le rapport de synthèse (Markdown)", rapport.encode("utf-8"),
                    f"rapport_synthese_aer_{date.today().isoformat()}.md", "text/markdown")

render_sidebar_footer()
