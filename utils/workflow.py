"""Workflow d'approbation formalisé — inspiré du moteur de workflow (BPM)
d'Oracle Cloud ERP : une étape d'un dossier peut nécessiter une DÉCISION
explicite (Approuvé / Rejeté) d'un poste précis avant de se poursuivre,
distincte du simple routage d'une transmission (voir `utils/transmissions.py`).
Trois opérations possibles sur une demande d'approbation :
  - **décider** (Approuvé / Rejeté), par le poste approbateur désigné ;
  - **déléguer** à un autre poste, sans trancher (le poste d'origine n'est
    alors plus celui attendu pour décider) ;
  - laisser en attente, avec une échéance propre à la demande (distincte de
    l'échéance globale du dossier) — une demande en attente dont l'échéance
    est dépassée apparaît comme en retard dans le centre de notifications
    (voir `utils/notifications.py`).

Stocké dans la même base SQLite partagée que le reste (voir `utils/db.py`),
donc visible par tous les postes connectés au même serveur, exactement comme
le registre et le journal des transmissions."""
from __future__ import annotations

from datetime import date, datetime

import pandas as pd
import streamlit as st

from . import db

APPROBATION_COLUMNS = [
    "id",
    "N° dossier",
    "Étape",
    "Demandé par",
    "Approbateur",
    "Statut",
    "Date de demande",
    "Échéance",
    "Date de décision",
    "Commentaire",
    "Commentaire de décision",
]

STATUT_EN_ATTENTE = db.STATUT_EN_ATTENTE
STATUT_APPROUVE = db.STATUT_APPROUVE
STATUT_REJETE = db.STATUT_REJETE
STATUTS_APPROBATION = db.STATUTS_APPROBATION


def _poste_auteur() -> str | None:
    poste = st.session_state.get("poste_courant")
    if poste and str(poste).startswith("("):
        return None
    return poste


def _cell_to_text(value) -> str | None:
    if value is None:
        return None
    try:
        if pd.isna(value):
            return None
    except (TypeError, ValueError):
        pass
    if isinstance(value, (pd.Timestamp, datetime, date)):
        return pd.Timestamp(value).strftime("%Y-%m-%d")
    text = str(value).strip()
    return text or None


def _rows_to_df(rows: list[dict]) -> pd.DataFrame:
    data = [{
        "id": r["id"],
        "N° dossier": r["numero_dossier"],
        "Étape": r["etape"],
        "Demandé par": r["demande_par"],
        "Approbateur": r["approbateur"],
        "Statut": r["statut"],
        "Date de demande": r["date_demande"],
        "Échéance": r["echeance"],
        "Date de décision": r["date_decision"],
        "Commentaire": r["commentaire"],
        "Commentaire de décision": r["decision_commentaire"],
    } for r in rows]
    df = pd.DataFrame(data, columns=APPROBATION_COLUMNS)
    df["Date de demande"] = pd.to_datetime(df["Date de demande"], errors="coerce")
    df["Échéance"] = pd.to_datetime(df["Échéance"], errors="coerce")
    df["Date de décision"] = pd.to_datetime(df["Date de décision"], errors="coerce")
    for col in ("Commentaire", "Commentaire de décision"):
        df[col] = df[col].fillna("")
    return df


def get_approbations(numero_dossier: str | None = None, approbateur: str | None = None,
                      statut: str | None = None) -> pd.DataFrame:
    rows = db.fetch_approbations(numero_dossier=numero_dossier, approbateur=approbateur, statut=statut)
    if not rows:
        return pd.DataFrame(columns=APPROBATION_COLUMNS)
    return _rows_to_df(rows)


def request_approval(numero_dossier: str, etape: str, approbateur: str,
                      echeance=None, commentaire: str = "") -> int:
    """Ouvre une demande d'approbation « En attente » pour `numero_dossier`,
    à décider par le poste `approbateur`. `demande_par` est déduit du poste
    courant simulé (barre latérale), comme pour une transmission."""
    fields = {
        "numero_dossier": numero_dossier,
        "etape": etape,
        "demande_par": _poste_auteur(),
        "approbateur": approbateur,
        "statut": STATUT_EN_ATTENTE,
        "date_demande": date.today().isoformat(),
        "echeance": _cell_to_text(echeance),
        "date_decision": None,
        "commentaire": commentaire or None,
        "decision_commentaire": None,
    }
    return db.insert_approbation(fields, _poste_auteur())


def decide(approbation_id: int, decision: str, commentaire: str = "") -> None:
    if decision not in (STATUT_APPROUVE, STATUT_REJETE):
        raise ValueError(f"Décision inconnue : {decision}")
    db.decide_approbation(approbation_id, decision, commentaire or None, _poste_auteur())


def delegate(approbation_id: int, nouvel_approbateur: str, commentaire: str = "") -> None:
    db.delegate_approbation(approbation_id, nouvel_approbateur, commentaire or None, _poste_auteur())


def pending_for(poste: str) -> pd.DataFrame:
    """Demandes « En attente » dont `poste` est l'approbateur désigné — le
    cœur de la liste de tâches personnelle (centre de notifications,
    page d'accueil)."""
    return get_approbations(approbateur=poste, statut=STATUT_EN_ATTENTE)


def overdue(poste: str | None = None) -> pd.DataFrame:
    """Demandes « En attente » dont l'échéance propre est dépassée —
    toutes approbateurs confondus si `poste` n'est pas précisé."""
    df = get_approbations(approbateur=poste, statut=STATUT_EN_ATTENTE)
    if df.empty:
        return df
    today = pd.Timestamp(date.today())
    return df[df["Échéance"].notna() & (df["Échéance"] < today)]
