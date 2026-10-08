"""Journal des transmissions entre services — c'est le cœur de la traçabilité :
le mémoire diagnostique des difficultés de suivi et de coordination faute de
trace centralisée des mouvements d'un dossier entre entités. Ce journal :
  - est stocké dans la base SQLite partagée (voir `utils/db.py`), commune à
    tous les utilisateurs connectés au même serveur — et non plus dans
    `st.session_state`, isolé par session de navigateur ;
  - n'accepte que des transmissions conformes au routage hiérarchique réel de
    l'AER (utils.orgchart.is_authorized) — pas de saut de niveau ;
  - distingue un mouvement « Aller » (descente/latéral) d'un « Retour » (vers
    l'émetteur du mouvement précédent pour ce dossier) ;
  - calcule le temps réellement passé à chaque étape à partir des dates
    saisies, et signale un dépassement de délai imparti si vous en fixez un.
"""
from __future__ import annotations

from datetime import date, datetime

import pandas as pd
import streamlit as st

from . import db
from . import orgchart as og

LOG_COLUMNS = [
    "N° dossier",
    "Date",
    "Service source",
    "Service destination",
    "Sens",
    "Délai imparti (jours)",
    "Commentaire",
]

_DISPLAY_TO_DB = {
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


def empty_log() -> pd.DataFrame:
    df = pd.DataFrame(columns=LOG_COLUMNS)
    df["Date"] = pd.to_datetime(df["Date"])
    df["Délai imparti (jours)"] = pd.to_numeric(df["Délai imparti (jours)"])
    return df


def get_log() -> pd.DataFrame:
    rows = db.fetch_transmissions()
    if not rows:
        return empty_log()
    data = [{
        "N° dossier": r["numero_dossier"],
        "Date": r["date"],
        "Service source": r["service_source"],
        "Service destination": r["service_destination"],
        "Sens": r["sens"],
        "Délai imparti (jours)": r["delai_imparti_jours"],
        "Commentaire": r["commentaire"],
    } for r in rows]
    df = pd.DataFrame(data, columns=LOG_COLUMNS)
    df["Date"] = pd.to_datetime(df["Date"], errors="coerce")
    df["Délai imparti (jours)"] = pd.to_numeric(df["Délai imparti (jours)"], errors="coerce")
    # Même traitement que get_register() : une cellule texte vide, pas le mot
    # « None », pour un commentaire non renseigné.
    df["Commentaire"] = df["Commentaire"].fillna("")
    return df


def _same_content(a: pd.DataFrame, b: pd.DataFrame) -> bool:
    if len(a) != len(b):
        return False
    a2 = a.reset_index(drop=True).apply(lambda col: col.map(_cell_to_text))
    b2 = b.reset_index(drop=True).apply(lambda col: col.map(_cell_to_text))
    return a2.equals(b2)


def set_log(df: pd.DataFrame) -> None:
    """Resynchronise le journal complet avec la base après une édition
    directe du tableau (page Transmissions). N'écrit — et ne journalise dans
    le journal d'audit — que s'il y a un changement réel, pour éviter de
    recréer inutilement toutes les lignes à chaque rafraîchissement de
    page."""
    current = get_log()
    if _same_content(current, df):
        return

    records = []
    for _, row in df.iterrows():
        delai = row.get("Délai imparti (jours)")
        records.append({
            "numero_dossier": _cell_to_text(row.get("N° dossier")),
            "date": _cell_to_text(row.get("Date")),
            "service_source": _cell_to_text(row.get("Service source")),
            "service_destination": _cell_to_text(row.get("Service destination")),
            "sens": _cell_to_text(row.get("Sens")),
            "delai_imparti_jours": None if pd.isna(delai) else int(delai),
            "commentaire": _cell_to_text(row.get("Commentaire")),
        })
    db.replace_all_transmissions(records, _poste_auteur(), "Édition directe du journal")


def last_movement_for(dossier_id: str) -> pd.Series | None:
    log = get_log()
    if log.empty:
        return None
    hist = log[log["N° dossier"] == dossier_id].sort_values("Date")
    return hist.iloc[-1] if not hist.empty else None


def suggested_return_target(dossier_id: str) -> str | None:
    """Le service vers lequel un « retour » serait naturel : la source du
    dernier mouvement enregistré pour ce dossier."""
    last = last_movement_for(dossier_id)
    return last["Service source"] if last is not None else None


def add_transmission(dossier_id: str, dt: date, source: str, destination: str,
                      commentaire: str, delai_impartis_jours: int | None = None) -> tuple[bool, str]:
    """Ajoute une transmission si elle respecte le routage hiérarchique réel.
    Renvoie (succès, message)."""
    if source == destination:
        return False, "La source et la destination sont identiques."
    if not og.is_authorized(source, destination):
        return False, (
            f"Transmission non autorisée : « {destination} » n'est ni un palier directement "
            f"inférieur, ni de même rang, ni le supérieur hiérarchique de « {source} ». "
            "Utilisez une étape intermédiaire de l'organigramme."
        )

    retour_cible = suggested_return_target(dossier_id)
    sens = "Retour" if destination == retour_cible else "Aller"

    fields = {
        "numero_dossier": dossier_id,
        "date": _cell_to_text(dt),
        "service_source": source,
        "service_destination": destination,
        "sens": sens,
        "delai_imparti_jours": delai_impartis_jours,
        "commentaire": commentaire,
    }
    db.insert_transmission(fields, _poste_auteur(), source="Transmission")
    return True, f"Transmission enregistrée ({sens}) : {source} → {destination}."


def history_for(dossier_id: str) -> pd.DataFrame:
    log = get_log()
    if log.empty:
        return log
    return log[log["N° dossier"] == dossier_id].sort_values("Date")


def temps_par_service(log: pd.DataFrame) -> pd.DataFrame:
    """Pour chaque dossier, calcule le temps écoulé entre une transmission
    vers un service et la transmission suivante (ou aujourd'hui si c'est la
    dernière) — mesure réelle du temps passé par service, calculée
    uniquement à partir des dates saisies. Signale un dépassement si un
    délai imparti a été fixé sur l'étape."""
    if log.empty:
        return pd.DataFrame(columns=["N° dossier", "Service", "Jours passés", "Délai imparti (jours)",
                                      "Dépassement", "Statut de la période"])

    rows = []
    today = pd.Timestamp(pd.Timestamp.now().date())
    for dossier_id, grp in log.sort_values("Date").groupby("N° dossier"):
        grp = grp.reset_index(drop=True)
        for i, r in grp.iterrows():
            debut = r["Date"]
            service = r["Service destination"]
            fin = grp.loc[i + 1, "Date"] if i + 1 < len(grp) else today
            jours = max((fin - debut).days, 0)
            statut = "Historique (service suivant atteint)" if i + 1 < len(grp) else "En cours (service actuel)"
            delai = r.get("Délai imparti (jours)")
            depassement = bool(pd.notna(delai) and jours > delai)
            rows.append({
                "N° dossier": dossier_id,
                "Service": service,
                "Jours passés": jours,
                "Délai imparti (jours)": delai,
                "Dépassement": depassement,
                "Statut de la période": statut,
            })
    return pd.DataFrame(rows)


def generer_bordereau(dossier_id: str, objet: str, source: str, destination: str,
                       dt: date, commentaire: str, agent: str = "") -> str:
    """Génère un bordereau de transmission texte, téléchargeable — pratique
    courante dans le suivi de courrier administratif, pour matérialiser
    l'envoi entre deux services."""
    return f"""BORDEREAU DE TRANSMISSION — AGENCE DE L'ÉLECTRIFICATION RURALE
{'=' * 64}

N° de dossier      : {dossier_id}
Objet              : {objet}
Date de transmission : {dt.strftime('%d/%m/%Y')}

Service émetteur   : {source}
Service destinataire : {destination}
Agent en charge    : {agent or '—'}

Observations :
{commentaire or '(aucune)'}

{'-' * 64}
Signature émetteur                         Signature destinataire (accusé de réception)


......................................     ......................................
Date : ____/____/________                  Date : ____/____/________

Document généré automatiquement par l'application de suivi des dossiers AER.
"""
