"""Couche de stockage partagée et persistante (SQLite), générique (table par
table), utilisée par `dossiers.py`, `transmissions.py` et `attachments.py`.

**Pourquoi ce module existe — la faille qu'il corrige** : la version initiale
du prototype gardait tout dans `st.session_state`, qui est isolé **par
session de navigateur**. Deux agents de l'AER ouvrant l'application dans
deux onglets différents voyaient donc chacun un registre vide et
indépendant — ce qui contredit l'objectif même de l'outil (coordination et
traçabilité partagées entre services). Ce module fait persister les données
dans un fichier SQLite unique, partagé par tous les utilisateurs connectés
au **même processus serveur** (la connexion est mise en cache par
`st.cache_resource`, donc un seul objet, réutilisé par toutes les sessions),
avec le mode WAL pour des écritures concurrentes raisonnables en usage
pilote (quelques dizaines d'utilisateurs simultanés, pas une charge de
production à grande échelle).

**Limite honnête à connaître avant un déploiement réel** : ce mécanisme
partage les données entre tous les utilisateurs d'UN MÊME processus
Streamlit en cours d'exécution, sur UN SEUL serveur (pas de réplication
multi-instance : SQLite ne s'y prête pas). Il ne survit pas non plus à un
redémarrage si le disque qui contient le fichier `.db` n'est pas lui-même
persistant — c'est le cas sur Streamlit Community Cloud, dont le système de
fichiers est réinitialisé à chaque redéploiement ou réveil de veille. Pour
un usage pilote réel durable, hébergez l'application sur un serveur où
`data/` est un répertoire qui survit aux redémarrages (volume Docker, VM de
l'AER, disque persistant d'un PaaS), et sauvegardez régulièrement le fichier
`.db` (ou utilisez l'export JSON complet toujours disponible sur la page
d'accueil — il reste le filet de sécurité ultime, inchangé).
"""
from __future__ import annotations

import base64
import os
import sqlite3
from datetime import date, datetime
from pathlib import Path
from typing import Any, Iterable

import streamlit as st

APP_DIR = Path(__file__).resolve().parent.parent
DEFAULT_DATA_DIR = APP_DIR / "data"
DB_PATH = Path(os.environ.get("AER_DOSSIERS_DB_PATH", str(DEFAULT_DATA_DIR / "suivi_dossiers.db")))
ATTACHMENTS_DIR = Path(os.environ.get("AER_DOSSIERS_ATTACHMENTS_DIR", str(DEFAULT_DATA_DIR / "attachments")))

MAX_FICHIERS_PAR_DOSSIER = 10
MAX_TAILLE_OCTETS = 5 * 1024 * 1024  # 5 Mo par fichier

SCHEMA = """
CREATE TABLE IF NOT EXISTS dossiers (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    numero TEXT UNIQUE NOT NULL,
    date_reception TEXT,
    objet TEXT,
    type_dossier TEXT,
    canal_reception TEXT,
    direction_concernee TEXT,
    service_destinataire TEXT,
    statut TEXT,
    priorite TEXT,
    echeance_prevue TEXT,
    agent_en_charge TEXT,
    reference_externe TEXT,
    notes TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS transmissions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    numero_dossier TEXT NOT NULL,
    date TEXT,
    service_source TEXT,
    service_destination TEXT,
    sens TEXT,
    delai_imparti_jours INTEGER,
    commentaire TEXT,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS attachments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    numero_dossier TEXT NOT NULL,
    nom TEXT,
    type TEXT,
    taille_octets INTEGER,
    chemin_fichier TEXT,
    date_ajout TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS audit_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    horodatage TEXT NOT NULL,
    numero_dossier TEXT,
    champ TEXT,
    ancienne_valeur TEXT,
    nouvelle_valeur TEXT,
    poste_auteur TEXT,
    source TEXT
);

CREATE INDEX IF NOT EXISTS idx_transmissions_numero ON transmissions(numero_dossier);
CREATE INDEX IF NOT EXISTS idx_attachments_numero ON attachments(numero_dossier);
CREATE INDEX IF NOT EXISTS idx_audit_numero ON audit_log(numero_dossier);
"""


@st.cache_resource(show_spinner=False)
def get_connection() -> sqlite3.Connection:
    """Connexion unique, partagée par tous les utilisateurs de ce processus
    serveur (mise en cache par `st.cache_resource`, contrairement à
    `st.session_state` qui serait isolé par session)."""
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    ATTACHMENTS_DIR.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH), check_same_thread=False)
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute("PRAGMA busy_timeout=5000;")
    conn.execute("PRAGMA foreign_keys=ON;")
    conn.executescript(SCHEMA)
    conn.commit()
    return conn


def reset_for_tests(db_path: Path) -> sqlite3.Connection:
    """Utilisé uniquement par la suite de tests : crée une base neuve à un
    chemin donné, sans passer par le cache Streamlit (qui survivrait entre
    les tests sinon)."""
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(db_path), check_same_thread=False)
    conn.execute("PRAGMA foreign_keys=ON;")
    conn.executescript(SCHEMA)
    conn.commit()
    return conn


def _now() -> str:
    return datetime.now().isoformat(timespec="seconds")


def log_audit(conn: sqlite3.Connection, numero_dossier: str | None, champ: str,
              ancienne_valeur: Any, nouvelle_valeur: Any, poste_auteur: str | None,
              source: str) -> None:
    conn.execute(
        "INSERT INTO audit_log (horodatage, numero_dossier, champ, ancienne_valeur, nouvelle_valeur, "
        "poste_auteur, source) VALUES (?, ?, ?, ?, ?, ?, ?)",
        (_now(), numero_dossier, champ,
         "" if ancienne_valeur is None else str(ancienne_valeur),
         "" if nouvelle_valeur is None else str(nouvelle_valeur),
         poste_auteur or "(non identifié)", source),
    )


# ---------------------------------------------------------------------------
# Dossiers
# ---------------------------------------------------------------------------
DOSSIER_DB_COLUMNS = [
    "date_reception", "objet", "type_dossier", "canal_reception", "direction_concernee",
    "service_destinataire", "statut", "priorite", "echeance_prevue", "agent_en_charge",
    "reference_externe", "notes",
]


def fetch_dossiers() -> list[dict]:
    conn = get_connection()
    rows = conn.execute(
        f"SELECT id, numero, {', '.join(DOSSIER_DB_COLUMNS)} FROM dossiers ORDER BY id"
    ).fetchall()
    cols = ["id", "numero"] + DOSSIER_DB_COLUMNS
    return [dict(zip(cols, r)) for r in rows]


def insert_dossier(fields: dict, poste_auteur: str | None, source: str = "Nouveau dossier") -> str:
    """Insère un nouveau dossier et lui attribue un numéro stable
    (« AER-{année}-{id:04d} »), basé sur l'identifiant auto-incrémenté
    interne qui n'est jamais réutilisé même après suppression — contrairement
    à l'ancien calcul `len(df) + 1`, qui pouvait entrer en collision avec un
    numéro existant dès qu'un dossier avait été supprimé entre-temps."""
    conn = get_connection()
    now = _now()
    with conn:
        cur = conn.execute(
            f"INSERT INTO dossiers (numero, {', '.join(DOSSIER_DB_COLUMNS)}, created_at, updated_at) "
            f"VALUES ('', {', '.join(['?'] * len(DOSSIER_DB_COLUMNS))}, ?, ?)",
            tuple(fields.get(c) for c in DOSSIER_DB_COLUMNS) + (now, now),
        )
        new_id = cur.lastrowid
        numero = f"AER-{date.today().strftime('%Y')}-{new_id:04d}"
        conn.execute("UPDATE dossiers SET numero=? WHERE id=?", (numero, new_id))
        log_audit(conn, numero, "(dossier créé)", None, fields.get("objet"), poste_auteur, source)
    return numero


def update_dossier_field(dossier_id: int, numero: str, champ_db: str, ancienne_valeur: Any,
                          nouvelle_valeur: Any, poste_auteur: str | None, source: str) -> None:
    conn = get_connection()
    with conn:
        conn.execute(f"UPDATE dossiers SET {champ_db}=?, updated_at=? WHERE id=?",
                      (nouvelle_valeur, _now(), dossier_id))
        log_audit(conn, numero, champ_db, ancienne_valeur, nouvelle_valeur, poste_auteur, source)


def delete_dossier(dossier_id: int, numero: str, snapshot: str, poste_auteur: str | None,
                    source: str) -> None:
    conn = get_connection()
    with conn:
        log_audit(conn, numero, "(dossier supprimé)", snapshot, None, poste_auteur, source)
        conn.execute("DELETE FROM dossiers WHERE id=?", (dossier_id,))
        conn.execute("DELETE FROM transmissions WHERE numero_dossier=?", (numero,))
        for att in conn.execute("SELECT chemin_fichier FROM attachments WHERE numero_dossier=?",
                                 (numero,)).fetchall():
            try:
                Path(att[0]).unlink(missing_ok=True)
            except OSError:
                pass
        conn.execute("DELETE FROM attachments WHERE numero_dossier=?", (numero,))


def replace_all_dossiers(records: list[dict], poste_auteur: str | None, source: str) -> int:
    """Remplace tout le registre (utilisé par la restauration de sauvegarde
    JSON et par le chargement d'un CSV complet). `records` utilise les noms
    de colonnes DB (voir `DOSSIER_DB_COLUMNS`)."""
    conn = get_connection()
    with conn:
        conn.execute("DELETE FROM dossiers")
        now = _now()
        for rec in records:
            cur = conn.execute(
                f"INSERT INTO dossiers (numero, {', '.join(DOSSIER_DB_COLUMNS)}, created_at, updated_at) "
                f"VALUES ('', {', '.join(['?'] * len(DOSSIER_DB_COLUMNS))}, ?, ?)",
                tuple(rec.get(c) for c in DOSSIER_DB_COLUMNS) + (now, now),
            )
            new_id = cur.lastrowid
            numero = rec.get("numero") or f"AER-{date.today().strftime('%Y')}-{new_id:04d}"
            conn.execute("UPDATE dossiers SET numero=? WHERE id=?", (numero, new_id))
        log_audit(conn, None, "(registre entier)", None, f"{len(records)} dossier(s) restauré(s)",
                  poste_auteur, source)
    return len(records)


# ---------------------------------------------------------------------------
# Transmissions
# ---------------------------------------------------------------------------
TRANSMISSION_DB_COLUMNS = ["numero_dossier", "date", "service_source", "service_destination", "sens",
                           "delai_imparti_jours", "commentaire"]


def fetch_transmissions() -> list[dict]:
    conn = get_connection()
    rows = conn.execute(
        f"SELECT id, {', '.join(TRANSMISSION_DB_COLUMNS)} FROM transmissions ORDER BY id"
    ).fetchall()
    cols = ["id"] + TRANSMISSION_DB_COLUMNS
    return [dict(zip(cols, r)) for r in rows]


def insert_transmission(fields: dict, poste_auteur: str | None,
                         source: str = "Transmission") -> int:
    conn = get_connection()
    with conn:
        cur = conn.execute(
            f"INSERT INTO transmissions ({', '.join(TRANSMISSION_DB_COLUMNS)}, created_at) "
            f"VALUES ({', '.join(['?'] * len(TRANSMISSION_DB_COLUMNS))}, ?)",
            tuple(fields.get(c) for c in TRANSMISSION_DB_COLUMNS) + (_now(),),
        )
        log_audit(conn, fields.get("numero_dossier"), "(transmission)",
                  fields.get("service_source"), fields.get("service_destination"), poste_auteur, source)
    return cur.lastrowid


def update_transmission_row(row_id: int, changes: dict, poste_auteur: str | None, source: str) -> None:
    conn = get_connection()
    with conn:
        for champ, (ancienne, nouvelle) in changes.items():
            conn.execute(f"UPDATE transmissions SET {champ}=? WHERE id=?", (nouvelle, row_id))
        numero = conn.execute("SELECT numero_dossier FROM transmissions WHERE id=?", (row_id,)).fetchone()
        for champ, (ancienne, nouvelle) in changes.items():
            log_audit(conn, numero[0] if numero else None, f"transmission.{champ}", ancienne, nouvelle,
                      poste_auteur, source)


def delete_transmission_row(row_id: int, poste_auteur: str | None, source: str) -> None:
    conn = get_connection()
    with conn:
        row = conn.execute("SELECT numero_dossier FROM transmissions WHERE id=?", (row_id,)).fetchone()
        conn.execute("DELETE FROM transmissions WHERE id=?", (row_id,))
        log_audit(conn, row[0] if row else None, "(transmission supprimée)", row_id, None,
                  poste_auteur, source)


def replace_all_transmissions(records: list[dict], poste_auteur: str | None, source: str) -> int:
    conn = get_connection()
    with conn:
        conn.execute("DELETE FROM transmissions")
        now = _now()
        for rec in records:
            conn.execute(
                f"INSERT INTO transmissions ({', '.join(TRANSMISSION_DB_COLUMNS)}, created_at) "
                f"VALUES ({', '.join(['?'] * len(TRANSMISSION_DB_COLUMNS))}, ?)",
                tuple(rec.get(c) for c in TRANSMISSION_DB_COLUMNS) + (now,),
            )
        log_audit(conn, None, "(journal entier)", None, f"{len(records)} transmission(s) restaurée(s)",
                  poste_auteur, source)
    return len(records)


# ---------------------------------------------------------------------------
# Pièces jointes — métadonnées en base, octets sur disque (évite de faire
# grossir la base SQLite elle-même avec des blobs volumineux).
# ---------------------------------------------------------------------------
def list_attachments(numero_dossier: str) -> list[dict]:
    conn = get_connection()
    rows = conn.execute(
        "SELECT id, nom, type, taille_octets, chemin_fichier, date_ajout FROM attachments "
        "WHERE numero_dossier=? ORDER BY id", (numero_dossier,),
    ).fetchall()
    return [dict(zip(["id", "nom", "type", "taille_octets", "chemin_fichier", "date_ajout"], r))
            for r in rows]


def count_attachments(numero_dossier: str | None = None) -> int:
    conn = get_connection()
    if numero_dossier:
        return conn.execute("SELECT COUNT(*) FROM attachments WHERE numero_dossier=?",
                             (numero_dossier,)).fetchone()[0]
    return conn.execute("SELECT COUNT(*) FROM attachments").fetchone()[0]


def add_attachment(numero_dossier: str, uploaded_file, poste_auteur: str | None) -> tuple[bool, str]:
    if count_attachments(numero_dossier) >= MAX_FICHIERS_PAR_DOSSIER:
        return False, f"Limite de {MAX_FICHIERS_PAR_DOSSIER} pièces jointes par dossier atteinte."
    contenu = uploaded_file.getvalue()
    if len(contenu) > MAX_TAILLE_OCTETS:
        return False, f"« {uploaded_file.name} » dépasse la limite de 5 Mo."

    conn = get_connection()
    dossier_dir = ATTACHMENTS_DIR / numero_dossier
    dossier_dir.mkdir(parents=True, exist_ok=True)
    now = _now()
    with conn:
        cur = conn.execute(
            "INSERT INTO attachments (numero_dossier, nom, type, taille_octets, chemin_fichier, date_ajout) "
            "VALUES (?, ?, ?, ?, '', ?)",
            (numero_dossier, uploaded_file.name, uploaded_file.type or "application/octet-stream",
             len(contenu), now),
        )
        att_id = cur.lastrowid
        chemin = dossier_dir / f"{att_id}_{uploaded_file.name}"
        chemin.write_bytes(contenu)
        conn.execute("UPDATE attachments SET chemin_fichier=? WHERE id=?", (str(chemin), att_id))
        log_audit(conn, numero_dossier, "(pièce jointe ajoutée)", None, uploaded_file.name,
                  poste_auteur, "Pièce jointe")
    return True, f"« {uploaded_file.name} » attaché au dossier {numero_dossier}."


def remove_attachment(attachment_id: int, poste_auteur: str | None) -> None:
    conn = get_connection()
    with conn:
        row = conn.execute("SELECT numero_dossier, nom, chemin_fichier FROM attachments WHERE id=?",
                            (attachment_id,)).fetchone()
        if row is None:
            return
        numero, nom, chemin = row
        if chemin:
            try:
                Path(chemin).unlink(missing_ok=True)
            except OSError:
                pass
        conn.execute("DELETE FROM attachments WHERE id=?", (attachment_id,))
        log_audit(conn, numero, "(pièce jointe retirée)", nom, None, poste_auteur, "Pièce jointe")


def decode_attachment(attachment: dict) -> bytes:
    chemin = attachment.get("chemin_fichier")
    if chemin and Path(chemin).exists():
        return Path(chemin).read_bytes()
    if attachment.get("data_b64"):  # compatibilité avec une ancienne sauvegarde JSON
        return base64.b64decode(attachment["data_b64"])
    return b""


def fetch_all_attachments_for_backup() -> dict[str, list[dict]]:
    """Regroupe toutes les pièces jointes par dossier, octets encodés en
    base64 — format utilisé par la sauvegarde JSON complète (inchangé pour
    rester compatible avec une sauvegarde de l'ancienne version)."""
    conn = get_connection()
    rows = conn.execute(
        "SELECT numero_dossier, nom, type, taille_octets, chemin_fichier, date_ajout FROM attachments "
        "ORDER BY numero_dossier, id"
    ).fetchall()
    out: dict[str, list[dict]] = {}
    for numero, nom, typ, taille, chemin, date_ajout in rows:
        contenu = b""
        if chemin and Path(chemin).exists():
            contenu = Path(chemin).read_bytes()
        out.setdefault(numero, []).append({
            "nom": nom, "type": typ, "taille_octets": taille, "date_ajout": date_ajout,
            "data_b64": base64.b64encode(contenu).decode("ascii"),
        })
    return out


def replace_all_attachments(data: dict[str, list[dict]], poste_auteur: str | None, source: str) -> int:
    conn = get_connection()
    with conn:
        for chemin, in conn.execute("SELECT chemin_fichier FROM attachments").fetchall():
            if chemin:
                try:
                    Path(chemin).unlink(missing_ok=True)
                except OSError:
                    pass
        conn.execute("DELETE FROM attachments")
        now = _now()
        total = 0
        for numero, fichiers in (data or {}).items():
            dossier_dir = ATTACHMENTS_DIR / numero
            dossier_dir.mkdir(parents=True, exist_ok=True)
            for f in fichiers:
                contenu = base64.b64decode(f["data_b64"]) if f.get("data_b64") else b""
                cur = conn.execute(
                    "INSERT INTO attachments (numero_dossier, nom, type, taille_octets, chemin_fichier, "
                    "date_ajout) VALUES (?, ?, ?, ?, '', ?)",
                    (numero, f.get("nom"), f.get("type"), f.get("taille_octets", len(contenu)),
                     f.get("date_ajout", now)),
                )
                att_id = cur.lastrowid
                chemin = dossier_dir / f"{att_id}_{f.get('nom', 'fichier')}"
                chemin.write_bytes(contenu)
                conn.execute("UPDATE attachments SET chemin_fichier=? WHERE id=?", (str(chemin), att_id))
                total += 1
        log_audit(conn, None, "(pièces jointes)", None, f"{total} fichier(s) restauré(s)",
                  poste_auteur, source)
    return total


# ---------------------------------------------------------------------------
# Audit log — journal des modifications directes
# ---------------------------------------------------------------------------
def fetch_audit_log(numero_dossier: str | None = None, limit: int = 500) -> list[dict]:
    conn = get_connection()
    if numero_dossier:
        rows = conn.execute(
            "SELECT horodatage, numero_dossier, champ, ancienne_valeur, nouvelle_valeur, poste_auteur, "
            "source FROM audit_log WHERE numero_dossier=? ORDER BY id DESC LIMIT ?",
            (numero_dossier, limit),
        ).fetchall()
    else:
        rows = conn.execute(
            "SELECT horodatage, numero_dossier, champ, ancienne_valeur, nouvelle_valeur, poste_auteur, "
            "source FROM audit_log ORDER BY id DESC LIMIT ?", (limit,),
        ).fetchall()
    cols = ["Horodatage", "N° dossier", "Champ modifié", "Ancienne valeur", "Nouvelle valeur",
            "Poste auteur", "Source"]
    return [dict(zip(cols, r)) for r in rows]
