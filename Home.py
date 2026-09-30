from datetime import date

import streamlit as st

from utils.ui import APP_TITLE, PAGE_ICON, inject_base_style, section_title, kpi_row, render_sidebar_footer
from utils.dossiers import get_register, with_derived_columns, STATUTS_CLOS
from utils.transmissions import get_log
from utils.session import current_post_selector
from utils.backup import build_backup_json, restore_backup_json

st.set_page_config(page_title=APP_TITLE, page_icon=PAGE_ICON, layout="wide")
inject_base_style()

poste_courant = current_post_selector()

st.title(f"{PAGE_ICON} {APP_TITLE}")
st.caption("Prototype de digitalisation du suivi des dossiers — Agence de l'Électrification Rurale (AER)")

with st.expander("ℹ️ À propos de cette application — à lire avant de l'utiliser", expanded=False):
    st.markdown(
        """
Cette application répond au constat posé dans le diagnostic (questionnaire + diagramme d'Ishikawa) :
**« Insuffisance de digitalisation et de centralisation des processus internes de l'A.E.R »**, avec pour
conséquences des difficultés de traçabilité, des retards de traitement, une dispersion de l'information
(WhatsApp, papier, Excel), et un manque de coordination entre entités.

**Ce que l'outil fait réellement :**
- Un **registre de dossiers** générique (tout type : courrier, projet, marché, RH, comptable, état
  civil...), avec statut, échéance et service destinataire.
- Un **circuit d'entrée conforme au fonctionnement réel** : un dossier entrant est reçu par défaut par le
  **Service du Courrier, de la Liaison et des Archives**, qui l'achemine ensuite vers le poste concerné —
  ce service a, dans l'application, le droit d'acheminer vers n'importe quel poste (exception assumée à la
  règle générale de routage), exactement comme un bureau d'ordre réel.
- Un **journal des transmissions** entre services, avec un **routage contraint par l'organigramme réel**
  (un dossier ne peut être transmis qu'à un palier directement inférieur, à un poste de même rang, ou en
  retour vers l'émetteur — jamais en sautant des niveaux, sauf depuis le service courrier), et un **graphe
  avec voyants de statut** (vert / jaune / rouge) montrant en temps réel où se trouvent les dossiers en
  attente ou en retard.
- Une **recherche plein texte** et un **registre chronologique du courrier** (page dédiée), et des
  **pièces jointes** (scans) par dossier.
- Une simulation de poste (barre latérale) pour filtrer l'affichage sur « mes » dossiers.

**Ce que l'outil n'est pas :**
- Un accès à de vrais dossiers de l'AER : aucune donnée n'est préchargée — c'est un **prototype à
  alimenter**.
- Une connexion réelle à AIGLES, PATRIMOINE, SYSTAC/SYGMA, SIGEC ou Maarch Courrier : ces systèmes de
  l'État camerounais ne sont ni accessibles ni interrogés par cette application. Elle s'en inspire pour
  certaines fonctions génériques et honnêtement réalisables (registre du courrier, recherche plein texte,
  pièces jointes, champ de référence externe), sans prétendre s'y interfacer — voir le README pour le
  détail de cette distinction.
- Un système avec authentification réelle : le sélecteur de poste est une commodité d'usage, pas un
  contrôle d'accès.
- Une base de données persistante entre sessions : **exportez une sauvegarde complète (JSON)** ci-dessous
  avant de fermer, et rechargez-la à la reprise.
        """
    )

register = with_derived_columns(get_register())
log = get_log()

if not register.empty:
    nb_retard_total = int(register["En retard"].sum())
    nb_proche_total = int(register["Échéance proche"].sum())
    if nb_retard_total:
        st.error(f"⚠️ {nb_retard_total} dossier(s) en retard sur l'échéance prévue — voir le détail ci-dessous "
                 "ou sur le Tableau de bord.")
    if nb_proche_total:
        st.warning(f"⏳ {nb_proche_total} dossier(s) arrivent à échéance dans 3 jours ou moins.")

section_title("VUE D'ENSEMBLE" + (f" — POSTE : {poste_courant}" if poste_courant else ""))
view = register
if poste_courant:
    view = register[register["Service destinataire actuel"] == poste_courant]

if register.empty:
    st.info("Aucun dossier enregistré pour l'instant. Rendez-vous sur la page **📂 Registre des dossiers** "
            "pour commencer à en ajouter, ou restaurez une sauvegarde JSON ci-dessous.")
else:
    nb_actifs = int((~view["Statut"].isin(STATUTS_CLOS)).sum())
    nb_retard = int(view["En retard"].sum())
    nb_clos = int(view["Statut"].isin(STATUTS_CLOS).sum())
    kpi_row([
        ("Dossiers" + (" à ce poste" if poste_courant else " au total"), str(len(view)), None),
        ("Dossiers actifs", str(nb_actifs), None),
        ("En retard", str(nb_retard), None),
        ("Traités / archivés", str(nb_clos), None),
        ("Mouvements enregistrés", str(len(log)), None),
    ])

    st.write("")
    st.markdown("**Dossiers en retard** (échéance dépassée, non clôturés)")
    retard_view = view[view["En retard"]].sort_values("Jours de retard", ascending=False)
    if retard_view.empty:
        st.success("Aucun dossier en retard parmi ceux affichés.")
    else:
        st.dataframe(
            retard_view[["N° dossier", "Objet", "Direction concernée", "Service destinataire actuel",
                         "Statut", "Échéance prévue", "Jours de retard", "Agent en charge"]],
            use_container_width=True, hide_index=True,
        )

st.write("")
st.markdown(
    "Naviguez via le menu de gauche : **📂 Registre des dossiers** (saisie et suivi), "
    "**🔀 Transmissions & traçabilité** (mouvements entre services, graphe avec voyants), "
    "**📊 Tableau de bord** (indicateurs), **🏢 Organigramme** (référentiel des services)."
)

st.write("")
section_title("SAUVEGARDE / RESTAURATION COMPLÈTE DE LA SESSION")
bc1, bc2 = st.columns(2)
with bc1:
    st.download_button(
        "💾 Télécharger une sauvegarde complète (JSON)",
        build_backup_json().encode("utf-8"),
        f"sauvegarde_suivi_dossiers_aer_{date.today().isoformat()}.json",
        "application/json",
    )
    st.caption("Contient le registre des dossiers, le journal des transmissions ET les pièces jointes "
               "éventuelles, en un seul fichier.")
with bc2:
    up = st.file_uploader("📤 Restaurer une sauvegarde (JSON)", type=["json"], key="backup_upload")
    if up is not None:
        if st.button("Restaurer cette sauvegarde (remplace les données actuelles)"):
            try:
                n_reg, n_log, n_pj = restore_backup_json(up.getvalue().decode("utf-8"))
                st.success(f"Restauré : {n_reg} dossier(s), {n_log} transmission(s), {n_pj} pièce(s) jointe(s).")
                st.rerun()
            except Exception as exc:  # noqa: BLE001
                st.error(f"Fichier de sauvegarde illisible : {exc}")

render_sidebar_footer()
