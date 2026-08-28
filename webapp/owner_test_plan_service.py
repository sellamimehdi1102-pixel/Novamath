"""
Mode test Owner — simulation locale de plan d'abonnement, réservée
exclusivement au compte configuré via NOVAMATH_OWNER_USER_ID (voir
owner_service.py). Chantier 2026-08-23, complément de l'Owner/Developer
Override existant (accès illimité par défaut) : permet à CE SEUL compte de
choisir un « plan de test » (FREE/PREMIUM/ULTRA) pour observer le
comportement réel du reste de l'application (features/quotas/routage IA)
SANS jamais toucher à `users.plan`, à Stripe, ni affecter le moindre autre
utilisateur.

Architecture stricte (voir CLAUDE.md/discussion de conception) :

    is_owner_account(user)  →  effective_plan(user)  →  features / provider

et séparément :

    owner_unlimited_quotas(user)

Ces deux notions ne se mélangent JAMAIS : `effective_plan()` détermine les
features et le routage IA ; `owner_unlimited_quotas()` détermine UNIQUEMENT
si quota_service.get_limit() doit rester illimité malgré un plan de test
actif — pour pouvoir tester le comportement fonctionnel d'un plan sans être
bloqué par ses quotas, tout en gardant la possibilité de désactiver ce
filet pour observer aussi les vraies limites numériques.

Fail-closed par construction, comme owner_service.py : si `user` n'est pas
le compte owner (is_owner_account renvoie False — notamment si
NOVAMATH_OWNER_USER_ID est absent/invalide), AUCUNE des fonctions de ce
module ne lit `system_settings` ni ne retourne quoi que ce soit d'autre que
le comportement par défaut décrit dans chaque docstring : le mode test est
alors totalement invisible et inactif, pour tout le monde, y compris un
autre super_admin.

Persistance : deux clés dans `system_settings` (table clé/valeur générique
déjà existante, voir db.py/settings_service.py — aucune migration créée
pour ce chantier). Ces clés sont globales (une seule ligne chacune, pas de
colonne user_id) car il ne peut structurellement exister qu'un seul compte
owner à la fois (NOVAMATH_OWNER_USER_ID est un entier unique) — documenté
ici pour qu'un futur lecteur ne les prenne pas pour un mécanisme par-
utilisateur généralisable :

    owner_test_plan               "free" | "premium" | "ultra" | absente
    owner_test_unlimited_quotas   "1" | "0" | absente (défaut "1")

Ni l'une ni l'autre n'est jamais lue par un autre module que celui-ci et les
3 points de consommation prévus (plan_service.has_feature,
quota_service.get_limit, chatbot/provider_manager.select_llm_for_user) —
jamais un accès direct à ces clés ailleurs dans le projet.
"""
import logging

import db
import owner_service
from plan_service import Plan

logger = logging.getLogger("owner_test_plan_service")

_KEY_TEST_PLAN = "owner_test_plan"
_KEY_UNLIMITED_QUOTAS = "owner_test_unlimited_quotas"


def get_test_plan(user):
    """Plan de test actuellement actif pour `user`, ou None si :
    - `user` n'est pas le compte owner (is_owner_account) — AUCUNE lecture DB
      dans ce cas, par fail-closed (voir docstring du module) ;
    - aucun plan de test n'a jamais été choisi (clé absente) ;
    - la valeur stockée ne correspond à aucun Plan connu (dégradation
      silencieuse vers "aucun override", jamais une exception pour une
      donnée corrompue — même philosophie que Plan.from_value)."""
    if not owner_service.is_owner_account(user):
        return None
    row = db.get_system_setting(_KEY_TEST_PLAN)
    if not row or not row["value"]:
        return None
    return Plan.parse(row["value"])


def set_test_plan(actor, plan_value):
    """Active/modifie (`plan_value` dans {"free","premium","ultra"}) ou
    désactive (`plan_value` None) le plan de test — réservé au compte owner,
    revérifié ici (jamais une confiance dans un appelant qui aurait déjà
    vérifié plus haut). `plan_value` est une valeur externe non fiable (corps
    JSON d'une requête HTTP) : validée via Plan.parse (stricte, contrairement
    à Plan.from_value), jamais dégradée silencieusement vers FREE en cas de
    faute de frappe côté client.

    Renvoie (ok, error) : error est une chaîne explicite si `actor` n'est pas
    owner ou si `plan_value` est invalide, None en cas de succès. N'écrit
    jamais `users.plan`, ne touche jamais Stripe."""
    if not owner_service.is_owner_account(actor):
        return False, "Réservé au compte owner."
    if plan_value is None:
        db.set_system_setting(_KEY_TEST_PLAN, "", updated_by_admin_id=actor.get("id"))
        logger.info("Mode test Owner désactivé (utilisateur %s).", actor.get("id"))
        return True, None
    plan = Plan.parse(plan_value)
    if plan is None:
        return False, f"Plan de test invalide : {plan_value!r} (attendu free/premium/ultra)."
    db.set_system_setting(_KEY_TEST_PLAN, plan.value, updated_by_admin_id=actor.get("id"))
    logger.info("Mode test Owner activé — plan de test = %s (utilisateur %s).", plan.value, actor.get("id"))
    return True, None


def get_unlimited_quotas(user):
    """True si les quotas de `user` doivent rester illimités malgré un plan
    de test actif — pertinent uniquement pour le compte owner (True par
    défaut pour TOUT le monde si `user` n'est pas owner, valeur qui n'a de
    sens que côté appelant : quota_service.get_limit ne consulte cette
    fonction qu'après avoir déjà vérifié is_owner_account, donc la valeur par
    défaut ici ne peut jamais s'appliquer à un utilisateur normal).

    Défaut True quand owner et jamais configuré : préserve exactement le
    comportement Owner/Developer Override historique (illimité) tant que
    l'owner n'a pas explicitement désactivé ce filet."""
    if not owner_service.is_owner_account(user):
        return True
    row = db.get_system_setting(_KEY_UNLIMITED_QUOTAS)
    if not row or row["value"] is None or row["value"] == "":
        return True
    return row["value"] == "1"


def set_unlimited_quotas(actor, enabled):
    """Active/désactive le filet "quotas illimités" pour le compte owner —
    réservé au owner, revérifié ici. `enabled` est castée en bool avant
    stockage (jamais une valeur brute non fiable écrite telle quelle)."""
    if not owner_service.is_owner_account(actor):
        return False, "Réservé au compte owner."
    db.set_system_setting(_KEY_UNLIMITED_QUOTAS, "1" if enabled else "0", updated_by_admin_id=actor.get("id"))
    logger.info("Quotas illimités Owner = %s (utilisateur %s).", enabled, actor.get("id"))
    return True, None


def effective_plan(user):
    """Point UNIQUE de résolution du plan « effectif » — celui que
    plan_service.has_feature/quota_service.get_limit/
    provider_manager.select_llm_for_user doivent utiliser à la place de
    plan_service.get_plan(user) quand la distinction importe.

    - Utilisateur normal (is_owner_account False, y compris un autre
      super_admin ou NOVAMATH_OWNER_USER_ID non configuré) : renvoie
      exactement plan_service.get_plan(user) — comportement 100% inchangé,
      aucune lecture de system_settings.
    - Compte owner SANS plan de test actif : renvoie Plan.ULTRA — reproduit
      exactement l'ancien court-circuit "owner = toujours tout débloqué"
      (FEATURE_MATRIX[ULTRA] couvre la totalité des Feature connues, donc
      has_feature(owner, n'importe quelle feature) reste toujours True,
      comme avant ce chantier).
    - Compte owner AVEC plan de test actif : renvoie ce plan de test — jamais
      users.plan, qui reste inchangé en base."""
    if not owner_service.is_owner_account(user):
        from plan_service import get_plan
        return get_plan(user)
    test_plan = get_test_plan(user)
    return test_plan if test_plan is not None else Plan.ULTRA


def status(user):
    """Aperçu JSON-sérialisable de l'état du mode test pour `user`, consommé
    par GET /api/owner/test-plan (voir server.py) — inclut le provider/
    modèle réellement sélectionnés (chatbot/provider_manager.select_llm_for_user,
    réutilisé tel quel, aucun second système de log/preview créé), pour
    vérifier concrètement l'effet du plan de test sur le routage IA sans
    avoir à lancer une conversation. N'affiche jamais de clé API."""
    from plan_service import get_plan
    from chatbot import provider_manager

    is_owner = owner_service.is_owner_account(user)
    real_plan = get_plan(user)
    test_plan = get_test_plan(user)
    plan = effective_plan(user)
    provider_name, model = provider_manager.select_llm_for_user(user)
    return {
        "is_owner": is_owner,
        "real_plan": real_plan.value,
        "test_plan": test_plan.value if test_plan else None,
        "effective_plan": plan.value,
        "owner_unlimited_quotas": get_unlimited_quotas(user),
        "provider": provider_name,
        "model": model,
    }
