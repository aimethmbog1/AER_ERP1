"""Structure réelle de l'organigramme de l'AER (Agence d'Électrification Rurale
du Cameroun), encodée à partir de deux documents fournis par l'utilisateur :
  - l'organigramme officiel « ORGANIGRAMME AER 2025 » (PDF),
  - la description textuelle du fonctionnement des directions (extrait de mémoire,
    pages 16-18).

Cette structure sert de référentiel réel pour le routage des dossiers entre
entités (émetteur / destinataire), afin que l'application reste ancrée dans
l'organisation effective de l'AER plutôt que dans une hiérarchie inventée.

Deux réserves honnêtes, visibles dans les deux sources :
  - Le texte liste deux fois « Service des Marchés » (une fois sous la
    Sous-Direction des Affaires Administratives, une fois sous celle des
    Ressources Humaines) — préservé tel quel, sans correction arbitraire de
    notre part.
  - La légende de l'organigramme annonce 5 « Directions », 17 « Sous-Directions »
    et 27 « Services » ; le décompte obtenu en aplatissant la liste ci-dessous
    peut différer légèrement (les organes de gouvernance — Conseil
    d'Administration, Cabinet du PCA, Conseiller technique — ne sont pas tous
    comptés de la même façon selon les documents). Ce module n'essaie pas de
    forcer une réconciliation qui n'est pas dans la source.
"""
from __future__ import annotations

# ---------------------------------------------------------------------------
# Organes de gouvernance et services rattachés à la Direction Générale
# ---------------------------------------------------------------------------
ORGANES_GOUVERNANCE = [
    "Conseil d'Administration",
    "Attaché au Cabinet du PCA",
]

SERVICES_RATTACHES_DG = [
    "Conseiller technique",
    "Division du Contrôle de Gestion et du Suivi de la Performance",
    "Cellule de la validation du budget, des engagements et des paiements",
    "Cellule de la comptabilité-matières et de la gestion du patrimoine",
    "Cellule de l'audit et de la gestion des risques",
    "Service de la Communication et de la Documentation",
    "Service de la Traduction et du Bilinguisme",
    "Service Informatique",
    "Service Juridique",
    "Service du Courrier, de la Liaison et des Archives",
    "Secrétariat Particulier du Directeur Général",
]

ANTENNES_REGIONALES = [
    "Antenne Régionale du Centre, Sud et Est",
    "Antenne Régionale du Littoral et du Sud-Ouest",
    "Antenne Régionale du Nord-Ouest et Ouest",
    "Antenne Régionale du Nord, Adamaoua et Extrême-Nord",
]

# ---------------------------------------------------------------------------
# Directions centrales -> Sous-directions -> Services
# ---------------------------------------------------------------------------
DIRECTIONS: dict[str, dict] = {
    "DECDP — Direction des Études, de la Coopération et du Développement des Partenariats": {
        "Sous-Direction des Études, de la Planification et de la Maturation des Projets": [
            "Service des Études et de la Centralisation des Données",
            "Service de l'Analyse et de la Maturation des Projets",
        ],
        "Sous-Direction de la Recherche et de la Mobilisation des Financements": [
            "Service des Financements Innovants des Projets/Programmes",
            "Service de la Prospection des Partenariats Financiers",
        ],
        "Sous-Direction de la Promotion et du Développement des Partenariats": [
            "Service de la Promotion et de la Vulgarisation de l'Électrification Rurale",
            "Service de la Coopération et des Partenariats avec les Investisseurs Nationaux et Internationaux",
        ],
    },
    "DGOER — Direction de la Gestion des Ouvrages d'Électrification Rurale": {
        "Sous-Direction de la Production et de la Distribution": [
            "Service de la Production",
            "Service de la Distribution",
        ],
        "Sous-Direction des Travaux et de la Maintenance": [
            "Service de la Maintenance des Ouvrages d'Électrification Rurale",
            "Service du Suivi des Travaux",
        ],
        "Sous-Direction du Monitoring et des Statistiques Énergétiques": [
            "Service des Statistiques Énergétiques",
            "Service du Monitoring",
        ],
    },
    "DAAF — Direction des Affaires Administratives et Financières": {
        "Sous-Direction des Affaires Administratives": [
            "Service Administratif",
            "Service des Marchés",
        ],
        "Sous-Direction des Ressources Humaines": [
            "Service du Personnel",
            "Service des Marchés",
            "Service du Développement des Compétences",
        ],
        "Sous-Direction des Finances et de la Comptabilité": [
            "Service du Budget et des Finances",
            "Service de la Comptabilité Générale et Analytique",
        ],
    },
}

DIRECTION_GENERALE = "Direction Générale"


def all_directions() -> list[str]:
    return [DIRECTION_GENERALE] + list(DIRECTIONS.keys())


def sous_directions_for(direction: str) -> list[str]:
    return list(DIRECTIONS.get(direction, {}).keys())


def services_for(direction: str, sous_direction: str | None = None) -> list[str]:
    if direction == DIRECTION_GENERALE:
        return SERVICES_RATTACHES_DG + ANTENNES_REGIONALES
    if sous_direction is None:
        out = []
        for services in DIRECTIONS.get(direction, {}).values():
            out.extend(services)
        return out
    return DIRECTIONS.get(direction, {}).get(sous_direction, [])


def flat_entities() -> list[str]:
    """Liste plate de toutes les entités pouvant émettre/recevoir un dossier
    (utilisée pour les filtres et les sélecteurs qui n'ont pas besoin de la
    hiérarchie complète)."""
    out = [DIRECTION_GENERALE] + SERVICES_RATTACHES_DG + ANTENNES_REGIONALES
    for direction, sous_dirs in DIRECTIONS.items():
        out.append(direction)
        for sd, services in sous_dirs.items():
            out.append(sd)
            out.extend(services)
    # dédoublonnage en conservant l'ordre (ex. « Service des Marchés » apparaît deux fois)
    seen = set()
    unique = []
    for e in out:
        if e not in seen:
            seen.add(e)
            unique.append(e)
    return unique


def hierarchy_rows() -> list[dict]:
    """Une ligne par nœud, avec son parent — utilisée pour un graphique icicle/
    sunburst représentant l'organigramme réel."""
    rows = [{"Entité": DIRECTION_GENERALE, "Parent": "", "Niveau": "Direction Générale"}]
    for s in SERVICES_RATTACHES_DG:
        rows.append({"Entité": s, "Parent": DIRECTION_GENERALE, "Niveau": "Service rattaché"})
    for a in ANTENNES_REGIONALES:
        rows.append({"Entité": a, "Parent": DIRECTION_GENERALE, "Niveau": "Antenne régionale"})
    for direction, sous_dirs in DIRECTIONS.items():
        rows.append({"Entité": direction, "Parent": DIRECTION_GENERALE, "Niveau": "Direction centrale"})
        for sd, services in sous_dirs.items():
            # étiquette unique par direction pour éviter les collisions d'ID dans l'icicle
            sd_label = f"{sd} ({direction.split(' — ')[0]})"
            rows.append({"Entité": sd_label, "Parent": direction, "Niveau": "Sous-direction"})
            for svc in services:
                svc_label = f"{svc} ({direction.split(' — ')[0]})"
                rows.append({"Entité": svc_label, "Parent": sd_label, "Niveau": "Service"})
    return rows


LEGENDE_ORGANIGRAMME = {
    "Direction Générale": 1,
    "Directions (selon légende officielle)": 5,
    "Sous-Directions (selon légende officielle)": 17,
    "Services (selon légende officielle)": 27,
}
