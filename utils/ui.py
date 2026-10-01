"""Composants d'interface et thème partagés par toutes les pages.

Thème « GED professionnelle » (inspiré des codes visuels des logiciels de
gestion documentaire d'entreprise type OpenKM / Maarch Courrier : barre
latérale sombre, cartes avec ombre discrète, badges de statut, typographie
sans-serif nette) — appliqué uniquement via CSS, sans dépendance externe,
pour rester 100% Streamlit natif et déployable tel quel."""
from __future__ import annotations

import textwrap

import streamlit as st
import plotly.graph_objects as go

PAGE_ICON = "📂"
APP_TITLE = "Suivi des dossiers — AER"
APP_SUBTITLE = "Agence de l'Électrification Rurale · Gestion documentaire & traçabilité"

# ---------------------------------------------------------------------------
# Palette — bleu institutionnel + accent sobre, sur fond neutre clair
# ---------------------------------------------------------------------------
NAVY = "#0B3D62"        # bleu institutionnel profond (marque, sidebar, titres)
NAVY_DARK = "#082A46"   # variante plus sombre (sidebar, hover)
BLUE = "#2E6DA4"        # bleu d'accent (liens, actions secondaires)
ACCENT = "#0E8FA3"      # teal d'accent (highlights, icônes actives)
GOLD = "#C9A24B"
RED = "#C0392B"
GREEN = "#1E8449"
AMBER = "#B8750A"
GREY = "#6B7280"
GREY_LIGHT = "#E5E8EC"
BG = "#F4F6F8"          # fond général de page
SURFACE = "#FFFFFF"     # fond des cartes
BORDER = "#E2E6EA"
TEXT = "#1C2733"
TEXT_MUTED = "#5B6672"

CATEGORICAL = [NAVY, ACCENT, GOLD, GREEN, RED, AMBER, GREY, BLUE]

STATUT_COLORS = {
    "Reçu": BLUE,
    "En cours": GOLD,
    "En attente": AMBER,
    "Traité / Clôturé": GREEN,
    "Archivé": GREY,
}


def inject_base_style():
    css = f"""
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');
        html, body, [class*="css"] {{
            font-family: 'Inter', 'Segoe UI', Arial, sans-serif;
        }}

        /* ---------- Fond général ---------- */
        .stApp {{ background: {BG}; }}
        .block-container {{ padding-top: 1.2rem; padding-bottom: 3rem; max-width: 1360px; }}

        /* ---------- Barre latérale — look "console GED" ---------- */
        section[data-testid="stSidebar"] {{
            background: linear-gradient(180deg, {NAVY} 0%, {NAVY_DARK} 100%);
        }}
        section[data-testid="stSidebar"] * {{ color: #EAF1F8 !important; }}
        section[data-testid="stSidebar"] .stSelectbox label,
        section[data-testid="stSidebar"] .stMarkdown p {{ color: #CBD9E6 !important; }}
        section[data-testid="stSidebar"] [data-baseweb="select"] > div {{
            background: rgba(255,255,255,0.08);
            border: 1px solid rgba(255,255,255,0.18);
            border-radius: 8px;
        }}
        section[data-testid="stSidebar"] hr {{ border-color: rgba(255,255,255,0.15); }}
        section[data-testid="stSidebarNav"] {{
            border-bottom: 1px solid rgba(255,255,255,0.12);
            padding-bottom: 0.6rem;
            margin-bottom: 0.4rem;
        }}
        section[data-testid="stSidebarNav"] a {{
            border-radius: 8px;
            margin: 1px 6px;
        }}
        section[data-testid="stSidebarNav"] a:hover {{ background: rgba(255,255,255,0.10); }}
        section[data-testid="stSidebarNav"] a[aria-current="page"] {{
            background: rgba(255,255,255,0.16);
            font-weight: 600;
        }}

        /* ---------- Titres ---------- */
        h1, h2, h3 {{ color: {NAVY}; font-weight: 700; letter-spacing: -0.01em; }}
        p, li, span, label {{ color: {TEXT}; }}

        /* ---------- Metrics (fallback) ---------- */
        [data-testid="stMetricValue"] {{ font-size: 1.55rem; color: {NAVY}; font-weight: 700; }}
        [data-testid="stMetricLabel"] {{ font-weight: 600; letter-spacing: .01em; color: {TEXT_MUTED}; }}

        /* ---------- Bannière de section (en-tête de bloc) ---------- */
        .aer-section-title {{
            background: {SURFACE}; color: {NAVY}; font-weight: 700; font-size: 0.95rem;
            text-transform: uppercase; letter-spacing: 0.04em;
            padding: 0.6rem 1rem; border-left: 4px solid {ACCENT};
            border-radius: 6px; margin: 1.1rem 0 0.9rem 0;
            box-shadow: 0 1px 3px rgba(16,24,40,0.06);
        }}

        /* ---------- En-tête de page ---------- */
        .aer-page-header {{
            display: flex; align-items: center; gap: 0.9rem;
            background: {SURFACE}; border: 1px solid {BORDER}; border-radius: 12px;
            padding: 1.1rem 1.4rem; margin-bottom: 1.1rem;
            box-shadow: 0 1px 4px rgba(16,24,40,0.05);
        }}
        .aer-page-header .aer-icon {{
            font-size: 1.9rem; width: 52px; height: 52px; min-width: 52px;
            display: flex; align-items: center; justify-content: center;
            background: {NAVY}; border-radius: 10px;
        }}
        .aer-page-header .aer-titles h1 {{
            font-size: 1.35rem; margin: 0; color: {NAVY}; line-height: 1.25;
        }}
        .aer-page-header .aer-titles p {{
            margin: 0.1rem 0 0 0; color: {TEXT_MUTED}; font-size: 0.9rem;
        }}

        /* ---------- Badges de statut (pilules) ---------- */
        .aer-badge {{
            display: inline-flex; align-items: center; gap: 0.35rem;
            padding: 0.22rem 0.7rem; border-radius: 999px;
            font-size: 0.76rem; font-weight: 700; color: white;
            box-shadow: 0 1px 2px rgba(16,24,40,0.12);
        }}
        .aer-badge::before {{
            content: ""; width: 6px; height: 6px; border-radius: 50%;
            background: rgba(255,255,255,0.85);
        }}

        /* ---------- Cartes KPI ---------- */
        .aer-kpi-card {{
            background: {SURFACE}; border: 1px solid {BORDER}; border-radius: 12px;
            padding: 0.95rem 1.1rem; box-shadow: 0 1px 4px rgba(16,24,40,0.05);
            height: 100%;
        }}
        .aer-kpi-card .aer-kpi-top {{
            display: flex; align-items: center; justify-content: space-between;
        }}
        .aer-kpi-card .aer-kpi-icon {{ font-size: 1.25rem; opacity: 0.85; }}
        .aer-kpi-card .aer-kpi-value {{
            font-size: 1.7rem; font-weight: 800; color: {NAVY}; line-height: 1.15; margin-top: 0.3rem;
        }}
        .aer-kpi-card .aer-kpi-label {{
            font-size: 0.78rem; font-weight: 600; color: {TEXT_MUTED};
            text-transform: uppercase; letter-spacing: 0.03em; margin-top: 0.15rem;
        }}

        /* ---------- Conteneurs / cartes génériques ---------- */
        div[data-testid="stContainer"] > div[style*="border"] {{
            border-radius: 12px !important; border-color: {BORDER} !important;
            box-shadow: 0 1px 4px rgba(16,24,40,0.05);
        }}

        /* ---------- Boutons ---------- */
        .stButton > button {{
            border-radius: 8px; font-weight: 600; border: 1px solid {BORDER};
            transition: all 0.15s ease;
        }}
        .stButton > button[kind="primary"] {{
            background: {NAVY}; border-color: {NAVY};
        }}
        .stButton > button[kind="primary"]:hover {{
            background: {NAVY_DARK}; border-color: {NAVY_DARK};
            box-shadow: 0 2px 8px rgba(11,61,98,0.35);
        }}
        .stDownloadButton > button {{ border-radius: 8px; font-weight: 600; }}

        /* ---------- Tableaux / data_editor ---------- */
        [data-testid="stDataFrame"], [data-testid="stDataEditor"] {{
            border-radius: 10px; overflow: hidden; border: 1px solid {BORDER};
        }}

        /* ---------- Expanders ---------- */
        .streamlit-expanderHeader {{
            border-radius: 8px; font-weight: 600;
        }}

        /* ---------- Tabs ---------- */
        .stTabs [data-baseweb="tab"] {{ font-weight: 600; }}
        </style>
    """
    st.markdown(textwrap.dedent(css), unsafe_allow_html=True)


def render_page_header(icon: str, title: str, subtitle: str = ""):
    """En-tête de page uniforme : icône sur pastille marine, titre, sous-titre."""
    st.markdown(
        f"""
        <div class="aer-page-header">
            <div class="aer-icon">{icon}</div>
            <div class="aer-titles">
                <h1>{title}</h1>
                {f'<p>{subtitle}</p>' if subtitle else ''}
            </div>
        </div>
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
        font=dict(family="Inter, Segoe UI, Arial, sans-serif", size=13, color=TEXT),
        title_font=dict(size=15, color=NAVY),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        showlegend=legend,
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        hoverlabel=dict(bgcolor="white", font_size=12, font_family="Inter, Segoe UI, Arial, sans-serif"),
        colorway=CATEGORICAL,
    )
    fig.update_xaxes(showgrid=False, zeroline=False)
    fig.update_yaxes(showgrid=True, gridcolor="rgba(11,61,98,0.08)", zeroline=False)
    return fig


def kpi_row(items: list[tuple[str, str, str | None]], icons: list[str] | None = None):
    """Rangée de cartes KPI façon tableau de bord GED.

    `items` garde la signature historique (label, valeur, delta) pour rester
    compatible avec tout le code existant ; `icons` est une liste optionnelle
    d'émojis/icônes alignée avec `items` (sinon une icône neutre est utilisée)."""
    cols = st.columns(len(items))
    default_icons = ["📁", "🟢", "⏱️", "✅", "🔁", "📊"]
    for i, (col, (label, value, delta)) in enumerate(zip(cols, items)):
        icon = (icons[i] if icons and i < len(icons) else default_icons[i % len(default_icons)])
        delta_html = ""
        if delta:
            delta_html = f'<div style="font-size:0.78rem;color:{TEXT_MUTED};margin-top:0.2rem;">{delta}</div>'
        with col:
            st.markdown(
                f"""
                <div class="aer-kpi-card">
                    <div class="aer-kpi-top">
                        <span class="aer-kpi-icon">{icon}</span>
                    </div>
                    <div class="aer-kpi-value">{value}</div>
                    <div class="aer-kpi-label">{label}</div>
                    {delta_html}
                </div>
                """,
                unsafe_allow_html=True,
            )


def render_sidebar_footer():
    st.sidebar.markdown("---")
    st.sidebar.markdown(
        f"""
        <div style="font-size:0.72rem; color:#AFC2D4; line-height:1.4;">
            <b style="color:#EAF1F8;">AER</b> · Suivi des dossiers<br>
            Prototype — Streamlit &amp; Plotly
        </div>
        """,
        unsafe_allow_html=True,
    )
