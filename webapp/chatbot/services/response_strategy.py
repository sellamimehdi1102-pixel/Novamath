"""
Response Strategy Engine — Phase 3A (Niveau 1, Response Engine v2).

Rôle UNIQUE de ce module : décider QUEL moteur doit répondre à une demande,
jamais produire lui-même une réponse. `decide_strategy()` renvoie une
`ResponseStrategy` (structure immuable) — aucun champ de cette structure ne
contient de texte destiné à l'élève.

Entrées consommées : Intent Engine v2 (`services/intent_service.py`),
Student Context Resolver v2 (`chatbot/student_context_resolver.py`),
Canonical IDs (`canonical_ids.py`) et les paramètres utilisateur
(`chatbot_settings`). Rien d'autre : ce module ne lit jamais directement
`auth.py`/`db.py`, il délègue toute lecture de données réelles à ces trois
briques déjà portées (Phases 1 et 2).

IMPORTANT (voir consigne explicite) : ce moteur n'est PAS câblé au pipeline
principal (`conversation_manager.py`). Il est entièrement testable en
isolation (voir webapp/tests/test_response_strategy.py). Le câblage réel
dans le pipeline est le sujet de la Phase 3B, volontairement hors périmètre
ici.

── Moteurs disponibles et ordre de priorité (fixé par le cahier des charges)
Une demande incompréhensible (voir intent_service.UNCLEAR) est un cas à part
qui prime sur tout le reste — comportement identique à ce que fait déjà
`conversation_manager.stream_reply()` aujourd'hui (retour immédiat avant même
le Rule Engine). Vient ensuite l'ordre demandé :

    1. Math Engine            (webapp/chatbot/math_engine.py, existant)
    2. Rule Engine             (webapp/chatbot/rule_engine.py, existant)
    3. Knowledge Engine        (webapp/chatbot/knowledge_engine.py, existant)
    4. Dashboard                (intent_service.LOCAL_DATA_INTENTS + response_composer/
                                 template_library, existant — "Dashboard" désigne ici tout
                                 intent de donnée locale : progression/statistique/
                                 dashboard/profil/paramètres/série)
    5. Search Service           (services/search_service.py, existant — grounding
                                 générique par recherche de cours quand aucun moteur
                                 plus spécifique n'a répondu)
    6. Exercise Engine          (RÉSERVÉ — pas encore un module dédié ; capacité
                                 sondée aujourd'hui via
                                 search_service.search_exercises_in_chapter, la même
                                 fonction qu'utilise déjà local_knowledge_service)
    7. Response Composer        (RÉSERVÉ — pas de template pour les intentions
                                 COURS/RESUME/METHODE/PROPRIETE/DEMONSTRATION/INDICE/
                                 RAPPEL/REVISION/REFORMULATION aujourd'hui ; sonde
                                 toujours indisponible, voir _probe_response_composer)
    8. Quiz Engine               (RÉSERVÉ — aucune génération de quiz locale n'existe ;
                                 local_knowledge_service exclut explicitement QUIZ)
    9. Recommendation Engine    (RÉSERVÉ — action_cards_service ne fait que suggérer des
                                 cartes après coup, ce n'est pas un moteur de réponse)
   10. LLM                      (filet de sécurité ultime, toujours disponible)

Les moteurs 7/8/9 n'existent pas encore : leurs sondes (`_probe_*`) sont
présentes avec la même signature que les moteurs réels, documentées, et
renvoient toujours `False` — l'interface est prête, l'implémentation viendra
avec une phase future sans toucher à `decide_strategy()`.

── Score de confiance (documenté, plafonné à 100)
    Moteur disponible                              : +30
    Identifiant (chapitre_id/topic_id) résolu       : +20
    Intent reconnu (ni NONE_INTENT, ni UNCLEAR)     : +20
    Contexte élève complet                          : +15
    Historique de conversation utile                : +10
    Paramètres utilisateur disponibles              : +5
                                                        ────
                                                      100 max

Chaque composant est additif et indépendant (un intent reconnu sans
chapitre résolu, par exemple pour "Salut", est possible et donne un score
plus bas mais toujours cohérent). `ResponseStrategy.explanation` détaille
la décomposition exacte pour CHAQUE décision — jamais un score sans
justification.

── Cache
Une paire (utilisateur, message, contexte pertinent) identique renvoie
toujours la même décision (déterminisme explicitement demandé) — un cache
mémoire process-local (LRU, même esprit que `chatbot/cache.py`) évite de
recalculer une décision déjà connue. Voir `clear_cache()`/`cache_stats()`.
"""
import logging
import time
from dataclasses import dataclass
from typing import Optional

import canonical_ids

from .. import cache, knowledge_engine, math_engine, rule_engine, student_context_resolver
from . import intent_service, mentions_service, search_service, template_library

logger = logging.getLogger("chatbot.response_strategy")

# ── Identifiants de moteurs ──────────────────────────────────────────────────
ENGINE_CLARIFICATION = "clarification"
ENGINE_MATH = "math_engine"
ENGINE_RULE = "rule_engine"
ENGINE_KNOWLEDGE = "knowledge_engine"
ENGINE_DASHBOARD = "dashboard"
ENGINE_SEARCH = "search_service"
ENGINE_EXERCISE = "exercise_engine"
ENGINE_COMPOSER = "response_composer"
ENGINE_QUIZ = "quiz_engine"
ENGINE_RECOMMENDATION = "recommendation_engine"
ENGINE_LLM = "llm"

# Ordre de priorité EXACT demandé (hors clarification, cas à part traité en
# premier — voir docstring module). Exposé pour l'inspection/les tests, pas
# utilisé par un simple parcours de liste dans decide_strategy() : chaque
# moteur a des conditions d'éligibilité différentes (voir les _probe_*).
PRIORITY_ORDER = [
    ENGINE_MATH, ENGINE_RULE, ENGINE_KNOWLEDGE, ENGINE_DASHBOARD, ENGINE_SEARCH,
    ENGINE_EXERCISE, ENGINE_COMPOSER, ENGINE_QUIZ, ENGINE_RECOMMENDATION, ENGINE_LLM,
]

# Moteurs pas encore implémentés (interface prête, toujours indisponible).
RESERVED_FUTURE_ENGINES = {ENGINE_EXERCISE, ENGINE_COMPOSER, ENGINE_QUIZ, ENGINE_RECOMMENDATION}

SOURCE_LOCAL = "LOCAL"
SOURCE_LLM = "LLM"

# ── Poids du score de confiance (documentés dans la docstring module) ───────
SCORE_ENGINE_AVAILABLE = 30
SCORE_IDENTIFIANT_RESOLU = 20
SCORE_INTENT_RECONNU = 20
SCORE_CONTEXTE_COMPLET = 15
SCORE_HISTORIQUE_UTILE = 10
SCORE_PARAMETRES_DISPONIBLES = 5
SCORE_MAX = 100


@dataclass(frozen=True)
class ResponseStrategy:
    """Décision immuable du Strategy Engine — jamais de texte de réponse ici.
    `fallback` : filet de sécurité ultime si le moteur choisi échoue
    réellement à produire une réponse au moment de la génération (Phase 3B) —
    toujours "llm" sauf quand le moteur choisi EST déjà "llm" (None, plus rien
    en dessous)."""

    source: str  # SOURCE_LOCAL ou SOURCE_LLM
    engine: str  # un des ENGINE_*
    confidence: int  # 0-100
    intent: str
    chapter_id: Optional[str]
    topic_id: Optional[str]
    quantity: Optional[int]
    difficulty: Optional[str]
    mode: Optional[str]
    should_use_llm: bool
    fallback: Optional[str]
    explanation: str
    simplify: bool = False
    cache_hit: bool = False
    class_level: Optional[str] = None
    # Escalade pédagogique (chantier "repeated_incomprehension insuffisant",
    # 2026-08-22) : PAS calculés ici (aucune logique de routage nouvelle) —
    # décorés après coup sur le résultat de decide_strategy() par
    # local_response_engine.generate() via dataclasses.replace(), à partir de
    # l'état déjà calculé par conversation_manager._advance_escalation_state.
    # Champs optionnels : aucune instanciation existante de ResponseStrategy
    # n'a besoin d'y toucher.
    escalation_level: int = 0
    recommended_approach: Optional[str] = None
    # Chantier "répétition des exemples" (2026-08-23) : ids des exemples déjà
    # montrés dans CETTE conversation (voir conversation_manager.
    # _commit_used_exemple), décoré après coup exactement comme escalation_
    # level/recommended_approach ci-dessus — jamais recalculé ici, aucune
    # logique de routage nouvelle. Lu par knowledge_response_composer.compose()
    # pour exclure ces ids du tirage d'exemple.
    used_exemple_ids: tuple = ()


# ── Cache (LRU mémoire process, réutilise cache.LRUCache/normalize_message) ─
_CACHE_MAX_ENTRIES = 500
_cache = cache.LRUCache(_CACHE_MAX_ENTRIES)


def _mentions_signature(mentions):
    """Représentation hashable des mentions "@" pour la clé de cache — un
    ordre différent de mentions identiques compte comme un contexte
    identique (trié), une mention en plus/en moins compte comme différent."""
    if not mentions:
        return ()
    return tuple(sorted(tuple(sorted((m or {}).items())) for m in mentions))


def make_cache_key(user_id, user_message, current_chapter_ref, current_topic_ref, chatbot_settings, mentions, class_level=None, learning_context=None):
    cs = chatbot_settings or {}
    # `learning_context` (chantier continuité conversationnelle, 2026-08-22) :
    # sans lui, un message ambigu identique ("développe", "pourquoi ?"...)
    # renverrait la même décision mise en cache dans deux conversations aux
    # sujets différents — même défaut que celui déjà corrigé pour le cache de
    # réponses LLM (voir chatbot/cache.py::make_key, paramètre `topic`).
    lc = learning_context or {}
    return (
        user_id,
        class_level or "seconde",
        cache.normalize_message(user_message),
        current_chapter_ref,
        current_topic_ref,
        cs.get("mode"),
        cs.get("responseLength"),
        _mentions_signature(mentions),
        lc.get("chapter_id"),
        lc.get("notion_id"),
    )


def _cache_get(key):
    return _cache.get(key)


def _cache_set(key, value):
    _cache.set(key, value)


def clear_cache():
    """Vide le cache de décisions — utilisé par les tests pour repartir d'un
    état connu, jamais nécessaire en usage normal."""
    _cache.clear()


def cache_stats():
    """Taille actuelle du cache — utilisé par le benchmark, jamais nécessaire
    en usage normal."""
    return {"entries": len(_cache), "max_entries": _CACHE_MAX_ENTRIES}


# ── Sondes de capacité par moteur ────────────────────────────────────────────
# Chaque sonde répond à une seule question : "ce moteur peut-il répondre ?" —
# jamais "voici sa réponse". Pour Math/Rule/Knowledge Engine, qui n'exposent
# pas de fonction de détection séparée de leur fonction de résolution
# (déterministe, sans IA — voir leurs docstrings respectives), la sonde
# appelle la fonction existante et ne conserve que `résultat is not None` :
# aucune logique de correspondance n'est dupliquée ici, et aucun texte
# produit n'est jamais renvoyé par ce module.
def _probe_math_engine(user_message):
    return math_engine.try_solve(user_message) is not None


def _probe_rule_engine(user_message):
    return rule_engine.try_handle(user_message) is not None


def _probe_knowledge_engine(user_message, class_level=None):
    return knowledge_engine.try_answer_definition(user_message, class_level=class_level) is not None


def _probe_dashboard(intent):
    """"Dashboard" désigne ici tout intent de donnée locale déjà répondu par
    response_composer.py + template_library.py (progression/statistique/
    dashboard/profil/paramètres/série) — même périmètre que
    intent_service.LOCAL_DATA_INTENTS."""
    return intent in intent_service.LOCAL_DATA_INTENTS and intent in template_library.TEMPLATES


def _probe_search_service(user_message, intent, class_level=None):
    """Grounding générique par recherche de cours (TF-IDF, même seuil que
    intent_service._detect_chapter) — ne s'applique pas à un EXERCICE (Exercise
    Engine, position 6) ni aux données locales (Dashboard, position 4, déjà
    tranché avant que cette sonde soit atteinte)."""
    if intent == intent_service.EXERCICE or intent in intent_service.LOCAL_DATA_INTENTS:
        return False, None
    matches = search_service.search(user_message, scope=[search_service.SCOPE_COURS], limit=1, class_level=class_level)
    if matches and matches[0]["score"] >= search_service.TFIDF_WEAK_THRESHOLD:
        return True, matches[0]
    return False, None


def _probe_exercise_engine(intent, chapter_id, difficulty, user_message, class_level=None):
    """RÉSERVÉ (interface prête) : aucun module `exercise_engine.py` dédié
    n'existe encore — la capacité réelle vient aujourd'hui de
    search_service.search_exercises_in_chapter (déjà utilisée par
    local_knowledge_service._try_exercise_answer), réutilisée ici sans
    duplication de logique."""
    if intent != intent_service.EXERCICE or not chapter_id:
        return False, []
    matched = search_service.search_exercises_in_chapter(
        chapter_id, query=user_message, difficulty=difficulty, limit=1, class_level=class_level,
    )
    return bool(matched), matched


def _probe_response_composer(intent):
    """RÉSERVÉ : aucun template n'existe encore (template_library.py) pour
    les intentions COURS/RESUME/METHODE/PROPRIETE/DEMONSTRATION/INDICE/
    RAPPEL/REVISION/REFORMULATION (Intent Engine v2) au-delà des données
    locales déjà couvertes par Dashboard. Toujours indisponible tant que ce
    travail n'est pas fait (hors périmètre Phase 3A) — interface prête pour
    qu'une phase future n'ait qu'à enrichir template_library.py, sans
    modifier decide_strategy()."""
    return False


def _probe_quiz_engine(intent):
    """RÉSERVÉ : aucune génération de quiz locale n'existe aujourd'hui —
    local_knowledge_service exclut explicitement l'intent QUIZ (voir
    webapp/tests/test_chatbot_routing.py::test_local_knowledge_service_ne_repond_pas_au_quiz).
    Toujours indisponible."""
    return False


def _probe_recommendation_engine(intent):
    """RÉSERVÉ : action_cards_service.build_cards() ne fait que suggérer des
    cartes APRÈS une réponse déjà produite — ce n'est pas un moteur capable de
    répondre à la place d'un autre. Toujours indisponible."""
    return False


def probe_engine_availability(engine, strategy, user_message):
    """API PUBLIQUE (additive, Phase 3A bis) : ré-évalue si `engine` peut
    répondre à `user_message` compte tenu d'une `ResponseStrategy` déjà
    décidée (chapter_id/intent/difficulty déjà résolus) — réutilise EXACTEMENT
    les mêmes sondes que `decide_strategy()`, jamais une nouvelle logique de
    correspondance. Sert à `local_response_engine.py` pour un repli en
    cascade fidèle aux mêmes règles d'éligibilité (ex. ne jamais retomber sur
    Search Service pour un intent de donnée locale comme PROGRESSION, déjà
    exclu par `_probe_search_service`)."""
    if engine == ENGINE_MATH:
        return _probe_math_engine(user_message)
    if engine == ENGINE_RULE:
        return _probe_rule_engine(user_message)
    if engine == ENGINE_KNOWLEDGE:
        return _probe_knowledge_engine(user_message, class_level=strategy.class_level)
    if engine == ENGINE_DASHBOARD:
        return _probe_dashboard(strategy.intent)
    if engine == ENGINE_SEARCH:
        found, _match = _probe_search_service(user_message, strategy.intent, class_level=strategy.class_level)
        return found
    if engine == ENGINE_EXERCISE:
        available, _matched = _probe_exercise_engine(
            strategy.intent, strategy.chapter_id, strategy.difficulty, user_message, class_level=strategy.class_level,
        )
        return available
    if engine == ENGINE_COMPOSER:
        return _probe_response_composer(strategy.intent)
    if engine == ENGINE_QUIZ:
        return _probe_quiz_engine(strategy.intent)
    if engine == ENGINE_RECOMMENDATION:
        return _probe_recommendation_engine(strategy.intent)
    return False


# ── Score de confiance ───────────────────────────────────────────────────────
def _context_is_complete(student_context):
    stats = (student_context or {}).get("statistiques") or {}
    return bool((student_context or {}).get("chapitre_courant")) or (stats.get("total_exercices") or 0) > 0


def _score_components(intent, chapter_id, topic_id, student_context, chatbot_settings):
    components = [("Moteur disponible", SCORE_ENGINE_AVAILABLE)]
    if chapter_id or topic_id:
        components.append(("Identifiant (chapitre/topic) résolu", SCORE_IDENTIFIANT_RESOLU))
    if intent not in (intent_service.NONE_INTENT, intent_service.UNCLEAR):
        components.append(("Intent reconnu", SCORE_INTENT_RECONNU))
    if _context_is_complete(student_context):
        components.append(("Contexte élève complet", SCORE_CONTEXTE_COMPLET))
    if (student_context or {}).get("historique_conversation"):
        components.append(("Historique de conversation utile", SCORE_HISTORIQUE_UTILE))
    parametres = (student_context or {}).get("parametres") or {}
    if (chatbot_settings or {}) or parametres.get("mode"):
        components.append(("Paramètres utilisateur disponibles", SCORE_PARAMETRES_DISPONIBLES))
    score = min(sum(points for _, points in components), SCORE_MAX)
    return score, components


def _build_explanation(engine, components, fallback):
    lines = [f"Moteur choisi : {engine}"]
    for label, points in components:
        lines.append(f"  + {points:>3} — {label}")
    lines.append(f"Score total : {sum(p for _, p in components)}/100")
    lines.append(f"Filet de sécurité : {fallback}" if fallback else "Filet de sécurité : aucun (déjà le LLM)")
    return "\n".join(lines)


def _build_strategy(engine, intent, chapter_id, topic_id, quantity, difficulty, mode, student_context, chatbot_settings, simplify=False):
    score, components = _score_components(intent, chapter_id, topic_id, student_context, chatbot_settings)
    fallback = None if engine == ENGINE_LLM else ENGINE_LLM
    source = SOURCE_LLM if engine == ENGINE_LLM else SOURCE_LOCAL
    return ResponseStrategy(
        source=source, engine=engine, confidence=score, intent=intent,
        chapter_id=chapter_id, topic_id=topic_id, quantity=quantity, difficulty=difficulty,
        mode=mode, should_use_llm=(engine == ENGINE_LLM), fallback=fallback,
        explanation=_build_explanation(engine, components, fallback), simplify=simplify,
        class_level=(student_context or {}).get("class_level"),
    )


def _clarification_strategy(mode):
    explanation = (
        f"Moteur choisi : {ENGINE_CLARIFICATION}\n"
        f"  + 100 — Demande incompréhensible détectée (intent_service._is_gibberish)\n"
        "Score total : 100/100\n"
        "Filet de sécurité : aucun (réponse de clarification déterministe, toujours fiable)"
    )
    return ResponseStrategy(
        source=SOURCE_LOCAL, engine=ENGINE_CLARIFICATION, confidence=100,
        intent=intent_service.UNCLEAR, chapter_id=None, topic_id=None, quantity=None,
        difficulty=None, mode=mode, should_use_llm=False, fallback=None, explanation=explanation,
    )


def _log_debug(strategy, student_context, elapsed_ms, cache_hit):
    logger.debug(
        "\n── Response Strategy Engine (debug) ──────────────────────────\n"
        "Intent            : %s\n"
        "Chapitre / Topic   : %s / %s\n"
        "Student Context    : chapitre_courant=%s, mode=%s\n"
        "Décision           : %s (source=%s)\n"
        "Score              : %s/100\n"
        "Fallback           : %s\n"
        "Cache              : %s (%.4f ms)\n"
        "───────────────────────────────────────────────────────────────\n%s",
        strategy.intent, strategy.chapter_id, strategy.topic_id,
        (student_context or {}).get("chapitre_courant"), strategy.mode,
        strategy.engine, strategy.source, strategy.confidence, strategy.fallback,
        "HIT" if cache_hit else "MISS", elapsed_ms, strategy.explanation,
    )


# ── Point d'entrée public ────────────────────────────────────────────────────
def decide_strategy(
    user_message, user, chapters_summary=None, chatbot_settings=None, mentions=None,
    current_chapter_ref=None, current_topic_ref=None, history_rows=None,
    student_context=None, use_cache=True, debug=False, class_level=None,
    learning_context=None, last_assistant_message=None,
):
    """Décide quel moteur doit répondre à `user_message`. Ne produit et ne
    renvoie AUCUN texte de réponse — uniquement une `ResponseStrategy`.

    `student_context` (optionnel) : permet d'injecter un StudentContext déjà
    calculé (tests, ou réutilisation d'un appel récent côté appelant) — sinon
    calculé ici via `student_context_resolver.resolve()` (Phase 2).
    `use_cache=True` (par défaut) : deux appels identiques (même utilisateur,
    même message normalisé, même chapitre/topic/mode/longueur/mentions)
    renvoient la même décision sans recalcul — déterminisme garanti par
    construction (voir docstring module).
    `learning_context`/`last_assistant_message` (chantier continuité
    conversationnelle, 2026-08-22) : Current Learning Context de la
    conversation en cours et dernier message assistant — transmis tels quels
    à intent_service.classify() pour que ce moteur (RÉELLEMENT actif pour
    Knowledge/Search Engine, pas seulement en aparté, voir conversation_
    manager._try_local_response_engine) bénéficie des mêmes corrections que
    le pipeline principal (messages courts, non-écrasement d'un sujet déjà
    établi) plutôt que de reclassifier le message hors de tout contexte."""
    chatbot_settings = chatbot_settings or {}
    t0 = time.perf_counter()

    # `class_level` : si un StudentContext est déjà fourni, sa propre classe
    # (déjà résolue par l'appelant) prime toujours — jamais deux sources de
    # vérité pour la même classe au sein d'un même appel.
    effective_class_level = (student_context or {}).get("class_level") or class_level

    cache_key = None
    if use_cache:
        cache_key = make_cache_key(
            user["id"], user_message, current_chapter_ref, current_topic_ref, chatbot_settings, mentions,
            class_level=effective_class_level, learning_context=learning_context,
        )
        cached = _cache_get(cache_key)
        if cached is not None:
            result = ResponseStrategy(**{**cached.__dict__, "cache_hit": True})
            if debug:
                _log_debug(result, student_context, (time.perf_counter() - t0) * 1000, cache_hit=True)
            return result

    if student_context is None:
        student_context = student_context_resolver.resolve(
            user, chapters_summary=chapters_summary, chatbot_settings=chatbot_settings,
            mentions=mentions, current_chapter_ref=current_chapter_ref, current_topic_ref=current_topic_ref,
            history_rows=history_rows, use_cache=use_cache, class_level=class_level,
        )

    # Contexte minimal requis par intent_service.classify (repli sur le
    # chapitre en cours) — dérivé du StudentContext déjà calculé, jamais relu
    # séparément via context_builder (voir Phase 2).
    pseudo_context_summary = {"chapters_in_progress": (student_context.get("dashboard") or {}).get("chapitres_en_cours") or []}
    intent_result = intent_service.classify(
        user_message, pseudo_context_summary, class_level=student_context.get("class_level"),
        learning_context=learning_context, last_assistant_message=last_assistant_message,
    )
    intent = intent_result["intent"]

    # Mention "@" seule (Phase R, inchangé) : une intention directe tout
    # aussi locale qu'une phrase tapée.
    mention_intent = mentions_service.single_data_mention_intent(user_message, mentions)
    if mention_intent:
        intent = mention_intent

    chapter_id = canonical_ids.resolve_chapter_id(intent_result.get("chapter_id")) or student_context.get("chapitre_courant")
    topic_id = intent_result.get("notion_id") or student_context.get("topic_courant")
    quantity = intent_result.get("quantity")
    difficulty = intent_result.get("difficulty")
    mode = (student_context.get("parametres") or {}).get("mode") or chatbot_settings.get("mode")

    def finalize(strategy):
        if cache_key is not None:
            _cache_set(cache_key, strategy)
        if debug:
            _log_debug(strategy, student_context, (time.perf_counter() - t0) * 1000, cache_hit=False)
        return strategy

    # 0. Demande incompréhensible — priorité absolue (comportement identique
    #    à conversation_manager.stream_reply aujourd'hui).
    if intent == intent_service.UNCLEAR:
        return finalize(_clarification_strategy(mode))

    # 1. Math Engine
    if _probe_math_engine(user_message):
        return finalize(_build_strategy(
            ENGINE_MATH, intent, chapter_id, topic_id, quantity, difficulty, mode,
            student_context, chatbot_settings, simplify=intent_result.get("simplify", False),
        ))

    # 2. Rule Engine
    if _probe_rule_engine(user_message):
        return finalize(_build_strategy(
            ENGINE_RULE, intent, chapter_id, topic_id, quantity, difficulty, mode,
            student_context, chatbot_settings, simplify=intent_result.get("simplify", False),
        ))

    # 3. Knowledge Engine
    if _probe_knowledge_engine(user_message, class_level=student_context.get("class_level")):
        return finalize(_build_strategy(
            ENGINE_KNOWLEDGE, intent, chapter_id, topic_id, quantity, difficulty, mode,
            student_context, chatbot_settings, simplify=intent_result.get("simplify", False),
        ))

    # 4. Dashboard (données locales : progression/statistique/dashboard/
    #    profil/paramètres/série)
    if _probe_dashboard(intent):
        return finalize(_build_strategy(
            ENGINE_DASHBOARD, intent, chapter_id, topic_id, quantity, difficulty, mode,
            student_context, chatbot_settings, simplify=intent_result.get("simplify", False),
        ))

    # 5. Search Service (grounding générique par recherche de cours) — cette
    #    sonde refait sa PROPRE recherche brute sur `user_message`, sans
    #    reranking de titre ni connaissance du Current Learning Context (voir
    #    _probe_search_service). Un score faible mais réel (≥
    #    TFIDF_WEAK_THRESHOLD) écrasait alors silencieusement un routage déjà
    #    correctement protégé par intent_service._detect_chapter (confidence
    #    "inherited" = sujet déjà établi, qu'un simple signal faible ne doit
    #    jamais pouvoir remplacer — voir sa docstring). Bug réel confirmé :
    #    "comment dérivé une fonction ?" avec pour sujet en cours "Fonction
    #    dérivée" faisait dériver la réponse vers "Fonction exponentielle"
    #    (score brut 0.157) alors qu'intent_service avait déjà correctement
    #    tranché "inherited" (audit du 2026-08-22). Ne PAS écraser chapter_id/
    #    topic_id dans ce seul cas : intent_service reste l'UNIQUE source de
    #    vérité du routage quand il a déjà décidé de protéger le contexte.
    found, match = _probe_search_service(user_message, intent, class_level=student_context.get("class_level"))
    if found:
        if intent_result.get("topic_confidence") != "inherited":
            topic_id = match.get("notion_id") or topic_id
            chapter_id = match.get("chapter_id") or chapter_id
        return finalize(_build_strategy(
            ENGINE_SEARCH, intent, chapter_id, topic_id, quantity, difficulty, mode,
            student_context, chatbot_settings, simplify=intent_result.get("simplify", False),
        ))

    # 6. Exercise Engine (réservé, capacité sondée via search_service)
    available, _matched = _probe_exercise_engine(
        intent, chapter_id, difficulty, user_message, class_level=(student_context or {}).get("class_level"),
    )
    if available:
        return finalize(_build_strategy(
            ENGINE_EXERCISE, intent, chapter_id, topic_id, quantity, difficulty, mode,
            student_context, chatbot_settings, simplify=intent_result.get("simplify", False),
        ))

    # 7. Response Composer (réservé, toujours indisponible aujourd'hui)
    if _probe_response_composer(intent):
        return finalize(_build_strategy(
            ENGINE_COMPOSER, intent, chapter_id, topic_id, quantity, difficulty, mode,
            student_context, chatbot_settings, simplify=intent_result.get("simplify", False),
        ))

    # 8. Quiz Engine (réservé, toujours indisponible aujourd'hui)
    if _probe_quiz_engine(intent):
        return finalize(_build_strategy(
            ENGINE_QUIZ, intent, chapter_id, topic_id, quantity, difficulty, mode,
            student_context, chatbot_settings, simplify=intent_result.get("simplify", False),
        ))

    # 9. Recommendation Engine (réservé, toujours indisponible aujourd'hui)
    if _probe_recommendation_engine(intent):
        return finalize(_build_strategy(
            ENGINE_RECOMMENDATION, intent, chapter_id, topic_id, quantity, difficulty, mode,
            student_context, chatbot_settings, simplify=intent_result.get("simplify", False),
        ))

    # 10. LLM — filet de sécurité ultime, toujours disponible.
    return finalize(_build_strategy(
        ENGINE_LLM, intent, chapter_id, topic_id, quantity, difficulty, mode,
        student_context, chatbot_settings,
    ))
