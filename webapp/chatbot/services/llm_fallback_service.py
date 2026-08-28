"""
Point de sortie unique vers le fournisseur IA actif — Phase Q du chantier
v2.12 : le LLM ne doit plus être que le filet de sécurité, jamais le premier
réflexe (voir local_knowledge_service.py, interrogé en premier par
conversation_manager.py). Isole explicitement le seul module qu'un
changement de fournisseur IA (Claude, OpenAI, Mistral, Ollama, Gemini...)
doit impacter — provider_manager.py gère déjà le choix du fournisseur/modèle
selon le plan (voir provider_manager.select_llm_for_user()), ce module se
contente d'essayer la chaîne de secours renvoyée par cette fonction et de
retenter le candidat suivant si le précédent échoue réellement à l'usage
(clé absente, compte à crédit épuisé, quota dépassé...). Une panne durable
(voir ProviderUnavailableError.durable) est signalée à
provider_manager.mark_unavailable() pour ne plus être retentée à chaque
message pendant sa fenêtre de cache.

Mode dégradé (audit du 2026-07-26) : quand le candidat résolu est "fake"
(Gemini durablement indisponible), on tente D'ABORD degraded_mode_service.
try_answer() — reconstruit une vraie réponse pédagogique à partir du Current
Learning Context/de l'historique/de la banque d'exercices (voir sa docstring)
— avant de retomber sur le message générique de FakeProvider.stream_chat()
si rien n'a pu être déterminé. Ce branchement est le SEUL endroit qui diffère
selon le provider résolu ; la boucle de retry/exclusion ci-dessous reste
strictement identique pour tous les fournisseurs, jamais de code dupliqué
depuis gemini_provider.py."""
import logging
import time

import ai_provider_key_service
import db
import quota_service

from .. import provider_manager
from . import degraded_mode_service

logger = logging.getLogger("chatbot.llm_fallback_service")

# Valeurs par défaut IDENTIQUES aux anciennes constantes codées en dur — tant
# que l'admin n'a rien configuré dans Paramètres > IA (system_settings vide),
# le comportement reste strictement inchangé. Voir settings_service.py
# (SETTINGS_SCHEMA: ai_temperature_default/ai_max_response_tokens_default/
# ai_fallback_enabled) pour la validation/persistance côté admin.
_DEFAULT_TEMPERATURE = 0.6
# Chantier 6 (bug "réponses parfois coupées", 2026-08-25) : 1024 était
# systématiquement insuffisant pour une explication pédagogique longue avec
# les modèles Gemini 3 (voir thinking_config dans gemini_provider.py — le
# raisonnement interne partage ce même budget). Passé à 1536 par ce chantier —
# mais Chantier 9 (2026-08-25, même bug remonté malgré ce premier correctif) a
# reproduit la troncature PAR APPEL RÉEL à l'API (pas une supposition) avec
# 1536 : sur DEUX questions pédagogiques réalistes, SIMPLES (une seule méthode
# + un exemple, pas une question composite artificielle), finish_reason/
# stop_reason=MAX_TOKENS sur gemini-3.1-pro-preview (567/1536 tokens visibles
# seulement — le reste parti dans le raisonnement interne même en
# thinking_level="low") ET sur claude-sonnet-5 (stop_reason=max_tokens pile à
# 1536, réponse coupée en plein milieu). Passé à 2500 : mêmes deux questions
# retestées à cette valeur, complétées normalement (STOP/end_turn) sur les 3
# fournisseurs (gemini-3-flash-preview, gemini-3.1-pro-preview, claude-sonnet-5),
# avec un temps de génération mesuré (jusqu'à ~26s pour gemini-3.1-pro-preview)
# restant largement sous le timeout réseau de 45s (GeminiProvider.
# DEFAULT_TIMEOUT_MS/AnthropicProvider.DEFAULT_TIMEOUT_SECONDS, inchangés).
# 2500 reste loin du plafond admin de 4096 (settings_service.SETTINGS_SCHEMA).
# Impact coût : seules les réponses qui auraient de toute façon atteint
# l'ancien plafond de 1536 (donc déjà tronquées) peuvent consommer plus de
# tokens qu'avant ; delta théorique dans le pire cas (nouveau plafond de 2500
# réellement atteint) par rapport à 1536 : Gemini Flash +0,0029 $/appel,
# Gemini Pro +0,0116 $/appel, Claude Sonnet 5 +0,0096 $/appel (voir
# PRICING_USD_PER_MILLION_TOKENS, ai_provider_service.py) — négligeable face
# aux LLM_CALLS/jour (20 Premium, 40 Ultra, inchangés par ce chantier) et aux
# prix commerciaux (également inchangés).
_DEFAULT_MAX_TOKENS = 2500


def _ai_default_temperature():
    row = db.get_system_setting("ai_temperature_default")
    return float(row["value"]) if row else _DEFAULT_TEMPERATURE


def _ai_default_max_tokens():
    row = db.get_system_setting("ai_max_response_tokens_default")
    return int(row["value"]) if row else _DEFAULT_MAX_TOKENS


def _ai_fallback_enabled():
    row = db.get_system_setting("ai_fallback_enabled")
    return row["value"] == "1" if row else True

# TTL de cooldown appliqué à UNE clé (ai_provider_api_keys.quota_exceeded_until)
# quand son échec est classifié `durable` par le provider (ProviderUnavailableError,
# voir providers/base.py) — reprend le même TTL que celui déjà calculé pour le
# couple (provider, modèle) par ce fournisseur (exc.ttl_seconds), pour rester
# cohérent avec la classification fine déjà en place (quota RPM court, quota
# journalier long, clé invalide très long...). Une exception durable SANS
# ttl_seconds précis (repli générique) utilise ce TTL par défaut.
_DEFAULT_KEY_COOLDOWN_SECONDS = 15 * 60


def _stream_chunks(
    provider, provider_name, messages, system_prompt, chatbot_settings, intent_result, class_level,
    default_temperature, default_max_tokens,
):
    """Source des fragments à yielder pour CE candidat — identique à
    provider.stream_chat() pour tout fournisseur réel ; pour "fake", tente
    d'abord le mode dégradé (voir degraded_mode_service.try_answer) et ne
    retombe sur la réponse générique de FakeProvider que si rien n'a été
    trouvé (intent_result/class_level absents faute d'appelant qui les
    fournit, ex: aucun contexte transmis par un futur appelant).
    `default_temperature`/`default_max_tokens` : résolus UNE SEULE FOIS par
    generate() (jamais par candidat/tentative) — dict.get() évalue son
    argument par défaut avant même de tester la clé, donc les recalculer ici
    aurait relu ces réglages en base à chaque candidat essayé."""
    if provider_name == "fake":
        degraded_reply = degraded_mode_service.try_answer(intent_result, messages, class_level=class_level)
        if degraded_reply is not None:
            yield degraded_reply
            return
    yield from provider.stream_chat(
        messages, system_prompt,
        temperature=float(chatbot_settings.get("temperature", default_temperature)),
        max_tokens=int(chatbot_settings.get("max_tokens", default_max_tokens)),
    )


def generate(messages, system_prompt, chatbot_settings, user=None, call_info=None, intent_result=None, class_level=None):
    """Générateur de fragments texte. `user` : transmis à
    provider_manager.select_llm_for_user() pour résoudre le fournisseur/
    modèle selon le plan — jamais un réglage lu depuis chatbot_settings.
    `call_info` (dict optionnel, rempli par effet de bord) : reçoit
    provider/model/fallback_from/usage une fois la génération terminée (ou
    juste avant qu'une exception ne soit propagée), pour que l'appelant
    (conversation_manager.py) puisse journaliser exactement ce qui a été
    utilisé, y compris après un repli automatique. Depuis le branchement de
    l'observabilité réelle (ai_provider_service.record_llm_usage), reçoit
    aussi : `success` (bool), `error_type`/`error_message` (None si succès),
    `attempts` (nombre de candidats essayés), `elapsed_ms` (durée réelle de
    CET appel LLM, mesurée ici — jamais celle, plus large, du tour complet
    déjà mesurée par conversation_manager.py), `fallback_reason` (raison du
    tout premier échec ayant déclenché un repli, None si aucun repli) et
    `time_lost_before_fallback_ms` (temps cumulé passé sur les candidats qui
    ont échoué avant celui retenu). `intent_result`/`class_level`
    (optionnels) : transmis tels quels au mode dégradé ci-dessus si le
    candidat résolu est "fake" — ignorés pour tout autre fournisseur, jamais
    transmis à provider.stream_chat() (contrat ChatProvider inchangé, voir
    providers/base.py)."""
    if call_info is None:
        call_info = {}
    attempted = []
    tried = set()
    call_started_at = time.perf_counter()
    time_lost_before_fallback_ms = 0.0
    fallback_reason = None
    last_exc = None
    fallback_enabled = _ai_fallback_enabled()
    default_temperature = _ai_default_temperature()
    default_max_tokens = _ai_default_max_tokens()

    while True:
        provider_name, model = provider_manager.select_llm_for_user(user, exclude=tried)
        tried.add((provider_name, model))
        budget_exhausted = False

        # Haute disponibilité (rotation de clés) : plusieurs clés API pour ce
        # fournisseur peuvent être configurées en base (voir
        # ai_provider_key_service.py) — chacune est essayée AVANT de passer
        # au modèle/fournisseur suivant (voir la boucle `while True`
        # au-dessus). `[None]` = aucune clé DB configurée pour ce
        # fournisseur : comportement historique inchangé, une seule
        # tentative avec la clé de la variable d'environnement.
        key_rows = ai_provider_key_service.available_keys_for_rotation(provider_name)
        candidates = key_rows if key_rows else [None]

        for key_row in candidates:
            # Chantier 5 (protection de la marge) : budget LLM_CALLS
            # INDÉPENDANT de CHAT_MESSAGES (déjà consommé une seule fois plus
            # haut dans la pile, voir conversation_manager.check_and_increment_
            # quota) — vérifié ici, juste avant CHAQUE tentative réseau réelle,
            # jamais pour "fake" (aucun réseau, mode dégradé/local uniquement).
            # Si le budget est atteint : AUCUN appel réseau n'est effectué pour
            # ce candidat — on le traite comme indisponible et on continue
            # directement vers le candidat suivant de la chaîne (finira par
            # atteindre "fake"), exactement comme demandé : le message
            # utilisateur n'est jamais bloqué, CHAT_MESSAGES continue de
            # fonctionner normalement. consume() est atomique (voir
            # quota_service.py) : aucune course concurrente ne peut faire
            # dépasser ce budget, y compris avec des requêtes simultanées.
            if provider_name != "fake" and user is not None:
                try:
                    quota_service.consume(user, quota_service.QuotaType.LLM_CALLS)
                except quota_service.QuotaExceededError:
                    logger.info(
                        "Budget LLM_CALLS atteint pour l'utilisateur %s : aucun appel réseau vers %s, "
                        "repli direct vers le candidat suivant.",
                        user["id"], provider_name,
                    )
                    budget_exhausted = True
                    break
            api_key = key_row["api_key"] if key_row else None
            provider = provider_manager.get_provider(provider=provider_name, model=model, api_key=api_key)
            attempted.append(
                f"{provider_name}:{provider.current_model()}" + (f" [{key_row['label']}]" if key_row else "")
            )
            attempt_started_at = time.perf_counter()
            yielded_any = False
            try:
                for chunk in _stream_chunks(
                    provider, provider_name, messages, system_prompt, chatbot_settings, intent_result, class_level,
                    default_temperature, default_max_tokens,
                ):
                    yielded_any = True
                    yield chunk
                # Succès : si ce couple sortait tout juste de son cache
                # d'indisponibilité (retenté après expiration), on le confirme
                # de nouveau disponible — no-op silencieux si rien n'était en
                # cache. Idem pour un éventuel cooldown sur cette clé précise.
                provider_manager.clear_unavailable(provider_name, model)
                if key_row:
                    ai_provider_key_service.record_result(
                        key_row["id"], True, response_time_ms=(time.perf_counter() - attempt_started_at) * 1000,
                    )
                call_info["provider"] = provider_name
                call_info["model"] = provider.current_model()
                call_info["fallback_from"] = attempted[0] if len(attempted) > 1 else None
                call_info["usage"] = provider.last_usage
                call_info["success"] = True
                call_info["error_type"] = None
                call_info["error_message"] = None
                call_info["attempts"] = len(attempted)
                call_info["elapsed_ms"] = (time.perf_counter() - call_started_at) * 1000
                call_info["fallback_reason"] = fallback_reason
                call_info["time_lost_before_fallback_ms"] = time_lost_before_fallback_ms
                # Chantier 6 (bug "réponses parfois coupées") : jusqu'ici, un
                # arrêt par MAX_TOKENS/max_tokens (budget de réponse atteint,
                # voir _DEFAULT_MAX_TOKENS/ai_max_response_tokens_default
                # ci-dessus) était traité EXACTEMENT comme un STOP normal —
                # aucun log, rien ne distinguait une réponse tronquée d'une
                # réponse terminée naturellement, à aucun niveau du pipeline.
                # Purement diagnostique (aucun retry, aucune troncature
                # cachée à l'utilisateur ne dépendait déjà de ce log) : permet
                # de confirmer/infirmer par la volumétrie réelle en production
                # si ce budget est réellement la cause des coupures observées.
                finish_reason = getattr(provider, "last_finish_reason", None)
                call_info["finish_reason"] = finish_reason
                if finish_reason and "MAX_TOKENS" in str(finish_reason).upper():
                    logger.warning(
                        "Réponse tronquée par la limite de tokens (finish_reason=%s, "
                        "provider=%s, model=%s, max_tokens=%s, usage=%s) — utilisateur %s.",
                        finish_reason, provider_name, provider.current_model(),
                        chatbot_settings.get("max_tokens", default_max_tokens),
                        provider.last_usage, user["id"] if user else None,
                    )
                return
            except Exception as exc:
                last_exc = exc
                attempt_elapsed_ms = (time.perf_counter() - attempt_started_at) * 1000
                if fallback_reason is None:
                    fallback_reason = f"{type(exc).__name__}: {exc}"[:300]
                call_info["provider"] = provider_name
                call_info["model"] = provider.current_model()
                call_info["fallback_from"] = attempted[0] if len(attempted) > 1 else None
                call_info["usage"] = provider.last_usage
                call_info["success"] = False
                call_info["error_type"] = type(exc).__name__
                call_info["error_message"] = str(exc)[:500]
                call_info["attempts"] = len(attempted)
                call_info["elapsed_ms"] = (time.perf_counter() - call_started_at) * 1000

                # Panne DURABLE (voir ProviderUnavailableError.durable dans
                # providers/base.py — quota Free Tier à 0, clé invalide, accès
                # refusé, crédit épuisé) : mise en cache pour ne plus retenter
                # CE COUPLE (provider, modèle) à chaque message tant que le
                # cache est actif — appelé ICI, inconditionnellement sur toute
                # exception durable (comme avant ce mécanisme de rotation de
                # clés), jamais seulement quand une bascule a lieu : même une
                # exception qui sera immédiatement repropagée ci-dessous
                # (réponse déjà partiellement diffusée, ou "fake" épuisé) doit
                # mettre ce couple en cache s'il est structurellement cassé.
                if getattr(exc, "durable", False):
                    ttl_seconds = getattr(exc, "ttl_seconds", None)
                    if ttl_seconds is not None:
                        provider_manager.mark_unavailable(provider_name, model, reason=str(exc), ttl_seconds=ttl_seconds)
                    else:
                        provider_manager.mark_unavailable(provider_name, model, reason=str(exc))

                # Une panne APRÈS avoir déjà streamé du texte à l'élève ne peut
                # jamais être rejouée proprement (réponse partielle déjà
                # envoyée) : elle est propagée telle quelle, comme avant ce
                # mécanisme de repli. "fake" est le dernier maillon de la
                # chaîne (provider_manager.py) : s'il échoue aussi, il n'y a
                # plus rien à retenter — dans les deux cas, aucune bascule
                # réelle n'a lieu, jamais comptée comme un fallback pour la clé.
                if yielded_any or provider_name == "fake":
                    if key_row:
                        ai_provider_key_service.record_result(
                            key_row["id"], False, response_time_ms=attempt_elapsed_ms,
                            error=str(exc)[:500], fallback=False,
                        )
                    call_info["fallback_reason"] = fallback_reason
                    call_info["time_lost_before_fallback_ms"] = time_lost_before_fallback_ms
                    raise

                # Échec réel qui déclenche une bascule (clé suivante du même
                # fournisseur, sinon modèle/fournisseur suivant via la boucle
                # englobante) — comptabilisé comme fallback pour CETTE clé.
                if key_row:
                    durable = getattr(exc, "durable", False)
                    cooldown_seconds = getattr(exc, "ttl_seconds", None) if durable else None
                    if durable and cooldown_seconds is None:
                        cooldown_seconds = _DEFAULT_KEY_COOLDOWN_SECONDS
                    ai_provider_key_service.record_result(
                        key_row["id"], False, response_time_ms=attempt_elapsed_ms,
                        error=str(exc)[:500], fallback=True, quota_cooldown_seconds=cooldown_seconds,
                    )
                time_lost_before_fallback_ms += attempt_elapsed_ms
                if key_row:
                    logger.warning(
                        "Clé API %s (%s) indisponible (%s), rotation vers la clé suivante.",
                        key_row["label"], provider_name, exc,
                    )
                else:
                    logger.warning(
                        "Fournisseur IA %s indisponible (%s), repli sur le candidat suivant.",
                        provider_name, exc,
                    )
                continue  # clé suivante du même (provider, modèle) — ou dernière itération si `candidates == [None]`

        # Toutes les clés disponibles pour ce (provider, modèle) ont échoué
        # (mark_unavailable déjà appelé au bon moment DANS le except
        # ci-dessus, pour chaque tentative durable) : passe au candidat
        # suivant via select_llm_for_user (boucle `while True` englobante) —
        # SAUF si l'admin a désactivé le fallback automatique (Paramètres >
        # IA) : dans ce cas on ne bascule JAMAIS vers un AUTRE fournisseur/
        # modèle, l'échec remonte tel quel. La rotation entre plusieurs clés
        # du MÊME fournisseur ci-dessus n'est pas concernée par ce réglage
        # (ce n'est pas un changement de fournisseur, juste de la haute
        # disponibilité technique).
        #
        # Le réglage ai_fallback_enabled ne s'applique JAMAIS à un repli
        # causé par le budget LLM_CALLS (budget_exhausted=True) : ce n'est
        # pas une bascule de robustesse technique face à une panne réelle
        # (aucune exception `last_exc` n'a forcément été levée — potentiellement
        # None au tout premier candidat), c'est une protection financière qui
        # doit TOUJOURS dégrader silencieusement vers le candidat suivant
        # (voir le Chantier 5 : ne jamais bloquer/rediriger l'élève).
        if budget_exhausted:
            continue
        if not fallback_enabled:
            raise last_exc
        continue
