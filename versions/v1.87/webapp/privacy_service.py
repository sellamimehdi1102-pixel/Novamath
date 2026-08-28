"""
Droits RGPD (export, historique des consentements) pour un compte NovaMath
déjà actif — SEC-04.

Architecture stricte, identique à consent_service.py :

    server.py  →  privacy_service.py  →  db.py / consent_service.py

jamais l'inverse : ce module ne connaît que db.py et consent_service.py (pour
réutiliser get_cookie_consent, seule source de vérité de ses valeurs par
défaut), jamais auth.py (la
suppression de compte et la rectification du profil existaient déjà avant ce
chantier — voir auth.py::_purge_account/DELETE /api/auth/me et
auth.py::update_me/PUT /api/auth/me — et restent la SEULE implémentation de
ces deux droits RGPD, désormais journalisées explicitement avec les
événements `gdpr_delete_account`/`gdpr_rectification` ; ce module ne les
duplique jamais). L'agrégation des données stockées en fichiers JSON par
utilisateur (stats/paramètres/progression Cours, voir auth.read_user_stats et
consorts) est faite par l'appelant HTTP (server.py, qui a déjà accès à
`auth`), pas ici, pour ne jamais faire dépendre ce module de auth.py.
"""
import logging

import consent_service
import db

logger = logging.getLogger("privacy_service")

# Champs de la table `users` jamais exposés dans un export RGPD (secrets
# techniques, pas des "données personnelles" au sens où l'utilisateur pourrait
# vouloir les relire) — même filtre que _public_user() dans auth.py.
_SENSITIVE_USER_FIELDS = {"password_hash", "two_factor_secret", "two_factor_last_counter"}


def export_account_data(user, ip=None):
    """Agrège toutes les données RGPD directement issues de la base (hors
    fichiers JSON par utilisateur, fusionnés par l'appelant) pour le compte
    `user` (dict déjà chargé) : profil, historique de consentement, demandes
    de consentement parental, préférences cookies, journal de sécurité.
    Journalise l'export (jamais son contenu)."""
    user_id = user["id"]
    account = {k: v for k, v in user.items() if k not in _SENSITIVE_USER_FIELDS}
    data = {
        "account": account,
        "consent_history": db.list_consent_records(user_id),
        "parental_consent_requests": [
            {k: v for k, v in row.items() if k != "parent_email"}
            for row in db.list_parental_consent_requests(user_id)
        ],
        "cookie_consent": consent_service.get_cookie_consent(user_id),
        "security_events": db.list_security_events_for_user(user_id),
    }
    db.log_security_event("gdpr_export", user_id, ip)
    logger.info("Export RGPD généré pour l'utilisateur %s.", user_id)
    return data


def get_consent_history(user_id):
    return db.list_consent_records(user_id)
