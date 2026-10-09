"""Tests de la couche de stockage SQLite (utils/db.py) : c'est la partie la
plus critique de cette refonte (stockage partagé et persistant, remplaçant
`st.session_state`), donc celle qui mérite la couverture la plus directe."""
from utils import db


class FakeUploadedFile:
    """Imite l'interface minimale d'un `st.file_uploader` pour les tests,
    sans dépendre de Streamlit."""
    def __init__(self, name: str, content: bytes, content_type: str = "text/plain"):
        self.name = name
        self.type = content_type
        self._content = content

    def getvalue(self) -> bytes:
        return self._content


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


def test_insert_dossier_attribue_un_numero_stable():
    numero = db.insert_dossier(_champs_dossier(), poste_auteur="Poste test")
    assert numero.startswith(f"AER-")
    rows = db.fetch_dossiers()
    assert len(rows) == 1
    assert rows[0]["numero"] == numero
    assert rows[0]["objet"] == "Objet de test"


def test_numero_ne_colisionne_pas_apres_suppression():
    """Reproduit le bug trouvé dans la version initiale : l'ancien calcul
    `len(df) + 1` pouvait réattribuer le numéro d'un dossier supprimé. Avec
    l'identifiant auto-incrémenté interne, ça ne doit plus jamais arriver."""
    numero1 = db.insert_dossier(_champs_dossier(objet="Premier"), poste_auteur="Poste test")
    numero2 = db.insert_dossier(_champs_dossier(objet="Deuxième"), poste_auteur="Poste test")
    assert len(db.fetch_dossiers()) == 2

    premier = next(r for r in db.fetch_dossiers() if r["numero"] == numero1)
    db.delete_dossier(premier["id"], numero1, "snapshot", "Poste test", "test")
    assert len(db.fetch_dossiers()) == 1

    numero3 = db.insert_dossier(_champs_dossier(objet="Troisième"), poste_auteur="Poste test")
    assert numero3 != numero1, "le numéro d'un dossier supprimé a été réattribué (collision)"
    assert numero3 != numero2


def test_update_dossier_field_journalise_dans_audit_log():
    numero = db.insert_dossier(_champs_dossier(), poste_auteur="Poste test")
    dossier_id = db.fetch_dossiers()[0]["id"]

    db.update_dossier_field(dossier_id, numero, "statut", "Reçu", "En cours",
                             "Poste test", "Édition directe du registre")

    rows = db.fetch_dossiers()
    assert rows[0]["statut"] == "En cours"

    audit = db.fetch_audit_log(numero_dossier=numero)
    assert any(a["Champ modifié"] == "statut" and a["Nouvelle valeur"] == "En cours" for a in audit)


def test_delete_dossier_cascade_transmissions_et_attachments():
    numero = db.insert_dossier(_champs_dossier(), poste_auteur="Poste test")
    db.insert_transmission({
        "numero_dossier": numero, "date": "2026-09-02", "service_source": "Externe (hors AER)",
        "service_destination": "Service du Courrier, de la Liaison et des Archives", "sens": "Aller",
        "delai_imparti_jours": None, "commentaire": "",
    }, "Poste test", "Transmission")
    db.add_attachment(numero, FakeUploadedFile("scan.txt", b"contenu"), "Poste test")

    assert len(db.fetch_transmissions()) == 1
    assert len(db.list_attachments(numero)) == 1

    dossier_id = db.fetch_dossiers()[0]["id"]
    db.delete_dossier(dossier_id, numero, "snapshot", "Poste test", "test")

    assert db.fetch_transmissions() == []
    assert db.list_attachments(numero) == []


def test_attachment_round_trip():
    numero = db.insert_dossier(_champs_dossier(), poste_auteur="Poste test")
    ok, message = db.add_attachment(numero, FakeUploadedFile("rapport.pdf", b"%PDF-contenu"), "Poste test")
    assert ok, message

    fichiers = db.list_attachments(numero)
    assert len(fichiers) == 1
    assert db.decode_attachment(fichiers[0]) == b"%PDF-contenu"

    db.remove_attachment(fichiers[0]["id"], "Poste test")
    assert db.list_attachments(numero) == []


def test_attachment_respecte_la_limite_de_taille():
    numero = db.insert_dossier(_champs_dossier(), poste_auteur="Poste test")
    trop_gros = b"x" * (db.MAX_TAILLE_OCTETS + 1)
    ok, message = db.add_attachment(numero, FakeUploadedFile("gros.bin", trop_gros), "Poste test")
    assert not ok
    assert "5 Mo" in message


def test_attachment_respecte_la_limite_de_nombre():
    numero = db.insert_dossier(_champs_dossier(), poste_auteur="Poste test")
    for i in range(db.MAX_FICHIERS_PAR_DOSSIER):
        ok, _ = db.add_attachment(numero, FakeUploadedFile(f"f{i}.txt", b"x"), "Poste test")
        assert ok
    ok, message = db.add_attachment(numero, FakeUploadedFile("de_trop.txt", b"x"), "Poste test")
    assert not ok
    assert "Limite" in message


def test_replace_all_dossiers_remplace_integralement():
    db.insert_dossier(_champs_dossier(objet="À remplacer"), poste_auteur="Poste test")
    n = db.replace_all_dossiers(
        [{"numero": "AER-2026-9999", **{k: v for k, v in _champs_dossier(objet="Restauré").items()}}],
        poste_auteur="Poste test", source="Restauration de sauvegarde",
    )
    assert n == 1
    rows = db.fetch_dossiers()
    assert len(rows) == 1
    assert rows[0]["objet"] == "Restauré"
    assert rows[0]["numero"] == "AER-2026-9999"


def test_insert_approbation_et_fetch():
    numero = db.insert_dossier(_champs_dossier(), poste_auteur="Poste test")
    appr_id = db.insert_approbation({
        "numero_dossier": numero, "etape": "Validation du budget", "demande_par": "Poste demandeur",
        "approbateur": "Poste approbateur", "statut": db.STATUT_EN_ATTENTE,
        "date_demande": "2026-09-05", "echeance": "2026-09-10", "date_decision": None,
        "commentaire": "Contexte", "decision_commentaire": None,
    }, "Poste demandeur")

    rows = db.fetch_approbations(numero_dossier=numero)
    assert len(rows) == 1
    assert rows[0]["id"] == appr_id
    assert rows[0]["statut"] == db.STATUT_EN_ATTENTE
    assert rows[0]["approbateur"] == "Poste approbateur"

    audit = db.fetch_audit_log(numero_dossier=numero)
    assert any(a["Champ modifié"] == "(approbation demandée)" for a in audit)


def test_decide_approbation_journalise_et_met_a_jour_le_statut():
    numero = db.insert_dossier(_champs_dossier(), poste_auteur="Poste test")
    appr_id = db.insert_approbation({
        "numero_dossier": numero, "etape": "Avis juridique", "demande_par": "A", "approbateur": "B",
        "statut": db.STATUT_EN_ATTENTE, "date_demande": "2026-09-05", "echeance": None,
        "date_decision": None, "commentaire": None, "decision_commentaire": None,
    }, "A")

    db.decide_approbation(appr_id, db.STATUT_APPROUVE, "Conforme", "B")

    rows = db.fetch_approbations(numero_dossier=numero)
    assert rows[0]["statut"] == db.STATUT_APPROUVE
    assert rows[0]["decision_commentaire"] == "Conforme"
    assert rows[0]["date_decision"] is not None

    audit = db.fetch_audit_log(numero_dossier=numero)
    assert any(a["Nouvelle valeur"] == db.STATUT_APPROUVE for a in audit)


def test_delegate_approbation_change_l_approbateur():
    numero = db.insert_dossier(_champs_dossier(), poste_auteur="Poste test")
    appr_id = db.insert_approbation({
        "numero_dossier": numero, "etape": "Avis", "demande_par": "A", "approbateur": "B",
        "statut": db.STATUT_EN_ATTENTE, "date_demande": "2026-09-05", "echeance": None,
        "date_decision": None, "commentaire": None, "decision_commentaire": None,
    }, "A")

    db.delegate_approbation(appr_id, "C", "Je suis absent", "B")

    rows = db.fetch_approbations(numero_dossier=numero)
    assert rows[0]["approbateur"] == "C"
    assert rows[0]["statut"] == db.STATUT_EN_ATTENTE  # toujours en attente, juste réassignée
    assert "délégué par B" in rows[0]["commentaire"]


def test_delete_dossier_cascade_approbations():
    numero = db.insert_dossier(_champs_dossier(), poste_auteur="Poste test")
    db.insert_approbation({
        "numero_dossier": numero, "etape": "Avis", "demande_par": "A", "approbateur": "B",
        "statut": db.STATUT_EN_ATTENTE, "date_demande": "2026-09-05", "echeance": None,
        "date_decision": None, "commentaire": None, "decision_commentaire": None,
    }, "A")
    assert len(db.fetch_approbations(numero_dossier=numero)) == 1

    dossier_id = db.fetch_dossiers()[0]["id"]
    db.delete_dossier(dossier_id, numero, "snapshot", "Poste test", "test")

    assert db.fetch_approbations(numero_dossier=numero) == []


def test_replace_all_approbations_remplace_integralement():
    db.insert_approbation({
        "numero_dossier": "AER-2026-0001", "etape": "Ancienne", "demande_par": "A", "approbateur": "B",
        "statut": db.STATUT_EN_ATTENTE, "date_demande": "2026-09-01", "echeance": None,
        "date_decision": None, "commentaire": None, "decision_commentaire": None,
    }, "A")
    n = db.replace_all_approbations([{
        "numero_dossier": "AER-2026-0002", "etape": "Restaurée", "demande_par": "X", "approbateur": "Y",
        "statut": db.STATUT_EN_ATTENTE, "date_demande": "2026-09-05", "echeance": None,
        "date_decision": None, "commentaire": None, "decision_commentaire": None,
    }], poste_auteur="Poste test", source="Restauration de sauvegarde")
    assert n == 1
    rows = db.fetch_approbations()
    assert len(rows) == 1
    assert rows[0]["numero_dossier"] == "AER-2026-0002"


def test_replace_all_transmissions_remplace_integralement():
    db.insert_transmission({
        "numero_dossier": "AER-2026-0001", "date": "2026-09-01", "service_source": "A",
        "service_destination": "B", "sens": "Aller", "delai_imparti_jours": None, "commentaire": "",
    }, "Poste test", "Transmission")
    n = db.replace_all_transmissions([{
        "numero_dossier": "AER-2026-0002", "date": "2026-09-05", "service_source": "C",
        "service_destination": "D", "sens": "Aller", "delai_imparti_jours": 5, "commentaire": "restauré",
    }], poste_auteur="Poste test", source="Restauration de sauvegarde")
    assert n == 1
    trans = db.fetch_transmissions()
    assert len(trans) == 1
    assert trans[0]["numero_dossier"] == "AER-2026-0002"
