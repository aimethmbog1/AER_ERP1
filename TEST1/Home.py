import streamlit as st

from utils.ui import APP_TITLE, PAGE_ICON, inject_base_style, section_title, kpi_row, render_sidebar_footer
from utils.dossiers import get_register, with_derived_columns, STATUTS_CLOS
from utils.transmissions import get_log

st.set_page_config(page_title=APP_TITLE, page_icon=PAGE_ICON, layout="wide")
inject_base_style()

st.title(f"{PAGE_ICON} {APP_TITLE}")
st.caption("Prototype de digitalisation du suivi des dossiers — Agence de l'Électrification Rurale (AER)")

with st.expander("ℹ️ À propos de cette application — à lire avant de l'utiliser", expanded=True):
    st.markdown(
        """
Cette application répond au constat posé dans le diagnostic (questionnaire + diagramme d'Ishikawa) :
**« Insuffisance de digitalisation et de centralisation des processus internes de l'A.E.R »**, avec pour
conséquences des difficultés de traçabilité, des retards de traitement, une dispersion de l'information
(WhatsApp, papier, Excel), et un manque de coordination entre entités.

**Ce que l'outil fait réellement :**
- Un **registre de dossiers** générique (tout type : courrier, projet, marché, RH...), avec statut,
  échéance et service destinataire — pour remplacer les tableaux Excel/Word dispersés par une source unique.
- Un **journal des transmissions** entre services, pour reconstituer le trajet réel d'un dossier et
  mesurer le temps passé à chaque étape — la traçabilité que le diagnostic identifie comme manquante.
- Le **routage entre services s'appuie sur l'organigramme réel de l'AER** (Direction Générale, DECDP,
  DGOER, DAAF, leurs sous-directions et services, et les 4 antennes régionales), pas sur une liste inventée.

**Ce que l'outil n'est pas :**
- Un accès à de vrais dossiers de l'AER : aucune donnée n'est préchargée — c'est un **prototype à
  alimenter**, à tester avec des cas réels ou fictifs selon vos besoins de démonstration.
- Une base de données persistante entre sessions : Streamlit ne conserve rien après fermeture. Pensez à
  **exporter vos registres en CSV** régulièrement et à les recharger à la prochaine session.
        """
    )

register = with_derived_columns(get_register())
log = get_log()

section_title("VUE D'ENSEMBLE")
if register.empty:
    st.info("Aucun dossier enregistré pour l'instant. Rendez-vous sur la page **📂 Registre des dossiers** "
            "pour commencer à en ajouter, ou chargez un registre CSV précédemment exporté.")
else:
    nb_actifs = int((~register["Statut"].isin(STATUTS_CLOS)).sum())
    nb_retard = int(register["En retard"].sum())
    nb_clos = int(register["Statut"].isin(STATUTS_CLOS).sum())
    kpi_row([
        ("Dossiers au total", str(len(register)), None),
        ("Dossiers actifs", str(nb_actifs), None),
        ("En retard", str(nb_retard), None),
        ("Traités / archivés", str(nb_clos), None),
        ("Mouvements enregistrés", str(len(log)), None),
    ])

    st.write("")
    st.markdown("**Dossiers en retard** (échéance dépassée, non clôturés)")
    retard_view = register[register["En retard"]].sort_values("Jours de retard", ascending=False)
    if retard_view.empty:
        st.success("Aucun dossier en retard parmi ceux enregistrés.")
    else:
        st.dataframe(
            retard_view[["N° dossier", "Objet", "Direction concernée", "Service destinataire actuel",
                         "Statut", "Échéance prévue", "Jours de retard", "Agent en charge"]],
            use_container_width=True, hide_index=True,
        )

st.write("")
st.markdown(
    "Naviguez via le menu de gauche : **📂 Registre des dossiers** (saisie et suivi), "
    "**🔀 Transmissions & traçabilité** (mouvements entre services), "
    "**📊 Tableau de bord** (indicateurs), **🏢 Organigramme** (référentiel des services)."
)

render_sidebar_footer()
