"""Export Excel multi-feuilles — complète les exports CSV par table déjà
disponibles sur chaque page et la sauvegarde JSON complète (page d'accueil).
Utile pour partager un instantané lisible (impression, transmission à la
hiérarchie) sans dépendre de l'application elle-même."""
from __future__ import annotations

import io

import pandas as pd

from .dossiers import get_register, with_derived_columns
from .transmissions import get_log
from .workflow import get_approbations
from . import db


def build_excel_export() -> bytes:
    registre = with_derived_columns(get_register())
    transmissions = get_log()
    approbations = get_approbations()
    audit = pd.DataFrame(db.fetch_audit_log(limit=2000))

    pieces = db.fetch_all_attachments_for_backup()
    pj_rows = []
    for numero, fichiers in pieces.items():
        for f in fichiers:
            pj_rows.append({
                "N° dossier": numero, "Nom du fichier": f.get("nom"), "Type": f.get("type"),
                "Taille (octets)": f.get("taille_octets"), "Date d'ajout": f.get("date_ajout"),
            })
    pieces_df = pd.DataFrame(pj_rows)

    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
        (registre if not registre.empty else pd.DataFrame(columns=["(registre vide)"])).to_excel(
            writer, sheet_name="Registre", index=False)
        (transmissions if not transmissions.empty else pd.DataFrame(columns=["(journal vide)"])).to_excel(
            writer, sheet_name="Transmissions", index=False)
        (approbations if not approbations.empty else pd.DataFrame(columns=["(aucune approbation)"])).to_excel(
            writer, sheet_name="Approbations", index=False)
        (pieces_df if not pieces_df.empty else pd.DataFrame(columns=["(aucune pièce jointe)"])).to_excel(
            writer, sheet_name="Pièces jointes", index=False)
        (audit if not audit.empty else pd.DataFrame(columns=["(journal d'audit vide)"])).to_excel(
            writer, sheet_name="Journal d'audit", index=False)

        for sheet in writer.sheets.values():
            for column_cells in sheet.columns:
                length = max((len(str(c.value)) for c in column_cells if c.value is not None), default=10)
                sheet.column_dimensions[column_cells[0].column_letter].width = min(max(length + 2, 12), 60)

    return buffer.getvalue()
