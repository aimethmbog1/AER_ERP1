"""Fiche dossier — vue 360° d'un seul dossier, inspirée de la « page objet »
d'Oracle Cloud ERP (Fusion) : toutes les informations qui concernent CE
dossier précis rassemblées à un seul endroit (identité, workflow
d'approbation, historique des transmissions, journal d'audit complet,
pièces jointes), plutôt que réparties entre plusieurs pages qu'il faut
recouper soi-même. Les autres pages restent les points d'entrée « par
activité » (Registre pour saisir/filtrer en masse, Transmissions pour
enregistrer un mouvement) ; celle-ci est le point d'entrée « par dossier »,
atteint depuis la recherche globale de l'accueil ou la liste de tâches
personnelle, ou choisi manuellement ci-dessous."""
from __future__ import annotations

from datetime import date

import pandas as pd
import streamlit as st

from utils.ui import (
    inject_base_style, section_title, render_sidebar_footer, render_page_header,
    status_badge, theme_palette, kpi_row,
)
from utils.dossiers import get_register, with_derived_columns
from utils.transmissions import history_for
from utils.orgchart import all_node_ids, depth_of, NODES
from utils.session import current_post_selector
from utils.attachments import list_for as attachments_for, decode as decode_attachment
from utils import workflow as wf
from utils import db

inject_base_style()

poste_courant = current_post_selector()

render_page_header(
    "🗂️", "Fiche dossier",
    "Vue 360° d'un dossier — identité, workflow d'approbation, historique des transmissions et "
    "journal d'audit complet, inspirée de la « page objet » d'Oracle Cloud ERP.",
)

register = with_derived_columns(get_register())
if register.empty:
    st.info("Enregistrez d'abord un dossier sur la page **Registre des dossiers**.")
    st.stop()

POSTE_OPTIONS = all_node_ids()
POSTE_LABELS = {p: ("— " * depth_of(p)) + p + f"  ·  {NODES[p].rang}" for p in POSTE_OPTIONS}

dossier_options = (register["N° dossier"] + " — " + register["Objet"].astype(str)).tolist()
numero_to_index = {opt.split(" — ")[0]: i for i, opt in enumerate(dossier_options)}

preselect = st.session_state.pop("_fiche_dossier_numero", None)
default_index = numero_to_index.get(preselect, 0) if preselect else 0

choix = st.selectbox("Dossier", dossier_options, index=default_index, key="fiche_dossier_choice")
numero = choix.split(" — ")[0]
row = register[register["N° dossier"] == numero].iloc[0]

# =====================================================================
# En-tête d'identité
# =====================================================================
p = theme_palette()
echeance_txt = row["Échéance prévue"].strftime("%d/%m/%Y") if pd.notna(row["Échéance prévue"]) else "—"
with st.container(border=True):
    st.markdown(f"### {row['Objet']}")
    st.markdown(
        f"{status_badge(row['Statut'])} &nbsp; "
        + (f'<span class="aer-badge" style="background:{p["red"]}">⚠️ En retard '
           f'({int(row["Jours de retard"])} j)</span>' if row["En retard"] else "")
        + (f'<span class="aer-badge" style="background:{p["amber"]}">⏳ Échéance proche</span>'
           if row.get("Échéance proche") and not row["En retard"] else ""),
        unsafe_allow_html=True,
    )
    ic1, ic2, ic3, ic4 = st.columns(4)
    ic1.markdown(f"**Poste actuel**  \n{row['Service destinataire actuel']}")
    ic2.markdown(f"**Direction**  \n{row['Direction concernée']}")
    ic3.markdown(f"**Priorité**  \n{row['Priorité']}")
    ic4.markdown(f"**Échéance prévue**  \n{echeance_txt}")
    if row["Agent en charge"] or row["Référence externe (optionnel)"]:
        st.caption(
            f"Agent en charge : {row['Agent en charge'] or '—'} · "
            f"Référence externe : {row['Référence externe (optionnel)'] or '—'}"
        )

st.write("")

# =====================================================================
# Workflow d'approbation
# =====================================================================
section_title("✅ WORKFLOW D'APPROBATION")
with st.expander("ℹ️ Différence avec une transmission", expanded=False):
    st.markdown(
        """
Une **transmission** (page *Transmissions & traçabilité*) déplace le dossier d'un poste à l'autre — c'est
le routage. Une **demande d'approbation** est une étape complémentaire et facultative : elle attend une
décision explicite (**Approuvé** / **Rejeté**) d'un poste précis, sans forcément déplacer le dossier. Les
deux journaux sont indépendants ; un dossier peut être transmis sans jamais passer par une approbation, ou
l'inverse. Inspiré du moteur de workflow (BPM) d'Oracle Cloud ERP.
        """
    )

approbations = wf.get_approbations(numero_dossier=numero)

if not approbations.empty:
    st.dataframe(
        approbations[["Étape", "Demandé par", "Approbateur", "Statut", "Date de demande", "Échéance",
                      "Date de décision", "Commentaire", "Commentaire de décision"]],
        width='stretch', hide_index=True,
        column_config={
            "Date de demande": st.column_config.DateColumn("Date de demande"),
            "Échéance": st.column_config.DateColumn("Échéance"),
            "Date de décision": st.column_config.DateColumn("Date de décision"),
        },
    )
else:
    st.caption("Aucune demande d'approbation pour ce dossier pour l'instant.")

pending_mine = approbations[
    (approbations["Statut"] == wf.STATUT_EN_ATTENTE) & (approbations["Approbateur"] == poste_courant)
] if poste_courant and not approbations.empty else approbations.iloc[0:0]

if not pending_mine.empty:
    st.markdown(f"**À décider par votre poste actuel ({poste_courant})**")
    for _, r in pending_mine.iterrows():
        with st.container(border=True):
            st.markdown(f"**{r['Étape'] or 'Étape'}** — demandé par {r['Demandé par'] or '—'}"
                        + (f" — commentaire : {r['Commentaire']}" if r["Commentaire"] else ""))
            dc1, dc2, dc3, dc4 = st.columns([2, 1, 1, 1.4])
            commentaire_decision = dc1.text_input(
                "Commentaire (optionnel)", key=f"appr_comment_{r['id']}", label_visibility="collapsed",
                placeholder="Commentaire de décision (optionnel)",
            )
            if dc2.button("✅ Approuver", key=f"appr_ok_{r['id']}", type="primary"):
                wf.decide(int(r["id"]), wf.STATUT_APPROUVE, commentaire_decision)
                st.toast("Approbation enregistrée.", icon="✅")
                st.rerun()
            if dc3.button("❌ Rejeter", key=f"appr_no_{r['id']}"):
                wf.decide(int(r["id"]), wf.STATUT_REJETE, commentaire_decision)
                st.toast("Rejet enregistré.", icon="🛑")
                st.rerun()
            with dc4.popover("↪️ Déléguer"):
                nouveau = st.selectbox(
                    "Déléguer à", [x for x in POSTE_OPTIONS if x != poste_courant],
                    format_func=lambda x: POSTE_LABELS[x], key=f"appr_delegate_target_{r['id']}",
                )
                if st.button("Confirmer la délégation", key=f"appr_delegate_btn_{r['id']}"):
                    wf.delegate(int(r["id"]), nouveau, commentaire_decision)
                    st.toast(f"Délégué à {nouveau}.", icon="↪️")
                    st.rerun()

st.markdown("**➕ Nouvelle demande d'approbation**")
with st.container(border=True):
    nc1, nc2 = st.columns(2)
    n_etape = nc1.text_input("Étape / objet de la décision attendue", key="appr_new_etape",
                              placeholder="Ex. : Validation du budget, Avis juridique...")
    n_approbateur = nc2.selectbox("Poste approbateur", POSTE_OPTIONS, format_func=lambda x: POSTE_LABELS[x],
                                   key="appr_new_approbateur")
    nc3, nc4 = st.columns(2)
    n_echeance_actif = nc3.checkbox("Fixer une échéance de décision", value=False, key="appr_new_echeance_actif")
    n_echeance = nc3.date_input("Échéance", value=date.today(), key="appr_new_echeance",
                                 disabled=not n_echeance_actif)
    n_commentaire = nc4.text_input("Commentaire (contexte, instruction...)", key="appr_new_commentaire")
    if st.button("Soumettre la demande d'approbation", type="primary", key="appr_new_submit"):
        if not n_etape:
            st.warning("Renseignez l'étape / objet de la décision attendue.")
        else:
            wf.request_approval(numero, n_etape, n_approbateur,
                                 echeance=(n_echeance if n_echeance_actif else None),
                                 commentaire=n_commentaire)
            st.toast(f"Demande d'approbation envoyée à {n_approbateur}.", icon="📨")
            st.rerun()

st.write("")

# =====================================================================
# Historique des transmissions
# =====================================================================
section_title("🔀 HISTORIQUE DES TRANSMISSIONS")
hist = history_for(numero)
if hist.empty:
    st.caption("Aucune transmission enregistrée pour ce dossier pour l'instant.")
else:
    st.dataframe(hist, width='stretch', hide_index=True,
                 column_config={"Date": st.column_config.DateColumn("Date")})

st.write("")

# =====================================================================
# Journal d'audit complet (champ par champ) pour ce dossier
# =====================================================================
section_title("🕵️ JOURNAL D'AUDIT COMPLET DE CE DOSSIER")
st.caption("Historique détaillé champ par champ (qui a changé quoi, quand), toutes sources confondues : "
           "création, édition directe du registre, transmission, approbation, pièce jointe.")
audit_rows = db.fetch_audit_log(numero_dossier=numero, limit=1000)
if not audit_rows:
    st.caption("Aucune entrée de journal d'audit pour ce dossier.")
else:
    st.dataframe(pd.DataFrame(audit_rows), width='stretch', hide_index=True, height=min(60 + 36 * (len(audit_rows) + 1), 420))

st.write("")

# =====================================================================
# Pièces jointes (lecture / téléchargement — l'ajout se fait depuis Registre)
# =====================================================================
section_title("📎 PIÈCES JOINTES")
fichiers = attachments_for(numero)
if not fichiers:
    st.caption("Aucune pièce jointe pour ce dossier. Ajoutez-en depuis la page **Registre des dossiers**.")
else:
    for i, f in enumerate(fichiers):
        fcol1, fcol2 = st.columns([3, 1])
        fcol1.write(f"📄 **{f['nom']}** — {f['taille_octets'] / 1024:.1f} Ko — ajouté le {f['date_ajout']}")
        fcol2.download_button("⬇️ Télécharger", decode_attachment(f), f["nom"], f["type"],
                               key=f"fiche_pj_dl_{numero}_{i}")

render_sidebar_footer()
