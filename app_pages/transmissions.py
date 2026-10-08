from datetime import date

import pandas as pd
import plotly.express as px
import streamlit as st

from utils.ui import (
    inject_base_style, section_title, plotly_base_layout, theme_palette,
    render_sidebar_footer, render_page_header, status_badge,
)
from utils.dossiers import get_register, update_service_destinataire
from utils.transmissions import (
    get_log, set_log, add_transmission, history_for, temps_par_service,
    suggested_return_target, generer_bordereau,
)
from utils.orgchart import allowed_destinations, all_node_ids, depth_of, NODES
from utils.session import current_post_selector
from utils import db

inject_base_style()

poste_courant = current_post_selector()

render_page_header("🔀", "Transmissions & traçabilité",
                    "Journal des mouvements d'un dossier entre services, avec un routage contraint par "
                    "l'organigramme réel — la traçabilité que le diagnostic identifie comme manquante.")

with st.expander("ℹ️ Règle de routage appliquée", expanded=False):
    st.markdown(
        """
Depuis un poste donné, un dossier ne peut être transmis qu'à :
- un poste **directement subordonné** (descente hiérarchique) ;
- un poste de **même rang** (transmission latérale entre pairs, ex. entre deux directeurs de
  département, ou entre deux chefs de service de directions différentes) ;
- le **supérieur hiérarchique direct** (remontée, ou retour vers l'émetteur) ;
- l'**extérieur de l'AER** (tout poste peut correspondre avec l'extérieur).

Impossible de sauter un niveau (ex. transmettre directement de la Direction Générale à un chef de
service sans passer par le directeur concerné, sauf pour les services rattachés directement à la DG,
qui sont ses subordonnés directs).

**Exception assumée — le Service du Courrier, de la Liaison et des Archives** : conformément au circuit
réel (« les dossiers entrants passent par le service courrier et celui-ci achemine vers les postes
concernés »), ce service peut transmettre vers **n'importe quel poste**, quel que soit son rang. Un
dossier externe arrive d'ailleurs par défaut à ce service (voir page Registre, section « Nouveau
dossier ») plutôt que directement à la Direction Générale.
        """
    )

register = get_register()

if register.empty:
    st.info("Enregistrez d'abord au moins un dossier sur la page **Registre des dossiers** avant de "
            "pouvoir tracer ses transmissions.")
    st.stop()

dossier_options = (register["N° dossier"] + " — " + register["Objet"].astype(str)).tolist()

# =====================================================================
# Enregistrer une transmission
# =====================================================================
st.markdown("**➕ Enregistrer une transmission**")
with st.container(border=True):
    choix = st.selectbox("Dossier concerné", dossier_options, key="trans_dossier")
    dossier_id = choix.split(" — ")[0]
    dossier_row = register[register["N° dossier"] == dossier_id].iloc[0]
    poste_actuel_dossier = dossier_row["Service destinataire actuel"]

    st.markdown(f"Poste actuel de ce dossier : **{poste_actuel_dossier}**  "
                f"{status_badge(dossier_row['Statut'])}", unsafe_allow_html=True)

    tc1, tc2 = st.columns(2)
    t_source = tc1.selectbox(
        "Service source (poste qui transmet)", all_node_ids(),
        index=all_node_ids().index(poste_actuel_dossier) if poste_actuel_dossier in all_node_ids() else 0,
        key="trans_source",
    )
    destinations = allowed_destinations(t_source)
    retour_cible = suggested_return_target(dossier_id)

    retour_disponible = retour_cible in destinations if retour_cible else False
    use_retour = False
    if retour_disponible:
        use_retour = st.checkbox(
            f"🔁 Retourner à l'émetteur précédent ({retour_cible}) après traitement", value=False,
            key="trans_use_retour",
        )

    if use_retour:
        t_dest = retour_cible
        tc2.selectbox("Service destination", [retour_cible], index=0, disabled=True, key="trans_dest_locked")
    else:
        if not destinations:
            tc2.warning("Aucune destination disponible depuis ce poste.")
            t_dest = None
        else:
            t_dest = tc2.selectbox("Service destination (postes autorisés uniquement)", destinations,
                                    key="trans_dest")

    tc3, tc4, tc5 = st.columns(3)
    t_date = tc3.date_input("Date de la transmission", value=date.today(), key="trans_date")
    with tc4:
        t_delai_actif = st.checkbox("Fixer un délai imparti", value=False, key="trans_delai_actif")
        t_delai = st.number_input("Délai (jours)", min_value=1, step=1, value=5, key="trans_delai",
                                   disabled=not t_delai_actif,
                                   help="Désactivé par défaut : aucun délai n'est alors enregistré, plutôt "
                                        "qu'un délai de 0 jour qui serait ambigu.")
    t_agent_dest = tc5.text_input("Agent destinataire (optionnel)", key="trans_agent_dest")
    t_commentaire = st.text_input("Commentaire (motif, pièce jointe, instruction...)", key="trans_commentaire")

    if st.button("Enregistrer la transmission", type="primary", disabled=(t_dest is None)):
        ok, message = add_transmission(
            dossier_id, t_date, t_source, t_dest, t_commentaire,
            delai_impartis_jours=(int(t_delai) if t_delai_actif else None),
        )
        if ok:
            update_service_destinataire(dossier_id, t_dest)
            st.toast(message, icon="✅")
            st.session_state["last_bordereau"] = generer_bordereau(
                dossier_id, dossier_row["Objet"], t_source, t_dest, t_date, t_commentaire, t_agent_dest,
            )
            st.rerun()
        else:
            st.error(message)

if st.session_state.get("last_bordereau"):
    st.download_button("📄 Télécharger le bordereau de transmission (dernier mouvement)",
                        st.session_state["last_bordereau"].encode("utf-8"),
                        f"bordereau_{dossier_id}_{date.today().isoformat()}.txt", "text/plain")

st.write("")
section_title("HISTORIQUE ET FRISE CHRONOLOGIQUE D'UN DOSSIER")
hist_choice = st.selectbox("Voir l'historique de :", dossier_options, key="hist_dossier")
hist_id = hist_choice.split(" — ")[0]
hist = history_for(hist_id)
if hist.empty:
    st.info("Aucune transmission enregistrée pour ce dossier pour l'instant.")
else:
    st.dataframe(hist, width='stretch', hide_index=True,
                 column_config={"Date": st.column_config.DateColumn("Date")})

    today = pd.Timestamp(pd.Timestamp.now().date())
    frise = hist.sort_values("Date").reset_index(drop=True)
    segments = []
    for i, r in frise.iterrows():
        fin = frise.loc[i + 1, "Date"] if i + 1 < len(frise) else today
        segments.append({"Service": r["Service destination"], "Début": r["Date"], "Fin": fin, "Sens": r["Sens"]})
    seg_df = pd.DataFrame(segments)
    p = theme_palette()
    fig = px.timeline(seg_df, x_start="Début", x_end="Fin", y="Service", color="Sens",
                       color_discrete_map={"Aller": p["navy"], "Retour": p["amber"]},
                       title=f"Trajet du dossier {hist_id} entre services")
    fig.update_yaxes(autorange="reversed")
    fig = plotly_base_layout(fig, height=max(220, 60 * len(seg_df)))
    st.plotly_chart(fig, width='stretch')

st.write("")
section_title("JOURNAL COMPLET DES TRANSMISSIONS")
log = get_log()
if log.empty:
    st.info("Le journal est vide pour l'instant.")
else:
    lc1, rc1 = st.columns([1.3, 1])
    with lc1:
        edited_log = st.data_editor(
            log, width='stretch', hide_index=True, num_rows="dynamic",
            height=min(60 + 36 * (len(log) + 1), 420),
            column_config={
                "Date": st.column_config.DateColumn("Date"),
                "Sens": st.column_config.SelectboxColumn("Sens", options=["Aller", "Retour"]),
            },
            key="log_editor",
        )
        set_log(edited_log)
        st.download_button("⬇️ Télécharger le journal (CSV)",
                            get_log().to_csv(index=False).encode("utf-8"),
                            f"journal_transmissions_aer_{date.today().isoformat()}.csv", "text/csv")
    with rc1:
        by_service = get_log()["Service destination"].value_counts().reset_index()
        by_service.columns = ["Service", "Nombre de transmissions reçues"]
        fig = px.bar(by_service.sort_values("Nombre de transmissions reçues", ascending=False).head(15),
                     x="Service", y="Nombre de transmissions reçues", color_discrete_sequence=[theme_palette()["navy"]],
                     title="Postes les plus sollicités (nombre de dossiers reçus)")
        fig = plotly_base_layout(fig, legend=False)
        fig.update_xaxes(tickangle=-35)
        st.plotly_chart(fig, width='stretch')

    st.write("")
    section_title("TEMPS PASSÉ PAR SERVICE — ET DÉPASSEMENTS DE DÉLAI IMPARTI")
    tps = temps_par_service(get_log())
    if tps.empty:
        st.info("Pas encore assez de mouvements pour calculer un temps de passage.")
    else:
        nb_depassements = int(tps["Dépassement"].sum())
        if nb_depassements:
            st.error(f"⚠️ {nb_depassements} étape(s) ont dépassé le délai imparti fixé lors de la "
                     "transmission.")
        moy = tps.groupby("Service", as_index=False)["Jours passés"].mean().sort_values(
            "Jours passés", ascending=False)
        moy.columns = ["Service", "Jours passés en moyenne"]
        c1, c2 = st.columns(2)
        with c1:
            fig = px.bar(moy.head(15), x="Service", y="Jours passés en moyenne",
                         color_discrete_sequence=[theme_palette()["amber"]],
                         title="Délai moyen de traitement par service (jours)")
            fig = plotly_base_layout(fig, legend=False)
            fig.update_xaxes(tickangle=-35)
            st.plotly_chart(fig, width='stretch')
        with c2:
            tps_display = tps.sort_values("Jours passés", ascending=False).copy()
            tps_display["Dépassement"] = tps_display["Dépassement"].map({True: "⚠️ Oui", False: ""})
            st.dataframe(tps_display, width='stretch', hide_index=True, height=380)

st.write("")
section_title("🕵️ JOURNAL D'AUDIT — QUI A MODIFIÉ QUOI, QUAND")
st.caption(
    "Toute transmission, tout ajout/modification/suppression direct du registre ou des pièces "
    "jointes, et toute restauration de sauvegarde sont journalisés ici — y compris les changements "
    "qui ne passent pas par une transmission en bonne et due forme (ex. statut modifié directement "
    "dans le tableau du Registre). Comble le trou de traçabilité identifié : sans ce journal, une "
    "modification directe du registre n'était tracée nulle part."
)
audit_scope = st.radio("Portée", ["Tous les dossiers", "Un dossier en particulier"],
                        horizontal=True, key="audit_scope")
if audit_scope == "Un dossier en particulier":
    audit_dossier = st.selectbox("Dossier", dossier_options, key="audit_dossier_choice")
    audit_rows = db.fetch_audit_log(numero_dossier=audit_dossier.split(" — ")[0])
else:
    audit_rows = db.fetch_audit_log()

if not audit_rows:
    st.info("Le journal d'audit est vide pour l'instant.")
else:
    st.dataframe(pd.DataFrame(audit_rows), width='stretch', hide_index=True, height=360)

render_sidebar_footer()
