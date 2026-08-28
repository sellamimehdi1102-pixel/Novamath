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
        "aucune mise en contexte superflue."
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
        "\"tu vas y arriver\") — une évaluation factuelle, pas un encouragement."
    ),
}


def build_intent_instruction(intent_result):
    """`intent_result` : dict renvoyé par intent_service.classify(). Renvoie
    une chaîne vide si rien de spécifique à instruire (intention NONE/UNCLEAR,
    déjà court-circuitées ailleurs)."""
    if not intent_result:
        return ""
    parts = []
    instr = _INTENT_INSTRUCTIONS.get(intent_result.get("intent"))
    if instr:
        parts.append(instr)
    if intent_result.get("simplify"):
        parts.append("Simplifie énormément : élève en difficulté, vocabulaire très basique, petites étapes.")
    if intent_result.get("difficulty") == "hard":
        parts.append("Adapte le niveau de difficulté à la hausse (exercice/exemple plus exigeant).")
    elif intent_result.get("difficulty") == "easy":
        parts.append("Adapte le niveau de difficulté à la baisse (exercice/exemple plus accessible).")
    return " ".join(parts)


def build_mode_instruction(mode):
    return _MODE_INSTRUCTIONS.get(mode, "")
