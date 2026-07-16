"""
Recherche unifiée sur le contenu réel de NovaMath (cours + exercices) — pour
GET /api/search, et demain la palette @ du chatbot et la Command Palette
Ctrl+K. Aucune donnée fictive : les cours viennent de knowledge_engine.py
(déjà un index TF-IDF sur webapp/static/data/cours/chapitre_*.json), les
exercices sont indexés ici à partir de la même exercises_bank.json que
/api/chapters et /api/exercise/<id> (webapp/server.py) — chargée une seule
fois en mémoire, jamais dupliquée en écriture.
"""
import json
from pathlib import Path

from .. import knowledge_engine, retrieval_engine

ROOT = Path(__file__).resolve().parent.parent.parent.parent
BANK_PATH = ROOT / "exercises_bank.json"

SCOPE_COURS = "cours"
SCOPE_EXERCICES = "exercices"
VALID_SCOPES = {SCOPE_COURS, SCOPE_EXERCICES}

_exercise_index = None  # retrieval_engine.Index — construit une seule fois


def _load_exercise_documents():
    if not BANK_PATH.exists():
        return []
    with open(BANK_PATH, "r", encoding="utf-8") as f:
        raw_bank = json.load(f)
    documents = []
    for i, ex in enumerate(raw_bank):
        exercise_id = ex.get("id") if ex.get("id") is not None else i
        notion = ex.get("notion", "") or ""
        enonce = ex.get("enonce", "") or ""
        documents.append({
            "exercise_id": exercise_id,
            "chapter_id": ex.get("chapter_id", ""),
            "notion": notion,
            "difficulty": ex.get("difficulty"),
            "text": f"{notion} {enonce}",
            "snippet": enonce,
        })
    return documents


def _get_exercise_index():
    global _exercise_index
    if _exercise_index is None:
        _exercise_index = retrieval_engine.build_index(_load_exercise_documents())
    return _exercise_index


def _search_cours(query, limit):
    results = []
    for m in knowledge_engine.search(query, top_k=limit, min_score=0.08):
        results.append({
            "type": SCOPE_COURS,
            "chapter_id": m["chapter_id"],
            "notion_id": m["notion_id"],
            "title": m["title"],
            "snippet": m["definition"],
            "score": m["score"],
            "url": f"cours.html?chapter={m['chapter_id']}&notion={m['notion_id']}",
        })
    return results


def _search_exercices(query, limit):
    matches = retrieval_engine.search(_get_exercise_index(), query, top_k=limit, min_score=0.08)
    results = []
    for m in matches:
        results.append({
            "type": SCOPE_EXERCICES,
            "chapter_id": m["chapter_id"],
            "notion": m["notion"],
            "exercise_id": m["exercise_id"],
            "title": m["notion"] or "Exercice",
            "snippet": m["snippet"],
            "score": m["score"],
            # Pas de lien direct : exercice.html attend une série posée dans
            # localStorage ("lumis:pending_series", cf. chapitres.js) — c'est
            # au consommateur (frontend) de construire ce payload à partir de
            # chapter_id/notion/exercise_id, une URL brute serait incorrecte.
            "url": None,
        })
    return results


def search(query, scope=None, limit=10):
    """`scope` : None (tout) ou itérable parmi VALID_SCOPES. Renvoie une liste
    triée par score décroissant, tronquée à `limit` au total."""
    query = (query or "").strip()
    if not query:
        return []
    scopes = VALID_SCOPES if not scope else (set(scope) & VALID_SCOPES)
    if not scopes:
        return []

    results = []
    if SCOPE_COURS in scopes:
        results.extend(_search_cours(query, limit))
    if SCOPE_EXERCICES in scopes:
        results.extend(_search_exercices(query, limit))

    results.sort(key=lambda r: r["score"], reverse=True)
    return results[:limit]
