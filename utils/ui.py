"""Design system AER — v3 (« la plus professionnelle »).

Changement de philosophie par rapport à la v2 : le thème (couleurs, police,
rayons, bordures) vient désormais de `.streamlit/config.toml`
([theme]/[theme.light]/[theme.dark]/[theme.sidebar]), qui gère nativement le
clair/sombre (menu ⋮ → Settings → Choose app theme) — ce n'est plus du CSS
qui le fait. Le CSS qui reste ici est un recours volontaire et restreint à
ce que le thème ne couvre pas : le dégradé de marque de la barre latérale,
le bandeau d'en-tête avec emblème, les badges de statut multicolores (le
thème ne connaît que 7 couleurs nommées), et la couche d'animations/
micro-interactions demandée explicitement par l'utilisateur. Chaque bloc CSS
lit les couleurs actives via `st.context.theme` pour rester synchronisé avec
le thème choisi, au lieu de dupliquer une palette figée.

Emblème : `assets/aer_logo_officiel.png` est le logo officiel de l'AER
(fourni par l'utilisateur), fond détouré en transparent pour s'intégrer
proprement sur le dégradé marine de la barre latérale ;
`assets/aer_logo_officiel_icon.png` en est un recadrage carré (le blason
seul, sans le bandeau de texte) pour l'icône compacte affichée quand la
barre latérale est réduite. Les anciens `assets/aer_emblem.svg` /
`assets/aer_wordmark.svg` (lockup original, provisoire) restent dans le
dépôt pour mémoire mais ne sont plus référencés."""
from __future__ import annotations

import textwrap
from pathlib import Path

import streamlit as st
import streamlit.components.v1 as components
import plotly.graph_objects as go

PAGE_ICON = ":material/folder_managed:"
APP_TITLE = "Suivi des dossiers — AER"
APP_SUBTITLE = "Agence de l'Électrification Rurale · Gestion documentaire & traçabilité"

ASSETS_DIR = Path(__file__).resolve().parent.parent / "assets"
BRAND_ICON = str(ASSETS_DIR / "aer_logo_officiel_icon.png")
BRAND_LOGO = str(ASSETS_DIR / "aer_logo_officiel.png")

# ---------------------------------------------------------------------------
# Palette de référence (identique à .streamlit/config.toml) — utilisée pour
# les éléments que le thème Streamlit ne pilote pas lui-même : les figures
# Plotly (qui veulent des couleurs littérales) et les badges de statut
# multicolores. `theme_palette()` ci-dessous choisit entre les deux jeux
# selon le thème actif.
# ---------------------------------------------------------------------------
_LIGHT = dict(
    navy="#0B3D62", navy_dark="#082A46", blue="#2E6DA4", accent="#0E8FA3", gold="#C9A24B",
    red="#C0392B", green="#1E8449", amber="#B8750A", grey="#6B7280", grey_light="#E5E8EC",
    bg="#F4F6F8", surface="#FFFFFF", border="#E2E6EA", text="#1C2733", text_muted="#5B6672",
)
_DARK = dict(
    navy="#5B9BD5", navy_dark="#0A1620", blue="#5B9BD5", accent="#2BB9CF", gold="#E3C26B",
    red="#E6684F", green="#4FBE7E", amber="#E0A23D", grey="#9AA5B1", grey_light="#22333F",
    bg="#0A1620", surface="#11212E", border="#22333F", text="#E7EEF5", text_muted="#9AA5B1",
)

# Rétro-compatibilité : constantes historiques utilisées par endroits dans
# les pages existantes (toujours la variante claire — l'essentiel de ce
# fichier est passé à `theme_palette()`, qui est theme-aware).
NAVY, NAVY_DARK, BLUE, ACCENT, GOLD = (_LIGHT[k] for k in ("navy", "navy_dark", "blue", "accent", "gold"))
RED, GREEN, AMBER, GREY, GREY_LIGHT = (_LIGHT[k] for k in ("red", "green", "amber", "grey", "grey_light"))
BG, SURFACE, BORDER, TEXT, TEXT_MUTED = (_LIGHT[k] for k in ("bg", "surface", "border", "text", "text_muted"))


def is_dark_theme() -> bool:
    try:
        return st.context.theme.type == "dark"
    except Exception:
        return False


def theme_palette() -> dict:
    """Palette littérale (hex) adaptée au thème clair/sombre actif —
    utilisée par les figures Plotly et les badges, que le thème Streamlit
    ne recolore pas automatiquement lui-même."""
    return dict(_DARK if is_dark_theme() else _LIGHT)


CATEGORICAL_LIGHT = [_LIGHT[k] for k in ("navy", "accent", "gold", "green", "red", "amber", "grey", "blue")]
CATEGORICAL_DARK = [_DARK[k] for k in ("blue", "accent", "gold", "green", "red", "amber", "grey", "navy")]
CATEGORICAL = CATEGORICAL_LIGHT  # rétro-compatibilité (code appelant qui importerait la constante)


def categorical_colors() -> list[str]:
    return CATEGORICAL_DARK if is_dark_theme() else CATEGORICAL_LIGHT


def status_colors() -> dict:
    p = theme_palette()
    return {
        "Reçu": p["blue"],
        "En cours": p["gold"],
        "En attente": p["amber"],
        "Traité / Clôturé": p["green"],
        "Archivé": p["grey"],
    }


STATUT_COLORS = status_colors  # certaines pages appellent STATUT_COLORS[...] ; voir status_badge()

# Couleurs "nommées" du thème (st.badge n'accepte que ce jeu fixe) pour les
# endroits où un badge natif suffit et où la couleur exacte importe moins
# que la cohérence avec le reste de l'app.
STATUT_BADGE_NATIF = {
    "Reçu": "blue",
    "En cours": "orange",
    "En attente": "orange",
    "Traité / Clôturé": "green",
    "Archivé": "gray",
}


# ---------------------------------------------------------------------------
# Couche CSS — volontairement restreinte (voir le docstring du module)
# ---------------------------------------------------------------------------
def inject_base_style():
    p = theme_palette()
    dark = is_dark_theme()
    sidebar_grad_top = "#0E4A74" if not dark else "#0C1D2B"
    sidebar_grad_bottom = "#082A46" if not dark else "#061019"

    css = f"""
        <style>
        /* ====================================================================
           1) Bandeau de marque + dégradé de la barre latérale
           (le thème config.toml pose une couleur plate ; le dégradé et
           l'emblème sont la seule touche de style de marque ajoutée ici) */
        section[data-testid="stSidebar"] {{
            background: linear-gradient(180deg, {sidebar_grad_top} 0%, {sidebar_grad_bottom} 100%) !important;
        }}
        [data-testid="stSidebarHeader"] {{ padding-top: 0.6rem; }}
        [data-testid="stSidebarHeader"] img {{
            border-radius: 10px;
            animation: aer-fade-in 0.5s ease both;
        }}

        /* ====================================================================
           2) En-tête de page (icône sur pastille + titre + sous-titre) */
        .aer-page-header {{
            display: flex; align-items: center; gap: 0.9rem;
            background: {p['surface']}; border: 1px solid {p['border']}; border-radius: 14px;
            padding: 1.05rem 1.35rem; margin-bottom: 1.1rem;
            box-shadow: 0 1px 4px rgba(16,24,40,0.06);
            animation: aer-slide-up 0.45s cubic-bezier(.2,.8,.2,1) both;
        }}
        .aer-page-header .aer-icon {{
            font-size: 1.55rem; width: 50px; height: 50px; min-width: 50px;
            display: flex; align-items: center; justify-content: center; color: white;
            background: linear-gradient(135deg, {p['navy']}, {p['accent']}); border-radius: 12px;
            box-shadow: 0 2px 10px rgba(14,143,163,0.35);
            overflow: hidden; white-space: nowrap;
        }}
        .aer-page-header .aer-titles h1 {{
            font-size: 1.32rem; margin: 0; color: {p['navy']}; line-height: 1.25; font-weight: 800;
        }}
        .aer-page-header .aer-titles p {{ margin: 0.15rem 0 0 0; color: {p['text_muted']}; font-size: 0.9rem; }}

        /* ====================================================================
           3) Bannière de section */
        .aer-section-title {{
            background: {p['surface']}; color: {p['navy']}; font-weight: 700; font-size: 0.92rem;
            text-transform: uppercase; letter-spacing: 0.04em;
            padding: 0.55rem 1rem; border-left: 4px solid {p['accent']};
            border-radius: 8px; margin: 1.1rem 0 0.9rem 0;
            box-shadow: 0 1px 3px rgba(16,24,40,0.06);
            animation: aer-fade-in 0.4s ease both;
        }}

        /* ====================================================================
           4) Badges de statut (pilule colorée — le thème ne propose que 7
              couleurs nommées, insuffisant pour les 5 statuts distincts) */
        .aer-badge {{
            display: inline-flex; align-items: center; gap: 0.35rem;
            padding: 0.22rem 0.7rem; border-radius: 999px;
            font-size: 0.76rem; font-weight: 700; color: white;
            box-shadow: 0 1px 2px rgba(16,24,40,0.18);
            transition: transform 0.15s ease;
        }}
        .aer-badge:hover {{ transform: translateY(-1px); }}
        .aer-badge::before {{ content: ""; width: 6px; height: 6px; border-radius: 50%; background: rgba(255,255,255,0.85); }}
        .aer-badge.aer-pulse::before {{ animation: aer-pulse-dot 1.6s ease-in-out infinite; }}

        /* ====================================================================
           5) Cartes KPI (utilisées ponctuellement en complément de st.metric,
              quand une icône et un dégradé de marque apportent une vraie
              lisibilité en plus — pas en remplacement systématique) */
        .aer-kpi-card {{
            background: {p['surface']}; border: 1px solid {p['border']}; border-radius: 14px;
            padding: 0.95rem 1.1rem 1.05rem 1.1rem; box-shadow: 0 1px 4px rgba(16,24,40,0.06);
            height: 100%; transition: transform 0.18s ease, box-shadow 0.18s ease;
            animation: aer-slide-up 0.45s cubic-bezier(.2,.8,.2,1) both;
        }}
        .aer-kpi-card:hover {{ transform: translateY(-2px); box-shadow: 0 6px 18px rgba(16,24,40,0.12); }}
        .aer-kpi-card .aer-kpi-top {{ display: flex; align-items: center; justify-content: space-between; }}
        .aer-kpi-card .aer-kpi-icon {{
            font-size: 1.05rem; width: 30px; height: 30px; border-radius: 9px; opacity: 0.95;
            display: flex; align-items: center; justify-content: center; color: white;
            background: linear-gradient(135deg, {p['navy']}, {p['accent']});
            overflow: hidden; white-space: nowrap;
        }}
        .aer-kpi-card .aer-kpi-value {{
            font-size: 1.75rem; font-weight: 800; color: {p['navy']}; line-height: 1.15; margin-top: 0.4rem;
        }}
        .aer-kpi-card .aer-kpi-label {{
            font-size: 0.78rem; font-weight: 600; color: {p['text_muted']};
            text-transform: uppercase; letter-spacing: 0.03em; margin-top: 0.15rem;
        }}

        /* ====================================================================
           6) Micro-interactions générales (boutons, cartes, onglets) */
        .stButton > button, .stDownloadButton > button {{ transition: transform 0.12s ease, box-shadow 0.12s ease; }}
        .stButton > button:hover, .stDownloadButton > button:hover {{ transform: translateY(-1px); }}
        .stButton > button:active {{ transform: translateY(0px) scale(0.98); }}
        div[data-testid="stMetric"] {{ transition: transform 0.18s ease; }}
        div[data-testid="stMetric"]:hover {{ transform: translateY(-2px); }}
        [data-testid="stDataFrame"], [data-testid="stDataEditor"] {{ border-radius: 12px; overflow: hidden; }}

        /* Apparition progressive du contenu principal au chargement de la page */
        .block-container > div:nth-of-type(1) {{ animation: aer-fade-in 0.35s ease both; }}

        /* ====================================================================
           6bis) Bandeau illustré (page d'accueil) — scène SVG originale
           (panneaux solaires, pylône, maisons) : voir render_hero_illustration() */
        .aer-hero-card {{
            background: {p['surface']}; border: 1px solid {p['border']}; border-radius: 14px;
            padding: 0.4rem 1rem 0; margin-bottom: 1.1rem; overflow: hidden;
            box-shadow: 0 1px 4px rgba(16,24,40,0.06);
            animation: aer-fade-in 0.5s ease both;
        }}
        .aer-hero-card svg {{ display: block; }}
        .aer-hero-sun {{ transform-origin: 790px 56px; animation: aer-sun-pulse 3.2s ease-in-out infinite; }}
        .aer-hero-wire {{ animation: aer-wire-flow 2.4s linear infinite; }}
        .aer-hero-glint {{ animation: aer-glint-sweep 5s ease-in-out infinite; }}
        @media (prefers-reduced-motion: reduce) {{
            .aer-hero-sun, .aer-hero-wire, .aer-hero-glint {{ animation: none; }}
        }}

        /* ====================================================================
           7) Indicateur "en direct" (pastille clignotante) */
        .aer-live-dot {{
            display: inline-block; width: 8px; height: 8px; border-radius: 50%;
            background: {p['green']}; margin-right: 0.4rem; vertical-align: middle;
            box-shadow: 0 0 0 0 rgba(30,132,73,0.55);
            animation: aer-live-ping 1.8s ease-out infinite;
        }}

        /* ====================================================================
           8) Compteur animé (valeur KPI qui "monte" au chargement) */
        .aer-counter {{ font-variant-numeric: tabular-nums; }}

        /* ====================================================================
           Keyframes */
        @keyframes aer-fade-in {{ from {{ opacity: 0; }} to {{ opacity: 1; }} }}
        @keyframes aer-slide-up {{ from {{ opacity: 0; transform: translateY(10px); }} to {{ opacity: 1; transform: translateY(0); }} }}
        @keyframes aer-pulse-dot {{ 0%, 100% {{ opacity: 0.85; }} 50% {{ opacity: 0.25; }} }}
        @keyframes aer-live-ping {{
            0% {{ box-shadow: 0 0 0 0 rgba(30,132,73,0.55); }}
            70% {{ box-shadow: 0 0 0 7px rgba(30,132,73,0); }}
            100% {{ box-shadow: 0 0 0 0 rgba(30,132,73,0); }}
        }}
        @keyframes aer-sun-pulse {{
            0%, 100% {{ transform: scale(1); opacity: 1; }}
            50% {{ transform: scale(1.08); opacity: 0.85; }}
        }}
        @keyframes aer-wire-flow {{ to {{ stroke-dashoffset: -120; }} }}
        @keyframes aer-glint-sweep {{
            0% {{ transform: translateX(0) skewX(-18deg); }}
            45%, 100% {{ transform: translateX(820px) skewX(-18deg); }}
        }}
        </style>
    """
    st.markdown(textwrap.dedent(css), unsafe_allow_html=True)


def render_brand_logo():
    """Logo + nom de l'app dans la barre latérale (natif `st.logo`, donc géré
    correctement en version réduite/étendue de la sidebar, sans CSS)."""
    st.logo(BRAND_LOGO, icon_image=BRAND_ICON, size="large")


def render_page_header(icon: str, title: str, subtitle: str = ""):
    """En-tête de page uniforme : icône sur pastille en dégradé, titre, sous-titre.

    `icon` est un émoji (ou tout glyphe Unicode simple), PAS un nom Material
    Symbols : une première version utilisait `:material/nom:` rendu via la
    police « Material Symbols Outlined » chargée depuis Google Fonts dans le
    CSS — fragile en pratique (QA visuelle : le glyphe ne s'affichait pas
    dans cet environnement de test, le nom de l'icône s'affichant en toutes
    lettres à la place, le réseau du bac à sable ne pouvant visiblement pas
    atteindre fonts.googleapis.com depuis le navigateur). Un émoji, lui, vient
    de la police à couleurs déjà installée par le système/navigateur, sans
    aucune dépendance réseau — plus robuste pour un élément d'identité
    visuelle central, quel que soit le réseau de l'utilisateur final. Les
    icônes de la barre de NAVIGATION, elles, restent en `:material/...:`
    (voir `streamlit_app.py`) : Streamlit les rend avec ses propres polices
    embarquées dans son build JS, pas via Google Fonts — QA confirmée, elles
    s'affichent correctement."""
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


def render_hero_illustration():
    """Bandeau illustré de la page d'accueil — une scène ORIGINALE (panneaux
    solaires, pylône électrique, maisons, soleil), dessinée en SVG à partir
    de la palette de marque active, pas une photo. Choix délibéré : les
    photos fournies par l'utilisateur pour « animer » la plateforme
    (cliché Alamy avec filigrane, et une image dont la source/licence n'est
    pas établie) ne peuvent pas être intégrées à une application publique
    sans droits clairs — voir le message envoyé à ce sujet. Cette
    illustration est 100 % originale (aucun tracé copié), cohérente avec le
    reste de l'identité visuelle, et légère (quelques Ko de SVG contre
    plusieurs centaines de Ko de photo)."""
    p = theme_palette()
    svg = f"""
    <svg viewBox="0 0 900 230" width="100%" height="auto" role="img" aria-label="Illustration : électrification rurale">
      <defs>
        <linearGradient id="aerSkyGrad" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stop-color="{p['accent']}" stop-opacity="0.10"/>
          <stop offset="100%" stop-color="{p['accent']}" stop-opacity="0"/>
        </linearGradient>
        <linearGradient id="aerPanelGrad" x1="0" y1="0" x2="1" y2="1">
          <stop offset="0%" stop-color="{p['navy']}"/>
          <stop offset="100%" stop-color="{p['accent']}"/>
        </linearGradient>
        <clipPath id="aerPanelClip">
          <polygon points="470,150 640,150 610,80 500,80"/>
        </clipPath>
      </defs>

      <rect x="0" y="0" width="900" height="230" fill="url(#aerSkyGrad)"/>

      <g class="aer-hero-sun">
        <circle cx="790" cy="56" r="26" fill="{p['gold']}"/>
        <g stroke="{p['gold']}" stroke-width="3" stroke-linecap="round">
          <line x1="790" y1="10" x2="790" y2="0"/>
          <line x1="834" y1="56" x2="844" y2="56"/>
          <line x1="821" y1="27" x2="828" y2="20"/>
          <line x1="821" y1="85" x2="828" y2="92"/>
          <line x1="759" y1="27" x2="752" y2="20"/>
          <line x1="759" y1="85" x2="752" y2="92"/>
        </g>
      </g>

      <line x1="0" y1="186" x2="900" y2="186" stroke="{p['border']}" stroke-width="2"/>

      <!-- Pylône + lignes électriques -->
      <g stroke="{p['text_muted']}" stroke-width="4" stroke-linecap="round">
        <line x1="120" y1="186" x2="120" y2="70"/>
        <line x1="92" y1="90" x2="148" y2="90"/>
        <line x1="100" y1="112" x2="140" y2="112"/>
      </g>
      <path class="aer-hero-wire" d="M 96 90 Q 300 40 500 95" fill="none" stroke="{p['accent']}" stroke-width="2.5" stroke-dasharray="2 10" stroke-linecap="round"/>
      <path class="aer-hero-wire" d="M 144 90 Q 320 150 470 128" fill="none" stroke="{p['accent']}" stroke-width="2.5" stroke-dasharray="2 10" stroke-linecap="round"/>

      <!-- Panneaux solaires -->
      <polygon points="470,150 640,150 610,80 500,80" fill="url(#aerPanelGrad)"/>
      <g clip-path="url(#aerPanelClip)">
        <g stroke="{p['surface']}" stroke-width="2" opacity="0.55">
          <line x1="470" y1="130" x2="640" y2="130"/>
          <line x1="470" y1="110" x2="640" y2="110"/>
          <line x1="470" y1="150" x2="610" y2="80"/>
          <line x1="520" y1="150" x2="552" y2="80"/>
          <line x1="565" y1="150" x2="595" y2="80"/>
        </g>
        <rect class="aer-hero-glint" x="-120" y="70" width="60" height="110" fill="{p['surface']}" opacity="0.35" transform="skewX(-18)"/>
      </g>
      <line x1="555" y1="150" x2="555" y2="186" stroke="{p['text_muted']}" stroke-width="5"/>

      <!-- Maisons -->
      <g>
        <rect x="660" y="140" width="64" height="46" fill="{p['navy']}" opacity="0.85"/>
        <polygon points="652,140 732,140 692,104" fill="{p['gold']}"/>
        <rect x="686" y="160" width="14" height="26" fill="{p['surface']}"/>
      </g>
      <g>
        <rect x="745" y="152" width="46" height="34" fill="{p['navy']}" opacity="0.7"/>
        <polygon points="740,152 796,152 768,126" fill="{p['green']}"/>
      </g>
      <g>
        <rect x="200" y="156" width="46" height="30" fill="{p['navy']}" opacity="0.6"/>
        <polygon points="195,156 251,156 223,132" fill="{p['red']}" opacity="0.85"/>
      </g>

      <!-- Arbres (petite touche rurale) -->
      <g fill="{p['green']}" opacity="0.8">
        <circle cx="330" cy="168" r="14"/>
        <rect x="327" y="174" width="6" height="12"/>
        <circle cx="820" cy="172" r="11"/>
        <rect x="817" y="177" width="6" height="10"/>
      </g>
    </svg>
    """
    # `st.markdown` passe par un rendu Markdown avant le HTML : un bloc HTML
    # brut (ici notre <div>) n'est traité comme tel par Markdown que tant
    # qu'aucune ligne vide ne l'interrompt — sinon le contenu qui suit est
    # ré-analysé comme du Markdown, et une ligne indentée de 4 espaces ou
    # plus devient un bloc de code (QA visuelle : le SVG s'affichait en
    # texte brut). On retire l'indentation ET les lignes vides du SVG avant
    # de l'injecter, pour qu'il ne forme qu'un seul bloc HTML continu.
    svg_compact = "\n".join(
        line for line in textwrap.dedent(svg).splitlines() if line.strip()
    )
    st.markdown(f'<div class="aer-hero-card">{svg_compact}</div>', unsafe_allow_html=True)


def section_title(text: str):
    st.markdown(f'<div class="aer-section-title">{text}</div>', unsafe_allow_html=True)


def status_badge(status: str, pulse: bool = False) -> str:
    color = status_colors().get(status, theme_palette()["grey"])
    cls = "aer-badge aer-pulse" if pulse else "aer-badge"
    return f'<span class="{cls}" style="background:{color}">{status}</span>'


def live_dot() -> str:
    return '<span class="aer-live-dot"></span>'


def plotly_base_layout(fig: go.Figure, height: int = 380, legend: bool = True) -> go.Figure:
    p = theme_palette()
    fig.update_layout(
        height=height,
        margin=dict(l=10, r=10, t=48, b=10),
        font=dict(family="Inter, Segoe UI, Arial, sans-serif", size=13, color=p["text"]),
        title_font=dict(size=15, color=p["navy"]),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        showlegend=legend,
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1,
                     font=dict(color=p["text"])),
        hoverlabel=dict(bgcolor=p["surface"], font_size=12, font_color=p["text"],
                        font_family="Inter, Segoe UI, Arial, sans-serif"),
        colorway=categorical_colors(),
        transition=dict(duration=350, easing="cubic-in-out"),
    )
    grid = "rgba(255,255,255,0.08)" if is_dark_theme() else "rgba(11,61,98,0.08)"
    fig.update_xaxes(showgrid=False, zeroline=False, color=p["text_muted"])
    fig.update_yaxes(showgrid=True, gridcolor=grid, zeroline=False, color=p["text_muted"])
    return fig


def kpi_row(items: list[tuple[str, str, str | None]], icons: list[str] | None = None):
    """Rangée de cartes KPI (identité visuelle de marque : icône en dégradé
    navy→teal). Conservée pour les emplacements où une carte de marque
    apporte plus qu'un `st.metric` nu (ex. Accueil) ; les tableaux de bord
    plus denses utilisent `st.metric(border=True, chart_data=...)` natif
    (voir pages/3)."""
    cols = st.columns(len(items))
    default_icons = ["📁", "✅", "⏱️", "🗂️", "🔁", "📊"]
    for i, (col, (label, value, delta)) in enumerate(zip(cols, items)):
        icon = (icons[i] if icons and i < len(icons) else default_icons[i % len(default_icons)])
        delta_html = ""
        if delta:
            delta_html = (f'<div style="font-size:0.78rem;color:{theme_palette()["text_muted"]};'
                           f'margin-top:0.25rem;">{delta}</div>')
        with col:
            st.markdown(
                f"""
                <div class="aer-kpi-card" style="animation-delay:{i * 60}ms">
                    <div class="aer-kpi-top">
                        <span class="aer-kpi-icon">{icon}</span>
                    </div>
                    <div class="aer-kpi-value aer-counter" data-aer-count="{_numeric_part(value)}">{value}</div>
                    <div class="aer-kpi-label">{label}</div>
                    {delta_html}
                </div>
                """,
                unsafe_allow_html=True,
            )
    _inject_counter_script()


def _numeric_part(value: str) -> str:
    digits = "".join(ch for ch in str(value) if ch.isdigit())
    return digits or "0"


_COUNTER_SCRIPT_DONE_KEY = "_aer_counter_script_emitted"


def _inject_counter_script():
    """Anime la montée en valeur des cartes KPI au premier rendu de la page.

    Un `<script>` inséré via `st.markdown(unsafe_allow_html=True)` n'est
    PAS exécuté par le navigateur (une balise <script> posée par
    innerHTML ne s'exécute jamais — limite connue du DOM, pas de
    Streamlit) : il faut passer par `components.v1.html`, qui rend dans un
    vrai `<iframe>` et peut donc remonter au document parent pour trouver
    les cartes à animer. Hauteur nulle : ce composant n'affiche rien par
    lui-même, il ne fait qu'agir sur le DOM déjà posé par `kpi_row()`."""
    components.html(
        """
        <script>
        (function() {
            const cards = window.parent.document.querySelectorAll('.aer-counter[data-aer-count]');
            cards.forEach((el) => {
                const target = parseInt(el.getAttribute('data-aer-count'), 10);
                if (!isFinite(target) || el.dataset.aerAnimated === "1") return;
                el.dataset.aerAnimated = "1";
                const suffix = el.textContent.replace(/[0-9\\s]/g, '').trim();
                const prefix = el.textContent.match(/^[^0-9]*/)[0];
                const duration = 650;
                const start = performance.now();
                function step(now) {
                    const t = Math.min(1, (now - start) / duration);
                    const eased = 1 - Math.pow(1 - t, 3);
                    const val = Math.round(eased * target);
                    el.textContent = prefix + val.toLocaleString('fr-FR') + (suffix ? ' ' + suffix : '');
                    if (t < 1) requestAnimationFrame(step);
                    else el.textContent = prefix + target.toLocaleString('fr-FR') + (suffix ? ' ' + suffix : '');
                }
                requestAnimationFrame(step);
            });
        })();
        </script>
        """,
        height=0,
    )


def render_sidebar_footer():
    st.sidebar.markdown("---")
    st.sidebar.markdown(
        """
        <div style="font-size:0.72rem; color:#AFC2D4; line-height:1.4;">
            <b style="color:#EAF1F8;">AER</b> · Suivi des dossiers<br>
            Application pilote — Streamlit
        </div>
        """,
        unsafe_allow_html=True,
    )
