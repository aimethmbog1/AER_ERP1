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
    "Canal de réception",
    "Direction concernée",
    "Service destinataire actuel",
    "Statut",
    "Priorité",
    "Échéance prévue",
    "Agent en charge",
    "Référence externe (optionnel)",
    "Notes",
]

TYPES_DOSSIER = [
    "Courrier entrant",
    "Courrier sortant",
    "Dossier projet",
    "Dossier marché",
    "Dossier RH / Carrière",
    "Dossier comptable / budgétaire",
    "Dossier état civil (naissance / mariage / décès)",
    "Autre",
]

# Circuit d'entrée d'un dossier : conforme au fonctionnement réel décrit par
# l'utilisateur, le canal normal pour un dossier externe est le service du
# courrier, qui l'achemine ensuite vers le poste concerné (voir
# utils.orgchart.SERVICE_COURRIER et la page Transmissions). Le dépôt direct
# reste possible pour un dossier d'origine interne (ex. note initiée par un
# service lui-même), sans passer par le bureau d'ordre.
CANAL_COURRIER = "Service du Courrier (bureau d'ordre)"
CANAL_DIRECT = "Dépôt direct au service concerné (dossier d'origine interne)"
CANAUX_RECEPTION = [CANAL_COURRIER, CANAL_DIRECT]

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

    jours_avant_echeance = (echeance - today).dt.days
    out["Échéance proche"] = ((~clos) & echeance.notna() & (jours_avant_echeance >= 0) &
                               (jours_avant_echeance <= 3))
    return out
