"""
Point d'entrée UNIQUE pour résoudre le fournisseur IA actif. C'est une
décision interne à NovaMath, jamais un réglage utilisateur : changer de
fournisseur (OpenAI/Gemini/DeepSeek/Qwen/Llama/OpenRouter/LM Studio/API perso)
= ajouter une entrée à PROVIDERS + une classe dans webapp/chatbot/providers/,
puis changer la variable d'environnement CHATBOT_PROVIDER — jamais toucher au
reste de la chaîne (conversation_manager, prompt_builder, routes Flask), et
jamais exposer ce choix côté client.

Résolution du fournisseur actif (voir active_provider_name()), par ordre de
priorité strict :
    1. CHATBOT_PROVIDER (variable d'environnement) si définie explicitement —
       reste le moyen de forcer "fake"/"ollama"/"anthropic"/"gemini" à la main.
    2. "gemini" automatiquement si GEMINI_API_KEY est présente — défaut sûr :
       CHATBOT_PROVIDER absent de .env ne doit plus jamais retomber en
       silence sur FakeProvider alors qu'une clé Gemini valide existe.
    3. "fake" en dernier repli (aucune clé disponible) — FakeProvider (aucune
       API, réponses assemblées depuis les cours NovaMath via le Knowledge
       Engine) ne sert alors que de filet de sécurité pour le développement
       sans clé, jamais un choix silencieux en présence d'une clé.

Anthropic (API officielle Claude), Gemini (API officielle Google) et Ollama
(modèle local) restent disponibles en option côté serveur uniquement, en
positionnant CHATBOT_PROVIDER explicitement.
"""
import logging
import os
import time

import ai_provider_service
import owner_test_plan_service

from .providers.anthropic_provider import AnthropicProvider
from .providers.fake_provider import FakeProvider
from .providers.gemini_provider import GeminiProvider
from .providers.ollama_provider import OllamaProvider

logger = logging.getLogger("chatbot.provider_manager")

PROVIDERS = {
    "fake": FakeProvider,
    "ollama": OllamaProvider,
    "anthropic": AnthropicProvider,
    "gemini": GeminiProvider,
}

# Catalogue statique de secours, utilisé si le provider ne peut pas détecter
# ses modèles dynamiquement (ex: Ollama arrêté) — voir available_models().
MODELS = {
    "fake": {
        "moteur-novamath": "Moteur NovaMath (sans IA, par défaut)",
    },
    "ollama": {
        "mistral": "Mistral (par défaut)",
    },
    "anthropic": {
        "claude-sonnet-5": "Claude Sonnet 5 (équilibré)",
        "claude-opus-4-8": "Claude Opus 4.8 (le plus capable)",
        "claude-haiku-4-5-20251001": "Claude Haiku 4.5 (le plus rapide)",
    },
    # gemini-2.5-* renvoie une 404 "no longer available to new users" pour
    # toute clé API créée après leur dépréciation (vérifié par un appel réel) —
    # -flash-preview confirmé fonctionnel en conditions réelles (audit
    # 2026-08-23 : appel réel réussi, tokens/coût enregistrés dans
    # ai_request_logs).
    # gemini-3-pro-preview a ensuite été retiré à son tour : un appel réel
    # (audit 2026-08-23) a confirmé un 404 explicite de l'API — "This model
    # models/gemini-3-pro-preview is no longer available. Please update your
    # code to use models/gemini-3.1-pro-preview" — remplacé ci-dessous par ce
    # successeur, dont l'existence a été vérifiée par un appel réel séparé
    # (l'API répond un 429 "limit: 0" propre à CE projet Google AI Studio —
    # palier Pro non activé côté facturation — jamais un 404 : le nom de
    # modèle est donc bien reconnu par Google, contrairement à l'ancien).
    # Tant que ce palier de facturation n'est pas activé sur le projet, ce
    # modèle reste durablement indisponible en pratique — mark_unavailable()
    # le mettra en cache 24h à chaque échec réel, et select_llm_for_user()
    # retombe automatiquement sur gemini-3-flash-preview (voir
    # MODEL_CHAIN_BY_PLAN ci-dessous) : ne jamais retirer ce modèle de la
    # matrice pour autant, le successeur redeviendra utilisable dès que la
    # facturation sera activée, sans changement de code.
    "gemini": {
        "gemini-3-flash-preview": "Gemini 3 Flash (rapide)",
        "gemini-3.1-pro-preview": "Gemini 3.1 Pro (le plus capable)",
    },
}

_instance_cache = {}


def active_provider_name(override=None):
    """Voir la docstring du module pour l'ordre de priorité complet."""
    if override:
        return override
    explicit = os.environ.get("CHATBOT_PROVIDER")
    if explicit:
        return explicit
    if os.environ.get("GEMINI_API_KEY"):
        return "gemini"
    return "fake"


def get_provider(provider=None, model=None, api_key=None):
    """`api_key` (optionnel, haute disponibilité — voir
    ai_provider_key_service.available_keys_for_rotation) : instancie le
    fournisseur avec CETTE clé précise plutôt que celle de la variable
    d'environnement. Le cache d'instances est alors tenu PAR clé (jamais
    partagé entre deux clés différentes du même provider/modèle, chacune
    a son propre client HTTP) — `api_key=None` (comportement historique,
    aucune clé DB configurée) continue de partager une unique instance par
    (provider, modèle), comme avant cette fonctionnalité."""
    name = active_provider_name(provider)
    provider_cls = PROVIDERS.get(name)
    if provider_cls is None:
        raise RuntimeError(f"Fournisseur IA inconnu : {name}")
    cache_key = (name, model, api_key)
    if cache_key not in _instance_cache:
        _instance_cache[cache_key] = provider_cls(model=model, api_key=api_key)
    return _instance_cache[cache_key]


# ── Sélection du modèle selon le plan d'abonnement ──────────────────────────
# Chaîne de secours ordonnée (provider, modèle) par plan — la seule table qui
# décrit "qui a droit à quoi". Invité et Free partagent la même entrée (un
# invité n'a pas de plan payant, get_plan() le traite déjà comme FREE).
MODEL_CHAIN_BY_PLAN = {
    "free": [
        ("gemini", "gemini-3-flash-preview"),
    ],
    "premium": [
        ("gemini", "gemini-3.1-pro-preview"),
        ("gemini", "gemini-3-flash-preview"),
    ],
    "ultra": [
        ("anthropic", "claude-sonnet-5"),
        ("gemini", "gemini-3.1-pro-preview"),
        ("gemini", "gemini-3-flash-preview"),
    ],
}

# Variable d'environnement attendue pour juger un fournisseur "disponible" —
# vérification statique (clé configurée), volontairement sans appel réseau
# pour rester rapide et totalement automatique à chaque message. Ollama
# (modèle local, aucune clé) est toujours considéré disponible statiquement.
_REQUIRED_ENV_KEY_BY_PROVIDER = {
    "gemini": "GEMINI_API_KEY",
    "anthropic": "ANTHROPIC_API_KEY",
}


def _has_credentials(provider_name):
    required_key = _REQUIRED_ENV_KEY_BY_PROVIDER.get(provider_name)
    if required_key is None:
        return True  # ollama (local) / fake (aucune API) : pas de clé à vérifier
    return bool(os.environ.get(required_key))


# ── Cache d'indisponibilité ──────────────────────────────────────────────────
# Évite de retenter à chaque message un couple (provider, modèle) dont l'appel
# précédent a échoué de façon DURABLE (quota Free Tier à 0, clé invalide,
# accès refusé, crédit épuisé — voir ProviderUnavailableError.durable dans
# webapp/chatbot/providers/base.py) : ces pannes ne se résolvent jamais toutes
# seules en quelques secondes, retenter ne fait qu'ajouter de la latence pour
# rien avant de retomber de toute façon sur le candidat suivant de la chaîne.
# Volontairement en mémoire process (comme cache.py) : perdre le cache au
# redémarrage est sans conséquence, le premier appel qui échoue le recrée.
UNAVAILABILITY_TTL_SECONDS = 15 * 60  # 15 minutes

_unavailability_cache = {}  # (provider, model) -> {"reason", "marked_at", "expires_at"}


def _label(provider_name, model):
    return f"{provider_name}:{model}" if model else provider_name


def _format_ttl_human(ttl_seconds):
    """Lisibilité des logs : "12h" plutôt que "720 minutes" pour un TTL long
    (quota journalier, clé invalide...) — voir gemini_provider.py::
    _classify_error, qui fixe des TTL très différents selon la famille de
    panne (5 min pour une rafale RPM, jusqu'à 24h pour une clé invalide)."""
    if ttl_seconds % 3600 == 0:
        return f"{ttl_seconds // 3600}h"
    if ttl_seconds >= 3600:
        return f"{ttl_seconds / 3600:.1f}h"
    return f"{ttl_seconds // 60} min"


def mark_unavailable(provider_name, model, reason, ttl_seconds=UNAVAILABILITY_TTL_SECONDS):
    """Met (provider, modèle) en cache d'indisponibilité pour `ttl_seconds` —
    appelé uniquement pour une ProviderUnavailableError avec durable=True
    (voir llm_fallback_service.generate()). `ttl_seconds` n'est plus figé à
    15 minutes pour toutes les pannes : un fournisseur peut transmettre un TTL
    adapté à la famille de panne détectée via ProviderUnavailableError.
    ttl_seconds (voir gemini_provider.py::_classify_error) — le défaut de ce
    paramètre ne s'applique qu'aux pannes qui ne précisent rien de plus fin."""
    now = time.time()
    _unavailability_cache[(provider_name, model)] = {
        "reason": reason, "marked_at": now, "expires_at": now + ttl_seconds,
    }
    logger.warning(
        "%s indisponible — raison : %s — expiration : %s.",
        _label(provider_name, model), reason, _format_ttl_human(ttl_seconds),
    )


def clear_unavailable(provider_name, model):
    """Supprime un éventuel cache d'indisponibilité — appelé après CHAQUE
    génération réussie (voir llm_fallback_service.generate()) : si le
    fournisseur venait d'être retenté après expiration et qu'il répond de
    nouveau, plus aucune raison de continuer à le considérer indisponible.
    N'op silencieux si rien n'était en cache (cas normal, immense majorité
    des appels)."""
    if _unavailability_cache.pop((provider_name, model), None) is not None:
        logger.info("%s de nouveau disponible — cache supprimé.", _label(provider_name, model))


def _is_marked_unavailable(provider_name, model):
    """True si (provider, modèle) est encore dans sa fenêtre d'indisponibilité
    — l'entrée expirée n'est pas supprimée ici (elle est soit rafraîchie par
    un nouvel échec via mark_unavailable(), soit effacée par un succès via
    clear_unavailable()) : ce n'est qu'une lecture, jamais une écriture
    silencieuse d'état."""
    entry = _unavailability_cache.get((provider_name, model))
    if entry is None:
        return False
    if time.time() >= entry["expires_at"]:
        logger.info("Nouvelle tentative %s (cache d'indisponibilité expiré).", _label(provider_name, model))
        return False
    remaining = int(entry["expires_at"] - time.time())
    logger.info(
        "%s ignoré (cache actif, expire dans %ds) — raison : %s",
        _label(provider_name, model), remaining, entry["reason"],
    )
    return True


def _load_chain_from_database(plan_value):
    """Reconstruit, en lecture seule, la chaîne (provider_key, model_name) du
    plan `plan_value` depuis ai_providers/subscription_ai_mapping — même
    format que MODEL_CHAIN_BY_PLAN[plan_value] ci-dessus. Utilisée par
    select_llm_for_user() comme SOURCE PRIORITAIRE de la chaîne de décision
    (voir _is_valid_chain) ; son résultat sert aussi, sans requête
    supplémentaire, à la comparaison de _compare_chain_with_database.

    Renvoie None (jamais d'exception) uniquement si la base n'a AUCUNE ligne
    de mapping pour ce plan, ou en cas d'erreur SQL — dans ces deux cas,
    select_llm_for_user() retombe immédiatement sur MODEL_CHAIN_BY_PLAN. Si
    des mappings existent mais que leurs fournisseurs sont désactivés/
    absents, la chaîne reconstruite (potentiellement vide, donc invalide) est
    renvoyée telle quelle : _is_valid_chain la rejettera et déclenchera le
    même repli."""
    try:
        mappings = ai_provider_service.list_mappings_for_subscription(plan_value)
        if not mappings:
            return None  # aucune ligne pour ce plan : rien à comparer, pas une divergence
        chain = []
        for mapping in mappings:
            provider = ai_provider_service.get_provider(mapping["provider_id"])
            if provider is None or not provider["enabled"]:
                continue  # fournisseur absent/désactivé : exclu de la chaîne reconstruite,
                          # mais la comparaison reste faite sur ce qui reste (chaîne possiblement vide)
            chain.append((provider["provider_key"], provider["model_name"]))
        return chain
    except Exception:
        logger.warning(
            "Lecture de la chaîne IA depuis la base impossible pour le plan %r (comparaison ignorée).",
            plan_value, exc_info=True,
        )
        return None


def _compare_chain_with_database(plan_value, static_chain, db_chain):
    """Shadow-mode de migration : journalise toute divergence entre
    `static_chain` (MODEL_CHAIN_BY_PLAN) et `db_chain` (déjà lu par
    _load_chain_from_database — jamais relu ici, pour ne pas doubler la
    requête SQL à chaque appel). N'influence jamais la décision : purement
    informatif, y compris maintenant que `db_chain` peut être réellement
    utilisé par select_llm_for_user() (voir _is_valid_chain ci-dessous)."""
    if db_chain is None or db_chain == static_chain:
        return
    logger.warning(
        "[AI CONFIG] Divergence détectée pour le plan %r.\nDatabase chain :\n%s\nStatic chain :\n%s",
        plan_value, db_chain, static_chain,
    )


def _is_valid_chain(chain):
    """Une chaîne (provider_key, model_name) est valide pour être utilisée
    par select_llm_for_user() si : elle existe et n'est pas vide, et qu'aucun
    de ses couples n'a un provider_key ou un model_name vide/None. Toute
    autre forme (None, [], ou une entrée incomplète) est invalide — repli
    immédiat sur MODEL_CHAIN_BY_PLAN, jamais une exception ni un candidat
    à moitié renseigné transmis plus loin dans la boucle de décision."""
    if not chain:
        return False
    return all(provider_name and model for provider_name, model in chain)


def select_llm_for_user(user, exclude=None):
    """Point UNIQUE de décision du fournisseur/modèle IA pour un utilisateur
    donné — jamais un réglage client, toute future évolution de la matrice
    plan -> modèle doit passer par cette fonction et par MODEL_CHAIN_BY_PLAN
    ci-dessus, jamais par une logique dupliquée ailleurs.

    Renvoie (provider_name, model) : le meilleur candidat selon le plan de
    `user`, en sautant :
    - les couples (provider, modèle) déjà présents dans `exclude` (utilisé
      par llm_fallback_service.generate() pour retenter le candidat suivant
      DANS LE MÊME message quand le précédent échoue réellement à l'usage) ;
    - les couples encore dans leur fenêtre de cache d'indisponibilité (voir
      _is_marked_unavailable() ci-dessus) — évite de retenter, à CHAQUE
      NOUVEAU message, un fournisseur qu'on sait déjà cassé pour un moment.
    L'exclusion se fait par COUPLE (provider, modèle), jamais par le seul nom
    de provider : le repli Premium Gemini Pro -> Gemini Flash partage le même
    provider ("gemini") avec un modèle différent, il ne doit donc jamais être
    sauté par erreur en excluant tout "gemini" d'un coup.

    CHATBOT_PROVIDER, s'il est défini explicitement (coupure d'urgence/ops,
    voir active_provider_name()), prime sur toute logique de plan : jamais de
    matrice plan -> modèle dans ce cas, le fournisseur forcé est utilisé tel
    quel avec son propre modèle par défaut (model=None).

    Origine de la chaîne plan -> (provider, modèle) : la base de données
    (ai_providers/subscription_ai_mapping, voir _load_chain_from_database) est
    désormais utilisée EN PRIORITÉ si elle renvoie une chaîne valide (voir
    _is_valid_chain) ; MODEL_CHAIN_BY_PLAN ne sert plus que de mécanisme de
    secours — base vide, mapping supprimé, plan inconnu de la base, erreur
    SQL, ou chaîne incomplète (provider_key/model vide) y font tous
    immédiatement retomber. Toute la suite de cette fonction (exclusion des
    couples déjà tentés, cache d'indisponibilité, vérification des
    identifiants, repli FakeProvider) est rigoureusement identique, quelle
    que soit l'origine de `chain`.

    Repli ultime si tous les candidats du plan sont exclus/indisponibles :
    ("fake", None) — jamais d'exception, le moteur local NovaMath répond
    toujours, même si aucune API n'est utilisable."""
    exclude = exclude or set()

    override = os.environ.get("CHATBOT_PROVIDER")
    if override and (override, None) not in exclude:
        return override, None

    # Owner/Developer Override (voir owner_service.py) + Mode test Owner
    # (voir owner_test_plan_service.py) : chaîne modèle du plan EFFECTIF pour
    # le compte configuré via NOVAMATH_OWNER_USER_ID uniquement — chaîne
    # Ultra par défaut (comportement historique, aucun plan de test actif),
    # ou celle du plan de test choisi (free/premium/ultra) sinon.
    # get_plan(user)/plan.value en base ne sont jamais modifiés, seul le
    # choix de la chaîne à utiliser ICI est supplanté (fail-closed par
    # défaut, aucun autre utilisateur n'est affecté).
    plan = owner_test_plan_service.effective_plan(user)
    static_chain = MODEL_CHAIN_BY_PLAN.get(plan.value, MODEL_CHAIN_BY_PLAN["free"])
    db_chain = _load_chain_from_database(plan.value)
    _compare_chain_with_database(plan.value, static_chain, db_chain)
    chain = db_chain if _is_valid_chain(db_chain) else static_chain
    for provider_name, model in chain:
        if (provider_name, model) in exclude:
            continue
        if _is_marked_unavailable(provider_name, model):
            continue
        if _has_credentials(provider_name):
            return provider_name, model
    return "fake", None


def available_models(provider=None):
    """Modèles disponibles pour le fournisseur actif : détection dynamique
    en priorité (ex: modèles réellement installés dans Ollama via /api/tags),
    repli sur le catalogue statique MODELS si la détection échoue ou ne
    retourne rien (fournisseur arrêté, catalogue non applicable...)."""
    name = active_provider_name(provider)
    try:
        detected = get_provider(provider=name).available_models()
    except Exception:
        detected = {}
    return detected or MODELS.get(name, {})


def health_check(provider=None):
    name = active_provider_name(provider)
    try:
        return {"provider": name, **get_provider(provider=name).health()}
    except Exception as exc:
        return {"provider": name, "ok": False, "detail": str(exc)}


def log_startup_banner():
    """Journalise, une fois au démarrage du serveur (voir server.py), le
    fournisseur IA réellement actif et pourquoi. Sert de garde-fou visible :
    un CHATBOT_PROVIDER oublié dans .env ne doit plus jamais se découvrir
    après coup — la raison exacte du choix apparaît dans les logs de
    démarrage, avant la première requête."""
    name = active_provider_name()
    border = "=" * 44
    lines = [border]
    if name == "fake":
        if os.environ.get("CHATBOT_PROVIDER") == "fake":
            reason = "CHATBOT_PROVIDER=fake défini explicitement"
        else:
            reason = "Aucune clé Gemini détectée (GEMINI_API_KEY absente) et aucun CHATBOT_PROVIDER défini"
        lines += ["IA Provider : FakeProvider", "Raison :", reason]
    else:
        try:
            instance = get_provider(provider=name)
            model = instance.current_model()
            key_present = instance.has_credentials()
        except Exception as exc:
            lines += [f"IA Provider : {name}", f"Erreur d'initialisation : {exc}"]
            lines.append(border)
            for line in lines:
                logger.info(line)
            return
        lines += [
            f"IA Provider : {name.capitalize()}",
            f"Model : {model}",
            f"API Key : {'détectée' if key_present else 'absente'}",
            "Fallback : FakeProvider désactivé",
        ]
    lines.append(border)
    for line in lines:
        logger.info(line)
