"""
Configuration Gunicorn pour NovaMath — lue automatiquement par :

    gunicorn -c gunicorn.conf.py webapp.server:app

exécuté depuis la RACINE du projet (même convention que le README existant,
`FLASK_ENV=production gunicorn webapp.server:app` — cette configuration ne
change ni le module d'entrée ni le comportement par défaut, elle ajoute
uniquement le réglage explicite des workers/timeouts/logging).

Chaque valeur peut être surchargée par une variable d'environnement — jamais
codée en dur ailleurs (même philosophie que webapp/config.py) — voir
.env.example et DEPLOYMENT.md pour la liste complète. Gunicorn est un
serveur POSIX (utilise fcntl/os.fork) : cette configuration n'est chargée
que sous Linux/macOS (Docker, VPS, Railway, Render, Fly.io, Coolify, Azure
App Service pour conteneurs, Cloud Run) — jamais sous Windows, où seul le
serveur de développement Flask (`python webapp/server.py`) est utilisé.
"""
import multiprocessing
import os


def _int_env(name, default):
    raw = os.environ.get(name)
    if not raw:
        return default
    try:
        return int(raw)
    except ValueError:
        return default


def _bool_env(name, default):
    raw = os.environ.get(name)
    if raw is None:
        return default
    return raw.strip().lower() in ("1", "true", "yes", "on")


# ── Réseau ───────────────────────────────────────────────────────────────
# PORT : injecté automatiquement par Railway/Render/Fly.io/Cloud Run/Azure
# App Service (chacun choisit son propre port au démarrage du conteneur) —
# jamais codé en dur. 8000 par défaut (Docker Compose/VPS/exécution locale
# de l'image), cohérent avec l'EXPOSE du Dockerfile.
bind = f"0.0.0.0:{os.environ.get('PORT', '8000')}"

# ── Workers ──────────────────────────────────────────────────────────────
# WEB_CONCURRENCY : convention 12-factor (reconnue nativement par Heroku,
# Railway, Render) pour le nombre de processus workers. Défaut : la formule
# standard Gunicorn (2×CPU+1), plafonnée à 4 pour ne pas épuiser la mémoire
# des instances gratuites/petites des PaaS ciblés (souvent ~512 Mo).
workers = _int_env("WEB_CONCURRENCY", min(multiprocessing.cpu_count() * 2 + 1, 4))

# GUNICORN_THREADS : threads par worker. Un worker "gthread" (thread pool)
# convient à une application principalement I/O-bound (SQLite, fichiers
# JSON, appels sortants Stripe/fournisseur LLM — voir chatbot/providers/) :
# meilleur débit qu'un worker "sync" pur, sans la complexité d'un worker
# asynchrone (gevent/uvicorn), non nécessaire ici.
threads = _int_env("GUNICORN_THREADS", 2)
worker_class = os.environ.get("GUNICORN_WORKER_CLASS", "gthread")

# ── Timeouts ─────────────────────────────────────────────────────────────
# GUNICORN_TIMEOUT : durée max (s) avant qu'un worker jugé silencieux soit
# tué et redémarré — généreux (60s) car certaines requêtes chatbot attendent
# la réponse d'un fournisseur LLM externe.
timeout = _int_env("GUNICORN_TIMEOUT", 60)
# GUNICORN_GRACEFUL_TIMEOUT : délai laissé à un worker pour terminer les
# requêtes en cours lors d'un redémarrage/déploiement (SIGTERM) avant d'être
# forcé (SIGKILL) — permet un déploiement sans requête coupée en plein vol.
graceful_timeout = _int_env("GUNICORN_GRACEFUL_TIMEOUT", 30)
# GUNICORN_KEEPALIVE : durée (s) qu'une connexion HTTP keep-alive reste
# ouverte en attendant une nouvelle requête — valeur standard derrière un
# reverse-proxy (Nginx/Railway/Render/Cloud Run terminent déjà le keep-alive
# côté client, ce réglage ne concerne que la connexion proxy <-> Gunicorn).
keepalive = _int_env("GUNICORN_KEEPALIVE", 5)

# ── Recyclage des workers (fuite mémoire / dérive long-terme) ──────────────
# GUNICORN_MAX_REQUESTS : un worker est recyclé après ce nombre de requêtes
# traitées — filet de sécurité contre une fuite mémoire progressive (ex :
# cache interne du chatbot, voir chatbot/cache.py) sans jamais nécessiter de
# redémarrage manuel du service.
max_requests = _int_env("GUNICORN_MAX_REQUESTS", 1000)
# GUNICORN_MAX_REQUESTS_JITTER : variation aléatoire ajoutée à max_requests
# pour éviter que tous les workers ne recyclent exactement au même instant
# (pic de latence synchronisé sinon).
max_requests_jitter = _int_env("GUNICORN_MAX_REQUESTS_JITTER", 100)

# ── Logging (12-factor : toujours stdout/stderr, jamais un fichier — la
# rotation/agrégation des logs est déléguée à la plateforme d'hébergement/
# Docker/journald, jamais gérée ici ; voir webapp/logging_service.py pour le
# format structuré des logs applicatifs, indépendant de ceux-ci qui restent
# les logs d'accès/erreurs bas niveau de Gunicorn lui-même) ─────────────────
accesslog = os.environ.get("GUNICORN_ACCESSLOG", "-")
errorlog = os.environ.get("GUNICORN_ERRORLOG", "-")
loglevel = os.environ.get("GUNICORN_LOGLEVEL", "info").strip().lower()

# GUNICORN_PRELOAD_APP : charge l'application UNE FOIS dans le processus
# maître avant de forker les workers (au lieu qu'aucun worker ne l'importe
# indépendamment) — réduit la mémoire totale (le modèle ML de
# webapp/models/level_predictor.pkl est alors partagé en copy-on-write entre
# workers) et accélère le démarrage. Sûr ici : aucune connexion base de
# données ni tâche de fond persistante n'est ouverte au niveau module (voir
# webapp/db.py, chaque connexion SQLite est ouverte puis fermée par appel).
preload_app = _bool_env("GUNICORN_PRELOAD_APP", True)
