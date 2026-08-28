"""
Configuration centralisée dépendant de l'environnement (dev / production).

Une seule variable pilote tout : FLASK_ENV=development (défaut) ou
FLASK_ENV=production. Chaque valeur dérivée peut être surchargée
individuellement par sa propre variable d'environnement si besoin (ex :
tester des cookies Secure en local avec un reverse-proxy HTTPS).

Rien n'est codé en dur : toute valeur sensible vient de l'environnement
(chargé depuis .env par server.py via python-dotenv avant l'import de ce
module).
"""
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def _env_flag(name, default):
    raw = os.environ.get(name)
    if raw is None:
        return default
    return raw.strip().lower() in ("1", "true", "yes", "on")


FLASK_ENV = os.environ.get("FLASK_ENV", "development").strip().lower()
IS_PRODUCTION = FLASK_ENV == "production"

# Débogueur Werkzeug + reloader (app.run) — jamais en production.
DEBUG = _env_flag("FLASK_DEBUG", not IS_PRODUCTION)

# Confiance dans les en-têtes X-Forwarded-* (X-Forwarded-Proto/-For/-Host)
# envoyés par un reverse proxy en amont (Render/Railway/Fly.io/Cloud Run
# terminent tous le TLS à la frontière et transmettent du HTTP en clair au
# conteneur) — voir server.py, où ProxyFix (werkzeug) n'est appliqué que si
# cette valeur est vraie. Sans ça, request.url_root/request.is_secure
# restent "http://" même derrière un domaine HTTPS réel, ce qui aurait
# généré des success_url/cancel_url Stripe et des liens d'email en http://
# (voir webapp/server.py::api_checkout_create_session, auth.py::APP_BASE_URL).
# Activé par défaut UNIQUEMENT en production (jamais en dev local, où il n'y
# a par définition aucun reverse proxy devant Flask) — désactivable
# explicitement si l'hébergeur choisi ne passe pas par un proxy de confiance.
TRUST_PROXY_HEADERS = _env_flag("TRUST_PROXY_HEADERS", IS_PRODUCTION)

# Cookie de session Flask (session["q"], etc. — état du quiz, server.py).
SESSION_COOKIE_SECURE = _env_flag("SESSION_COOKIE_SECURE", IS_PRODUCTION)
SESSION_COOKIE_HTTPONLY = _env_flag("SESSION_COOKIE_HTTPONLY", True)
SESSION_COOKIE_SAMESITE = os.environ.get("SESSION_COOKIE_SAMESITE", "Lax")

# Cookie nm_session (connexion, y compris "remember me" 30 jours — auth.py).
REMEMBER_COOKIE_SECURE = _env_flag("REMEMBER_COOKIE_SECURE", IS_PRODUCTION)

# Cookie nm_csrf (double-submit CSRF, reste volontairement lisible en JS — auth.py).
CSRF_COOKIE_SECURE = _env_flag("CSRF_COOKIE_SECURE", IS_PRODUCTION)

# Rate limiting HTTP (webapp/rate_limit_service.py) — désactivé par défaut
# hors production : la suite de tests appelle /api/auth/register et
# /api/auth/login des centaines de fois depuis la même IP (client de test
# Flask) sur la base SQLite réelle, non isolée par test (voir
# tests/test_server_feature_gating.py et consorts) ; y appliquer les mêmes
# limites qu'en production casserait la quasi-totalité de la suite sans
# rien apporter (la protection anti-bots n'a pas de sens en local/CI). Les
# tests dédiés au rate limiting (tests/test_rate_limit_service.py,
# test_server_rate_limits.py) l'activent explicitement pour la durée de leurs
# propres cas, comme n'importe quelle autre configuration de test ciblée.
RATE_LIMIT_ENABLED = _env_flag("RATE_LIMIT_ENABLED", IS_PRODUCTION)

# Journalisation structurée (webapp/logging_service.py) — niveau standard du
# module logging ("DEBUG"/"INFO"/"WARNING"/"ERROR"/"CRITICAL").
LOG_LEVEL = os.environ.get("LOG_LEVEL", "INFO").strip().upper()

# Sentry (webapp/logging_service.py) — absent par défaut : aucune erreur, le
# système fonctionne normalement sans Sentry configuré (voir sa docstring).
SENTRY_DSN = os.environ.get("SENTRY_DSN") or None

# Sauvegardes (webapp/backup_service.py). Dossier créé automatiquement s'il
# n'existe pas encore ; rétention en jours, avec un second filet de sécurité
# (nombre absolu de sauvegardes) codé dans backup_service.py lui-même — pas
# une valeur "sensible", mais centralisée ici comme le reste de la config.
BACKUP_DIRECTORY = os.environ.get("BACKUP_DIRECTORY", str(ROOT / "backups"))
# Plancher à 1 jour : BACKUP_RETENTION_DAYS=0 (ou une valeur négative, par
# erreur de configuration) supprimerait sinon TOUTE sauvegarde, y compris
# celle qui vient d'être créée dans le même appel (voir
# backup_service._apply_retention, exécutée juste après backup_database()).
BACKUP_RETENTION_DAYS = max(1, int(os.environ.get("BACKUP_RETENTION_DAYS", "30")))

# Sauvegarde automatique quotidienne (webapp/backup_scheduler.py) — désactivée
# uniquement si explicitement mise à "0"/"false" (ex: environnement de test),
# activée par défaut partout ailleurs, y compris en développement local.
# BACKUP_AUTO_HOUR_UTC : heure (0-23, UTC) à partir de laquelle la sauvegarde
# du jour est déclenchée si elle ne l'a pas encore été — 3h UTC par défaut,
# creux de trafic pour un public scolaire francophone.
BACKUP_AUTO_ENABLED = _env_flag("BACKUP_AUTO_ENABLED", True)
BACKUP_AUTO_HOUR_UTC = int(os.environ.get("BACKUP_AUTO_HOUR_UTC", "3"))
# Fréquence à laquelle le thread de fond vérifie s'il doit déclencher la
# sauvegarde du jour — pas une exécution précise à l'heure pile, une simple
# vérification périodique (suffisant pour une tâche quotidienne, évite toute
# dépendance à un scheduler externe type cron/APScheduler).
BACKUP_AUTO_CHECK_INTERVAL_SECONDS = int(os.environ.get("BACKUP_AUTO_CHECK_INTERVAL_SECONDS", str(30 * 60)))

# Authentification à deux facteurs / TOTP (webapp/two_factor_service.py) —
# SEC-03. TWO_FACTOR_SECRET_KEY chiffre le secret TOTP stocké en base (jamais
# en clair) : clé Fernet (cryptography.fernet), à générer une fois avec
#   python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
# et à ne jamais faire tourner sans sauvegarder les secrets déjà chiffrés (une
# clé perdue = tous les comptes 2FA existants irrécupérables). Absente : la
# 2FA reste indisponible (même philosophie que STRIPE_SECRET_KEY/SENTRY_DSN —
# jamais d'erreur au démarrage, le reste du site fonctionne normalement).
TWO_FACTOR_SECRET_KEY = os.environ.get("TWO_FACTOR_SECRET_KEY") or None

# Nom affiché par l'application d'authentification (Google/Microsoft
# Authenticator, Authy, 1Password, Bitwarden...) à côté du compte NovaMath.
TWO_FACTOR_ISSUER = os.environ.get("TWO_FACTOR_ISSUER", "NovaMath")

# En-têtes de sécurité HTTP (webapp/security_headers_service.py) — SEC-06.
# Coupure d'urgence globale (CSP/HSTS/X-Frame-Options/etc.) : reste True dans
# tous les environnements sauf configuration explicite contraire ; le
# Cache-Control "jamais de cache" (comportement historique du projet) n'est
# pas concerné par ce flag et reste toujours appliqué.
ENABLE_SECURITY_HEADERS = _env_flag("ENABLE_SECURITY_HEADERS", True)
# Bascule la CSP en mode observation (Content-Security-Policy-Report-Only) :
# journalise les violations côté navigateur sans jamais rien bloquer — utile
# pour valider une nouvelle règle avant de l'appliquer réellement.
CSP_REPORT_ONLY = _env_flag("CSP_REPORT_ONLY", False)
# HSTS (Strict-Transport-Security) : n'est JAMAIS envoyée hors production ni
# hors HTTPS, quelle que soit cette valeur (voir security_headers_service.py,
# build_hsts()) — activée par défaut en production, désactivable en cas de
# déploiement HTTPS non encore stabilisé (préférer résoudre le certificat
# plutôt que désactiver ce flag durablement).
ENABLE_HSTS = _env_flag("ENABLE_HSTS", IS_PRODUCTION)
# Durée en secondes (défaut 31536000 = 1 an, valeur recommandée par
# hstspreload.org — en-deçà, la directive `preload` n'est pas ajoutée).
HSTS_MAX_AGE = int(os.environ.get("HSTS_MAX_AGE", "31536000"))
# Sources CSP additionnelles (connect-src/img-src/font-src), séparées par des
# espaces — vide par défaut (aucun domaine externe requis aujourd'hui en
# dehors du CDN KaTeX déjà autorisé en dur dans security_headers_service.py).
# Permet d'ouvrir la CSP à un futur besoin (ex : Sentry browser SDK, avatar
# hébergé ailleurs) sans modifier de code.
CSP_ALLOWED_CONNECT = os.environ.get("CSP_ALLOWED_CONNECT", "")
CSP_ALLOWED_IMAGES = os.environ.get("CSP_ALLOWED_IMAGES", "")
CSP_ALLOWED_FONTS = os.environ.get("CSP_ALLOWED_FONTS", "")

# Base de données (webapp/database_service.py) — ARCH-02. Absente : SQLite
# (fichier local, data/novamath.db) — comportement historique inchangé,
# aucune installation supplémentaire requise en développement. Positionnée
# avec un schéma postgres(ql):// : PostgreSQL, détecté automatiquement (voir
# database_service.detect_engine()) — jamais besoin de changer de code, ni
# ici ni dans aucun service métier (plan_service, quota_service,
# billing_service, role_service, ...), qui continuent d'appeler db.py
# exactement comme avant.
DATABASE_URL = os.environ.get("DATABASE_URL") or None

# Pool de connexions PostgreSQL (psycopg_pool.ConnectionPool) — sans effet
# tant que DATABASE_URL ne pointe pas vers PostgreSQL. Noms alignés sur la
# convention SQLAlchemy (pool_size/max_overflow/pool_timeout/pool_recycle),
# largement reconnue, pour rester sans ambiguïté.
# Nombre de connexions maintenues ouvertes en permanence dans le pool.
DATABASE_POOL_SIZE = int(os.environ.get("DATABASE_POOL_SIZE", "5"))
# Connexions supplémentaires autorisées au-delà de DATABASE_POOL_SIZE en cas
# de pic (taille max du pool = DATABASE_POOL_SIZE + DATABASE_MAX_OVERFLOW).
DATABASE_MAX_OVERFLOW = int(os.environ.get("DATABASE_MAX_OVERFLOW", "10"))
# Secondes maximum d'attente pour obtenir une connexion du pool avant de
# lever database_service.DatabaseConnectionError (pool épuisé).
DATABASE_POOL_TIMEOUT = int(os.environ.get("DATABASE_POOL_TIMEOUT", "30"))
# Durée de vie maximale (secondes) d'une connexion avant recyclage — évite
# d'accumuler des connexions obsolètes (coupées par un pare-feu/proxy, ou
# par le serveur PostgreSQL lui-même après une inactivité prolongée).
DATABASE_POOL_RECYCLE = int(os.environ.get("DATABASE_POOL_RECYCLE", "3600"))

# Stripe (webapp/stripe_service.py) — SEC-08/E2E. stripe_service.py continue
# de lire ces mêmes variables directement depuis l'environnement (pattern
# historique préservé tel quel, voir sa docstring, jamais modifié par ce
# chantier) : les constantes ci-dessous sont un miroir en lecture seule,
# utilisé UNIQUEMENT par l'infrastructure de tests E2E
# (webapp/tests/stripe_e2e_helpers.py), qui — comme le reste du code récent
# du projet — passe par config.py plutôt que de relire os.environ.
STRIPE_SECRET_KEY = os.environ.get("STRIPE_SECRET_KEY") or None
STRIPE_PUBLIC_KEY = os.environ.get("STRIPE_PUBLIC_KEY") or None
STRIPE_PRICE_PREMIUM = os.environ.get("STRIPE_PRICE_PREMIUM") or None
STRIPE_PRICE_ULTRA = os.environ.get("STRIPE_PRICE_ULTRA") or None
STRIPE_WEBHOOK_SECRET = os.environ.get("STRIPE_WEBHOOK_SECRET") or None

# Délai (secondes) au-delà duquel une réservation de webhook Stripe
# (stripe_webhook_events, voir db.py::mark_stripe_event_processed) sans
# completed_at est considérée abandonnée — cas d'un process tué (SIGKILL,
# restart Fly.io) en plein traitement, qui n'a jamais pu marquer l'event
# complété ni libérer sa réservation. Défaut 300s : largement au-dessus de la
# durée réelle d'un handler (un ou deux appels Stripe API + quelques écritures
# SQLite, jamais plus de quelques secondes en pratique), pour ne jamais
# ré-exécuter un handler encore réellement en cours sur un worker lent.
STRIPE_WEBHOOK_CLAIM_TIMEOUT_SECONDS = int(os.environ.get("STRIPE_WEBHOOK_CLAIM_TIMEOUT_SECONDS", "300"))

# Envoi d'email (webapp/email_service.py) — SEC-04. Absent : aucun email n'est
# réellement envoyé, le lien concerné (consentement parental) est renvoyé en
# clair dans la réponse JSON, comme dev_reset_link dans auth.py::forgot_
# password — jamais une erreur, même philosophie que STRIPE_SECRET_KEY/
# TWO_FACTOR_SECRET_KEY. À configurer pour que NovaMath soit réellement
# exploitable commercialement (consentement parental RGPD).
EMAIL_SMTP_HOST = os.environ.get("EMAIL_SMTP_HOST") or None
EMAIL_SMTP_PORT = int(os.environ.get("EMAIL_SMTP_PORT", "587"))
EMAIL_SMTP_USERNAME = os.environ.get("EMAIL_SMTP_USERNAME") or None
EMAIL_SMTP_PASSWORD = os.environ.get("EMAIL_SMTP_PASSWORD") or None
EMAIL_SMTP_USE_TLS = _env_flag("EMAIL_SMTP_USE_TLS", True)
EMAIL_FROM_ADDRESS = os.environ.get("EMAIL_FROM_ADDRESS") or None
EMAIL_FROM_NAME = os.environ.get("EMAIL_FROM_NAME", "NovaMath")

# URL absolue de base utilisée UNIQUEMENT pour construire des liens cliquables
# dans les emails (webapp/email_service.py) — un email ne peut pas utiliser de
# chemin relatif comme le fait dev_reset_link. Défaut adapté au développement
# local ; DOIT être positionnée avec le vrai domaine en production, sans quoi
# les liens envoyés aux parents pointeraient vers localhost.
APP_BASE_URL = os.environ.get("APP_BASE_URL", "http://localhost:5000").rstrip("/")

# Consentement parental RGPD (webapp/consent_service.py) — SEC-04. Durée de
# validité du lien envoyé au parent avant qu'il faille en redemander un
# nouveau (voir consent_service.resend_consent_email).
PARENTAL_CONSENT_TOKEN_TTL_DAYS = int(os.environ.get("PARENTAL_CONSENT_TOKEN_TTL_DAYS", "30"))

# Taille maximale (octets) d'une requête HTTP entrante, tous corps confondus
# (JSON, multipart) — Flask/Werkzeug rejette le corps en 413 avant même de le
# lire intégralement en mémoire, dès que Content-Length dépasse cette valeur
# (ou pendant la lecture d'un corps chunké sans Content-Length). 20 Mo couvre
# la plus grosse limite métier existante (PDF chatbot, 15 Mo — voir
# server.py::api_chatbot_attachment_pdf) avec une marge pour l'overhead
# multipart, sans jamais élargir aucune limite métier déjà en place (support :
# 5 Mo par pièce jointe, voir support_attachment_service.MAX_SIZE_BYTES).
MAX_CONTENT_LENGTH = int(os.environ.get("MAX_CONTENT_LENGTH", str(20 * 1024 * 1024)))
