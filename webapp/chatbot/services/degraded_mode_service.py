"""
Mode dégradé du chatbot NovaMath — audit du 2026-07-26 : quand le fournisseur
IA réellement actif (Gemini) est indisponible (voir provider_manager.
select_llm_for_user, qui renvoie ("fake", None) une fois tous les candidats
de la chaîne du plan épuisés/en cache d'indisponibilité), NovaMath ne doit
PAS se contenter du message générique de FakeProvider (voir fake_provider.py
::NO_MATCH_ANSWERS) — il doit d'abord exploiter tout ce qui est déjà connu
de la conversation, exactement comme un professeur le ferait sans accès à
une IA générative.

Appelé UNIQUEMENT par llm_fallback_service.generate(), juste avant de
basculer sur FakeProvider — jamais un appel direct depuis
conversation_manager.py (qui reste inchangé sur ce point : il ignore
totalement si le tour se terminera sur Gemini ou en mode dégradé). Contrairement
à fake_provider.py (qui ne reçoit que le texte déjà figé du prompt système,
partagé à l'identique avec Gemini — jamais modifiable pour ce chantier),
ce module accède directement aux VRAIS objets notion via knowledge_engine
(a_retenir, exemples structurés) et à la banque d'exercices via
search_service — jamais disponibles dans le texte du prompt.

Ordre de repli (du plus fiable au moins fiable, jamais un abandon prématuré) :
1. Notion précise du Current Learning Context (lookup exact par
   chapter_id/notion_id — voir conversation_manager._update_learning_context).
2. Chapitre du Current Learning Context connu sans notion précise (notion
   représentative du chapitre, lookup exact).
3. Recherche sur l'historique récent de la conversation : un message ambigu
   ("je n'ai toujours pas compris") ne contient lui-même aucun mot-clé
   exploitable, mais les messages précédents (question initiale de l'élève,
   réponse de l'assistant) le contiennent presque toujours.
4. Recherche floue sur le message courant (RAG générique, même moteur que
   conversation_manager._resolve_rag_context).
5. Banque d'exercices (search_service) — dernier repli avant d'admettre
   qu'aucun sujet n'a pu être déterminé.

Renvoie None seulement si absolument aucun de ces paliers n'a rien donné —
c'est alors, et alors seulement, que FakeProvider affiche son message de
clarification neutre.
"""
import logging

from .. import knowledge_engine
from . import intent_service, search_service

logger = logging.getLogger("chatbot.services.degraded_mode")

# Nombre de messages récents (élève + assistant) pris en compte pour la
# recherche sur l'historique (palier 3) — au-delà, le sujet a probablement
# changé plusieurs fois, une fenêtre trop large risquerait de remonter un
# ancien sujet abandonné plutôt que le sujet réellement en cours.
_MAX_HISTORY_MESSAGES_FOR_SEARCH = 6


def _last_user_message(messages):
    for message in reversed(messages or []):
        if message.get("role") == "user":
            return message.get("content", "")
    return ""


# Chantier "mode dégradé répétitif" (2026-08-22) : audit LIVE confirmé — quand
# Gemini est indisponible plusieurs tours de suite (quota/panne), ce module
# répondait avec le même a_retenir[0] à chaque appel, produisant des réponses
# strictement identiques (MSG3 == MSG4 au caractère près, cas réel observé sur
# "Chapitre_2/valeur-absolue-dun-nombre-reel"). `messages` (déjà reçu par
# try_answer, mêmes objets que ceux envoyés à Gemini via prompt_builder.
# build_messages) contient l'historique complet, y COMPRIS les réponses
# assistant déjà données pour CETTE conversation — jamais exploité jusqu'ici.
def _recent_assistant_text(messages):
    """Concatène le texte des réponses assistant déjà présentes dans
    `messages` — sert uniquement à repérer ce qui a déjà été montré à
    l'élève, jamais pour autre chose. Même principe que
    phrasing_memory.recent_assistant_text, adapté au format `messages`
    ({role, content}) déjà reçu par try_answer plutôt qu'à un StudentContext."""
    return " \n".join(m.get("content", "") for m in (messages or []) if m.get("role") == "assistant")


def _pick_unused(candidates, avoid_blob):
    """Renvoie le premier élément de `candidates` absent (mot pour mot) de
    `avoid_blob` — stratégie VOLONTAIREMENT déterministe (jamais un
    `random.choice`, qui pourrait retomber deux fois de suite sur le même
    élément par hasard, et rendrait les tests non reproductibles) : le même
    historique produit toujours le même choix, testable de façon stable.
    Repli sur le premier élément si tous ont déjà été vus (mieux vaut répéter
    occasionnellement qu'échouer) ou s'il n'y en a qu'un seul — dans ce cas
    la répétition est normale et attendue (aucune autre donnée disponible),
    pas une régression."""
    for candidate in candidates:
        if candidate and candidate not in avoid_blob:
            return candidate
    return candidates[0] if candidates else None


def _notion_from_learning_context(intent_result, class_level=None):
    """Paliers 1+2 : Current Learning Context (chapter_id/notion_id déjà
    résolus par intent_service.classify, voir conversation_manager.py). Un
    chapitre connu sans notion précise retombe sur une notion représentative
    du chapitre (première du fichier source) — même repli que
    knowledge_engine.chapter_context_block, mais ici on a besoin de l'OBJET
    notion complet (pas seulement son texte formaté) pour accéder à
    get_a_retenir()/get_exemple() ci-dessous."""
    chapter_id = intent_result.get("chapter_id")
    if not chapter_id:
        return None
    notion_id = intent_result.get("notion_id")
    if notion_id:
        notion = knowledge_engine.get_notion(chapter_id, notion_id, class_level=class_level)
        if notion:
            return notion
    candidates = [
        doc for doc in knowledge_engine.all_documents(class_level=class_level)
        if doc["chapter_id"] == chapter_id
    ]
    return candidates[0] if candidates else None


def _notion_from_history(messages, class_level=None):
    """Palier 3 : recherche sur les derniers messages de la conversation
    (question initiale de l'élève, réponse précédente de l'assistant),
    jamais seulement le message courant — voir docstring du module."""
    prior_messages = (messages or [])[:-1]
    if not prior_messages:
        return None
    recent_text = " ".join(
        m.get("content", "") for m in prior_messages[-_MAX_HISTORY_MESSAGES_FOR_SEARCH:] if m.get("content")
    )
    if not recent_text.strip():
        return None
    matches = knowledge_engine.search(recent_text, top_k=1, class_level=class_level)
    return matches[0] if matches else None


def _notion_from_message(user_message, class_level=None):
    """Palier 4 : recherche floue sur le message courant lui-même (RAG
    générique) — même moteur que knowledge_engine.context_block, mais on
    garde ici l'objet notion complet plutôt que le texte déjà formaté."""
    if not (user_message or "").strip():
        return None
    matches = knowledge_engine.search(user_message, top_k=1, class_level=class_level)
    return matches[0] if matches else None


def _exercise_fallback(chapter_id, user_message, class_level=None):
    """Palier 5 : banque d'exercices — d'abord scopée au chapitre déjà connu
    (jamais un exercice d'un autre chapitre par coïncidence de vocabulaire,
    voir search_service.search_exercises_in_chapter), sinon une recherche
    libre sur la banque entière en tout dernier recours avant d'admettre
    qu'aucun sujet n'a pu être déterminé."""
    if chapter_id:
        results = search_service.search_exercises_in_chapter(
            chapter_id, query=user_message, limit=1, class_level=class_level,
        )
        if results:
            return results[0]
    results = search_service.search(
        user_message, scope=[search_service.SCOPE_EXERCICES], limit=1, class_level=class_level,
    )
    return results[0] if results else None


def _exemple_leadin(notion, exclude_ids, normal_text):
    """Chantier "répétition des exemples" (2026-08-23) : `normal_text` si un
    exemple réellement inédit reste disponible, sinon une formulation
    honnête (jamais un texte prétendant un exemple neuf alors que le stock
    de la notion est épuisé — voir knowledge_engine.exemple_pool_exhausted)."""
    if knowledge_engine.exemple_pool_exhausted(notion, exclude_ids):
        return "Je n'ai pas d'autre exemple différent sous la main pour ce point précis — reprenons celui-ci, ça vaut le coup de bien le fixer :"
    return normal_text


def _build_definition_answer(lines, notion, avoid_blob, restart_from_basics, exclude_ids=()):
    """Niveau 0 (ou repli par défaut) — comportement historique inchangé :
    une idée (a_retenir/règle) + un exemple avec sa réponse. Renvoie
    `(approche, exemple_id)` — l'approche RÉELLEMENT produite ("definition",
    voir chantier "fausse mémoire d'approche", 2026-08-22) et l'id de
    l'exemple RÉELLEMENT inclus (None si aucun, chantier "répétition des
    exemples", 2026-08-23 — voir conversation_manager._commit_used_exemples).
    `exclude_ids` : ids d'exemples déjà montrés dans la conversation, exclus
    du tirage en priorité (repli honnête si le stock est épuisé, voir
    _exemple_leadin)."""
    a_retenir = knowledge_engine.get_a_retenir(notion)
    regles = knowledge_engine.get_regles(notion)
    idee_pool = (list(regles) + list(a_retenir)) if restart_from_basics else (list(a_retenir) + list(regles))
    idee = _pick_unused(idee_pool, avoid_blob) if idee_pool else None
    lines.append(f"L'idée importante : {idee}" if idee else (notion.get("definition") or ""))

    exemple = knowledge_engine.get_exemple(notion, exclude_ids=exclude_ids)
    exemple_id = None
    if exemple and exemple.get("enonce"):
        exemple_id = exemple.get("id")
        lines.append("")
        lines.append(_exemple_leadin(notion, exclude_ids, "Voici un autre exemple :"))
        lines.append(exemple["enonce"])
        if exemple.get("reponse"):
            lines.append(f"Réponse : {exemple['reponse']}")

    if restart_from_basics:
        erreurs = notion.get("erreurs") or []
        erreur = _pick_unused(erreurs, avoid_blob) if erreurs else None
        if erreur:
            lines.append("")
            lines.append(f"Attention à l'erreur fréquente : {erreur}")

    lines.append("")
    lines.append("Dis-moi ensuite précisément ce qui te bloque.")
    return "definition", exemple_id


def _build_exemple_answer(lines, notion, avoid_blob, exclude_ids=()):
    """Niveau 1 (recommended_approach="exemple") — structure CONCEPT (bref)
    → EXEMPLE CONCRET → petite conclusion. Renvoie `(approche, exemple_id)` —
    "exemple" si un exemple a réellement été inclus, sinon "definition"
    (repli explicite, jamais inventé — voir _build_definition_answer)."""
    a_retenir = knowledge_engine.get_a_retenir(notion)
    regles = knowledge_engine.get_regles(notion)
    idee = _pick_unused(list(a_retenir) + list(regles), avoid_blob) if (a_retenir or regles) else None
    lines.append(f"Pour rappel : {idee}" if idee else (notion.get("definition") or ""))
    lines.append("")

    exemple = knowledge_engine.get_exemple(notion, exclude_ids=exclude_ids)
    if exemple and exemple.get("enonce"):
        lines.append(_exemple_leadin(notion, exclude_ids, "Voyons ça avec un exemple concret :"))
        lines.append(exemple["enonce"])
        if exemple.get("reponse"):
            lines.append(f"Réponse : {exemple['reponse']}")
        lines.append("")
        lines.append("Regarde bien comment on applique la règle dans ce cas précis.")
        return "exemple", exemple.get("id")
    # Aucun exemple disponible pour cette notion — jamais d'invention, repli
    # explicite sur la structure niveau 0 (garde-fou).
    return _build_definition_answer(lines, notion, avoid_blob, restart_from_basics=False, exclude_ids=exclude_ids)


def _build_analogie_answer(lines, notion, avoid_blob, exclude_ids=()):
    """Niveau 2 (recommended_approach="analogie") — REPLI HONNÊTE : aucune
    notion migrée ne porte de champ d'analogie réel (vérifié) — ce module NE
    FABRIQUE JAMAIS d'analogie depuis rien. Structure de repli assumée :
    PRÉREQUIS/RÈGLE SIMPLE → exemple concret → mini-vérification.

    Chantier "fausse mémoire d'approche" (2026-08-22) : cette fonction NE
    PRODUIT JAMAIS de vraie analogie (aucune donnée du corpus ne le permet
    aujourd'hui) — elle renvoie donc TOUJOURS "exemple" (si un exemple a pu
    être inclus) ou "definition" (sinon), JAMAIS "analogie". C'est
    précisément la correction du bug confirmé par l'audit QA : avant ce
    correctif, "analogie" était mémorisée dans approaches_used pour CE
    résultat alors qu'aucune analogie n'était réellement produite. Renvoie
    `(approche, exemple_id)` — voir _build_definition_answer."""
    regles = knowledge_engine.get_regles(notion)
    a_retenir = knowledge_engine.get_a_retenir(notion)
    regle = _pick_unused(list(regles) + list(a_retenir), avoid_blob) if (regles or a_retenir) else None
    lines.append("Reprenons depuis la règle de base, simplement :")
    lines.append(regle if regle else (notion.get("definition") or ""))

    exemple = knowledge_engine.get_exemple(notion, exclude_ids=exclude_ids)
    if exemple and exemple.get("enonce"):
        lines.append("")
        lines.append(_exemple_leadin(notion, exclude_ids, "Applique-la sur ce cas concret :"))
        lines.append(exemple["enonce"])
        if exemple.get("reponse"):
            lines.append(f"Réponse : {exemple['reponse']}")
        lines.append("")
        lines.append("Est-ce que cette règle te semble plus claire maintenant ?")
        return "exemple", exemple.get("id")
    lines.append("")
    lines.append("Est-ce que cette règle te semble plus claire maintenant ?")
    return "definition", None


def _build_question_guidee_answer(lines, notion, avoid_blob, exclude_ids=()):
    """Niveau 3 (recommended_approach="question_guidee") — LE PLUS IMPORTANT.
    Contrairement à tous les niveaux précédents, cette fonction NE DONNE PLUS
    l'explication complète. Elle rappelle le strict minimum (une ligne), puis
    pose une VRAIE QUESTION DE RAISONNEMENT (chantier "vraie question
    guidée", 2026-08-22 : le QA a confirmé que la version précédente,
    purement impérative ("Essaie cette étape..."), n'était formellement pas
    une question — corrigé en une interrogation explicite qui porte sur le
    raisonnement, jamais une simple confirmation rhétorique du type "tu
    comprends ?") construite à partir de l'énoncé d'un VRAI exemple de la
    notion (jamais une question inventée sans rapport). La réponse/le calcul
    de l'exemple ne sont JAMAIS révélés. Si aucun exemple n'est disponible
    pour construire une question sûre, repli explicite sur le niveau 0
    (jamais de question mathématique fabriquée sans donnée) — renvoie alors
    "definition", jamais "question_guidee". Renvoie `(approche, exemple_id)`."""
    exemple = knowledge_engine.get_exemple(notion, exclude_ids=exclude_ids)
    if not exemple or not exemple.get("enonce"):
        return _build_definition_answer(lines, notion, avoid_blob, restart_from_basics=True, exclude_ids=exclude_ids)

    a_retenir = knowledge_engine.get_a_retenir(notion)
    rappel = a_retenir[0] if a_retenir else (notion.get("definition") or "")
    lines.append(f"Pour rappel, en une phrase : {rappel}")
    lines.append("")
    lines.append(_exemple_leadin(notion, exclude_ids, "Regarde cet exemple :"))
    lines.append(exemple["enonce"])
    lines.append("")
    lines.append(
        "Quelle serait, selon toi, la première étape pour résoudre ce cas ? "
        "Essaie-la, puis dis-moi ce que tu trouves — je ne te donne pas encore la réponse."
    )
    return "question_guidee", exemple.get("id")


def _build_pedagogical_answer(
    notion, reformulation, intent=None, avoid_blob="", escalation_level=0, recommended_approach=None,
    exclude_exemple_ids=(),
):
    """Compose une VRAIE explication à partir de la notion trouvée — jamais
    un simple copier-coller du bloc RAG déjà figé dans le prompt système
    (voir docstring du module). `reformulation` : True si l'élève poursuit
    sur un sujet déjà établi (intent_result["topic_inherited"]) — change
    l'ouverture, jamais le sujet traité.

    `recommended_approach` (chantier "escalade réellement exécutée",
    2026-08-22) : SOURCE DE VÉRITÉ du plan pédagogique de ce tour — calculé
    par conversation_manager._select_approach à partir de données RÉELLEMENT
    disponibles pour la notion (voir conversation_manager.
    _approaches_available_for_notion), donc toujours réalisable ici SANS
    invention. Chaque approche a sa propre structure (voir les fonctions
    _build_*_answer ci-dessus) — ce n'est plus seulement un réordonnancement
    de la même liste, mais un changement RÉEL de forme pédagogique :
    - "definition" : idée + exemple complet (comportement historique).
    - "exemple"    : rappel bref → exemple mis en avant → conclusion.
    - "analogie"   : règle simple (repli honnête, aucune fausse analogie
                     inventée) → exemple → mini-vérification.
    - "question_guidee" : rappel minimal SEULEMENT → question construite sur
                     un vrai exemple → attente de la réponse de l'élève
                     (la réponse de l'exemple n'est jamais révélée ici).
    `intent`/`escalation_level` restent lus pour le repli historique
    (`recommended_approach` absent — compatibilité) et pour la garde
    "erreur fréquente" du niveau 0.

    Renvoie `(texte, actual_approach, exemple_id)` — chantier "fausse mémoire
    d'approche" (2026-08-22) : `actual_approach` est l'approche RÉELLEMENT
    produite par la fonction `_build_*_answer` dispatchée, jamais supposée
    égale à `recommended_approach` (voir try_answer(), qui persiste cette
    valeur — jamais `recommended_approach` — dans approaches_used).
    `exemple_id` (chantier "répétition des exemples", 2026-08-23) : id de
    l'exemple RÉELLEMENT inclus (None si aucun) — `exclude_exemple_ids` (ids
    déjà montrés dans la conversation) est transmis à chaque fonction
    `_build_*_answer` pour éviter de reproposer le même."""
    title = notion.get("title") or "cette notion"
    lines = []
    lines.append(f"Reprenons {title} autrement." if reformulation else f"Voici ce que dit ton cours sur {title} :")
    lines.append("")

    restart_from_basics = intent == intent_service.RESTART_BASICS or (escalation_level or 0) >= 2

    if recommended_approach == "exemple":
        actual_approach, exemple_id = _build_exemple_answer(lines, notion, avoid_blob, exclude_ids=exclude_exemple_ids)
    elif recommended_approach == "analogie":
        actual_approach, exemple_id = _build_analogie_answer(lines, notion, avoid_blob, exclude_ids=exclude_exemple_ids)
    elif recommended_approach == "question_guidee":
        actual_approach, exemple_id = _build_question_guidee_answer(lines, notion, avoid_blob, exclude_ids=exclude_exemple_ids)
    else:
        actual_approach, exemple_id = _build_definition_answer(
            lines, notion, avoid_blob, restart_from_basics, exclude_ids=exclude_exemple_ids,
        )

    return "\n".join(lines), actual_approach, exemple_id


def _build_exercise_answer(exercise):
    """Réponse de dernier repli (palier 5) : pas de nouvelle explication de
    cours disponible, mais un exercice réel sur le même sujet pour continuer
    à faire progresser l'élève plutôt que d'abandonner."""
    lines = [
        f"Je n'ai pas de nouvelle explication de cours à te proposer sur ce point précis, "
        f"mais voici un exercice sur {exercise['title']} pour t'entraîner :",
        "",
        exercise["snippet"],
        "",
        "Essaie de le résoudre, puis dis-moi précisément où tu bloques.",
    ]
    return "\n".join(lines)


def try_answer(intent_result, messages, class_level=None):
    """Point d'entrée unique — voir docstring du module pour l'ordre de
    repli complet. `intent_result` : dict renvoyé par intent_service.classify
    (chapter_id/notion_id/topic_inherited), ou None. `messages` : historique
    au format provider ({role, content}, voir prompt_builder.build_messages)
    — le dernier message est toujours le message courant de l'élève. Renvoie
    une chaîne de réponse, ou None si absolument aucun palier n'a rien
    trouvé (FakeProvider affiche alors son message de clarification neutre).

    Chantier "fausse mémoire d'approche" (2026-08-22) : quand un des 3
    premiers paliers compose réellement une réponse pédagogique (via
    _build_pedagogical_answer), l'approche RÉELLEMENT produite est écrite
    dans `intent_result["actual_approach"]` — EN PLACE, sur le même dict que
    l'appelant (conversation_manager.py) continue de détenir (même principe
    déjà utilisé pour `repeated_incomprehension`/`escalation_level` : une
    mutation en place, pas un nouveau contrat de retour pour cette fonction,
    qui reste "une chaîne, ou None"). L'appelant lit ensuite cette clé après
    la fin du flux de réponse pour décider quoi persister dans
    approaches_used (voir conversation_manager._commit_actual_approach)."""
    intent_result = intent_result or {}
    user_message = _last_user_message(messages)
    intent = intent_result.get("intent")
    avoid_blob = _recent_assistant_text(messages)
    escalation_level = intent_result.get("escalation_level") or 0
    recommended_approach = intent_result.get("recommended_approach")
    # Chantier "répétition des exemples" (2026-08-23) : ids déjà montrés
    # DANS CETTE CONVERSATION (voir conversation_manager._update_learning_
    # context / _commit_used_exemples), transmis tel quel — aucun recalcul,
    # aucune nouvelle logique de mémorisation ici.
    exclude_exemple_ids = tuple(intent_result.get("used_exemple_ids") or ())

    notion = _notion_from_learning_context(intent_result, class_level=class_level)
    if notion:
        text, actual_approach, exemple_id = _build_pedagogical_answer(
            notion, reformulation=bool(intent_result.get("topic_inherited")), intent=intent, avoid_blob=avoid_blob,
            escalation_level=escalation_level, recommended_approach=recommended_approach,
            exclude_exemple_ids=exclude_exemple_ids,
        )
        intent_result["actual_approach"] = actual_approach
        intent_result["new_exemple_ids"] = (exemple_id,) if exemple_id and exemple_id not in exclude_exemple_ids else ()
        return text

    notion = _notion_from_history(messages, class_level=class_level)
    if notion:
        text, actual_approach, exemple_id = _build_pedagogical_answer(
            notion, reformulation=False, intent=intent, avoid_blob=avoid_blob, escalation_level=escalation_level,
            recommended_approach=recommended_approach, exclude_exemple_ids=exclude_exemple_ids,
        )
        intent_result["actual_approach"] = actual_approach
        intent_result["new_exemple_ids"] = (exemple_id,) if exemple_id and exemple_id not in exclude_exemple_ids else ()
        return text

    notion = _notion_from_message(user_message, class_level=class_level)
    if notion:
        text, actual_approach, exemple_id = _build_pedagogical_answer(
            notion, reformulation=False, intent=intent, avoid_blob=avoid_blob, escalation_level=escalation_level,
            recommended_approach=recommended_approach, exclude_exemple_ids=exclude_exemple_ids,
        )
        intent_result["actual_approach"] = actual_approach
        intent_result["new_exemple_ids"] = (exemple_id,) if exemple_id and exemple_id not in exclude_exemple_ids else ()
        return text

    exercise = _exercise_fallback(intent_result.get("chapter_id"), user_message, class_level=class_level)
    if exercise:
        return _build_exercise_answer(exercise)

    return None
