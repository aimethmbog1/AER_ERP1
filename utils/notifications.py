"""Centre de notifications / liste de tâches personnelle — inspiré du
« Worklist » et de la cloche de notifications d'Oracle Cloud ERP : plutôt
qu'un flux d'alertes générique, une liste courte et actionnable de ce qui
attend une DÉCISION ou une ACTION du poste actuellement simulé (barre
latérale), calculée à la volée à partir des données déjà saisies — aucune
table de notifications séparée, donc rien à synchroniser ni à purger : une
notification disparaît d'elle-même dès que la situation qui la justifiait
change (dossier traité, approbation décidée, échéance repoussée).

Trois sources, par ordre de gravité :
  1. demandes d'approbation **en attente** dont le poste est l'approbateur
     désigné (et en premier, celles dont l'échéance propre est dépassée) ;
  2. dossiers **en retard** actuellement à ce poste ;
  3. dossiers à **échéance proche** (≤ 3 jours) actuellement à ce poste.

Sans poste sélectionné (vue globale), ce module ne renvoie rien : une
notification « personnelle » n'a de sens que rattachée à un poste, exactement
comme le filtre « mes dossiers » déjà présent sur le Registre."""
from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from . import workflow as wf


@dataclass(frozen=True)
class Notification:
    gravite: str  # "retard" | "echeance" | "approbation"
    titre: str
    detail: str
    numero_dossier: str | None


def _approbations_notifications(poste: str) -> list[Notification]:
    pending = wf.pending_for(poste)
    if pending.empty:
        return []
    today = pd.Timestamp(pd.Timestamp.now().date())
    out = []
    for _, r in pending.sort_values("Échéance", na_position="last").iterrows():
        en_retard = pd.notna(r["Échéance"]) and r["Échéance"] < today
        titre = f"Approbation attendue — {r['Étape'] or 'Étape'}"
        if en_retard:
            titre = "⏰ " + titre + " (échéance dépassée)"
        out.append(Notification(
            gravite="approbation", titre=titre,
            detail=f"{r['N° dossier']} · demandé par {r['Demandé par'] or '—'}",
            numero_dossier=r["N° dossier"],
        ))
    return out


def _dossiers_notifications(register_with_derived: pd.DataFrame, poste: str) -> list[Notification]:
    mine = register_with_derived[register_with_derived["Service destinataire actuel"] == poste]
    out = []
    for _, r in mine[mine["En retard"]].sort_values("Jours de retard", ascending=False).iterrows():
        out.append(Notification(
            gravite="retard", titre=f"Dossier en retard ({int(r['Jours de retard'])} j)",
            detail=f"{r['N° dossier']} — {r['Objet']}", numero_dossier=r["N° dossier"],
        ))
    proche = mine[mine["Échéance proche"] & ~mine["En retard"]] if "Échéance proche" in mine.columns else mine.iloc[0:0]
    for _, r in proche.iterrows():
        out.append(Notification(
            gravite="echeance", titre="Échéance proche (≤ 3 j)",
            detail=f"{r['N° dossier']} — {r['Objet']}", numero_dossier=r["N° dossier"],
        ))
    return out


_ORDRE_GRAVITE = {"approbation": 0, "retard": 1, "echeance": 2}


def worklist_for(poste: str | None, register_with_derived: pd.DataFrame) -> list[Notification]:
    """Liste complète, triée par gravité, pour le poste donné. Renvoie une
    liste vide si aucun poste n'est sélectionné (vue globale)."""
    if not poste:
        return []
    items = _approbations_notifications(poste)
    if not register_with_derived.empty:
        items += _dossiers_notifications(register_with_derived, poste)
    return sorted(items, key=lambda n: _ORDRE_GRAVITE.get(n.gravite, 9))


def count_for(poste: str | None, register_with_derived: pd.DataFrame) -> int:
    return len(worklist_for(poste, register_with_derived))
