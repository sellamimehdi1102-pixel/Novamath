"""
Agrégation des signaux de santé de NovaMath pour GET /api/health (server.py).

Architecture stricte, identique au reste des services :

    server.py  →  health_service.py  →  db.py / backup_service.py / stripe_service.py

jamais l'inverse. Chaque vérification est indépendante et défensive
individuellement : un sous-système en panne ne doit jamais faire planter la
route elle-même — c'est justement ce qu'elle sert à détecter (Partie 4).
"""
import logging
import os
import shutil
from pathlib import Path

import backup_service
import db
import email_service
import stripe_service

logger = logging.getLogger("health_service")

ROOT = Path(__file__).resolve().parent.parent
VERSION_FILE = ROOT / "VERSION"

# Seuil d'ALERTE (le check devient "degraded"), pas un blocage brutal du
# serveur — voir check_disk_space().
MIN_FREE_DISK_MB = 100


def check_database():
    """True si une connexion + requête triviale réussissent."""
    try:
        conn = db.get_connection()
        try:
            conn.execute("SELECT 1")
        finally:
            conn.close()
        return True
    except Exception as e:
        logger.error("Health check : base de données indisponible : %s", e)
        return False


def check_stripe_configured():
    """Configuration uniquement (STRIPE_SECRET_KEY présente et valide) —
    jamais d'appel réseau vers Stripe dans un health check (Partie 4)."""
    try:
        return stripe_service.is_configured()
    except Exception as e:
        logger.error("Health check : impossible de vérifier la configuration Stripe : %s", e)
        return False


def check_backup_directory():
    """True si le dossier de sauvegarde existe (créé si besoin) et est
    accessible en écriture."""
    try:
        path = backup_service.backup_dir()
        return path.is_dir() and os.access(path, os.W_OK)
    except OSError as e:
        logger.error("Health check : dossier de sauvegarde inaccessible : %s", e)
        return False


def check_disk_space(min_free_mb=MIN_FREE_DISK_MB):
    """True si au moins `min_free_mb` Mo sont encore libres sur le volume
    hébergeant le projet."""
    try:
        usage = shutil.disk_usage(ROOT)
        return (usage.free / (1024 * 1024)) >= min_free_mb
    except OSError as e:
        logger.error("Health check : impossible de lire l'espace disque : %s", e)
        return False


def check_smtp_configured():
    """Configuration uniquement (EMAIL_SMTP_HOST + EMAIL_FROM_ADDRESS
    présentes) — jamais de connexion SMTP réelle depuis un health check, même
    politique que check_stripe_configured() ci-dessus. Utilisée uniquement
    par system_health_service.py (page Santé du système) : volontairement
    PAS ajoutée à snapshot()/GET /api/health pour ne rien changer au statut
    déjà surveillé par un éventuel load balancer/uptime monitor externe."""
    try:
        return email_service.is_configured()
    except Exception as e:
        logger.error("Health check : impossible de vérifier la configuration SMTP : %s", e)
        return False


def app_version():
    """Version courante lue depuis VERSION (racine du projet, même source
    que create_version_snapshot.py) — "unknown" si le fichier est absent,
    jamais une exception."""
    try:
        return VERSION_FILE.read_text(encoding="utf-8").strip()
    except OSError:
        return "unknown"


def snapshot():
    """Instantané complet consommé par GET /api/health. Ne lève jamais :
    chaque sous-vérification est déjà défensive individuellement."""
    checks = {
        "database": check_database(),
        "stripe_configured": check_stripe_configured(),
        "backup_directory": check_backup_directory(),
        "disk_space": check_disk_space(),
    }
    return {
        "status": "ok" if all(checks.values()) else "degraded",
        "version": app_version(),
        "checks": checks,
    }
