"""
Journalisation structurée + supervision runtime pour NovaMath.

Architecture stricte, identique à plan_service.py/quota_service.py/
role_service.py/rate_limit_service.py :

    server.py  →  logging_service.py  →  db.py (indirectement, via metrics_service)

jamais l'inverse. Ce module centralise TOUTE la configuration du logging du
projet (aucun autre fichier n'appelle logging.basicConfig() ni ne construit
de Formatter/Handler) — chaque module continue d'utiliser
`logging.getLogger("<nom>")` exactement comme avant (billing_service.py,
quota_service.py, rate_limit_service.py, chatbot/...), sans aucune
modification : configure_logging() agit au niveau du logger racine, donc
tous les logs existants du projet héritent automatiquement du format
structuré et de l'enrichissement (utilisateur/IP/requête) définis ici.

Trois responsabilités :
1. Formatage structuré (StructuredFormatter) — lisible en développement,
   JSON en production (Partie 1) : timestamp, niveau, module, utilisateur,
   IP, requête, durée, message. Un logging.Filter (_ContextFilter) enrichit
   CHAQUE LogRecord depuis le contexte Flask courant, sans toucher aux
   centaines d'appels `logger.info(...)` déjà écrits ailleurs dans le projet.
2. Intégration Sentry optionnelle (Partie 2) — activée uniquement si
   SENTRY_DSN est configurée ET que le paquet sentry-sdk est installé ;
   absente des deux : le système fonctionne normalement, jamais d'exception.
3. Middleware Flask (init_app) — mesure la durée de chaque requête, journalise
   sa fin, et capture toute exception non gérée (Partie 6, "panic log") sans
   jamais la laisser disparaître silencieusement ; alimente metrics_service
   (compteurs) sans qu'aucune autre route n'ait à s'en soucier.
"""
import json
import logging
import time
import uuid
from datetime import datetime, timezone

from flask import g, has_request_context, jsonify, request
from werkzeug.exceptions import HTTPException

import config
import metrics_service

logger = logging.getLogger("logging_service")
request_logger = logging.getLogger("http")

_configured = False
_sentry_enabled = False


class _ContextFilter(logging.Filter):
    """Enrichit chaque LogRecord avec l'utilisateur/l'IP/la requête courants
    (contexte Flask), sans jamais lever si aucune requête n'est en cours
    (logs de démarrage, tâches de fond, tests hors contexte de requête)."""

    def filter(self, record):
        if has_request_context():
            user = getattr(request, "current_user", None)
            record.user = user["id"] if user else "-"
            record.ip = request.headers.get("X-Forwarded-For", request.remote_addr) or "-"
            record.request = f"{request.method} {request.path}"
        else:
            record.user = "-"
            record.ip = "-"
            record.request = "-"
        # duration_ms n'est connue qu'à la toute fin d'une requête (voir
        # _log_request ci-dessous, qui la fournit via extra=) — ne jamais
        # écraser une valeur déjà posée explicitement par l'appelant.
        if not hasattr(record, "duration_ms"):
            record.duration_ms = "-"
        # BLACK BOX RECORDER : identifiant unique de requête, posé sur `g` une
        # seule fois par requête HTTP (voir _start_request_timer ci-dessous) —
        # enrichit AUTOMATIQUEMENT chaque logger.info/warning/exception déjà
        # existant dans tout le projet, sans modifier aucun des appels
        # logger.*() existants. Ne jamais écraser une valeur déjà posée
        # explicitement par l'appelant via extra= : c'est le cas des
        # générateurs SSE (server.py/conversation_manager.py), qui exécutent
        # APRÈS que Flask ait dépilé le contexte de requête (has_request_context()
        # y est donc False) et doivent transmettre request_id explicitement.
        if not hasattr(record, "request_id"):
            record.request_id = getattr(g, "_novamath_request_id", "-") if has_request_context() else "-"
        return True


class StructuredFormatter(logging.Formatter):
    """Un seul Formatter pour tout le projet, deux rendus :
    - développement : une ligne lisible humainement ;
    - production (config.IS_PRODUCTION) : une ligne JSON, prête à être
      ingérée telle quelle par Sentry/Datadog/Grafana Loki/ELK (Partie 1)."""

    def __init__(self, json_output):
        super().__init__()
        self.json_output = json_output

    def format(self, record):
        payload = {
            "timestamp": datetime.fromtimestamp(record.created, tz=timezone.utc).isoformat(),
            "level": record.levelname,
            "module": record.name,
            "user": getattr(record, "user", "-"),
            "ip": getattr(record, "ip", "-"),
            "request": getattr(record, "request", "-"),
            "request_id": getattr(record, "request_id", "-"),
            "duration_ms": getattr(record, "duration_ms", "-"),
            "message": record.getMessage(),
        }
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)

        if self.json_output:
            return json.dumps(payload, ensure_ascii=False, default=str)

        line = (
            f"{payload['timestamp']} {payload['level']:<8} {payload['module']} | "
            f"user={payload['user']} ip={payload['ip']} request={payload['request']} "
            f"request_id={payload['request_id']} duration_ms={payload['duration_ms']} | {payload['message']}"
        )
        if "exception" in payload:
            line += f"\n{payload['exception']}"
        return line


def configure_logging():
    """Configure le logger racine (niveau, handler, formatter, filtre) et
    tente d'activer Sentry — idempotent (peut être rappelée sans dupliquer de
    handlers, utile en tests ou en cas de rechargement). Renvoie le logger
    racine, surtout utile pour les tests."""
    global _configured
    level = getattr(logging, config.LOG_LEVEL, logging.INFO)
    root = logging.getLogger()
    root.setLevel(level)
    for handler in list(root.handlers):
        root.removeHandler(handler)

    handler = logging.StreamHandler()
    handler.setFormatter(StructuredFormatter(json_output=config.IS_PRODUCTION))
    handler.addFilter(_ContextFilter())
    root.addHandler(handler)

    configure_sentry()
    _configured = True
    return root


def configure_sentry():
    """Active Sentry si SENTRY_DSN est configurée (Partie 2). Absence de
    SENTRY_DSN, ou paquet sentry-sdk non installé : ne fait rien, ne lève
    jamais — le système doit fonctionner normalement dans les deux cas.
    Renvoie True si Sentry est effectivement actif après cet appel."""
    global _sentry_enabled
    if not config.SENTRY_DSN:
        _sentry_enabled = False
        return False
    try:
        import sentry_sdk
        from sentry_sdk.integrations.flask import FlaskIntegration
    except ImportError:
        logger.warning(
            "SENTRY_DSN configurée mais le paquet sentry-sdk n'est pas installé — Sentry désactivé."
        )
        _sentry_enabled = False
        return False

    sentry_sdk.init(
        dsn=config.SENTRY_DSN,
        integrations=[FlaskIntegration()],
        environment=config.FLASK_ENV,
        # Aucune trace de performance envoyée par défaut : ce projet ne fait
        # que du suivi d'erreurs (Partie 2), jamais de profiling à distance
        # sans configuration explicite ultérieure.
        traces_sample_rate=0.0,
    )
    _sentry_enabled = True
    return True


def sentry_enabled():
    """État courant de l'intégration Sentry — utilisé par health_service.py
    et les tests, sans dupliquer la logique de configure_sentry()."""
    return _sentry_enabled


def capture_exception(exc):
    """Point d'entrée unique pour signaler une exception (Partie 6) :
    journalise TOUJOURS (jamais d'erreur perdue silencieusement, même sans
    Sentry), et transmet en plus à Sentry si configuré."""
    logger.error("Exception non gérée : %s", exc, exc_info=exc)
    if _sentry_enabled:
        import sentry_sdk
        sentry_sdk.capture_exception(exc)


def init_app(app):
    """Installe le middleware HTTP de NovaMath sur `app` : configuration du
    logging, mesure de la durée de chaque requête, journal de fin de requête,
    alimentation de metrics_service, et capture de toute exception non gérée
    (panic log, Partie 6) — jamais silencieuse, jamais un 500 générique sans
    trace.

    Appelée une seule fois depuis server.py (server.py ne fait ensuite plus
    que router, toute la logique reste ici)."""
    configure_logging()

    @app.before_request
    def _start_request_timer():
        g._novamath_request_start = time.perf_counter()
        # BLACK BOX RECORDER : un seul identifiant généré une fois par requête
        # HTTP, transporté par `g` (routes classiques, via _ContextFilter
        # ci-dessus) et par le header de réponse X-Request-Id ci-dessous (lu
        # par api.js côté frontend) — jamais recalculé ailleurs, jamais un
        # second système d'identifiant.
        g._novamath_request_id = uuid.uuid4().hex

    @app.after_request
    def _log_request(response):
        # Ne compte PAS les erreurs ici (voir _handle_unexpected_exception
        # ci-dessous, seul point qui incrémente metrics_service.record_error())
        # : en mode debug, ce handler re-lève l'exception (pour laisser le
        # débogueur Werkzeug s'en charger) et ce hook after_request n'est
        # alors jamais atteint — le compter aussi ici double-compterait la
        # même exception dans le cas hors-debug, où les deux s'exécutent.
        start = getattr(g, "_novamath_request_start", None)
        duration_ms = round((time.perf_counter() - start) * 1000, 2) if start is not None else 0.0
        metrics_service.record_request(duration_ms)
        # BLACK BOX RECORDER : renvoyé au frontend pour que chatbot.js/api.js
        # puissent attacher le même request_id à un rapport d'erreur éventuel
        # (voir buildApiError() dans api.js) — un simple en-tête de réponse,
        # aucun changement du corps ni du code HTTP de la réponse.
        response.headers["X-Request-Id"] = getattr(g, "_novamath_request_id", "-")
        request_logger.info(
            "%s %s -> %s", request.method, request.path, response.status_code,
            extra={"duration_ms": duration_ms},
        )
        return response

    @app.errorhandler(Exception)
    def _handle_unexpected_exception(exc):
        # Les erreurs HTTP "normales" (404, 400 volontaire via abort(), etc.)
        # ne sont pas des pannes : laissées à la gestion standard de Flask,
        # jamais journalisées comme une exception non gérée.
        if isinstance(exc, HTTPException):
            return exc

        metrics_service.record_error()
        capture_exception(exc)

        if app.debug:
            # Développement local : laisse le débogueur interactif Werkzeug
            # afficher la traceback comme avant l'ajout de ce middleware —
            # seul le log/la capture Sentry ci-dessus est un ajout, jamais
            # une dégradation de l'expérience de développement.
            raise exc
        return jsonify({"error": "Une erreur interne est survenue."}), 500

    return app
