"""Chargement automatique du jeu de données de démonstration (300 dossiers,
620 transmissions) fourni par l'utilisateur, au premier démarrage de
l'application UNIQUEMENT (base vide).

**Décision prise sans préférence exprimée par l'utilisateur** (question
posée explicitement, réponse « sans préférence ») : plutôt que de livrer
l'application vide comme la v2, elle démarre pré-remplie avec ce jeu de
démonstration réaliste — plus convaincant pour une présentation ou un
pilote, et cohérent avec la demande de « version la plus professionnelle ».
Le fichier CSV fourni séparément (300 lignes) n'est PAS importé en plus :
son contenu est strictement le même registre que celui déjà inclus dans ce
JSON (`registre_dossiers`), l'importer aussi aurait dupliqué les 300
dossiers sous de nouveaux numéros. Si vous préférez démarrer à vide,
supprimez l'appel à `seed_demo_data_if_empty()` dans `streamlit_app.py`, ou
videz la base (page Paramètres & thème → Réinitialiser)."""
from __future__ import annotations

from pathlib import Path

from . import db
from .backup import restore_backup_json

SEED_PATH = Path(__file__).resolve().parent.parent / "seed_data" / "aer_demo_300.json"


def seed_demo_data_if_empty() -> tuple[int, int, int, int] | None:
    """Restaure le jeu de démonstration si — et seulement si — le registre
    est actuellement vide. Ne touche jamais à des données déjà saisies :
    aucune vérification de contenu au-delà de « la table dossiers est-elle
    vide ? », volontairement simple et sûr (jamais de restauration
    silencieuse par-dessus un usage réel en cours)."""
    if not SEED_PATH.exists():
        return None
    if db.fetch_dossiers():
        return None
    content = SEED_PATH.read_text(encoding="utf-8")
    result = restore_backup_json(content)
    db.log_audit(db.get_connection(), None, "(données de démonstration)", None,
                 f"{result[0]} dossier(s) / {result[1]} transmission(s) chargés au premier démarrage",
                 None, "Démarrage initial")
    return result


def reset_all_data() -> None:
    """Vide intégralement la base (utilisé par la page Paramètres & thème).
    Irréversible — l'appelant doit faire confirmer l'action par l'utilisateur
    avant d'appeler cette fonction (voir app_pages/parametres_theme.py)."""
    conn = db.get_connection()
    with conn:
        conn.execute("DELETE FROM dossiers")
        conn.execute("DELETE FROM transmissions")
        conn.execute("DELETE FROM attachments")
        conn.execute("DELETE FROM approbations")
        db.log_audit(conn, None, "(réinitialisation complète)", None, "Toutes les données supprimées",
                     None, "Paramètres & thème")
