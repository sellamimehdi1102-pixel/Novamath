"""
Service pour le module "Santé du système" (/admin/health) — centre d'ALERTE
de NovaMath (pas un tableau d'observation) : vue d'ensemble, services
(SQLite/Stripe/SMTP/fournisseurs IA), incidents, disponibilité IA, base
SQLite, stockage, serveur, alertes. Chaque champ conservé correspond à une
décision concrète (investiguer un service précis, restaurer une sauvegarde,
libérer de l'espace disque...) — voir le chantier de simplification
documenté sur chaque fonction ci-dessous pour ce qui a été retiré et
pourquoi (détail par fournisseur IA/clés API dupliquant /admin/ia,
moyennes globales mélangeant des services hétérogènes, métriques
décoratives sans décision associée).

Architecture stricte, identique au reste du projet :

    server.py  →  system_health_service.py  →  {health_service, backup_service,
                  email_service, metrics_service, admin_ai_service,
                  ai_provider_service, ai_provider_key_service,
                  admin_ai_log_service, support_attachment_service, db}.py

jamais l'inverse. Ce module ne fait QUE lire et agréger — aucune écriture,
aucun appel réseau vers un fournisseur externe (les seuls health-checks réels
restent ceux déjà exposés par /admin/ia, réutilisés tels quels par le
bouton "Tester la connexion" de cette page). Ne touche JAMAIS au routage des
LLM (provider_manager.py), aux quotas, à Stripe, ni au chatbot.

── Politique "aucune donnée inventée" ──────────────────────────────────────
Identique à admin_ai_service.py/admin_dashboard_service.py : tout ce qui ne
peut pas être calculé à partir d'une donnée réellement enregistrée renvoie
{"available": False, "value": None, "reason": "..."} avec une raison précise
(quelle table/colonne/instrumentation manquante), jamais une valeur à zéro ou
une date fabriquée pour "faire joli".
"""
import logging
import os
import shutil
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

import admin_ai_log_service
import admin_ai_service
import ai_provider_key_service
import ai_provider_service as ai_svc
import backup_service
import db
import health_service
import metrics_service
import support_attachment_service

try:
    import psutil
except ImportError:  # pragma: no cover - psutil est dans requirements.txt
    psutil = None

logger = logging.getLogger("webapp.system_health_service")

ROOT = Path(__file__).resolve().parent.parent

# Horodatage du démarrage de CE process — utilisé pour l'uptime serveur
# (Partie 8). Fixé une seule fois à l'import du module, comme
# metrics_service._stats : remis à zéro à chaque redémarrage, sans
# conséquence (même convention que pipeline_metrics.py).
_PROCESS_STARTED_AT = time.time()

WINDOWS = {"24h": timedelta(hours=24), "7j": timedelta(days=7), "30j": timedelta(days=30), "tous": None}

# Seuils d'alerte (Partie 11) — arbitraires mais EXPLICITES : documentés ici
# et affichés tels quels côté frontend, jamais un seuil caché.
ALERT_FALLBACK_COUNT_1H = 3
ALERT_LATENCY_MS = 3000
ALERT_DB_SIZE_MB = 500
ALERT_BACKUP_MAX_AGE_DAYS = 7


def _na(reason):
    return {"available": False, "value": None, "reason": reason}


def _ok(value):
    return {"available": True, "value": value}


def _now():
    return datetime.now(timezone.utc)


def _since_iso(window):
    delta = WINDOWS.get(window)
    return (_now() - delta).isoformat() if delta else None


def _parse_iso(value):
    if not value:
        return None
    try:
        return datetime.fromisoformat(value)
    except ValueError:
        return None


# ── 1. Vue d'ensemble + 9. Cartes "Services" ────────────────────────────────
def _sqlite_service(introspection):
    started = time.perf_counter()
    ok = health_service.check_database()
    latency_ms = round((time.perf_counter() - started) * 1000)
    now_iso = _now().isoformat()
    return {
        "id": "sqlite", "name": "Base SQLite", "state": "ok" if ok else "down",
        "latency_ms": _ok(latency_ms), "last_success": _ok(now_iso) if ok else _na("Dernière vérification en échec."),
        "last_failure": _ok(now_iso) if not ok else _na("Aucun échec lors de cette vérification."),
        "version": _ok(introspection["sqlite_version"]) if introspection else _na(
            "Moteur PostgreSQL actif : la version SQLite ne s'applique pas."
        ),
    }


def _stripe_service():
    configured = health_service.check_stripe_configured()
    return {
        "id": "stripe", "name": "Stripe", "state": "ok" if configured else "down",
        "latency_ms": _na("Aucun appel réseau vers Stripe n'est exécuté par un health check (vérification de "
                          "configuration uniquement, par choix — voir health_service.py)."),
        "last_success": _na("Idem : aucun appel réel n'est jamais tenté ici."),
        "last_failure": _na("Idem : aucun appel réel n'est jamais tenté ici."),
        "version": _na("Stripe est un service externe versionné par leur API, non interrogé ici."),
    }


def _smtp_service():
    configured = health_service.check_smtp_configured()
    return {
        "id": "smtp", "name": "SMTP", "state": "ok" if configured else "down",
        "latency_ms": _na("Aucune connexion SMTP réelle n'est ouverte par un health check (vérification de "
                          "configuration uniquement, pour éviter tout trafic réseau à chaque actualisation)."),
        "last_success": _na("Idem : aucune connexion réelle n'est jamais tentée ici."),
        "last_failure": _na("Idem : aucune connexion réelle n'est jamais tentée ici."),
        "version": _na("Protocole standard, aucune notion de version applicative à afficher."),
    }


def _provider_state(health):
    if health is None:
        return "non_teste"
    last_success = _parse_iso(health["last_success"])
    last_failure = _parse_iso(health["last_failure"])
    if last_failure and (last_success is None or last_failure > last_success):
        return "down"
    if health["success_rate"] is not None and health["success_rate"] < 100:
        return "degraded"
    return "ok"


def _ai_provider_service_card(provider):
    health = ai_svc.get_health(provider["id"])
    state = _provider_state(health)
    return {
        "id": f"ai_{provider['id']}", "name": provider["name"], "state": state,
        "latency_ms": _ok(health["average_latency"]) if health and health["average_latency"] is not None else _na(
            admin_ai_service.NO_HEALTH_DATA
        ),
        "last_success": _ok(health["last_success"]) if health and health["last_success"] else _na(
            admin_ai_service.NO_HEALTH_DATA
        ),
        "last_failure": _ok(health["last_failure"]) if health and health["last_failure"] else _na(
            "Aucun échec de santé enregistré pour ce fournisseur."
        ),
        "version": _ok(provider["model_name"]),
    }


def list_services(introspection=None):
    """Cartes de la Partie 9 ("SQLite"/"Stripe"/"SMTP"/un fournisseur IA par
    ligne de ai_providers, ex : "Gemini Flash"/"Gemini Pro"/"Claude"). "Fake"/
    "Ollama" n'apparaissent que s'ils ont été enregistrés dans ai_providers
    (voir /admin/ia) — aucune carte fabriquée pour un fournisseur jamais
    configuré. `introspection` : résultat déjà calculé de
    db.sqlite_introspection(), pour éviter de le recalculer (COUNT(*) sur
    chaque table) plusieurs fois par requête — recalculé ici seulement si
    absent."""
    if introspection is None:
        introspection = db.sqlite_introspection()
    services = [_sqlite_service(introspection), _stripe_service(), _smtp_service()]
    services += [_ai_provider_service_card(p) for p in ai_svc.list_providers()]
    return services


def overview(introspection=None):
    """Partie 1 : vue d'ensemble résumée, calculée à partir de list_services().

    `total_services`/`ok_count`/`untested_count` et les moyennes globales
    "disponibilité"/"temps de réponse" (mélangeant SQLite/Stripe/SMTP/IA dans
    un seul chiffre non actionnable) ont été retirés (chantier de
    simplification de la page Santé) : seuls `degraded_count`/`down_count`
    restent, pour jauger la sévérité à côté du badge `global_status` — le
    détail précis (quel service, quelle latence) reste dans list_services()."""
    services = list_services(introspection)
    degraded_count = sum(1 for s in services if s["state"] == "degraded")
    down_count = sum(1 for s in services if s["state"] == "down")

    if down_count:
        global_status = "down"
    elif degraded_count:
        global_status = "degraded"
    else:
        global_status = "ok"

    return {
        "global_status": global_status,
        "degraded_count": degraded_count,
        "down_count": down_count,
        "checked_at": _now().isoformat(),
    }


# ── 4. Historique des incidents ──────────────────────────────────────────────
def list_incidents(window="7j"):
    """Partie 4 : chronologie fusionnée à partir de TROIS sources réelles déjà
    existantes — ai_provider_fallback_events (bascules réelles),
    ai_admin_log (actions d'administration échouées) et ai_provider_health
    (dernier échec connu par fournisseur). Aucune table "incident" dédiée
    n'existe : ce module ne fait que composer ce qui est déjà enregistré,
    jamais une invention de ligne."""
    since_iso = _since_iso(window)
    events = []

    for ev in db.list_ai_provider_fallback_events(since_iso=since_iso, limit=500):
        events.append({
            "created_at": ev["created_at"],
            "service": f"{ev['provider_initial']} → {ev['provider_final']}",
            "level": "warning",
            "message": (
                f"Bascule automatique ({ev['reason'] or 'raison non précisée'}) : "
                f"{ev['provider_initial']}/{ev['model_initial']} → {ev['provider_final']}/{ev['model_final']}."
            ),
            "resolution": "Résolu (le fournisseur de secours a pris le relais avec succès).",
            "duration_ms": ev["time_lost_ms"],
        })

    log = admin_ai_log_service.list_log(result="error", date_from=since_iso, page_size=200)
    for entry in log["items"]:
        provider = entry.get("provider")
        events.append({
            "created_at": entry["created_at"],
            "service": provider["name"] if provider else "Administration IA",
            "level": "error",
            "message": (
                f"Action d'administration « {entry['action']} » échouée"
                + (f" : {entry['error_message']}" if entry["error_message"] else ".")
            ),
            "resolution": "Non suivi (aucune notion de résolution pour une action d'administration).",
            "duration_ms": None,
        })

    providers_by_id = {p["id"]: p for p in ai_svc.list_providers()}
    for h in db.list_ai_provider_health():
        if not h["last_failure"]:
            continue
        if since_iso and h["last_failure"] < since_iso:
            continue
        provider = providers_by_id.get(h["provider_id"])
        resolved = bool(h["last_success"]) and h["last_success"] > h["last_failure"]
        events.append({
            "created_at": h["last_failure"],
            "service": provider["name"] if provider else f"Fournisseur #{h['provider_id']}",
            "level": "warning" if resolved else "error",
            "message": "Dernier échec de santé enregistré" + (f" : {h['last_error']}" if h["last_error"] else "."),
            "resolution": (
                "Résolu (un succès plus récent a été enregistré depuis)." if resolved
                else "Non résolu (aucun succès enregistré depuis)."
            ),
            "duration_ms": None,
        })

    events.sort(key=lambda e: e["created_at"], reverse=True)
    return events


# ── 5. Disponibilité ──────────────────────────────────────────────────────────
_MIN_SAMPLES_FOR_AVAILABILITY = 5


def _availability_for_window(window):
    since_iso = _since_iso(window)
    rows = db.list_ai_request_logs_since(since_iso) if since_iso else db.list_ai_request_logs_since("1970-01-01")
    total = len(rows)
    if total < _MIN_SAMPLES_FOR_AVAILABILITY:
        return _na(
            "Données insuffisantes pour calculer la disponibilité "
            f"({total} appel(s) réel(s) enregistré(s) dans ai_request_logs sur cette période, "
            f"{_MIN_SAMPLES_FOR_AVAILABILITY} minimum)."
        )
    success = sum(1 for r in rows if r["success"])
    return _ok(round(success / total * 100, 2))


def availability():
    """Partie 5 : calculée EXCLUSIVEMENT à partir de ai_request_logs (une
    ligne par appel réel, succès ou échec) — jamais une valeur type
    "99.99 %" affichée sans données réelles derrière (voir le seuil minimal
    ci-dessus)."""
    return {window: _availability_for_window(window) for window in ("24h", "7j", "30j")}


# ── 6. Base SQLite ────────────────────────────────────────────────────────────
def database_info(introspection=None):
    if introspection is None:
        introspection = db.sqlite_introspection()
    backups = backup_service.list_backups()
    last_backup = _ok(backups[0]) if backups else _na(
        "Aucune sauvegarde trouvée dans le dossier de sauvegarde (voir backup_service.backup_dir())."
    )
    return {
        "state": _ok("ok") if health_service.check_database() else _ok("down"),
        "introspection": _ok(introspection) if introspection is not None else _na(
            "Moteur PostgreSQL actif : PRAGMA integrity_check/sqlite_master ne s'appliquent qu'à SQLite."
        ),
        "last_backup": last_backup,
    }


# ── 7. Stockage ───────────────────────────────────────────────────────────────
def _dir_size_bytes(path):
    if not path.is_dir():
        return 0
    total = 0
    for dirpath, _dirnames, filenames in os.walk(path):
        for name in filenames:
            try:
                total += (Path(dirpath) / name).stat().st_size
            except OSError:
                continue
    return total


def storage_info():
    """`disk_total_bytes` a été retiré (chantier de simplification de la page
    Santé) : calculé mais jamais affiché (disk_free_bytes/disk_used_bytes
    suffisent à l'alerte "espace disque")."""
    uploads_dir = support_attachment_service.ATTACHMENTS_DIR
    db_size = db.DB_PATH.stat().st_size if db.DB_PATH.exists() else 0
    usage = shutil.disk_usage(ROOT)
    return {
        "uploads_bytes": _ok(_dir_size_bytes(uploads_dir)),
        "database_bytes": _ok(db_size),
        "disk_free_bytes": _ok(usage.free),
        "disk_used_bytes": _ok(usage.used),
    }


# ── 8. Serveur ─────────────────────────────────────────────────────────────────
# `load_average` a été retiré : os.getloadavg() n'existe pas sous Windows,
# système d'exploitation de ce déploiement — toujours indisponible en
# pratique ici (chantier de simplification de la page Santé).
# `ram_available_bytes`/`process_count` retirés : redondants avec ram_percent
# (même fait, deux présentations) ou non actionnables (nombre de process OS
# entier, pas spécifique à NovaMath). `avg_backend_time_ms` retiré : doublon
# exact de `avg_api_response_time_ms` (même variable), jamais affiché sous ce
# second nom.
def server_info():
    uptime_seconds = time.time() - _PROCESS_STARTED_AT
    api_metrics = metrics_service.in_memory_snapshot()
    avg_api_ms = _ok(api_metrics["avg_request_duration_ms"]) if api_metrics["total_requests"] else _na(
        "Aucune requête HTTP n'a encore été comptabilisée par metrics_service depuis le dernier démarrage du "
        "serveur."
    )
    if psutil is None:
        cpu = ram = _na("Le module psutil n'est pas installé sur ce serveur (voir requirements.txt).")
    else:
        cpu = _ok(psutil.cpu_percent(interval=0.1))
        ram = _ok(psutil.virtual_memory().percent)
    return {
        "cpu_percent": cpu,
        "ram_percent": ram,
        "uptime_seconds": round(uptime_seconds),
        "process_started_at": datetime.fromtimestamp(_PROCESS_STARTED_AT, tz=timezone.utc).isoformat(),
        "avg_api_response_time_ms": avg_api_ms,
    }


# ── 11. Alertes ────────────────────────────────────────────────────────────────
def list_alerts():
    """Partie 11 : règles appliquées à des données réelles, avec des seuils
    EXPLICITES (voir les constantes ALERT_* en tête de fichier) — jamais une
    alerte fabriquée sans donnée réelle derrière."""
    alerts = []

    for row in ai_provider_key_service.list_keys():
        if ai_provider_key_service.is_in_cooldown(row):
            alerts.append({
                "level": "warning", "code": "quota_atteint",
                "message": f"Clé API « {row['label']} » ({row['provider_key']}) en cooldown : quota atteint.",
            })

    for h in db.list_ai_provider_health():
        if _provider_state(h) == "down":
            provider = ai_svc.get_provider(h["provider_id"])
            name = provider["name"] if provider else f"Fournisseur #{h['provider_id']}"
            alerts.append({"level": "critical", "code": "api_indisponible", "message": f"{name} est indisponible."})
        if h["average_latency"] and h["average_latency"] > ALERT_LATENCY_MS:
            provider = ai_svc.get_provider(h["provider_id"])
            name = provider["name"] if provider else f"Fournisseur #{h['provider_id']}"
            alerts.append({
                "level": "warning", "code": "latence_elevee",
                "message": f"Latence élevée pour {name} ({round(h['average_latency'])} ms, seuil {ALERT_LATENCY_MS} ms).",
            })

    since_1h = (_now() - timedelta(hours=1)).isoformat()
    fallback_1h = db.list_ai_provider_fallback_events(since_iso=since_1h, limit=1000)
    if len(fallback_1h) >= ALERT_FALLBACK_COUNT_1H:
        alerts.append({
            "level": "warning", "code": "fallback_frequent",
            "message": f"{len(fallback_1h)} bascules de fournisseur en 1h (seuil {ALERT_FALLBACK_COUNT_1H}).",
        })

    db_size_mb = (db.DB_PATH.stat().st_size / (1024 * 1024)) if db.DB_PATH.exists() else 0
    if db_size_mb > ALERT_DB_SIZE_MB:
        alerts.append({
            "level": "info", "code": "base_volumineuse",
            "message": f"Base SQLite volumineuse : {round(db_size_mb)} Mo (seuil {ALERT_DB_SIZE_MB} Mo).",
        })

    backups = backup_service.list_backups()
    if not backups:
        alerts.append({"level": "critical", "code": "sauvegarde_absente", "message": "Aucune sauvegarde n'existe."})
    else:
        age_days = (_now() - _parse_iso(backups[0]["created_at"])).days
        if age_days > ALERT_BACKUP_MAX_AGE_DAYS:
            alerts.append({
                "level": "warning", "code": "sauvegarde_absente",
                "message": f"Dernière sauvegarde vieille de {age_days} jour(s) (seuil {ALERT_BACKUP_MAX_AGE_DAYS}).",
            })

    if not health_service.check_smtp_configured():
        alerts.append({"level": "info", "code": "smtp_non_configure", "message": "SMTP n'est pas configuré."})
    if not health_service.check_stripe_configured():
        alerts.append({"level": "info", "code": "stripe_non_configure", "message": "Stripe n'est pas configuré."})

    return alerts


# ── Agrégat complet (une seule route) ─────────────────────────────────────────
# `ai_providers`/`api_keys` ont été retirés (chantier de simplification de la
# page Santé) : produits mais jamais lus par admin-health.js — ce détail par
# fournisseur duplique intégralement /admin/ia (déjà retiré du rendu
# frontend dans un chantier antérieur, jamais suivi côté backend).
def full_snapshot():
    introspection = db.sqlite_introspection()
    return {
        "overview": overview(introspection),
        "services": list_services(introspection),
        "availability": availability(),
        "database": database_info(introspection),
        "storage": storage_info(),
        "server": server_info(),
        "alerts": list_alerts(),
    }
