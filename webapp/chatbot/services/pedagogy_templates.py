"""
Bibliothèque de préréponses pédagogiques (cahier des charges, section 3) :
pas des réponses toutes faites, mais des fragments d'instruction système par
intention (intent_service.classify, Phase G) et par mode de réponse
(paramètres du chatbot, Phase I) — pour que le fournisseur IA adopte le bon
format selon ce que l'élève demande réellement, plutôt que de répondre de
façon générique à "donne-moi un exemple" comme à "explique-moi".
"""
from . import intent_service

_INTENT_INSTRUCTIONS = {
    intent_service.EXERCICE: (
        "L'élève demande un exercice d'entraînement. Présente l'exercice fourni ci-dessous "
        "(jamais un autre), puis laisse-le chercher avant de donner la solution complète."
    ),
    intent_service.EXEMPLE: (
        "L'élève demande un exemple. Donne un exemple simple, concret et entièrement résolu, "
        "sur exactement la notion demandée — jamais une autre notion."
    ),
    intent_service.FICHE: (
        "L'élève demande une fiche de synthèse. Structure ta réponse comme une fiche : "
        "définition, règles/propriétés clés, méthode, exemple rapide, erreurs fréquentes à éviter."
    ),
    intent_service.RESTART_BASICS: (
        "L'élève dit n'avoir rien compris. Repars des prérequis avec un vocabulaire très simple, "
        "en petites étapes, sans supposer aucune connaissance acquise sur cette notion."
    ),
    intent_service.QUIZ: (
        "L'élève veut être interrogé. Pose UNE seule question à la fois sur la notion concernée, "
        "attends sa réponse avant de donner la correction ou la question suivante."
    ),
    intent_service.CORRECTION: (
        "L'élève demande une correction. Corrige pas à pas, indique précisément où se situe "
        "l'erreur, sans donner d'emblée la solution complète s'il n'a pas encore réessayé."
    ),
    intent_service.REFORMULATION: (
        "L'élève demande une nouvelle explication de la même notion, formulée différemment "
        "(reformulation, simplification, nouvel exemple, incompréhension exprimée...). Ne change "
        "surtout pas de sujet : explique cette même notion avec une approche différente (autre "
        "angle, autre exemple, vocabulaire plus simple si besoin), jamais une autre notion."
    ),
    intent_service.FOLLOWUP: (
        "L'élève poursuit directement l'échange qui précède (« continue », « pourquoi ? », "
        "« développe », ou une confirmation « oui »/« non » à ta dernière question). Ne redémarre "
        "PAS une nouvelle explication depuis le début et ne répète pas ce qui a déjà été dit : "
        "prends appui sur ton message précédent et poursuis le raisonnement — réponds précisément "
        "au « pourquoi » posé, développe le point qui vient d'être abordé, ou continue l'exercice/"
        "l'explication en cours, sans changer de sujet."
    ),
}

_MODE_INSTRUCTIONS = {
    # Chaque instruction couvre désormais deux aspects distincts : le
    # COMPORTEMENT (que faire) ET le STYLE (comment le dire — ton, longueur
    # de phrase, densité de transitions) — sans cette seconde partie, un
    # même fournisseur IA peut respecter la consigne de fond tout en gardant
    # la même voix générique d'un mode à l'autre (mission Personality Engine :
    # le mode doit être reconnaissable À LA LECTURE, pas seulement au contenu).
    "professeur": (
        "Mode professeur : sois très détaillé et pédagogique, comme un cours particulier. "
        "Ton rassurant, phrases qui relient les idées entre elles, prends le temps d'expliquer "
        "le pourquoi et pas seulement le comment, n'hésite pas à reformuler un même point "
        "différemment si cela aide à la compréhension."
    ),
    "rapide": (
        "Mode rapide : va droit au but, uniquement la réponse et l'essentiel, sans détour. "
        "Phrases courtes, presque aucune transition entre les idées, aucune reformulation, "
        "aucune mise en contexte superflue. Ce mode prime sur toute consigne de méthode "
        "pédagogique en plusieurs étapes ci-dessus : même face à un exercice, n'attends pas de "
        "validation intermédiaire entre chaque étape — propose directement l'aide la plus utile "
        "(indice bref puis solution si besoin), sans multiplier les interruptions."
    ),
    "pas_a_pas": (
        "Mode pas-à-pas : décompose la résolution en étapes numérotées, une seule à la fois. "
        "Beaucoup de transitions explicites entre les étapes (« maintenant que... », « passons "
        "à... », « une fois ceci acquis... ») : chaque étape doit clairement préparer la suivante, "
        "jamais un enchaînement sec."
    ),
    "visuel": "Mode visuel : utilise des schémas ASCII simples quand ils peuvent aider à visualiser.",
    "examen": (
        "Mode examen : ne donne JAMAIS la réponse ni le moindre indice, contente-toi de valider "
        "ou d'invalider ce que propose l'élève. Ton neutre et académique, vocabulaire précis, "
        "aucune familiarité et aucune formule d'encouragement (jamais de \"super !\", \"bravo\", "
        "\"tu vas y arriver\") — une évaluation factuelle, pas un encouragement. Ce mode prime sur "
        "toute instruction ci-dessus qui suggérerait de finir par donner un indice ou la solution "
        "complète (ex: une demande d'exercice) : dans ce mode, cette étape finale n'a jamais lieu."
    ),
}


# Libellés lisibles pour l'élève/le LLM — même vocabulaire d'approche que
# conversation_manager._LLM_APPROACHES (aucune nouvelle catégorie inventée).
_APPROACH_LABELS = {
    "definition": "la définition classique",
    "methode": "la méthode/les étapes",
    "exemple": "un exemple concret",
    "analogie": "une analogie de la vie courante",
    "question_guidee": "une question guidée",
}

# Recommandation textuelle par approche — utilisée uniquement pour NOMMER
# l'action attendue du LLM, jamais pour lui fournir un contenu tout fait
# (le LLM reste seul responsable de la formulation réelle).
_APPROACH_INSTRUCTION = {
    "definition": "Redonne la définition, mais formulée différemment de ce qui a déjà été dit.",
    "methode": "Montre la méthode ou les étapes de résolution, pas seulement la définition.",
    "exemple": "Donne un exemple concret et entièrement résolu, différent de ceux déjà utilisés.",
    "analogie": "Utilise une analogie de la vie courante pour rendre la notion intuitive.",
    "question_guidee": (
        "Ne donne pas immédiatement toute l'explication. Pose UNE question très simple qui amène "
        "l'élève à trouver lui-même la prochaine étape, et attends sa réponse avant de continuer."
    ),
}


def _build_escalation_instruction(incomprehension_count, escalation_level, approaches_used, recommended_approach):
    """Instruction STRUCTURÉE (chantier "escalade pédagogique", 2026-08-22) —
    remplace l'ancienne phrase statique unique ("change réellement
    d'approche") par une instruction dérivée de données réelles : nombre
    d'échecs, approches déjà tentées (nommées explicitement, pas devinées),
    approche recommandée pour ce tour. Reste un texte déterministe assemblé
    par le code, jamais un appel LLM supplémentaire pour le construire."""
    parts = [
        f"L'élève n'a toujours pas compris malgré {incomprehension_count} tentative(s) "
        f"d'explication sur ce sujet (niveau d'escalade {escalation_level}/4)."
    ]
    used_labels = [_APPROACH_LABELS.get(a, a) for a in dict.fromkeys(approaches_used) if a != recommended_approach]
    if used_labels:
        parts.append(
            "Approches déjà utilisées, à ne PAS répéter si une alternative est disponible : "
            + ", ".join(used_labels) + "."
        )
    if recommended_approach:
        parts.append(_APPROACH_INSTRUCTION.get(
            recommended_approach, "Change réellement d'approche par rapport aux tentatives précédentes.",
        ))
    else:
        parts.append("Change réellement d'approche par rapport aux tentatives précédentes.")
    return " ".join(parts)


def build_intent_instruction(intent_result, topic_label=None):
    """`intent_result` : dict renvoyé par intent_service.classify(). Renvoie
    une chaîne vide si rien de spécifique à instruire (intention NONE/UNCLEAR,
    déjà court-circuitées ailleurs).

    `topic_label` (Current Learning Context, voir conversation_manager.py) :
    titre de la notion actuellement discutée dans la conversation. Si
    `intent_result["topic_inherited"]` est vrai (chapitre/notion hérités du
    contexte mémorisé plutôt que d'une mention fraîche du message — voir
    intent_service.classify()) et qu'un sujet est connu, une instruction
    EXPLICITE et non ambiguë est ajoutée pour que le LLM ne devine jamais le
    sujet et ne dévie jamais vers une autre notion, quelle que soit
    l'intention détectée par ailleurs (reformulation, simplification,
    nouvel exemple...)."""
    if not intent_result:
        return ""
    parts = []
    instr = _INTENT_INSTRUCTIONS.get(intent_result.get("intent"))
    if instr:
        parts.append(instr)
    if intent_result.get("topic_inherited") and topic_label:
        parts.append(
            f"Sujet actuel de la conversation : « {topic_label} ». L'élève poursuit sur cette même "
            f"notion (reformulation, simplification, nouvel exemple...). Ne dévie jamais vers une "
            f"autre notion tant qu'il ne change pas explicitement de sujet."
        )
    escalation_level = intent_result.get("escalation_level") or 0
    if escalation_level >= 1:
        parts.append(_build_escalation_instruction(
            intent_result.get("incomprehension_count") or 0, escalation_level,
            intent_result.get("approaches_used") or [], intent_result.get("recommended_approach"),
        ))
    elif intent_result.get("repeated_incomprehension"):
        # Repli de compatibilité : signal encore présent (voir
        # conversation_manager._detect_repeated_incomprehension) mais sans
        # état d'escalade structuré associé (ex: ancien appelant, ou tour où
        # _update_learning_context n'a pas pu résoudre de chapter_id) —
        # conserve l'instruction historique plutôt que de ne rien dire.
        parts.append(
            "ATTENTION : c'est la deuxième fois de suite que l'élève exprime une incompréhension sur "
            "ce sujet. Ne répète surtout pas la même explication sous une forme à peine reformulée : "
            "change réellement d'approche — un exemple concret différent, une analogie de la vie "
            "courante, ou une question guidée qui l'amène à trouver lui-même la prochaine étape. "
            "Découpe en une étape encore plus petite que la précédente si besoin."
        )
    if intent_result.get("simplify"):
        parts.append("Simplifie énormément : élève en difficulté, vocabulaire très basique, petites étapes.")
    if intent_result.get("difficulty") == "hard":
        parts.append("Adapte le niveau de difficulté à la hausse (exercice/exemple plus exigeant).")
    elif intent_result.get("difficulty") == "easy":
        parts.append("Adapte le niveau de difficulté à la baisse (exercice/exemple plus accessible).")
    return " ".join(parts)


def build_mode_instruction(mode):
    return _MODE_INSTRUCTIONS.get(mode, "")
