"""Sauvegarde / restauration complète de la session en un seul fichier JSON
(registre des dossiers + journal des transmissions), en plus des exports CSV
par table déjà disponibles sur chaque page. Utile pour ne pas perdre le
travail entre deux sessions, Streamlit ne conservant rien côté serveur."""
from __future__ import annotations

import json
from datetime import date, datetime

import pandas as pd

from .dossiers import REGISTER_COLUMNS, get_register, set_register
from .transmissions import LOG_COLUMNS, get_log, set_log
from .attachments import get_attachments, set_attachments


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

    reg = pd.DataFrame(payload.get("registre_dossiers", [])).reindex(columns=REGISTER_COLUMNS)
    if not reg.empty:
        reg["Date de réception"] = pd.to_datetime(reg["Date de réception"], errors="coerce")
        reg["Échéance prévue"] = pd.to_datetime(reg["Échéance prévue"], errors="coerce")
    set_register(reg)

    log = pd.DataFrame(payload.get("journal_transmissions", [])).reindex(columns=LOG_COLUMNS)
    if not log.empty:
        log["Date"] = pd.to_datetime(log["Date"], errors="coerce")
        log["Délai imparti (jours)"] = pd.to_numeric(log["Délai imparti (jours)"], errors="coerce")
    set_log(log)

    pieces = payload.get("pieces_jointes", {})
    set_attachments(pieces if isinstance(pieces, dict) else {})

    return len(reg), len(log), sum(len(v) for v in (pieces or {}).values())
