"""
Haute disponibilité IA : plusieurs clés API par fournisseur (Gemini/Claude),
avec rotation automatique en cas d'échec — voir SCHEMA/ai_provider_api_keys
dans db.py pour le détail des colonnes.

Architecture stricte, identique au reste du projet :

    webapp/chatbot/services/llm_fallback_service.py  →  ai_provider_key_service.py  →  db.py
    webapp/admin_ai_service.py                       →  ai_provider_key_service.py  →  db.py

Une clé n'est JAMAIS stockée ni renvoyée en clair une fois chiffrée : chiffrée
avec Fernet (cryptography.fernet) via TWO_FACTOR_SECRET_KEY — même mécanisme
que two_factor_service._encrypt_secret/_decrypt_secret (réutilise la même clé
serveur plutôt que d'en exiger une seconde à configurer). L'admin ne revoit
jamais la clé en clair après sa création (voir mask_api_key ci-dessous,
utilisée par admin_ai_service pour l'affichage — seuls les 4 derniers
caractères sont montrés).

Si AUCUNE clé n'est configurée en base pour un fournisseur (l'admin n'a
jamais ouvert l'écran multi-clés), available_keys() renvoie [] et
llm_fallback_service.generate() retombe intégralement sur le comportement
historique (une seule tentative, clé lue depuis la variable d'environnement
du provider) — zéro changement de comportement pour qui n'adopte pas cette
fonctionnalité.
"""
import logging
from datetime import datetime, timedelta, timezone

from cryptography.fernet import Fernet, InvalidToken

import config
import db

logger = logging.getLogger("webapp.ai_provider_key_service")


class KeyEncryptionNotConfigured(RuntimeError):
    """TWO_FACTOR_SECRET_KEY absente/invalide — impossible de chiffrer ou
    déchiffrer une clé API IA (même exigence que le secret 2FA)."""


def _fernet():
    key = config.TWO_FACTOR_SECRET_KEY
    if not key:
        raise KeyEncryptionNotConfigured(
            "TWO_FACTOR_SECRET_KEY n'est pas configurée sur ce serveur — nécessaire aussi pour chiffrer "
            "les clés API IA (haute disponibilité)."
        )
    try:
        return Fernet(key.encode() if isinstance(key, str) else key)
    except (ValueError, TypeError) as exc:
        raise KeyEncryptionNotConfigured(f"TWO_FACTOR_SECRET_KEY invalide : {exc}") from exc


def _encrypt(raw_api_key):
    return _fernet().encrypt(raw_api_key.encode()).decode()


def _decrypt(encrypted_api_key):
    try:
        return _fernet().decrypt(encrypted_api_key.encode()).decode()
    except InvalidToken as exc:
        raise KeyEncryptionNotConfigured(
            "Impossible de déchiffrer cette clé API (TWO_FACTOR_SECRET_KEY a changé depuis, ou donnée corrompue)."
        ) from exc


def mask_api_key(raw_or_encrypted_tail):
    """Affichage sûr : ne montre jamais la clé complète, seulement ses 4
    derniers caractères (assez pour qu'un admin la reconnaisse parmi
    plusieurs, jamais assez pour la réutiliser)."""
    tail = raw_or_encrypted_tail[-4:] if raw_or_encrypted_tail else ""
    return f"••••{tail}"


def _now_iso():
    return datetime.now(timezone.utc).isoformat()


def is_in_cooldown(row):
    until = row.get("quota_exceeded_until")
    if not until:
        return False
    try:
        return datetime.fromisoformat(until) > datetime.now(timezone.utc)
    except ValueError:
        return False


# ── CRUD (admin) ─────────────────────────────────────────────────────────────
def create_key(provider_key, label, raw_api_key, priority=0):
    encrypted = _encrypt(raw_api_key)
    key_id = db.create_ai_provider_api_key(provider_key, label, encrypted, priority=priority)
    return db.get_ai_provider_api_key(key_id)


def list_keys(provider_key=None):
    """Pour l'écran d'administration — jamais la clé en clair, voir
    _serialize_key dans admin_ai_service.py pour le masquage à l'affichage."""
    return db.list_ai_provider_api_keys(provider_key)


def get_key(key_id):
    return db.get_ai_provider_api_key(key_id)


def update_key(key_id, *, label=None, enabled=None, priority=None):
    fields = {}
    if label is not None:
        fields["label"] = label
    if enabled is not None:
        fields["enabled"] = enabled
    if priority is not None:
        fields["priority"] = priority
    db.update_ai_provider_api_key(key_id, **fields)
    return db.get_ai_provider_api_key(key_id)


def delete_key(key_id):
    db.delete_ai_provider_api_key(key_id)


def clear_cooldown(key_id):
    db.clear_ai_provider_api_key_cooldown(key_id)


# ── Rotation (chatbot) ───────────────────────────────────────────────────────
def available_keys_for_rotation(provider_key):
    """Clés utilisables MAINTENANT pour `provider_key`, triées par priorité
    (plus petite d'abord) — exclut les clés désactivées et celles encore en
    cooldown (quota_exceeded_until dans le futur). Chaque élément contient la
    clé DÉCHIFFRÉE (`api_key`), prête à instancier un provider — jamais
    renvoyée ailleurs que dans ce processus serveur, jamais journalisée en
    clair. [] si aucune clé n'est configurée pour ce fournisseur (voir
    docstring du module : llm_fallback_service.generate() retombe alors sur
    le comportement historique)."""
    rows = db.list_ai_provider_api_keys(provider_key)
    usable = []
    for row in rows:
        if not row["enabled"]:
            continue
        if is_in_cooldown(row):
            continue
        try:
            decrypted = _decrypt(row["api_key_encrypted"])
        except KeyEncryptionNotConfigured:
            logger.error(
                "Clé API IA id=%s (%s) illisible (chiffrement) — ignorée pour la rotation.",
                row["id"], row["label"],
            )
            continue
        usable.append({**row, "api_key": decrypted})
    return usable


def record_result(key_id, success, response_time_ms=0, error=None, fallback=False, quota_cooldown_seconds=None):
    """Comptabilise une tentative réelle sur cette clé — voir
    db.record_ai_provider_api_key_result pour la sémantique exacte du
    cooldown (jamais effacé par un échec non lié au quota)."""
    quota_exceeded_until = None
    if not success and quota_cooldown_seconds:
        quota_exceeded_until = (datetime.now(timezone.utc) + timedelta(seconds=quota_cooldown_seconds)).isoformat()
    db.record_ai_provider_api_key_result(
        key_id, success, response_time_ms=response_time_ms, error=error, fallback=fallback,
        quota_exceeded_until=quota_exceeded_until,
    )


def test_key(key_id):
    """Health-check réel pour CETTE clé précise (bouton "Tester" de l'écran
    admin) — instancie le bon provider avec cette clé déchiffrée, appelle
    son .health(), enregistre le résultat via record_result(), jamais une
    génération réelle (pas de tokens consommés). None si `key_id` inconnu."""
    import time as _time

    from chatbot import provider_manager

    row = db.get_ai_provider_api_key(key_id)
    if row is None:
        return None
    try:
        raw_api_key = _decrypt(row["api_key_encrypted"])
    except KeyEncryptionNotConfigured as exc:
        return {"ok": False, "detail": str(exc), "latency_ms": None}

    provider_cls = provider_manager.PROVIDERS.get(row["provider_key"])
    if provider_cls is None:
        return {"ok": False, "detail": f"provider_key inconnu : {row['provider_key']!r}.", "latency_ms": None}

    instance = provider_cls(api_key=raw_api_key)
    started = _time.perf_counter()
    try:
        result = instance.health()
    except Exception as exc:
        result = {"ok": False, "detail": str(exc)}
    latency_ms = round((_time.perf_counter() - started) * 1000)
    record_result(key_id, result["ok"], response_time_ms=latency_ms, error=None if result["ok"] else result.get("detail"))
    return {"ok": result["ok"], "detail": result.get("detail", ""), "latency_ms": latency_ms}
