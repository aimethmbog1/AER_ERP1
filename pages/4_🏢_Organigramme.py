import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from utils.ui import (
    PAGE_ICON, inject_base_style, section_title, plotly_base_layout, GREEN, AMBER, RED, GREY,
    render_sidebar_footer, render_page_header,
)
from utils.dossiers import get_register, with_derived_columns, STATUTS_CLOS
from utils.orgchart import (
    hierarchy_rows, all_directions, sous_directions_for, services_for,
    ANTENNES_REGIONALES, SERVICES_RATTACHES_DG, ORGANES_GOUVERNANCE, LEGENDE_ORGANIGRAMME,
    DIRECTION_GENERALE, NODES, all_node_ids, compute_tree_layout, children_of,
)

st.set_page_config(page_title="Organigramme — AER", page_icon=PAGE_ICON, layout="wide")
inject_base_style()

render_page_header("🏢", "Organigramme de l'AER",
                    "Structure réelle utilisée pour le routage des dossiers — d'après l'organigramme "
                    "officiel « AER 2025 » et le descriptif du fonctionnement des directions fourni.")

with st.expander("ℹ️ Deux réserves honnêtes sur cette structure", expanded=False):
    st.markdown(
        """
- Le document source liste deux fois **« Service des Marchés »** (sous la Sous-Direction des Affaires
  Administratives, et sous celle des Ressources Humaines) — les deux sont conservés, distingués ici par
  un suffixe `(DAAF-Admin)` / `(DAAF-RH)` pour éviter toute ambiguïté dans les listes de choix ; le texte
  source, lui, ne les distinguait pas autrement que par leur position.
- La légende de l'organigramme officiel annonce **5 Directions, 17 Sous-Directions, 27 Services**. En
  aplatissant le texte détaillé fourni, notre décompte peut différer légèrement — les organes de
  gouvernance (Conseil d'Administration, Cabinet du PCA, Conseiller technique) ne sont pas nécessairement
  comptés de la même façon d'un document à l'autre. Les deux décomptes sont affichés plutôt que d'en
  forcer un.
- Les 4 chefs d'antenne régionale sont positionnés au même palier hiérarchique que les directeurs de
  département **pour les besoins du routage des dossiers**, conformément à l'usage décrit pour cette
  application — ce n'est pas nécessairement la grille indiciaire officielle de l'AER.
- Le **Service du Courrier, de la Liaison et des Archives** a, dans le routage de cette application, un
  droit d'acheminement vers n'importe quel poste (contrairement à tous les autres services, limités à
  leurs subordonnés, leurs pairs et leur supérieur) — une exception assumée qui reflète la fonction réelle
  d'un bureau d'ordre : « les dossiers entrants passent par le service courrier et celui-ci achemine vers
  les postes concernés ». Un dossier externe arrive d'ailleurs à ce service par défaut, plutôt qu'à la
  Direction Générale.
        """
    )

# =====================================================================
# Graphe organigramme avec voyants de statut en temps réel
# =====================================================================
section_title("🚦 GRAPHE ORGANIGRAMME — VOYANTS DE STATUT EN TEMPS RÉEL")
st.caption(
    "Chaque poste est colorié selon les dossiers qui s'y trouvent **actuellement** (colonne "
    "« Service destinataire actuel » du registre) : 🔴 rouge si au moins un dossier y est en retard, "
    "🟡 jaune si un dossier approche de son échéance (≤ 3 jours) sans être en retard, 🟢 vert si tous "
    "les dossiers présents sont dans les délais, ⚪ gris si aucun dossier n'y est actuellement."
)

register = with_derived_columns(get_register())

status_by_node: dict[str, str] = {}
count_by_node: dict[str, int] = {}
if not register.empty:
    actifs = register[~register["Statut"].isin(STATUTS_CLOS)]
    for node_id in all_node_ids():
        sub = actifs[actifs["Service destinataire actuel"] == node_id]
        count_by_node[node_id] = len(sub)
        if sub.empty:
            status_by_node[node_id] = "grey"
        elif sub["En retard"].any():
            status_by_node[node_id] = "red"
        elif sub["Échéance proche"].any():
            status_by_node[node_id] = "yellow"
        else:
            status_by_node[node_id] = "green"
else:
    for node_id in all_node_ids():
        status_by_node[node_id] = "grey"
        count_by_node[node_id] = 0

COLOR_MAP = {"red": RED, "yellow": AMBER, "green": GREEN, "grey": "#C8CDD3"}

positions = compute_tree_layout()

edge_x, edge_y = [], []
for node_id in positions:
    for child in children_of(node_id):
        if child in positions:
            x0, y0 = positions[node_id]
            x1, y1 = positions[child]
            edge_x += [x0, x1, None]
            edge_y += [y0, y1, None]

node_ids_plot = list(positions.keys())
node_x = [positions[n][0] for n in node_ids_plot]
node_y = [positions[n][1] for n in node_ids_plot]
node_color = [COLOR_MAP[status_by_node.get(n, "grey")] for n in node_ids_plot]
node_size = [16 + 6 * min(count_by_node.get(n, 0), 5) for n in node_ids_plot]
node_text = [NODES[n].label for n in node_ids_plot]
node_hover = [
    f"<b>{NODES[n].label}</b><br>Rang : {NODES[n].rang}<br>Dossiers actifs ici : {count_by_node.get(n, 0)}"
    for n in node_ids_plot
]

fig = go.Figure()
fig.add_trace(go.Scatter(x=edge_x, y=edge_y, mode="lines",
                          line=dict(color="rgba(31,56,100,0.25)", width=1.2), hoverinfo="skip",
                          showlegend=False))
fig.add_trace(go.Scatter(
    x=node_x, y=node_y, mode="markers+text",
    marker=dict(size=node_size, color=node_color, line=dict(color="white", width=1.5)),
    text=node_text, textposition="bottom center", textfont=dict(size=9),
    hovertext=node_hover, hoverinfo="text", showlegend=False,
))
for label, color in [("🔴 En retard", RED), ("🟡 Échéance proche", AMBER),
                     ("🟢 Dans les délais", GREEN), ("⚪ Aucun dossier", "#C8CDD3")]:
    fig.add_trace(go.Scatter(x=[None], y=[None], mode="markers",
                              marker=dict(size=12, color=color), name=label))
fig.update_layout(title="Organigramme AER — voyants de statut par poste", showlegend=True)
fig.update_xaxes(visible=False)
fig.update_yaxes(visible=False)
fig = plotly_base_layout(fig, height=680, legend=True)
st.plotly_chart(fig, use_container_width=True)

if register.empty:
    st.info("Tous les voyants sont gris : aucun dossier n'a encore été saisi (voir la page Registre).")

st.write("")
section_title("DÉCOMPTE — LÉGENDE OFFICIELLE VS. STRUCTURE DÉTAILLÉE FOURNIE")
rows = hierarchy_rows()
decompte_detail = {
    "Direction Générale": 1,
    "Directions centrales (texte détaillé)": len([r for r in rows if r["Niveau"] == "Directeur / Chef d'Antenne"
                                                    and r["Entité"] in all_directions()]),
    "Sous-directions (texte détaillé)": len([r for r in rows if r["Niveau"] == "Sous-Directeur / Chef de Cellule"]),
    "Services (texte détaillé, y compris doublons distingués)": len(
        [r for r in rows if r["Niveau"] == "Chef de Service"]),
}
c1, c2 = st.columns(2)
with c1:
    st.markdown("**Légende de l'organigramme officiel**")
    st.table(pd.DataFrame(LEGENDE_ORGANIGRAMME.items(), columns=["Élément", "Nombre annoncé"]))
with c2:
    st.markdown("**Décompte à partir du texte détaillé fourni**")
    st.table(pd.DataFrame(decompte_detail.items(), columns=["Élément", "Nombre obtenu"]))

st.write("")
section_title("EXPLORER PAR DIRECTION")
direction = st.selectbox("Direction", all_directions())
if direction == DIRECTION_GENERALE:
    ec1, ec2 = st.columns(2)
    with ec1:
        st.markdown("**Organes de gouvernance**")
        st.write("\n".join(f"- {o}" for o in ORGANES_GOUVERNANCE))
        st.markdown("**Services rattachés à la Direction Générale**")
        st.write("\n".join(f"- {s}" for s in SERVICES_RATTACHES_DG))
    with ec2:
        st.markdown("**Antennes régionales**")
        st.write("\n".join(f"- {a}" for a in ANTENNES_REGIONALES))
else:
    for sd in sous_directions_for(direction):
        st.markdown(f"**{sd}**")
        st.write("\n".join(f"- {s}" for s in services_for(direction, sd)))

render_sidebar_footer()
