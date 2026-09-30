"""Structure réelle de l'organigramme de l'AER (Agence d'Électrification Rurale
du Cameroun), encodée à partir de deux documents fournis par l'utilisateur :
  - l'organigramme officiel « ORGANIGRAMME AER 2025 » (PDF),
  - la description textuelle du fonctionnement des directions (extrait de mémoire,
    pages 16-18).

Ce module fait deux choses :
  1. Il expose la structure « classification » (Direction / Sous-Direction /
     Service), utilisée pour catégoriser un dossier (page Registre).
  2. Il expose un vrai **graphe hiérarchique avec rangs**, utilisé pour
     contraindre le routage des dossiers (page Transmissions) : un dossier ne
     peut être transmis qu'à un palier directement inférieur, à un poste de
     même rang, ou en retour vers le supérieur/l'émetteur — jamais en sautant
     des niveaux, conformément au fonctionnement réel décrit par l'utilisateur.

Rangs utilisés, d'après la légende de l'organigramme officiel :
  « Chef division et conseiller technique avec rang de directeur »,
  « Chef de cellule avec rang de sous-directeur »,
  « Chargé d'étude avec rang de chef de service ».
Les 4 chefs d'antenne régionale sont traités au même palier que les directeurs
de département, conformément à l'exemple donné par l'utilisateur pour cette
application (« le DG transmet aux Directeurs de département, aux chefs
d'antennes, aux conseillers techniques ») — cette équivalence n'est pas
explicitement écrite dans la légende officielle, elle reflète la logique de
transmission décrite pour cet outil, pas nécessairement une grille indiciaire
formelle de l'AER.

Réserves honnêtes conservées telles quelles :
  - Le texte source liste deux fois « Service des Marchés » (une fois sous la
    Sous-Direction des Affaires Administratives, une fois sous celle des
    Ressources Humaines) — les deux sont conservés, avec un libellé
    d'affichage distinct pour éviter toute confusion dans les listes de choix.
  - La légende de l'organigramme annonce 5 Directions / 17 Sous-Directions /
    27 Services ; notre décompte à partir du texte détaillé peut différer
    légèrement (voir la page Organigramme).
"""
from __future__ import annotations

from dataclasses import dataclass

DIRECTION_GENERALE = "Direction Générale"
EXTERNE = "Externe (hors AER)"

RANG_DG = "Direction Générale"
RANG_DIRECTION = "Directeur / Chef d'Antenne"
RANG_SOUSDIR = "Sous-Directeur / Chef de Cellule"
RANG_SERVICE = "Chef de Service"
RANG_EXTERNE = "Externe"

RANGS_ORDRE = [RANG_DG, RANG_DIRECTION, RANG_SOUSDIR, RANG_SERVICE]

ORGANES_GOUVERNANCE = [
    "Conseil d'Administration",
    "Attaché au Cabinet du PCA",
]

# ---------------------------------------------------------------------------
# Rattachés à la Direction Générale, par rang réel (légende de l'organigramme)
# ---------------------------------------------------------------------------
RATTACHES_DG_RANG_DIRECTEUR = [
    "Conseiller technique",
    "Division du Contrôle de Gestion et du Suivi de la Performance",
]
RATTACHES_DG_RANG_SOUSDIR = [
    "Cellule de la validation du budget, des engagements et des paiements",
    "Cellule de la comptabilité-matières et de la gestion du patrimoine",
    "Cellule de l'audit et de la gestion des risques",
]
RATTACHES_DG_RANG_SERVICE = [
    "Service de la Communication et de la Documentation",
    "Service de la Traduction et du Bilinguisme",
    "Service Informatique",
    "Service Juridique",
    "Service du Courrier, de la Liaison et des Archives",
    "Secrétariat Particulier du Directeur Général",
]
SERVICES_RATTACHES_DG = RATTACHES_DG_RANG_DIRECTEUR + RATTACHES_DG_RANG_SOUSDIR + RATTACHES_DG_RANG_SERVICE

ANTENNES_REGIONALES = [
    "Antenne Régionale du Centre, Sud et Est",
    "Antenne Régionale du Littoral et du Sud-Ouest",
    "Antenne Régionale du Nord-Ouest et Ouest",
    "Antenne Régionale du Nord, Adamaoua et Extrême-Nord",
]

# ---------------------------------------------------------------------------
# Directions centrales -> Sous-directions (avec code court) -> Services
# ---------------------------------------------------------------------------
DIRECTIONS: dict[str, dict[str, dict]] = {
    "DECDP — Direction des Études, de la Coopération et du Développement des Partenariats": {
        "Sous-Direction des Études, de la Planification et de la Maturation des Projets": {
            "code": "DECDP-Études",
            "services": [
                "Service des Études et de la Centralisation des Données",
                "Service de l'Analyse et de la Maturation des Projets",
            ],
        },
        "Sous-Direction de la Recherche et de la Mobilisation des Financements": {
            "code": "DECDP-Financements",
            "services": [
                "Service des Financements Innovants des Projets/Programmes",
                "Service de la Prospection des Partenariats Financiers",
            ],
        },
        "Sous-Direction de la Promotion et du Développement des Partenariats": {
            "code": "DECDP-Partenariats",
            "services": [
                "Service de la Promotion et de la Vulgarisation de l'Électrification Rurale",
                "Service de la Coopération et des Partenariats avec les Investisseurs Nationaux et Internationaux",
            ],
        },
    },
    "DGOER — Direction de la Gestion des Ouvrages d'Électrification Rurale": {
        "Sous-Direction de la Production et de la Distribution": {
            "code": "DGOER-ProdDistrib",
            "services": ["Service de la Production", "Service de la Distribution"],
        },
        "Sous-Direction des Travaux et de la Maintenance": {
            "code": "DGOER-Travaux",
            "services": [
                "Service de la Maintenance des Ouvrages d'Électrification Rurale",
                "Service du Suivi des Travaux",
            ],
        },
        "Sous-Direction du Monitoring et des Statistiques Énergétiques": {
            "code": "DGOER-Monitoring",
            "services": ["Service des Statistiques Énergétiques", "Service du Monitoring"],
        },
    },
    "DAAF — Direction des Affaires Administratives et Financières": {
        "Sous-Direction des Affaires Administratives": {
            "code": "DAAF-Admin",
            "services": ["Service Administratif", "Service des Marchés"],
        },
        "Sous-Direction des Ressources Humaines": {
            "code": "DAAF-RH",
            "services": ["Service du Personnel", "Service des Marchés", "Service du Développement des Compétences"],
        },
        "Sous-Direction des Finances et de la Comptabilité": {
            "code": "DAAF-Finances",
            "services": ["Service du Budget et des Finances", "Service de la Comptabilité Générale et Analytique"],
        },
    },
}

LEGENDE_ORGANIGRAMME = {
    "Direction Générale": 1,
    "Directions (selon légende officielle)": 5,
    "Sous-Directions (selon légende officielle)": 17,
    "Services (selon légende officielle)": 27,
}


# ---------------------------------------------------------------------------
# API « classification » (rétro-compatible avec la page Registre)
# ---------------------------------------------------------------------------
def all_directions() -> list[str]:
    return [DIRECTION_GENERALE] + list(DIRECTIONS.keys())


def sous_directions_for(direction: str) -> list[str]:
    return list(DIRECTIONS.get(direction, {}).keys())


def services_for(direction: str, sous_direction: str | None = None) -> list[str]:
    if direction == DIRECTION_GENERALE:
        return SERVICES_RATTACHES_DG + ANTENNES_REGIONALES
    if sous_direction is None:
        out = []
        for sd in DIRECTIONS.get(direction, {}).values():
            out.extend(sd["services"])
        return out
    return DIRECTIONS.get(direction, {}).get(sous_direction, {}).get("services", [])


# ---------------------------------------------------------------------------
# Graphe hiérarchique (id, parent, rang) — utilisé pour le routage contraint
# et pour le graphe organigramme avec voyants de statut.
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class Node:
    id: str
    label: str
    parent_id: str | None
    rang: str


_NODES: dict[str, Node] = {}


def _add(node_id: str, parent_id: str | None, rang: str, label: str | None = None) -> None:
    _NODES[node_id] = Node(node_id, label or node_id, parent_id, rang)


_add(DIRECTION_GENERALE, None, RANG_DG)
for _e in RATTACHES_DG_RANG_DIRECTEUR:
    _add(_e, DIRECTION_GENERALE, RANG_DIRECTION)
for _e in ANTENNES_REGIONALES:
    _add(_e, DIRECTION_GENERALE, RANG_DIRECTION)
for _e in RATTACHES_DG_RANG_SOUSDIR:
    _add(_e, DIRECTION_GENERALE, RANG_SOUSDIR)
for _e in RATTACHES_DG_RANG_SERVICE:
    _add(_e, DIRECTION_GENERALE, RANG_SERVICE)

for _direction, _sous_dirs in DIRECTIONS.items():
    _add(_direction, DIRECTION_GENERALE, RANG_DIRECTION)
    for _sd, _info in _sous_dirs.items():
        _sd_id = f"{_sd} ({_info['code'].split('-')[0]})"
        _add(_sd_id, _direction, RANG_SOUSDIR, label=_sd)
        for _svc in _info["services"]:
            _svc_id = f"{_svc} ({_info['code']})"
            _add(_svc_id, _sd_id, RANG_SERVICE, label=_svc)

_add(EXTERNE, None, RANG_EXTERNE)

NODES: dict[str, Node] = _NODES


def all_node_ids() -> list[str]:
    """Tous les postes, dans l'ordre hiérarchique (DG puis rang par rang)."""
    order = {r: i for i, r in enumerate(RANGS_ORDRE + [RANG_EXTERNE])}
    return sorted(NODES.keys(), key=lambda n: (order[NODES[n].rang], NODES[n].id))


def node_rang(node_id: str) -> str | None:
    n = NODES.get(node_id)
    return n.rang if n else None


def node_parent(node_id: str) -> str | None:
    n = NODES.get(node_id)
    return n.parent_id if n else None


def children_of(node_id: str) -> list[str]:
    return [n.id for n in NODES.values() if n.parent_id == node_id]


def peers_of(node_id: str) -> list[str]:
    n = NODES.get(node_id)
    if n is None or n.rang in (RANG_DG, RANG_EXTERNE):
        return []
    return [m.id for m in NODES.values() if m.rang == n.rang and m.id != node_id]


def allowed_destinations(node_id: str) -> list[str]:
    """Postes vers lesquels un dossier peut être transmis depuis `node_id` :
    les enfants directs (descente hiérarchique), les postes de même rang
    (transmission latérale entre pairs), le supérieur hiérarchique direct
    (remontée / retour), et l'extérieur (tout poste peut correspondre avec
    l'extérieur de l'AER)."""
    if node_id == EXTERNE:
        return [DIRECTION_GENERALE]
    n = NODES.get(node_id)
    if n is None:
        return []
    dest = set(children_of(node_id)) | set(peers_of(node_id))
    if n.parent_id:
        dest.add(n.parent_id)
    dest.add(EXTERNE)
    dest.discard(node_id)
    return sorted(dest)


def is_authorized(source: str, destination: str) -> bool:
    if source == destination:
        return False
    return destination in allowed_destinations(source)


def direction_of(node_id: str) -> str:
    """Remonte l'arbre jusqu'au niveau « direction » (ou la Direction Générale
    elle-même) — utilisé pour classer/regrouper un poste dans les statistiques
    par direction, quel que soit le poste précis choisi comme destinataire."""
    current = NODES.get(node_id)
    if current is None or current.rang == RANG_EXTERNE:
        return EXTERNE
    if current.id == DIRECTION_GENERALE:
        return DIRECTION_GENERALE
    # Remonte jusqu'au premier ancêtre directement rattaché à la Direction Générale
    while current.parent_id is not None and current.parent_id != DIRECTION_GENERALE:
        current = NODES[current.parent_id]
    # `current` est maintenant un enfant direct de la DG : une direction centrale,
    # ou un poste/antenne/cellule rattaché directement à la DG.
    return current.id if current.id in DIRECTIONS else DIRECTION_GENERALE


def depth_of(node_id: str) -> int:
    """Profondeur dans l'arbre (0 = Direction Générale), pour la mise en page
    du graphe organigramme."""
    depth = 0
    current = NODES.get(node_id)
    while current and current.parent_id:
        depth += 1
        current = NODES.get(current.parent_id)
    return depth


def flat_entities() -> list[str]:
    return all_node_ids()


def compute_tree_layout() -> dict[str, tuple[float, float]]:
    """Calcule des coordonnées (x, y) pour un rendu en arbre classique
    (Direction Générale en haut, feuilles en bas), utilisées par le graphe
    organigramme avec voyants de statut. y = -profondeur ; x centré sur les
    enfants (calcul récursif post-ordre)."""
    positions: dict[str, tuple[float, float]] = {}
    next_x = [0.0]

    def visit(node_id: str) -> float:
        kids = children_of(node_id)
        depth = depth_of(node_id)
        if not kids:
            x = next_x[0]
            next_x[0] += 1.0
            positions[node_id] = (x, -depth)
            return x
        xs = [visit(k) for k in kids]
        x = sum(xs) / len(xs)
        positions[node_id] = (x, -depth)
        return x

    visit(DIRECTION_GENERALE)
    return positions


def hierarchy_rows() -> list[dict]:
    """Une ligne par nœud, avec son parent — utilisée pour le graphique icicle
    représentant l'organigramme réel (hors nœud Externe)."""
    rows = []
    for node_id in all_node_ids():
        n = NODES[node_id]
        if n.rang == RANG_EXTERNE:
            continue
        rows.append({"Entité": n.id, "Parent": n.parent_id or "", "Niveau": n.rang, "Libellé": n.label})
    return rows
