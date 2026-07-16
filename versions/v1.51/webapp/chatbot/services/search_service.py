"""
Recherche unifiée sur le contenu réel de NovaMath (cours + exercices) — pour
GET /api/search, la palette @ du chatbot (mentions_service.py) et la Command
Palette Ctrl+K. Aucune donnée fictive : les cours viennent de
knowledge_engine.py (déjà un index TF-IDF sur webapp/static/data/cours/
chapitre_*.json), les exercices sont indexés ici à partir de la même
exercises_bank.json que /api/chapters et /api/exercise/<id> (webapp/server.py)
— chargée une seule fois en mémoire, jamais dupliquée en écriture.

En complément du TF-IDF (qui exige un chevauchement de mots), un repli flou
(difflib, stdlib) tolère les fautes de frappe/variantes ("valeur absolu" ->
"Valeurs absolues") en comparant directement aux titres réels du corpus.
"""
import difflib
import json
from pathlib import Path

from .. import knowledge_engine, retrieval_engine

ROOT = Path(__file__).resolve().parent.parent.parent.parent
BANK_PATH = ROOT / "exercises_bank.json"

SCOPE_COURS = "cours"
SCOPE_EXERCICES = "exercices"
VALID_SCOPES = {SCOPE_COURS, SCOPE_EXERCICES}

# Repli flou (fautes de frappe) présenté comme un résultat normal : cutoff
# volontairement strict (0.62) — en dessous, difflib produit trop de faux
# positifs sur des mots courts sans rapport ("thales" ~ "intervalles" à 0.59
# par pur hasard de lettres communes). Le "Voulez-vous dire ?" (mentions_service)
# utilise un cutoff plus bas car il est explicitement présenté comme incertain.
FUZZY_CUTOFF = 0.62
DID_YOU_MEAN_CUTOFF = 0.4
TFIDF_WEAK_THRESHOLD = 0.12

_exercise_index = None  # retrieval_engine.Index — construit une seule fois
_exercise_by_id = None  # dict {exercise_id: document} — lookup exact


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


def _get_exercise_by_id():
    global _exercise_by_id
    if _exercise_by_id is None:
        _exercise_by_id = {d["exercise_id"]: d for d in _load_exercise_documents()}
    return _exercise_by_id


def _cours_result(m, score=None):
    return {
        "type": SCOPE_COURS,
        "chapter_id": m["chapter_id"],
        "notion_id": m["notion_id"],
        "title": m["title"],
        "snippet": m["definition"],
        "score": score if score is not None else m["score"],
        "url": f"cours.html?chapter={m['chapter_id']}&notion={m['notion_id']}",
    }


def _exercice_result(m, score=None):
    return {
        "type": SCOPE_EXERCICES,
        "chapter_id": m["chapter_id"],
        "notion": m["notion"],
        "exercise_id": m["exercise_id"],
        "title": m["notion"] or "Exercice",
        "snippet": m["snippet"],
        "score": score if score is not None else m["score"],
        # Pas de lien direct : exercice.html attend une série posée dans
        # localStorage ("lumis:pending_series", cf. chapitres.js) — c'est
        # au consommateur (frontend) de construire ce payload à partir de
        # chapter_id/notion/exercise_id, une URL brute serait incorrecte.
        "url": None,
    }


def _search_cours(query, limit):
    return [_cours_result(m) for m in knowledge_engine.search(query, top_k=limit, min_score=0.08)]


def _search_exercices(query, limit):
    matches = retrieval_engine.search(_get_exercise_index(), query, top_k=limit, min_score=0.08)
    return [_exercice_result(m) for m in matches]


def _dedupe_key(r):
    return (r["type"], r.get("chapter_id"), r.get("notion_id") or r.get("exercise_id"))


def _fuzzy_fallback(query, scopes, limit, exclude_keys, cutoff=FUZZY_CUTOFF):
    """Repli tolérant aux fautes de frappe : compare `query` directement aux
    titres réels (notions de cours + notions d'exercice), sans exiger de mot
    commun exact comme le fait le TF-IDF. Utilisé quand la recherche normale
    est vide ou trop faible."""
    candidates = []  # (title, kind, document)
    if SCOPE_COURS in scopes:
        candidates.extend((d["title"], "cours", d) for d in knowledge_engine.all_documents())
    if SCOPE_EXERCICES in scopes:
        candidates.extend((d["notion"], "exercices", d) for d in _get_exercise_documents_cached())

    titles = [c[0] for c in candidates if c[0]]
    close = difflib.get_close_matches(query, titles, n=limit * 2, cutoff=cutoff)
    results = []
    seen_titles = set()
    for title in close:
        if title in seen_titles:
            continue
        seen_titles.add(title)
        for t, kind, doc in candidates:
            if t != title:
                continue
            ratio = difflib.SequenceMatcher(a=query.lower(), b=title.lower()).ratio()
            result = _cours_result(doc, score=ratio) if kind == "cours" else _exercice_result(doc, score=ratio)
            key = _dedupe_key(result)
            if key in exclude_keys:
                continue
            results.append(result)
            break
    results.sort(key=lambda r: r["score"], reverse=True)
    return results[:limit]


def _get_exercise_documents_cached():
    # Réutilise le même chargement que l'index TF-IDF (une seule lecture disque).
    return _get_exercise_index().documents


def search(query, scope=None, limit=10):
    """`scope` : None (tout) ou itérable parmi VALID_SCOPES. Renvoie une liste
    triée par score décroissant, tronquée à `limit` au total. Bascule sur un
    repli flou (fautes de frappe) si la recherche exacte est vide ou faible."""
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

    if not results or results[0]["score"] < TFIDF_WEAK_THRESHOLD:
        seen = {_dedupe_key(r) for r in results}
        fuzzy = _fuzzy_fallback(query, scopes, limit, seen)
        results = (results + fuzzy)
        results.sort(key=lambda r: r["score"], reverse=True)

    return results[:limit]


def best_guess(query, scope=None):
    """Un seul candidat, même faible (utilisé pour le "Voulez-vous dire : X ?"
    des mentions "@" quand rien de solide n'a été trouvé). None si vraiment
    rien ne s'en approche."""
    query = (query or "").strip()
    if not query:
        return None
    scopes = VALID_SCOPES if not scope else (set(scope) & VALID_SCOPES)
    fuzzy = _fuzzy_fallback(query, scopes, 1, set(), cutoff=DID_YOU_MEAN_CUTOFF)
    return fuzzy[0] if fuzzy else None


def resolve(kind, chapter_id=None, notion_id=None, exercise_id=None):
    """Résolution exacte (pas une recherche) d'une ressource déjà identifiée
    par ses ids — utilisée par mentions_service.py pour injecter la vraie
    donnée dans le prompt système, jamais laisser le LLM deviner."""
    if kind == SCOPE_COURS and chapter_id and notion_id:
        doc = knowledge_engine.get_notion(chapter_id, notion_id)
        return _cours_result(doc, score=1.0) if doc else None
    if kind == SCOPE_EXERCICES and exercise_id is not None:
        doc = _get_exercise_by_id().get(exercise_id)
        return _exercice_result(doc, score=1.0) if doc else None
    return None
