"""
En-têtes de sécurité HTTP pour NovaMath — niveau proche d'un SaaS
professionnel (Content-Security-Policy, HSTS, X-Frame-Options, etc.).

Architecture stricte, identique à logging_service.py/health_service.py :

    server.py  →  security_headers_service.py  →  config.py

jamais l'inverse. server.py ne fait qu'appeler
`security_headers_service.init_app(app)` — toute la construction des
en-têtes vit ici, entièrement pilotée par config.py (aucune valeur codée en
dur dans server.py).

Remplace l'ancien `@app.after_request security_headers()` qui vivait dans
server.py (même comportement CSP à base de nonce + Cache-Control "jamais de
cache", désormais piloté par la configuration au lieu d'être codé en dur, et
étendu : HSTS conditionnel, Permissions-Policy plus complète,
Cross-Origin-Opener-Policy, Cross-Origin-Resource-Policy, en-tête Server
neutralisé).

Sources externes réellement chargées par le frontend (vérifié dans
webapp/static/ : aucun autre domaine externe n'est référencé) :
- KaTeX (rendu des formules mathématiques) et jsPDF (export PDF), tous deux
  servis par le CDN jsdelivr — scripts, feuille de style et fonts.
Stripe Checkout et Google OAuth sont intégrés par redirection complète du
navigateur (voir abonnement.js / auth.py::oauth_start) — jamais par un
script, un iframe ou un appel fetch() embarqué — donc aucune autorisation
CSP supplémentaire n'est nécessaire pour ces deux services : une CSP stricte
ne peut pas bloquer une redirection HTTP standard (Location).

Cross-Origin-Embedder-Policy (COEP) n'est PAS envoyée : l'activer
(`require-corp`) casserait le chargement des scripts/styles/fonts KaTeX et
du script jsPDF depuis jsdelivr, qui ne portent pas l'attribut `crossorigin`
et pour lesquels la présence d'en-têtes CORP/CORS n'est pas garantie —
"uniquement si compatible" (cahier des charges) est donc interprété comme
"non" tant que ces dépendances restent chargées telles quelles.
"""
import logging

from flask import g, request

import config

logger = logging.getLogger("security_headers_service")

# Unique CDN externe utilisé par le frontend (KaTeX + jsPDF, voir docstring
# ci-dessus) — jamais un autre domaine sans revue explicite de ce fichier.
_KATEX_CDN = "https://cdn.jsdelivr.net"

# Longueur minimale usuelle pour que `preload` ait un sens (1 an, valeur
# recommandée par hstspreload.org) — sous ce seuil, HSTS reste actif mais
# sans le directive `preload` (qui exige un engagement long).
_HSTS_PRELOAD_MIN_AGE = 31536000


def _split_sources(raw):
    """Convertit une variable d'environnement "a b c" (séparée par des
    espaces) en liste de sources CSP — jamais d'erreur si vide/absente."""
    return [source for source in (raw or "").split() if source]


def _dedupe(sources):
    """Préserve l'ordre, retire les doublons — deux variables d'env pourraient
    se recouper avec les valeurs par défaut."""
    return list(dict.fromkeys(sources))


def _is_https(req):
    """HTTPS réel, ou signalé par un reverse-proxy (X-Forwarded-Proto) — même
    convention que le reste du projet pour lire un en-tête de proxy (voir
    rate_limit_service.py/logging_service.py et leur lecture de
    X-Forwarded-For), plutôt qu'un middleware ProxyFix absent de ce projet."""
    if req.is_secure:
        return True
    return req.headers.get("X-Forwarded-Proto", "").strip().lower() == "https"


def build_csp(nonce=None):
    """Construit la valeur de l'en-tête CSP (Content-Security-Policy ou
    Content-Security-Policy-Report-Only selon config.CSP_REPORT_ONLY).

    `nonce` : nonce du script inline injecté par `_serve_protected()` dans
    server.py (page protégée uniquement) — permet un script-src strict, sans
    jamais 'unsafe-inline' ni 'unsafe-eval'."""
    script_sources = _dedupe(["'self'", _KATEX_CDN] + ([f"'nonce-{nonce}'"] if nonce else []))
    # style-src garde 'unsafe-inline' : de nombreux styles inline sont générés
    # dynamiquement par le JS existant (dashboard.js, profil.js, reviews.js,
    # ...) — les migrer vers des classes CSS est hors périmètre de cette passe
    # (voir TODO.md). C'est la SEULE directive avec 'unsafe-inline' — jamais
    # sur script-src, et 'unsafe-eval' n'est utilisé nulle part.
    style_sources = _dedupe(["'self'", "'unsafe-inline'", _KATEX_CDN])
    img_sources = _dedupe(["'self'", "data:"] + _split_sources(config.CSP_ALLOWED_IMAGES))
    font_sources = _dedupe(["'self'", _KATEX_CDN] + _split_sources(config.CSP_ALLOWED_FONTS))
    connect_sources = _dedupe(["'self'"] + _split_sources(config.CSP_ALLOWED_CONNECT))

    directives = [
        "default-src 'self'",
        f"script-src {' '.join(script_sources)}",
        f"style-src {' '.join(style_sources)}",
        f"img-src {' '.join(img_sources)}",
        f"font-src {' '.join(font_sources)}",
        f"connect-src {' '.join(connect_sources)}",
        "frame-src 'none'",
        "object-src 'none'",
        "base-uri 'self'",
        "frame-ancestors 'none'",
        "form-action 'self'",
    ]
    if config.IS_PRODUCTION:
        directives.append("upgrade-insecure-requests")
    return "; ".join(directives)


def build_hsts():
    """Valeur de Strict-Transport-Security, ou None si HSTS ne doit pas être
    envoyée pour cette requête (jamais en développement, jamais hors HTTPS —
    voir _is_https)."""
    if not (config.ENABLE_HSTS and config.IS_PRODUCTION and _is_https(request)):
        return None
    value = f"max-age={config.HSTS_MAX_AGE}; includeSubDomains"
    if config.HSTS_MAX_AGE >= _HSTS_PRELOAD_MIN_AGE:
        value += "; preload"
    return value


def apply_headers(response):
    """Pose l'ensemble des en-têtes de sécurité + la politique de cache sur
    `response`. Appelée par le middleware `after_request` installé par
    init_app() — jamais appelée directement par une route."""
    # ── Cache-Control ───────────────────────────────────────────────────────
    # Projet en développement actif : aucun cache navigateur, pour être sûr
    # que chaque rechargement récupère la dernière version du JS/CSS (sinon
    # un correctif déjà livré peut sembler "ne pas s'appliquer" côté client).
    # Comportement inchangé (déplacé tel quel depuis server.py).
    response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"

    if not config.ENABLE_SECURITY_HEADERS:
        return response

    nonce = getattr(g, "csp_nonce", None)
    csp_header = "Content-Security-Policy-Report-Only" if config.CSP_REPORT_ONLY else "Content-Security-Policy"
    response.headers[csp_header] = build_csp(nonce)

    hsts_value = build_hsts()
    if hsts_value is not None:
        response.headers["Strict-Transport-Security"] = hsts_value

    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Permissions-Policy"] = (
        "geolocation=(), microphone=(), camera=(), payment=(), usb=(), "
        "magnetometer=(), gyroscope=(), accelerometer=(), interest-cohort=()"
    )
    # Défense en profondeur pré-CSP (navigateurs anciens sans frame-ancestors) :
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Cross-Origin-Opener-Policy"] = "same-origin"
    response.headers["Cross-Origin-Resource-Policy"] = "same-origin"
    # Aucune ressource de ce projet n'est destinée à être embarquée/chargée
    # depuis un autre site — voir docstring du module pour Cross-Origin-
    # Embedder-Policy (COEP), volontairement absente (incompatible avec le
    # CDN KaTeX/jsPDF tel qu'utilisé aujourd'hui).

    # Neutralise la valeur du header Server plutôt que de la supprimer : sous
    # Gunicorn (production), l'application contrôle ce header et cette valeur
    # est bien celle envoyée au client. Sous le serveur de développement
    # Werkzeug, le header "Server: Werkzeug/x.x Python/x.x" est ajouté par le
    # serveur HTTP lui-même après la réponse de l'application et ne peut pas
    # être modifié depuis ici — suppression "si possible" (cahier des
    # charges), donc effective uniquement en production.
    response.headers["Server"] = "NovaMath"

    return response


def init_app(app):
    """Installe le middleware d'en-têtes de sécurité sur `app`. Appelée une
    seule fois depuis server.py, après logging_service.init_app(app) — server.py
    ne fait ensuite plus que router, toute la logique reste ici."""

    @app.after_request
    def _security_headers(response):
        return apply_headers(response)

    return app
