"""
Système d'authentification NovaMath : inscription, connexion, session
persistante, mot de passe oublié, et architecture prête pour l'OAuth
(Google en premier, Microsoft/Apple/GitHub par extension du même mécanisme).

Toute la logique métier (validation, hachage, anti brute-force) vit ici ;
`webapp/db.py` ne fait que lire/écrire SQLite. `webapp/server.py` monte ce
blueprint et utilise `get_current_user()`/`login_required` pour protéger les
pages et API existantes.
"""
import base64
import binascii
import json
import logging
import os
import re
import secrets
import tempfile
import time
from functools import wraps
from pathlib import Path
from urllib.parse import urlencode, quote

import requests
from flask import Blueprint, jsonify, request, redirect, session
from werkzeug.security import check_password_hash
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError, InvalidHash

import config
import consent_service
import curriculum_registry
import db
import plan_service
import role_service
import two_factor_service
from rate_limit_service import rate_limit

logger = logging.getLogger("auth")

# ── Hachage des mots de passe ────────────────────────────────────────────────
# Argon2id (argon2-cffi), algorithme recommandé par l'OWASP — remplace le
# scrypt de werkzeug utilisé jusqu'à NovaMath V7. Les comptes déjà créés ont un
# hash werkzeug ("scrypt:...") en base : `verify_password()` reconnaît les deux
# formats, et `login()` ré-encode silencieusement en Argon2 dès la première
# connexion réussie avec l'ancien hash (migration transparente, sans forcer de
# réinitialisation de mot de passe pour les comptes existants).
_ph = PasswordHasher()


def hash_password(password):
    return _ph.hash(password)


def verify_password(password_hash, password):
    if not password_hash:
        return False
    if password_hash.startswith("$argon2"):
        try:
            _ph.verify(password_hash, password)
            return True
        except (VerifyMismatchError, InvalidHash):
            return False
    return check_password_hash(password_hash, password)


def needs_rehash(password_hash):
    if not password_hash.startswith("$argon2"):
        return True
    try:
        return _ph.check_needs_rehash(password_hash)
    except InvalidHash:
        return True


# ── Validation réelle des images uploadées ──────────────────────────────────
def sniff_image_type(data_url):
    """Décode le data URL et vérifie que les octets réels correspondent à un
    format d'image reconnu (PNG/JPEG/WEBP/GIF), au lieu de se fier au seul
    préfixe `data:image/...` déclaré par le client (facilement falsifiable).
    Retourne le type détecté ou None si le contenu n'est pas une image valide."""
    try:
        _, b64data = data_url.split(",", 1)
        raw = base64.b64decode(b64data, validate=True)
    except (ValueError, binascii.Error):
        return None
    if raw.startswith(b"\x89PNG\r\n\x1a\n"):
        return "png"
    if raw[:3] == b"\xff\xd8\xff":
        return "jpeg"
    if raw[:4] == b"RIFF" and raw[8:12] == b"WEBP":
        return "webp"
    if raw[:6] in (b"GIF87a", b"GIF89a"):
        return "gif"
    return None

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data"
USER_STATS_DIR = DATA_DIR / "user_stats"
USER_SETTINGS_DIR = DATA_DIR / "user_settings"
USER_COURSE_DIR = DATA_DIR / "user_course_progress"
LEGACY_STATS_PATH = DATA_DIR / "stats_store.json"

SESSION_COOKIE = "nm_session"
REMEMBER_DAYS = 30
DEFAULT_DAYS = 1  # persiste quand même après fermeture du navigateur, juste plus courte durée

EMAIL_RE = re.compile(r"^[a-zA-Z0-9](?:[a-zA-Z0-9._+-]*[a-zA-Z0-9])?@gmail\.com$")
USERNAME_RE = re.compile(r"^[a-zA-Z0-9_-]{3,25}$")
SPECIAL_RE = re.compile(r"[^a-zA-Z0-9]")

MAX_LOGIN_ATTEMPTS = 5
LOCKOUT_MINUTES = 15

auth_bp = Blueprint("auth", __name__, url_prefix="/api/auth")


# ── Validation ──────────────────────────────────────────────────────────────
def _clean(value, max_len=None):
    v = re.sub(r"\s+", " ", str(value or "")).strip()
    return v[:max_len] if max_len else v


def validate_email(email):
    email = _clean(email, 254)
    if not email:
        return None, "L'adresse email est obligatoire."
    if not EMAIL_RE.match(email):
        return None, "Utilise une adresse Gmail valide (exemple : nom@gmail.com)."
    return email.lower(), None



# Contrairement à EMAIL_RE (comptes NovaMath, restreints à Gmail), l'email
# d'un parent n'a aucune raison d'être limité à un fournisseur particulier —
# format RFC 5322 simplifié, même tolérance que la plupart des validateurs
# email côté serveur.
PARENT_EMAIL_RE = re.compile(r"^[^\s@]+@[^\s@]+\.[^\s@]+$")


def validate_parent_email(email):
    email = _clean(email, 254)
    if not email:
        return None, "L'adresse email du parent est obligatoire."
    if not PARENT_EMAIL_RE.match(email):
        return None, "Adresse email du parent invalide."
    return email.lower(), None


def validate_username(username):
    username = _clean(username, 25)
    if not username:
        return None, "Le nom d'utilisateur est obligatoire."
    if not USERNAME_RE.match(username):
        return None, "3 à 25 caractères : lettres, chiffres, tirets ou underscores uniquement, sans espace."
    return username, None


def validate_pseudo(pseudo):
    pseudo = _clean(pseudo, 30)
    if not pseudo:
        return None, "Le pseudo est obligatoire."
    return pseudo, None


def validate_birth_date(birth_date):
    """Valide une date de naissance ISO (`YYYY-MM-DD`) — jamais un âge saisi
    directement (voir consent_service.compute_age, qui le dérive toujours de
    cette date). Rejette les dates futures et les âges déraisonnables (>120
    ans), qui trahissent une saisie erronée plutôt qu'une vraie date."""
    from datetime import date

    birth_date = _clean(birth_date, 10)
    if not birth_date:
        return None, "La date de naissance est obligatoire."
    try:
        year, month, day = (int(part) for part in birth_date.split("-"))
        parsed = date(year, month, day)
    except (ValueError, TypeError):
        return None, "Date de naissance invalide (format attendu : AAAA-MM-JJ)."
    today = date.today()
    if parsed > today:
        return None, "La date de naissance ne peut pas être dans le futur."
    age_years = today.year - parsed.year - ((today.month, today.day) < (parsed.month, parsed.day))
    if age_years > 120:
        return None, "Date de naissance invalide."
    return parsed.isoformat(), None


def password_strength(password):
    """Retourne (score 0-4, label). Utilisé à la fois pour l'indicateur visuel
    et pour la validation stricte côté serveur (score minimal requis)."""
    if not password:
        return 0, "Faible"
    checks = [
        len(password) >= 8,
        any(c.islower() for c in password),
        any(c.isupper() for c in password),
        any(c.isdigit() for c in password),
        bool(SPECIAL_RE.search(password)),
    ]
    score = sum(checks)
    if len(password) < 8:
        score = min(score, 1)
    labels = {0: "Faible", 1: "Faible", 2: "Faible", 3: "Moyen", 4: "Fort", 5: "Très fort"}
    return score, labels[score]


def validate_password(password, confirm=None):
    if not password or not password.strip():
        return "Le mot de passe est obligatoire."
    if len(password) < 8:
        return "Le mot de passe doit contenir au moins 8 caractères."
    if not any(c.islower() for c in password):
        return "Le mot de passe doit contenir au moins une minuscule."
    if not any(c.isupper() for c in password):
        return "Le mot de passe doit contenir au moins une majuscule."
    if not any(c.isdigit() for c in password):
        return "Le mot de passe doit contenir au moins un chiffre."
    if not SPECIAL_RE.search(password):
        return "Le mot de passe doit contenir au moins un caractère spécial."
    if confirm is not None and password != confirm:
        return "Les deux mots de passe ne correspondent pas."
    return None


# ── Stockage des statistiques par utilisateur ──────────────────────────────
def _user_stats_path(user_id):
    return USER_STATS_DIR / f"{user_id}.json"


def read_user_stats(user_id):
    path = _user_stats_path(user_id)
    if not path.exists():
        return {"xp": 0, "history": [], "badges": [], "series": []}
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    data.setdefault("series", [])
    return data


def write_user_stats(user_id, payload):
    """Écriture atomique (fichier temporaire + rename), même stratégie que le
    reste du projet (data/stats_store.json, data/reviews.json)."""
    USER_STATS_DIR.mkdir(parents=True, exist_ok=True)
    fd, tmp_path = tempfile.mkstemp(dir=USER_STATS_DIR, suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False)
        os.replace(tmp_path, _user_stats_path(user_id))
    finally:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)


# ── Stockage des préférences (paramètres) par utilisateur ──────────────────
# Même stratégie que read_user_stats/write_user_stats (un fichier JSON par
# compte, écriture atomique) : une seule source de vérité par utilisateur,
# jamais partagée entre comptes. Un invité a un fichier comme n'importe quel
# compte, mais il est supprimé par _purge_account dès la fin de sa session
# (expiration d'inactivité ou fermeture du navigateur) — ses préférences sont
# donc bien temporaires, sans mécanisme séparé à maintenir.
DEFAULT_SETTINGS = {
    "appearance": {
        "theme": "light",
        "accent": "purple",
        "fontSize": "normal",
        "radius": "normal",
        "animations": True,
        "transparency": True,
    },
    "training": {
        "questionsPerSeries": 10,
        "chrono": True,
        "confirmBeforeLeave": True,
        "autoResume": True,
        "autoShowCorrection": False,
        "soundEffects": True,
    },
    "learning": {
        "dailyGoalExercises": 10,
        "dailyGoalTimeMin": 15,
        "targetAccuracyOn20": 16,
        "prioritizeWeakNotions": True,
        "prioritizeUnmasteredChapters": True,
        "spacedRepetition": True,
        "hints": "parfois",  # jamais | parfois | toujours
        "correctionDisplay": "fin",  # fin | chaque_question
    },
    "language": "fr",
    # Chapitres "enregistrés" (favoris) sur la page Exercices — liste de
    # chapter_id (ex: "Chapitre_3"), persistée comme le reste des préférences,
    # sans nouveau point d'API ni logique de stockage parallèle.
    "favorites": [],
    # Chatbot pédagogique (voir webapp/chatbot/) — FakeProvider (aucune API,
    # réponses assemblées depuis les cours NovaMath) est le fournisseur par
    # défaut aujourd'hui ; Anthropic (API officielle Claude) et Ollama (modèle
    # local) restent disponibles en option ; provider_manager.py permet d'en
    # ajouter d'autres sans migration de schéma.
    "chatbot": {
        "provider": "fake",
        "model": "moteur-novamath",
        "temperature": 0.6,
        "responseLength": "normal",  # court | normal | detaille
        "explanationLevel": "auto",  # auto | college | lycee | expert
        "mode": "professeur",  # professeur | rapide | pas_a_pas | visuel | examen
        "streaming": True,
        "historyEnabled": True,
        "memoryEnabled": True,
    },
}


def _deep_merge_defaults(defaults, override):
    merged = dict(defaults)
    for key, value in (override or {}).items():
        if isinstance(value, dict) and isinstance(defaults.get(key), dict):
            merged[key] = _deep_merge_defaults(defaults[key], value)
        elif key in defaults:
            merged[key] = value
    return merged


def _user_settings_path(user_id):
    return USER_SETTINGS_DIR / f"{user_id}.json"


def read_user_settings(user_id):
    path = _user_settings_path(user_id)
    if not path.exists():
        return json.loads(json.dumps(DEFAULT_SETTINGS))  # copie profonde
    with open(path, "r", encoding="utf-8") as f:
        try:
            saved = json.load(f)
        except json.JSONDecodeError:
            saved = {}
    return _deep_merge_defaults(DEFAULT_SETTINGS, saved)


def write_user_settings(user_id, payload):
    merged = _deep_merge_defaults(DEFAULT_SETTINGS, payload)
    USER_SETTINGS_DIR.mkdir(parents=True, exist_ok=True)
    fd, tmp_path = tempfile.mkstemp(dir=USER_SETTINGS_DIR, suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(merged, f, ensure_ascii=False)
        os.replace(tmp_path, _user_settings_path(user_id))
    finally:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)
    return merged


# ── Stockage de la progression du module Cours par utilisateur ─────────────
# Même stratégie que read_user_stats/write_user_stats : un fichier JSON par
# compte, écriture atomique, purgé avec le reste du compte par _purge_account
# (invités inclus — ils ne conservent aucune progression de lecture).
def _user_course_path(user_id):
    return USER_COURSE_DIR / f"{user_id}.json"


def _read_course_progress_raw(user_id):
    path = _user_course_path(user_id)
    if not path.exists():
        return {}
    with open(path, "r", encoding="utf-8") as f:
        try:
            return json.load(f)
        except json.JSONDecodeError:
            return {}


def _is_namespaced_by_class(raw):
    """Distingue le nouveau format ({class_level: {chapterId: {...}}}) de
    l'ancien format à plat ({chapterId: {...}}, seule forme qui existait avant
    l'audit multi-classe du module Cours). Un dictionnaire vide n'a rien à
    distinguer (traité comme "pas encore namespacé", sans conséquence — voir
    read_user_course_progress). Les clés de premier niveau ne peuvent pas se
    confondre : class_level vient de curriculum_registry.py ("seconde",
    "premiere"...) tandis qu'un chapter_id est toujours "Chapitre_N"."""
    return bool(raw) and all(key in curriculum_registry.CURRICULUM_REGISTRY for key in raw)


def read_user_course_progress(user_id, class_level=None):
    """Progression de lecture du module Cours, isolée par classe.

    `class_level` (optionnel, "seconde" par défaut) : chaque classe a ses
    propres chapter_id ("Chapitre_1"...) réutilisés à l'identique d'une classe
    à l'autre (voir curriculum_registry.py) — sans cette isolation, la
    progression de Première pourrait apparaître comme celle de Seconde et
    inversement.

    Aucune migration destructive : les fichiers écrits avant cette évolution
    sont au format à plat ({chapterId: {...}}), qui appartient entièrement à
    "seconde" par convention (même repli que store.js pour les données non
    taguées ailleurs dans le projet) — lus tels quels, jamais réécrits tant
    qu'aucune nouvelle progression n'est enregistrée (voir
    write_user_course_progress)."""
    class_level = class_level or "seconde"
    raw = _read_course_progress_raw(user_id)
    if _is_namespaced_by_class(raw):
        return raw.get(class_level, {})
    # Format historique (à plat) : n'existe que pour Seconde — une autre
    # classe n'a honnêtement aucune donnée à ce stade, jamais un mélange.
    return raw if class_level == "seconde" else {}


def write_user_course_progress(user_id, chapter_id, notion_id, patch, class_level=None):
    """Fusion partielle d'une seule notion (pas un remplacement complet), pour
    que deux onglets ouverts sur des notions différentes ne s'écrasent pas.
    Bascule paresseusement vers le format namespacé par classe dès la première
    écriture après cette évolution — les données "seconde" déjà présentes au
    format historique sont conservées telles quelles sous la clé "seconde",
    jamais perdues ni dupliquées."""
    class_level = class_level or "seconde"
    raw = _read_course_progress_raw(user_id)
    by_class = raw if _is_namespaced_by_class(raw) else ({"seconde": raw} if raw else {})

    class_progress = dict(by_class.get(class_level, {}))
    chapter_progress = dict(class_progress.get(chapter_id, {}))
    notion_progress = dict(chapter_progress.get(notion_id, {}))
    notion_progress.update(patch)
    notion_progress["updatedAt"] = int(time.time() * 1000)
    chapter_progress[notion_id] = notion_progress
    class_progress[chapter_id] = chapter_progress
    by_class[class_level] = class_progress

    USER_COURSE_DIR.mkdir(parents=True, exist_ok=True)
    fd, tmp_path = tempfile.mkstemp(dir=USER_COURSE_DIR, suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(by_class, f, ensure_ascii=False)
        os.replace(tmp_path, _user_course_path(user_id))
    finally:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)
    return class_progress


def _migrate_legacy_stats_if_first_user(user_id):
    """La toute première inscription hérite de la progression globale existante
    (data/stats_store.json), accumulée avant l'introduction des comptes —
    décision explicitement validée avec l'utilisateur plutôt que de perdre ces
    données ou de les rattacher arbitrairement à un autre compte."""
    if db.count_users() != 1:
        return
    if not LEGACY_STATS_PATH.exists():
        return
    try:
        with open(LEGACY_STATS_PATH, "r", encoding="utf-8") as f:
            legacy = json.load(f)
    except (OSError, json.JSONDecodeError):
        return
    history = legacy.get("history", [])
    xp = legacy.get("xp", 0)
    write_user_stats(user_id, {
        "xp": xp,
        "history": history,
        "badges": legacy.get("badges", []),
        "series": legacy.get("series", []),
    })
    LEGACY_STATS_PATH.rename(DATA_DIR / "stats_store.legacy.json")

    # Pré-remplit le cache du compte (xp/accuracy/temps) immédiatement, pour que
    # /api/auth/me reflète la progression migrée sans attendre une première
    # réponse enregistrée après l'inscription. `progression` (couverture par
    # chapitre) nécessite la banque d'exercices, chargée uniquement dans
    # server.py : elle se resynchronise automatiquement au premier
    # `POST /api/stats` (déclenché par la moindre réponse à un exercice).
    total = len(history)
    correct = sum(1 for h in history if h.get("correct"))
    accuracy = round((correct / total) * 100, 1) if total else 0.0
    total_time_s = sum(h.get("duration_s") or 0 for h in history)
    db.update_stats_cache(user_id, xp, 1, accuracy, 0.0, total_time_s)


# ── Sessions HTTP ────────────────────────────────────────────────────────────
GUEST_IDLE_TTL_MINUTES = 120  # "quitte le site, revient quelques heures plus tard" → nouvel invité


def get_current_user():
    token = request.cookies.get(SESSION_COOKIE)
    user = db.get_session_user(token)
    if user is None:
        return None
    if user["auth_provider"] == "guest":
        # Session invité considérée terminée après trop longtemps d'inactivité :
        # on supprime immédiatement toutes ses données (compte + stats) et on
        # se comporte comme si aucune session n'existait — le prochain
        # `enterGuest()` côté client recréera un invité totalement vierge.
        if db.is_guest_expired(user, GUEST_IDLE_TTL_MINUTES):
            _purge_account(user["id"])
            return None
        db.touch_guest_activity(user["id"])
    return user


def login_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        user = get_current_user()
        if user is None:
            return jsonify({"error": "Connexion requise."}), 401
        request.current_user = user
        return view(*args, **kwargs)
    return wrapped


def _set_session_cookie(response, token, days, persistent=True):
    """`persistent=False` (mode invité) pose un vrai cookie de session sans
    Max-Age : le navigateur le supprime lui-même à sa fermeture complète, ce
    qui coupe déjà une partie des sessions invité même sans attendre le délai
    d'inactivité serveur (voir get_current_user/GUEST_IDLE_TTL_MINUTES)."""
    kwargs = dict(
        httponly=True,
        samesite=config.SESSION_COOKIE_SAMESITE,
        # Piloté par REMEMBER_COOKIE_SECURE / FLASK_ENV (voir config.py) :
        # False en développement (HTTP local), True en production (HTTPS obligatoire).
        secure=config.REMEMBER_COOKIE_SECURE,
    )
    if persistent:
        kwargs["max_age"] = days * 24 * 3600
    response.set_cookie(SESSION_COOKIE, token, **kwargs)


# ── CSRF (double-submit cookie) ─────────────────────────────────────────────
# Le cookie de session est déjà SameSite=Lax (n'est pas envoyé sur une requête
# POST/PUT/DELETE cross-site dans les navigateurs modernes), ce qui bloque déjà
# l'essentiel du CSRF classique. Ce mécanisme est une défense en profondeur
# supplémentaire (couvre aussi les navigateurs anciens sans SameSite) : un
# cookie lisible par le JS du site (donc jamais accessible à un site tiers à
# cause de la same-origin policy) doit être renvoyé à l'identique dans un
# en-tête pour toute requête qui modifie l'état.
CSRF_COOKIE = "nm_csrf"


def _set_csrf_cookie(response, persistent=True):
    token = secrets.token_urlsafe(32)
    kwargs = dict(
        httponly=False,  # doit être lisible par js/api.js pour être renvoyé en en-tête
        samesite=config.SESSION_COOKIE_SAMESITE,
        secure=config.CSRF_COOKIE_SECURE,
    )
    if persistent:
        kwargs["max_age"] = REMEMBER_DAYS * 24 * 3600
    response.set_cookie(CSRF_COOKIE, token, **kwargs)
    return token


def csrf_protect(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if request.method in ("POST", "PUT", "DELETE", "PATCH"):
            # Ne s'applique que s'il y a une session active à protéger : une
            # action anonyme (ex: avis publié sans compte) n'a pas de cookie de
            # session à falsifier, donc rien à vérifier ici pour ce cas.
            user = getattr(request, "current_user", None) or get_current_user()
            if user is not None:
                cookie_token = request.cookies.get(CSRF_COOKIE)
                header_token = request.headers.get("X-CSRF-Token")
                if not cookie_token or not header_token or not secrets.compare_digest(cookie_token, header_token):
                    return jsonify({"error": "Jeton CSRF invalide ou manquant."}), 403
        return view(*args, **kwargs)
    return wrapped


# ── Journal de sécurité ──────────────────────────────────────────────────────
def _client_ip():
    return request.headers.get("X-Forwarded-For", request.remote_addr)


def _log_security_event(event_type, user_id=None):
    db.log_security_event(event_type, user_id=user_id, ip=_client_ip())


# ── Suppression de compte ────────────────────────────────────────────────────
# server.py y ajoute un hook pour libérer l'appartenance des avis publiés par
# le compte (ils restent visibles, mais ne sont plus rattachés à personne) —
# évite une dépendance circulaire entre auth.py et server.py.
ACCOUNT_DELETION_HOOKS = []


def _purge_account(user_id, email=None):
    """Supprime intégralement un compte (utilisé par la suppression volontaire
    et par le nettoyage d'un compte invité une fois ses données transférées)."""
    for hook in ACCOUNT_DELETION_HOOKS:
        hook(user_id)
    stats_path = _user_stats_path(user_id)
    if stats_path.exists():
        stats_path.unlink()
    settings_path = _user_settings_path(user_id)
    if settings_path.exists():
        settings_path.unlink()
    course_path = _user_course_path(user_id)
    if course_path.exists():
        course_path.unlink()
    if email:
        db.delete_login_attempts(email)
    db.delete_user(user_id)  # cascade : sessions / oauth_accounts / password_resets


def _public_user(user):
    return {
        "id": user["id"],
        "email": user["email"],
        "username": user["username"],
        "pseudo": user["pseudo"],
        "avatar": user["avatar"],
        "auth_provider": user["auth_provider"],
        "is_guest": user["auth_provider"] == "guest",
        # Un compte local (email + mot de passe) n'a pas de flux de vérification
        # d'email dans ce projet (aucun service d'envoi configuré, voir
        # forgot_password ci-dessus) — seul un compte lié à un fournisseur OAuth
        # (email déjà vérifié par ce fournisseur) est honnêtement "vérifié".
        "email_verified": user["auth_provider"] not in ("local", "guest"),
        "created_at": user["created_at"],
        "last_login_at": user["last_login_at"],
        "xp": user["xp"],
        "level": user["level"],
        "accuracy": user["accuracy"],
        "progression": user["progression"],
        "total_time_s": user["total_time_s"],
        # Passe par plan_service (source unique de vérité des plans) plutôt
        # que de renvoyer la colonne brute : canonicalise toute valeur
        # inconnue/corrompue vers "free" au lieu de l'exposer telle quelle.
        "plan": plan_service.get_plan(user).value,
        # Passe par role_service (source unique de vérité des rôles), même
        # canonicalisation défensive que "plan" ci-dessus — jamais la colonne
        # brute. Consommé par une future UI admin pour savoir quoi afficher ;
        # l'autorisation réelle reste toujours vérifiée côté serveur (voir
        # role_service.requires_role), ce champ n'est qu'informatif.
        "role": role_service.get_role(user).value,
        # État 2FA (webapp/two_factor_service.py) — jamais le secret ni les
        # recovery codes, uniquement le booléen consommé par le panneau
        # Sécurité pour afficher "Activée"/"Désactivée" et par auth.js pour
        # savoir si l'écran de saisie du code doit apparaître après connexion.
        "two_factor_enabled": two_factor_service.is_enabled(user),
    }


# ── Mode invité ──────────────────────────────────────────────────────────────
GUEST_SESSION_DAYS = 1


@auth_bp.route("/guest", methods=["POST"])
def enter_guest():
    """Entrée en mode invité : compte éphémère réutilisant l'infrastructure de
    comptes existante (sessions, stats par utilisateur, page gating) plutôt
    qu'un système parallèle — voir db.create_guest_user(). Identifiant unique
    et aléatoire (secrets.token_hex), jamais réutilisé d'une session à l'autre.
    Cookie de session non persistant (voir _set_session_cookie) + expiration
    par inactivité côté serveur (GUEST_IDLE_TTL_MINUTES) : la session invité ne
    survit ni à la fermeture du navigateur ni à une longue absence. Les invités
    déjà expirés sont purgés à chaque nouvelle entrée (pas de tâche planifiée
    disponible dans ce projet, un nettoyage paresseux suffit largement)."""
    db.cleanup_expired_guests()
    user_id = db.create_guest_user(secrets.token_hex(8))
    token = db.create_session(user_id, days=GUEST_SESSION_DAYS, user_agent=request.headers.get("User-Agent"))
    db.touch_guest_activity(user_id)
    user = db.get_user_by_id(user_id)

    session.clear()
    _log_security_event("guest_session_started", user_id=user_id)

    resp = jsonify({"user": _public_user(user)})
    _set_session_cookie(resp, token, GUEST_SESSION_DAYS, persistent=False)
    _set_csrf_cookie(resp, persistent=False)
    return resp, 201


@auth_bp.route("/guest/dashboard-seen", methods=["POST"])
@login_required
@csrf_protect
def guest_dashboard_seen():
    """Le Dashboard est intégralement accessible lors de la toute première
    consultation d'un invité (découverte de la plateforme après son évaluation
    initiale) ; toute consultation suivante doit se présenter flouté avec une
    invitation à créer un compte. Le client (dashboard.js) appelle cette route
    une fois par chargement de page : la réponse reflète l'état AVANT cet
    appel (donc `locked: false` la toute première fois), puis marque le
    Dashboard comme déjà vu pour toutes les fois suivantes."""
    user = request.current_user
    if user["auth_provider"] != "guest":
        return jsonify({"locked": False})
    already_viewed = bool(user["guest_dashboard_viewed"])
    if not already_viewed:
        db.mark_guest_dashboard_viewed(user["id"])
    return jsonify({"locked": already_viewed})


def _transfer_guest_data(guest_user, new_user_id):
    """Reprend la progression de la session invité en cours vers le compte
    fraîchement créé (opt-in explicite du client via `transfer_guest`), puis
    supprime le compte invité désormais inutile."""
    stats = read_user_stats(guest_user["id"])
    write_user_stats(new_user_id, stats)
    db.update_stats_cache(
        new_user_id,
        guest_user["xp"], guest_user["level"], guest_user["accuracy"],
        guest_user["progression"], guest_user["total_time_s"],
    )
    _purge_account(guest_user["id"])


# ── Routes ───────────────────────────────────────────────────────────────────
@auth_bp.route("/register", methods=["POST"])
@rate_limit(requests=3, per_seconds=3600)
def register():
    data = request.get_json(force=True) or {}

    email, err = validate_email(data.get("email"))
    if err:
        return jsonify({"error": err, "field": "email"}), 400
    username, err = validate_username(data.get("username"))
    if err:
        return jsonify({"error": err, "field": "username"}), 400
    pseudo, err = validate_pseudo(data.get("pseudo"))
    if err:
        return jsonify({"error": err, "field": "pseudo"}), 400
    birth_date, err = validate_birth_date(data.get("birth_date"))
    if err:
        return jsonify({"error": err, "field": "birth_date"}), 400

    password = data.get("password") or ""
    confirm = data.get("confirm_password")
    err = validate_password(password, confirm)
    if err:
        return jsonify({"error": err, "field": "password"}), 400

    if not data.get("accept_terms"):
        return jsonify({"error": "Tu dois accepter les conditions d'utilisation.", "field": "accept_terms"}), 400
    if not data.get("accept_privacy"):
        return jsonify({"error": "Tu dois accepter la politique de confidentialité.", "field": "accept_privacy"}), 400

    # Protection des mineurs (RGPD art. 8 / art. 45 Loi Informatique et
    # Libertés) — voir consent_service pour le seuil légal français (15 ans).
    # L'email du parent n'est demandé (et validé) que si nécessaire : jamais
    # un champ visible/obligatoire pour un compte majeur.
    is_minor = consent_service.requires_parental_consent(birth_date)
    parent_email = None
    if is_minor:
        parent_email, err = validate_parent_email(data.get("parent_email"))
        if err:
            return jsonify({"error": err, "field": "parent_email"}), 400

    if db.get_user_by_email(email):
        return jsonify({"error": "Cette adresse email est déjà utilisée.", "field": "email"}), 409
    if db.get_user_by_username(username):
        return jsonify({"error": "Ce nom d'utilisateur est déjà pris.", "field": "username"}), 409

    # Capturé avant la création du nouveau compte : si l'utilisateur était en
    # mode invité, on lui propose de conserver sa progression temporaire.
    previous_user = get_current_user()
    was_guest = bool(previous_user) and previous_user["auth_provider"] == "guest"
    transfer_guest = was_guest and bool(data.get("transfer_guest")) and not is_minor

    password_hash = hash_password(password)
    account_status = "pending_parental_consent" if is_minor else "active"
    user_id = db.create_user(
        email, username, pseudo, password_hash,
        birth_date=birth_date, account_status=account_status,
    )
    consent_service.record_initial_policy_acceptance(user_id, ip=_client_ip())

    if transfer_guest:
        _transfer_guest_data(previous_user, user_id)
    else:
        _migrate_legacy_stats_if_first_user(user_id)
        # Si l'invité a choisi "Non" (ne pas conserver sa progression), ou
        # que le nouveau compte est mineur (transfert désactivé le temps du
        # consentement parental), son compte éphémère n'a plus aucune raison
        # de traîner en base jusqu'au nettoyage paresseux de
        # db.cleanup_expired_guests() — autant le supprimer tout de suite.
        if was_guest:
            _purge_account(previous_user["id"])

    user = db.get_user_by_id(user_id)
    _log_security_event("account_created", user_id=user_id)

    if is_minor:
        # Aucune session créée : un compte en attente de consentement parental
        # n'a, par construction, accès à rien (voir _finish_login) — le lien
        # de consentement part directement vers l'email du parent, jamais
        # vers l'enfant.
        token, sent = consent_service.create_consent_request(user, parent_email, ip=_client_ip())
        session.clear()
        payload = {
            "account_status": "pending_parental_consent",
            "message": (
                "Ton compte a été créé mais nécessite l'autorisation d'un parent "
                "avant de pouvoir être utilisé. Un email vient d'être envoyé à "
                "l'adresse fournie."
            ),
        }
        if not sent:
            # Aucun service d'envoi d'email n'est configuré (voir
            # email_service.is_configured()) : le lien est renvoyé en clair
            # dans la réponse JSON en mode développement, jamais journalisé —
            # même filet de secours que dev_reset_link ci-dessus.
            payload["dev_consent_link"] = f"/parent/consent/{token}"
        return jsonify(payload), 202

    token = db.create_session(user_id, days=REMEMBER_DAYS, user_agent=request.headers.get("User-Agent"))
    db.update_last_login(user_id)
    user = role_service.sync_admin_bootstrap(user)

    # La progression d'évaluation/entraînement en cours (session Flask signée,
    # distincte de nm_session) n'est pas liée à un compte : sans ce reset, un
    # quiz commencé avant l'inscription (ou par un compte précédent sur ce
    # même navigateur) pourrait continuer à alimenter le nouveau compte.
    session.clear()

    resp = jsonify({"user": _public_user(user)})
    _set_session_cookie(resp, token, REMEMBER_DAYS)
    _set_csrf_cookie(resp)
    return resp, 201


# ── Consentement parental (RGPD, protection des mineurs) ───────────────────
# Routes PUBLIQUES (aucune session requise — le parent qui ouvre le lien reçu
# par email n'a, et ne doit jamais avoir besoin, de compte NovaMath). Seules
# des informations minimales sont exposées (voir consent_service.
# get_public_consent_info : jamais l'email du parent, uniquement le pseudo de
# l'enfant, le statut et l'expiration).
@auth_bp.route("/parental-consent/<token>", methods=["GET"])
@rate_limit(requests=20, per_seconds=3600)
def get_parental_consent_status(token):
    try:
        info = consent_service.get_public_consent_info(token)
    except consent_service.InvalidConsentToken as e:
        return jsonify({"error": str(e)}), 404
    return jsonify(info)


@auth_bp.route("/parental-consent/<token>/accept", methods=["POST"])
@rate_limit(requests=10, per_seconds=3600)
def accept_parental_consent(token):
    try:
        consent_service.resolve_consent(token, "accepted", ip=_client_ip())
    except consent_service.InvalidConsentToken as e:
        return jsonify({"error": str(e)}), 404
    except consent_service.ConsentAlreadyResolved as e:
        return jsonify({"error": str(e)}), 409
    except consent_service.ConsentExpired as e:
        return jsonify({"error": str(e)}), 410
    return jsonify({"ok": True, "status": "accepted"})


@auth_bp.route("/parental-consent/<token>/refuse", methods=["POST"])
@rate_limit(requests=10, per_seconds=3600)
def refuse_parental_consent(token):
    try:
        consent_service.resolve_consent(token, "refused", ip=_client_ip())
    except consent_service.InvalidConsentToken as e:
        return jsonify({"error": str(e)}), 404
    except consent_service.ConsentAlreadyResolved as e:
        return jsonify({"error": str(e)}), 409
    except consent_service.ConsentExpired as e:
        return jsonify({"error": str(e)}), 410
    return jsonify({"ok": True, "status": "refused"})


@auth_bp.route("/parental-consent/resend", methods=["POST"])
@rate_limit(requests=3, per_seconds=3600)
def resend_parental_consent():
    """Renvoi de l'email de consentement — le compte concerné n'a par
    définition pas de session (voir register()), donc identifié par email +
    mot de passe, comme un login partiel (jamais par simple user_id fourni par
    le client, qui permettrait de spammer n'importe quel compte)."""
    data = request.get_json(force=True) or {}
    email = _clean(data.get("email"), 254).lower()
    password = data.get("password") or ""
    user = db.get_user_by_email(email) if email else None

    generic_error = jsonify({"error": "Email ou mot de passe incorrect."}), 401
    if not user or not verify_password(user.get("password_hash"), password):
        return generic_error
    if user.get("account_status") != "pending_parental_consent":
        return jsonify({"error": "Aucune demande de consentement parental en attente pour ce compte."}), 400

    try:
        token, sent = consent_service.resend_consent_email(user, ip=_client_ip())
    except consent_service.NoPendingConsentRequest as e:
        return jsonify({"error": str(e)}), 400

    payload = {"ok": True}
    if not sent:
        payload["dev_consent_link"] = f"/parent/consent/{token}"
    return jsonify(payload)


def _create_authenticated_session(user, days, event_type="login_success"):
    """Crée la vraie session (token + cookies) pour un utilisateur déjà
    entièrement authentifié — mot de passe seul, mot de passe + second facteur
    déjà validé, ou échange OAuth déjà vérifié (voir oauth_callback). Point de
    sortie unique partagé par tous les chemins de connexion — la séquence de
    création de session ne doit jamais être dupliquée."""
    token = db.create_session(user["id"], days=days, user_agent=request.headers.get("User-Agent"))
    db.update_last_login(user["id"])
    user = db.get_user_by_id(user["id"])
    user = role_service.sync_admin_bootstrap(user)
    _log_security_event(event_type, user_id=user["id"])

    session.clear()  # même raison qu'à l'inscription — voir commentaire dans register()
    return token, user


def _finish_login(user, days):
    token, user = _create_authenticated_session(user, days)
    resp = jsonify({"user": _public_user(user)})
    _set_session_cookie(resp, token, days)
    _set_csrf_cookie(resp)
    return resp


@auth_bp.route("/login", methods=["POST"])
@rate_limit(requests=5, per_seconds=60)
def login():
    data = request.get_json(force=True) or {}
    email = _clean(data.get("email"), 254).lower()
    password = data.get("password") or ""
    remember = bool(data.get("remember"))

    if not email or not password:
        return jsonify({"error": "Adresse email et mot de passe requis."}), 400

    recent_failures = db.count_recent_failed_attempts(email, LOCKOUT_MINUTES)
    if recent_failures >= MAX_LOGIN_ATTEMPTS:
        return jsonify({"error": f"Trop de tentatives échouées. Réessaie dans {LOCKOUT_MINUTES} minutes."}), 429

    # Temporisation progressive : chaque échec récent ralentit un peu plus la
    # réponse suivante, avant même d'atteindre le verrou strict ci-dessus —
    # décourage le brute-force automatisé sans pénaliser un utilisateur qui se
    # trompe une seule fois.
    if recent_failures > 0:
        time.sleep(min(0.5 * recent_failures, 3.0))

    user = db.get_user_by_email(email)
    ok = bool(user) and verify_password(user.get("password_hash"), password)
    db.record_login_attempt(email, ok)

    if not ok:
        _log_security_event("login_failed", user_id=user["id"] if user else None)
        return jsonify({"error": "Email ou mot de passe incorrect."}), 401

    if needs_rehash(user["password_hash"]):
        db.set_password_hash(user["id"], hash_password(password))

    # Protection des mineurs (RGPD) — aucune session n'est créée pour un
    # compte encore en attente de consentement parental (ou dont le parent l'a
    # refusé), avant même de vérifier la 2FA : bloque nativement tout accès
    # (chatbot, Premium, exercices, données personnelles) sans dupliquer une
    # vérification dans chaque route existante (voir consent_service.py).
    account_status = user.get("account_status", "active")
    if account_status != "active":
        _log_security_event("login_blocked_account_status", user_id=user["id"])
        return jsonify({
            "error": "Ce compte n'a pas encore accès : consentement parental requis ou refusé.",
            "account_status": account_status,
        }), 403

    days = REMEMBER_DAYS if remember else DEFAULT_DAYS

    if two_factor_service.is_enabled(user):
        # Mot de passe correct mais connexion PAS encore terminée : aucune
        # session créée tant que le second facteur n'est pas validé (voir
        # /2fa/verify, /2fa/recovery) — "login_success" n'est journalisé que
        # dans _finish_login(), une fois la connexion réellement complète.
        challenge_token = two_factor_service.create_login_challenge(user, remember)
        _log_security_event("login_password_verified", user_id=user["id"])
        return jsonify({"two_factor_required": True, "challenge_token": challenge_token})

    return _finish_login(user, days)


@auth_bp.route("/logout", methods=["POST"])
@csrf_protect
def logout():
    token = request.cookies.get(SESSION_COOKIE)
    if token:
        user = db.get_session_user(token)
        _log_security_event("logout", user_id=user["id"] if user else None)
        db.delete_session(token)
    session.clear()  # purge la progression de quiz en cours — voir commentaire dans register()
    resp = jsonify({"ok": True})
    resp.delete_cookie(SESSION_COOKIE)
    resp.delete_cookie(CSRF_COOKIE)
    return resp


@auth_bp.route("/me", methods=["GET"])
@login_required
def me():
    return jsonify({"user": _public_user(request.current_user)})


@auth_bp.route("/me", methods=["PUT"])
@login_required
@csrf_protect
def update_me():
    if request.current_user["auth_provider"] == "guest":
        return jsonify({
            "error": "La personnalisation du profil nécessite un compte.",
            "guest_restricted": True,
        }), 403

    data = request.get_json(force=True) or {}
    user_id = request.current_user["id"]

    pseudo = None
    if "pseudo" in data:
        pseudo, err = validate_pseudo(data.get("pseudo"))
        if err:
            return jsonify({"error": err, "field": "pseudo"}), 400

    avatar_explicit = "avatar" in data
    avatar = data.get("avatar")
    if avatar_explicit and avatar:
        allowed_prefixes = ("data:image/png;base64,", "data:image/jpeg;base64,", "data:image/jpg;base64,", "data:image/webp;base64,")
        if not isinstance(avatar, str) or not avatar.startswith(allowed_prefixes):
            return jsonify({"error": "Format de photo non supporté.", "field": "avatar"}), 400
        if len(avatar) > 500_000:
            return jsonify({"error": "Photo trop volumineuse.", "field": "avatar"}), 400
        if sniff_image_type(avatar) is None:
            return jsonify({"error": "Le contenu du fichier ne correspond pas à une image valide.", "field": "avatar"}), 400

    # Changement d'adresse email : sensible, exige le mot de passe actuel (même
    # logique que delete_me) — évite qu'une session volée (XSS, appareil laissé
    # ouvert) puisse détourner le compte en changeant l'email de récupération.
    if "email" in data:
        email, err = validate_email(data.get("email"))
        if err:
            return jsonify({"error": err, "field": "email"}), 400
        password = data.get("current_password") or ""
        if not request.current_user.get("password_hash") or not verify_password(request.current_user["password_hash"], password):
            return jsonify({"error": "Mot de passe actuel incorrect.", "field": "current_password"}), 401
        existing = db.get_user_by_email(email)
        if existing and existing["id"] != user_id:
            return jsonify({"error": "Cette adresse email est déjà utilisée.", "field": "email"}), 409
        db.update_email(user_id, email)
        _log_security_event("email_changed", user_id=user_id)

    db.update_profile(user_id, pseudo=pseudo, avatar=avatar, avatar_explicit=avatar_explicit)
    # Droit de rectification RGPD : cette route EST le mécanisme de
    # rectification des informations personnelles (pseudo/avatar/email) —
    # jamais dupliqué ailleurs, seule la journalisation est ajoutée ici.
    if pseudo is not None or avatar_explicit or "email" in data:
        _log_security_event("gdpr_rectification", user_id=user_id)
    user = db.get_user_by_id(user_id)
    return jsonify({"user": _public_user(user)})


@auth_bp.route("/change-password", methods=["POST"])
@login_required
@csrf_protect
def change_password():
    user = request.current_user
    if user["auth_provider"] == "guest":
        return jsonify({"error": "Le mode invité n'a pas de mot de passe.", "guest_restricted": True}), 403

    data = request.get_json(force=True) or {}
    current_password = data.get("current_password") or ""
    new_password = data.get("new_password") or ""
    confirm = data.get("confirm_password")

    if not user.get("password_hash") or not verify_password(user["password_hash"], current_password):
        return jsonify({"error": "Mot de passe actuel incorrect.", "field": "current_password"}), 401

    err = validate_password(new_password, confirm)
    if err:
        return jsonify({"error": err, "field": "new_password"}), 400

    db.set_password_hash(user["id"], hash_password(new_password))
    _log_security_event("password_changed", user_id=user["id"])
    return jsonify({"ok": True})


@auth_bp.route("/sessions", methods=["GET"])
@login_required
def list_sessions():
    """Appareils connectés (section Confidentialité & Sécurité)."""
    current_token = request.cookies.get(SESSION_COOKIE)
    rows = db.list_sessions(request.current_user["id"])
    return jsonify({
        "sessions": [
            {
                "current": r["token"] == current_token,
                "created_at": r["created_at"],
                "expires_at": r["expires_at"],
                "user_agent": r.get("user_agent") or "Appareil inconnu",
            }
            for r in rows
        ],
    })


@auth_bp.route("/sessions/logout-others", methods=["POST"])
@login_required
@csrf_protect
def logout_other_sessions():
    current_token = request.cookies.get(SESSION_COOKIE)
    db.delete_other_sessions(request.current_user["id"], current_token)
    _log_security_event("logout_all_devices", user_id=request.current_user["id"])
    return jsonify({"ok": True})


# ── Authentification à deux facteurs (SEC-03, webapp/two_factor_service.py) ──
# Toute la logique métier (génération/chiffrement du secret, QR code,
# vérification TOTP, recovery codes, verrouillage) vit dans two_factor_
# service.py ; ces routes ne font que traduire HTTP <-> appels au service,
# exactement comme pour billing_service.py/quota_service.py ailleurs dans ce
# fichier. Le mode invité n'a pas de mot de passe (voir change_password
# ci-dessus, même exclusion) : la 2FA lui est donc également fermée.
def _reject_guest_2fa(user):
    if user["auth_provider"] == "guest":
        return jsonify({"error": "Le mode invité ne permet pas la 2FA.", "guest_restricted": True}), 403
    return None


@auth_bp.route("/2fa/setup", methods=["POST"])
@login_required
@rate_limit(requests=10, per_seconds=3600)
@csrf_protect
def setup_2fa():
    user = request.current_user
    guest_rejected = _reject_guest_2fa(user)
    if guest_rejected:
        return guest_rejected

    try:
        result = two_factor_service.begin_setup(user)
    except two_factor_service.TwoFactorNotConfigured as e:
        logger.error("2FA non configurée côté serveur : %s", e)
        return jsonify({
            "error": "L'authentification à deux facteurs n'est pas encore configurée sur ce serveur.",
        }), 501
    except two_factor_service.TwoFactorAlreadyEnabled:
        return jsonify({"error": "La 2FA est déjà active sur ce compte."}), 400

    return jsonify(result)


@auth_bp.route("/2fa/enable", methods=["POST"])
@login_required
@rate_limit(requests=10, per_seconds=3600)
@csrf_protect
def enable_2fa():
    user = request.current_user
    guest_rejected = _reject_guest_2fa(user)
    if guest_rejected:
        return guest_rejected

    data = request.get_json(force=True) or {}
    code = (data.get("code") or "").strip()

    try:
        recovery_codes = two_factor_service.confirm_setup(user, code)
    except two_factor_service.TwoFactorNotConfigured as e:
        logger.error("2FA non configurée côté serveur : %s", e)
        return jsonify({
            "error": "L'authentification à deux facteurs n'est pas encore configurée sur ce serveur.",
        }), 501
    except two_factor_service.TwoFactorAlreadyEnabled:
        return jsonify({"error": "La 2FA est déjà active sur ce compte."}), 400
    except two_factor_service.NoPendingSetup as e:
        return jsonify({"error": str(e)}), 400
    except two_factor_service.InvalidTotpCode:
        _log_security_event("two_factor_enable_failed", user_id=user["id"])
        return jsonify({"error": "Code de vérification invalide.", "field": "code"}), 400

    _log_security_event("two_factor_enabled", user_id=user["id"])
    return jsonify({"ok": True, "recovery_codes": recovery_codes}), 201


@auth_bp.route("/2fa/disable", methods=["POST"])
@login_required
@rate_limit(requests=10, per_seconds=3600)
@csrf_protect
def disable_2fa():
    user = request.current_user
    guest_rejected = _reject_guest_2fa(user)
    if guest_rejected:
        return guest_rejected

    data = request.get_json(force=True) or {}
    password = data.get("password") or ""
    code = (data.get("code") or "").strip()

    # Mot de passe ET code TOTP obligatoires (deux facteurs indépendants) —
    # vérifiés séparément : le mot de passe ici (déjà l'utilitaire de ce
    # fichier), le code TOTP délégué au service (voir two_factor_service.disable).
    if not user.get("password_hash") or not verify_password(user["password_hash"], password):
        return jsonify({"error": "Mot de passe actuel incorrect.", "field": "password"}), 401

    try:
        two_factor_service.disable(user, code)
    except two_factor_service.TwoFactorNotEnabled as e:
        return jsonify({"error": str(e)}), 400
    except two_factor_service.TooManyAttempts as e:
        return jsonify({"error": str(e), "retry_after_minutes": e.retry_after_minutes}), 429
    except two_factor_service.InvalidTotpCode as e:
        _log_security_event("two_factor_disable_failed", user_id=e.user_id or user["id"])
        return jsonify({"error": "Code de vérification invalide.", "field": "code"}), 400

    _log_security_event("two_factor_disabled", user_id=user["id"])
    return jsonify({"ok": True})


@auth_bp.route("/2fa/verify", methods=["POST"])
@rate_limit(requests=5, per_seconds=60)
def verify_2fa():
    """Deuxième étape de connexion (voir login() ci-dessus, qui renvoie
    `two_factor_required` + `challenge_token` au lieu d'une session quand le
    compte a la 2FA active) — jamais de session tant que ce code n'est pas
    validé."""
    data = request.get_json(force=True) or {}
    challenge_token = data.get("challenge_token") or ""
    code = (data.get("code") or "").strip()

    try:
        user, remember = two_factor_service.verify_login_challenge(challenge_token, code)
    except two_factor_service.InvalidChallenge as e:
        return jsonify({"error": str(e)}), 400
    except two_factor_service.TwoFactorNotEnabled as e:
        return jsonify({"error": str(e)}), 400
    except two_factor_service.TooManyAttempts as e:
        return jsonify({"error": str(e), "retry_after_minutes": e.retry_after_minutes}), 429
    except two_factor_service.InvalidTotpCode as e:
        _log_security_event("two_factor_verify_failed", user_id=e.user_id)
        return jsonify({"error": "Code de vérification invalide."}), 401

    _log_security_event("two_factor_verify_success", user_id=user["id"])
    days = REMEMBER_DAYS if remember else DEFAULT_DAYS
    return _finish_login(user, days)


@auth_bp.route("/2fa/recovery", methods=["POST"])
@rate_limit(requests=5, per_seconds=60)
def recovery_2fa():
    """Alternative à /2fa/verify quand l'utilisateur n'a plus accès à son
    application TOTP — termine la connexion avec un recovery code à usage
    unique (voir two_factor_service.verify_recovery_challenge)."""
    data = request.get_json(force=True) or {}
    challenge_token = data.get("challenge_token") or ""
    recovery_code = (data.get("recovery_code") or "").strip()

    try:
        user, remember = two_factor_service.verify_recovery_challenge(challenge_token, recovery_code)
    except two_factor_service.InvalidChallenge as e:
        return jsonify({"error": str(e)}), 400
    except two_factor_service.TwoFactorNotEnabled as e:
        return jsonify({"error": str(e)}), 400
    except two_factor_service.TooManyAttempts as e:
        return jsonify({"error": str(e), "retry_after_minutes": e.retry_after_minutes}), 429
    except two_factor_service.InvalidRecoveryCode as e:
        _log_security_event("two_factor_recovery_failed", user_id=e.user_id)
        return jsonify({"error": "Recovery code invalide ou déjà utilisé."}), 401

    _log_security_event("two_factor_recovery_used", user_id=user["id"])
    days = REMEMBER_DAYS if remember else DEFAULT_DAYS
    return _finish_login(user, days)


@auth_bp.route("/me", methods=["DELETE"])
@login_required
@csrf_protect
def delete_me():
    """Suppression de compte : mot de passe requis (sauf comptes OAuth sans mot
    de passe local) + confirmation explicite du client — jamais une simple
    requête DELETE sans vérification, pour éviter une suppression accidentelle
    ou forcée (ex: CSRF, déjà bloqué par @csrf_protect, mais défense en
    profondeur supplémentaire)."""
    data = request.get_json(force=True) or {}
    user = request.current_user

    if not data.get("confirm"):
        return jsonify({"error": "Confirmation requise."}), 400

    if user.get("password_hash"):
        password = data.get("password") or ""
        if not password or not verify_password(user["password_hash"], password):
            return jsonify({"error": "Mot de passe incorrect.", "field": "password"}), 401

    _log_security_event("account_deleted", user_id=user["id"])
    # Droit à l'effacement RGPD : cette route EST le mécanisme de suppression
    # complète de compte (_purge_account supprime la ligne `users`, ce qui
    # supprime en cascade sessions/oauth_accounts/password_resets/
    # conversations, et efface les fichiers stats/settings/progression Cours)
    # — jamais dupliqué ailleurs. consent_records/security_events survivent
    # volontairement (preuves légales, voir leur commentaire dans SCHEMA).
    _log_security_event("gdpr_delete_account", user_id=user["id"])
    _purge_account(user["id"], email=user["email"])

    session.clear()
    resp = jsonify({"ok": True})
    resp.delete_cookie(SESSION_COOKIE)
    resp.delete_cookie(CSRF_COOKIE)
    return resp


@auth_bp.route("/forgot-password", methods=["POST"])
@rate_limit(requests=3, per_seconds=3600)
def forgot_password():
    data = request.get_json(force=True) or {}
    email = _clean(data.get("email"), 254).lower()
    user = db.get_user_by_email(email) if email else None

    # Réponse volontairement identique que l'email existe ou non (anti énumération de comptes).
    generic = {"ok": True, "message": "Si un compte existe avec cette adresse, un lien de réinitialisation a été généré."}

    if not user:
        return jsonify(generic)

    token = db.create_password_reset(user["id"])
    reset_link = f"/reset-password.html?token={token}"
    _log_security_event("password_reset_requested", user_id=user["id"])

    # Aucun service d'envoi d'email n'est configuré dans ce projet local : le
    # lien est renvoyé au client en mode développement (jamais journalisé —
    # un token de réinitialisation est un secret au même titre qu'un mot de
    # passe, voir _log_security_event ci-dessus qui n'enregistre que l'id
    # utilisateur). Pour brancher un vrai envoi, remplacer ce bloc par un appel
    # à un fournisseur SMTP/API (ex: send_email(user["email"], "Réinitialisation
    # NovaMath", reset_link)) et supprimer `dev_reset_link` de la réponse.
    generic["dev_reset_link"] = reset_link
    return jsonify(generic)


@auth_bp.route("/reset-password", methods=["POST"])
# Non listée explicitement dans la spec SEC (qui ne cite que "mot de passe
# oublié" = forgot_password ci-dessus), mais soumettre un token de
# réinitialisation est exactement le genre d'endpoint qu'un brute force
# distribué viserait (deviner `token`) — même limite que forgot_password par
# cohérence, plutôt que de laisser ce point d'entrée sans aucune protection.
@rate_limit(requests=3, per_seconds=3600)
def reset_password():
    data = request.get_json(force=True) or {}
    token = data.get("token") or ""
    password = data.get("password") or ""
    confirm = data.get("confirm_password")

    reset = db.get_password_reset(token)
    if not reset:
        return jsonify({"error": "Ce lien de réinitialisation est invalide ou a expiré."}), 400

    err = validate_password(password, confirm)
    if err:
        return jsonify({"error": err, "field": "password"}), 400

    db.set_password_hash(reset["user_id"], hash_password(password))
    db.mark_reset_used(token)
    _log_security_event("password_changed", user_id=reset["user_id"])
    return jsonify({"ok": True})


# ── OAuth (Google prêt à configurer, architecture prête pour les autres) ─────
# Chaque fournisseur n'a besoin que d'un identifiant client + une fonction
# d'échange de code ; ajouter Microsoft/Apple/GitHub = ajouter une entrée ici
# et une fonction _exchange_<provider>_code(), sans toucher au reste du flux
# (create_user / get_user_by_oauth / link_oauth_account sont déjà génériques).
OAUTH_PROVIDERS = {
    "google": {
        "client_id_env": "GOOGLE_CLIENT_ID",
        "client_secret_env": "GOOGLE_CLIENT_SECRET",
        "authorize_url": "https://accounts.google.com/o/oauth2/v2/auth",
        "token_url": "https://oauth2.googleapis.com/token",
        "userinfo_url": "https://www.googleapis.com/oauth2/v3/userinfo",
        "scope": "openid email profile",
    },
}


def _provider_configured(provider):
    cfg = OAUTH_PROVIDERS.get(provider)
    if not cfg:
        return False
    return bool(os.environ.get(cfg["client_id_env"])) and bool(os.environ.get(cfg["client_secret_env"]))


def _oauth_redirect_uri(provider):
    return f"{request.url_root}api/auth/{provider}/callback"


@auth_bp.route("/<provider>/start")
def oauth_start(provider):
    if provider not in OAUTH_PROVIDERS:
        return jsonify({"error": "Fournisseur inconnu."}), 404
    if not _provider_configured(provider):
        return jsonify({
            "error": f"La connexion via {provider.capitalize()} n'est pas encore configurée sur ce serveur.",
            "detail": (
                f"Architecture prête (routes /api/auth/{provider}/start et /callback, table oauth_accounts) — "
                f"il ne manque que les identifiants OAuth ({OAUTH_PROVIDERS[provider]['client_id_env']} / "
                f"{OAUTH_PROVIDERS[provider]['client_secret_env']}) à définir en variables d'environnement."
            ),
        }), 501

    cfg = OAUTH_PROVIDERS[provider]
    # `state` protège contre le CSRF sur le callback OAuth (RFC 6749 §10.12) —
    # stocké dans la session Flask signée (cookie), jamais en base : sa seule
    # fonction est de vérifier que le navigateur qui revient sur /callback est
    # bien celui qui a initié /start, pas de survivre à la session.
    state = secrets.token_urlsafe(32)
    session["oauth_state"] = state
    session["oauth_provider"] = provider
    params = urlencode({
        "client_id": os.environ[cfg["client_id_env"]],
        "redirect_uri": _oauth_redirect_uri(provider),
        "response_type": "code",
        "scope": cfg["scope"],
        "access_type": "offline",
        "prompt": "consent",
        "state": state,
    })
    return redirect(f"{cfg['authorize_url']}?{params}")


def _oauth_error_redirect(message):
    """Les erreurs OAuth surviennent après une navigation top-level (retour du
    fournisseur), jamais via fetch/XHR — impossible de renvoyer un JSON
    exploitable par le JS déjà en place. On redirige vers l'accueil avec un
    paramètre que la modale de connexion sait afficher (voir auth.js)."""
    session.pop("oauth_state", None)
    session.pop("oauth_provider", None)
    return redirect(f"{request.url_root}?oauth_error={quote(message)}")


@auth_bp.route("/<provider>/callback")
def oauth_callback(provider):
    if provider not in OAUTH_PROVIDERS or not _provider_configured(provider):
        return jsonify({"error": "Fournisseur non configuré."}), 501
    cfg = OAUTH_PROVIDERS[provider]

    if request.args.get("error"):
        # L'utilisateur a refusé le consentement côté Google (ou une autre
        # erreur du fournisseur) — pas une panne NovaMath, jamais journalisé
        # comme un échec de sécurité.
        return _oauth_error_redirect("Connexion annulée.")

    expected_state = session.get("oauth_state")
    expected_provider = session.get("oauth_provider")
    state = request.args.get("state")
    if not expected_state or state != expected_state or provider != expected_provider:
        _log_security_event("oauth_state_mismatch")
        return _oauth_error_redirect("Requête de connexion invalide ou expirée, réessaie.")

    code = request.args.get("code")
    if not code:
        return _oauth_error_redirect("Requête de connexion invalide, réessaie.")

    try:
        token_resp = requests.post(
            cfg["token_url"],
            data={
                "client_id": os.environ[cfg["client_id_env"]],
                "client_secret": os.environ[cfg["client_secret_env"]],
                "code": code,
                "redirect_uri": _oauth_redirect_uri(provider),
                "grant_type": "authorization_code",
            },
            timeout=10,
        )
        token_resp.raise_for_status()
        access_token = token_resp.json().get("access_token")
    except (requests.RequestException, ValueError) as e:
        logger.warning("Échange de code OAuth (%s) échoué : %s", provider, e)
        return _oauth_error_redirect("Connexion impossible, réessaie dans un instant.")
    if not access_token:
        logger.warning("Réponse token OAuth (%s) sans access_token.", provider)
        return _oauth_error_redirect("Connexion impossible, réessaie dans un instant.")

    try:
        info_resp = requests.get(
            cfg["userinfo_url"],
            headers={"Authorization": f"Bearer {access_token}"},
            timeout=10,
        )
        info_resp.raise_for_status()
        profile = info_resp.json()
    except (requests.RequestException, ValueError) as e:
        logger.warning("Récupération du profil OAuth (%s) échouée : %s", provider, e)
        return _oauth_error_redirect("Connexion impossible, réessaie dans un instant.")

    provider_user_id = profile.get("sub")
    email = (profile.get("email") or "").lower()
    email_verified = profile.get("email_verified")
    # Google encode ce champ en booléen ou en chaîne "true" selon l'endpoint —
    # on accepte les deux plutôt que de rejeter par excès de prudence.
    email_verified = email_verified is True or email_verified == "true"
    if not provider_user_id or not email or not email_verified:
        return _oauth_error_redirect("Ton compte Google doit avoir un email vérifié.")

    session.pop("oauth_state", None)
    session.pop("oauth_provider", None)

    existing = db.get_user_by_oauth(provider, provider_user_id)
    if existing:
        token, user = _create_authenticated_session(existing, REMEMBER_DAYS, event_type="oauth_login_success")
        resp = redirect(f"{request.url_root}dashboard.html")
        _set_session_cookie(resp, token, REMEMBER_DAYS)
        _set_csrf_cookie(resp)
        return resp

    by_email = db.get_user_by_email(email)
    if by_email:
        # Email vérifié par Google == preuve suffisante de propriété pour lier
        # un compte local existant (jamais l'inverse : on ne crée jamais de
        # compte local à partir d'un email non vérifié).
        db.link_oauth_account(by_email["id"], provider, provider_user_id)
        _log_security_event("oauth_account_linked", user_id=by_email["id"])
        token, user = _create_authenticated_session(by_email, REMEMBER_DAYS, event_type="oauth_login_success")
        resp = redirect(f"{request.url_root}dashboard.html")
        _set_session_cookie(resp, token, REMEMBER_DAYS)
        _set_csrf_cookie(resp)
        return resp

    # Nouveau compte : la date de naissance (obligation RGPD art. 8 — seuil de
    # consentement parental, voir consent_service) n'existe pas côté Google et
    # doit être collectée avant de créer quoi que ce soit. Profil vérifié
    # posé en session (signée, jamais en base) le temps que le front complète
    # l'inscription via /api/auth/<provider>/complete-signup.
    session["pending_oauth_profile"] = {
        "provider": provider,
        "provider_user_id": provider_user_id,
        "email": email,
        "name": profile.get("name") or profile.get("given_name") or "",
    }
    return redirect(f"{request.url_root}?oauth_complete_signup={provider}")


@auth_bp.route("/<provider>/complete-signup", methods=["POST"])
@rate_limit(requests=5, per_seconds=3600)
def oauth_complete_signup(provider):
    """Termine une inscription Google amorcée par oauth_callback : même
    validations que register() (nom d'utilisateur, pseudo, date de naissance,
    CGU/confidentialité), mais email déjà vérifié par le fournisseur et aucun
    mot de passe à choisir (password_hash reste NULL, colonne nullable conçue
    pour ça — voir schéma users)."""
    pending = session.get("pending_oauth_profile")
    if not pending or pending.get("provider") != provider:
        return jsonify({"error": "Aucune inscription Google en attente."}), 400

    email = pending["email"]
    email, err = validate_email(email)
    if err:
        # Compte Google valide mais hors du domaine accepté par NovaMath
        # (voir EMAIL_RE) — même contrainte que l'inscription classique.
        session.pop("pending_oauth_profile", None)
        return jsonify({"error": err, "field": "email"}), 400

    data = request.get_json(force=True) or {}
    username, err = validate_username(data.get("username"))
    if err:
        return jsonify({"error": err, "field": "username"}), 400
    pseudo, err = validate_pseudo(data.get("pseudo") or pending.get("name"))
    if err:
        return jsonify({"error": err, "field": "pseudo"}), 400
    birth_date, err = validate_birth_date(data.get("birth_date"))
    if err:
        return jsonify({"error": err, "field": "birth_date"}), 400

    if not data.get("accept_terms"):
        return jsonify({"error": "Tu dois accepter les conditions d'utilisation.", "field": "accept_terms"}), 400
    if not data.get("accept_privacy"):
        return jsonify({"error": "Tu dois accepter la politique de confidentialité.", "field": "accept_privacy"}), 400

    is_minor = consent_service.requires_parental_consent(birth_date)
    parent_email = None
    if is_minor:
        parent_email, err = validate_parent_email(data.get("parent_email"))
        if err:
            return jsonify({"error": err, "field": "parent_email"}), 400

    if db.get_user_by_email(email):
        return jsonify({"error": "Cette adresse email est déjà utilisée.", "field": "email"}), 409
    if db.get_user_by_username(username):
        return jsonify({"error": "Ce nom d'utilisateur est déjà pris.", "field": "username"}), 409

    account_status = "pending_parental_consent" if is_minor else "active"
    user_id = db.create_user(
        email, username, pseudo, password_hash=None, auth_provider=provider,
        birth_date=birth_date, account_status=account_status,
    )
    db.link_oauth_account(user_id, provider, pending["provider_user_id"])
    consent_service.record_initial_policy_acceptance(user_id, ip=_client_ip())
    _log_security_event("account_created", user_id=user_id)
    session.pop("pending_oauth_profile", None)

    if is_minor:
        user = db.get_user_by_id(user_id)
        token, sent = consent_service.create_consent_request(user, parent_email, ip=_client_ip())
        session.clear()
        payload = {
            "account_status": "pending_parental_consent",
            "message": (
                "Ton compte a été créé mais nécessite l'autorisation d'un parent "
                "avant de pouvoir être utilisé. Un email vient d'être envoyé à "
                "l'adresse fournie."
            ),
        }
        if not sent:
            payload["dev_consent_link"] = f"/parent/consent/{token}"
        return jsonify(payload), 202

    user = db.get_user_by_id(user_id)
    token, user = _create_authenticated_session(user, REMEMBER_DAYS, event_type="oauth_login_success")
    resp = jsonify({"user": _public_user(user)})
    _set_session_cookie(resp, token, REMEMBER_DAYS)
    _set_csrf_cookie(resp)
    return resp, 201
