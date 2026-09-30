import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from utils.ui import PAGE_ICON, inject_base_style, section_title, plotly_base_layout, render_sidebar_footer
from utils.orgchart import (
    hierarchy_rows, all_directions, sous_directions_for, services_for,
    ANTENNES_REGIONALES, SERVICES_RATTACHES_DG, ORGANES_GOUVERNANCE, LEGENDE_ORGANIGRAMME,
    DIRECTION_GENERALE,
)

st.set_page_config(page_title="Organigramme — AER", page_icon=PAGE_ICON, layout="wide")
inject_base_style()

st.title("🏢 Organigramme de l'AER — référentiel de routage")
st.caption("Structure réelle utilisée pour proposer les services émetteurs/destinataires dans le registre "
           "et le journal de transmissions — d'après l'organigramme officiel « AER 2025 » et le descriptif "
           "du fonctionnement des directions fourni.")

with st.expander("ℹ️ Deux réserves honnêtes sur cette structure", expanded=False):
    st.markdown(
        """
- Le document source liste deux fois **« Service des Marchés »** (sous la Sous-Direction des Affaires
  Administratives, et sous celle des Ressources Humaines) — reproduit tel quel ici, sans correction de
  notre part : c'est peut-être une redite dans le texte d'origine, ou deux services distincts portant le
  même nom dans deux sous-directions différentes ; sans confirmation de l'AER, nous ne tranchons pas.
- La légende de l'organigramme officiel annonce **5 Directions, 17 Sous-Directions, 27 Services**. En
  aplatissant la liste du texte fourni, notre décompte peut différer légèrement (voir ci-dessous) — les
  organes de gouvernance (Conseil d'Administration, Cabinet du PCA, Conseiller technique) ne sont pas
  nécessairement comptés de la même façon d'un document à l'autre. Nous affichons les deux décomptes
  plutôt que d'en forcer un.
        """
    )

section_title("DÉCOMPTE — LÉGENDE OFFICIELLE VS. STRUCTURE DÉTAILLÉE FOURNIE")
rows = hierarchy_rows()
df_rows = pd.DataFrame(rows)
decompte_detail = {
    "Direction Générale": 1,
    "Directions centrales (texte détaillé)": len([r for r in rows if r["Niveau"] == "Direction centrale"]),
    "Sous-directions (texte détaillé)": len([r for r in rows if r["Niveau"] == "Sous-direction"]),
    "Services (texte détaillé, hors doublons)": len(set(
        r["Entité"].split(" (")[0] for r in rows if r["Niveau"] == "Service"
    )),
}
c1, c2 = st.columns(2)
with c1:
    st.markdown("**Légende de l'organigramme officiel**")
    st.table(pd.DataFrame(LEGENDE_ORGANIGRAMME.items(), columns=["Élément", "Nombre annoncé"]))
with c2:
    st.markdown("**Décompte à partir du texte détaillé fourni**")
    st.table(pd.DataFrame(decompte_detail.items(), columns=["Élément", "Nombre obtenu"]))

st.write("")
section_title("HIÉRARCHIE COMPLÈTE (GRAPHIQUE)")
labels = [DIRECTION_GENERALE] + [r["Entité"] for r in rows if r["Entité"] != DIRECTION_GENERALE]
parents = [""] + [r["Parent"] for r in rows if r["Entité"] != DIRECTION_GENERALE]

fig = go.Figure(go.Icicle(
    labels=labels,
    parents=parents,
    root_color="lightgrey",
))
fig.update_layout(title="Organigramme AER — Direction Générale, directions, sous-directions, services")
fig = plotly_base_layout(fig, height=620, legend=False)
st.plotly_chart(fig, use_container_width=True)

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
