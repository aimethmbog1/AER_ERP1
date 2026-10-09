"""Tests de la couche d'orchestration du workflow d'approbation
(`utils/workflow.py`) et du centre de notifications (`utils/notifications.py`)
— `tests/test_db.py` couvre déjà la couche de stockage SQLite sous-jacente,
ces tests-ci couvrent la couche appelée par les pages (conversion en
DataFrame, calcul de la liste de tâches personnelle)."""
from datetime import date, timedelta

from utils import db, workflow as wf, notifications as notif
from utils.dossiers import with_derived_columns, get_register


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


def test_request_approval_puis_decide():
    numero = db.insert_dossier(_champs_dossier(), poste_auteur="Poste test")

    appr_id = wf.request_approval(numero, "Validation du budget", "Poste approbateur",
                                   echeance=date.today() + timedelta(days=5), commentaire="Contexte")

    pending = wf.get_approbations(numero_dossier=numero)
    assert len(pending) == 1
    assert pending.iloc[0]["Statut"] == wf.STATUT_EN_ATTENTE
    assert pending.iloc[0]["Approbateur"] == "Poste approbateur"

    wf.decide(appr_id, wf.STATUT_APPROUVE, "Conforme")
    after = wf.get_approbations(numero_dossier=numero)
    assert after.iloc[0]["Statut"] == wf.STATUT_APPROUVE
    assert after.iloc[0]["Commentaire de décision"] == "Conforme"


def test_delegate_puis_pending_for_reflete_le_nouvel_approbateur():
    numero = db.insert_dossier(_champs_dossier(), poste_auteur="Poste test")
    appr_id = wf.request_approval(numero, "Avis", "Poste A")

    assert len(wf.pending_for("Poste A")) == 1
    assert len(wf.pending_for("Poste B")) == 0

    wf.delegate(appr_id, "Poste B", "Je suis en mission")

    assert len(wf.pending_for("Poste A")) == 0
    assert len(wf.pending_for("Poste B")) == 1


def test_overdue_detecte_une_echeance_depassee():
    numero = db.insert_dossier(_champs_dossier(), poste_auteur="Poste test")
    wf.request_approval(numero, "Avis en retard", "Poste C", echeance=date.today() - timedelta(days=2))
    wf.request_approval(numero, "Avis dans les temps", "Poste C", echeance=date.today() + timedelta(days=2))

    en_retard = wf.overdue("Poste C")
    assert len(en_retard) == 1
    assert en_retard.iloc[0]["Étape"] == "Avis en retard"


def test_worklist_for_combine_approbations_et_dossiers_en_retard():
    numero = db.insert_dossier(_champs_dossier(
        service_destinataire="Poste D", echeance_prevue="2000-01-01",  # largement dépassée
    ), poste_auteur="Poste test")
    wf.request_approval(numero, "Décision attendue", "Poste D")

    register = with_derived_columns(get_register())
    items = notif.worklist_for("Poste D", register)

    gravites = {item.gravite for item in items}
    assert "approbation" in gravites
    assert "retard" in gravites
    # Les approbations passent avant les dossiers en retard (tri par gravité).
    assert items[0].gravite == "approbation"


def test_worklist_for_vide_sans_poste():
    register = with_derived_columns(get_register())
    assert notif.worklist_for(None, register) == []
