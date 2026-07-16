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
import os
import re
import secrets
import tempfile
import time
from functools import wraps
from pathlib import Path

from flask import Blueprint, jsonify, request, redirect, session
from werkzeug.security import check_password_hash
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError, InvalidHash

import db

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
        "theme": "dark",
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


def read_user_course_progress(user_id):
    path = _user_course_path(user_id)
    if not path.exists():
        return {}
    with open(path, "r", encoding="utf-8") as f:
        try:
            return json.load(f)
        except json.JSONDecodeError:
            return {}


def write_user_course_progress(user_id, chapter_id, notion_id, patch):
    """Fusion partielle d'une seule notion (pas un remplacement complet), pour
    que deux onglets ouverts sur des notions différentes ne s'écrasent pas."""
    data = read_user_course_progress(user_id)
    chapter_progress = dict(data.get(chapter_id, {}))
    notion_progress = dict(chapter_progress.get(notion_id, {}))
    notion_progress.update(patch)
    notion_progress["updatedAt"] = int(time.time() * 1000)
    chapter_progress[notion_id] = notion_progress
    data[chapter_id] = chapter_progress

    USER_COURSE_DIR.mkdir(parents=True, exist_ok=True)
    fd, tmp_path = tempfile.mkstemp(dir=USER_COURSE_DIR, suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False)
        os.replace(tmp_path, _user_course_path(user_id))
    finally:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)
    return data


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
        samesite="Lax",
        # `secure=False` : le projet tourne en local sur http://127.0.0.1.
        # À activer avant tout déploiement public (HTTPS obligatoire).
        secure=False,
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
        samesite="Lax",
        secure=False,
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
def _log_security_event(event_type, user_id=None):
    db.log_security_event(event_type, user_id=user_id, ip=request.headers.get("X-Forwarded-For", request.remote_addr))


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

    password = data.get("password") or ""
    confirm = data.get("confirm_password")
    err = validate_password(password, confirm)
    if err:
        return jsonify({"error": err, "field": "password"}), 400

    if not data.get("accept_terms"):
        return jsonify({"error": "Tu dois accepter les conditions d'utilisation.", "field": "accept_terms"}), 400
    if not data.get("accept_privacy"):
        return jsonify({"error": "Tu dois accepter la politique de confidentialité.", "field": "accept_privacy"}), 400

    if db.get_user_by_email(email):
        return jsonify({"error": "Cette adresse email est déjà utilisée.", "field": "email"}), 409
    if db.get_user_by_username(username):
        return jsonify({"error": "Ce nom d'utilisateur est déjà pris.", "field": "username"}), 409

    # Capturé avant la création du nouveau compte : si l'utilisateur était en
    # mode invité, on lui propose de conserver sa progression temporaire.
    previous_user = get_current_user()
    was_guest = bool(previous_user) and previous_user["auth_provider"] == "guest"
    transfer_guest = was_guest and bool(data.get("transfer_guest"))

    password_hash = hash_password(password)
    user_id = db.create_user(email, username, pseudo, password_hash)
    if transfer_guest:
        _transfer_guest_data(previous_user, user_id)
    else:
        _migrate_legacy_stats_if_first_user(user_id)
        # Si l'invité a choisi "Non" (ne pas conserver sa progression), son
        # compte éphémère n'a plus aucune raison de traîner en base jusqu'au
        # nettoyage paresseux de db.cleanup_expired_guests() — autant le
        # supprimer tout de suite.
        if was_guest:
            _purge_account(previous_user["id"])

    token = db.create_session(user_id, days=REMEMBER_DAYS, user_agent=request.headers.get("User-Agent"))
    db.update_last_login(user_id)
    user = db.get_user_by_id(user_id)

    # La progression d'évaluation/entraînement en cours (session Flask signée,
    # distincte de nm_session) n'est pas liée à un compte : sans ce reset, un
    # quiz commencé avant l'inscription (ou par un compte précédent sur ce
    # même navigateur) pourrait continuer à alimenter le nouveau compte.
    session.clear()
    _log_security_event("account_created", user_id=user_id)

    resp = jsonify({"user": _public_user(user)})
    _set_session_cookie(resp, token, REMEMBER_DAYS)
    _set_csrf_cookie(resp)
    return resp, 201


@auth_bp.route("/login", methods=["POST"])
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
    _log_security_event("login_failed" if not ok else "login_success", user_id=user["id"] if (user and ok) else None)

    if not ok:
        return jsonify({"error": "Email ou mot de passe incorrect."}), 401

    if needs_rehash(user["password_hash"]):
        db.set_password_hash(user["id"], hash_password(password))

    days = REMEMBER_DAYS if remember else DEFAULT_DAYS
    token = db.create_session(user["id"], days=days, user_agent=request.headers.get("User-Agent"))
    db.update_last_login(user["id"])
    user = db.get_user_by_id(user["id"])

    session.clear()  # même raison qu'à l'inscription — voir commentaire dans register()

    resp = jsonify({"user": _public_user(user)})
    _set_session_cookie(resp, token, days)
    _set_csrf_cookie(resp)
    return resp


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


@auth_bp.route("/2fa/enable", methods=["POST"])
@login_required
@csrf_protect
def enable_2fa():
    """Architecture prête (route + emplacement UI dans les paramètres) mais non
    implémentée — même pattern honnête que oauth_start()/oauth_callback() pour
    les fournisseurs non configurés : jamais de flux qui semble fonctionner
    sans réellement sécuriser le compte."""
    return jsonify({
        "error": "L'authentification à deux facteurs n'est pas encore disponible.",
        "detail": "Architecture prête (route /api/auth/2fa/enable) — l'envoi de codes TOTP/SMS reste à implémenter.",
    }), 501


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
    _purge_account(user["id"], email=user["email"])

    session.clear()
    resp = jsonify({"ok": True})
    resp.delete_cookie(SESSION_COOKIE)
    resp.delete_cookie(CSRF_COOKIE)
    return resp


@auth_bp.route("/forgot-password", methods=["POST"])
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
    params = (
        f"client_id={os.environ[cfg['client_id_env']]}"
        f"&redirect_uri={request.url_root}api/auth/{provider}/callback"
        f"&response_type=code&scope={cfg['scope']}&access_type=offline&prompt=consent"
    )
    return redirect(f"{cfg['authorize_url']}?{params}")


@auth_bp.route("/<provider>/callback")
def oauth_callback(provider):
    if provider not in OAUTH_PROVIDERS or not _provider_configured(provider):
        return jsonify({"error": "Fournisseur non configuré."}), 501
    # L'échange code -> token -> userinfo sera implémenté ici une fois les
    # identifiants fournis (nécessite des appels HTTP sortants ; non branché
    # tant que GOOGLE_CLIENT_ID/SECRET ne sont pas définis, pour ne jamais
    # exposer un flux qui semble fonctionner sans réellement authentifier).
    return jsonify({"error": "Échange OAuth non implémenté sans identifiants configurés."}), 501
