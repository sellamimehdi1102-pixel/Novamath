"""
Source unique de vérité des rôles d'équipe (autorisations d'administration)
pour NovaMath.

Architecture stricte, identique à plan_service.py/quota_service.py :

    server.py  →  role_service.py  →  db.py

jamais l'inverse. Ce module reçoit un `user` déjà chargé (dict tel que
renvoyé par db.get_user_by_id/get_current_user), exactement comme
plan_service.py — aucune requête SQL sur la table `users` ici en dehors de
sync_admin_bootstrap (qui délègue l'écriture à db.set_user_role, jamais de
SQL direct dans ce module).

Distinct de plan_service.py : Plan/Feature gouvernent ce qu'un ABONNÉ peut
faire (Free/Premium/Ultra) ; Role gouverne ce qu'un MEMBRE DE L'ÉQUIPE peut
faire (tableau de bord développeur, modération, futurs outils internes),
indépendamment de son plan. Un compte peut être Role.ADMIN et Plan.FREE en
même temps — les deux colonnes (`role`, `plan`) sont orthogonales.

Règle du projet : aucune comparaison directe de rôle ailleurs
(`user["role"] == "admin"`) — toujours passer par get_role()/
has_role_at_least()/requires_role() ci-dessous.
"""
import os
from enum import Enum
from functools import wraps
from typing import Callable, Optional

from flask import jsonify, request

import db


class Role(Enum):
    USER = "user"
    SUPPORT = "support"
    MODERATOR = "moderator"
    ADMIN = "admin"
    SUPER_ADMIN = "super_admin"

    @classmethod
    def from_value(cls, value: Optional[str]) -> "Role":
        """Traduit une valeur brute (colonne users.role) en Role, en
        dégradant silencieusement vers USER pour toute valeur inconnue,
        absente ou corrompue — jamais d'exception pour un simple champ mal
        renseigné (même philosophie que Plan.from_value)."""
        for role in cls:
            if role.value == value:
                return role
        return cls.USER

    @classmethod
    def parse(cls, value) -> Optional["Role"]:
        """Variante stricte de from_value, pour valider une entrée externe
        non fiable : renvoie None si `value` ne correspond à aucun rôle
        connu, plutôt que de dégrader silencieusement vers USER."""
        for role in cls:
            if role.value == value:
                return role
        return None


# Ordre croissant de privilège — chaque rôle satisfait toute exigence posée
# pour un rôle qui le précède dans ce tuple (ex: ADMIN satisfait une
# exigence MODERATOR). Seul point du projet qui connaît la hiérarchie ;
# ne jamais comparer deux Role autrement que via has_role_at_least().
_ROLE_ORDER = (Role.USER, Role.SUPPORT, Role.MODERATOR, Role.ADMIN, Role.SUPER_ADMIN)


def get_role(user: Optional[dict]) -> Role:
    """Rôle effectif d'un utilisateur. `user` peut être None (invité non
    connecté, appel défensif) : traité comme USER, jamais une exception."""
    if not user:
        return Role.USER
    return Role.from_value(user.get("role"))


def has_role_at_least(user: Optional[dict], minimum: Role) -> bool:
    """True si le rôle effectif de `user` est `minimum` ou un rôle plus
    privilégié dans _ROLE_ORDER."""
    return _ROLE_ORDER.index(get_role(user)) >= _ROLE_ORDER.index(minimum)


def is_staff(user: Optional[dict]) -> bool:
    """True pour tout rôle interne (strictement au-dessus de USER) — utile
    pour une vérification générique ("fait-il partie de l'équipe ?") sans se
    soucier du rôle précis."""
    return get_role(user) is not Role.USER


def requires_role(minimum: Role) -> Callable:
    """Décorateur de route Flask : renvoie 403 si l'utilisateur courant n'a
    pas au moins le rôle `minimum` (voir _ROLE_ORDER). Doit être posé APRÈS
    @login_required dans la pile de décorateurs (donc en dessous, plus
    proche de la fonction), pour que request.current_user soit déjà
    renseigné quand ce décorateur s'exécute :

        @app.route(...)
        @login_required
        @requires_role(Role.ADMIN)
        def view():
            ...

    Toute future route interne/admin se protège de la même façon, en
    changeant uniquement `minimum` — aucune duplication de logique
    d'autorisation. Réponse 403 volontairement minimale (même format que les
    autres erreurs d'autorisation du projet, voir plan_service.requires_
    feature et server.py::api_review_pin) : jamais de détail sur la nature
    des données protégées, jamais d'exception non interceptée (donc jamais
    de 500) qui laisserait deviner l'existence d'une ressource interne."""
    def decorator(view):
        @wraps(view)
        def wrapped(*args, **kwargs):
            user = getattr(request, "current_user", None)
            if not has_role_at_least(user, minimum):
                return jsonify({"error": "Réservé à l'administrateur."}), 403
            return view(*args, **kwargs)
        return wrapped
    return decorator


def _admin_emails_from_env() -> frozenset:
    """Liste d'emails séparés par des virgules dans NOVAMATH_ADMIN_EMAILS
    (voir .env.example) — jamais codée en dur, même convention que
    NOVAMATH_ADMIN_KEY/NOVAMATH_SECRET_KEY (server.py::_get_or_create_secret).
    Absente ou vide : aucun bootstrap, comportement par défaut inchangé."""
    raw = os.environ.get("NOVAMATH_ADMIN_EMAILS", "")
    return frozenset(e.strip().lower() for e in raw.split(",") if e.strip())


def sync_admin_bootstrap(user: dict) -> dict:
    """Promeut automatiquement en Role.ADMIN tout compte dont l'email figure
    dans NOVAMATH_ADMIN_EMAILS — bootstrap du tout premier administrateur
    sans outil de gestion des rôles séparé (aucun n'existe encore dans ce
    projet) ni valeur codée en dur. N'agit qu'à la hausse : ne rétrograde
    jamais un rôle déjà égal ou supérieur à ADMIN (ex: un SUPER_ADMIN promu
    manuellement en base n'est jamais redescendu). Idempotent : sans effet
    une fois le rôle déjà à jour.

    Appelé à chaque connexion locale réussie (voir auth.py::register/login) —
    jamais pour un compte invité (auth_provider='guest'), qui n'a par
    construction aucune chance de figurer dans NOVAMATH_ADMIN_EMAILS.
    Renvoie le `user` (éventuellement mis à jour) pour que l'appelant reflète
    immédiatement le nouveau rôle sans requête SQL supplémentaire."""
    email = (user.get("email") or "").lower()
    if not email or email not in _admin_emails_from_env():
        return user
    if has_role_at_least(user, Role.ADMIN):
        return user
    db.set_user_role(user["id"], Role.ADMIN.value)
    return {**user, "role": Role.ADMIN.value}
