"""
Service pour le module "Paramètres" (/admin/settings) — centre de
configuration de NovaMath : IA/Clés API/SMTP/Stripe/Sauvegardes/Sécurité/Logs
(lecture agrégée de services déjà existants, jamais recodés — seuls les 3
réglages IA sont réellement écrits ici, voir AI_SETTINGS_KEYS).

Nettoyage (chantier simplification admin) : les réglages site_name,
site_description, logo_url, favicon_url, public_url, timezone,
maintenance_enabled, maintenance_message, registrations_enabled,
email_verification_required, manual_account_validation, min_age,
inactive_account_deletion_days, primary_color ont été supprimés — audit +
re-grep confirmés : jamais lus/appliqués ailleurs que dans ce module
lui-même (uniquement `enforced:False` avec explication, jamais un vrai point
d'application). Les sections "Comptes" et "Apparence" disparaissent avec eux
(tous leurs champs en faisaient partie).

Audit round 2 : la section "Général" (réglage `language`) a été supprimée à
son tour — `enforced:True` était trompeur : aucun code ne lit jamais cette
clé de `system_settings` (grep exhaustif). Le réglage de langue réellement
utilisé par le chatbot est un réglage PAR UTILISATEUR distinct (voir
`auth.DEFAULT_USER_SETTINGS`/`chatbot/context_builder.py`), sans aucun lien
avec celui-ci. Si un jour un réglage de langue global doit exister, il faudra
le recréer avec un vrai point d'application. Si l'un des réglages
Comptes/Apparence doit un jour être réellement implémenté (mode maintenance,
validation manuelle de compte, etc.), il faudra recréer le réglage à ce
moment-là, avec son point d'application réel.

Architecture stricte, identique au reste du projet :

    server.py  →  settings_service.py  →  {db, backup_service, email_service,
                   health_service, admin_ai_service, ai_provider_key_service,
                   ai_provider_service, admin_ai_log_service, rate_limit_service,
                   role_service}.py

jamais l'inverse. Ce module NE modifie JAMAIS le routage des fournisseurs IA
(provider_manager.py), NE modifie JAMAIS Stripe/les quotas/le système
d'abonnements — il ne fait qu'agréger en lecture ce qui existe déjà, et ne
persiste QUE des réglages qui n'ont structurellement aucune autre source de
vérité aujourd'hui (voir docstring de system_settings dans db.py).

── Politique "aucune donnée inventée" ──────────────────────────────────────
Identique à system_health_service.py : {"available": False, "value": None,
"reason": "..."} pour tout ce qui ne peut pas être calculé/n'existe pas.

── Politique de persistance vs application réelle (IMPORTANT) ─────────────
Les réglages des sections Général/Comptes/Apparence sont RÉELLEMENT persistés
dans system_settings (aucune valeur fabriquée à la lecture) et RÉELLEMENT
appliqués quand un comportement existant les consomme déjà (ex: aucun cas
aujourd'hui). Pour les réglages qui n'ont PAS encore de point d'application
dans le code (ex: "autoriser les inscriptions" n'est pas encore branché sur
la route d'inscription de auth.py — le brancher est un chantier à part,
risqué à faire sans tests dédiés du parcours d'inscription), le champ
`enforced` de chaque réglage l'indique explicitement : la valeur EST bien
enregistrée, mais n'influence PAS ENCORE le comportement réel. Jamais caché,
toujours affiché tel quel côté frontend (voir admin-settings.js).

── Historique ───────────────────────────────────────────────────────────────
Toute écriture passe par _record_change() → admin_ai_log_service.record()
(table ai_admin_log, déjà générique — voir sa docstring : réutilisée telle
quelle par Abonnements, maintenant par Paramètres, jamais une seconde table
créée pour la même chose)."""
import re
from datetime import datetime, timezone

import admin_ai_log_service
import auth
import admin_ai_service
import ai_provider_service as ai_svc
import backup_service
import config
import db
import email_service
import health_service
import role_service
import system_health_service


def _na(reason):
    return {"available": False, "value": None, "reason": reason}


def _ok(value):
    return {"available": True, "value": value}


def _now_iso():
    return datetime.now(timezone.utc).isoformat()


# ── Réglages persistés (Général/Comptes/Apparence) ──────────────────────────
# `enforced` : False = valeur enregistrée mais n'influence pas encore un
# comportement réel (voir docstring du module) — jamais masqué au frontend.
SETTINGS_SCHEMA = {
    # ── Réglages IA réellement lus par le pipeline chatbot ────────────────
    # (voir chatbot/services/llm_fallback_service.py::_ai_default_temperature/
    # _ai_default_max_tokens/_ai_fallback_enabled) — enforced=True car
    # consommés à chaque appel LLM, pas seulement affichés.
    "ai_temperature_default": {"type": "float", "default": 0.6, "min": 0.0, "max": 1.0, "enforced": True,
                                 "enforced_reason": None},
    # Chantier 9 (2026-08-25) : ce "default" affiché à l'admin (valeur montrée
    # quand aucune ligne n'existe encore en base, voir _serialize_setting)
    # était resté à 1024 alors que llm_fallback_service._DEFAULT_MAX_TOKENS
    # (réellement utilisé par le pipeline chatbot tant qu'aucune valeur n'est
    # configurée) était déjà passé à 1536 par le Chantier 6 puis à 2500 par ce
    # chantier — l'admin voyait donc une valeur trompeuse, différente du
    # comportement réel. Resynchronisé à 2500, sans aucun changement de
    # comportement (ce champ n'est jamais écrit en base tout seul, voir
    # docstring du module — uniquement affiché et utilisé comme repli si
    # `raw_value is None` dans _cast, jamais atteint par le pipeline réel qui
    # lit sa propre constante).
    "ai_max_response_tokens_default": {"type": "int", "default": 2500, "min": 128, "max": 4096, "enforced": True,
                                         "enforced_reason": None},
    "ai_fallback_enabled": {"type": "bool", "default": True, "enforced": True, "enforced_reason": None},
}

AI_SETTINGS_KEYS = ("ai_temperature_default", "ai_max_response_tokens_default", "ai_fallback_enabled")


def _default_for(key):
    return SETTINGS_SCHEMA[key]["default"]


def _cast(key, raw_value):
    spec = SETTINGS_SCHEMA[key]
    if raw_value is None:
        return _default_for(key)
    if spec["type"] == "bool":
        return raw_value == "1"
    if spec["type"] == "int":
        return int(raw_value)
    if spec["type"] == "float":
        return float(raw_value)
    return raw_value


def _serialize_setting(key):
    spec = SETTINGS_SCHEMA[key]
    row = db.get_system_setting(key)
    value = _cast(key, row["value"] if row else None)
    result = {
        "key": key,
        "type": spec["type"],
        "value": value,
        "source": "database" if row else "default",
        "updated_at": row["updated_at"] if row else None,
        "enforced": spec["enforced"],
        "enforced_reason": spec["enforced_reason"],
    }
    if spec["type"] in ("int", "float"):
        result["min"], result["max"] = spec["min"], spec["max"]
    if spec["type"] == "enum":
        result["choices"] = spec["choices"]
    if spec["type"] == "str":
        result["max_len"] = spec.get("max_len", 500)
    return result


def _validate(key, value):
    spec = SETTINGS_SCHEMA[key]
    if spec["type"] == "bool":
        if not isinstance(value, bool):
            return None, "Valeur booléenne attendue."
        return ("1" if value else "0"), None
    if spec["type"] == "int":
        try:
            n = int(value)
        except (TypeError, ValueError):
            return None, "Nombre entier attendu."
        if n < spec["min"] or n > spec["max"]:
            return None, f"Doit être compris entre {spec['min']} et {spec['max']}."
        return str(n), None
    if spec["type"] == "float":
        try:
            n = float(value)
        except (TypeError, ValueError):
            return None, "Nombre décimal attendu."
        if n < spec["min"] or n > spec["max"]:
            return None, f"Doit être compris entre {spec['min']} et {spec['max']}."
        return str(n), None
    if spec["type"] == "enum":
        if value not in spec["choices"]:
            return None, f"Valeur invalide, attendu l'une de : {', '.join(spec['choices'])}."
        return value, None
    if spec["type"] == "color":
        if not isinstance(value, str) or not re.fullmatch(r"#[0-9A-Fa-f]{6}", value):
            return None, "Couleur hexadécimale attendue (ex: #7c5cff)."
        return value, None
    # str / enum-libre
    if not isinstance(value, str):
        return None, "Chaîne de caractères attendue."
    if len(value) > spec.get("max_len", 500):
        return None, f"Longueur maximale dépassée ({spec['max_len']} caractères)."
    return value, None


def _record_change(actor, key, old_value, new_value):
    admin_ai_log_service.record(
        actor, action="update_setting", provider_id=None, provider_name=key,
        old_values={key: old_value}, new_values={key: new_value}, result="success",
    )


def _update_keys(actor, data, allowed_keys):
    """Valide puis persiste chaque clé PRÉSENTE dans `data` parmi
    `allowed_keys` — jamais une clé hors périmètre de la section appelante.
    Renvoie (ok, errors) ; `errors` est un dict {key: message}, jamais une
    exception pour une valeur invalide (Partie 13 : rejeter, pas planter)."""
    errors = {}
    to_apply = {}
    for key in data:
        if key not in allowed_keys:
            continue
        raw, error = _validate(key, data[key])
        if error:
            errors[key] = error
            continue
        to_apply[key] = raw
    if errors:
        return False, errors
    admin_id = actor.get("id") if actor else None
    for key, raw in to_apply.items():
        previous = _serialize_setting(key)
        db.set_system_setting(key, raw, updated_by_admin_id=admin_id)
        _record_change(actor, key, previous["value"], _cast(key, raw))
    return True, {}


# ── IA (lecture seule — jamais de modification du routage) ──────────────────
def ai_settings():
    """Sous-ensemble RÉELLEMENT éditable de la section IA (voir AI_SETTINGS_KEYS)
    — même forme que general(), consommé tel quel par le frontend après une
    sauvegarde réussie (PATCH /api/admin/settings/ai), jamais mélangé aux
    informations en lecture seule de ai_config() qui ne sont pas des
    `setting` valides pour settingField() côté JS."""
    return {key: _serialize_setting(key) for key in AI_SETTINGS_KEYS}


def ai_config():
    """Partie 3, réduite au strict nécessaire (chantier de simplification) :
    uniquement les réglages RÉELLEMENT éditables (température/max tokens/
    fallback — persistés dans system_settings ET lus à chaque appel LLM, voir
    chatbot/services/llm_fallback_service.py) et le fournisseur/modèle
    principal réellement utilisé (ai_providers, priorité la plus basse).
    `retry`/`cache` (constantes techniques jamais consultées par un admin au
    quotidien, jamais affichées ailleurs que dans du texte explicatif) et
    `default_provider` (jamais consommé par le frontend, doublon strict du
    premier élément de `provider_order`) ont été supprimés — voir docstring
    du module pour la politique de suppression du bruit."""
    providers = ai_svc.list_providers()
    order = [
        {
            "id": p["id"], "name": p["name"], "provider_key": p["provider_key"],
            "model_name": p["model_name"], "priority": p["priority"], "enabled": bool(p["enabled"]),
        }
        for p in sorted(providers, key=lambda p: p["priority"])
    ]
    settings = ai_settings()
    return {
        "provider_order": _ok(order) if order else _na("Aucun fournisseur IA n'est configuré."),
        "temperature_default": settings["ai_temperature_default"],
        "max_response_tokens_default": settings["ai_max_response_tokens_default"],
        "fallback_enabled": settings["ai_fallback_enabled"],
    }


def update_ai_settings(actor, data):
    return _update_keys(actor, data, AI_SETTINGS_KEYS)


def api_keys():
    """Partie 4 : réutilise intégralement admin_ai_service.list_api_keys()
    (déjà masqué, déjà utilisé par /admin/ia et la page Santé du système) —
    jamais recodé ici. Les actions (créer/modifier/supprimer/activer/
    désactiver/tester) réutilisent les routes /api/admin/ai/keys/* déjà
    existantes, jamais dupliquées côté serveur.

    Enrichit chaque clé de `model_name` : une clé API est liée à un
    `provider_key` (famille "gemini"/"anthropic", pas à un fournisseur précis
    — voir ai_provider_key_service.create_key), donc le modèle affiché est
    celui du fournisseur RÉELLEMENT actif pour cette famille (activé, priorité
    la plus basse — les mêmes règles que provider_manager.select_llm_for_user),
    sinon celui du premier fournisseur configuré pour cette famille."""
    providers_by_key = {}
    for p in sorted(ai_svc.list_providers(), key=lambda p: p["priority"]):
        providers_by_key.setdefault(p["provider_key"], []).append(p)
    keys = admin_ai_service.list_api_keys()
    for key in keys:
        candidates = providers_by_key.get(key["provider_key"], [])
        active = next((p for p in candidates if p["enabled"]), candidates[0] if candidates else None)
        key["model_name"] = active["model_name"] if active else None
    return keys


# ── SMTP ──────────────────────────────────────────────────────────────────────
def smtp_info():
    last_test_at = db.get_system_setting("smtp_last_test_at")
    last_test_ok = db.get_system_setting("smtp_last_test_ok")
    last_test_error = db.get_system_setting("smtp_last_test_error")
    return {
        "configured": email_service.is_configured(),
        "host": _ok(config.EMAIL_SMTP_HOST) if config.EMAIL_SMTP_HOST else _na(
            "EMAIL_SMTP_HOST n'est pas définie — piloté par variable d'environnement, non modifiable depuis "
            "cette interface."
        ),
        "port": _ok(config.EMAIL_SMTP_PORT),
        "username": _ok(config.EMAIL_SMTP_USERNAME) if config.EMAIL_SMTP_USERNAME else _na(
            "EMAIL_SMTP_USERNAME n'est pas définie."
        ),
        "encryption": _ok("STARTTLS" if config.EMAIL_SMTP_USE_TLS else "Aucun (non chiffré)"),
        "from_address": _ok(f"{config.EMAIL_FROM_NAME} <{config.EMAIL_FROM_ADDRESS}>") if config.EMAIL_FROM_ADDRESS else _na(
            "EMAIL_FROM_ADDRESS n'est pas définie."
        ),
        "env_controlled": True,
        "env_controlled_reason": "Ces valeurs sont pilotées par les variables d'environnement EMAIL_SMTP_*/"
                                   "EMAIL_FROM_* (voir config.py) — non modifiables depuis cette interface, pour "
                                   "ne jamais casser la rétrocompatibilité avec le déploiement actuel.",
        "last_test_at": _ok(last_test_at["value"]) if last_test_at else _na("Aucun test d'envoi n'a encore été effectué."),
        "last_test_ok": _ok(last_test_ok["value"] == "1") if last_test_ok else _na("Aucun test d'envoi n'a encore été effectué."),
        "last_test_error": _ok(last_test_error["value"]) if last_test_error else _na("Aucune erreur enregistrée."),
    }


def test_smtp(actor, to_address):
    """Envoie un VRAI email de test (voir email_service.send_email) — n'écrit
    RIEN dans ai_providers/Stripe/quotas, uniquement le résultat dans
    system_settings (pour l'affichage "dernier succès"/"dernière erreur")."""
    admin_id = actor.get("id") if actor else None
    if not email_service.is_configured():
        db.set_system_setting("smtp_last_test_at", _now_iso(), updated_by_admin_id=admin_id)
        db.set_system_setting("smtp_last_test_ok", "0", updated_by_admin_id=admin_id)
        db.set_system_setting("smtp_last_test_error", "SMTP non configuré (EMAIL_SMTP_HOST absente).", updated_by_admin_id=admin_id)
        admin_ai_log_service.record(actor, action="test_smtp", provider_name="smtp", result="error",
                                      error_message="SMTP non configuré.")
        return False, "SMTP non configuré (EMAIL_SMTP_HOST absente)."
    subject = "NovaMath — Email de test (Paramètres)"
    html = "<p>Ceci est un email de test envoyé depuis le panneau d'administration NovaMath (Paramètres > Email).</p>"
    text = "Ceci est un email de test envoyé depuis le panneau d'administration NovaMath (Paramètres > Email)."
    try:
        sent = email_service.send_email(to_address, subject, html, text, required=True)
    except email_service.EmailNotConfigured as exc:
        sent, error = False, str(exc)
    except Exception as exc:  # noqa: BLE001 - un test d'envoi ne doit jamais faire planter la route
        sent, error = False, str(exc)
    else:
        error = None if sent else "Échec de l'envoi (voir les logs serveur pour le détail SMTP)."
    db.set_system_setting("smtp_last_test_at", _now_iso(), updated_by_admin_id=admin_id)
    db.set_system_setting("smtp_last_test_ok", "1" if sent else "0", updated_by_admin_id=admin_id)
    db.set_system_setting("smtp_last_test_error", error or "", updated_by_admin_id=admin_id)
    admin_ai_log_service.record(actor, action="test_smtp", provider_name="smtp",
                                  result="success" if sent else "error", error_message=error)
    return sent, error


# ── Stripe (lecture seule — jamais de modification) ──────────────────────────
def stripe_info():
    secret = config.STRIPE_SECRET_KEY or ""
    if not health_service.check_stripe_configured():
        mode = _na("Stripe n'est pas configuré (STRIPE_SECRET_KEY absente ou placeholder).")
    elif secret.startswith("sk_live_"):
        mode = _ok("production")
    elif secret.startswith("sk_test_"):
        mode = _ok("test")
    else:
        mode = _na("Clé présente mais préfixe non reconnu (ni sk_test_ ni sk_live_).")
    webhook_configured = bool(config.STRIPE_WEBHOOK_SECRET)
    return {
        "mode": mode,
        "webhook_configured": webhook_configured,
        "env_controlled_reason": "Mode et webhook sont dérivés de STRIPE_SECRET_KEY/STRIPE_WEBHOOK_SECRET "
                                   "(variables d'environnement) — jamais affichés en clair, non modifiables "
                                   "depuis cette interface. Le détail des événements reçus est consultable dans "
                                   "le Journal admin.",
    }


# ── Sauvegardes ───────────────────────────────────────────────────────────────
def backups_info():
    backups = backup_service.list_backups()
    last_error_at_row = db.get_system_setting("backup_last_error_at")
    last_error_row = db.get_system_setting("backup_last_error")
    last_error_at = last_error_at_row["value"] if last_error_at_row else None
    # Une dernière sauvegarde est considérée réussie si elle est plus récente
    # que le dernier échec enregistré (ou si aucun échec n'a jamais eu lieu) —
    # comparaison de deux timestamps ISO 8601 réels, jamais une valeur devinée.
    last_backup_successful = bool(backups) and (last_error_at is None or backups[0]["created_at"] > last_error_at)
    storage = system_health_service.storage_info()
    return {
        "items": backups,
        "total_size_bytes": sum(b["size_bytes"] for b in backups),
        "last_backup": _ok(backups[0]) if backups else _na("Aucune sauvegarde n'existe."),
        "last_backup_successful": _ok(last_backup_successful) if backups else _na("Aucune sauvegarde n'existe."),
        "last_error_at": _ok(last_error_at) if last_error_at else _na("Aucun échec enregistré."),
        "last_error": _ok(last_error_row["value"]) if last_error_row else _na("Aucun échec enregistré."),
        "disk_used_bytes": storage["disk_used_bytes"],
        # `disk_total_bytes` a été volontairement retiré de storage_info() (voir
        # sa docstring) : jamais recalculé ici pour ne pas contourner ce choix,
        # simplement représenté comme indisponible via le contrat {available,
        # value, reason} déjà géré par admin-settings.js (EMPTY_LABEL).
        "disk_total_bytes": _na("Cette donnée n'est plus calculée par system_health_service.storage_info() "
                                 "(retirée comme non actionnable lors du nettoyage de la page Santé)."),
    }


def create_backup(actor):
    try:
        path = backup_service.backup_database()
    except Exception as exc:  # noqa: BLE001 - une sauvegarde échouée ne doit jamais faire 500 silencieusement
        admin_id = actor.get("id") if actor else None
        db.set_system_setting("backup_last_error_at", _now_iso(), updated_by_admin_id=admin_id)
        db.set_system_setting("backup_last_error", str(exc), updated_by_admin_id=admin_id)
        admin_ai_log_service.record(actor, action="create_backup", result="error", error_message=str(exc))
        return None, str(exc)
    admin_ai_log_service.record(actor, action="create_backup", new_values={"filename": path.name}, result="success")
    return path.name, None


def restore_backup(actor, filename):
    try:
        backup_service.restore_backup(filename)
    except (backup_service.BackupNotFound, backup_service.BackupCorrupted) as exc:
        admin_ai_log_service.record(actor, action="restore_backup", old_values={"filename": filename},
                                      result="error", error_message=str(exc))
        return False, str(exc)
    admin_ai_log_service.record(actor, action="restore_backup", old_values={"filename": filename}, result="success")
    return True, None


def delete_backup(actor, filename):
    """Renvoie (ok, error, not_found) — `not_found` distingue "aucune
    sauvegarde de ce nom" (404 côté route) d'un échec de suppression réel
    (fichier verrouillé par l'OS, permissions...), qui doit remonter comme
    une vraie erreur, jamais un faux 404 trompeur."""
    try:
        backup_service.delete_backup(filename)
    except backup_service.BackupNotFound as exc:
        return False, str(exc), True
    except OSError as exc:
        admin_ai_log_service.record(actor, action="delete_backup", old_values={"filename": filename},
                                      result="error", error_message=str(exc))
        return False, f"Suppression impossible : {exc}", False
    admin_ai_log_service.record(actor, action="delete_backup", old_values={"filename": filename}, result="success")
    return True, None, False


# ── Sécurité (lecture seule) ──────────────────────────────────────────────────
def security_info():
    team_roles = [r.value for r in role_service.Role if r != role_service.Role.USER]
    two_fa = db.count_admins_with_two_factor(team_roles)
    return {
        "two_factor_admins": _ok(two_fa),
        "csp": _ok({
            "enabled": config.ENABLE_SECURITY_HEADERS,
            "report_only": config.CSP_REPORT_ONLY,
        }),
        "session_durations": _ok({
            "default_days": auth.DEFAULT_DAYS, "remember_me_days": auth.REMEMBER_DAYS,
            "guest_days": auth.GUEST_SESSION_DAYS,
        }),
        "login_attempts": _ok({"max_attempts": auth.MAX_LOGIN_ATTEMPTS, "lockout_minutes": auth.LOCKOUT_MINUTES}),
        "hsts_enabled": _ok(config.ENABLE_HSTS),
    }


# ── Journalisation (lecture seule) ────────────────────────────────────────────
def logs_info():
    return {
        "level": _ok(config.LOG_LEVEL),
        "level_env_controlled_reason": "Piloté par la variable d'environnement LOG_LEVEL — non modifiable "
                                          "depuis cette interface. Logs envoyés uniquement vers stdout/stderr "
                                          "(voir logging_service.py) : aucune rotation/rétention/taille "
                                          "maximale à gérer côté NovaMath (délégué à la plateforme d'hébergement, "
                                          "12-factor).",
        "sentry_enabled": _ok(bool(config.SENTRY_DSN)),
    }


def full_snapshot():
    return {
        "ai": ai_config(),
        "api_keys": api_keys(),
        "smtp": smtp_info(),
        "stripe": stripe_info(),
        "backups": backups_info(),
        "security": security_info(),
        "logs": logs_info(),
    }
