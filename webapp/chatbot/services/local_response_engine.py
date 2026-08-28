"""
Local Response Engine — orchestrateur unique des réponses locales (Response
Engine v2). Point d'entrée voulu, à terme, comme UNIQUE appel du pipeline
principal (`conversation_manager.py`) — mais volontairement PAS branché
aujourd'hui (voir consigne explicite) : ce module ne fait aucune décision
pédagogique lui-même, il se contente d'orchestrer les moteurs déjà validés :

    Intent Engine v2 + Student Context Resolver v2 (Phases 1-2)
        └── response_strategy.decide_strategy()          (Phase 3A, QUI répond)
                └── selon `strategy.engine` :
                    - math_engine.try_solve()              (calcul déterministe)
                    - rule_engine.try_handle()              (salutations/identité)
                    - knowledge_response_composer.compose() (Knowledge Engine
                      ET Search Service — les deux ont un chapter_id/topic_id
                      résolu et un intent, le composeur ne distingue pas leur
                      origine, voir sa docstring)
                    - local_knowledge_service.try_answer()  (Dashboard ET
                      Exercise Engine — déjà le point d'entrée unique et
                      TESTÉ de ces deux moteurs, réutilisé tel quel plutôt
                      que dupliqué ici)
                    - LLM : jamais appelé ici (voir "Portée", plus bas)

Ce module NE PRODUIT AUCUNE DONNÉE PÉDAGOGIQUE : chaque moteur cité ci-dessus
reste l'unique source de son propre contenu. `local_response_engine.py` ne
fait que décider, dans l'ordre, LEQUEL exécuter et gérer le repli si
l'exécution réelle échoue malgré une décision favorable (voir "Fallback
d'exécution").

── Portée (pourquoi le LLM n'est jamais appelé ici)
Le mission brief demande un point d'entrée unique `generate()` qui "choisit
automatiquement quel moteur appeler", LLM inclus dans le schéma. Mais appeler
réellement le LLM exige le streaming (`llm_fallback_service.generate()` est
un générateur), la gestion du provider actif (`provider_manager.py`), et la
persistance progressive des chunks (`db.add_message` dans un `finally`,
voir `conversation_manager.py`) — un modèle d'exécution fondamentalement
différent d'un simple retour de texte. Ajouter cela ici reviendrait à
recréer une partie du pipeline principal dans un module qui doit rester
"totalement indépendant" et non branché (consigne explicite). Le contrat de
`generate()` est donc : renvoyer soit un texte local prêt à l'emploi, soit
`should_use_llm=True` (texte `None`) — charge à l'appelant (Phase 3B, futur
branchement dans `conversation_manager.py`) d'invoquer le LLM lui-même
exactement comme il le fait déjà aujourd'hui.

── Fallback d'exécution (au-delà de la décision de response_strategy)
`response_strategy.decide_strategy()` a déjà éliminé les moteurs
indisponibles (voir ses sondes `_probe_*`) — mais entre la décision et
l'exécution réelle, un moteur peut échouer à produire un texte exploitable
dans de rares cas limites (ex. `local_knowledge_service.try_answer` renvoie
`None` si un template attendu manque, voir `response_composer.py`). Dans ce
cas, `generate()` NE RECOMMENCE PAS depuis Math Engine : il reprend la
cascade `response_strategy.PRIORITY_ORDER` À PARTIR du moteur choisi, dans
l'ordre déjà validé (Math → Rule → Knowledge/Search → Dashboard/Exercise →
Composer/Quiz/Recommandation réservés → LLM), puisque les moteurs plus
prioritaires ont déjà été jugés indisponibles par `response_strategy`. Toute
exception levée pendant l'exécution d'un moteur est absorbée (jamais
propagée) et traitée comme un échec de ce moteur, qui déclenche le repli
suivant — jamais d'erreur renvoyée à l'appelant.

── Cache (donnée, jamais texte)
Le cache porte UNIQUEMENT sur les données coûteuses à récolter :
- La décision de stratégie : déjà mise en cache par `response_strategy.py`
  lui-même (déterministe, voir sa suite de tests) — jamais recalculée ici.
- Le `StudentContext` : déjà mis en cache par `student_context_resolver.py`
  (TTL 5s) — un second appel dans cette même fenêtre ne relit aucun fichier.
- Le `context_summary` (ancien format, nécessaire à `local_knowledge_service`
  pour Dashboard/Exercise) : mis en cache ici (même esprit, TTL 5s) car
  aucun des modules existants ne l'expose déjà en cache sous ce format.

Le texte FINAL n'est en revanche JAMAIS mis en cache : `knowledge_response_
composer.py` et `response_composer.py` (Dashboard) choisissent tous deux une
formulation au hasard par conception ("ne plus jamais deux réponses
identiques", chantier précédent) — un cache de texte final annulerait cette
variabilité voulue. Voir rapport de phase pour la justification complète.
"""
import dataclasses
import logging
import time
from dataclasses import dataclass
from typing import Optional

from .. import math_engine, rule_engine, student_context_resolver
from ..context_builder import build_context_summary
from . import intent_service, knowledge_response_composer, local_knowledge_service, response_strategy

logger = logging.getLogger("chatbot.local_response_engine")

ENGINE_NAME = "local_response_engine"

# ── Cache du context_summary (ancien format, TTL court — même esprit que
# student_context_resolver.py et chatbot/cache.py) ──────────────────────────
_CONTEXT_SUMMARY_TTL_SECONDS = 5
_context_summary_cache = {}


def _get_context_summary(user, chapters_summary, context_summary=None, class_level=None):
    if context_summary is not None:
        return context_summary
    cache_key = (user["id"], class_level or "seconde")
    cached = _context_summary_cache.get(cache_key)
    if cached is not None:
        ts, value = cached
        if time.monotonic() - ts <= _CONTEXT_SUMMARY_TTL_SECONDS:
            return value
    value = build_context_summary(user, chapters_summary, class_level=class_level)
    _context_summary_cache[cache_key] = (time.monotonic(), value)
    return value


def _lazy(compute_fn):
    """Mémoïse `compute_fn` (sans argument) — appelée au plus une fois, lors
    du premier accès au getter renvoyé. `box` (liste à un élément) sert de
    cellule mutable capturée par la closure, seule façon de distinguer "pas
    encore calculé" d'un résultat valant `None`."""
    box = []

    def get():
        if not box:
            box.append(compute_fn())
        return box[0]

    return get


def clear_cache():
    """Vide tous les caches de données impliqués (context_summary local,
    StudentContext v2, décisions de stratégie) — utilisé par les tests pour
    repartir d'un état connu, jamais nécessaire en usage normal."""
    _context_summary_cache.clear()
    student_context_resolver.clear_cache()
    response_strategy.clear_cache()


def cache_stats():
    return {
        "context_summary_entries": len(_context_summary_cache),
        "strategy_cache": response_strategy.cache_stats(),
    }


@dataclass(frozen=True)
class LocalResponseResult:
    """Résultat de `generate()`. `text=None` et `should_use_llm=True` signifie
    littéralement "aucun moteur local ne peut répondre, appelle le LLM
    toi-même" — jamais une erreur silencieuse."""

    text: Optional[str]
    engine: str
    source: str
    should_use_llm: bool
    intent: str
    chapter_id: Optional[str]
    topic_id: Optional[str]
    strategy: Optional[response_strategy.ResponseStrategy]
    used_fallback: bool
    explanation: str
    # Chantier "fausse mémoire d'approche" (2026-08-22) : approche RÉELLEMENT
    # produite par le moteur exécuté (voir knowledge_response_composer.
    # _primary_approach) — None quand le moteur exécuté n'a pas de notion
    # d'approche (math_engine, rule_engine, dashboard/exercise) ou quand le
    # premier bloc de contenu ne correspond à aucune approche du vocabulaire
    # d'escalade. Jamais deviné à partir de `recommended_approach`.
    actual_approach: Optional[str] = None
    # Chantier "répétition des exemples" (2026-08-23) : ids d'exemples
    # RÉELLEMENT choisis pendant cette exécution (voir knowledge_response_
    # composer.ResponseDraft.new_exemple_ids), () pour tout moteur sans
    # notion d'exemple pédagogique (math_engine, rule_engine, dashboard/
    # exercise) — jamais devinés.
    new_exemple_ids: tuple = ()


def _intent_result_from_strategy(strategy):
    """Reconstruit le petit dict `{intent, chapter_id, notion_id, difficulty}`
    attendu par `local_knowledge_service.try_answer` — mêmes champs, mêmes
    noms, aucune nouvelle logique de correspondance."""
    return {
        "intent": strategy.intent,
        "chapter_id": strategy.chapter_id,
        "notion_id": strategy.topic_id,
        "difficulty": strategy.difficulty,
        "simplify": strategy.simplify,
    }


def _execute_engine(engine, strategy, user_message, user, student_context_getter, context_summary_getter, chatbot_settings):
    """Exécute RÉELLEMENT le moteur donné (contrairement aux sondes de
    `response_strategy`, qui ne font que détecter la disponibilité) et
    renvoie `(texte, actual_approach, new_exemple_ids)`, où `texte` est
    `None` si ce moteur échoue à répondre malgré la décision, `actual_
    approach` est `None` pour tout moteur sans notion d'approche
    pédagogique, et `new_exemple_ids` est `()` pour tout moteur sans notion
    d'exemple pédagogique.
    `student_context_getter`/`context_summary_getter` : appels
    paresseux (lazy) — un contexte n'est calculé que si le moteur choisi en a
    réellement besoin, jamais par avance."""
    if engine == response_strategy.ENGINE_MATH:
        return math_engine.try_solve(user_message), None, ()

    if engine == response_strategy.ENGINE_RULE:
        return rule_engine.try_handle(user_message), None, ()

    if engine in (response_strategy.ENGINE_KNOWLEDGE, response_strategy.ENGINE_SEARCH):
        draft = knowledge_response_composer.compose(
            strategy, student_context=student_context_getter(), chatbot_settings=chatbot_settings,
        )
        # Audit "le chatbot ne doit jamais donner l'impression d'abandonner"
        # (2026-07-26, épisode 2) : la cause racine du message froid affiché
        # à l'élève n'était PAS une absence de mode dégradé (déjà traité,
        # voir degraded_mode_service.py) mais un DÉCOUPLAGE en amont —
        # response_strategy._probe_knowledge_engine() peut juger ENGINE_
        # KNOWLEDGE éligible (sa propre recherche interne trouve une notion)
        # alors que chapter_id/topic_id (résolus séparément par
        # intent_service.classify()/le Student Context) restent None/None
        # pour CE message précis. knowledge_response_composer.compose() ne
        # peut alors rien composer et renvoie un texte de repli générique
        # (`notion_resolved=False`) — jamais une réponse à afficher telle
        # quelle : on la traite ici comme un ÉCHEC de ce moteur, exactement
        # comme un texte vide, pour que la cascade ci-dessous (search_service/
        # exercise/LLM) continue plutôt que de s'arrêter sur ce repli.
        if not draft.notion_resolved:
            return None, None, ()
        return draft.text, draft.primary_approach, draft.new_exemple_ids

    if engine in (response_strategy.ENGINE_DASHBOARD, response_strategy.ENGINE_EXERCISE):
        intent_result = _intent_result_from_strategy(strategy)
        return local_knowledge_service.try_answer(
            intent_result, user, context_summary_getter(), chatbot_settings, user_message=user_message,
            student_context=student_context_getter(),
        ), None, ()

    # Moteurs réservés (Response Composer générique/Quiz/Recommendation) :
    # jamais sélectionnés aujourd'hui par response_strategy (leurs sondes
    # renvoient toujours False), donc jamais atteints en pratique — gérés
    # ici pour que l'interface reste prête sans jamais lever d'erreur.
    return None, None, ()


def generate(
    user_message, user, chapters_summary=None, chatbot_settings=None, mentions=None,
    current_chapter_ref=None, current_topic_ref=None, history_rows=None,
    student_context=None, context_summary=None, use_cache=True, debug=False, class_level=None,
    learning_context=None, last_assistant_message=None,
    escalation_level=0, recommended_approach=None, used_exemple_ids=(),
):
    """Point d'entrée unique. Décide (`response_strategy`) puis EXÉCUTE
    réellement le moteur local retenu, avec repli en cascade si l'exécution
    échoue malgré la décision (voir docstring module). Ne lève jamais
    d'exception : toute erreur d'un moteur est absorbée et traitée comme une
    indisponibilité de ce moteur.

    `learning_context`/`last_assistant_message` (chantier "learning_context
    perdu par le Local Response Engine", 2026-08-22) : Current Learning
    Context de la conversation en cours, déjà résolu par l'appelant
    (conversation_manager.py, voir db.get_conversation_learning_context) —
    UNIQUEMENT transmis tel quel à response_strategy.decide_strategy(),
    jamais recalculé ni rechargé ici. Sans cela, la classification interne à
    ce module ignorait tout sujet déjà établi et pouvait dériver vers une
    notion sans rapport sur un message de suivi court (bug confirmé, audit
    du 2026-08-22 : "encore une autre façon" avec le sujet "Fonction
    dérivée"/"La valeur absolue" déjà établi retombait sur une notion sans
    rapport, faute de ce contexte).

    `escalation_level`/`recommended_approach` (chantier "escalade
    pédagogique", 2026-08-22) : état déjà calculé par
    conversation_manager._advance_escalation_state, transmis tel quel —
    AUCUN recalcul ici. Décorés sur le `strategy` déjà décidé par
    response_strategy.decide_strategy() (via dataclasses.replace, PAS un
    nouveau paramètre de decide_strategy() : ces champs n'influencent JAMAIS
    le choix du moteur ni le routage chapitre/notion, seulement le contenu
    composé une fois le moteur déjà choisi — voir knowledge_response_
    composer._content_plan)."""
    chatbot_settings = chatbot_settings or {}
    t0 = time.perf_counter()

    try:
        strategy = response_strategy.decide_strategy(
            user_message, user, chapters_summary=chapters_summary, chatbot_settings=chatbot_settings,
            mentions=mentions, current_chapter_ref=current_chapter_ref, current_topic_ref=current_topic_ref,
            history_rows=history_rows, student_context=student_context, use_cache=use_cache, debug=debug,
            class_level=class_level, learning_context=learning_context, last_assistant_message=last_assistant_message,
        )
        if strategy is not None:
            strategy = dataclasses.replace(
                strategy, escalation_level=escalation_level, recommended_approach=recommended_approach,
                used_exemple_ids=tuple(used_exemple_ids or ()),
            )
    except Exception:
        # Le Strategy Engine (Phase 3A, déjà validé) n'est pas protégé contre
        # une panne d'un moteur sondé (voir rapport de phase) — cette garde
        # assure que le contrat "jamais d'exception" du Local Response Engine
        # tient MÊME si une de ses dépendances amont échoue.
        logger.exception("Échec de response_strategy.decide_strategy() — repli immédiat sur le LLM.")
        return LocalResponseResult(
            text=None, engine=response_strategy.ENGINE_LLM, source=response_strategy.SOURCE_LLM,
            should_use_llm=True, intent=intent_service.NONE_INTENT, chapter_id=None, topic_id=None,
            strategy=None, used_fallback=True,
            explanation="La décision de stratégie a échoué de façon inattendue — filet de sécurité LLM.",
        )

    if strategy.engine == response_strategy.ENGINE_CLARIFICATION:
        result = LocalResponseResult(
            text=intent_service.CLARIFICATION_MESSAGE, engine=strategy.engine, source=strategy.source,
            should_use_llm=False, intent=strategy.intent, chapter_id=None, topic_id=None,
            strategy=strategy, used_fallback=False,
            explanation="Demande incompréhensible — réponse de clarification déterministe, jamais le LLM.",
        )
        if debug:
            _log_debug(result, (time.perf_counter() - t0) * 1000)
        return result

    # Contextes calculés paresseusement (une seule fois, réutilisés entre
    # tentatives de la cascade) — jamais avant qu'un moteur en ait besoin.
    def _resolve_student_context():
        return student_context if student_context is not None else student_context_resolver.resolve(
            user, chapters_summary=chapters_summary, chatbot_settings=chatbot_settings,
            mentions=mentions, current_chapter_ref=current_chapter_ref,
            current_topic_ref=current_topic_ref, history_rows=history_rows, use_cache=use_cache,
            class_level=class_level,
        )

    def _resolve_context_summary():
        return _get_context_summary(user, chapters_summary, context_summary, class_level=class_level)

    get_student_context = _lazy(_resolve_student_context)
    get_context_summary = _lazy(_resolve_context_summary)

    start_index = response_strategy.PRIORITY_ORDER.index(strategy.engine)
    cascade = response_strategy.PRIORITY_ORDER[start_index:]

    for position, engine in enumerate(cascade):
        if engine == response_strategy.ENGINE_LLM:
            break
        # Le premier moteur (position 0) a déjà été jugé éligible par
        # decide_strategy() — pas besoin de re-sonder. Pour un repli
        # (position > 0), on revérifie l'éligibilité RÉELLE (même sonde que
        # response_strategy) avant de tenter l'exécution : sans cela, un
        # moteur générique comme Search Service pourrait produire un texte
        # hors-sujet pour un intent de donnée locale déjà exclu par sa propre
        # sonde (`_probe_search_service`), voir rapport de phase.
        if position > 0 and not response_strategy.probe_engine_availability(engine, strategy, user_message):
            continue
        try:
            text, actual_approach, new_exemple_ids = _execute_engine(
                engine, strategy, user_message, user, get_student_context, get_context_summary, chatbot_settings,
            )
        except Exception:
            logger.exception("Échec d'exécution du moteur %s — repli sur le suivant.", engine)
            text, actual_approach, new_exemple_ids = None, None, ()
        if text:
            result = LocalResponseResult(
                text=text, engine=engine, source=response_strategy.SOURCE_LOCAL, should_use_llm=False,
                intent=strategy.intent, chapter_id=strategy.chapter_id, topic_id=strategy.topic_id,
                strategy=strategy, used_fallback=(position > 0),
                explanation=(
                    f"Moteur exécuté : {engine}"
                    + (f" (repli depuis {strategy.engine})" if position > 0 else "")
                ),
                actual_approach=actual_approach,
                new_exemple_ids=new_exemple_ids,
            )
            if debug:
                _log_debug(result, (time.perf_counter() - t0) * 1000)
            return result

    result = LocalResponseResult(
        text=None, engine=response_strategy.ENGINE_LLM, source=response_strategy.SOURCE_LLM, should_use_llm=True,
        intent=strategy.intent, chapter_id=strategy.chapter_id, topic_id=strategy.topic_id,
        strategy=strategy, used_fallback=(strategy.engine != response_strategy.ENGINE_LLM),
        explanation="Aucun moteur local n'a produit de réponse exploitable — filet de sécurité LLM.",
    )
    if debug:
        _log_debug(result, (time.perf_counter() - t0) * 1000)
    return result


def _log_debug(result, elapsed_ms):
    logger.debug(
        "\n── Local Response Engine (debug) ─────────────────────────────\n"
        "Intent             : %s\n"
        "Chapitre / Topic    : %s / %s\n"
        "Moteur exécuté      : %s (source=%s)\n"
        "Repli utilisé       : %s\n"
        "should_use_llm      : %s\n"
        "Temps               : %.4f ms\n"
        "───────────────────────────────────────────────────────────────\n%s",
        result.intent, result.chapter_id, result.topic_id, result.engine, result.source,
        result.used_fallback, result.should_use_llm, elapsed_ms, result.explanation,
    )
