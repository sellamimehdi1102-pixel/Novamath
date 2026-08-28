"""
Owner/Developer Override — NovaMath.

Mécanisme technique isolé du système commercial (Stripe / plan_service.py /
quota_service.py / role_service.py restent, pour TOUT LE MONDE d'autre, la
seule source de vérité — ce module ne modifie ni ne remplace la matrice
commerciale, il fournit uniquement un point de décision central que
plan_service.py/quota_service.py/provider_manager.py peuvent consulter en
plus de leurs règles habituelles).

Fail-closed par construction : si `NOVAMATH_OWNER_USER_ID` est absent ou
invalide, `is_owner_account()` renvoie toujours False, pour tout compte,
y compris un futur super_admin ou un compte Ultra payant — Role
(role_service.py, accès équipe/panneau admin) et Plan (plan_service.py,
abonnement commercial) restent des concepts totalement orthogonaux à
"owner" : être ADMIN, SUPER_ADMIN ou payer Ultra ne donne JAMAIS ce
privilège, seul l'id configuré ici le donne.

Ne JAMAIS déterminer ce statut depuis une donnée fournie par le frontend
(email/plan/rôle envoyés dans une requête) — uniquement depuis
`user["id"]`, déjà chargé côté serveur depuis la session authentifiée (voir
auth.py::get_current_user), comparé à un entier lu depuis l'environnement
serveur (jamais configurable côté client).
"""
import logging
import os
from functools import wraps

from flask import jsonify, request

logger = logging.getLogger("owner_service")

_ENV_VAR = "NOVAMATH_OWNER_USER_ID"


def _owner_user_id():
    """Lit et parse NOVAMATH_OWNER_USER_ID à chaque appel (pas de cache
    process — cohérent avec le reste du projet, ex. role_service._emails_from_
    env, pour qu'un changement de variable d'environnement en dev soit pris en
    compte sans redémarrage forcé du process Python). None si absente ou non
    parsable en entier — jamais une valeur devinée ou par défaut."""
    raw = os.environ.get(_ENV_VAR)
    if not raw:
        return None
    try:
        return int(raw)
    except (TypeError, ValueError):
        logger.warning("%s invalide (%r) — override owner désactivé.", _ENV_VAR, raw)
        return None


def is_owner_account(user):
    """True UNIQUEMENT si `user["id"]` correspond exactement à
    NOVAMATH_OWNER_USER_ID. `user` est le dict déjà chargé côté serveur
    (même convention que plan_service.get_plan/quota_service.get_limit —
    aucune requête SQL ici). Fail-closed : variable absente/invalide ou
    `user` vide/None → False, sans exception."""
    if not user:
        return False
    owner_id = _owner_user_id()
    if owner_id is None:
        return False
    return user.get("id") == owner_id


def owner_only(view):
    """Décorateur de route Flask : 404 (jamais 403) si l'utilisateur courant
    n'est pas le compte owner — un 404 plutôt qu'un 403 pour ne même pas
    révéler l'existence de la route à un autre compte (y compris un autre
    super_admin), conformément au fail-closed de ce module. Doit être posé
    APRÈS @login_required (donc en dessous, plus proche de la fonction), pour
    que request.current_user soit déjà renseigné :

        @app.route(...)
        @login_required
        @owner_service.owner_only
        def view():
            ...

    N'utilise QUE is_owner_account(request.current_user) — jamais role/
    email/plan, jamais une donnée envoyée par le frontend."""
    @wraps(view)
    def wrapped(*args, **kwargs):
        user = getattr(request, "current_user", None)
        if not is_owner_account(user):
            return jsonify({"error": "not_found"}), 404
        return view(*args, **kwargs)
    return wrapped
