"""
Source unique de vérité des droits utilisateur (Feature Flags) pour NovaMath.

Architecture stricte :

    server.py  →  plan_service.py  →  db.py

jamais l'inverse. Ce module ne dépend ni de Stripe ni de auth.py — il reçoit
un `user` déjà chargé (dict tel que renvoyé par db.get_user_by_id/
get_current_user/get_session_user), exactement comme le reste du projet
(auth.py::write_user_stats, _public_user, etc. prennent tous un `user` déjà
en main plutôt que de re-fetcher). Aucune requête SQL ici.

Stripe (stripe_service.py/stripe_webhook_service.py) ne fait qu'écrire le
plan brut en base (colonne users.plan) suite à un événement webhook — il ne
décide jamais des accès. C'est CE module, et uniquement lui, qui décide à
quoi un utilisateur a droit à partir de cette donnée.

Règle du projet : aucune comparaison directe de plan ailleurs
(`user["plan"] == "premium"`, `plan == "ultra"`, ...) — toujours passer par
get_plan()/has_feature()/is_free()/is_premium()/is_ultra() ci-dessous.
"""
from enum import Enum
from functools import wraps

from flask import jsonify, request


class Plan(Enum):
    FREE = "free"
    PREMIUM = "premium"
    ULTRA = "ultra"

    @classmethod
    def from_value(cls, value):
        """Traduit une valeur brute (colonne users.plan) en Plan, en
        dégradant silencieusement vers FREE pour toute valeur inconnue,
        absente ou corrompue — jamais d'exception pour un simple champ mal
        renseigné (même philosophie que canonical_ids.py::resolve_chapter_id)."""
        for plan in cls:
            if plan.value == value:
                return plan
        return cls.FREE

    @classmethod
    def parse(cls, value):
        """Variante stricte de from_value, pour valider une entrée externe
        non fiable (ex: corps JSON d'une requête HTTP) : renvoie None si
        `value` ne correspond à aucun plan connu, plutôt que de dégrader
        silencieusement vers FREE (qui masquerait une faute de frappe côté
        client derrière un comportement qui semble fonctionner)."""
        for plan in cls:
            if plan.value == value:
                return plan
        return None


class Feature(Enum):
    CHATBOT = "chatbot"
    CHATBOT_UNLIMITED = "chatbot_unlimited"
    ADVANCED_AI = "advanced_ai"
    ADVANCED_EXPLANATIONS = "advanced_explanations"
    COURSES = "courses"
    EXERCISES = "exercises"
    CUSTOM_EXERCISES = "custom_exercises"
    STATISTICS = "statistics"
    HISTORY = "history"
    GOALS = "goals"
    EXPORT = "export"
    PROFILE_ANALYTICS = "profile_analytics"
    EARLY_ACCESS = "early_access"
    PRIORITY_QUEUE = "priority_queue"
    PRIORITY_SUPPORT = "priority_support"
    LONG_RESPONSES = "long_responses"


# ── Matrice centralisée ──────────────────────────────────────────────────────
# Unique endroit du projet qui sait "quel plan donne accès à quoi". Chaque
# palier reprend explicitement le précédent (union d'ensembles) : Premium
# inclut tout Free, Ultra inclut tout Premium — jamais de liste dupliquée à
# resynchroniser à la main entre paliers.
_FREE_FEATURES = frozenset({
    Feature.COURSES,
    Feature.EXERCISES,
    Feature.STATISTICS,
    Feature.HISTORY,
    Feature.GOALS,
    Feature.CHATBOT,
    Feature.EXPORT,
})

_PREMIUM_FEATURES = _FREE_FEATURES | frozenset({
    Feature.CHATBOT_UNLIMITED,
    Feature.ADVANCED_EXPLANATIONS,
    Feature.PROFILE_ANALYTICS,
    Feature.PRIORITY_SUPPORT,
})

_ULTRA_FEATURES = _PREMIUM_FEATURES | frozenset({
    Feature.ADVANCED_AI,
    Feature.CUSTOM_EXERCISES,
    Feature.EARLY_ACCESS,
    Feature.PRIORITY_QUEUE,
    Feature.LONG_RESPONSES,
})

FEATURE_MATRIX = {
    Plan.FREE: _FREE_FEATURES,
    Plan.PREMIUM: _PREMIUM_FEATURES,
    Plan.ULTRA: _ULTRA_FEATURES,
}


def get_plan(user):
    """Plan effectif d'un utilisateur. `user` peut être None (invité non
    connecté, appel défensif) : traité comme FREE, jamais une exception."""
    if not user:
        return Plan.FREE
    return Plan.from_value(user.get("plan"))


def list_features(plan):
    """Ensemble des Feature disponibles pour un Plan donné."""
    return FEATURE_MATRIX[plan]


def has_feature(user, feature):
    # Owner/Developer Override (voir owner_service.py) + Mode test Owner
    # (voir owner_test_plan_service.py) : pour le compte configuré via
    # NOVAMATH_OWNER_USER_ID UNIQUEMENT, les features suivent le plan
    # EFFECTIF (Plan.ULTRA par défaut si aucun plan de test n'est actif —
    # équivalent strict à l'ancien court-circuit "toujours True", puisque
    # FEATURE_MATRIX[ULTRA] couvre la totalité des Feature ; ou le plan de
    # test choisi sinon). Import différé pour éviter un import circulaire
    # (owner_test_plan_service importe Plan/list_features de ce module).
    # N'affecte jamais get_plan()/FEATURE_MATRIX ni les autres utilisateurs
    # (fail-closed par défaut, voir owner_service/owner_test_plan_service).
    import owner_test_plan_service
    plan = owner_test_plan_service.effective_plan(user)
    return feature in list_features(plan)


def is_free(user):
    return get_plan(user) is Plan.FREE


def is_premium(user):
    return get_plan(user) is Plan.PREMIUM


def is_ultra(user):
    return get_plan(user) is Plan.ULTRA


# Ordre croissant des paliers — sert à trouver le plan le moins élevé qui
# débloque une feature donnée (ex: proposer "Ultra" plutôt que "Premium" à un
# utilisateur déjà Premium qui heurte une feature réservée à Ultra).
_PLAN_ORDER = (Plan.FREE, Plan.PREMIUM, Plan.ULTRA)


def minimal_plan_for_feature(feature):
    """Plan le moins élevé qui inclut `feature`. Lève ValueError si `feature`
    n'apparaît dans aucun palier de FEATURE_MATRIX (erreur de programmation —
    toute Feature doit être rangée dans au moins Plan.ULTRA)."""
    for plan in _PLAN_ORDER:
        if feature in FEATURE_MATRIX[plan]:
            return plan
    raise ValueError(f"Feature absente de FEATURE_MATRIX : {feature!r}")


def requires_feature(feature):
    """Décorateur de route Flask : renvoie 403 si l'utilisateur courant n'a
    pas `feature`. Doit être posé APRÈS @login_required dans la pile de
    décorateurs (donc en dessous, plus proche de la fonction), pour que
    request.current_user soit déjà renseigné quand ce décorateur s'exécute :

        @app.route(...)
        @login_required
        @requires_feature(Feature.CHATBOT_UNLIMITED)
        def view():
            ...

    Réponse 403 au format attendu par le frontend (abonnement.js lit
    `required_plan` pour savoir quelle carte mettre en avant — Premium ou
    Ultra) :

        {"error": "premium_required", "feature": "...", "required_plan": "..."}
    """
    def decorator(view):
        @wraps(view)
        def wrapped(*args, **kwargs):
            user = getattr(request, "current_user", None)
            if user is None or not has_feature(user, feature):
                return jsonify({
                    "error": "premium_required",
                    "feature": feature.value,
                    "required_plan": minimal_plan_for_feature(feature).value,
                }), 403
            return view(*args, **kwargs)
        return wrapped
    return decorator
