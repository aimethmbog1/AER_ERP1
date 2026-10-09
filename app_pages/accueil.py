from datetime import date

import pandas as pd
import streamlit as st

from utils.ui import (
    APP_TITLE, APP_SUBTITLE, ASSETS_DIR, inject_base_style, section_title, kpi_row,
    render_sidebar_footer, render_page_header, render_hero_illustration, live_dot, theme_palette,
    status_badge,
)
from utils.dossiers import get_register, with_derived_columns, STATUTS_CLOS
from utils.transmissions import get_log
from utils.search import search_dossiers
from utils.workflow import get_approbations, STATUT_EN_ATTENTE
from utils.notifications import worklist_for
from utils.session import current_post_selector
from utils.backup import build_backup_json, restore_backup_json
from utils.exports import build_excel_export

inject_base_style()

poste_courant = current_post_selector()

render_page_header("🏠", APP_TITLE, APP_SUBTITLE)
render_hero_illustration()

# =====================================================================
# Recherche globale — inspirée de la recherche globale d'Oracle Cloud ERP,
# accessible depuis l'accueil plutôt que depuis un seul module dédié. Même
# logique que la page Recherche & registre courrier (voir utils/search.py) ;
# un résultat ouvre directement la Fiche dossier (vue 360°).
# =====================================================================
_recherche_rapide = st.text_input(
    "🔎 Recherche globale", key="accueil_recherche_globale", placeholder=(
        "Rechercher un dossier par objet, agent, référence externe, service destinataire..."
    ),
)
if _recherche_rapide:
    _resultats = search_dossiers(with_derived_columns(get_register()), _recherche_rapide)
    if _resultats.empty:
        st.warning("Aucun dossier ne correspond à cette recherche.")
    else:
        st.caption(f"{len(_resultats)} résultat(s)")
        for _, _r in _resultats.head(8).iterrows():
            with st.container(border=True):
                rc1, rc2 = st.columns([5, 1])
                rc1.markdown(
                    f"**{_r['N° dossier']}** — {_r['Objet']}  \n"
                    f"<span style='font-size:0.82rem;opacity:0.8;'>{_r['Service destinataire actuel']} · "
                    f"{_r['Direction concernée']}</span> &nbsp; {status_badge(_r['Statut'])}",
                    unsafe_allow_html=True,
                )
                if rc2.button("Ouvrir →", key=f"accueil_search_open_{_r['N° dossier']}"):
                    st.session_state["_fiche_dossier_numero"] = _r["N° dossier"]
                    st.switch_page("app_pages/fiche_dossier.py")
        if len(_resultats) > 8:
            st.caption(f"… et {len(_resultats) - 8} de plus — affinez la recherche, ou utilisez la page "
                       "**Recherche & registre courrier** pour la liste complète.")
    st.write("")

# =====================================================================
# Mes tâches en attente — liste de travail personnelle inspirée du
# « Worklist » d'Oracle Cloud ERP : ce qui attend une décision ou une action
# du poste actuellement simulé, calculé à la volée (voir
# utils/notifications.py — mêmes données que la cloche de la barre
# latérale, présentées ici en plus grand sur la page d'accueil).
# =====================================================================
if poste_courant:
    _taches = worklist_for(poste_courant, with_derived_columns(get_register()))
    section_title(f"📋 MES TÂCHES EN ATTENTE — {poste_courant}")
    if not _taches:
        st.success("Aucune tâche en attente pour ce poste : rien en retard, aucune échéance proche, "
                   "aucune approbation à décider.")
    else:
        _icone_gravite = {"approbation": "✅", "retard": "⚠️", "echeance": "⏳"}
        for _i, _n in enumerate(_taches[:6]):
            with st.container(border=True):
                tc1, tc2 = st.columns([5, 1])
                tc1.markdown(f"{_icone_gravite.get(_n.gravite, '🔔')} **{_n.titre}**  \n"
                             f"<span style='font-size:0.82rem;opacity:0.8;'>{_n.detail}</span>",
                             unsafe_allow_html=True)
                if _n.numero_dossier and tc2.button("Ouvrir →", key=f"accueil_tache_{_i}_{_n.numero_dossier}"):
                    st.session_state["_fiche_dossier_numero"] = _n.numero_dossier
                    st.switch_page("app_pages/fiche_dossier.py")
        if len(_taches) > 6:
            st.caption(f"… et {len(_taches) - 6} tâche(s) de plus — voir la cloche 🔔 dans la barre latérale "
                       "pour la liste complète.")
    st.write("")
else:
    st.info("💡 Sélectionnez un poste dans la barre latérale (« Se positionner comme poste ») pour voir "
            "ici votre liste personnelle de tâches en attente (dossiers en retard, échéances proches, "
            "approbations à décider).")
    st.write("")

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
- Une **recherche plein texte** (y compris depuis cette page d'accueil) et un **registre chronologique du
  courrier** (page dédiée), et des **pièces jointes** (scans) par dossier.
- Un **workflow d'approbation formalisé** (page *Fiche dossier*) : une étape peut attendre une décision
  explicite (Approuvé / Rejeté) d'un poste précis, avec délégation possible — en complément, et non à la
  place, du routage par transmission. Inspiré du moteur de workflow d'Oracle Cloud ERP.
- Un **centre de notifications personnel** (cloche 🔔 dans la barre latérale, et section « Mes tâches en
  attente » sur cette page) : dossiers en retard, échéances proches et approbations à décider pour le poste
  sélectionné — calculé à la volée, rien à synchroniser.
- Une **fiche dossier** (vue 360°) qui rassemble, pour un seul dossier, son identité, son workflow
  d'approbation, son historique de transmissions et son journal d'audit complet.
- Une simulation de poste (barre latérale) pour filtrer l'affichage sur « mes » dossiers.

**Ce que l'outil n'est pas :**
- Un accès à de vrais dossiers de l'AER : les 300 dossiers visibles au premier démarrage sont un
  **jeu de démonstration réaliste**, pas de vraies archives — voir la page **Paramètres & thème** pour
  repartir d'une base vide si vous préférez.
- Une connexion réelle à AIGLES, PATRIMOINE, SYSTAC/SYGMA, SIGEC ou Maarch Courrier : ces systèmes de
  l'État camerounais ne sont ni accessibles ni interrogés par cette application. Elle s'en inspire pour
  certaines fonctions génériques et honnêtement réalisables (registre du courrier, recherche plein texte,
  pièces jointes, champ de référence externe), sans prétendre s'y interfacer — voir le README pour le
  détail de cette distinction.
- Un système avec authentification réelle : le sélecteur de poste est une commodité d'usage, pas un
  contrôle d'accès.
- Un système multi-serveurs : les données sont partagées entre tous les utilisateurs connectés au **même**
  serveur (voir `utils/db.py`) ; exportez une sauvegarde JSON ci-dessous si votre hébergement ne garantit
  pas un disque persistant (c'est le cas de Streamlit Community Cloud).
        """
    )

st.image(
    str(ASSETS_DIR / "photos" / "installation_solaire_pexels.jpg"),
    use_container_width=True,
    caption="Illustration générique — photo libre de droits (Pexels, photographe Cristian Rojas) : "
            "ce n'est pas un site de l'AER, seulement un visuel d'ambiance pour l'application.",
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

section_title(("VUE D'ENSEMBLE" + (f" — POSTE : {poste_courant}" if poste_courant else "")))
view = register
if poste_courant:
    view = register[register["Service destinataire actuel"] == poste_courant]

if register.empty:
    st.info("Aucun dossier enregistré pour l'instant. Rendez-vous sur la page **Registre des dossiers** "
            "pour commencer à en ajouter, ou restaurez une sauvegarde JSON ci-dessous.")
else:
    nb_actifs = int((~view["Statut"].isin(STATUTS_CLOS)).sum())
    nb_retard = int(view["En retard"].sum())
    nb_clos = int(view["Statut"].isin(STATUTS_CLOS).sum())
    appr_attente = get_approbations(approbateur=poste_courant, statut=STATUT_EN_ATTENTE) if poste_courant \
        else get_approbations(statut=STATUT_EN_ATTENTE)
    st.markdown(f"{live_dot()}<span style='font-size:0.85rem;color:{theme_palette()['text_muted']};'>"
                "Indicateurs calculés en direct à partir du registre partagé</span>", unsafe_allow_html=True)
    kpi_row([
        ("Dossiers" + (" à ce poste" if poste_courant else " au total"), str(len(view)), None),
        ("Dossiers actifs", str(nb_actifs), None),
        ("En retard", str(nb_retard), None),
        ("Traités / archivés", str(nb_clos), None),
        ("Approbations en attente" + (" (ce poste)" if poste_courant else ""), str(len(appr_attente)), None),
        ("Mouvements enregistrés", str(len(log)), None),
    ], icons=["📁", "🗂️", "🔴", "✅", "🖊️", "🔁"])

    st.write("")
    st.markdown("**Dossiers en retard** (échéance dépassée, non clôturés)")
    retard_view = view[view["En retard"]].sort_values("Jours de retard", ascending=False)
    if retard_view.empty:
        st.success("Aucun dossier en retard parmi ceux affichés.")
    else:
        st.dataframe(
            retard_view[["N° dossier", "Objet", "Direction concernée", "Service destinataire actuel",
                         "Statut", "Échéance prévue", "Jours de retard", "Agent en charge"]],
            width='stretch', hide_index=True,
            column_config={
                "Échéance prévue": st.column_config.DateColumn("Échéance prévue"),
                "Jours de retard": st.column_config.ProgressColumn(
                    "Jours de retard", min_value=0,
                    max_value=max(1, int(retard_view["Jours de retard"].max())), format="%d j",
                ),
            },
        )

    st.write("")
    st.markdown("**⏰ Rappels — échéances à venir (7 jours), non clôturés et pas déjà en retard**")
    today_ts = pd.Timestamp(date.today())
    a_venir = view[
        (~view["Statut"].isin(STATUTS_CLOS)) & (~view["En retard"]) &
        view["Échéance prévue"].notna() &
        ((view["Échéance prévue"] - today_ts).dt.days.between(0, 7))
    ].copy()
    if a_venir.empty:
        st.caption("Aucune échéance dans les 7 prochains jours parmi les dossiers affichés.")
    else:
        a_venir["Jours restants"] = (a_venir["Échéance prévue"] - today_ts).dt.days
        st.dataframe(
            a_venir.sort_values("Jours restants")[
                ["N° dossier", "Objet", "Service destinataire actuel", "Échéance prévue",
                 "Jours restants", "Agent en charge"]],
            width='stretch', hide_index=True,
            column_config={"Échéance prévue": st.column_config.DateColumn("Échéance prévue")},
        )

st.write("")
st.markdown(
    "Naviguez via le menu de gauche : **Registre des dossiers** (saisie et suivi), "
    "**Transmissions & traçabilité** (mouvements entre services, graphe avec voyants), "
    "**Tableau de bord** (indicateurs), **Organigramme** (référentiel des services)."
)

st.write("")
section_title("SAUVEGARDE / RESTAURATION, ET EXPORT DE PARTAGE")
bc1, bc2 = st.columns(2)
with bc1:
    st.download_button(
        "💾 Télécharger une sauvegarde complète (JSON)",
        build_backup_json().encode("utf-8"),
        f"sauvegarde_suivi_dossiers_aer_{date.today().isoformat()}.json",
        "application/json",
    )
    st.caption("Format machine, ré-importable ci-contre : registre, journal des transmissions ET "
               "pièces jointes, en un seul fichier. Depuis l'ajout du stockage partagé, ce n'est plus "
               "l'unique moyen de ne rien perdre — c'est désormais le filet de sécurité ultime, utile "
               "surtout si l'hébergement choisi ne garantit pas un disque persistant.")
    st.download_button(
        "📊 Télécharger un export Excel (lecture seule, partage/impression)",
        build_excel_export(),
        f"export_suivi_dossiers_aer_{date.today().isoformat()}.xlsx",
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )
    st.caption("Registre, transmissions, pièces jointes (métadonnées) et journal d'audit, chacun sur "
               "sa propre feuille — pratique pour partager un instantané à la hiérarchie sans donner "
               "accès à l'application elle-même. Non ré-importable (contrairement à la sauvegarde JSON).")
with bc2:
    up = st.file_uploader("📤 Restaurer une sauvegarde (JSON)", type=["json"], key="backup_upload")
    if up is not None:
        if st.button("Restaurer cette sauvegarde (remplace les données actuelles)", type="primary"):
            st.session_state["_pending_restore"] = up.getvalue().decode("utf-8")
            st.rerun()

if st.session_state.get("_pending_restore"):
    @st.dialog("Confirmer la restauration")
    def _confirm_restore():
        st.warning("Cette action **remplace intégralement** le registre, le journal des transmissions, les "
                   "pièces jointes et les demandes d'approbation actuels par le contenu du fichier chargé. "
                   "Cette opération est irréversible (sauf à restaurer une sauvegarde plus récente par la "
                   "suite).")
        cc1, cc2 = st.columns(2)
        if cc1.button("Oui, remplacer les données", type="primary", width='stretch'):
            try:
                n_reg, n_log, n_pj, n_appr = restore_backup_json(st.session_state.pop("_pending_restore"))
                st.toast(f"Restauré : {n_reg} dossier(s), {n_log} transmission(s), {n_pj} pièce(s) jointe(s), "
                         f"{n_appr} approbation(s).", icon="✅")
                st.balloons()
                st.rerun()
            except Exception as exc:  # noqa: BLE001
                st.session_state.pop("_pending_restore", None)
                st.error(f"Fichier de sauvegarde illisible : {exc}")
        if cc2.button("Annuler", width='stretch'):
            st.session_state.pop("_pending_restore", None)
            st.rerun()

    _confirm_restore()

render_sidebar_footer()
