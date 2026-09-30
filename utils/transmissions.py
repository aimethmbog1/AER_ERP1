"""Journal des transmissions entre services — c'est le cœur de la traçabilité :
le mémoire diagnostique des difficultés de suivi et de coordination faute de
trace centralisée des mouvements d'un dossier entre entités. Ce journal :
  - démarre vide (aucun mouvement réel n'est préchargé) ;
  - n'accepte que des transmissions conformes au routage hiérarchique réel de
    l'AER (utils.orgchart.is_authorized) — pas de saut de niveau ;
  - distingue un mouvement « Aller » (descente/latéral) d'un « Retour » (vers
    l'émetteur du mouvement précédent pour ce dossier) ;
  - calcule le temps réellement passé à chaque étape à partir des dates
    saisies, et signale un dépassement de délai imparti si vous en fixez un.
"""
from __future__ import annotations

from datetime import date, datetime

import pandas as pd
import streamlit as st

from . import orgchart as og

LOG_COLUMNS = [
    "N° dossier",
    "Date",
    "Service source",
    "Service destination",
    "Sens",
    "Délai imparti (jours)",
    "Commentaire",
]


def empty_log() -> pd.DataFrame:
    df = pd.DataFrame(columns=LOG_COLUMNS)
    df["Date"] = pd.to_datetime(df["Date"])
    df["Délai imparti (jours)"] = pd.to_numeric(df["Délai imparti (jours)"])
    return df


def get_log() -> pd.DataFrame:
    if "transmissions_log" not in st.session_state:
        st.session_state["transmissions_log"] = empty_log()
    return st.session_state["transmissions_log"]


def set_log(df: pd.DataFrame) -> None:
    st.session_state["transmissions_log"] = df


def last_movement_for(dossier_id: str) -> pd.Series | None:
    log = get_log()
    if log.empty:
        return None
    hist = log[log["N° dossier"] == dossier_id].sort_values("Date")
    return hist.iloc[-1] if not hist.empty else None


def suggested_return_target(dossier_id: str) -> str | None:
    """Le service vers lequel un « retour » serait naturel : la source du
    dernier mouvement enregistré pour ce dossier."""
    last = last_movement_for(dossier_id)
    return last["Service source"] if last is not None else None


def add_transmission(dossier_id: str, dt: date, source: str, destination: str,
                      commentaire: str, delai_impartis_jours: int | None = None) -> tuple[bool, str]:
    """Ajoute une transmission si elle respecte le routage hiérarchique réel.
    Renvoie (succès, message)."""
    if source == destination:
        return False, "La source et la destination sont identiques."
    if not og.is_authorized(source, destination):
        return False, (
            f"Transmission non autorisée : « {destination} » n'est ni un palier directement "
            f"inférieur, ni de même rang, ni le supérieur hiérarchique de « {source} ». "
            "Utilisez une étape intermédiaire de l'organigramme."
        )

    retour_cible = suggested_return_target(dossier_id)
    sens = "Retour" if destination == retour_cible else "Aller"

    log = get_log()
    new_row = pd.DataFrame([{
        "N° dossier": dossier_id,
        "Date": pd.to_datetime(dt),
        "Service source": source,
        "Service destination": destination,
        "Sens": sens,
        "Délai imparti (jours)": delai_impartis_jours,
        "Commentaire": commentaire,
    }])
    set_log(pd.concat([log, new_row], ignore_index=True))
    return True, f"Transmission enregistrée ({sens}) : {source} → {destination}."


def history_for(dossier_id: str) -> pd.DataFrame:
    log = get_log()
    if log.empty:
        return log
    return log[log["N° dossier"] == dossier_id].sort_values("Date")


def temps_par_service(log: pd.DataFrame) -> pd.DataFrame:
    """Pour chaque dossier, calcule le temps écoulé entre une transmission
    vers un service et la transmission suivante (ou aujourd'hui si c'est la
    dernière) — mesure réelle du temps passé par service, calculée
    uniquement à partir des dates saisies. Signale un dépassement si un
    délai imparti a été fixé sur l'étape."""
    if log.empty:
        return pd.DataFrame(columns=["N° dossier", "Service", "Jours passés", "Délai imparti (jours)",
                                      "Dépassement", "Statut de la période"])

    rows = []
    today = pd.Timestamp(pd.Timestamp.now().date())
    for dossier_id, grp in log.sort_values("Date").groupby("N° dossier"):
        grp = grp.reset_index(drop=True)
        for i, r in grp.iterrows():
            debut = r["Date"]
            service = r["Service destination"]
            fin = grp.loc[i + 1, "Date"] if i + 1 < len(grp) else today
            jours = max((fin - debut).days, 0)
            statut = "Historique (service suivant atteint)" if i + 1 < len(grp) else "En cours (service actuel)"
            delai = r.get("Délai imparti (jours)")
            depassement = bool(pd.notna(delai) and jours > delai)
            rows.append({
                "N° dossier": dossier_id,
                "Service": service,
                "Jours passés": jours,
                "Délai imparti (jours)": delai,
                "Dépassement": depassement,
                "Statut de la période": statut,
            })
    return pd.DataFrame(rows)


def generer_bordereau(dossier_id: str, objet: str, source: str, destination: str,
                       dt: date, commentaire: str, agent: str = "") -> str:
    """Génère un bordereau de transmission texte, téléchargeable — pratique
    courante dans le suivi de courrier administratif, pour matérialiser
    l'envoi entre deux services."""
    return f"""BORDEREAU DE TRANSMISSION — AGENCE DE L'ÉLECTRIFICATION RURALE
{'=' * 64}

N° de dossier      : {dossier_id}
Objet              : {objet}
Date de transmission : {dt.strftime('%d/%m/%Y')}

Service émetteur   : {source}
Service destinataire : {destination}
Agent en charge    : {agent or '—'}

Observations :
{commentaire or '(aucune)'}

{'-' * 64}
Signature émetteur                         Signature destinataire (accusé de réception)


......................................     ......................................
Date : ____/____/________                  Date : ____/____/________

Document généré automatiquement par l'application de suivi des dossiers AER.
"""
