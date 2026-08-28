"""
Façade de lecture/écriture pure sur la table subscription_plans — le
catalogue administrable des abonnements NovaMath (Free/Premium/Ultra).

IMPORTANT : ce module n'est PAS branché aux droits/quotas réellement
appliqués. Le plan effectif d'un utilisateur et ses droits restent
entièrement pilotés par plan_service.py (FEATURE_MATRIX) et
quota_service.py (QUOTA_MATRIX) — aucun appelant existant (chatbot,
quota_service, plan_service, stripe_webhook_service) ne lit cette table.
Modifier une ligne ici change uniquement ce qui s'affiche/s'édite dans le
panneau d'administration Abonnements (voir admin_subscriptions_service.py),
jamais le comportement réel du chatbot ni les montants réellement facturés
par Stripe (toujours pilotés par STRIPE_PRICE_PREMIUM/STRIPE_PRICE_ULTRA,
voir stripe_service.py, totalement inchangé par ce module).

Architecture identique au reste du projet :

    (futur appelant)  →  subscription_plan_service.py  →  db.py

jamais l'inverse. Ce module ne dépend ni de Flask ni de role_service — les
permissions sont déjà tranchées côté route (voir server.py).

`advantages`/`limits` : listes de chaînes, sérialisées en JSON dans la
colonne TEXT correspondante (même convention que
conversations.learning_context) — ce module s'occupe seul de l'encodage/
décodage, jamais l'appelant.
"""
import json

import db
from plan_service import Plan


def _encode_list(value):
    return json.dumps(value or [], ensure_ascii=False)


def _decode_list(value):
    return json.loads(value) if value else []


def _row_to_plan(row):
    if row is None:
        return None
    return {
        **row,
        "active": bool(row["active"]),
        "advantages": _decode_list(row["advantages"]),
        "limits": _decode_list(row["limits"]),
    }


def get_plan(plan):
    """`plan` : valeur brute (ex: "premium") — renvoie None si `plan` n'a
    jamais été seedé (voir seed_default_plans)."""
    return _row_to_plan(db.get_subscription_plan(plan))


def list_plans():
    """Tous les plans catalogués, triés par display_order — jamais les 3
    plans de plan_service.Plan directement : seuls ceux réellement présents
    en base (après seed_default_plans) sont renvoyés."""
    return [_row_to_plan(row) for row in db.list_subscription_plans()]


def update_plan(plan, name, description, price_amount_cents, currency, duration_label,
                 advantages, limits, quota_daily, quota_chatbot,
                 display_order, active):
    """`quota_monthly` n'est plus un paramètre : aucun mécanisme de quota
    mensuel n'existe dans quota_service.py (uniquement journalier), ce champ
    catalogue n'était donc jamais qu'un espace réservé jamais branché — voir
    docstring de seed_default_plans ci-dessous. Toujours écrit à None en
    base (colonne conservée, inutilisée)."""
    db.update_subscription_plan(
        plan, name, description, price_amount_cents, currency, duration_label,
        _encode_list(advantages), _encode_list(limits), quota_daily, None, quota_chatbot,
        display_order, active,
    )


def set_plan_active(plan, active):
    db.set_subscription_plan_active(plan, active)


# ── Initialisation par défaut (seed) ─────────────────────────────────────────
# Chantier "Synchronisation globale des abonnements" (2026-08-27) : les
# advantages/limits/quota_chatbot ci-dessous étaient désynchronisés de la
# réalité technique sur DEUX points distincts, découverts par cet audit —
# corrigés ici (jamais dans quota_service.py, seule véritable source
# d'application des quotas — voir docstring du module) :
#   1. Texte marketing obsolète : "Support prioritaire"/"Statistiques
#      avancées et badges exclusifs"/"Accès anticipé"/"Génération
#      d'exercices sur mesure" (CUSTOM_EXERCISES/PRIORITY_SUPPORT/
#      PROFILE_ANALYTICS/EARLY_ACCESS ne sont utilisées par AUCUNE route,
#      voir l'audit du chantier précédent sur abonnement.html) et "Exports
#      PDF illimités"/"1 export PDF par mois" (Feature.EXPORT n'est
#      restreinte pour AUCUN plan, voir server.py::api_data_summary —
#      jamais une vraie différenciation).
#   2. quota_chatbot INCORRECT (jamais branché à un vrai comportement, mais
#      induit l'admin en erreur en l'affichant) : Free=25 (réel : 15,
#      QUOTA_MATRIX[FREE][CHAT_MESSAGES]) ; Premium=250 (réel : 25,
#      QUOTA_MATRIX[PREMIUM][CHAT_MESSAGES] — vraisemblablement un facteur
#      10 introduit lors d'une saisie manuelle) ; Ultra=None/illimité (réel :
#      40, QUOTA_MATRIX[ULTRA][CHAT_MESSAGES] — Ultra n'est PAS illimité en
#      messages, seul LLM_CALLS partage cette limite de 40). quota_daily
#      (miroir de AI_GENERATIONS) était déjà correct (20/500/illimité) et
#      reste inchangé.
# Aucune notion de quota MENSUEL n'existe nulle part ailleurs dans NovaMath
# (user_daily_usage est strictement journalier, voir quota_service.py) :
# quota_monthly reste semé à None ("non défini"), jamais une valeur inventée.
#
# Chantier "Différenciateurs Premium/Ultra" (même jour, 2026-08-27) : "Bilan
# de progression détaillé par notion" (Premium) et "Génération d'exercices
# sur mesure" (Ultra) rajoutées ci-dessous — CUSTOM_EXERCISES est
# redevenue une vraie fonctionnalité (voir server.py::api_practice_generate,
# POST /api/practice/generate, moteur exercise_generator/), contrairement à
# la note du point 1 ci-dessus qui décrivait son statut AVANT ce chantier.
_DEFAULT_PLANS = (
    # (plan, name, description, price_cents, currency, duration_label, advantages, limits,
    #  quota_daily, quota_chatbot, display_order)
    (
        Plan.FREE.value, "Gratuit", "Pour découvrir NovaMath et progresser à ton rythme.",
        0, "eur", "mois",
        ["Accès à tous les chapitres, avec l'essentiel du cours", "Suivi de progression et statistiques de base",
         "Chatbot : 15 messages/jour", "3 suggestions de révision personnalisées"],
        ["Analyse de PDF non disponible", "Génération d'exercices personnalisés non disponible",
         "Explications avancées non disponibles"],
        20, 15, 0,
    ),
    (
        Plan.PREMIUM.value, "Premium", "Pour les élèves qui veulent progresser sans limites.",
        699, "eur", "mois",
        ["Cours complet, toutes les notions et exemples", "Chatbot : 25 messages/jour",
         "Explications avancées du chatbot", "Dashboard élargi : 50 séries d'entraînement conservées",
         "5 suggestions de révision personnalisées", "Bilan de progression détaillé par notion"],
        ["Analyse de PDF non disponible"],
        500, 25, 1,
    ),
    (
        Plan.ULTRA.value, "Ultra", "L'expérience NovaMath complète, sans compromis.",
        1299, "eur", "mois",
        ["Cours complet, avec les démonstrations", "Exercices illimités",
         "Chatbot : 40 messages/jour", "Analyse de PDF par l'IA du chatbot",
         "Dashboard complet : toutes les séries conservées", "8 suggestions de révision personnalisées",
         "Génération d'exercices sur mesure"],
        [],
        None, 40, 2,
    ),
)


def seed_default_plans():
    """Initialise subscription_plans avec les 3 plans réels de NovaMath, une
    seule fois — n'insère quoi que ce soit QUE si la table est entièrement
    vide (même politique que ai_provider_service.seed_default_providers).
    Sûre à appeler à chaque démarrage du serveur. Renvoie True si les lignes
    ont été créées lors de CET appel, False sinon."""
    if db.list_subscription_plans():
        return False
    for plan, name, description, price_cents, currency, duration_label, advantages, limits, \
            quota_daily, quota_chatbot, display_order in _DEFAULT_PLANS:
        db.create_subscription_plan(
            plan, name, description, price_cents, currency, duration_label,
            _encode_list(advantages), _encode_list(limits),
            quota_daily, None, quota_chatbot, display_order, True,
        )
    return True
