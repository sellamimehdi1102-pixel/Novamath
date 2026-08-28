"""
Mémoire de style partagée : évite qu'un moteur de composition locale ne
répète mot pour mot une formulation déjà utilisée dans les réponses
assistant récentes de LA MÊME conversation. Ne relit jamais la base, ne
touche à aucune décision stratégique — un pur outil de variété rédactionnelle.

── Un seul point d'entrée, sans exception (Phase Personality Engine) ────────
`pick_rendered` est OBLIGATOIRE pour tout pool de formulations, qu'il
contienne des placeholders ou non : RENDER d'abord (chaque variante
substituée via `str.format_map`), PICK ensuite parmi les textes réellement
affichés à l'élève — jamais l'inverse. Comparer un template encore truffé de
`{variable}` à un historique déjà rendu ne peut jamais matcher : c'est le
blind spot identifié à l'audit (pool `_LEADIN_DEFINITION`, seul à contenir
`{title}`, dont la mémoire anti-répétition était de fait inopérante). Pour un
pool sans placeholder, `mapping=None` laisse chaque variante inchangée :
le même mécanisme s'applique donc uniformément à tous les pools.
"""


def recent_assistant_text(student_context):
    """Concatène les réponses assistant récentes exposées par le Student
    Context Resolver v2 (`historique_conversation`) en un seul texte — sert
    uniquement de "mémoire" anti-répétition, jamais pour autre chose."""
    history = (student_context or {}).get("historique_conversation") or []
    return " \n".join(h.get("content", "") for h in history if h.get("role") == "assistant")


def pick_rendered(rng, variants, avoid_blob, mapping=None):
    """Rend CHAQUE variante avec `mapping` (un dict, ou un `_SafeDict`-like
    tolérant les clés manquantes — au choix de l'appelant) puis choisit un
    texte non présent (mot pour mot) dans `avoid_blob` parmi les résultats.
    Repli sur l'ensemble complet si toutes ont déjà été utilisées (mieux
    vaut répéter occasionnellement que ne pas répondre).

    `mapping=None` (défaut) : aucune substitution, chaque variante ressort
    telle quelle — cas normal pour un pool sans placeholder, qui évite alors
    tout appel `format_map` inutile (la majorité des pools, voir docstring
    module)."""
    rendered = variants if mapping is None else [v.format_map(mapping) for v in variants]
    candidates = [v for v in rendered if v not in avoid_blob] or rendered
    return rng.choice(candidates)
