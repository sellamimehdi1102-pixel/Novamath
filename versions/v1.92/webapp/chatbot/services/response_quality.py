"""
Analyseur de qualité des réponses — Phase 4, Mission 5.

Outil d'ANALYSE PURE : note une réponse déjà produite (texte + blocs
optionnels d'un `ResponseDraft`), ne génère et ne modifie jamais de texte.
Appelable en isolation (tests, audit ponctuel) ou en aparté depuis le
pipeline (jamais sur le chemin critique — voir conversation_manager.py).

Dimensions notées (documentées, poids sommant à 100) :
    Richesse pédagogique (blocs de contenu distincts)     : 30
    Structure (nombre de blocs, ni vide ni surchargé)      : 20
    Lisibilité (longueur de phrase raisonnable)            : 20
    Cohérence (pas de bloc dupliqué consécutif, non vide)  : 15
    Variété (blocs distincts / total, anti-répétition)     : 15
"""
import re

CONTENT_BLOCK_KINDS = (
    "definition", "methode", "exemple", "exemple_2", "propriete", "formule",
    "erreur_frequente", "astuce", "rappel", "conseil", "resume",
)

WEIGHT_RICHESSE = 30
WEIGHT_STRUCTURE = 20
WEIGHT_LISIBILITE = 20
WEIGHT_COHERENCE = 15
WEIGHT_VARIETE = 15

_SENTENCE_SPLIT_RE = re.compile(r"[.!?]+\s+")
_WORD_RE = re.compile(r"\S+")

# Longueur de phrase cible (mots/phrase) — au-delà, la lisibilité baisse.
TARGET_SENTENCE_LENGTH = 18


def _sentences(text):
    return [s for s in _SENTENCE_SPLIT_RE.split(text or "") if s.strip()]


def _score_richesse(block_kinds):
    content_present = {k for k in block_kinds if k in CONTENT_BLOCK_KINDS}
    ratio = len(content_present) / len(CONTENT_BLOCK_KINDS)
    return round(min(ratio * 2, 1.0) * WEIGHT_RICHESSE, 1)  # 5 blocs de contenu distincts = score plein


def _score_structure(block_kinds):
    n = len(block_kinds)
    if n == 0:
        return 0.0
    if 2 <= n <= 7:
        return float(WEIGHT_STRUCTURE)
    if n == 1:
        return WEIGHT_STRUCTURE * 0.5
    return WEIGHT_STRUCTURE * 0.7  # trop long, mais pas disqualifiant


def _score_lisibilite(text):
    sentences = _sentences(text)
    if not sentences:
        return 0.0
    lengths = [len(_WORD_RE.findall(s)) for s in sentences]
    avg = sum(lengths) / len(lengths)
    excess = max(0, avg - TARGET_SENTENCE_LENGTH)
    penalty = min(excess / TARGET_SENTENCE_LENGTH, 1.0)
    return round(WEIGHT_LISIBILITE * (1 - penalty), 1)


def _score_coherence(block_kinds):
    if not block_kinds:
        return 0.0
    duplicates_consecutifs = sum(1 for a, b in zip(block_kinds, block_kinds[1:]) if a == b)
    penalty = min(duplicates_consecutifs * 0.3, 1.0)
    return round(WEIGHT_COHERENCE * (1 - penalty), 1)


def _score_variete(block_kinds):
    if not block_kinds:
        return 0.0
    ratio = len(set(block_kinds)) / len(block_kinds)
    return round(WEIGHT_VARIETE * ratio, 1)


def score_response(text, block_kinds=None):
    """Note une réponse (texte final + kinds de blocs si disponibles, ex.
    `[b.kind for b in draft.blocks]`). Sans `block_kinds`, la richesse/
    structure/cohérence/variété sont estimées à 0 (seule la lisibilité reste
    mesurable sur un texte brut) — toujours honnête, jamais une note
    inventée."""
    block_kinds = block_kinds or []
    scores = {
        "richesse_pedagogique": _score_richesse(block_kinds),
        "structure": _score_structure(block_kinds),
        "lisibilite": _score_lisibilite(text),
        "coherence": _score_coherence(block_kinds),
        "variete": _score_variete(block_kinds),
    }
    total = round(sum(scores.values()), 1)
    return {
        "score_global": total,
        **scores,
        "blocs_presents": sorted(set(block_kinds) & set(CONTENT_BLOCK_KINDS)),
        "blocs_pedagogiques_manquants": sorted(set(CONTENT_BLOCK_KINDS) - set(block_kinds)),
    }


def score_draft(draft):
    """Raccourci pour un `ResponseDraft` (knowledge_response_composer.py) —
    évite à l'appelant d'extraire `[b.kind for b in draft.blocks]` lui-même."""
    return score_response(draft.text, [b.kind for b in draft.blocks])
