"""Tests du routage hiérarchique (utils/orgchart.py) — c'est la règle métier
centrale de l'application : un dossier ne doit jamais pouvoir sauter un
niveau, sauf les deux exceptions assumées et documentées (Service du
Courrier, et l'extérieur)."""
from utils import orgchart as og


def test_dg_peut_transmettre_a_ses_subordonnes_directs():
    # Le Service Informatique est un service rattaché directement à la DG.
    assert og.is_authorized(og.DIRECTION_GENERALE, "Service Informatique")


def test_dg_ne_peut_pas_sauter_vers_un_service_d_une_direction():
    # Un service d'une sous-direction de la DGOER n'est pas un subordonné
    # direct de la DG : il faut passer par la direction puis la sous-direction.
    destinations = og.allowed_destinations(og.DIRECTION_GENERALE)
    service_profond = "Service de la Production (DGOER-ProdDistrib)"
    assert service_profond not in destinations


def test_transmission_laterale_entre_pairs_de_meme_rang():
    directions = [d for d in og.DIRECTIONS.keys()]
    assert len(directions) >= 2
    assert og.is_authorized(directions[0], directions[1]), "deux directions sont des pairs (même rang)"


def test_retour_vers_le_superieur_hierarchique():
    direction = next(iter(og.DIRECTIONS.keys()))
    sous_directions = og.sous_directions_for(direction)
    assert sous_directions
    sd_id = f"{sous_directions[0]} ({og.DIRECTIONS[direction][sous_directions[0]]['code'].split('-')[0]})"
    assert og.is_authorized(sd_id, direction), "une sous-direction doit pouvoir remonter vers sa direction"


def test_service_courrier_peut_joindre_n_importe_quel_poste():
    # Exception assumée et documentée : le bureau d'ordre peut acheminer vers
    # n'importe quel poste, quel que soit son rang.
    cible_profonde = "Service des Études et de la Centralisation des Données (DECDP-Études)"
    assert og.is_authorized(og.SERVICE_COURRIER, cible_profonde)


def test_aucun_autre_service_n_a_l_exception_du_courrier():
    # Un autre service de même rang (ex. Service Juridique) PEUT joindre un
    # service de même rang ailleurs dans l'organigramme (transmission
    # latérale entre pairs — règle générale, documentée dans le README).
    # Mais contrairement au Service du Courrier, il ne peut PAS joindre un
    # poste d'un rang différent (ici une sous-direction) qui n'est ni son
    # enfant, ni son pair, ni son supérieur direct : seule l'exception
    # assumée du bureau d'ordre permet ce saut de palier.
    direction = next(iter(og.DIRECTIONS.keys()))
    sous_direction = og.sous_directions_for(direction)[0]
    sd_id = f"{sous_direction} ({og.DIRECTIONS[direction][sous_direction]['code'].split('-')[0]})"

    assert not og.is_authorized("Service Juridique", sd_id)
    assert og.is_authorized(og.SERVICE_COURRIER, sd_id)


def test_externe_ne_peut_joindre_que_courrier_et_dg():
    destinations = og.allowed_destinations(og.EXTERNE)
    assert set(destinations) == {og.SERVICE_COURRIER, og.DIRECTION_GENERALE}


def test_source_et_destination_identiques_refusees():
    assert not og.is_authorized(og.DIRECTION_GENERALE, og.DIRECTION_GENERALE)


def test_tous_les_noeuds_ont_un_rang_et_sont_atteignables():
    # Vérifie l'intégrité du graphe : chaque nœud (hors Externe) doit avoir
    # un chemin remontant jusqu'à la Direction Générale.
    for node_id in og.all_node_ids():
        if node_id in (og.EXTERNE,):
            continue
        current = node_id
        depth_guard = 0
        while og.node_parent(current) is not None:
            current = og.node_parent(current)
            depth_guard += 1
            assert depth_guard < 20, f"boucle infinie détectée en remontant depuis {node_id}"
        assert current == og.DIRECTION_GENERALE
