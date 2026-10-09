"""Recherche plein texte partagée — logique extraite de la page **Recherche
& registre courrier** pour être réutilisée telle quelle par la barre de
recherche globale de la page d'accueil (inspirée de la recherche globale
d'Oracle Cloud ERP, qui permet de retrouver un enregistrement depuis
n'importe quel écran plutôt que depuis un seul module de recherche dédié).
Une seule implémentation, deux points d'entrée dans l'interface — pas de
divergence possible entre « ce que trouve l'accueil » et « ce que trouve la
page Recherche »."""
from __future__ import annotations

import pandas as pd

CHAMPS_DOSSIER_RECHERCHES = [
    "N° dossier", "Objet", "Agent en charge", "Notes", "Référence externe (optionnel)",
    "Service destinataire actuel", "Direction concernée",
]


def search_dossiers(register: pd.DataFrame, requete: str) -> pd.DataFrame:
    if not requete or register.empty:
        return register.iloc[0:0]
    mask = pd.Series(False, index=register.index)
    for champ in CHAMPS_DOSSIER_RECHERCHES:
        if champ in register.columns:
            mask = mask | register[champ].astype(str).str.contains(requete, case=False, na=False)
    return register[mask]


def search_transmissions(log: pd.DataFrame, requete: str) -> pd.DataFrame:
    if not requete or log.empty:
        return log.iloc[0:0]
    mask = log["Commentaire"].astype(str).str.contains(requete, case=False, na=False)
    return log[mask]
