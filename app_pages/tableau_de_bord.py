from datetime import date, timedelta

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from utils.ui import (
    inject_base_style, section_title, plotly_base_layout, status_colors, theme_palette,
    render_sidebar_footer, render_page_header,
)
from utils.dossiers import get_register, with_derived_columns, STATUTS_CLOS
from utils.transmissions import get_log, temps_par_service

inject_base_style()

render_page_header("📊", "Tableau de bord",
                    "Indicateurs calculés uniquement à partir des dossiers et transmissions saisis.")

register = with_derived_columns(get_register())

if register.empty:
    st.info("Le tableau de bord se remplira dès que des dossiers seront saisis sur la page "
            "**Registre des dossiers**.")
    st.stop()

nb_actifs = int((~register["Statut"].isin(STATUTS_CLOS)).sum())
nb_retard = int(register["En retard"].sum())
nb_proche = int(register["Échéance proche"].sum())
delai_moyen = register.loc[register["Statut"].isin(STATUTS_CLOS), "Jours depuis réception"].mean()
taux_retard = (nb_retard / nb_actifs * 100) if nb_actifs else 0

# ---------------------------------------------------------------------------
# KPI natifs (st.metric), avec une mini-tendance réelle (14 derniers jours de
# réception) sur le volume — jamais de tendance inventée sur un indicateur
# dont on n'a pas d'historique réel (statut, retard : seule la base actuelle
# est connue, pas son évolution jour par jour).
# ---------------------------------------------------------------------------
today = date.today()
last_14 = [today - timedelta(days=i) for i in range(13, -1, -1)]
par_jour = register["Date de réception"].dt.date.value_counts()
volume_trend = [int(par_jour.get(d, 0)) for d in last_14]

k1, k2, k3, k4, k5 = st.columns(5)
k1.metric("Dossiers au total", len(register), border=True,
          chart_data=volume_trend, chart_type="area",
          help="Dossiers reçus sur les 14 derniers jours (mini-graphique).")
k2.metric("Dossiers actifs", nb_actifs, border=True)
k3.metric("En retard", nb_retard, border=True,
          delta=None if nb_retard == 0 else f"{taux_retard:.1f} % des actifs", delta_color="inverse")
k4.metric("Échéance proche (≤ 3 j)", nb_proche, border=True)
k5.metric("Délai moyen de clôture", f"{delai_moyen:,.1f} j" if pd.notna(delai_moyen) else "—", border=True)

st.write("")


@st.fragment
def _repartition_section(register: pd.DataFrame):
    """Isolé en fragment : se re-calcule seul si l'utilisateur interagit avec
    un contrôle propre à ce bloc, sans relancer tout le tableau de bord."""
    c1, c2 = st.columns(2)
    with c1:
        counts = register["Statut"].value_counts()
        colors = status_colors()
        fig = go.Figure(data=[go.Pie(
            labels=counts.index, values=counts.values, hole=0.5,
            marker=dict(colors=[colors.get(s, theme_palette()["grey"]) for s in counts.index]),
            textinfo="label+percent", pull=[0.02] * len(counts),
        )])
        fig.update_layout(title="Répartition des dossiers par statut")
        fig = plotly_base_layout(fig, legend=False)
        st.plotly_chart(fig, width='stretch')
    with c2:
        by_dir = register.groupby("Direction concernée", as_index=False).size().sort_values(
            "size", ascending=False).set_index("Direction concernée")
        by_dir.columns = ["Nombre de dossiers"]
        st.markdown("**Dossiers par direction**")
        st.bar_chart(by_dir, horizontal=True, height=340, color=theme_palette()["navy"])


_repartition_section(register)

c3, c4 = st.columns(2)
with c3:
    by_type = register.groupby("Type de dossier", as_index=False).size().sort_values(
        "size", ascending=False).set_index("Type de dossier")
    by_type.columns = ["Nombre de dossiers"]
    st.markdown("**Dossiers par type**")
    st.bar_chart(by_type, height=320, color=theme_palette()["gold"])
with c4:
    by_service = register.groupby("Service destinataire actuel", as_index=False).size().sort_values(
        "size", ascending=False).head(15).set_index("Service destinataire actuel")
    by_service.columns = ["Nombre de dossiers"]
    st.markdown("**Charge actuelle par service (top 15)**")
    st.bar_chart(by_service, height=320, color=theme_palette()["blue"])

st.write("")
section_title("BENCHMARKING DES SERVICES — DISTRIBUTION DES DÉLAIS DE TRAITEMENT")
tps = temps_par_service(get_log())
if tps.empty:
    st.info("Enregistrez des transmissions (page Transmissions & traçabilité) pour voir apparaître la "
            "distribution des délais par service ici.")
else:
    top_services = tps.groupby("Service")["Jours passés"].mean().sort_values(ascending=False).head(12).index
    fig = px.box(tps[tps["Service"].isin(top_services)], x="Service", y="Jours passés",
                 color_discrete_sequence=[theme_palette()["blue"]],
                 title="Distribution du temps passé par service (jours) — identifie les goulots d'étranglement")
    fig = plotly_base_layout(fig, legend=False, height=420)
    fig.update_xaxes(tickangle=-35)
    st.plotly_chart(fig, width='stretch')
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
        width='stretch', hide_index=True,
        column_config={
            "Échéance prévue": st.column_config.DateColumn("Échéance prévue"),
            "Jours de retard": st.column_config.ProgressColumn(
                "Jours de retard", min_value=0, max_value=max(1, int(retard_view["Jours de retard"].max())),
                format="%d j",
            ),
            "Priorité": st.column_config.TextColumn("Priorité"),
        },
    )

with st.expander("📄 Détail complet avec colonnes calculées"):
    st.dataframe(
        register, width='stretch', hide_index=True, height=420,
        column_config={
            "Date de réception": st.column_config.DateColumn("Date de réception"),
            "Échéance prévue": st.column_config.DateColumn("Échéance prévue"),
        },
    )

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
