"""
Orchestre le chatbot : CRUD conversations/messages (SQLite via webapp/db.py),
puis pipeline local-first AVANT tout appel LLM (v2.12 : le LLM devient un
filet de sécurité, jamais le premier réflexe) — Rule Engine (salutations/
identité) -> Math Engine (calcul déterministe via sympy) -> Knowledge Engine
(définitions/propriétés retrouvées dans les cours) -> Local Knowledge Service
(progression/statistiques/dashboard/profil/exercices scopés par chapitre,
données réelles de l'élève, jamais d'appel IA) -> sinon Prompt Builder (avec
contexte RAG) + LLM Fallback Service en streaming. Point d'entrée unique
utilisé par les routes Flask (webapp/server.py) — aucune route n'accède
directement à db.py ni aux providers.
"""
import logging
import time

import ai_provider_service
import ai_request_log_service
import db
import plan_service
import quota_service
from auth import read_user_settings
from quota_service import QuotaType

from . import rule_engine, math_engine, knowledge_engine, cache, student_context_resolver, provider_manager
from .context_builder import build_context_summary
from .prompt_builder import build_system_prompt, build_messages
from .services import (
    action_cards_service, intent_service, llm_call_analytics, llm_fallback_service, local_knowledge_service,
    local_response_engine, mentions_service, pipeline_metrics, response_strategy, search_service,
    variable_resolver,
)

logger = logging.getLogger("chatbot.conversation_manager")

# ── Feature flags (Phase 3B, intégration progressive) ───────────────────────
# Chaque brique est indépendante et réversible INSTANTANÉMENT (remettre à
# False) sans toucher au code — c'est la garantie demandée pour un
# déploiement progressif, mesurable, jamais brutal.
#
# ENABLE_INTENT_ENGINE_V2 : intent_service.py EST déjà l'Intent Engine v2
# (portage Phase 1) — ce flag ne restaure pas un ancien fichier disparu, il
# restreint la classification aux intents "historiques" (ceux qui existaient
# avant le portage) si désactivé, pour un retour de comportement fidèle sans
# dépendre d'un second fichier à maintenir.
ENABLE_INTENT_ENGINE_V2 = True

# ENABLE_STUDENT_CONTEXT : remplace STUDENT_CONTEXT_RESOLVER_ENABLED (Phase
# 1+2) — même rôle, nom aligné sur les flags de cette phase. L'ancien nom
# reste disponible ci-dessous (alias) pour compatibilité ascendante.
ENABLE_STUDENT_CONTEXT = True
STUDENT_CONTEXT_RESOLVER_ENABLED = ENABLE_STUDENT_CONTEXT

# ENABLE_RESPONSE_STRATEGY (Étape 1) : calcule la décision du Strategy Engine
# à chaque tour réel, EN APARTÉ — comparée au moteur qui répond réellement
# (voir pipeline_metrics.log_comparison), mais NE MODIFIE JAMAIS la réponse
# envoyée à l'élève à elle seule (voir ENABLE_LOCAL_RESPONSE_ENGINE).
ENABLE_RESPONSE_STRATEGY = True

# ENABLE_LOCAL_RESPONSE_ENGINE (Étapes 2+3) : quand True ET que la décision du
# Strategy Engine tombe sur un moteur listé dans
# LOCAL_RESPONSE_ENGINE_ALLOWED_ENGINES, la réponse du Local Response Engine
# REMPLACE réellement l'appel à l'ancien pipeline pour ce tour. Sinon (moteur
# hors périmètre, ou flag à False), l'ancien pipeline s'exécute EXACTEMENT
# comme avant, sans aucune modification.
ENABLE_LOCAL_RESPONSE_ENGINE = True

# Périmètre actuel du déploiement progressif :
#   Étape 2 : salutations/remerciements (Rule Engine) + Dashboard (données
#             locales : progression/statistiques/dashboard/profil/paramètres/
#             série)
#   Étape 3 : Knowledge Response Composer (définition/cours/résumé/méthode/
#             propriété/exemple), couvert par ENGINE_KNOWLEDGE et
#             ENGINE_SEARCH (grounding générique, même composeur — voir
#             knowledge_response_composer.py)
#   Étape 4 (extension à Exercise Engine et au-delà) : PAS encore incluse ici,
#             volontairement — Math Engine reste géré par l'ancien
#             `_try_internal_answer` (déjà local, aucun gain à migrer).
LOCAL_RESPONSE_ENGINE_ALLOWED_ENGINES = {
    response_strategy.ENGINE_RULE,
    response_strategy.ENGINE_DASHBOARD,
    response_strategy.ENGINE_KNOWLEDGE,
    response_strategy.ENGINE_SEARCH,
}

# ENABLE_LLM_FALLBACK : coupe-circuit ultime — si False, plus aucun appel réel
# au fournisseur IA n'est effectué ; un message fixe est renvoyé à la place.
# Sert de garde-fou opérationnel (incident fournisseur, maîtrise des coûts),
# pas un usage courant.
ENABLE_LLM_FALLBACK = True
LLM_DISABLED_MESSAGE = (
    "Le mode intelligence artificielle est temporairement désactivé. "
    "Je ne peux répondre qu'aux questions couvertes par les données du cours pour l'instant."
)

# ENABLE_LLM_CALL_ANALYTICS (Phase 4, Mission 3) : journalise, en aparté, la
# raison classée automatiquement de chaque appel LLM réel — pure
# observabilité (voir llm_call_analytics.py), ne modifie jamais la réponse.
ENABLE_LLM_CALL_ANALYTICS = True

# Intents "historiques" (existaient avant l'Intent Engine v2, Phase 1) —
# utilisés uniquement quand ENABLE_INTENT_ENGINE_V2=False pour restreindre la
# classification à un comportement fidèle à l'avant-portage.
_LEGACY_INTENTS = {
    intent_service.EXERCICE, intent_service.EXEMPLE, intent_service.EXPLICATION, intent_service.QUIZ,
    intent_service.FICHE, intent_service.CORRECTION, intent_service.RESTART_BASICS, intent_service.FORMULE,
    intent_service.PROGRESSION, intent_service.STATISTIQUE, intent_service.DASHBOARD, intent_service.PROFIL,
    intent_service.PARAMETRES, intent_service.SERIE, intent_service.NONE_INTENT, intent_service.UNCLEAR,
}


def _classify_intent(user_message, context_summary, class_level=None, learning_context=None, last_assistant_message=None):
    """Classification d'intention, respectant ENABLE_INTENT_ENGINE_V2. Le
    module `intent_service.py` est déjà l'Intent Engine v2 (aucun ancien
    fichier à restaurer) — désactiver le flag retombe sur NONE_INTENT pour
    tout intent introduit par le portage (DEFINITION/COURS/RESUME/METHODE/
    PROPRIETE/DEMONSTRATION/INDICE/RAPPEL/REVISION/REFORMULATION/FOLLOWUP),
    sans jamais toucher à UNCLEAR (la détection de charabia reste active dans
    les deux cas — elle existait déjà avant le portage). `learning_context` :
    Current Learning Context de cette conversation, voir
    _update_learning_context ci-dessous. `last_assistant_message` : dernier
    message DE L'ASSISTANT (pas de l'élève), utilisé uniquement pour
    résoudre l'ambiguïté d'un "oui"/"non" nu (voir intent_service.classify)."""
    result = intent_service.classify(
        user_message, context_summary, class_level=class_level, learning_context=learning_context,
        last_assistant_message=last_assistant_message,
    )
    if not ENABLE_INTENT_ENGINE_V2 and result["intent"] not in _LEGACY_INTENTS:
        result = {**result, "intent": intent_service.NONE_INTENT}
    return result


# Intents qui expriment une incompréhension ou une demande de reformulation
# de la même notion — voir audit Phase 0 du chantier pédagogique : rien ne
# détectait jusqu'ici qu'un élève exprime une incompréhension deux tours de
# suite, ce qui pouvait mener le LLM à répéter presque la même explication.
_INCOMPREHENSION_INTENTS = (intent_service.REFORMULATION, intent_service.RESTART_BASICS)


def _previous_user_message_text(conversation_id):
    """Texte du message utilisateur précédent immédiatement le tour en cours
    (donc PAS le message qu'on est en train de traiter, déjà persisté par
    stream_reply avant l'appel à _generate_assistant_reply — voir son
    ORDER BY id ASC : le dernier élément est toujours le message courant).
    Renvoie None s'il n'y a pas d'échange précédent (première question)."""
    rows = [r for r in db.list_messages(conversation_id) if r["role"] == "user"]
    return rows[-2]["content"] if len(rows) >= 2 else None


def _previous_assistant_message_text(conversation_id):
    """Texte du DERNIER message de l'assistant déjà persisté pour cette
    conversation — utilisé uniquement pour résoudre l'ambiguïté d'un
    "oui"/"non" nu (voir intent_service.classify::last_assistant_message) :
    un "oui"/"non" isolé n'a de sens qu'en regard de ce que le chatbot vient
    de proposer. Renvoie None si l'assistant n'a encore jamais répondu dans
    cette conversation (première question)."""
    rows = [r for r in db.list_messages(conversation_id) if r["role"] == "assistant"]
    return rows[-1]["content"] if rows else None


def _detect_repeated_incomprehension(intent_result, conversation_id, context_summary, class_level, learning_context):
    """Vrai si l'élève exprime une incompréhension/demande de reformulation
    ET que son message précédent exprimait déjà la même chose — signal pour
    forcer un changement d'approche plutôt qu'une simple répétition de
    l'explication (voir pedagogy_templates.build_intent_instruction)."""
    if intent_result.get("intent") not in _INCOMPREHENSION_INTENTS:
        return False
    previous_text = _previous_user_message_text(conversation_id)
    if not previous_text:
        return False
    previous_intent = _classify_intent(previous_text, context_summary, class_level=class_level, learning_context=learning_context)
    return previous_intent.get("intent") in _INCOMPREHENSION_INTENTS


# ── Escalade pédagogique (chantier "repeated_incomprehension insuffisant",
# 2026-08-22) : `repeated_incomprehension` (ci-dessus) reste un booléen sur
# UN SEUL tour de mémoire — il ne dit jamais "combien de fois", ni "quelles
# approches ont déjà échoué". Ce mécanisme reste EN PLACE (compatibilité,
# voir pedagogy_templates.py) ; l'escalade ci-dessous en est une extension,
# pas un remplacement.
#
# Vocabulaire d'approches VOLONTAIREMENT court, réutilisant les catégories
# déjà existantes de knowledge_response_composer.py (BLOCK_DEFINITION/
# BLOCK_METHODE/BLOCK_EXEMPLE) pour tout ce qui doit être réellement composé
# localement (Local Response Engine, mode dégradé) — jamais un contenu
# inventé, jamais forcé si la notion ne le possède pas (voir _select_approach
# ci-dessous : repli sur la première approche disponible, répétition
# acceptée plutôt qu'invention). "analogie"/"question_guidee" sont des
# concepts UNIQUEMENT valables pour l'instruction textuelle envoyée au LLM
# (un LLM peut réellement produire une analogie ou une question guidée en
# prose ; le composeur local, lui, ne compose qu'à partir de blocs de
# données réels, jamais de génération).
_LOCAL_APPROACHES = ("definition", "methode", "exemple")
_LLM_APPROACHES = ("definition", "exemple", "analogie", "question_guidee")

# Progression pédagogique : à chaque niveau d'escalade correspond une
# approche PRÉFÉRÉE (piste de conception validée) — jamais imposée si non
# disponible/déjà utilisée, voir _select_approach. Au-delà du dernier palier
# défini (niveau 4+), aucune préférence explicite : _select_approach retombe
# alors sur "la première approche non encore utilisée", ce qui correspond
# exactement à "changement radical, éviter les approches déjà tentées".
_ESCALATION_PREFERRED_APPROACH = {
    0: "definition",
    1: "exemple",
    2: "analogie",
    3: "question_guidee",
}
_MAX_ESCALATION_LEVEL = 4


def _get_escalation_level(incomprehension_count):
    """Fonction pure et déterministe : niveau d'escalade à partir du nombre
    d'incompréhensions déjà exprimées SUR LE SUJET ACTUEL de la conversation
    (voir _advance_escalation_state pour le calcul de ce compteur, et
    _update_learning_context pour son reset au changement de sujet)."""
    return min(incomprehension_count or 0, _MAX_ESCALATION_LEVEL)


# Chantier "escalade réellement exécutée" (2026-08-22) : audit LIVE confirmé
# — recommander "analogie"/"question_guidee" puis les marquer comme
# `approaches_used` MÊME quand la notion ne contient aucune donnée
# permettant de les réaliser produisait une fausse mémoire (le système
# "croit" avoir tenté une analogie alors qu'il a réellement redonné une
# règle isolée). `_approaches_available_for_notion` filtre le vocabulaire
# AVANT toute recommandation, à partir des VRAIES données de la notion —
# jamais après coup, jamais une supposition. `notion` est déjà chargé par
# l'appelant (_update_learning_context, qui a déjà besoin de get_notion pour
# topic_label) — aucun appel supplémentaire à la base de cours.
_APPROACH_REALISABLE_SI = {
    "definition": lambda notion: True,
    "exemple": lambda notion: bool(notion.get("exemples")),
    # "analogie" : aucune notion migrée ne porte de champ d'analogie dédié
    # (vérifié) — le repli honnête (règle/prérequis + exemple + mini-
    # vérification, voir degraded_mode_service._build_pedagogical_answer)
    # nécessite au minimum une règle ou un point à retenir à présenter.
    "analogie": lambda notion: bool(knowledge_engine.get_regles(notion) or knowledge_engine.get_a_retenir(notion)),
    # "question_guidee" : construite à partir de l'énoncé d'un exemple RÉEL
    # (jamais une question mathématique inventée sans rapport avec le
    # contenu) — nécessite donc qu'un exemple existe.
    "question_guidee": lambda notion: bool(notion.get("exemples")),
}


def _approaches_available_for_notion(notion):
    """Sous-ensemble de _LLM_APPROACHES réellement réalisable pour CETTE
    notion, dans le même ordre (compatible avec _ESCALATION_PREFERRED_
    APPROACH). `notion` peut être None (aucune notion résolue) — repli sur
    "definition" seule, jamais une liste vide (voir _select_approach, qui
    gère déjà une liste vide, mais autant rester explicite ici)."""
    if not notion:
        return ("definition",)
    return tuple(a for a in _LLM_APPROACHES if _APPROACH_REALISABLE_SI[a](notion))


def _select_approach(escalation_level, approaches_used, available_approaches):
    """Fonction pure et déterministe : choisit l'approche à privilégier pour
    ce tour, parmi `available_approaches` (le vocabulaire RÉELLEMENT
    utilisable dans ce contexte — _LOCAL_APPROACHES pour un moteur local/
    dégradé limité aux données de la notion, _LLM_APPROACHES pour
    l'instruction textuelle du LLM), en évitant `approaches_used` quand une
    alternative existe. Ne force JAMAIS une approche absente de
    `available_approaches` (jamais de contenu inventé) — et accepte
    explicitement la répétition si aucune alternative n'existe (mieux vaut
    répéter une approche pertinente qu'échouer ou halluciner)."""
    if not available_approaches:
        return None
    preferred = _ESCALATION_PREFERRED_APPROACH.get(escalation_level)
    if preferred and preferred in available_approaches and preferred not in approaches_used:
        return preferred
    for approach in available_approaches:
        if approach not in approaches_used:
            return approach
    return available_approaches[0]


def _advance_escalation_state(intent, chapter_id, existing_learning_context, available_approaches):
    """Calcule le nouvel état d'escalade pour CE tour, à partir de l'état
    précédent (existing_learning_context, lu en DB par l'appelant) et de
    l'intent déjà classifié pour ce tour — AUCUNE nouvelle classification,
    AUCUNE nouvelle regex : réutilise exactement l'intent déjà déterminé par
    intent_service.classify() (voir _INCOMPREHENSION_INTENTS, déjà en place).

    Règles (voir rapport de conception du 2026-08-22) :
    - Changement de sujet (nouveau chapter_id différent de l'ancien) : reset
      complet — un compteur d'incompréhension ne doit JAMAIS survivre à un
      changement de notion, même implicite (une correspondance "explicit" ou
      "inherited" different du sujet précédent suffit à le prouver).
    - Message exprimant une incompréhension (intent ∈ _INCOMPREHENSION_
      INTENTS, le même ensemble déjà utilisé par _detect_repeated_
      incomprehension) : incrémente le compteur.
    - Sinon (FOLLOWUP simple "pourquoi ?"/"continue", question normale,
      demande d'exemple ordinaire...) : le compteur ne bouge PAS — un simple
      suivi de conversation n'est pas un nouvel échec de compréhension.

    `available_approaches` (chantier "escalade réellement exécutée",
    2026-08-22) : vocabulaire RÉELLEMENT réalisable pour la notion résolue
    ce tour (voir _approaches_available_for_notion, appelé par
    _update_learning_context qui a déjà chargé l'objet notion) — jamais le
    vocabulaire LLM générique aveuglément : recommander (et donc marquer
    comme utilisée) une approche que la notion ne permet pas de réaliser
    produirait une fausse mémoire (bug confirmé par l'audit LIVE : "analogie"
    marquée utilisée alors qu'aucune analogie n'était jamais produite,
    faute de contenu, quel que soit le moteur qui répond finalement).

    Renvoie (incomprehension_count, escalation_level, approaches_used,
    recommended_approach).

    `chapter_id` : le chapitre FINAL déjà résolu par l'appelant (après
    application de la garde _LOW_CONFIDENCE_TOPIC) — jamais relu depuis
    intent_result ici, pour ne jamais diverger de la décision réellement
    persistée par _update_learning_context (sinon un tour à confiance
    faible pourrait réinitialiser l'escalade alors que le sujet mémorisé,
    lui, n'a pas changé)."""
    old_chapter_id = (existing_learning_context or {}).get("chapter_id")
    topic_changed = bool(chapter_id) and chapter_id != old_chapter_id

    if topic_changed or not existing_learning_context:
        count = 0
        approaches_used = []
    else:
        count = existing_learning_context.get("incomprehension_count", 0) or 0
        approaches_used = list(existing_learning_context.get("approaches_used", []) or [])

    if intent in _INCOMPREHENSION_INTENTS:
        count += 1

    escalation_level = _get_escalation_level(count)
    # Chantier "fausse mémoire d'approche" (2026-08-22) : `recommended_approach`
    # N'EST PLUS ajoutée ici à `approaches_used` — ce n'est qu'une SUGGESTION
    # transmise aux moteurs (voir intent_result["recommended_approach"]),
    # jamais une certitude qu'elle sera réellement réalisée (le mode dégradé
    # peut retomber sur un repli honnête si la notion ne permet pas de
    # produire l'approche recommandée, ex. "analogie" sans donnée d'analogie
    # réelle — bug confirmé par l'audit QA du 2026-08-22). Seule l'approche
    # RÉELLEMENT PRODUITE (voir _commit_actual_approach, appelé APRÈS
    # génération de la réponse) est ajoutée à `approaches_used`.
    recommended_approach = _select_approach(escalation_level, approaches_used, available_approaches)

    return count, escalation_level, approaches_used, recommended_approach


# Niveaux de confiance (intent_service._detect_chapter) qui n'ont PAS le
# droit d'écraser un Current Learning Context déjà établi pour cette
# conversation — seul "explicit" (sujet nettement identifié dans CE message)
# et "inherited" (cohérent avec le contexte déjà mémorisé, donc une écriture
# sans effet) peuvent le faire. "weak" et "global" sont des suppositions,
# jamais une certitude suffisante pour remplacer un sujet déjà établi (voir
# audit "équation cartésienne" -> "proportionnalité" : c'est précisément ce
# genre d'écrasement non fiable qui causait la dérive).
_LOW_CONFIDENCE_TOPIC = {"weak", "global"}


def _update_learning_context(
    conversation_id, intent_result, class_level=None, existing_learning_context=None, advance_escalation=True,
):
    """Current Learning Context (voir db.get/set_conversation_learning_context
    et intent_service.classify) : mémorise le sujet réellement identifié pour
    ce tour (frais ou hérité), pour que le PROCHAIN message ambigu
    ("réexplique", "encore"...) puisse s'y raccrocher. Appelé à CHAQUE tour où
    un chapitre a pu être résolu, qu'il soit finalement répondu par un moteur
    local ou par le LLM — renvoie le titre de la notion (`topic_label`),
    injecté dans le prompt système pour interdire explicitement au LLM de
    deviner ou de changer de sujet. Une erreur ici est journalisée et avalée,
    jamais propagée à l'élève (même philosophie que _resolve_student_context).

    `topic_label` retombe sur le TITRE DU CHAPITRE si aucune notion précise
    n'est connue (chapter_id résolu, notion_id absent — ex: le premier message
    de la conversation n'a matché aucune notion par recherche, voir
    intent_service._detect_chapter, repli context_summary["chapters_in_
    progress"]) : sans ce repli, l'instruction "ne change pas de sujet"
    (pedagogy_templates.build_intent_instruction) ne pouvait jamais être
    injectée faute de topic_label, alors même que le chapitre était connu.

    `existing_learning_context` (Current Learning Context AVANT ce tour, lu
    par l'appelant via db.get_conversation_learning_context) : si un sujet
    est déjà mémorisé pour cette conversation ET que la confiance de ce tour
    est faible ("weak"/"global", voir _LOW_CONFIDENCE_TOPIC), le sujet
    existant est conservé TEL QUEL plutôt qu'écrasé par une supposition —
    c'est la correction directe du bug "équation cartésienne" -> "proportionnalité"
    (une correspondance à peine au-dessus du seuil ne doit plus jamais
    remplacer silencieusement un sujet déjà établi).

    `advance_escalation=False` (chantier "regenerate_last n'avance pas
    l'état pédagogique", 2026-08-22) : une RÉGÉNÉRATION rejoue le MÊME
    message utilisateur déjà compté au tour précédent — ce n'est jamais une
    nouvelle tentative d'incompréhension. Dans ce mode, l'état d'escalade
    (count/approaches_used) est repris TEL QUEL depuis `existing_learning_
    context`, jamais recalculé via _advance_escalation_state (qui
    incrémenterait à tort) — seule `recommended_approach` est recalculée
    (fonction pure de escalation_level/approaches_used déjà figés + données
    de la notion), pour que la régénération puisse quand même produire une
    réponse cohérente avec le niveau actuel."""
    chapter_id = intent_result.get("chapter_id")
    if not chapter_id:
        return existing_learning_context.get("topic_label") if existing_learning_context else None

    if (
        intent_result.get("topic_confidence") in _LOW_CONFIDENCE_TOPIC
        and existing_learning_context and existing_learning_context.get("chapter_id")
        and existing_learning_context.get("chapter_id") != chapter_id
    ):
        return existing_learning_context.get("topic_label")

    try:
        notion = None
        if intent_result.get("notion_id"):
            notion = knowledge_engine.get_notion(chapter_id, intent_result["notion_id"], class_level=class_level)
        topic_label = notion["title"] if notion else knowledge_engine.get_chapter_title(chapter_id, class_level=class_level)
        available = _approaches_available_for_notion(notion)

        if advance_escalation:
            count, escalation_level, approaches_used, recommended_approach = _advance_escalation_state(
                intent_result.get("intent"), chapter_id, existing_learning_context, available,
            )
        else:
            count = (existing_learning_context or {}).get("incomprehension_count", 0) or 0
            approaches_used = list((existing_learning_context or {}).get("approaches_used", []) or [])
            escalation_level = _get_escalation_level(count)
            recommended_approach = _select_approach(escalation_level, approaches_used, available)

        # Chantier "répétition des exemples" (2026-08-23) : même granularité
        # de reset que approaches_used ci-dessus (changement de chapter_id) —
        # un id d'exemple d'une AUTRE notion, resté par erreur dans la liste
        # après un changement de notion au sein du même chapitre, est de
        # toute façon inoffensif (il ne correspondra à aucun exemple réel de
        # la nouvelle notion, voir knowledge_engine.get_exemple/exemple_pool_
        # exhausted — simple no-op), donc pas besoin d'une granularité plus
        # fine que le chapitre pour rester correct.
        old_chapter_id = (existing_learning_context or {}).get("chapter_id")
        topic_changed = bool(chapter_id) and chapter_id != old_chapter_id
        if topic_changed or not existing_learning_context:
            used_exemple_ids = []
        else:
            used_exemple_ids = list(existing_learning_context.get("used_exemple_ids", []) or [])

        db.set_conversation_learning_context(
            conversation_id, chapter_id, intent_result.get("notion_id"), topic_label,
            incomprehension_count=count, approaches_used=approaches_used, class_level=class_level,
            used_exemple_ids=used_exemple_ids,
        )
        intent_result["incomprehension_count"] = count
        intent_result["escalation_level"] = escalation_level
        intent_result["approaches_used"] = approaches_used
        intent_result["recommended_approach"] = recommended_approach
        intent_result["used_exemple_ids"] = used_exemple_ids
        return topic_label
    except Exception:
        logger.exception("Échec de la mise à jour du Current Learning Context — ignoré.")
        return None


def _commit_actual_approach(conversation_id, actual_approach):
    """Chantier "fausse mémoire d'approche" (2026-08-22) — étape 2/2 : appelé
    UNIQUEMENT après que la réponse a été réellement composée (par le Local
    Response Engine ou le mode dégradé, voir call sites), avec l'approche
    RÉELLEMENT PRODUITE (jamais la seule `recommended_approach`, voir
    _advance_escalation_state qui ne la propose plus qu'à titre de
    suggestion). Relit le Current Learning Context TEL QU'IL VIENT D'ÊTRE
    écrit par _update_learning_context (même chapter_id/notion_id/topic_label/
    incomprehension_count, jamais recalculés ici) et n'ajoute que
    `actual_approach` à `approaches_used`, une seule fois. `actual_approach`
    peut être `None` (ex: réponse produite par un vrai LLM sans repli local —
    voir docstring des call sites) : dans ce cas, rien n'est fait, la
    suggestion `recommended_approach` déjà transmise au LLM reste la seule
    trace de ce tour, comme avant ce chantier (le LLM reste réputé fiable sur
    ce qu'on lui a demandé — seuls les moteurs LOCAUX/dégradés, dont on
    connaît le fonctionnement exact, peuvent faussement promettre une
    approche qu'ils n'ont pas réalisée)."""
    if not actual_approach:
        return
    try:
        current = db.get_conversation_learning_context(conversation_id)
        if not current or not current.get("chapter_id"):
            return
        approaches_used = list(current.get("approaches_used", []) or [])
        if approaches_used and approaches_used[-1] == actual_approach:
            return  # déjà enregistrée (ex: appel redondant) — jamais de doublon consécutif inutile
        approaches_used = approaches_used + [actual_approach]
        db.set_conversation_learning_context(
            conversation_id, current["chapter_id"], current.get("notion_id"), current.get("topic_label"),
            incomprehension_count=current.get("incomprehension_count", 0) or 0, approaches_used=approaches_used,
            class_level=current.get("class_level"), used_exemple_ids=current.get("used_exemple_ids"),
        )
    except Exception:
        logger.exception("Échec de l'enregistrement de l'approche réellement utilisée — ignoré.")


def _commit_used_exemples(conversation_id, new_exemple_ids):
    """Chantier "répétition des exemples" (2026-08-23) : même schéma que
    _commit_actual_approach() ci-dessus (lecture-ajout-écriture APRÈS
    composition réelle, jamais avant) — ajoute les ids d'exemples RÉELLEMENT
    montrés ce tour (voir knowledge_response_composer.ResponseDraft.
    new_exemple_ids / degraded_mode_service via intent_result) à
    used_exemple_ids, sans doublon. `new_exemple_ids` vide/None : aucune
    écriture (aucun exemple réellement montré ce tour, ou moteur sans notion
    d'exemple — ex: math_engine, LLM libre sans repli local)."""
    new_exemple_ids = [eid for eid in (new_exemple_ids or ()) if eid]
    if not new_exemple_ids:
        return
    try:
        current = db.get_conversation_learning_context(conversation_id)
        if not current or not current.get("chapter_id"):
            return
        used_exemple_ids = list(current.get("used_exemple_ids", []) or [])
        added = False
        for eid in new_exemple_ids:
            if eid not in used_exemple_ids:
                used_exemple_ids.append(eid)
                added = True
        if not added:
            return  # déjà toutes enregistrées (ex: appel redondant)
        db.set_conversation_learning_context(
            conversation_id, current["chapter_id"], current.get("notion_id"), current.get("topic_label"),
            incomprehension_count=current.get("incomprehension_count", 0) or 0,
            approaches_used=current.get("approaches_used"), class_level=current.get("class_level"),
            used_exemple_ids=used_exemple_ids,
        )
    except Exception:
        logger.exception("Échec de l'enregistrement des exemples réellement utilisés — ignoré.")


def _resolve_rag_context(intent_result, user_message, class_level=None):
    """Contexte RAG (extraits de cours) pour ce tour — TROIS niveaux de repli,
    du plus fiable au plus incertain, jamais un abandon prématuré :

    1. Notion précise (lookup exact) si le Current Learning Context connaît
       chapitre ET notion — ne peut jamais se tromper de notion.
    2. CHAPITRE connu (lookup exact, plusieurs notions) si le Current Learning
       Context connaît le chapitre mais pas la notion précise — AVANT toute
       recherche floue sur le message. Sans ce palier intermédiaire, un
       message ambigu ("réexplique", "je n'ai pas compris"...) qui hérite
       d'un chapitre sans notion précise (recherche initiale trop faible,
       repli sur `context_summary["chapters_in_progress"]`, voir
       intent_service._detect_chapter) retombait directement sur une
       recherche floue non fiable sur ce message ambigu lui-même — souvent
       vide ou hors-sujet, c'est la cause racine du chatbot qui "abandonne
       trop vite" (voir audit du 2026-07-26).
    3. Recherche floue sur le message lui-même (context_block), en tout
       dernier recours — seulement si aucun chapitre n'est connu du tout, ou
       si les deux paliers précédents n'ont rien trouvé."""
    chapter_id = intent_result.get("chapter_id")
    notion_id = intent_result.get("notion_id")
    if intent_result.get("topic_inherited") and chapter_id:
        if notion_id:
            rag_context = knowledge_engine.notion_context_block(chapter_id, notion_id, class_level=class_level)
            if rag_context:
                return rag_context
        rag_context = knowledge_engine.chapter_context_block(chapter_id, class_level=class_level)
        if rag_context:
            return rag_context
    return knowledge_engine.context_block(user_message, class_level=class_level)


def _resolve_student_context(user, chapters_summary, chatbot_settings, mentions, history_rows, class_level=None):
    """Calcule le StudentContext v2 sans jamais impacter la réponse envoyée à
    l'élève : une erreur ici est journalisée et avalée, jamais propagée."""
    if not ENABLE_STUDENT_CONTEXT:
        return None
    try:
        return student_context_resolver.resolve(
            user, chapters_summary=chapters_summary, chatbot_settings=chatbot_settings,
            mentions=mentions, history_rows=history_rows, class_level=class_level,
        )
    except Exception:
        return None


def _decide_strategy_shadow(
    user_message, user, chapters_summary, chatbot_settings, mentions, student_context, debug, class_level=None,
    learning_context=None, last_assistant_message=None,
):
    """Étape 1 : calcule la décision du Strategy Engine — PAS toujours un
    aparté (voir _try_local_response_engine : le résultat peut réellement
    remplacer la réponse pour Rule/Dashboard/Knowledge/Search). `learning_context`/
    `last_assistant_message` : transmis pour que ce moteur bénéficie des mêmes
    corrections de continuité que le pipeline principal. Une erreur ici est
    journalisée et avalée."""
    if not ENABLE_RESPONSE_STRATEGY:
        return None
    try:
        return response_strategy.decide_strategy(
            user_message, user, chapters_summary=chapters_summary, chatbot_settings=chatbot_settings,
            mentions=mentions, student_context=student_context, use_cache=True, debug=debug,
            class_level=class_level, learning_context=learning_context, last_assistant_message=last_assistant_message,
        )
    except Exception:
        logger.exception("Échec du Response Strategy Engine (aparté) — ignoré.")
        return None


def _try_local_response_engine(
    strategy, user_message, user, chapters_summary, chatbot_settings, mentions, student_context, debug, class_level=None,
    learning_context=None, last_assistant_message=None, escalation_level=0, recommended_approach=None,
    used_exemple_ids=(),
):
    """Étapes 2+3 : n'exécute (et ne peut donc REMPLACER la réponse) que si la
    décision du Strategy Engine tombe sur un moteur déjà couvert par le
    périmètre actuel du déploiement (LOCAL_RESPONSE_ENGINE_ALLOWED_ENGINES).
    Renvoie `None` si hors périmètre, désactivé, ou en échec — l'appelant
    retombe alors sur l'ancien pipeline, inchangé.

    `learning_context`/`last_assistant_message` (chantier "learning_context
    perdu par le Local Response Engine", 2026-08-22) : transmis TELS QUELS
    (jamais recalculés) à local_response_engine.generate() — avant ce
    correctif, `strategy` (calculé avec le bon contexte par
    _decide_strategy_shadow) ne servait qu'à la vérification d'éligibilité
    ci-dessus ; l'exécution réelle du moteur local reclassait le message
    depuis zéro, sans aucun contexte, et pouvait donc écraser un sujet déjà
    établi (bug confirmé, voir audit du 2026-08-22)."""
    if not ENABLE_LOCAL_RESPONSE_ENGINE or strategy is None or strategy.engine not in LOCAL_RESPONSE_ENGINE_ALLOWED_ENGINES:
        return None
    try:
        result = local_response_engine.generate(
            user_message, user, chapters_summary=chapters_summary, chatbot_settings=chatbot_settings,
            mentions=mentions, student_context=student_context, use_cache=True, debug=debug,
            class_level=class_level, learning_context=learning_context, last_assistant_message=last_assistant_message,
            escalation_level=escalation_level, recommended_approach=recommended_approach,
            used_exemple_ids=used_exemple_ids,
        )
    except Exception:
        logger.exception("Échec du Local Response Engine — repli sur l'ancien pipeline.")
        return None
    if result.should_use_llm or not result.text:
        return None
    return result


def _log_llm_call_details(user, call_info, elapsed_s, conversation_id=None, request_id=None):
    """Journalise, pour CHAQUE appel réel au fournisseur IA, qui a demandé
    quoi et ce qui a réellement été utilisé — pour ne plus jamais devoir
    deviner après coup si un utilisateur Premium/Ultra a réellement reçu un
    appel Gemini Pro/Claude ou un repli automatique (voir
    llm_fallback_service.generate(), qui remplit `call_info`). Un échec ici
    est journalisé et avalé, jamais propagé à l'élève.
    `request_id` (BLACK BOX RECORDER, optionnel) : identifiant de requête
    transmis explicitement depuis server.py (le contexte Flask `g` n'est plus
    disponible ici — cette fonction s'exécute dans le générateur SSE, après
    dépilement du contexte de requête) — corrèle cet appel LLM avec le reste
    du tour (frontend, route, exceptions) sans changer ce qui est journalisé
    par ailleurs."""
    try:
        provider_name = call_info.get("provider", "?")
        model_used = call_info.get("model", "?")
        fallback_from = call_info.get("fallback_from")
        usage = call_info.get("usage")
        tokens_display = usage["total_tokens"] if usage else "N/A"
        logger.info(
            "Appel LLM — request_id=%s utilisateur=%s plan=%s provider=%s modele=%s repli_depuis=%s temps=%.2fs tokens=%s",
            request_id or "-", user["id"], plan_service.get_plan(user).value, provider_name, model_used,
            fallback_from or "aucun", elapsed_s, tokens_display,
        )
    except Exception:
        logger.exception("Échec de la journalisation détaillée de l'appel LLM — ignoré.")

    # Alimente le Dashboard Administrateur (cartes/graphiques observabilité
    # IA, voir admin_dashboard_service.py) avec CE QUI S'EST RÉELLEMENT
    # PASSÉ — succès ou échec — pour cet appel LLM (voir
    # llm_fallback_service.generate()::call_info, qui remplit success/
    # error_type/error_message/elapsed_ms/fallback_from/fallback_reason/
    # time_lost_before_fallback_ms en plus de provider/model/usage déjà
    # utilisés). Point d'entrée unique : ai_provider_service.record_llm_usage()
    # — ne lève jamais d'exception : un échec ici ne doit jamais faire perdre
    # la réponse déjà envoyée à l'élève.
    try:
        ai_provider_service.record_llm_usage(
            call_info.get("provider"), call_info.get("model"), call_info.get("usage"),
            success=call_info.get("success", True),
            response_time_ms=call_info.get("elapsed_ms"),
            error_type=call_info.get("error_type"),
            error_message=call_info.get("error_message"),
            is_fallback=bool(call_info.get("fallback_from")),
        )
    except Exception:
        logger.exception("Échec de l'enregistrement de la consommation IA — ignoré.")

    # Consommation IA PAR UTILISATEUR (table ai_request_logs, distincte de
    # ai_provider_usage ci-dessus) — alimente l'onglet Chatbot de la fiche
    # utilisateur (voir admin_user_profile_service.get_chatbot()). Même
    # tolérance aux pannes que ci-dessus : ne doit jamais faire perdre la
    # réponse déjà envoyée à l'élève.
    try:
        ai_request_log_service.record(
            user["id"], conversation_id, call_info.get("provider"), call_info.get("model"),
            call_info.get("usage"),
            success=call_info.get("success", True),
            response_time_ms=call_info.get("elapsed_ms"),
            is_fallback=bool(call_info.get("fallback_from")),
        )
    except Exception:
        logger.exception("Échec de l'enregistrement de la consommation IA par utilisateur — ignoré.")

    # Événement de fallback détaillé (fournisseur initial/final, raison,
    # temps perdu) — enregistré séparément de l'agrégat ci-dessus, voir
    # docstring de ai_provider_service.record_provider_fallback(). Seulement
    # si un repli a réellement eu lieu pour ce tour (fallback_from non vide).
    fallback_from = call_info.get("fallback_from")
    if fallback_from:
        try:
            provider_initial, _, model_initial = fallback_from.partition(":")
            ai_provider_service.record_provider_fallback(
                provider_initial, model_initial or "?",
                call_info.get("provider"), call_info.get("model"),
                call_info.get("fallback_reason"),
                time_lost_ms=call_info.get("time_lost_before_fallback_ms") or 0,
            )
        except Exception:
            logger.exception("Échec de l'enregistrement de l'événement de fallback — ignoré.")


def _record_llm_call(user_message, strategy):
    """Journalisation Mission 3 (Phase 4) : pur aparté, une panne ici ne doit
    jamais empêcher la réponse déjà décidée d'être envoyée à l'élève."""
    if not ENABLE_LLM_CALL_ANALYTICS:
        return
    try:
        llm_call_analytics.record(user_message, strategy, LOCAL_RESPONSE_ENGINE_ALLOWED_ENGINES)
    except Exception:
        logger.exception("Échec de la journalisation llm_call_analytics — ignoré.")


# ── Quota de messages IA ─────────────────────────────────────────────────────
# Source de vérité unique : quota_service.py (Feature Flags + Quotas). Cette
# fonction reste le seul point du chatbot qui consomme le quota — appelée une
# fois par tour réel (stream_reply/regenerate_last), jamais par retry_last
# (un hoquet réseau ne coûte pas de message, voir sa docstring).
def check_and_increment_quota(user):
    """Consomme un message IA du quota quotidien de `user` (QuotaType.CHAT_MESSAGES)
    et renvoie le nouveau total consommé aujourd'hui. Lève
    quota_service.QuotaExceededError si la limite du palier actuel est
    dépassée — propagée telle quelle jusqu'à la route Flask
    (webapp/server.py), qui la traduit en réponse HTTP 429."""
    return quota_service.consume(user, QuotaType.CHAT_MESSAGES)


def quota_status(user):
    """Statut du quota de messages IA de `user`, au format historique
    {"used": int, "limit": int|None} consommé par GET /api/chatbot/quota
    (voir server.py). Le format détaillé (remaining/unlimited) vit dans
    quota_service.usage_snapshot(), exposé par le nouveau GET /api/quota."""
    snapshot = quota_service.usage_snapshot(user, QuotaType.CHAT_MESSAGES)
    return {"used": snapshot["used"], "limit": snapshot["limit"]}


# ── Conversations ────────────────────────────────────────────────────────────
def create_conversation(user_id, title="Nouvelle conversation"):
    conv_id = db.create_conversation(user_id, title)
    return db.get_conversation(conv_id, user_id)


def list_conversations(user_id, search=None):
    return db.list_conversations(user_id, search)


def rename_conversation(user_id, conversation_id, title):
    return db.update_conversation(conversation_id, user_id, title=title)


def pin_conversation(user_id, conversation_id, pinned):
    return db.update_conversation(conversation_id, user_id, pinned=pinned)


def delete_conversation(user_id, conversation_id):
    db.delete_conversation(conversation_id, user_id)


def get_messages(user_id, conversation_id):
    conv = db.get_conversation(conversation_id, user_id)
    if conv is None:
        return None
    return db.list_messages(conversation_id)


# ── Pipeline hybride (court-circuite le LLM quand la logique interne suffit) ─
def _try_internal_answer(user_message, class_level=None):
    """Rule Engine (salutations/identité) -> Math Engine (calcul déterministe)
    -> Knowledge Engine (définition retrouvée avec une correspondance nette
    dans les cours). Renvoie une réponse toute faite, ou None si seul le LLM
    peut répondre (question ouverte, méthode à expliquer pas à pas...)."""
    answer = rule_engine.try_handle(user_message)
    if answer is not None:
        return answer
    answer = math_engine.try_solve(user_message)
    if answer is not None:
        return answer
    return knowledge_engine.try_answer_definition(user_message, class_level=class_level)


# ── Envoi d'un message (génère la réponse en streaming) ─────────────────────
def stream_reply(user, conversation_id, user_message, chapters_summary=None, mentions=None, debug=False, class_level=None, request_id=None):
    """Générateur de fragments texte. Persiste le message utilisateur avant de
    commencer, puis le message assistant complet à la fin du flux — pour que
    l'historique reste cohérent même si le client interrompt le stream.
    `mentions` : ressources "@" résolues côté frontend (chapter_id/notion_id
    ou exercise_id) — injectées telles quelles dans le prompt système, jamais
    devinées par le LLM (voir mentions_service.build_grounding_block).
    `debug=True` : journalise (logger DEBUG) un bloc détaillé Intent/Strategy/
    Moteur/Temps/Fallback pour ce tour (Phase 3B).
    `class_level` (optionnel, "seconde" par défaut) : classe active de
    l'élève (curriculum_registry.py) — transportée jusqu'au bout du pipeline
    (StudentContext, Knowledge/Search Engine, grounding des mentions "@")
    afin qu'aucune donnée d'une autre classe ne soit jamais utilisée.
    `request_id` (BLACK BOX RECORDER, optionnel) : identifiant de requête
    transmis par server.py, uniquement pour corréler les logs de ce tour
    (voir _log_llm_call_details) — ne modifie aucune décision du pipeline."""
    conv = db.get_conversation(conversation_id, user["id"])
    if conv is None:
        raise ValueError("Conversation introuvable.")

    check_and_increment_quota(user)
    db.add_message(conversation_id, "user", user_message, mentions=mentions)

    # Titre auto : première question de la conversation, tronquée.
    if conv["title"] == "Nouvelle conversation":
        auto_title = user_message.strip()[:60] or "Nouvelle conversation"
        db.update_conversation(conversation_id, user["id"], title=auto_title)

    try:
        yield from _generate_assistant_reply(
            user, conversation_id, user_message, chapters_summary, mentions, debug, class_level, request_id=request_id,
        )
    except Exception:
        # Le quota vient d'être facturé (check_and_increment_quota ci-dessus),
        # mais une exception AVANT tout appel réel au fournisseur IA (ex:
        # classification d'intention, résolution du contexte RAG) ne doit
        # jamais laisser ce message facturé sans qu'aucune réponse n'ait été
        # produite — voir quota_service.refund(). Si une réponse (même
        # partielle, voir le `finally` de _generate_assistant_reply) a déjà
        # été persistée, le dernier message est "assistant" et rien n'est
        # remboursé : le quota reste dû pour toute réponse réellement
        # délivrée, même tronquée.
        latest = db.list_messages(conversation_id)
        if not latest or latest[-1]["role"] != "assistant":
            quota_service.refund(user, QuotaType.CHAT_MESSAGES)
        raise


def retry_last(user, conversation_id, chapters_summary=None, debug=False, class_level=None, request_id=None):
    """Réessaie la génération de réponse pour le dernier message utilisateur,
    SANS le dupliquer en base — pour le cas où une tentative précédente
    (stream_reply ou regenerate_last) a échoué avant qu'aucun message
    assistant n'ait pu être persisté (panne réseau/fournisseur pendant le
    tout premier essai, cf. robustesse chatbot). Ne consomme pas de quota
    supplémentaire : un hoquet réseau ne doit jamais coûter un message à
    l'élève. Si une réponse assistant a déjà été persistée pour ce tour,
    c'est `regenerate_last` qu'il faut utiliser à la place — celui-ci lève
    une erreur explicite sinon (aucun risque de double génération)."""
    conv = db.get_conversation(conversation_id, user["id"])
    if conv is None:
        raise ValueError("Conversation introuvable.")
    rows = db.list_messages(conversation_id)
    if not rows or rows[-1]["role"] != "user":
        raise ValueError("Rien à réessayer.")
    last_user = rows[-1]
    # Jeton de course (même principe que regenerate_last, voir db.delete_
    # message) : aucun message assistant à supprimer ici pour servir de
    # jeton, donc réclamation atomique explicite sur l'id du dernier message
    # utilisateur — une seule requête concurrente (double-clic, double onglet
    # sur "réessayer") peut gagner et générer réellement une réponse.
    if not db.claim_message_retry(last_user["id"]):
        raise ValueError("Cette réponse est déjà en cours de génération.")
    try:
        yield from _generate_assistant_reply(
            user, conversation_id, last_user["content"], chapters_summary, last_user.get("mentions"), debug, class_level,
            request_id=request_id,
        )
    finally:
        # Relâche la réclamation UNIQUEMENT si la génération n'a produit
        # aucun message assistant (échec réseau/fournisseur à nouveau) — un
        # vrai nouvel essai séquentiel (pas concurrent) doit rester possible.
        # En cas de succès, le dernier message n'est plus "user" : plus
        # jamais réexaminé par un futur retry_last sur ce même message, la
        # réclamation devenue inutile n'a pas besoin d'être nettoyée.
        latest = db.list_messages(conversation_id)
        if not latest or latest[-1]["role"] != "assistant":
            db.release_message_retry_claim(last_user["id"])


def _generate_assistant_reply(user, conversation_id, user_message, chapters_summary, mentions, debug, class_level=None, request_id=None):
    """Cœur de sélection/génération de réponse (Intent → Strategy Engine/
    Local Response Engine → moteurs legacy → LLM en dernier recours), extrait
    de stream_reply pour être partagé avec retry_last sans jamais dupliquer
    le message utilisateur (déjà persisté par l'appelant)."""
    t0 = time.perf_counter()
    pipeline_metrics.record_request()

    settings = read_user_settings(user["id"])
    chatbot_settings = settings.get("chatbot", {})

    # Current Learning Context (continuité de sujet) : dernier chapitre/
    # notion réellement discuté dans CETTE conversation, voir
    # db.get_conversation_learning_context et intent_service.classify. Permet
    # à un message ambigu ("réexplique", "encore"...) de rester sur le même
    # sujet sans jamais deviner via une recherche floue.
    learning_context = db.get_conversation_learning_context(conversation_id)

    # Classification d'intention (Phase G) : détecte les demandes
    # incompréhensibles AVANT tout appel LLM — jamais laisser le fournisseur
    # IA inventer une réponse à "aaaa" ou "......".
    context_summary = build_context_summary(user, chapters_summary, class_level=class_level)
    last_assistant_message = _previous_assistant_message_text(conversation_id)
    intent_result = _classify_intent(
        user_message, context_summary, class_level=class_level, learning_context=learning_context,
        last_assistant_message=last_assistant_message,
    )
    if intent_result["intent"] == intent_service.UNCLEAR:
        db.add_message(conversation_id, "assistant", intent_service.CLARIFICATION_MESSAGE, engine="clarification")
        db.touch_conversation(conversation_id)
        elapsed_ms = (time.perf_counter() - t0) * 1000
        pipeline_metrics.record_response("clarification", local=True, elapsed_ms=elapsed_ms)
        ai_request_log_service.record_local_response(
            user["id"], conversation_id, "clarification", "clarification", "clarification",
            user_text=user_message, response_text=intent_service.CLARIFICATION_MESSAGE, response_time_ms=elapsed_ms,
        )
        yield intent_service.CLARIFICATION_MESSAGE
        return

    if _detect_repeated_incomprehension(intent_result, conversation_id, context_summary, class_level, learning_context):
        intent_result = {**intent_result, "repeated_incomprehension": True}

    topic_label = _update_learning_context(
        conversation_id, intent_result, class_level=class_level, existing_learning_context=learning_context,
    )

    # Une mention "@" seule ("@Progression", sans question ouverte autour,
    # Phase R) est une intention directe tout aussi locale qu'une phrase
    # tapée — mêmes données réelles, même moteur, jamais le LLM.
    mention_intent = mentions_service.single_data_mention_intent(user_message, mentions)
    if mention_intent:
        intent_result = {**intent_result, "intent": mention_intent}

    # Student Context Resolver v2 (portage Phase 2) : calculé à chaque tour
    # réel — consommé par le Strategy/Local Response Engine ci-dessous quand
    # ils sont activés, sinon un aparté sans effet (comme avant Phase 3B).
    student_context = _resolve_student_context(
        user, chapters_summary, chatbot_settings, mentions, history_rows=None, class_level=class_level,
    )

    # Étape 1 (Phase 3B) : décision du Strategy Engine en aparté, comparée au
    # moteur qui répond réellement plus bas — ne change jamais la réponse à
    # elle seule.
    strategy = _decide_strategy_shadow(
        user_message, user, chapters_summary, chatbot_settings, mentions, student_context, debug,
        class_level=class_level, learning_context=learning_context, last_assistant_message=last_assistant_message,
    )

    # Étapes 2+3 (Phase 3B) : le Local Response Engine ne remplace la réponse
    # que si la décision tombe dans le périmètre déployé aujourd'hui
    # (LOCAL_RESPONSE_ENGINE_ALLOWED_ENGINES) — sinon `None`, et l'ancien
    # pipeline s'exécute juste en dessous, à l'identique d'avant cette phase.
    local_result = _try_local_response_engine(
        strategy, user_message, user, chapters_summary, chatbot_settings, mentions, student_context, debug,
        class_level=class_level, learning_context=learning_context, last_assistant_message=last_assistant_message,
        escalation_level=intent_result.get("escalation_level", 0),
        recommended_approach=intent_result.get("recommended_approach"),
        used_exemple_ids=intent_result.get("used_exemple_ids", ()),
    )
    if local_result is not None:
        db.add_message(conversation_id, "assistant", local_result.text, engine=local_result.engine)
        db.touch_conversation(conversation_id)
        # Chantier "fausse mémoire d'approche" (2026-08-22) — étape 2/2 :
        # commit APRÈS composition réelle, jamais avant (voir
        # _commit_actual_approach). `local_result.actual_approach` reflète ce
        # que le moteur a VRAIMENT produit, pas `recommended_approach`.
        _commit_actual_approach(conversation_id, local_result.actual_approach)
        # Chantier "répétition des exemples" (2026-08-23) — même principe :
        # commit APRÈS composition réelle, jamais avant.
        _commit_used_exemples(conversation_id, local_result.new_exemple_ids)
        elapsed_ms = (time.perf_counter() - t0) * 1000
        pipeline_metrics.record_response(local_result.engine, local=True, elapsed_ms=elapsed_ms, fallback=local_result.used_fallback)
        pipeline_metrics.log_comparison(strategy, local_result.engine)
        ai_request_log_service.record_local_response(
            user["id"], conversation_id, local_result.engine, "local", local_result.engine,
            user_text=user_message, response_text=local_result.text, response_time_ms=elapsed_ms,
            fallback=local_result.used_fallback,
        )
        if debug:
            logger.debug(pipeline_metrics.format_debug_trace(strategy, local_result.engine, elapsed_ms, local_result.used_fallback))
        yield local_result.text
        return

    internal_answer = _try_internal_answer(user_message, class_level=(student_context or {}).get("class_level"))
    if internal_answer is not None:
        db.add_message(conversation_id, "assistant", internal_answer, engine="legacy_internal")
        db.touch_conversation(conversation_id)
        elapsed_ms = (time.perf_counter() - t0) * 1000
        pipeline_metrics.record_response("legacy_internal", local=True, elapsed_ms=elapsed_ms)
        pipeline_metrics.log_comparison(strategy, "legacy_internal")
        ai_request_log_service.record_local_response(
            user["id"], conversation_id, "legacy_internal", "local", "legacy_internal",
            user_text=user_message, response_text=internal_answer, response_time_ms=elapsed_ms,
        )
        if debug:
            logger.debug(pipeline_metrics.format_debug_trace(strategy, "legacy_internal", elapsed_ms))
        yield internal_answer
        return

    # Moteur de réponses locales (Phase Q, v2.12) : le LLM ne doit être qu'un
    # filet de sécurité, jamais le premier réflexe. Toute intention couverte
    # localement (données réelles de l'élève, exercice scopé par chapitre —
    # jamais un autre chapitre, jamais halluciné) est répondue ici, sans
    # jamais appeler le fournisseur IA.
    local_answer = local_knowledge_service.try_answer(
        intent_result, user, context_summary, chatbot_settings, user_message=user_message,
        student_context=student_context,
    )
    if local_answer is not None:
        db.add_message(conversation_id, "assistant", local_answer, engine="legacy_local_knowledge")
        db.touch_conversation(conversation_id)
        elapsed_ms = (time.perf_counter() - t0) * 1000
        pipeline_metrics.record_response("legacy_local_knowledge", local=True, elapsed_ms=elapsed_ms)
        pipeline_metrics.log_comparison(strategy, "legacy_local_knowledge")
        ai_request_log_service.record_local_response(
            user["id"], conversation_id, "legacy_local_knowledge", "local", "legacy_local_knowledge",
            user_text=user_message, response_text=local_answer, response_time_ms=elapsed_ms,
        )
        if debug:
            logger.debug(pipeline_metrics.format_debug_trace(strategy, "legacy_local_knowledge", elapsed_ms))
        yield local_answer
        return

    history_enabled = chatbot_settings.get("historyEnabled", True)
    history_rows = db.list_messages(conversation_id) if history_enabled else [
        {"role": "user", "content": user_message}
    ]

    provider_name, model_name = provider_manager.select_llm_for_user(user)
    # BLACK BOX RECORDER : provider/modèle réellement sélectionnés pour ce
    # tour, avant même de savoir si le cache/LLM sera atteint — permet de
    # savoir, pour un request_id donné, quel fournisseur était visé dès le
    # départ (à comparer avec celui effectivement utilisé, journalisé plus
    # bas par _log_llm_call_details une fois l'appel LLM réellement effectué).
    logger.info(
        "[BLACKBOX] provider selectionne — request_id=%s provider=%s modele=%s",
        request_id or "-", provider_name, model_name,
    )
    cache_key = cache.make_key(
        user["id"], provider_name, model_name, user_message, class_level=(student_context or {}).get("class_level"),
        topic=intent_result.get("chapter_id"),
    )
    cached_answer = cache.get(cache_key)
    if cached_answer is not None:
        db.add_message(conversation_id, "assistant", cached_answer, engine="cache")
        db.touch_conversation(conversation_id)
        elapsed_ms = (time.perf_counter() - t0) * 1000
        pipeline_metrics.record_response("cache", local=True, elapsed_ms=elapsed_ms)
        pipeline_metrics.log_comparison(strategy, "cache")
        ai_request_log_service.record_local_response(
            user["id"], conversation_id, "cache", "cache", model_name,
            user_text=user_message, response_text=cached_answer, response_time_ms=elapsed_ms,
        )
        if debug:
            logger.debug(pipeline_metrics.format_debug_trace(strategy, "cache", elapsed_ms))
        yield cached_answer
        return

    if not ENABLE_LLM_FALLBACK:
        db.add_message(conversation_id, "assistant", LLM_DISABLED_MESSAGE, engine="llm_disabled")
        db.touch_conversation(conversation_id)
        elapsed_ms = (time.perf_counter() - t0) * 1000
        pipeline_metrics.record_response("llm_disabled", local=True, elapsed_ms=elapsed_ms)
        ai_request_log_service.record_local_response(
            user["id"], conversation_id, "llm_disabled", "local", "llm_disabled",
            user_text=user_message, response_text=LLM_DISABLED_MESSAGE, response_time_ms=elapsed_ms,
        )
        if debug:
            logger.debug(pipeline_metrics.format_debug_trace(strategy, "llm_disabled", elapsed_ms))
        yield LLM_DISABLED_MESSAGE
        return

    rag_class_level = (student_context or {}).get("class_level")
    rag_context = _resolve_rag_context(intent_result, user_message, class_level=rag_class_level)
    mentions_block = mentions_service.build_grounding_block(
        mentions, user=user, chapters_summary=chapters_summary, class_level=rag_class_level,
    )
    system_prompt = build_system_prompt(
        user, chatbot_settings, chapters_summary, rag_context, mentions_block, intent_result=intent_result,
        class_level=rag_class_level, topic_label=topic_label,
    )
    messages = build_messages(history_rows)

    pipeline_metrics.log_comparison(strategy, response_strategy.ENGINE_LLM)
    _record_llm_call(user_message, strategy)
    if debug:
        logger.debug(pipeline_metrics.format_debug_trace(strategy, response_strategy.ENGINE_LLM, (time.perf_counter() - t0) * 1000))

    call_info = {}
    full_reply = []
    try:
        for chunk in llm_fallback_service.generate(
            messages, system_prompt, chatbot_settings, user, call_info,
            intent_result=intent_result, class_level=rag_class_level,
        ):
            full_reply.append(chunk)
            yield chunk
    finally:
        elapsed_s = time.perf_counter() - t0
        if full_reply:
            reply_text = "".join(full_reply)
            db.add_message(
                conversation_id, "assistant", reply_text,
                engine=response_strategy.ENGINE_LLM, provider=call_info.get("provider"),
            )
            db.touch_conversation(conversation_id)
            # Clé recalculée avec le provider/modèle RÉELLEMENT utilisé (voir
            # call_info, rempli par llm_fallback_service.generate — peut
            # différer de provider_name/model_name choisis en amont si un
            # fallback a eu lieu), jamais celle du GET ci-dessus — même
            # correction que regenerate_last : sans elle, une réponse produite
            # par un fournisseur de repli serait mise en cache sous la clé du
            # fournisseur initialement visé, et resservie à tort une fois ce
            # dernier redevenu disponible.
            actual_provider, actual_model = call_info.get("provider"), call_info.get("model")
            write_cache_key = cache.make_key(
                user["id"], actual_provider, actual_model, user_message,
                class_level=(student_context or {}).get("class_level"), topic=intent_result.get("chapter_id"),
            )
            cache.set(write_cache_key, reply_text)
            pipeline_metrics.record_response(response_strategy.ENGINE_LLM, local=False, elapsed_ms=elapsed_s * 1000)
            # Chantier "fausse mémoire d'approche" (2026-08-22) — étape 2/2 :
            # `intent_result["actual_approach"]` n'est posé que si le mode
            # dégradé (degraded_mode_service.try_answer, appelé depuis
            # llm_fallback_service._stream_chunks) a réellement produit la
            # réponse — reste absent/None si le vrai LLM a répondu, auquel cas
            # rien n'est commité (une réponse LLM libre n'a pas d'« approche »
            # du vocabulaire d'escalade à mémoriser).
            _commit_actual_approach(conversation_id, intent_result.get("actual_approach"))
            # Chantier "répétition des exemples" (2026-08-23) — même principe :
            # `intent_result["new_exemple_ids"]` n'est posé que si le mode
            # dégradé a réellement composé un exemple ce tour (voir
            # degraded_mode_service.try_answer) — vide/absent sinon.
            _commit_used_exemples(conversation_id, intent_result.get("new_exemple_ids"))
        if call_info:
            _log_llm_call_details(user, call_info, elapsed_s, conversation_id=conversation_id, request_id=request_id)


def regenerate_last(user, conversation_id, chapters_summary=None, debug=False, class_level=None, request_id=None):
    """Supprime le dernier message assistant et redemande une réponse à partir
    du dernier message utilisateur (rejoué, pas dupliqué)."""
    t0 = time.perf_counter()
    pipeline_metrics.record_request()

    rows = db.list_messages(conversation_id)
    if not rows or rows[-1]["role"] != "assistant":
        raise ValueError("Rien à régénérer.")
    last_user = next((m for m in reversed(rows[:-1]) if m["role"] == "user"), None)
    if last_user is None:
        raise ValueError("Aucun message utilisateur précédent.")
    # Jeton de course : db.delete_message renvoie False si une autre requête
    # concurrente (double-clic, double onglet) a déjà supprimé CE message
    # avant nous — dans ce cas on abandonne immédiatement, AVANT de consommer
    # du quota ou de générer quoi que ce soit, plutôt que de produire une
    # seconde réponse assistant dupliquée pour une seule intention
    # utilisateur (voir db.delete_message et l'audit production correspondant).
    if not db.delete_message(rows[-1]["id"]):
        raise ValueError("Cette réponse est déjà en cours de régénération.")

    check_and_increment_quota(user)
    settings = read_user_settings(user["id"])
    chatbot_settings = settings.get("chatbot", {})
    learning_context = db.get_conversation_learning_context(conversation_id)
    context_summary = build_context_summary(user, chapters_summary, class_level=class_level)
    # Dernier message assistant AVANT le message assistant qu'on régénère
    # (déjà supprimé ci-dessus, voir db.delete_message plus haut) — donc le
    # message qui précédait la réponse qu'on est en train de recalculer,
    # même sémantique que dans _generate_assistant_reply (résolution
    # "oui"/"non" nu par rapport à ce qui a réellement été demandé).
    last_assistant_message = _previous_assistant_message_text(conversation_id)
    intent_result = _classify_intent(
        last_user["content"], context_summary, class_level=class_level, learning_context=learning_context,
        last_assistant_message=last_assistant_message,
    )
    mention_intent = mentions_service.single_data_mention_intent(last_user["content"], last_user.get("mentions"))
    if mention_intent:
        intent_result = {**intent_result, "intent": mention_intent}
    if _detect_repeated_incomprehension(intent_result, conversation_id, context_summary, class_level, learning_context):
        intent_result = {**intent_result, "repeated_incomprehension": True}
    # Phase H (régénération/réessai) : une régénération ne doit pas changer
    # de sujet simplement parce que la classification varie légèrement d'un
    # appel à l'autre — même garde que le tour normal (_LOW_CONFIDENCE_TOPIC).
    # advance_escalation=False (chantier "regenerate_last n'avance pas
    # l'état pédagogique", 2026-08-22) : regenerate_last() rejoue LE MÊME
    # message utilisateur déjà compté lors du tour original — sans cette
    # garde, _update_learning_context incrémentait incomprehension_count une
    # seconde fois pour une seule intention réelle de l'élève (bug confirmé
    # par le test live : count passait de 2 à 3 sur une simple régénération).
    topic_label = _update_learning_context(
        conversation_id, intent_result, class_level=class_level, existing_learning_context=learning_context,
        advance_escalation=False,
    )

    student_context = _resolve_student_context(
        user, chapters_summary, chatbot_settings, last_user.get("mentions"), history_rows=None, class_level=class_level,
    )
    strategy = _decide_strategy_shadow(
        last_user["content"], user, chapters_summary, chatbot_settings, last_user.get("mentions"), student_context, debug,
        class_level=class_level, learning_context=learning_context, last_assistant_message=last_assistant_message,
    )
    local_result = _try_local_response_engine(
        strategy, last_user["content"], user, chapters_summary, chatbot_settings,
        last_user.get("mentions"), student_context, debug, class_level=class_level,
        learning_context=learning_context, last_assistant_message=last_assistant_message,
        escalation_level=intent_result.get("escalation_level", 0),
        recommended_approach=intent_result.get("recommended_approach"),
        used_exemple_ids=intent_result.get("used_exemple_ids", ()),
    )
    # Chantiers "fausse mémoire d'approche"/"répétition des exemples" :
    # AUCUN commit ici, volontairement — voir TestRegenerationNAvancePasLescalade
    # et la contrainte explicite "regenerate_last() ne doit jamais modifier
    # approaches_used/used_exemple_ids". used_exemple_ids ci-dessus n'est
    # transmis qu'en LECTURE (pour préférer un exemple pas déjà vu si
    # possible), jamais complété après coup par cette fonction.
    if local_result is not None:
        db.add_message(conversation_id, "assistant", local_result.text, engine=local_result.engine)
        db.touch_conversation(conversation_id)
        elapsed_ms = (time.perf_counter() - t0) * 1000
        pipeline_metrics.record_response(local_result.engine, local=True, elapsed_ms=elapsed_ms, fallback=local_result.used_fallback)
        pipeline_metrics.log_comparison(strategy, local_result.engine)
        ai_request_log_service.record_local_response(
            user["id"], conversation_id, local_result.engine, "local", local_result.engine,
            user_text=last_user["content"], response_text=local_result.text, response_time_ms=elapsed_ms,
            fallback=local_result.used_fallback,
        )
        yield local_result.text
        return

    # Même priorité locale que stream_reply (Phase Q) : régénérer une
    # question de progression/statistiques/exercice ne doit pas non plus
    # appeler le LLM.
    local_answer = local_knowledge_service.try_answer(
        intent_result, user, context_summary, chatbot_settings, user_message=last_user["content"],
        student_context=student_context,
    )
    if local_answer is not None:
        db.add_message(conversation_id, "assistant", local_answer, engine="legacy_local_knowledge")
        db.touch_conversation(conversation_id)
        elapsed_ms = (time.perf_counter() - t0) * 1000
        pipeline_metrics.record_response("legacy_local_knowledge", local=True, elapsed_ms=elapsed_ms)
        pipeline_metrics.log_comparison(strategy, "legacy_local_knowledge")
        ai_request_log_service.record_local_response(
            user["id"], conversation_id, "legacy_local_knowledge", "local", "legacy_local_knowledge",
            user_text=last_user["content"], response_text=local_answer, response_time_ms=elapsed_ms,
        )
        yield local_answer
        return

    if not ENABLE_LLM_FALLBACK:
        db.add_message(conversation_id, "assistant", LLM_DISABLED_MESSAGE, engine="llm_disabled")
        db.touch_conversation(conversation_id)
        elapsed_ms = (time.perf_counter() - t0) * 1000
        pipeline_metrics.record_response("llm_disabled", local=True, elapsed_ms=elapsed_ms)
        ai_request_log_service.record_local_response(
            user["id"], conversation_id, "llm_disabled", "local", "llm_disabled",
            user_text=last_user["content"], response_text=LLM_DISABLED_MESSAGE, response_time_ms=elapsed_ms,
        )
        yield LLM_DISABLED_MESSAGE
        return

    rag_class_level = (student_context or {}).get("class_level")
    rag_context = _resolve_rag_context(intent_result, last_user["content"], class_level=rag_class_level)
    mentions_block = mentions_service.build_grounding_block(
        last_user.get("mentions"), user=user, chapters_summary=chapters_summary,
        class_level=rag_class_level,
    )
    system_prompt = build_system_prompt(
        user, chatbot_settings, chapters_summary, rag_context, mentions_block, intent_result=intent_result,
        class_level=rag_class_level, topic_label=topic_label,
    )
    messages = build_messages(db.list_messages(conversation_id))
    pipeline_metrics.log_comparison(strategy, response_strategy.ENGINE_LLM)
    _record_llm_call(last_user["content"], strategy)

    call_info = {}
    full_reply = []
    try:
        for chunk in llm_fallback_service.generate(
            messages, system_prompt, chatbot_settings, user, call_info,
            intent_result=intent_result, class_level=rag_class_level,
        ):
            full_reply.append(chunk)
            yield chunk
    finally:
        elapsed_s = time.perf_counter() - t0
        if full_reply:
            reply_text = "".join(full_reply)
            db.add_message(
                conversation_id, "assistant", reply_text,
                engine=response_strategy.ENGINE_LLM, provider=call_info.get("provider"),
            )
            db.touch_conversation(conversation_id)
            provider_name, model_name = call_info.get("provider"), call_info.get("model")
            cache_key = cache.make_key(
                user["id"], provider_name, model_name, last_user["content"],
                class_level=(student_context or {}).get("class_level"), topic=intent_result.get("chapter_id"),
            )
            cache.set(cache_key, reply_text)
            pipeline_metrics.record_response(response_strategy.ENGINE_LLM, local=False, elapsed_ms=elapsed_s * 1000)
        if call_info:
            _log_llm_call_details(user, call_info, elapsed_s, conversation_id=conversation_id, request_id=request_id)


# ── Cartes d'action (Phase C) ────────────────────────────────────────────────
def attach_action_cards(user, conversation_id, chapters_summary=None, class_level=None):
    """Appelée par les routes SSE une fois le stream texte terminé (voir
    server.py::api_chatbot_messages/api_chatbot_regenerate) : calcule les
    cartes d'action pertinentes pour le dernier échange et les persiste sur
    le dernier message assistant, pour qu'elles réapparaissent à l'historique.
    Ne modifie jamais le contenu texte déjà streamé/persisté."""
    rows = db.list_messages(conversation_id)
    if not rows or rows[-1]["role"] != "assistant":
        return []
    last_assistant = rows[-1]
    last_user = next((m for m in reversed(rows[:-1]) if m["role"] == "user"), None)
    if last_user is None:
        return []

    context_summary = build_context_summary(user, chapters_summary, class_level=class_level)
    intent_result = _classify_intent(last_user["content"], context_summary, class_level=class_level)
    mention_intent = mentions_service.single_data_mention_intent(last_user["content"], last_user.get("mentions"))
    if mention_intent:
        intent_result = {**intent_result, "intent": mention_intent}

    chatbot_settings = read_user_settings(user["id"]).get("chatbot", {})
    _resolve_student_context(
        user, chapters_summary, chatbot_settings, last_user.get("mentions"), history_rows=None, class_level=class_level,
    )

    search_results = search_service.search(last_user["content"], limit=8, class_level=class_level)
    intent_chapter_id = (
        intent_result["chapter_id"] if intent_result["intent"] == intent_service.EXERCICE else None
    )
    # Phase S : quand la réponse portait sur la progression/les statistiques,
    # propose de revoir le chapitre le plus faible de l'élève (même donnée
    # réelle que celle utilisée pour composer la réponse, variable_resolver.py).
    weak_chapter_id = None
    if intent_result["intent"] in (intent_service.PROGRESSION, intent_service.STATISTIQUE):
        variables = variable_resolver.resolve(
            user, context_summary, read_user_settings(user["id"]).get("chatbot", {}), class_level=class_level,
        )
        candidate = variables.get("chapitre_le_plus_faible")
        if candidate and candidate != variable_resolver.NO_DATA:
            weak_chapter_id = candidate
    cards = action_cards_service.build_cards(
        last_user["content"], last_assistant["content"], context_summary, search_results,
        intent_chapter_id=intent_chapter_id, weak_chapter_id=weak_chapter_id, class_level=class_level,
    )
    if cards:
        db.set_message_cards(last_assistant["id"], cards)
    return cards


def set_feedback(user_id, message_id, liked):
    message = db.get_message(message_id)
    if message is None:
        raise ValueError("Message introuvable.")
    conv = db.get_conversation(message["conversation_id"], user_id)
    if conv is None:
        raise ValueError("Message introuvable.")
    db.set_message_feedback(message_id, liked)
