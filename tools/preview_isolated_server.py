"""Serveur de prévisualisation sur DONNÉES DE TEST isolées — lancé par
`python tools/run_preview.py --donnees-test`, jamais directement.

Même serveur (webapp/server.py), même code, mêmes classes servies : seuls la
base SQLite et les fichiers utilisateur (progression, statistiques,
réglages, avis, pièces jointes, rapports, sauvegardes) sont redirigés vers le
dossier passé en argument, AVANT l'import du serveur — aucune ligne de
data/ (comptes réels) n'est lue ni écrite. Aucun module de production n'est
modifié : les chemins sont réaffectés ici, comme le font déjà les tests.

    python tools/preview_isolated_server.py <dossier>   (PORT et
    NOVAMATH_PREVIEW_CURRICULA viennent de l'environnement du lanceur)
"""
import os
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
WEBAPP = PROJECT_ROOT / "webapp"


def main(argv):
    data_dir = Path(argv[1]).resolve()
    data_dir.mkdir(parents=True, exist_ok=True)
    # Chemin absolu AVANT os.chdir : le rechargeur Werkzeug relance ce même
    # script avec sys.argv, qui doit donc désigner le même dossier.
    sys.argv[1:2] = [str(data_dir)]
    os.environ["BACKUP_DIRECTORY"] = str(data_dir / "backups")
    sys.path.insert(0, str(WEBAPP))
    os.chdir(WEBAPP)

    import db  # noqa: E402 — doit précéder l'import de server

    db.DATA_DIR = data_dir
    db.DB_PATH = data_dir / "novamath.db"
    import auth  # noqa: E402

    auth.DATA_DIR = data_dir
    auth.USER_STATS_DIR = data_dir / "user_stats"
    auth.USER_SETTINGS_DIR = data_dir / "user_settings"
    auth.USER_COURSE_DIR = data_dir / "user_course_progress"
    auth.LEGACY_STATS_PATH = data_dir / "stats_store.json"
    import server  # noqa: E402
    import admin_user_profile_service  # noqa: E402

    server.DATA_DIR = data_dir
    server.REVIEWS_PATH = data_dir / "reviews.json"
    admin_user_profile_service.REVIEWS_PATH = data_dir / "reviews.json"
    import config  # noqa: E402
    import dev_server  # noqa: E402

    print(f"Données de test isolées : {data_dir}", flush=True)
    _owner_de_test(db)
    # Même serveur que `python webapp/server.py` (dev_server : port exclusif,
    # rechargeur en mode debug). Le rechargeur relance CE script avec les
    # mêmes arguments : les réaffectations ci-dessus sont refaites dans
    # chaque processus enfant avant l'import du serveur.
    dev_server.run(server.app, debug=config.DEBUG, data=f"de test ({data_dir})")


def _owner_de_test(db):
    """Mode test Owner (owner_test_plan_service.py) sur la base ISOLÉE.

    NOVAMATH_OWNER_USER_ID (.env) désigne un numéro de compte de data/ : dans
    la base de test, ce numéro n'est pas le même compte (le propriétaire y a
    un autre id, et un compte de test quelconque pourrait un jour porter ce
    numéro). Pour CE processus seulement, l'owner devient le compte de la
    base isolée dont l'email est l'UNIQUE adresse de
    NOVAMATH_SUPER_ADMIN_EMAILS (configuration existante, .env inchangé).
    Fail-closed : 0 ou plusieurs adresses, ou aucun compte correspondant →
    mode Owner désactivé (variable retirée de ce processus)."""
    emails = [e.strip().lower() for e in os.environ.get("NOVAMATH_SUPER_ADMIN_EMAILS", "").split(",") if e.strip()]
    user = db.get_user_by_email(emails[0]) if len(emails) == 1 else None
    if user is not None:
        os.environ["NOVAMATH_OWNER_USER_ID"] = str(user["id"])
        print(f"Mode test Owner : compte n° {user['id']} de la base de test (adresse de NOVAMATH_SUPER_ADMIN_EMAILS).", flush=True)
    else:
        os.environ.pop("NOVAMATH_OWNER_USER_ID", None)
        print("Mode test Owner désactivé : aucun compte de la base de test ne correspond à l'adresse de "
              "NOVAMATH_SUPER_ADMIN_EMAILS (crée-le, puis python tools/run_preview.py --redemarrer).", flush=True)


if __name__ == "__main__":
    main(sys.argv)
