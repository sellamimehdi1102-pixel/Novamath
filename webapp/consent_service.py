"""
Consentement (âge, protection des mineurs, cookies, versions de politique)
pour NovaMath — SEC-04, conformité RGPD/CNIL.

Architecture stricte, identique à role_service.py/two_factor_service.py :

    auth.py / server.py  →  consent_service.py  →  db.py / email_service.py

jamais l'inverse. Ce module reçoit un `user` déjà chargé (dict tel que renvoyé
par db.get_user_by_id, même convention que role_service.py) et contient TOUTE
la logique métier de consentement : calcul d'âge, seuil légal français,
cycle de vie du consentement parental (création du lien, envoi de l'email,
acceptation/refus, renvoi), consentement cookies, versionnement des CGU/
politique de confidentialité. auth.py/server.py ne font que traduire HTTP <->
appels à ce module.

Seuil légal français (art. 45 Loi Informatique et Libertés modifiée par la loi
n°2018-493, transposant l'art. 8 RGPD) : en-dessous de 15 ans, le traitement
des données d'un mineur nécessite le consentement conjoint du mineur et du
titulaire de l'autorité parentale. Tant que ce consentement n'est pas obtenu,
`account_status` reste 'pending_parental_consent' — AUCUNE session n'est créée
pour ce compte (voir auth.py::_finish_login), ce qui bloque nativement tout
accès (chatbot, Premium, exercices, données personnelles) sans dupliquer une
vérification dans chaque route existante.
"""
import logging
from datetime import date, datetime, timezone
from functools import wraps

from flask import jsonify, request

import config
import db
import email_service

logger = logging.getLogger("consent_service")

MINOR_CONSENT_AGE_THRESHOLD = 15

# Versions courantes des documents légaux — à incrémenter manuellement (même
# principe que quota_service.QUOTA_MATRIX : une constante de code, pas une
# variable d'environnement) à chaque publication d'un nouveau texte. Toute
# incrémentation déclenche needs_policy_reacceptance() pour tous les comptes
# existants dont *_accepted_version ne correspond plus.
TERMS_VERSION = "2026-01-01"
PRIVACY_VERSION = "2026-01-01"


class InvalidConsentToken(Exception):
    """Jeton de consentement parental inconnu — jamais traduite en 500,
    toujours en réponse HTTP explicite (404) par server.py, même famille que
    two_factor_service.InvalidChallenge."""


class ConsentAlreadyResolved(Exception):
    """Le lien a déjà été utilisé (accepté ou refusé) — un lien de
    consentement parental n'est, comme un token de réinitialisation de mot de
    passe, jamais réutilisable une fois résolu."""


class ConsentExpired(Exception):
    """Le lien a dépassé sa durée de validité (config.PARENTAL_CONSENT_TOKEN_TTL_DAYS)."""


class NoPendingConsentRequest(Exception):
    """Levée par resend_consent_email si aucune demande n'existe encore pour
    ce compte (rien à renvoyer)."""


# ── Âge et seuil légal ──────────────────────────────────────────────────────
def compute_age(birth_date_str, on_date=None):
    """Âge en années révolues à `on_date` (aujourd'hui par défaut), calculé à
    partir d'une date de naissance ISO (`YYYY-MM-DD`) — comparaison exacte
    mois/jour (gère les années bissextiles) : ne jamais approximer via une
    simple division du nombre de jours."""
    on_date = on_date or date.today()
    year, month, day = (int(part) for part in birth_date_str.split("-"))
    born = date(year, month, day)
    return on_date.year - born.year - ((on_date.month, on_date.day) < (born.month, born.day))


def requires_parental_consent(birth_date_str, on_date=None):
    """True si, à `on_date`, la personne née le `birth_date_str` est encore
    sous le seuil légal français de consentement autonome (art. 8 RGPD /
    art. 45 Loi Informatique et Libertés)."""
    return compute_age(birth_date_str, on_date=on_date) < MINOR_CONSENT_AGE_THRESHOLD


# ── Cycle de vie du consentement parental ──────────────────────────────────
def create_consent_request(user, parent_email, ip=None):
    """Crée une demande de consentement parental pour `user` (déjà en base,
    `account_status='pending_parental_consent'`), envoie l'email au parent et
    journalise la création. Renvoie (token, configured) — `configured` reflète
    email_service.is_configured() (pas le résultat de l'envoi : un échec SMTP
    transitoire en production ne doit jamais faire fuiter le lien de
    consentement en clair dans la réponse JSON, contrairement à l'absence de
    configuration qui est le filet de secours voulu pour le développement,
    voir dev_reset_link dans auth.py::forgot_password)."""
    token = db.create_parental_consent_request(
        user["id"], parent_email, days=config.PARENTAL_CONSENT_TOKEN_TTL_DAYS
    )
    request_row = db.get_parental_consent_request(token)
    consent_url = f"{config.APP_BASE_URL}/parent/consent/{token}"
    subject, html, text = email_service.build_parental_consent_request_email(
        user["pseudo"], consent_url, request_row["expires_at"]
    )
    email_service.send_email(parent_email, subject, html, text)
    db.log_security_event("parental_consent_requested", user["id"], ip)
    logger.info("Consentement parental : demande créée pour l'utilisateur %s.", user["id"])
    return token, email_service.is_configured()


def resend_consent_email(user, ip=None):
    """Invalide toute demande encore en attente et en émet une nouvelle vers
    le même email parent (renvoi demandé par l'utilisateur, ex: email non
    reçu). Lève NoPendingConsentRequest si aucune demande n'existe encore."""
    latest = db.get_latest_parental_consent_request(user["id"])
    if latest is None:
        raise NoPendingConsentRequest("Aucune demande de consentement parental existante pour ce compte.")
    db.supersede_pending_parental_consent_requests(user["id"])
    db.log_security_event("parental_consent_resent", user["id"], ip)
    return create_consent_request(user, latest["parent_email"], ip=ip)


def get_public_consent_info(token):
    """Informations minimales exposées à la page publique `/parent/consent/
    <token>` — jamais l'email du parent ni aucune autre donnée personnelle de
    l'enfant au-delà de son pseudo (déjà public partout ailleurs sur
    NovaMath)."""
    row = db.get_parental_consent_request(token)
    if row is None:
        raise InvalidConsentToken("Ce lien de consentement est invalide.")
    child = db.get_user_by_id(row["user_id"])
    expires_at = datetime.fromisoformat(row["expires_at"])
    now = datetime.now(timezone.utc)
    return {
        "status": row["status"],
        "child_pseudo": child["pseudo"] if child else None,
        "expires_at": row["expires_at"],
        "expired": row["status"] == "pending" and now > expires_at,
    }


def resolve_consent(token, decision, ip=None):
    """Accepte ou refuse une demande de consentement parental (`decision` =
    'accepted'/'refused'). Lève InvalidConsentToken (jeton inconnu),
    ConsentAlreadyResolved (déjà accepté/refusé/renvoyé) ou ConsentExpired
    (délai dépassé). La résolution en base est atomique (voir
    db.resolve_parental_consent_request) : deux résolutions concurrentes du
    même lien ne peuvent jamais toutes les deux réussir."""
    if decision not in ("accepted", "refused"):
        raise ValueError("decision doit être 'accepted' ou 'refused'.")

    row = db.get_parental_consent_request(token)
    if row is None:
        raise InvalidConsentToken("Ce lien de consentement est invalide.")
    if row["status"] != "pending":
        raise ConsentAlreadyResolved("Cette demande de consentement a déjà été traitée.")
    expires_at = datetime.fromisoformat(row["expires_at"])
    if datetime.now(timezone.utc) > expires_at:
        raise ConsentExpired("Ce lien de consentement a expiré.")

    resolved = db.resolve_parental_consent_request(token, decision, ip)
    if not resolved:
        # Course concurrente perdue entre la lecture ci-dessus et l'UPDATE.
        raise ConsentAlreadyResolved("Cette demande de consentement a déjà été traitée.")

    user = db.get_user_by_id(row["user_id"])
    if decision == "accepted":
        db.set_account_status(user["id"], "active")
        db.add_consent_record(user["id"], "parental_consent", "accepted", None, ip)
        db.log_security_event("parental_consent_accepted", user["id"], ip)
        subject, html, text = email_service.build_parental_consent_confirmed_email(user["pseudo"])
    else:
        db.set_account_status(user["id"], "parental_consent_refused")
        db.add_consent_record(user["id"], "parental_consent", "refused", None, ip)
        db.log_security_event("parental_consent_refused", user["id"], ip)
        subject, html, text = email_service.build_parental_consent_refused_email(user["pseudo"])
    email_service.send_email(user["email"], subject, html, text)
    return db.get_user_by_id(user["id"])


def requires_active_account(view):
    """Décorateur de route Flask (défense en profondeur) : renvoie 403 si le
    compte connecté n'est pas `account_status='active'`. La protection
    principale reste en amont (auth.py::_finish_login ne crée aucune session
    pour un compte non actif) — ce décorateur couvre les routes qui, comme
    /api/auth/me, doivent rester joignables (le client a besoin de connaître
    son statut) tout en refusant explicitement toute action de fond. Doit être
    posé APRÈS @login_required, même convention que role_service.requires_role."""
    @wraps(view)
    def wrapped(*args, **kwargs):
        user = getattr(request, "current_user", None)
        status = (user or {}).get("account_status", "active")
        if status != "active":
            return jsonify({
                "error": "Ce compte n'a pas encore accès : consentement parental requis ou refusé.",
                "account_status": status,
            }), 403
        return view(*args, **kwargs)
    return wrapped


# ── Versions des CGU / politique de confidentialité ────────────────────────
def needs_policy_reacceptance(user):
    return (
        user.get("terms_accepted_version") != TERMS_VERSION
        or user.get("privacy_accepted_version") != PRIVACY_VERSION
    )


def record_initial_policy_acceptance(user_id, ip=None):
    """Enregistre l'acceptation des CGU et de la politique de confidentialité
    en vigueur au moment de l'inscription (remplace la simple case à cocher
    booléenne par une preuve RGPD immuable — voir consent_records)."""
    db.set_policy_acceptance(user_id, terms_version=TERMS_VERSION, privacy_version=PRIVACY_VERSION)
    db.add_consent_record(user_id, "terms", "accepted", TERMS_VERSION, ip)
    db.add_consent_record(user_id, "privacy_policy", "accepted", PRIVACY_VERSION, ip)


def record_policy_reacceptance(user_id, ip=None):
    """Enregistre l'acceptation d'une NOUVELLE version des CGU/politique de
    confidentialité (flux de ré-acceptation forcée, voir needs_policy_
    reacceptance) et journalise l'événement."""
    record_initial_policy_acceptance(user_id, ip=ip)
    db.log_security_event("policy_accepted", user_id, ip)


# ── Consentement cookies ────────────────────────────────────────────────────
def get_cookie_consent(user_id):
    row = db.get_cookie_consent(user_id)
    if row is None:
        return {"statistics": False, "marketing": False, "updated_at": None}
    return {
        "statistics": bool(row["statistics"]),
        "marketing": bool(row["marketing"]),
        "updated_at": row["updated_at"],
    }


def set_cookie_consent(user_id, statistics, marketing, ip=None):
    row = db.set_cookie_consent(user_id, statistics, marketing)
    db.add_consent_record(user_id, "cookie_statistics", "accepted" if statistics else "refused", None, ip)
    db.add_consent_record(user_id, "cookie_marketing", "accepted" if marketing else "refused", None, ip)
    db.log_security_event("cookie_consent_updated", user_id, ip)
    return {
        "statistics": bool(row["statistics"]),
        "marketing": bool(row["marketing"]),
        "updated_at": row["updated_at"],
    }
