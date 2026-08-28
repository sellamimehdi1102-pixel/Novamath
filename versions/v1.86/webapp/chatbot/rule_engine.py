"""
Court-circuite l'appel au LLM pour les demandes qui n'en ont pas besoin.
Phase 1 : couverture volontairement minimale (salutations, identité). Le Math
Engine (calcul symbolique) et un Rule Engine plus complet arriveront en
Phase 2 pour viser les >70% de réponses sans LLM demandés dans le cahier des
charges — l'appel est déjà à la bonne place dans conversation_manager.py pour
que cette montée en couverture n'exige aucun changement d'architecture.
"""
import re

GREETING_RE = re.compile(r"^\s*(salut|bonjour|bonsoir|coucou|hello|hey|cc)\s*[!.?]*\s*$", re.IGNORECASE)
IDENTITY_RE = re.compile(r"(qui es[- ]tu|tu es qui|c'est quoi novamath|présente[- ]toi)", re.IGNORECASE)
THANKS_RE = re.compile(r"^\s*(merci|merci beaucoup|ok merci|super merci)\s*[!.]*\s*$", re.IGNORECASE)

IDENTITY_ANSWER = (
    "Je suis l'assistant pédagogique de NovaMath 🙂 Je t'aide à comprendre tes cours et à résoudre tes "
    "exercices de maths, étape par étape — jamais en te donnant juste la réponse finale. "
    "Pose-moi une question sur un chapitre, une notion, ou colle-moi un exercice sur lequel tu bloques !"
)


def try_handle(user_message):
    """Retourne une réponse toute faite si la demande peut être traitée sans
    appel IA, sinon None (le conversation_manager appellera alors le LLM)."""
    text = (user_message or "").strip()
    if GREETING_RE.match(text):
        return "Salut ! Sur quel chapitre ou quel exercice veux-tu travailler aujourd'hui ?"
    if THANKS_RE.match(text):
        return "Avec plaisir ! N'hésite pas si tu as une autre question 🙂"
    if IDENTITY_RE.search(text):
        return IDENTITY_ANSWER
    return None
