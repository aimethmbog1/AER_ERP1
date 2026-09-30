"""Registre générique des dossiers — démarre vide.

Comme pour le fonds revolving de l'application AER, aucun dossier réel n'est
préchargé : ni le mémoire, ni l'organigramme fourni ne contiennent de vrais
dossiers, échéances ou statuts. Cette application est un prototype à alimenter,
pensé pour démontrer et tester concrètement la solution de digitalisation /
centralisation proposée dans le diagnostic (traçabilité, délais, coordination),
pas un accès à un vrai système d'information existant.
"""
from __future__ import annotations

from datetime import date, datetime

import pandas as pd
import streamlit as st

REGISTER_COLUMNS = [
    "N° dossier",
    "Date de réception",
    "Objet",
    "Type de dossier",
    "Direction concernée",
    "Service destinataire actuel",
    "Statut",
    "Priorité",
    "Échéance prévue",
    "Agent en charge",
    "Notes",
]

TYPES_DOSSIER = [
    "Courrier entrant",
    "Courrier sortant",
    "Dossier projet",
    "Dossier marché",
    "Dossier RH",
    "Autre",
]

STATUTS = ["Reçu", "En cours", "En attente", "Traité / Clôturé", "Archivé"]
STATUTS_CLOS = {"Traité / Clôturé", "Archivé"}
PRIORITES = ["Normale", "Urgente"]


def empty_register() -> pd.DataFrame:
    df = pd.DataFrame(columns=REGISTER_COLUMNS)
    df["Date de réception"] = pd.to_datetime(df["Date de réception"])
    df["Échéance prévue"] = pd.to_datetime(df["Échéance prévue"])
    return df


def get_register() -> pd.DataFrame:
    if "dossiers_register" not in st.session_state:
        st.session_state["dossiers_register"] = empty_register()
    return st.session_state["dossiers_register"]


def set_register(df: pd.DataFrame) -> None:
    st.session_state["dossiers_register"] = df


def next_dossier_id(df: pd.DataFrame) -> str:
    n = len(df) + 1
    annee = date.today().strftime("%Y")
    return f"AER-{annee}-{n:04d}"


def with_derived_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Ajoute des colonnes calculées à partir des seules données saisies :
    ancienneté du dossier et retard éventuel par rapport à l'échéance."""
    out = df.copy()
    if out.empty:
        out["Jours depuis réception"] = pd.Series(dtype="float64")
        out["Jours de retard"] = pd.Series(dtype="float64")
        out["En retard"] = pd.Series(dtype="bool")
        return out

    today = pd.Timestamp(datetime.now().date())
    reception = pd.to_datetime(out["Date de réception"], errors="coerce")
    echeance = pd.to_datetime(out["Échéance prévue"], errors="coerce")
    clos = out["Statut"].isin(STATUTS_CLOS)

    out["Jours depuis réception"] = (today - reception).dt.days
    retard_jours = (today - echeance).dt.days
    out["Jours de retard"] = retard_jours.where((~clos) & echeance.notna() & (retard_jours > 0), 0)
    out["En retard"] = (out["Jours de retard"] > 0)
    return out
