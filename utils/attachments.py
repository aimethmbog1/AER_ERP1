"""Pièces jointes (scans) rattachées à un dossier.

Inspiré de la fonction de numérisation « à la volée » de Maarch Courrier —
mais implémenté nativement ici, sans aucune connexion à Maarch ni à un vrai
système de gestion électronique de documents (GED) : les fichiers sont
conservés sur disque, à côté de la base SQLite partagée (voir `utils/db.py`),
et leurs métadonnées en base ; ils ne sont plus perdus d'une session de
navigateur à l'autre comme dans la version initiale (qui gardait tout en
mémoire de session, encodé en base64). Ce n'est toujours pas un coffre-fort
documentaire — limitez le nombre et la taille des fichiers attachés, et
consultez les limites honnêtes documentées dans `utils/db.py` (persistance
du disque selon l'hébergement choisi).
"""
from __future__ import annotations

import streamlit as st

from . import db

MAX_FICHIERS_PAR_DOSSIER = db.MAX_FICHIERS_PAR_DOSSIER
MAX_TAILLE_OCTETS = db.MAX_TAILLE_OCTETS


def _poste_auteur() -> str | None:
    poste = st.session_state.get("poste_courant")
    if poste and str(poste).startswith("("):
        return None
    return poste


def get_attachments() -> dict[str, list[dict]]:
    """Regroupe toutes les pièces jointes par dossier (format utilisé par la
    sauvegarde JSON complète)."""
    return db.fetch_all_attachments_for_backup()


def set_attachments(data: dict[str, list[dict]]) -> None:
    db.replace_all_attachments(data, _poste_auteur(), "Restauration de sauvegarde")


def list_for(dossier_id: str) -> list[dict]:
    return db.list_attachments(dossier_id)


def add_attachment(dossier_id: str, uploaded_file) -> tuple[bool, str]:
    return db.add_attachment(dossier_id, uploaded_file, _poste_auteur())


def remove_attachment(dossier_id: str, index: int) -> None:
    fichiers = db.list_attachments(dossier_id)
    if 0 <= index < len(fichiers):
        db.remove_attachment(fichiers[index]["id"], _poste_auteur())


def decode(attachment: dict) -> bytes:
    return db.decode_attachment(attachment)


def total_count() -> int:
    return db.count_attachments()
