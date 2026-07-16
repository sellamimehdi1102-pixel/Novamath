"""
Classification d'intention pédagogique — appelée AVANT tout appel LLM
(conversation_manager.py) pour détecter ce que demande l'élève (exercice /
exemple / explication / quiz / fiche / correction / reprise des bases) par
mots-clés et regex (pas de ML), et repérer le chapitre/la notion visée par
recherche floue déjà éprouvée (search_service — aucune logique de
correspondance dupliquée ici). Sert à piloter la sélection d'exercices scopée
par chapitre (search_service.search_exercises_in_chapter) et les
préréponses pédagogiques (pedagogy_templates.py).

Détecte aussi les demandes incompréhensibles ("aaaa", "......") pour
court-circuiter le LLM avec une réponse de clarification fixe plutôt que de
laisser le fournisseur IA halluciner une réponse hors-sujet.
"""
import re

from . import search_service

EXERCICE = "exercice"
EXEMPLE = "exemple"
EXPLICATION = "explication"
QUIZ = "quiz"
FICHE = "fiche"
CORRECTION = "correction"
RESTART_BASICS = "restart_basics"
NONE_INTENT = "none"
UNCLEAR = "unclear"

CLARIFICATION_MESSAGE = (
    "Je n'ai pas bien compris votre demande.\n\n"
    "Pouvez-vous reformuler votre question ?\n\n"
    "Vous pouvez par exemple me demander :\n"
    "- expliquer une notion ;\n"
    "- proposer un exercice ;\n"
    "- corriger un exercice ;\n"
    "- créer une série d'entraînement."
)

_GIBBERISH_PUNCT_RE = re.compile(r"^[^a-zàâäéèêëïîôöùûüç0-9]+$", re.IGNORECASE)
_REPEATED_CHAR_RE = re.compile(r"^(.)\1{3,}$")
_VOWEL_RE = re.compile(r"[aeiouyàâäéèêëïîôöùûü]", re.IGNORECASE)
_LETTERS_RE = re.compile(r"[^a-zàâäéèêëïîôöùûüç]", re.IGNORECASE)

RESTART_RE = re.compile(
    r"(j'ai rien compris|je n'ai rien compris|j'y comprends rien|je ne comprends rien|"
    r"reprend(?:re|s)?.{0,15}(d[ée]but|base)|repartir.{0,10}(z[ée]ro|base))",
    re.IGNORECASE,
)
QUIZ_RE = re.compile(
    r"(interroge[- ]moi|pose[- ]moi des questions|fais[- ]moi (un )?quiz|teste[- ]moi|questionne[- ]moi)",
    re.IGNORECASE,
)
CORRECTION_RE = re.compile(
    r"(corrige (mon|cet|ce)|correction de|est[- ]ce que c'est juste|v[ée]rifie ma r[ée]ponse)",
    re.IGNORECASE,
)
FICHE_RE = re.compile(
    r"(fais[- ]moi (une )?fiche|fiche de synth[eè]se|fiche r[ée]cap|r[ée]sume[- ]moi)",
    re.IGNORECASE,
)
EXERCICE_RE = re.compile(
    r"(donne(?:-moi)? un exercice|un exercice (?:\w+\s+){0,3}sur|propose[- ]moi (?:un )?exercice|"
    r"entra[iî]ne[- ]moi|exercice d'entra[iî]nement)",
    re.IGNORECASE,
)
EXEMPLE_RE = re.compile(
    r"(donne(?:-moi)? un exemple|un exemple (?:\w+\s+){0,3}sur|montre[- ]moi un exemple)",
    re.IGNORECASE,
)
EXPLICATION_RE = re.compile(r"(explique[- ]moi|^explique\b|comment (fonctionne|marche))", re.IGNORECASE)

SIMPLIFY_RE = re.compile(
    r"(comme [aà] un [ée]l[eè]ve en difficult[ée]|explique(?:-moi)? simplement|plus simplement|vulgarise)",
    re.IGNORECASE,
)
DIFFICULT_RE = re.compile(r"\b(difficile|dur|cors[ée]|compliqu[ée])\b", re.IGNORECASE)
EASY_RE = re.compile(r"\b(facile|simple|basique)\b", re.IGNORECASE)

# Ordre de priorité : le premier motif qui correspond l'emporte (une demande
# de reprise des bases prime sur une simple demande d'explication, etc.)
_INTENT_PATTERNS = [
    (RESTART_BASICS, RESTART_RE),
    (QUIZ, QUIZ_RE),
    (CORRECTION, CORRECTION_RE),
    (FICHE, FICHE_RE),
    (EXERCICE, EXERCICE_RE),
    (EXEMPLE, EXEMPLE_RE),
    (EXPLICATION, EXPLICATION_RE),
]


def _is_gibberish(text):
    t = text.strip()
    if len(t) < 2:
        return True
    if _GIBBERISH_PUNCT_RE.match(t):
        return True
    if _REPEATED_CHAR_RE.match(t.lower()):
        return True
    letters = _LETTERS_RE.sub("", t.lower())
    if len(letters) >= 4 and not _VOWEL_RE.search(letters):
        return True
    return False


def _detect_difficulty(text):
    if DIFFICULT_RE.search(text):
        return "hard"
    if EASY_RE.search(text):
        return "easy"
    return None


def _detect_chapter(text, context_summary):
    """Chapitre/notion visé par la demande — réutilise la recherche déjà
    éprouvée de search_service (TF-IDF + repli flou), jamais de logique de
    correspondance dupliquée ici. Repli sur le chapitre en cours de l'élève
    si rien n'est trouvé dans le texte, plutôt que de deviner au hasard."""
    matches = search_service.search(text, scope=[search_service.SCOPE_COURS], limit=1)
    if matches and matches[0]["score"] >= search_service.TFIDF_WEAK_THRESHOLD:
        return matches[0]["chapter_id"], matches[0]["notion_id"]
    if context_summary and context_summary.get("chapters_in_progress"):
        return context_summary["chapters_in_progress"][0], None
    return None, None


def classify(user_message, context_summary=None):
    """Retourne {intent, chapter_id, notion_id, difficulty, simplify}.
    `intent` vaut NONE_INTENT si aucun mot-clé pédagogique n'est reconnu (la
    question reste ouverte, traitée normalement par le LLM) — à ne pas
    confondre avec UNCLEAR (demande incompréhensible, court-circuitée avant
    tout appel IA)."""
    text = (user_message or "").strip()
    if _is_gibberish(text):
        return {"intent": UNCLEAR, "chapter_id": None, "notion_id": None, "difficulty": None, "simplify": False}

    intent = NONE_INTENT
    matched = None
    for key, pattern in _INTENT_PATTERNS:
        m = pattern.search(text)
        if m:
            intent = key
            matched = m
            break

    # Cherche le chapitre seulement sur ce qui reste une fois la formule
    # déclencheuse retirée ("donne-moi un exercice" -> "") : sinon une
    # requête sans sujet réel se fait attribuer un chapitre au hasard par le
    # repli flou (comparaison de lettres sur des mots génériques).
    topic_text = text
    if matched:
        topic_text = (text[:matched.start()] + " " + text[matched.end():]).strip()

    chapter_id, notion_id = _detect_chapter(topic_text, context_summary)
    return {
        "intent": intent,
        "chapter_id": chapter_id,
        "notion_id": notion_id,
        "difficulty": _detect_difficulty(text),
        "simplify": bool(SIMPLIFY_RE.search(text)),
    }
