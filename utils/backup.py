"""Sauvegarde / restauration complète en un seul fichier JSON (registre des
dossiers + journal des transmissions + pièces jointes), en plus des exports
CSV par table déjà disponibles sur chaque page.

Depuis l'ajout du stockage SQLite partagé (voir `utils/db.py`), les données
survivent déjà entre deux sessions de navigateur tant que le serveur tourne
et que son disque est persistant — cette sauvegarde JSON reste néanmoins le
filet de sécurité ultime : portable, lisible hors de l'application, et seul
recours si l'hébergement choisi ne garantit pas un disque persistant (c'est
le cas, par exemple, de Streamlit Community Cloud)."""
from __future__ import annotations

import json
from datetime import datetime

import pandas as pd
import streamlit as st

from . import db
from .dossiers import get_register
from .transmissions import get_log
from .attachments import get_attachments

_DISPLAY_TO_DB_DOSSIER = {
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

_DISPLAY_TO_DB_TRANSMISSION = {
    "N° dossier": "numero_dossier",
    "Date": "date",
    "Service source": "service_source",
    "Service destination": "service_destination",
    "Sens": "sens",
    "Délai imparti (jours)": "delai_imparti_jours",
    "Commentaire": "commentaire",
}


def _poste_auteur() -> str | None:
    poste = st.session_state.get("poste_courant")
    if poste and str(poste).startswith("("):
        return None
    return poste


def _df_to_records(df: pd.DataFrame) -> list[dict]:
    out = df.copy()
    for col in out.columns:
        if pd.api.types.is_datetime64_any_dtype(out[col]):
            out[col] = out[col].dt.strftime("%Y-%m-%d")
    return json.loads(out.to_json(orient="records", force_ascii=False))


def build_backup_json() -> str:
    payload = {
        "application": "Suivi des dossiers AER",
        "exporte_le": datetime.now().isoformat(timespec="seconds"),
        "registre_dossiers": _df_to_records(get_register()),
        "journal_transmissions": _df_to_records(get_log()),
        "pieces_jointes": get_attachments(),
    }
    return json.dumps(payload, ensure_ascii=False, indent=2)


def restore_backup_json(content: str) -> tuple[int, int, int]:
    payload = json.loads(content)
    poste_auteur = _poste_auteur()

    reg_records = payload.get("registre_dossiers", [])
    dossier_rows = []
    for rec in reg_records:
        row = {db_col: rec.get(disp_col) for disp_col, db_col in _DISPLAY_TO_DB_DOSSIER.items()}
        row["numero"] = rec.get("N° dossier")
        dossier_rows.append(row)
    n_reg = db.replace_all_dossiers(dossier_rows, poste_auteur, "Restauration de sauvegarde")

    log_records = payload.get("journal_transmissions", [])
    trans_rows = [{db_col: rec.get(disp_col) for disp_col, db_col in _DISPLAY_TO_DB_TRANSMISSION.items()}
                  for rec in log_records]
    n_log = db.replace_all_transmissions(trans_rows, poste_auteur, "Restauration de sauvegarde")

    pieces = payload.get("pieces_jointes", {})
    n_pj = db.replace_all_attachments(pieces if isinstance(pieces, dict) else {}, poste_auteur,
                                       "Restauration de sauvegarde")

    return n_reg, n_log, n_pj
