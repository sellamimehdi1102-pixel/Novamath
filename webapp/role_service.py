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


def _emails_from_env(env_name: str) -> frozenset:
    """Liste d'emails séparés par des virgules dans la variable d'environnement
    `env_name` — jamais codée en dur, même convention que
    NOVAMATH_ADMIN_KEY/NOVAMATH_SECRET_KEY (server.py::_get_or_create_secret).
    Absente ou vide : ensemble vide, aucun bootstrap déclenché."""
    raw = os.environ.get(env_name, "")
    return frozenset(e.strip().lower() for e in raw.split(",") if e.strip())


def _admin_emails_from_env() -> frozenset:
    """Voir NOVAMATH_ADMIN_EMAILS dans .env.example."""
    return _emails_from_env("NOVAMATH_ADMIN_EMAILS")


def _super_admin_emails_from_env() -> frozenset:
    """Voir NOVAMATH_SUPER_ADMIN_EMAILS dans .env.example — même mécanisme que
    NOVAMATH_ADMIN_EMAILS ci-dessus, pour un palier de privilège distinct
    (SUPER_ADMIN plutôt qu'ADMIN). Variable séparée volontairement : un email
    peut figurer dans l'une sans figurer dans l'autre, les deux listes ne
    sont jamais fusionnées."""
    return _emails_from_env("NOVAMATH_SUPER_ADMIN_EMAILS")


def _bootstrap_role_from_env(user: dict, emails: frozenset, target_role: Role) -> dict:
    """Promeut automatiquement `user` vers `target_role` si son email figure
    dans `emails`. N'agit qu'à la hausse : ne rétrograde jamais un rôle déjà
    égal ou supérieur à `target_role` (ex: un SUPER_ADMIN promu manuellement
    en base, ou déjà promu par un appel précédent, n'est jamais redescendu).
    Idempotent : sans effet une fois le rôle déjà à jour. Renvoie le `user`
    (éventuellement mis à jour) pour que l'appelant reflète immédiatement le
    nouveau rôle sans requête SQL supplémentaire."""
    email = (user.get("email") or "").lower()
    if not email or email not in emails:
        return user
    if has_role_at_least(user, target_role):
        return user
    db.set_user_role(user["id"], target_role.value)
    return {**user, "role": target_role.value}


def sync_admin_bootstrap(user: dict) -> dict:
    """Promeut automatiquement en Role.ADMIN tout compte dont l'email figure
    dans NOVAMATH_ADMIN_EMAILS — bootstrap du tout premier administrateur
    sans outil de gestion des rôles séparé (aucun n'existe encore dans ce
    projet) ni valeur codée en dur.

    Appelé à chaque connexion locale réussie (voir auth.py::register/
    _create_authenticated_session) — jamais pour un compte invité
    (auth_provider='guest'), qui n'a par construction aucune chance de
    figurer dans NOVAMATH_ADMIN_EMAILS."""
    return _bootstrap_role_from_env(user, _admin_emails_from_env(), Role.ADMIN)


def sync_super_admin_bootstrap(user: dict) -> dict:
    """Même principe que sync_admin_bootstrap, pour NOVAMATH_SUPER_ADMIN_EMAILS
    et Role.SUPER_ADMIN — appelé aux mêmes points d'entrée (register/
    _create_authenticated_session), juste après sync_admin_bootstrap.
    L'ordre entre les deux appels est sans importance : chacun ne promeut
    qu'à la hausse et ignore silencieusement tout compte non listé dans SA
    propre variable d'environnement."""
    return _bootstrap_role_from_env(user, _super_admin_emails_from_env(), Role.SUPER_ADMIN)


def sync_super_admin_bootstrap_for_configured_emails() -> None:
    """Applique sync_super_admin_bootstrap() à chaque email de
    NOVAMATH_SUPER_ADMIN_EMAILS qui correspond DÉJÀ à un compte existant en
    base — couvre le cas où le compte a été créé avant que cette variable ne
    soit configurée (ou avant un redémarrage du serveur), sans attendre sa
    prochaine connexion. Sûre à appeler à chaque démarrage du serveur (voir
    server.py) : no-op silencieux pour tout email absent de la table `users`
    ou déjà au rôle SUPER_ADMIN — jamais d'exception, jamais de création de
    compte."""
    for email in _super_admin_emails_from_env():
        user = db.get_user_by_email(email)
        if user is not None:
            sync_super_admin_bootstrap(user)
