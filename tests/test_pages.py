"""Tests fonctionnels des pages (streamlit.testing.v1.AppTest) : vérifie que
chaque page s'exécute sans exception, à vide puis avec des données, et que
le partage des données entre « utilisateurs » fonctionne bien (c'est le
changement le plus important de la v2 : deux AppTest représentent ici deux
navigateurs/sessions différents, qui doivent voir le même registre).

Depuis la v3, chaque page est testée directement via son fichier dans
`app_pages/` (ce que `AppTest.from_file` continue de supporter très bien,
sans dépendre de `st.navigation`/`streamlit_app.py` — qui est, lui, testé
séparément ci-dessous, seeding du jeu de démonstration inclus)."""
from pathlib import Path

from streamlit.testing.v1 import AppTest

from utils import db

PROJECT_ROOT = Path(__file__).resolve().parent.parent

PAGES = [
    PROJECT_ROOT / "app_pages" / "accueil.py",
    PROJECT_ROOT / "app_pages" / "registre.py",
    PROJECT_ROOT / "app_pages" / "transmissions.py",
    PROJECT_ROOT / "app_pages" / "fiche_dossier.py",
    PROJECT_ROOT / "app_pages" / "tableau_de_bord.py",
    PROJECT_ROOT / "app_pages" / "organigramme.py",
    PROJECT_ROOT / "app_pages" / "recherche.py",
    PROJECT_ROOT / "app_pages" / "aide_assistant.py",
    PROJECT_ROOT / "app_pages" / "parametres_theme.py",
]


def _champs_dossier(**overrides) -> dict:
    base = {
        "date_reception": "2026-09-01", "objet": "Objet de test", "type_dossier": "Courrier entrant",
        "canal_reception": "Service du Courrier (bureau d'ordre)",
        "direction_concernee": "Direction Générale",
        "service_destinataire": "Service du Courrier, de la Liaison et des Archives",
        "statut": "Reçu", "priorite": "Normale", "echeance_prevue": "2026-09-20",
        "agent_en_charge": "Agent test", "reference_externe": "", "notes": "",
    }
    base.update(overrides)
    return base


def test_toutes_les_pages_se_chargent_a_vide():
    for page in PAGES:
        at = AppTest.from_file(str(page), default_timeout=30)
        at.run()
        assert not at.exception, f"{page.name} a levé une exception à vide : {at.exception}"


def test_toutes_les_pages_se_chargent_avec_des_donnees():
    numero = db.insert_dossier(_champs_dossier(), poste_auteur="Poste test")
    db.insert_transmission({
        "numero_dossier": numero, "date": "2026-09-02", "service_source": "Externe (hors AER)",
        "service_destination": "Service du Courrier, de la Liaison et des Archives", "sens": "Aller",
        "delai_imparti_jours": 5, "commentaire": "Réception initiale",
    }, "Poste test", "Transmission")

    for page in PAGES:
        at = AppTest.from_file(str(page), default_timeout=30)
        at.run()
        assert not at.exception, f"{page.name} a levé une exception avec données : {at.exception}"


def test_les_donnees_sont_partagees_entre_deux_sessions():
    """C'est LE test qui vérifie la correction de la faille structurelle
    principale : deux instances d'AppTest représentent deux sessions de
    navigateur différentes (donc deux `st.session_state` différents) — mais
    doivent voir le même registre, puisqu'il vit maintenant dans la base
    partagée et non plus dans `st.session_state`."""
    numero = db.insert_dossier(_champs_dossier(objet="Dossier partagé"), poste_auteur="Poste test")

    session_a = AppTest.from_file(str(PROJECT_ROOT / "app_pages" / "accueil.py"), default_timeout=30)
    session_a.run()
    session_b = AppTest.from_file(str(PROJECT_ROOT / "app_pages" / "accueil.py"), default_timeout=30)
    session_b.run()

    assert not session_a.exception and not session_b.exception
    texte_a = " ".join(m.value for m in session_a.markdown if m.value)
    texte_b = " ".join(m.value for m in session_b.markdown if m.value)
    assert "Dossier partagé" not in texte_a and "Dossier partagé" not in texte_b  # pas affiché sur Accueil
    assert len(db.fetch_dossiers()) == 1
    assert db.fetch_dossiers()[0]["numero"] == numero


def test_formulaire_nouveau_dossier_fonctionne_de_bout_en_bout():
    at = AppTest.from_file(str(PROJECT_ROOT / "app_pages" / "registre.py"), default_timeout=30)
    at.run()
    assert not at.exception

    at.text_input(key="add_objet").set_value("Dossier saisi via le formulaire")
    boutons = [b for b in at.button if b.label == "Ajouter au registre"]
    assert boutons, "bouton « Ajouter au registre » introuvable"
    boutons[0].click().run()
    assert not at.exception

    rows = db.fetch_dossiers()
    assert any(r["objet"] == "Dossier saisi via le formulaire" for r in rows)


def test_workflow_approbation_fonctionne_de_bout_en_bout_depuis_la_fiche_dossier():
    """Soumet une demande d'approbation depuis le formulaire de la page Fiche
    dossier, puis se positionne comme l'approbateur désigné et clique sur
    « Approuver » — vérifie que la décision est bien journalisée en base,
    exactement comme pour une interaction utilisateur réelle."""
    numero = db.insert_dossier(_champs_dossier(), poste_auteur="Poste test")
    fiche = PROJECT_ROOT / "app_pages" / "fiche_dossier.py"

    at = AppTest.from_file(str(fiche), default_timeout=30)
    at.run()
    assert not at.exception

    at.text_input(key="appr_new_etape").set_value("Validation du budget")
    at.selectbox(key="appr_new_approbateur").set_value(
        "Service du Courrier, de la Liaison et des Archives"
    )
    boutons = [b for b in at.button if b.key == "appr_new_submit"]
    assert boutons, "bouton de soumission de la demande d'approbation introuvable"
    boutons[0].click().run()
    assert not at.exception

    approbations = db.fetch_approbations(numero_dossier=numero)
    assert len(approbations) == 1
    assert approbations[0]["statut"] == db.STATUT_EN_ATTENTE
    appr_id = approbations[0]["id"]

    # Se positionner comme le poste approbateur désigné, puis approuver.
    at.selectbox(key="poste_courant_select").set_value(
        "Service du Courrier, de la Liaison et des Archives"
    ).run()
    assert not at.exception

    boutons_approuver = [b for b in at.button if b.key == f"appr_ok_{appr_id}"]
    assert boutons_approuver, "bouton « Approuver » introuvable pour le poste approbateur"
    boutons_approuver[0].click().run()
    assert not at.exception

    approbations_apres = db.fetch_approbations(numero_dossier=numero)
    assert approbations_apres[0]["statut"] == db.STATUT_APPROUVE


def test_entree_streamlit_app_se_charge_et_seme_la_demo():
    """`streamlit_app.py` seul charge le jeu de démonstration (300 dossiers /
    620 transmissions) si la base est vide — vérifie l'intégration bout en
    bout de `utils.demo_data.seed_demo_data_if_empty()` depuis le vrai point
    d'entrée, pas seulement la fonction en isolation."""
    assert not db.fetch_dossiers(), "la base doit être vide avant ce test (fixture _clean_database)"
    at = AppTest.from_file(str(PROJECT_ROOT / "streamlit_app.py"), default_timeout=60)
    at.run()
    assert not at.exception
    assert len(db.fetch_dossiers()) == 300
    assert len(db.fetch_transmissions()) == 620
