"""Composants d'interface et thème partagés par toutes les pages."""
from __future__ import annotations

import streamlit as st
import plotly.graph_objects as go

PAGE_ICON = "📂"
APP_TITLE = "Suivi des dossiers — AER"

NAVY = "#1F3864"
BLUE = "#2E5C99"
GOLD = "#C9A24B"
RED = "#C00000"
GREEN = "#2E7D32"
AMBER = "#C77800"
GREY = "#8A8A8A"
CATEGORICAL = [NAVY, BLUE, GOLD, GREEN, RED, AMBER, GREY, "#7A5C61"]

STATUT_COLORS = {
    "Reçu": BLUE,
    "En cours": GOLD,
    "En attente": AMBER,
    "Traité / Clôturé": GREEN,
    "Archivé": GREY,
}


def inject_base_style():
    st.markdown(
        f"""
        <style>
        .block-container {{ padding-top: 1.6rem; padding-bottom: 3rem; }}
        [data-testid="stMetricValue"] {{ font-size: 1.6rem; color: {NAVY}; }}
        [data-testid="stMetricLabel"] {{ font-weight: 600; letter-spacing: .02em; }}
        .aer-section-title {{
            background: #DCE6F1; color: {NAVY}; font-weight: 700; font-size: 1.02rem;
            padding: 0.5rem 0.8rem; border-radius: 6px; margin: 0.6rem 0 0.8rem 0;
        }}
        .aer-badge {{
            display: inline-block; padding: 0.15rem 0.6rem; border-radius: 999px;
            font-size: 0.78rem; font-weight: 700; color: white;
        }}
        </style>
        """,
        unsafe_allow_html=True,
    )


def section_title(text: str):
    st.markdown(f'<div class="aer-section-title">{text}</div>', unsafe_allow_html=True)


def status_badge(status: str) -> str:
    color = STATUT_COLORS.get(status, GREY)
    return f'<span class="aer-badge" style="background:{color}">{status}</span>'


def plotly_base_layout(fig: go.Figure, height: int = 380, legend: bool = True) -> go.Figure:
    fig.update_layout(
        height=height,
        margin=dict(l=10, r=10, t=48, b=10),
        font=dict(family="Segoe UI, Arial, sans-serif", size=13, color="#2B2B2B"),
        title_font=dict(size=15, color=NAVY),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        showlegend=legend,
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        hoverlabel=dict(bgcolor="white", font_size=12),
    )
    fig.update_xaxes(showgrid=False, zeroline=False)
    fig.update_yaxes(showgrid=True, gridcolor="rgba(31,56,100,0.08)", zeroline=False)
    return fig


def kpi_row(items: list[tuple[str, str, str | None]]):
    cols = st.columns(len(items))
    for col, (label, value, delta) in zip(cols, items):
        with col:
            st.metric(label, value, delta=delta)


def render_sidebar_footer():
    st.sidebar.markdown("---")
    st.sidebar.caption("AER · Prototype de suivi des dossiers — construit avec Streamlit & Plotly.")
