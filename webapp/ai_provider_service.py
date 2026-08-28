"""
Service de gestion des fournisseurs IA configurables.

IMPORTANT : le CHOIX du fournisseur IA reste entièrement piloté par les
constantes statiques de webapp/chatbot/provider_manager.py (PROVIDERS/MODELS/
MODEL_CHAIN_BY_PLAN) — ce module ne décide jamais quel fournisseur est
utilisé, il ne fait qu'exposer un point d'entrée unique,
record_llm_usage(), pour ENREGISTRER la consommation réelle (tokens) d'un
appel déjà terminé (voir webapp/chatbot/conversation_manager.py::
_log_llm_call_details, seul appelant). provider_manager.py/
select_llm_for_user()/llm_fallback_service.py restent inchangés.

Architecture identique au reste du projet :

    (appelant)  →  ai_provider_service.py  →  db.py

jamais l'inverse. Ce module ne dépend ni de Flask ni de plan_service —
`subscription` est ici une simple valeur texte (ex: "free"/"premium"/
"ultra", reprenant par convention plan_service.Plan.value), jamais l'Enum
Plan lui-même, exactement comme db.py ignore déjà plan_service ailleurs
dans le projet (voir set_stripe_subscription).
"""
import logging
from datetime import datetime, timezone

import db

logger = logging.getLogger("webapp.ai_provider_service")


# ── Fournisseurs IA ───────────────────────────────────────────────────────────
def create_provider(name, provider_key, model_name, enabled=True, priority=0, fallback_provider_id=None,
                     code=None, description=None, badge=None, icon=None, color=None):
    """Crée un fournisseur IA configurable et renvoie son id. `provider_key`
    doit correspondre à une clé de provider_manager.PROVIDERS (ex: "gemini",
    "anthropic", "ollama", "fake") le jour où ce module sera branché — non
    validé ici volontairement, ce service ignore tout de provider_manager.py
    (même séparation stricte que le reste de l'architecture). `code`/
    `description`/`badge`/`icon`/`color` : métadonnées d'affichage pour la
    future interface d'administration, jamais lues par le chatbot."""
    return db.create_ai_provider(
        name=name,
        provider_key=provider_key,
        model_name=model_name,
        enabled=enabled,
        priority=priority,
        fallback_provider_id=fallback_provider_id,
        code=code,
        description=description,
        badge=badge,
        icon=icon,
        color=color,
    )


def get_provider(provider_id):
    """Le fournisseur configuré, ou None si `provider_id` est inconnu."""
    return db.get_ai_provider(provider_id)


def list_providers(enabled_only=False):
    """Tous les fournisseurs configurés, triés par priorité croissante (0 =
    priorité la plus haute). `enabled_only=True` : uniquement les fournisseurs
    actifs."""
    return db.list_ai_providers(enabled_only=enabled_only)


def update_provider(provider_id, name, provider_key, model_name, enabled, priority, fallback_provider_id=None,
                     code=None, description=None, badge=None, icon=None, color=None):
    """Remplace l'intégralité des champs modifiables d'un fournisseur
    existant."""
    db.update_ai_provider(
        provider_id,
        name=name,
        provider_key=provider_key,
        model_name=model_name,
        enabled=enabled,
        priority=priority,
        fallback_provider_id=fallback_provider_id,
        code=code,
        description=description,
        badge=badge,
        icon=icon,
        color=color,
    )


def set_provider_enabled(provider_id, enabled):
    """Active/désactive un fournisseur sans toucher à ses autres champs."""
    db.set_ai_provider_enabled(provider_id, enabled)


def delete_provider(provider_id):
    """Supprime un fournisseur. Toute association subscription_ai_mapping
    pointant vers lui est supprimée en cascade (voir SCHEMA, ON DELETE
    CASCADE) ; tout fournisseur qui le référençait comme
    `fallback_provider_id` voit ce champ repassé à NULL (ON DELETE SET
    NULL)."""
    db.delete_ai_provider(provider_id)


# ── Association abonnement → fournisseur IA ───────────────────────────────────
def map_subscription_to_provider(subscription, provider_id):
    """Associe un palier d'abonnement (ex: "free"/"premium"/"ultra") à un
    fournisseur configuré et renvoie l'id de l'association créée. Un même
    `subscription` peut être associé à plusieurs fournisseurs (plusieurs
    lignes) : list_mappings_for_subscription() les renvoie triées par
    priorité du fournisseur, pour représenter une chaîne de repli comme
    MODEL_CHAIN_BY_PLAN aujourd'hui."""
    return db.create_subscription_ai_mapping(subscription, provider_id)


def get_mapping(mapping_id):
    """L'association subscription → fournisseur, ou None si `mapping_id` est
    inconnu."""
    return db.get_subscription_ai_mapping(mapping_id)


def list_mappings_for_subscription(subscription):
    """Toutes les associations d'un palier donné, triées par priorité du
    fournisseur associé (le premier de la liste est le candidat prioritaire)."""
    return db.list_subscription_ai_mappings(subscription=subscription)


def list_all_mappings():
    """Toutes les associations subscription → fournisseur, tous paliers
    confondus."""
    return db.list_subscription_ai_mappings()


def delete_mapping(mapping_id):
    """Supprime une association subscription → fournisseur."""
    db.delete_subscription_ai_mapping(mapping_id)


# ── Initialisation par défaut (seed) ──────────────────────────────────────────
# Reprend EXACTEMENT les valeurs actuellement codées en dur dans
# webapp/chatbot/provider_manager.py (DEFAULT_MODEL de chaque provider et
# MODEL_CHAIN_BY_PLAN, CHAÎNE COMPLÈTE — audit 2026-08-23 : la version
# précédente de ce seed ne reprenait que MODEL_CHAIN_BY_PLAN[plan][0], le
# premier candidat de chaque plan, jamais les repli — ce qui faisait que
# select_llm_for_user() préférait silencieusement cette chaîne DB tronquée
# à la chaîne statique complète dès qu'une seule ligne existait pour un plan
# (voir _is_valid_chain/_load_chain_from_database dans provider_manager.py),
# et que Premium/Ultra ne retombaient donc jamais réellement sur Gemini Flash
# quand leur modèle principal échouait. Corrigé ici pour que la table reflète
# fidèlement TOUTE la chaîne de secours, pas seulement son premier maillon.
# `code`/`description`/`badge`/`icon`/`color` : métadonnées d'affichage
# arbitraires pour l'interface d'administration (jamais lues par le chatbot)
# — valeurs raisonnables par défaut, librement modifiables ensuite via
# update_provider().
#
# La priorité (colonne unique, voir admin_ai_service._validate_provider_payload)
# est un ordre GLOBAL, pas propre à un abonnement : list_subscription_ai_mappings()
# trie chaque plan par priorité croissante de SES fournisseurs associés
# uniquement (voir db.py) — un même modèle qui doit être le premier choix
# d'un plan et le repli d'un autre a donc besoin de DEUX lignes ai_providers
# distinctes (même provider_key/model_name, priorité différente), jamais
# partagées : Gemini Flash reste le fournisseur n°0 pour Free, mais un second
# enregistrement "Gemini Flash (repli)" à priorité plus basse sert de dernier
# recours pour Premium/Ultra ; de même pour "Gemini Pro (repli Ultra)".
_DEFAULT_PROVIDERS = (
    # (name, provider_key, model_name, priority, code, description, badge, icon, color)
    ("Gemini Flash", "gemini", "gemini-3-flash-preview", 0, "gemini_flash",
     "Modèle Gemini rapide, candidat par défaut du plan Gratuit.", "Rapide", "zap", "#22C55E"),
    ("Gemini Pro", "gemini", "gemini-3.1-pro-preview", 1, "gemini_pro",
     "Modèle Gemini le plus capable, candidat prioritaire du plan Premium.", "Avancé", "brain", "#3B82F6"),
    ("Claude", "anthropic", "claude-sonnet-5", 2, "claude_sonnet",
     "Modèle Claude Sonnet, candidat prioritaire du plan Ultra.", "Premium", "sparkles", "#D97757"),
    ("Gemini Pro (repli Ultra)", "gemini", "gemini-3.1-pro-preview", 3, "gemini_pro_ultra_fallback",
     "Repli du plan Ultra si Claude échoue, avant Gemini Flash.", "Repli", "brain", "#3B82F6"),
    ("Gemini Flash (repli)", "gemini", "gemini-3-flash-preview", 4, "gemini_flash_fallback",
     "Dernier repli commun à Premium et Ultra avant le moteur local.", "Repli", "zap", "#22C55E"),
)

# (subscription, index dans _DEFAULT_PROVIDERS ci-dessus) — reprend
# MODEL_CHAIN_BY_PLAN[plan] EN ENTIER (tous les maillons, pas seulement le
# premier — voir commentaire ci-dessus).
_DEFAULT_SUBSCRIPTION_MAPPING = (
    ("free", 0),      # Gemini Flash
    ("premium", 1),   # Gemini Pro
    ("premium", 4),   # Gemini Flash (repli)
    ("ultra", 2),     # Claude
    ("ultra", 3),     # Gemini Pro (repli Ultra)
    ("ultra", 4),     # Gemini Flash (repli)
)


def seed_default_providers():
    """Initialise ai_providers/subscription_ai_mapping avec les fournisseurs
    actuels de NovaMath, une seule fois, puis complète les métadonnées
    d'affichage (`code`/`description`/`badge`/`icon`/`color`) de tout
    fournisseur par défaut déjà présent qui ne les a pas encore (voir
    _backfill_default_metadata ci-dessous).

    Création des lignes idempotente par construction : n'insère quoi que ce
    soit QUE si ai_providers est entièrement vide (voir db.list_ai_providers())
    — si la table contient déjà au moins une ligne (seed précédent, ou données
    créées manuellement/par un appelant futur), aucune ligne n'est créée.
    Sûre à appeler à chaque démarrage du serveur (voir server.py), exactement
    comme db.init_db() (CREATE TABLE IF NOT EXISTS) et
    rate_limit_service.cleanup().

    Complétion des métadonnées idempotente séparément (COALESCE, voir
    db.backfill_ai_provider_metadata) : ne remplit que les champs encore NULL,
    ne modifie/écrase JAMAIS une valeur déjà renseignée, manuellement ou non.

    Renvoie True si les lignes ai_providers/subscription_ai_mapping ont été
    créées lors de CET appel, False si la table contenait déjà des lignes
    (le backfill des métadonnées a quand même pu s'appliquer dans ce cas).

    Ne touche jamais provider_manager.py ni aucun fichier de webapp/chatbot/ :
    ce seed ne fait que peupler des tables non lues par le chatbot à ce jour."""
    created = False
    if not db.list_ai_providers():
        provider_ids = [
            create_provider(name, provider_key, model_name, enabled=True, priority=priority,
                             code=code, description=description, badge=badge, icon=icon, color=color)
            for name, provider_key, model_name, priority, code, description, badge, icon, color in _DEFAULT_PROVIDERS
        ]
        for subscription, provider_index in _DEFAULT_SUBSCRIPTION_MAPPING:
            map_subscription_to_provider(subscription, provider_ids[provider_index])
        created = True

    _backfill_default_metadata()
    return created


# ── Santé des fournisseurs IA ──────────────────────────────────────────────────
# Infrastructure de préparation pour un futur écran d'administration : aucun
# appelant existant n'écrit ni ne lit ces fonctions (aucun appel API réel,
# aucune lecture par webapp/chatbot/) — voir docstring du module.
def record_health(provider_id, last_success=None, last_failure=None, http_code=None, latency_ms=None,
                   average_latency=None, total_requests=0, total_errors=0, success_rate=None, last_error=None):
    """Enregistre (ou remplace) le snapshot de santé complet d'un fournisseur.
    Une seule ligne par fournisseur (UPSERT) — l'appelant fournit l'état
    complet qu'il souhaite enregistrer, jamais une mise à jour partielle
    implicite."""
    return db.create_or_update_ai_provider_health(
        provider_id,
        last_success=last_success,
        last_failure=last_failure,
        http_code=http_code,
        latency_ms=latency_ms,
        average_latency=average_latency,
        total_requests=total_requests,
        total_errors=total_errors,
        success_rate=success_rate,
        last_error=last_error,
    )


def get_health(provider_id):
    """Le snapshot de santé d'un fournisseur, ou None s'il n'a jamais été
    enregistré."""
    return db.get_ai_provider_health(provider_id)


def list_health():
    """Le snapshot de santé de tous les fournisseurs qui en ont un, triés par
    priorité du fournisseur."""
    return db.list_ai_provider_health()


def delete_health(provider_id):
    """Supprime le snapshot de santé d'un fournisseur."""
    db.delete_ai_provider_health(provider_id)


# ── Consommation des fournisseurs IA ───────────────────────────────────────────
# Même philosophie que ci-dessus : infrastructure de préparation, aucun appel
# API réel, aucune lecture par le chatbot.
def record_usage(provider_id, date, input_tokens=0, output_tokens=0, total_tokens=0, requests=0,
                  estimated_cost=0, success_count=0, error_count=0, fallback_count=0,
                  response_time_ms=0, error_type=None, error_message=None, error_at=None):
    """Crée une ligne de consommation pour (`provider_id`, `date`). Échoue si
    la ligne existe déjà pour ce couple — voir increment_usage() pour
    l'accumulation progressive au fil de la journée."""
    return db.create_ai_provider_usage(
        provider_id, date, input_tokens=input_tokens, output_tokens=output_tokens, total_tokens=total_tokens,
        requests=requests, estimated_cost=estimated_cost, success_count=success_count, error_count=error_count,
        fallback_count=fallback_count, response_time_ms=response_time_ms, error_type=error_type,
        error_message=error_message, error_at=error_at,
    )


def increment_usage(provider_id, date, input_tokens=0, output_tokens=0, total_tokens=0, requests=0,
                     estimated_cost=0, success_count=0, error_count=0, fallback_count=0,
                     response_time_ms=0, error_type=None, error_message=None, error_at=None):
    """Incrémente (ou crée) la consommation de `provider_id` pour `date` et
    renvoie la ligne à jour — appelé après CHAQUE appel LLM réel (succès ou
    échec), voir record_llm_usage() ci-dessous."""
    return db.increment_ai_provider_usage(
        provider_id, date, input_tokens=input_tokens, output_tokens=output_tokens, total_tokens=total_tokens,
        requests=requests, estimated_cost=estimated_cost, success_count=success_count, error_count=error_count,
        fallback_count=fallback_count, response_time_ms=response_time_ms, error_type=error_type,
        error_message=error_message, error_at=error_at,
    )


# ── Tarification & enregistrement de la consommation réelle du chatbot ─────
# Seule constante à modifier pour ajuster un tarif ou ajouter un futur
# modèle — aucune valeur magique dans le code du chatbot. Clé =
# (provider_key, model_name), exactement les valeurs stockées dans
# ai_providers.provider_key/model_name (voir _DEFAULT_PROVIDERS ci-dessus) et
# celles renvoyées par call_info["provider"]/call_info["model"] (voir
# webapp/chatbot/services/llm_fallback_service.py::generate). Prix publics
# officiels en USD par million de tokens — revérifiés le 2026-08-24
# (Chantier 4, les anciennes valeurs étaient obsolètes dans les deux sens :
# Gemini sous-évalué, Claude Sonnet 5 surévalué) :
#   - Gemini 3 Flash Preview : https://ai.google.dev/gemini-api/docs/pricing
#     (page datée 13/08/2026) — tarif Standard, tier texte/image/vidéo (le
#     tarif audio, 1,00 $/M en entrée, ne s'applique jamais ici : NovaMath
#     n'envoie que du texte).
#   - Gemini 3.1 Pro Preview : idem, tier prompts <= 200k tokens (le tier
#     > 200k, 4,00 $/12,00 $... 18,00 $, ne s'applique jamais aux échanges
#     courts d'un chatbot pédagogique).
#   - Claude Sonnet 5 : https://platform.claude.com/docs/fr/about-claude/pricing
#     — 2,00 $/10,00 $ était le tarif de LANCEMENT annoncé jusqu'au
#     31/08/2026 ; la doc officielle confirme désormais explicitement que la
#     hausse prévue à 3,00 $/15,00 $ n'aura PAS lieu et que 2,00 $/10,00 $
#     devient le tarif standard permanent — d'où la correction ci-dessous
#     (l'ancienne valeur de ce fichier anticipait à tort cette hausse).
# À revérifier si Google/Anthropic republient une nouvelle grille.
PRICING_USD_PER_MILLION_TOKENS = {
    ("gemini", "gemini-3-flash-preview"): {"input": 0.50, "output": 3.00},
    ("gemini", "gemini-3.1-pro-preview"): {"input": 2.00, "output": 12.00},
    ("anthropic", "claude-sonnet-5"): {"input": 2.00, "output": 10.00},
}


def estimate_llm_cost(provider_key, model_name, input_tokens, output_tokens, total_tokens=None):
    """Coût estimé en USD d'un appel LLM, à partir de
    PRICING_USD_PER_MILLION_TOKENS. Renvoie 0.0 (jamais une exception) si
    (provider_key, model_name) n'a pas de tarif connu — un modèle non
    répertorié ne doit jamais empêcher l'enregistrement des tokens, seul le
    coût reste alors à 0.

    `total_tokens` (optionnel — toujours transmis par les deux seuls
    appelants réels, ai_request_log_service.record() et
    record_llm_usage() ci-dessous, qui l'ont déjà sous la main) : sert
    UNIQUEMENT à retrouver les tokens de raisonnement (« thinking »/
    « thoughts ») que Gemini facture réellement mais expose dans un champ
    SÉPARÉ de candidatesTokenCount (voir gemini_provider.py::stream_chat,
    qui alimente completion_tokens depuis candidates_token_count, jamais
    depuis thoughts_token_count). Vérifié par appel réel (audit du
    2026-08-24) : total_token_count == prompt_token_count +
    candidates_token_count + thoughts_token_count, EXACTEMENT — donc
    `total_tokens - input_tokens - output_tokens` retrouve précisément les
    thinking tokens sans nouvelle colonne ni second champ à faire remonter.
    Confirmé par la documentation officielle Google
    (ai.google.dev/gemini-api/docs/pricing, consultée le 2026-08-24) :
    « Output price (including thinking tokens) » — facturés au tarif OUTPUT,
    jamais un tarif séparé.

    Sur Anthropic, ce delta est TOUJOURS nul : anthropic_provider.py
    alimente total_tokens comme input_tokens + output_tokens (jamais un
    troisième nombre), et un appel réel (audit du 2026-08-24, question à
    raisonnement visible) confirme qu'Claude Sonnet 5 n'expose aucun champ
    usage séparé pour le raisonnement — la documentation officielle
    (platform.claude.com/docs/en/build-with-claude/extended-thinking)
    confirme explicitement que les tokens de raisonnement sont DÉJÀ inclus
    dans usage.output_tokens (voir usage.output_tokens_details.thinking_tokens,
    un sous-détail du total facturé, jamais un surplus à ajouter). Cette
    fonction reste donc correcte pour Anthropic sans aucun changement de
    comportement — seul Gemini était sous-facturé."""
    pricing = PRICING_USD_PER_MILLION_TOKENS.get((provider_key, model_name))
    if pricing is None:
        return 0.0
    input_tokens = input_tokens or 0
    output_tokens = output_tokens or 0
    billable_output_tokens = output_tokens
    if total_tokens is not None:
        thinking_tokens = total_tokens - input_tokens - output_tokens
        if thinking_tokens > 0:
            billable_output_tokens += thinking_tokens
    return (
        input_tokens * pricing["input"] / 1_000_000
        + billable_output_tokens * pricing["output"] / 1_000_000
    )


def _find_provider_id(provider_key, model_name, is_fallback=False):
    """L'id du fournisseur configuré correspondant à (provider_key, model_name)
    — mêmes valeurs que celles seedées par seed_default_providers() et
    modifiables depuis /admin/ia. None si aucun fournisseur configuré ne
    correspond (ex: fournisseur "fake"/"ollama" jamais configurés dans
    ai_providers, ou modèle retiré du panneau d'administration).

    Chantier "fiabilité des données d'analytics IA" (audit 2026-08-27) : le
    catalogue par défaut contient VOLONTAIREMENT deux lignes distinctes pour
    un même (provider_key, model_name) — un rôle "primaire" (ex: "Gemini
    Flash", priority 0) et un rôle "repli" (ex: "Gemini Flash (repli)",
    priority 4), voir _DEFAULT_PROVIDERS ci-dessus. provider_manager.py ne
    renvoie jamais l'id exact du rôle (seulement le couple provider_key/
    model_name, voir select_llm_for_user()) — cette fonction doit donc
    désambiguïser elle-même SANS toucher provider_manager.py ni la mécanique
    de repli.

    `is_fallback` (déjà transmis par record_llm_usage(), voir call_info
    ci-dessous) : quand plusieurs lignes correspondent au même couple, choisit
    celle de plus haute priorité (= dernière de la liste, triée priority ASC
    par db.list_ai_providers()) si is_fallback=True, celle de plus basse
    priorité (= première) sinon — reprend la convention déjà en vigueur dans
    tout le projet (priority = ordre d'essai dans la chaîne, voir
    provider_manager.MODEL_CHAIN_BY_PLAN/select_llm_for_user) plutôt qu'un
    index arbitraire ou un nom codé en dur : robuste à un renommage/à un
    fournisseur personnalisé ajouté par l'admin. Un seul fournisseur configuré
    partageant ce couple (cas normal, ex: Claude, ou toute configuration sans
    doublon volontaire) : is_fallback n'a alors aucun effet, l'unique
    correspondance est toujours renvoyée — jamais redirigée arbitrairement
    vers une entrée de repli qui n'existe pas."""
    matches = [
        provider for provider in db.list_ai_providers()
        if provider["provider_key"] == provider_key and provider["model_name"] == model_name
    ]
    if not matches:
        return None
    return matches[-1]["id"] if is_fallback else matches[0]["id"]


def record_llm_usage(provider_key, model_name, usage, *, success=True, response_time_ms=None,
                      error_type=None, error_message=None, is_fallback=False):
    """Point d'entrée UNIQUE pour le chatbot (voir conversation_manager.py::
    _log_llm_call_details, seul appelant) : enregistre CHAQUE appel LLM réel
    — succès ou échec — accumulé par jour dans ai_provider_usage via
    increment_usage() ci-dessus.

    `usage` : dict {"prompt_tokens", "completion_tokens", "total_tokens"} ou
    None/vide (aucun usage remonté, ex: échec avant le premier chunk, ou
    FakeProvider) — dans ce cas les compteurs de tokens restent à 0, mais la
    requête (succès/échec/durée) est quand même enregistrée.
    `success` : False sur un appel qui a fini par échouer (voir
    llm_fallback_service.generate()::call_info["success"]) — incrémente
    error_count au lieu de success_count, et fige last_error_type/
    last_error_message/last_error_at pour (provider_key, model_name, jour).
    `response_time_ms` : durée RÉELLE de cet appel (voir call_info["elapsed_ms"]),
    accumulée dans total_response_time_ms (moyenne calculée à la lecture).
    `is_fallback` : True si ce fournisseur n'était pas le premier candidat
    tenté pour ce tour — incrémente fallback_count (le détail — fournisseur
    initial/final/raison/temps perdu — est enregistré séparément par
    record_provider_fallback(), voir conversation_manager.py).

    Ne lève JAMAIS d'exception : un fournisseur non configuré est journalisé
    (logger.warning) puis ignoré, un échec SQL est journalisé
    (logger.exception) puis ignoré — l'enregistrement de ces statistiques ne
    doit jamais empêcher ou retarder la réponse déjà envoyée à l'élève."""
    if not provider_key or not model_name:
        return
    try:
        provider_id = _find_provider_id(provider_key, model_name, is_fallback=is_fallback)
        if provider_id is None:
            logger.warning(
                "record_llm_usage : aucun fournisseur configuré pour provider_key=%s model_name=%s "
                "— consommation non enregistrée.", provider_key, model_name,
            )
            return
        usage = usage or {}
        input_tokens = usage.get("prompt_tokens") or 0
        output_tokens = usage.get("completion_tokens") or 0
        total_tokens = usage.get("total_tokens") or (input_tokens + output_tokens)
        cost = estimate_llm_cost(provider_key, model_name, input_tokens, output_tokens, total_tokens)
        today = datetime.now(timezone.utc).date().isoformat()
        increment_usage(
            provider_id, today,
            input_tokens=input_tokens, output_tokens=output_tokens, total_tokens=total_tokens,
            requests=1, estimated_cost=cost,
            success_count=1 if success else 0,
            error_count=0 if success else 1,
            fallback_count=1 if is_fallback else 0,
            response_time_ms=round(response_time_ms) if response_time_ms else 0,
            error_type=None if success else error_type,
            error_message=None if success else error_message,
            error_at=None if success else datetime.now(timezone.utc).isoformat(),
        )
    except Exception:
        logger.exception("record_llm_usage : échec de l'enregistrement de la consommation IA — ignoré.")


def record_provider_fallback(provider_initial, model_initial, provider_final, model_final, reason,
                             time_lost_ms=0):
    """Enregistre UN événement de fallback réellement déclenché (voir
    docstring de ai_provider_fallback_events dans db.py::SCHEMA) — appelé
    par conversation_manager.py::_log_llm_call_details uniquement quand
    call_info["fallback_from"] est renseigné (le premier candidat tenté a
    échoué). Ne lève jamais d'exception, même logique de tolérance que
    record_llm_usage() ci-dessus."""
    try:
        db.create_ai_provider_fallback_event(
            provider_initial, model_initial, provider_final, model_final, reason,
            time_lost_ms=round(time_lost_ms) if time_lost_ms else 0,
        )
    except Exception:
        logger.exception("record_provider_fallback : échec de l'enregistrement — ignoré.")


def get_usage(provider_id, date):
    """La consommation de `provider_id` pour `date`, ou None si aucune ligne
    n'existe encore pour ce jour."""
    return db.get_ai_provider_usage(provider_id, date)


def list_usage(provider_id=None):
    """Toute la consommation enregistrée (optionnellement filtrée par
    `provider_id`), triée par date croissante."""
    return db.list_ai_provider_usage(provider_id=provider_id)


def update_usage(usage_id, input_tokens, output_tokens, requests, estimated_cost):
    """Remplace l'intégralité des champs numériques d'une ligne de
    consommation existante, par id."""
    db.update_ai_provider_usage(usage_id, input_tokens, output_tokens, requests, estimated_cost)


def delete_usage(usage_id):
    """Supprime une ligne de consommation."""
    db.delete_ai_provider_usage(usage_id)


def _backfill_default_metadata():
    """Complète `code`/`description`/`badge`/`icon`/`color` pour tout
    fournisseur déjà en base (typiquement seedé avant l'introduction de ces
    colonnes) dont le (provider_key, model_name) correspond à un des
    fournisseurs par défaut — uniquement les champs encore NULL (voir
    db.backfill_ai_provider_metadata), jamais une valeur déjà renseignée."""
    for name, provider_key, model_name, priority, code, description, badge, icon, color in _DEFAULT_PROVIDERS:
        db.backfill_ai_provider_metadata(provider_key, model_name, code, description, badge, icon, color)
