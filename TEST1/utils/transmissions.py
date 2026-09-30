"""Journal des transmissions entre services — c'est le cœur de la traçabilité :
le mémoire diagnostique des difficultés de suivi et de coordination faute de
trace centralisée des mouvements d'un dossier entre entités. Cette page
matérialise ce journal, démarre vide, et calcule le temps réellement passé
dans chaque service à partir des dates de transmission saisies."""
from __future__ import annotations

from datetime import date

import pandas as pd
import streamlit as st

LOG_COLUMNS = [
    "N° dossier",
    "Date",
    "Service source",
    "Service destination",
    "Commentaire",
]


def empty_log() -> pd.DataFrame:
    df = pd.DataFrame(columns=LOG_COLUMNS)
    df["Date"] = pd.to_datetime(df["Date"])
    return df


def get_log() -> pd.DataFrame:
    if "transmissions_log" not in st.session_state:
        st.session_state["transmissions_log"] = empty_log()
    return st.session_state["transmissions_log"]


def set_log(df: pd.DataFrame) -> None:
    st.session_state["transmissions_log"] = df


def add_transmission(dossier_id: str, dt: date, source: str, destination: str, commentaire: str) -> None:
    log = get_log()
    new_row = pd.DataFrame([{
        "N° dossier": dossier_id,
        "Date": pd.to_datetime(dt),
        "Service source": source,
        "Service destination": destination,
        "Commentaire": commentaire,
    }])
    set_log(pd.concat([log, new_row], ignore_index=True))


def history_for(dossier_id: str) -> pd.DataFrame:
    log = get_log()
    if log.empty:
        return log
    return log[log["N° dossier"] == dossier_id].sort_values("Date")


def temps_par_service(log: pd.DataFrame) -> pd.DataFrame:
    """Pour chaque dossier, calcule le temps écoulé entre une transmission
    vers un service et la transmission suivante (ou aujourd'hui si c'est la
    dernière) — donne une mesure réelle du temps passé par service, calculée
    uniquement à partir des dates que l'utilisateur a saisies."""
    if log.empty:
        return pd.DataFrame(columns=["N° dossier", "Service", "Jours passés", "Statut de la période"])

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
            rows.append({
                "N° dossier": dossier_id,
                "Service": service,
                "Jours passés": jours,
                "Statut de la période": statut,
            })
    return pd.DataFrame(rows)
