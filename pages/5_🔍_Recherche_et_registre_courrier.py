from datetime import date

import pandas as pd
import streamlit as st

from utils.ui import PAGE_ICON, inject_base_style, section_title, kpi_row, render_sidebar_footer
from utils.dossiers import get_register, with_derived_columns, CANAL_COURRIER
from utils.transmissions import get_log
from utils.session import current_post_selector

st.set_page_config(page_title="Recherche & registre du courrier — AER", page_icon=PAGE_ICON, layout="wide")
inject_base_style()

poste_courant = current_post_selector()

st.title("🔍 Recherche & registre du courrier")
st.caption(
    "Deux fonctions inspirées de ce que propose Maarch Courrier (recherche plein texte, registre "
    "chronologique du courrier) — mais **implémentées nativement ici, sans aucune connexion à Maarch ni à "
    "un autre système**. Rien n'est interrogé à l'extérieur de cette application."
)

register = with_derived_columns(get_register())
log = get_log()

# =====================================================================
# Recherche plein texte
# =====================================================================
section_title("🔎 RECHERCHE PLEIN TEXTE")
st.caption("Cherche dans le registre (objet, agent, notes, référence externe) et dans les commentaires "
           "du journal des transmissions.")

requete = st.text_input("Rechercher", key="recherche_globale", placeholder="Ex. : nom d'agent, mot-clé, référence...")

if not requete:
    st.info("Saisissez un mot-clé ci-dessus pour lancer la recherche.")
else:
    if register.empty:
        matches_reg = register
    else:
        champs = ["N° dossier", "Objet", "Agent en charge", "Notes", "Référence externe (optionnel)",
                  "Service destinataire actuel", "Direction concernée"]
        mask = pd.Series(False, index=register.index)
        for champ in champs:
            if champ in register.columns:
                mask = mask | register[champ].astype(str).str.contains(requete, case=False, na=False)
        matches_reg = register[mask]

    if log.empty:
        matches_log = log
    else:
        mask_log = log["Commentaire"].astype(str).str.contains(requete, case=False, na=False)
        matches_log = log[mask_log]

    kpi_row([
        ("Dossiers correspondants", str(len(matches_reg)), None),
        ("Transmissions correspondantes", str(len(matches_log)), None),
    ])

    if not matches_reg.empty:
        st.markdown("**Dossiers**")
        st.dataframe(
            matches_reg[["N° dossier", "Objet", "Type de dossier", "Direction concernée",
                         "Service destinataire actuel", "Statut", "Référence externe (optionnel)",
                         "Agent en charge"]],
            use_container_width=True, hide_index=True,
        )
    if not matches_log.empty:
        st.markdown("**Transmissions (commentaires)**")
        st.dataframe(matches_log, use_container_width=True, hide_index=True)
    if matches_reg.empty and matches_log.empty:
        st.warning("Aucun résultat pour cette recherche.")

st.write("")

# =====================================================================
# Registre chronologique du courrier (bureau d'ordre)
# =====================================================================
section_title("📖 REGISTRE CHRONOLOGIQUE DU COURRIER (BUREAU D'ORDRE)")
st.caption(
    f"Liste, dans l'ordre d'arrivée, des dossiers reçus par le « {CANAL_COURRIER} » — l'équivalent d'un "
    "registre papier de bureau d'ordre, mais tenu automatiquement à partir du canal de réception saisi "
    "sur la page Registre."
)

if register.empty:
    st.info("Aucun dossier enregistré pour l'instant.")
else:
    courrier_view = register[register.get("Canal de réception") == CANAL_COURRIER].copy()
    if courrier_view.empty:
        st.info(f"Aucun dossier n'a encore été enregistré avec le canal « {CANAL_COURRIER} ».")
    else:
        courrier_view = courrier_view.sort_values("Date de réception").reset_index(drop=True)
        courrier_view.insert(0, "N° d'ordre", range(1, len(courrier_view) + 1))
        colonnes = ["N° d'ordre", "Date de réception", "N° dossier", "Objet", "Type de dossier",
                    "Référence externe (optionnel)", "Direction concernée", "Service destinataire actuel",
                    "Statut", "Agent en charge"]
        st.dataframe(courrier_view[colonnes], use_container_width=True, hide_index=True, height=420)
        st.download_button(
            "⬇️ Télécharger le registre du courrier (CSV)",
            courrier_view[colonnes].to_csv(index=False).encode("utf-8"),
            f"registre_courrier_aer_{date.today().isoformat()}.csv", "text/csv",
        )

with st.expander("ℹ️ Ce que cette page ne fait pas", expanded=False):
    st.markdown(
        """
- Elle **ne se connecte à aucun système externe** (ni Maarch Courrier, ni AIGLES, ni PATRIMOINE, ni
  SYSTAC/SYGMA, ni SIGEC) : la recherche et le registre ne portent que sur les données saisies dans cette
  application.
- Le champ « Référence externe » sur un dossier est une **note libre**, saisie manuellement par
  l'utilisateur — elle n'est ni vérifiée ni synchronisée avec quoi que ce soit.
        """
    )

render_sidebar_footer()
