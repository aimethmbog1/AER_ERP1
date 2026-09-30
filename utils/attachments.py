"""Pièces jointes (scans) rattachées à un dossier.

Inspiré de la fonction de numérisation « à la volée » de Maarch Courrier —
mais implémenté nativement ici, sans aucune connexion à Maarch ni à un vrai
système de gestion électronique de documents (GED) : les fichiers sont
conservés dans la session Streamlit (encodés en base64) et inclus dans la
sauvegarde JSON complète (page d'accueil) pour ne pas être perdus d'une
session à l'autre. Ce n'est pas un coffre-fort documentaire — limitez le
nombre et la taille des fichiers attachés.
"""
from __future__ import annotations

import base64
from datetime import datetime

import streamlit as st

MAX_FICHIERS_PAR_DOSSIER = 10
MAX_TAILLE_OCTETS = 5 * 1024 * 1024  # 5 Mo par fichier — limite raisonnable pour une session Streamlit


def get_attachments() -> dict[str, list[dict]]:
    if "dossiers_attachments" not in st.session_state:
        st.session_state["dossiers_attachments"] = {}
    return st.session_state["dossiers_attachments"]


def set_attachments(data: dict[str, list[dict]]) -> None:
    st.session_state["dossiers_attachments"] = data


def list_for(dossier_id: str) -> list[dict]:
    return get_attachments().get(dossier_id, [])


def add_attachment(dossier_id: str, uploaded_file) -> tuple[bool, str]:
    data = get_attachments()
    fichiers = data.setdefault(dossier_id, [])
    if len(fichiers) >= MAX_FICHIERS_PAR_DOSSIER:
        return False, f"Limite de {MAX_FICHIERS_PAR_DOSSIER} pièces jointes par dossier atteinte."
    contenu = uploaded_file.getvalue()
    if len(contenu) > MAX_TAILLE_OCTETS:
        return False, f"« {uploaded_file.name} » dépasse la limite de 5 Mo pour cette session."
    fichiers.append({
        "nom": uploaded_file.name,
        "type": uploaded_file.type or "application/octet-stream",
        "taille_octets": len(contenu),
        "date_ajout": datetime.now().isoformat(timespec="seconds"),
        "data_b64": base64.b64encode(contenu).decode("ascii"),
    })
    set_attachments(data)
    return True, f"« {uploaded_file.name} » attaché au dossier {dossier_id}."


def remove_attachment(dossier_id: str, index: int) -> None:
    data = get_attachments()
    fichiers = data.get(dossier_id, [])
    if 0 <= index < len(fichiers):
        fichiers.pop(index)
        data[dossier_id] = fichiers
        set_attachments(data)


def decode(attachment: dict) -> bytes:
    return base64.b64decode(attachment["data_b64"])


def total_count() -> int:
    return sum(len(v) for v in get_attachments().values())
