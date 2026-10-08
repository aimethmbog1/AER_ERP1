"""Registre générique des dossiers — stocké dans une base SQLite partagée
(voir `utils/db.py`), et non plus dans `st.session_state`. Comme pour le
fonds revolving de l'application AER, aucun dossier réel n'est préchargé :
ni le mémoire, ni l'organigramme fourni ne contiennent de vrais dossiers,
échéances ou statuts. Cette application est un prototype à alimenter, pensé
pour démontrer et tester concrètement la solution de digitalisation /
centralisation proposée dans le diagnostic (traçabilité, délais,
coordination), pas un accès à un vrai système d'information existant.

**Changement important par rapport à la version initiale** : le registre est
désormais commun à tous les utilisateurs connectés au même serveur (et
persiste entre les sessions), et non plus isolé par session de navigateur —
voir la documentation en tête de `utils/db.py` pour le détail et les limites
honnêtes de ce mécanisme.
"""
from __future__ import annotations

from datetime import date, datetime

import pandas as pd
import streamlit as st

from . import db

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

CANAL_COURRIER = "Service du Courrier (bureau d'ordre)"
CANAL_DIRECT = "Dépôt direct au service concerné (dossier d'origine interne)"
CANAUX_RECEPTION = [CANAL_COURRIER, CANAL_DIRECT]

STATUTS = ["Reçu", "En cours", "En attente", "Traité / Clôturé", "Archivé"]
STATUTS_CLOS = {"Traité / Clôturé", "Archivé"}
PRIORITES = ["Normale", "Urgente"]

_DISPLAY_TO_DB = {
    "Date de réception": "date_reception",
    "Objet": "objet",
    "Type de dossier": "type_dossier",
    "Canal de réception": "canal_reception",
    "Direction concernée": "direction_concernee",
    "Service destinataire actuel": "service_destinataire",
    "Statut": "statut",
    "Priorité": "priorite",
    "Échéance prévue": "echeance_prevue",
    "Agent en charge": "agent_en_charge",
    "Référence externe (optionnel)": "reference_externe",
    "Notes": "notes",
}


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


def empty_register() -> pd.DataFrame:
    df = pd.DataFrame(columns=REGISTER_COLUMNS)
    df["Date de réception"] = pd.to_datetime(df["Date de réception"])
    df["Échéance prévue"] = pd.to_datetime(df["Échéance prévue"])
    return df


def get_register() -> pd.DataFrame:
    rows = db.fetch_dossiers()
    if not rows:
        return empty_register()
    data = [{
        "N° dossier": r["numero"],
        "Date de réception": r["date_reception"],
        "Objet": r["objet"],
        "Type de dossier": r["type_dossier"],
        "Canal de réception": r["canal_reception"],
        "Direction concernée": r["direction_concernee"],
        "Service destinataire actuel": r["service_destinataire"],
        "Statut": r["statut"],
        "Priorité": r["priorite"],
        "Échéance prévue": r["echeance_prevue"],
        "Agent en charge": r["agent_en_charge"],
        "Référence externe (optionnel)": r["reference_externe"],
        "Notes": r["notes"],
    } for r in rows]
    df = pd.DataFrame(data, columns=REGISTER_COLUMNS)
    df["Date de réception"] = pd.to_datetime(df["Date de réception"], errors="coerce")
    df["Échéance prévue"] = pd.to_datetime(df["Échéance prévue"], errors="coerce")
    return df


def set_register(df: pd.DataFrame) -> None:
    """Synchronise l'intégralité du registre avec la base à partir d'un
    DataFrame édité (page Registre) : met à jour les dossiers modifiés,
    insère les nouvelles lignes ajoutées directement dans le tableau
    (reconnaissables à un N° dossier vide — cette colonne est en lecture
    seule dans l'éditeur, voir la page Registre), supprime celles absentes
    de `df`, et journalise chaque changement dans le journal d'audit (page
    Transmissions & traçabilité, section « Journal d'audit »)."""
    poste_auteur = _poste_auteur()
    current = {r["numero"]: r for r in db.fetch_dossiers()}
    seen_numeros: set[str] = set()

    for _, row in df.iterrows():
        numero = _cell_to_text(row.get("N° dossier"))
        fields = {db_col: _cell_to_text(row.get(disp_col)) for disp_col, db_col in _DISPLAY_TO_DB.items()}

        if numero and numero in current:
            seen_numeros.add(numero)
            existing = current[numero]
            for disp_col, db_col in _DISPLAY_TO_DB.items():
                nouvelle = fields[db_col]
                ancienne = existing.get(db_col)
                if (ancienne or None) != (nouvelle or None):
                    db.update_dossier_field(existing["id"], numero, db_col, ancienne, nouvelle,
                                             poste_auteur, "Édition directe du registre")
                    existing[db_col] = nouvelle
        elif fields.get("objet"):
            # Ligne ajoutée directement dans le tableau (le N° dossier, en lecture seule, est vide
            # pour une ligne neuve tant qu'elle n'a pas été enregistrée).
            new_numero = db.insert_dossier(fields, poste_auteur, source="Ajout direct dans le tableau")
            seen_numeros.add(new_numero)

    for numero, existing in current.items():
        if numero not in seen_numeros:
            snapshot = f"{existing.get('objet')} — {existing.get('statut')}"
            db.delete_dossier(existing["id"], numero, snapshot, poste_auteur,
                               "Suppression directe dans le tableau")


def add_dossier(*, objet: str, type_dossier: str, canal: str, direction: str, poste: str, statut: str,
                priorite: str, date_reception, echeance, agent: str, ref_externe: str, notes: str) -> str:
    """Ajoute un nouveau dossier via le formulaire dédié (page Registre,
    section « Nouveau dossier ») et renvoie son numéro, attribué de façon
    stable (voir `db.insert_dossier`)."""
    fields = {
        "date_reception": _cell_to_text(date_reception),
        "objet": objet,
        "type_dossier": type_dossier,
        "canal_reception": canal,
        "direction_concernee": direction,
        "service_destinataire": poste,
        "statut": statut,
        "priorite": priorite,
        "echeance_prevue": _cell_to_text(echeance),
        "agent_en_charge": agent,
        "reference_externe": ref_externe,
        "notes": notes,
    }
    return db.insert_dossier(fields, _poste_auteur(), source="Nouveau dossier (formulaire)")


def update_service_destinataire(numero: str, nouveau_poste: str) -> None:
    """Met à jour le poste destinataire actuel d'un dossier suite à une
    transmission déjà validée par `transmissions.add_transmission` (routage
    déjà vérifié) — distinct d'une édition directe du tableau : journalisé
    avec la source « Transmission » plutôt que « Édition directe du
    registre », pour ne pas dupliquer/brouiller l'entrée d'audit déjà posée
    par la transmission elle-même."""
    rows = {r["numero"]: r for r in db.fetch_dossiers()}
    existing = rows.get(numero)
    if existing is None:
        return
    ancien = existing.get("service_destinataire")
    if ancien != nouveau_poste:
        db.update_dossier_field(existing["id"], numero, "service_destinataire", ancien, nouveau_poste,
                                 _poste_auteur(), "Transmission")


def date_echeance_warning(date_reception, echeance) -> str | None:
    """Avertissement si l'échéance saisie est antérieure à la date de
    réception — aucune vérification de ce type n'existait avant."""
    if echeance is not None and date_reception is not None and echeance < date_reception:
        return ("L'échéance prévue est antérieure à la date de réception — vérifiez les dates avant "
                "d'ajouter ce dossier.")
    return None


def next_dossier_id(df: pd.DataFrame) -> str:
    """Conservé pour compatibilité ascendante uniquement (ancien aperçu
    indicatif). L'attribution réelle du numéro se fait désormais dans
    `db.insert_dossier()`, à partir de l'identifiant auto-incrémenté interne
    de la base — qui n'est jamais réutilisé même après suppression d'un
    dossier, contrairement à ce calcul `len(df) + 1`, qui pouvait entrer en
    collision avec un numéro existant dès qu'un dossier avait été supprimé."""
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
