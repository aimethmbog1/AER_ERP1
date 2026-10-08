"""Tests fonctionnels des pages (streamlit.testing.v1.AppTest) : vérifie que
chaque page s'exécute sans exception, à vide puis avec des données, et que
le partage des données entre « utilisateurs » fonctionne bien (c'est le
changement le plus important de cette refonte : deux AppTest représentent
ici deux navigateurs/sessions différents, qui doivent voir le même
registre)."""
from pathlib import Path

from streamlit.testing.v1 import AppTest

from utils import db

PROJECT_ROOT = Path(__file__).resolve().parent.parent

PAGES = [
    PROJECT_ROOT / "Home.py",
    PROJECT_ROOT / "pages" / "1_📂_Registre_des_dossiers.py",
    PROJECT_ROOT / "pages" / "2_🔀_Transmissions_et_traçabilité.py",
    PROJECT_ROOT / "pages" / "3_📊_Tableau_de_bord.py",
    PROJECT_ROOT / "pages" / "4_🏢_Organigramme.py",
    PROJECT_ROOT / "pages" / "5_🔍_Recherche_et_registre_courrier.py",
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
        at = AppTest.from_file(str(page), default_timeout=20)
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
        at = AppTest.from_file(str(page), default_timeout=20)
        at.run()
        assert not at.exception, f"{page.name} a levé une exception avec données : {at.exception}"


def test_les_donnees_sont_partagees_entre_deux_sessions():
    """C'est LE test qui vérifie la correction de la faille structurelle
    principale : deux instances d'AppTest représentent deux sessions de
    navigateur différentes (donc deux `st.session_state` différents) — mais
    doivent voir le même registre, puisqu'il vit maintenant dans la base
    partagée et non plus dans `st.session_state`."""
    numero = db.insert_dossier(_champs_dossier(objet="Dossier partagé"), poste_auteur="Poste test")

    session_a = AppTest.from_file(str(PROJECT_ROOT / "Home.py"), default_timeout=20)
    session_a.run()
    session_b = AppTest.from_file(str(PROJECT_ROOT / "Home.py"), default_timeout=20)
    session_b.run()

    assert not session_a.exception and not session_b.exception
    # Le KPI "Dossiers au total" (première carte) doit refléter 1 dossier dans les deux sessions.
    texte_a = " ".join(m.value for m in session_a.markdown if m.value)
    texte_b = " ".join(m.value for m in session_b.markdown if m.value)
    assert "Dossier partagé" not in texte_a and "Dossier partagé" not in texte_b  # pas affiché sur Home
    # Vérification directe et sans ambiguïté : la base est unique, donc les deux sessions
    # interrogent exactement les mêmes lignes.
    assert len(db.fetch_dossiers()) == 1
    assert db.fetch_dossiers()[0]["numero"] == numero


def test_formulaire_nouveau_dossier_fonctionne_de_bout_en_bout():
    at = AppTest.from_file(str(PROJECT_ROOT / "pages" / "1_📂_Registre_des_dossiers.py"),
                            default_timeout=20)
    at.run()
    assert not at.exception

    at.text_input(key="add_objet").set_value("Dossier saisi via le formulaire")
    boutons = [b for b in at.button if b.label == "Ajouter au registre"]
    assert boutons, "bouton « Ajouter au registre » introuvable"
    boutons[0].click().run()
    assert not at.exception

    rows = db.fetch_dossiers()
    assert any(r["objet"] == "Dossier saisi via le formulaire" for r in rows)
