"""
Sait où aller chercher les connaissances pédagogiques NovaMath — ne contient
aucune donnée lui-même. Source unique : les cours déjà écrits
(webapp/static/data/cours/*.json — définitions, règles importantes, méthodes,
erreurs fréquentes, points à retenir), lus directement, jamais dupliqués. Ce
module construit les "documents" à indexer et délègue la recherche elle-même
à retrieval_engine.py (générique, sans connaissance métier).

Deux usages :
1. Question factuelle claire ("c'est quoi...", "définition de...") avec une
   correspondance forte sur une seule notion -> réponse instantanée directe,
   sans appel au fournisseur IA (voir conversation_manager.py, entre le Math
   Engine et le Provider Manager).
2. Sinon -> les meilleures notions retrouvées sont injectées comme contexte
   compact dans le prompt système (prompt_builder.py), pour que le
   fournisseur actif (FakeProvider ou un futur LLM) s'appuie sur le cours
   réel plutôt que d'inventer, tout en limitant le volume envoyé.
"""
import json
import re
from pathlib import Path

from . import retrieval_engine

COURS_DIR = Path(__file__).resolve().parent.parent / "static" / "data" / "cours"

DEFINITION_RE = re.compile(
    r"\b(c'est quoi|qu'est[- ]ce que|définition de|défini[st]|que veut dire|"
    r"rappelle[- ]moi|propriété de|règle de|théorème de|formule de)\b",
    re.IGNORECASE,
)

_index = None  # retrieval_engine.Index — construit une seule fois, en mémoire


def _load_notions():
    """Construit les documents à indexer à partir des cours NovaMath existants
    (source unique de vérité) — aucune copie persistée nulle part."""
    notions = []
    if not COURS_DIR.exists():
        return notions
    for path in sorted(COURS_DIR.glob("chapitre_*.json")):
        try:
            with open(path, "r", encoding="utf-8") as f:
                chapter = json.load(f)
        except (json.JSONDecodeError, OSError):
            continue
        for notion in chapter.get("notions", []):
            text_parts = [
                notion.get("title", ""),
                notion.get("definition", ""),
                " ".join(notion.get("reglesImportantes", []) or []),
                " ".join(notion.get("aRetenir", []) or []),
                notion.get("astuce", "") or "",
            ]
            notions.append({
                "chapter_id": chapter.get("chapterId", ""),
                "chapter_title": chapter.get("title", ""),
                "notion_id": notion.get("id", ""),
                "title": notion.get("title", ""),
                "definition": notion.get("definition", ""),
                "regles": notion.get("reglesImportantes", []) or [],
                "a_retenir": notion.get("aRetenir", []) or [],
                "erreurs": notion.get("erreursFrequentes", []) or [],
                "text": " ".join(p for p in text_parts if p),
            })
    return notions


def _get_index():
    global _index
    if _index is None:
        _index = retrieval_engine.build_index(_load_notions())
    return _index


def search(query, top_k=3, min_score=0.12):
    return retrieval_engine.search(_get_index(), query, top_k=top_k, min_score=min_score)


def try_answer_definition(user_message):
    """Réponse directe (sans IA) si la question est clairement une demande
    de définition/rappel ET qu'une notion correspond nettement mieux que les
    autres. Sinon None (le pipeline continue vers le contexte + le fournisseur actif)."""
    text = (user_message or "").strip()
    if not text or not DEFINITION_RE.search(text):
        return None
    # min_score=0 ici : on a besoin du DEUXIÈME résultat même faible pour
    # juger de l'ambiguïté (un filtrage précoce le ferait disparaître et
    # romprait la comparaison d'écart ci-dessous).
    matches = search(text, top_k=2, min_score=0.0)
    if not matches or matches[0]["score"] < 0.22:
        return None
    if len(matches) >= 2 and matches[0]["score"] - matches[1]["score"] < 0.12:
        return None  # ambigu entre deux notions -> laisser le contexte départager
    best = matches[0]
    lines = [f"**{best['title']}** *({best['chapter_title']})*", "", best["definition"]]
    if best["regles"]:
        lines.append("")
        lines.append("**Règles importantes :**")
        lines.extend(f"- {r}" for r in best["regles"])
    if best["a_retenir"]:
        lines.append("")
        lines.append("**À retenir :**")
        lines.extend(f"- {r}" for r in best["a_retenir"])
    return "\n".join(lines)


def context_block(user_message, top_k=3):
    """Bloc de contexte compact (RAG) : quelques notions pertinentes, jamais
    le cours entier. Chaîne vide si rien de pertinent n'est trouvé."""
    matches = search(user_message, top_k=top_k)
    if not matches:
        return ""
    blocks = []
    for m in matches:
        block = [f"### {m['title']} ({m['chapter_title']})", m["definition"]]
        if m["regles"]:
            block.append("Règles : " + " ; ".join(m["regles"]))
        if m["erreurs"]:
            block.append("Erreurs fréquentes : " + " ; ".join(m["erreurs"]))
        blocks.append("\n".join(block))
    return "\n\n".join(blocks)
