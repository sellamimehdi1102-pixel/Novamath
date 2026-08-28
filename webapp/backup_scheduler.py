"""
Sauvegarde automatique quotidienne de la base de données NovaMath.

Ne remplace PAS backup_service.py (toujours la seule couche qui sait
réellement sauvegarder/restaurer) — ce module se contente de décider QUAND
déclencher backup_database(), en tâche de fond, sans dépendance externe
(pas de cron système, pas d'APScheduler) : une simple vérification
périodique dans un thread démon.

Compatible multi-worker Gunicorn par construction : chaque worker peut faire
tourner sa propre boucle de vérification (voir gunicorn.conf.py::post_fork),
mais seul UN SEUL déclenche réellement la sauvegarde d'une journée donnée —
db.claim_daily_backup() (INSERT OR IGNORE atomique, même mécanisme que
l'idempotence des webhooks Stripe) garantit qu'aucune sauvegarde concurrente
n'est jamais lancée, quel que soit le nombre de workers.

Le bouton "Créer une sauvegarde" (settings_service.create_backup, panneau
Administration) reste totalement inchangé et indépendant de ce module.
"""
import logging
import threading
from datetime import datetime, timezone

import config
import db
import settings_service

logger = logging.getLogger("backup_scheduler")

# Acteur synthétique pour la journalisation admin (admin_ai_log_service) :
# jamais un vrai utilisateur, mais jamais "None" nu non plus — une sauvegarde
# automatique doit être traçable dans le journal au même titre qu'une
# sauvegarde manuelle, clairement identifiée comme automatique.
_AUTO_ACTOR = {"id": None, "name": "Sauvegarde automatique (planificateur)", "role": "system"}

_stop_event = threading.Event()


def _today_str(now=None):
    return (now or datetime.now(timezone.utc)).strftime("%Y-%m-%d")


def maybe_run_daily_backup(now=None):
    """Déclenche la sauvegarde du jour si (a) l'heure programmée est atteinte
    et (b) elle n'a pas déjà été prise aujourd'hui. Ne lève jamais — une
    boucle de fond ne doit jamais mourir sur une erreur de sauvegarde (déjà
    journalisée par backup_service/settings_service.create_backup, qui avale
    déjà les exceptions et les trace en base). Renvoie True si une sauvegarde
    a été effectivement déclenchée par CET appel (utile pour les tests),
    False sinon (trop tôt, déjà faite, ou désactivée)."""
    if not config.BACKUP_AUTO_ENABLED:
        return False
    now = now or datetime.now(timezone.utc)
    if now.hour < config.BACKUP_AUTO_HOUR_UTC:
        return False

    if not db.claim_daily_backup(_today_str(now)):
        return False  # déjà prise aujourd'hui (par ce worker ou un autre)

    try:
        filename, error = settings_service.create_backup(_AUTO_ACTOR)
        if error:
            logger.error("Sauvegarde automatique quotidienne échouée : %s", error)
        else:
            logger.info("Sauvegarde automatique quotidienne créée : %s.", filename)
    except Exception:
        # Filet de sécurité ultime : create_backup() encapsule déjà ses
        # propres erreurs (voir settings_service.py), mais la boucle de fond
        # ne doit JAMAIS s'arrêter, quelle que soit la cause.
        logger.exception("Sauvegarde automatique quotidienne : erreur inattendue.")
    return True


def _loop():
    logger.info(
        "Planificateur de sauvegarde automatique démarré (heure=%sh UTC, vérification toutes les %ss).",
        config.BACKUP_AUTO_HOUR_UTC, config.BACKUP_AUTO_CHECK_INTERVAL_SECONDS,
    )
    while not _stop_event.is_set():
        try:
            maybe_run_daily_backup()
        except Exception:
            logger.exception("Planificateur de sauvegarde automatique : erreur inattendue dans la boucle.")
        _stop_event.wait(config.BACKUP_AUTO_CHECK_INTERVAL_SECONDS)


def start_background_scheduler():
    """Démarre le thread de fond (démon : ne bloque jamais l'arrêt du
    worker). Appelée depuis gunicorn.conf.py::post_fork — jamais au niveau
    module de server.py (voir sa docstring : aucune tâche de fond persistante
    ne doit être ouverte avant le fork, pour rester compatible
    GUNICORN_PRELOAD_APP=True). Sûre à appeler plusieurs fois par erreur
    (chaque appel démarre un thread indépendant ; l'idempotence réelle contre
    les sauvegardes concurrentes est assurée par db.claim_daily_backup, pas
    par l'unicité du thread)."""
    if not config.BACKUP_AUTO_ENABLED:
        logger.info("Sauvegarde automatique désactivée (BACKUP_AUTO_ENABLED=false).")
        return
    thread = threading.Thread(target=_loop, name="backup-scheduler", daemon=True)
    thread.start()
