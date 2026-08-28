"""
Authentification à deux facteurs (2FA) — TOTP, RFC 6238 — pour NovaMath.
SEC-03 : remplace l'ancien stub non fonctionnel de POST /api/auth/2fa/enable.

Architecture stricte, identique à plan_service.py/quota_service.py/
role_service.py/rate_limit_service.py :

    auth.py  →  two_factor_service.py  →  db.py

jamais l'inverse. Ce module reçoit un `user` déjà chargé (même convention que
plan_service.py/quota_service.py — aucune requête sur la table `users` en
dehors de db.py) et contient TOUTE la logique métier 2FA : génération du
secret, chiffrement, QR code, vérification TOTP (avec protection anti-rejeu),
recovery codes, verrouillage temporaire après échecs répétés. auth.py ne fait
que traduire HTTP <-> appels à ce module (comme pour tous les autres
services), exactement le même contrat que billing_service.py vis-à-vis de
stripe_service.py.

Ne réimplémente jamais l'algorithme TOTP : délègue entièrement à `pyotp`
(RFC 6238) et `qrcode` — génère un vrai otpauth:// URI, compatible avec
n'importe quelle application TOTP standard (Google Authenticator, Microsoft
Authenticator, Authy, 1Password, Bitwarden...), aucune n'ayant de spécificité
propriétaire au-delà du standard.

Secret jamais stocké en clair : chiffré avec Fernet (cryptography.fernet),
clé = TWO_FACTOR_SECRET_KEY (config.py, uniquement depuis l'environnement).
Recovery codes hachés avec SHA-256 (hashlib, stdlib) plutôt qu'Argon2 (utilisé
pour les mots de passe, voir auth.py::hash_password) : un recovery code est
un jeton à haute entropie généré par `secrets` (jamais choisi par
l'utilisateur, donc jamais vulnérable à une attaque par dictionnaire) — un
hachage cryptographique rapide suffit, même principe que le hachage des
jetons d'API personnels chez GitHub/GitLab. Argon2 (lent, memory-hard) n'a
d'intérêt que contre des mots de passe faibles/devinables.
"""
import base64
import hashlib
import io
import logging
import re
import secrets
import time

import pyotp
import qrcode
from cryptography.fernet import Fernet, InvalidToken

import config
import db

logger = logging.getLogger("two_factor_service")

# ── Paramètres ────────────────────────────────────────────────────────────────
RECOVERY_CODE_COUNT = 10
TOTP_STEP_SECONDS = 30
# Tolérance d'une fenêtre de 30s avant/après l'heure serveur — absorbe une
# petite dérive d'horloge côté client sans élargir excessivement la fenêtre
# de validité (recommandation RFC 6238 §5.2).
TOTP_VALID_WINDOWS = 1
_CODE_RE = re.compile(r"^\d{6}$")

# Verrouillage temporaire après codes invalides répétés (Partie SÉCURITÉ) —
# mêmes valeurs que le verrouillage par mot de passe (voir
# auth.py::MAX_LOGIN_ATTEMPTS/LOCKOUT_MINUTES), pour un comportement cohérent
# et prévisible entre les deux mécanismes de protection du compte.
MAX_ATTEMPTS = 5
LOCKOUT_MINUTES = 15

CHALLENGE_TTL_MINUTES = 5


class TwoFactorNotConfigured(Exception):
    """Levée quand TWO_FACTOR_SECRET_KEY est absente ou invalide côté serveur
    — même famille que stripe_service.StripeNotConfigured : jamais une
    exception qui remonte en 500 générique, toujours traduite par auth.py en
    réponse HTTP explicite (501)."""


class TwoFactorAlreadyEnabled(Exception):
    """Levée par begin_setup()/confirm_setup() quand la 2FA est déjà active —
    il faut la désactiver avant d'en reconfigurer une nouvelle."""


class TwoFactorNotEnabled(Exception):
    """Levée par disable()/verify_login_challenge() quand la 2FA n'est pas
    (ou plus) active sur le compte concerné."""


class NoPendingSetup(Exception):
    """Levée par confirm_setup() quand aucun /2fa/setup n'a été appelé avant
    (aucun secret en attente de confirmation)."""


class InvalidTotpCode(Exception):
    """Code TOTP à 6 chiffres invalide, expiré, ou déjà utilisé (rejeu).
    `user_id` (optionnel) : renseigné par verify_login_challenge()/disable()
    quand le compte concerné est déjà connu, pour que l'appelant (auth.py)
    puisse journaliser l'échec sous le bon utilisateur — sans ça, le
    verrouillage temporaire (voir _ensure_not_locked_out, qui compte les
    échecs PAR utilisateur) ne pourrait jamais se déclencher côté connexion."""

    def __init__(self, message, user_id=None):
        self.user_id = user_id
        super().__init__(message)


class InvalidRecoveryCode(Exception):
    """Recovery code inconnu ou déjà consommé. `user_id` : voir InvalidTotpCode."""

    def __init__(self, message, user_id=None):
        self.user_id = user_id
        super().__init__(message)


class InvalidChallenge(Exception):
    """Jeton de défi de connexion (voir create_login_challenge) inconnu,
    expiré, ou déjà résolu."""


class TooManyAttempts(Exception):
    """Verrouillage temporaire après trop de codes invalides — voir
    MAX_ATTEMPTS/LOCKOUT_MINUTES."""

    def __init__(self, retry_after_minutes):
        self.retry_after_minutes = retry_after_minutes
        super().__init__(f"Trop de tentatives échouées. Réessaie dans {retry_after_minutes} minutes.")


# ── Chiffrement du secret (Fernet, clé depuis l'environnement uniquement) ─────
def _fernet():
    key = config.TWO_FACTOR_SECRET_KEY
    if not key:
        raise TwoFactorNotConfigured("TWO_FACTOR_SECRET_KEY n'est pas configurée sur ce serveur.")
    try:
        return Fernet(key.encode() if isinstance(key, str) else key)
    except (ValueError, TypeError) as e:
        raise TwoFactorNotConfigured(f"TWO_FACTOR_SECRET_KEY invalide : {e}") from e


def _encrypt_secret(raw_secret):
    return _fernet().encrypt(raw_secret.encode()).decode()


def _decrypt_secret(encrypted_secret):
    try:
        return _fernet().decrypt(encrypted_secret.encode()).decode()
    except InvalidToken as e:
        # Clé de chiffrement changée depuis, ou donnée corrompue : jamais une
        # exception brute de la lib crypto qui remonterait jusqu'à l'appelant.
        raise TwoFactorNotConfigured(
            "Secret 2FA illisible avec la clé de chiffrement actuelle."
        ) from e


# ── Recovery codes ──────────────────────────────────────────────────────────
def _hash_recovery_code(code):
    return hashlib.sha256(code.encode()).hexdigest()


def _generate_recovery_codes(count=RECOVERY_CODE_COUNT):
    """Codes lisibles, groupés par blocs de 4 (ex: "a1b2-c3d4-e5f6-a7b8") —
    8 octets aléatoires par code (secrets.token_hex, cryptographiquement sûr,
    64 bits d'entropie), largement suffisant pour un jeton à usage unique
    jamais devinable par force brute."""
    codes = []
    for _ in range(count):
        raw = secrets.token_hex(8)  # 16 caractères hexadécimaux
        codes.append("-".join(raw[i:i + 4] for i in range(0, 16, 4)))
    return codes


def recovery_codes_remaining(user):
    return db.count_recovery_codes(user["id"])


# ── TOTP ─────────────────────────────────────────────────────────────────────
def _totp(raw_secret):
    return pyotp.TOTP(raw_secret, interval=TOTP_STEP_SECONDS)


def provisioning_uri(raw_secret, email):
    """URI otpauth:// standard (RFC 6238 / Key URI Format Google), lu par
    n'importe quelle application TOTP (Google/Microsoft Authenticator, Authy,
    1Password, Bitwarden...) — aucune n'a besoin d'un format propriétaire."""
    return _totp(raw_secret).provisioning_uri(name=email, issuer_name=config.TWO_FACTOR_ISSUER)


def generate_qr_code_data_uri(otpauth_uri):
    """PNG encodé en data URI (`data:image/png;base64,...`), directement
    utilisable dans un attribut `src` d'`<img>` côté frontend — aucun fichier
    écrit sur disque, aucune route de téléchargement séparée nécessaire."""
    img = qrcode.make(otpauth_uri)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return f"data:image/png;base64,{base64.b64encode(buf.getvalue()).decode()}"


def _totp_counter_now():
    return int(time.time() / TOTP_STEP_SECONDS)


def _verify_totp_code(raw_secret, code, last_counter):
    """Vérifie `code` contre `raw_secret` sur la fenêtre de tolérance
    [-1, 0, +1] pas de 30s. Renvoie (True, nouveau_compteur) si valide ET pas
    déjà utilisé ; (False, last_counter) sinon — un code dont le pas est
    <= last_counter est refusé même s'il reste mathématiquement correct dans
    sa fenêtre de validité (protection anti-rejeu : un même code à 6 chiffres
    ne peut jamais être accepté deux fois, voir la colonne
    users.two_factor_last_counter)."""
    if not code or not _CODE_RE.match(code):
        return False, last_counter
    totp = _totp(raw_secret)
    now_counter = _totp_counter_now()
    for offset in range(-TOTP_VALID_WINDOWS, TOTP_VALID_WINDOWS + 1):
        counter = now_counter + offset
        # TOTP.at() attend un timestamp (secondes), pas le compteur de pas
        # brut — reconvertir explicitement (counter * intervalle), sinon
        # pyotp redivise en interne et compare le mauvais pas.
        if totp.at(counter * TOTP_STEP_SECONDS) != code:
            continue
        if last_counter is not None and counter <= last_counter:
            return False, last_counter
        return True, counter
    return False, last_counter


# ── Verrouillage temporaire (échecs répétés) ──────────────────────────────────
def _ensure_not_locked_out(user_id):
    failures = db.count_recent_two_factor_failures(user_id, minutes=LOCKOUT_MINUTES)
    if failures >= MAX_ATTEMPTS:
        raise TooManyAttempts(LOCKOUT_MINUTES)


# ── Activation ───────────────────────────────────────────────────────────────
def is_enabled(user):
    return bool(user.get("two_factor_enabled"))


def begin_setup(user):
    """Génère un nouveau secret TOTP, le chiffre et le stocke — SANS activer
    la 2FA (voir confirm_setup, seule fonction qui active réellement).
    Rappelable plusieurs fois : chaque appel remplace le secret en attente
    (l'ancien, jamais confirmé, devient caduc). Renvoie de quoi construire
    l'écran de configuration : secret en clair (saisie manuelle, filet de
    secours si le QR code ne peut pas être scanné), URI otpauth://, QR code."""
    if is_enabled(user):
        raise TwoFactorAlreadyEnabled("La 2FA est déjà active sur ce compte.")

    raw_secret = pyotp.random_base32()
    db.set_two_factor_secret(user["id"], _encrypt_secret(raw_secret))
    uri = provisioning_uri(raw_secret, user["email"])
    logger.info("2FA : configuration initiée pour l'utilisateur %s.", user["id"])
    return {"secret": raw_secret, "otpauth_uri": uri, "qr_code": generate_qr_code_data_uri(uri)}


def confirm_setup(user, code):
    """Vérifie le premier code TOTP et, seulement s'il est valide, active
    définitivement la 2FA + génère les recovery codes (renvoyés UNE SEULE
    FOIS en clair, jamais récupérables ensuite — seuls leurs hachages sont
    conservés). Ne modifie rien si le code est invalide."""
    if is_enabled(user):
        raise TwoFactorAlreadyEnabled("La 2FA est déjà active sur ce compte.")
    encrypted_secret = user.get("two_factor_secret")
    if not encrypted_secret:
        raise NoPendingSetup("Aucune configuration 2FA en attente — appelle /2fa/setup d'abord.")

    raw_secret = _decrypt_secret(encrypted_secret)
    ok, counter = _verify_totp_code(raw_secret, code, last_counter=None)
    if not ok:
        logger.warning("2FA : code invalide lors de l'activation pour l'utilisateur %s.", user["id"])
        raise InvalidTotpCode("Code de vérification invalide.")

    db.enable_two_factor(user["id"])
    db.set_two_factor_last_counter(user["id"], counter)
    recovery_codes = _generate_recovery_codes()
    db.replace_recovery_codes(user["id"], [_hash_recovery_code(c) for c in recovery_codes])
    logger.info("2FA : activée pour l'utilisateur %s.", user["id"])
    return recovery_codes


def disable(user, code):
    """Désactive la 2FA après vérification du code TOTP (le mot de passe est
    vérifié par l'appelant, voir auth.py::disable_2fa — deux facteurs
    indépendants requis, aucun des deux n'est du ressort de ce module seul).
    Supprime le secret ET tous les recovery codes restants."""
    if not is_enabled(user):
        raise TwoFactorNotEnabled("La 2FA n'est pas active sur ce compte.")
    _ensure_not_locked_out(user["id"])

    raw_secret = _decrypt_secret(user["two_factor_secret"])
    ok, _ = _verify_totp_code(raw_secret, code, user.get("two_factor_last_counter"))
    if not ok:
        logger.warning("2FA : code invalide lors d'une tentative de désactivation pour l'utilisateur %s.", user["id"])
        raise InvalidTotpCode("Code de vérification invalide.", user_id=user["id"])

    db.disable_two_factor(user["id"])
    db.delete_all_recovery_codes(user["id"])
    logger.info("2FA : désactivée pour l'utilisateur %s.", user["id"])


# ── Connexion (défi 2FA) ───────────────────────────────────────────────────────
def create_login_challenge(user, remember):
    """Appelée par auth.py::login() une fois email+mot de passe validés, si
    la 2FA est active : AUCUNE session n'est créée ici, seulement un jeton de
    défi à courte durée de vie que le client doit résoudre via
    verify_login_challenge()/verify_recovery_challenge()."""
    token = db.create_two_factor_challenge(user["id"], remember, minutes=CHALLENGE_TTL_MINUTES)
    logger.info("2FA : défi de connexion émis pour l'utilisateur %s.", user["id"])
    return token


def _load_challenge(challenge_token):
    challenge = db.get_two_factor_challenge(challenge_token)
    if challenge is None:
        raise InvalidChallenge("Ce défi de connexion est invalide ou a expiré.")
    return challenge


def verify_login_challenge(challenge_token, code):
    """Résout un défi de connexion avec un code TOTP. Renvoie (user, remember)
    si valide ; lève InvalidChallenge/TwoFactorNotEnabled/TooManyAttempts/
    InvalidTotpCode sinon. Le jeton n'est consommé (supprimé) qu'en cas de
    succès — un code invalide laisse le défi réutilisable jusqu'à son
    expiration naturelle ou le verrouillage temporaire."""
    challenge = _load_challenge(challenge_token)
    user_id = challenge["user_id"]
    _ensure_not_locked_out(user_id)

    user = db.get_user_by_id(user_id)
    if user is None or not is_enabled(user):
        raise TwoFactorNotEnabled("La 2FA n'est plus active sur ce compte.")

    raw_secret = _decrypt_secret(user["two_factor_secret"])
    ok, counter = _verify_totp_code(raw_secret, code, user.get("two_factor_last_counter"))
    if not ok:
        logger.warning("2FA : code invalide lors d'une connexion pour l'utilisateur %s.", user_id)
        raise InvalidTotpCode("Code de vérification invalide.", user_id=user_id)

    db.set_two_factor_last_counter(user_id, counter)
    db.delete_two_factor_challenge(challenge_token)
    logger.info("2FA : connexion validée par code TOTP pour l'utilisateur %s.", user_id)
    return user, bool(challenge["remember"])


def verify_recovery_challenge(challenge_token, recovery_code):
    """Résout un défi de connexion avec un recovery code (voir
    verify_login_challenge — même contrat). Le code est supprimé
    immédiatement après usage (à usage unique, voir SCHEMA), qu'il reste ou
    non d'autres codes disponibles."""
    challenge = _load_challenge(challenge_token)
    user_id = challenge["user_id"]
    _ensure_not_locked_out(user_id)

    user = db.get_user_by_id(user_id)
    if user is None or not is_enabled(user):
        raise TwoFactorNotEnabled("La 2FA n'est plus active sur ce compte.")

    recovery_code = (recovery_code or "").strip()
    consumed = bool(recovery_code) and db.consume_recovery_code(user_id, _hash_recovery_code(recovery_code))
    if not consumed:
        logger.warning("2FA : recovery code invalide lors d'une connexion pour l'utilisateur %s.", user_id)
        raise InvalidRecoveryCode("Recovery code invalide ou déjà utilisé.", user_id=user_id)

    db.delete_two_factor_challenge(challenge_token)
    logger.info("2FA : connexion validée par recovery code pour l'utilisateur %s (%s restant(s)).",
                user_id, db.count_recovery_codes(user_id))
    return user, bool(challenge["remember"])
