"""Configuration pytest : redirige la base SQLite et le dossier des pièces
jointes vers un répertoire temporaire dédié aux tests, AVANT tout import de
`utils.db` (les chemins y sont lus une seule fois, au chargement du
module)."""
import os
import sys
import tempfile
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

_TEST_DATA_DIR = Path(tempfile.mkdtemp(prefix="suivi_dossiers_tests_"))
os.environ["AER_DOSSIERS_DB_PATH"] = str(_TEST_DATA_DIR / "test.db")
os.environ["AER_DOSSIERS_ATTACHMENTS_DIR"] = str(_TEST_DATA_DIR / "attachments")

import pytest

from utils import db as _db  # noqa: E402  (import after sys.path/env setup, intentional)


@pytest.fixture(autouse=True)
def _clean_database():
    """Vide toutes les tables avant chaque test, pour que les tests restent
    indépendants malgré la connexion partagée (mise en cache par
    `st.cache_resource`, donc réutilisée d'un test à l'autre dans un même
    processus — exactement le comportement voulu en production, mais qui
    exige une remise à zéro explicite ici)."""
    conn = _db.get_connection()
    with conn:
        conn.execute("DELETE FROM dossiers")
        conn.execute("DELETE FROM transmissions")
        conn.execute("DELETE FROM attachments")
        conn.execute("DELETE FROM approbations")
        conn.execute("DELETE FROM audit_log")
        conn.execute("DELETE FROM sqlite_sequence")  # réinitialise aussi les compteurs auto-incrémentés
    yield
