"""
Source unique de vérité du rate limiting HTTP (fréquence des requêtes) pour
NovaMath.

Architecture stricte, identique à plan_service.py/quota_service.py/
role_service.py :

    server.py / auth.py  →  rate_limit_service.py  →  db.py

jamais l'inverse. Ce module ne connaît ni Stripe, ni les plans, ni les rôles —
il ne fait qu'une chose : compter des requêtes HTTP par (identité, endpoint)
sur une fenêtre glissante et décider de laisser passer ou non.

Distinct de quota_service.py : QuotaType limite un VOLUME métier quotidien
(ex: 25 messages chatbot/jour, remis à zéro chaque jour) ; rate_limit_service
limite une FRÉQUENCE (ex: 5 tentatives de connexion/minute), protège le
serveur/les coûts Anthropic/Stripe contre les bots et le brute force, et ne
partage aucune table ni aucune logique avec les quotas (voir
db.py::rate_limit_events, distincte de user_daily_usage).

Identité : privilégie toujours `request.current_user` (déjà résolu par
@login_required plus haut dans la pile de décorateurs — voir
plan_service.requires_feature/role_service.requires_role, même convention).
À défaut (aucune session, ou route intentionnellement anonyme comme
login/register/forgot-password, ou authentification optionnelle comme
POST /api/reviews), la clé retombe sur l'adresse IP. Ce module ne lit jamais
lui-même le cookie de session ni n'appelle auth.get_current_user() — cela
créerait une dépendance circulaire (auth.py doit pouvoir importer ce module
pour décorer /login, /register, etc.) et dupliquerait une logique qui vit
déjà dans auth.py.

Algorithme : fenêtre glissante réelle (sliding window), pas un compteur
remis à zéro sur une minute calendaire. Chaque requête acceptée est
enregistrée dans un "bucket" d'1 seconde (window_start = epoch seconds) ;
l'usage courant est recalculé à chaque appel en sommant tous les buckets
encore dans la fenêtre des `per_seconds` dernières secondes. Précision : à la
seconde près, largement suffisant pour des fenêtres de 60s à 3600s, et bien
moins coûteux en lignes qu'un vrai log d'un timestamp par requête individuelle
sous forte charge (plusieurs requêtes par seconde d'un même client regroupées
dans le même bucket).

Concurrence : même technique que quota_service.consume() (incrémenter
D'ABORD via une opération SQL atomique unique, vérifier ENSUITE, annuler
l'incrément si la limite est dépassée) — jamais un lire-puis-écrire séparé
qui laisserait une fenêtre à une requête concurrente.
"""
import logging
import time
from collections import namedtuple
from functools import wraps
from typing import Optional

from flask import current_app, jsonify, make_response, request

import db

logger = logging.getLogger("rate_limit_service")

# Toute fenêtre plus ancienne que ceci n'a plus d'influence sur AUCUNE
# décision de rate limiting actuellement configurée dans le projet (le plus
# grand per_seconds utilisé aujourd'hui est 3600, voir les @rate_limit(...)
# posés dans auth.py/server.py) — seule valeur que cleanup() doit connaître
# pour rester sûre sans dépendre de la liste exacte des routes décorées.
DEFAULT_RETENTION_SECONDS = 3600


RateLimitState = namedtuple("RateLimitState", "allowed limit remaining reset retry_after")


def _client_ip() -> str:
    """Même expression que auth.py::_log_security_event (X-Forwarded-For en
    priorité, sinon l'adresse socket directe) — pas de dépendance vers
    auth.py pour autant : c'est un idiome d'une ligne, pas une logique
    métier à centraliser."""
    return request.headers.get("X-Forwarded-For", request.remote_addr) or "unknown"


def _identity_key() -> str:
    """Clé d'identité pour le rate limiting : `user:<id>` si un compte est
    déjà résolu dans la requête courante (voir docstring du module),
    `ip:<adresse>` sinon. Toujours préfixée par son type pour qu'un id
    utilisateur ne puisse jamais collisionner avec une adresse IP qui
    ressemblerait à la même chaîne."""
    user = getattr(request, "current_user", None)
    if user is not None:
        return f"user:{user['id']}"
    return f"ip:{_client_ip()}"


def check(key: str, endpoint: str, requests: int, per_seconds: int) -> RateLimitState:
    """Décide si une requête pour (key, endpoint) est autorisée sous la
    limite `requests` par fenêtre glissante de `per_seconds` secondes, et
    enregistre la tentative si elle est autorisée. Fonction pure vis-à-vis de
    l'appelant (aucun accès à `request` ici) — testable indépendamment de
    Flask, réutilisée par le décorateur rate_limit() ci-dessous.

    Incrémente D'ABORD (opération atomique unique, voir db.record_rate_limit_
    event), compare ENSUITE : si le total dépasse `requests`, l'incrément qui
    vient d'être posé est immédiatement annulé par un décrément tout aussi
    atomique avant de refuser — jamais de requête comptée au-delà de la
    limite même sous accès concurrents (même principe que
    quota_service.consume())."""
    now = int(time.time())
    since = now - per_seconds + 1

    db.record_rate_limit_event(key, endpoint, now, amount=1)
    total, oldest = db.get_rate_limit_usage(key, endpoint, since)
    effective_oldest = oldest if oldest is not None else now
    reset = effective_oldest + per_seconds

    if total > requests:
        db.record_rate_limit_event(key, endpoint, now, amount=-1)
        retry_after = max(1, reset - now)
        return RateLimitState(allowed=False, limit=requests, remaining=0, reset=reset, retry_after=retry_after)

    remaining = max(0, requests - total)
    return RateLimitState(allowed=True, limit=requests, remaining=remaining, reset=reset, retry_after=0)


def _apply_headers(resp, state: RateLimitState):
    """Pose les en-têtes X-RateLimit-* (convention GitHub) sur `resp`, qu'elle
    corresponde à une requête autorisée ou refusée — un client doit toujours
    pouvoir lire sa limite/son usage restant, pas seulement en cas de 429."""
    resp.headers["X-RateLimit-Limit"] = str(state.limit)
    resp.headers["X-RateLimit-Remaining"] = str(state.remaining)
    resp.headers["X-RateLimit-Reset"] = str(state.reset)
    if not state.allowed:
        resp.headers["Retry-After"] = str(state.retry_after)
    return resp


def rate_limit(requests: int, per_seconds: int, methods: Optional[set] = None):
    """Décorateur de route Flask : limite `requests` requêtes par fenêtre
    glissante de `per_seconds` secondes, par identité (voir _identity_key)
    et par route. Même style que role_service.requires_role /
    plan_service.requires_feature :

        @app.route(...)
        @login_required            # pose request.current_user AVANT nous
        @rate_limit(requests=5, per_seconds=60)
        def view():
            ...

    Sur une route sans @login_required (ex: /api/auth/login — anonyme par
    construction), la clé retombe simplement sur l'IP, ce qui est le
    comportement voulu (on ne peut pas rate-limiter par compte une tentative
    de connexion qui n'a pas encore réussi).

    `methods` (optionnel) restreint le contrôle à un sous-ensemble des
    méthodes HTTP de la route — utile quand une seule vue Flask gère
    plusieurs méthodes dont une seule doit être limitée (ex: POST /api/reviews
    gère GET *et* POST, seule la création doit être limitée ; voir server.py).
    None (par défaut) limite toutes les méthodes de la route.

    Réponse 429 au format demandé par le frontend (voir api.js) :

        {"error": "rate_limited", "retry_after": 42}

    plus les en-têtes X-RateLimit-Limit/Remaining/Reset (et Retry-After)
    posés dans tous les cas, succès compris — jamais de 500, jamais de
    détail sur l'identité/les autres clients dans la réponse.

    Coupe-circuit global : app.config["RATE_LIMIT_ENABLED"] (voir config.py,
    dérivé de FLASK_ENV — False par défaut hors production) désactive tout
    contrôle sans qu'il soit nécessaire de retirer ce décorateur route par
    route, même principe que ENABLE_DEV_DASHBOARD dans server.py."""
    def decorator(view):
        @wraps(view)
        def wrapped(*args, **kwargs):
            if not current_app.config.get("RATE_LIMIT_ENABLED", True):
                return make_response(view(*args, **kwargs))
            if methods is not None and request.method not in methods:
                return make_response(view(*args, **kwargs))

            # request.endpoint est toujours résolu pour une route Flask
            # réelle (werkzeug l'assigne au moment du routage) ; le repli sur
            # request.path ne joue que dans un contexte de requête construit
            # à la main (tests) sans passer par le routage applicatif.
            endpoint = request.endpoint or request.path
            state = check(_identity_key(), endpoint, requests, per_seconds)
            if not state.allowed:
                logger.info(
                    "Rate limit dépassé : endpoint=%s limite=%s/%ss retry_after=%ss",
                    endpoint, requests, per_seconds, state.retry_after,
                )
                resp = jsonify({"error": "rate_limited", "retry_after": state.retry_after})
                resp.status_code = 429
                return _apply_headers(resp, state)

            resp = make_response(view(*args, **kwargs))
            return _apply_headers(resp, state)
        return wrapped
    return decorator


def cleanup(older_than_seconds: int = DEFAULT_RETENTION_SECONDS) -> int:
    """Supprime les buckets dont la fenêtre ne peut plus influencer aucune
    décision de rate limiting (window_start plus ancien que `older_than_
    seconds`) — empêche rate_limit_events de grossir indéfiniment. Aucune
    tâche planifiée n'existe dans ce projet (même situation que
    db.cleanup_expired_guests) : appelée une fois au démarrage du serveur
    (voir server.py, juste après db.init_db()), idempotente et sûre à
    répéter. Renvoie le nombre de lignes supprimées."""
    cutoff = int(time.time()) - older_than_seconds
    deleted = db.cleanup_rate_limit_events(cutoff)
    if deleted:
        logger.info("Nettoyage rate_limit_events : %s fenêtre(s) expirée(s) supprimée(s).", deleted)
    return deleted
