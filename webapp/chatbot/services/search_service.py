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
import random
from pathlib import Path

import canonical_ids
import curriculum_registry

from .. import knowledge_engine, retrieval_engine

ROOT = Path(__file__).resolve().parent.parent.parent.parent
_DEFAULT_CLASS_LEVEL = "seconde"


def _resolve_class_level(class_level):
    return class_level or _DEFAULT_CLASS_LEVEL


def _bank_path_for(class_level):
    profile = curriculum_registry.CURRICULUM_REGISTRY[_resolve_class_level(class_level)]
    return profile.exercise_bank


# Alias rétrocompatible : pointe vers exactement le même fichier qu'avant
# (exercise_bank de "seconde"), aucune valeur différente.
BANK_PATH = _bank_path_for(None)

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
# Seuil "fort" (chantier continuité conversationnelle, 2026-08-22) : distingue
# un sujet FRANCHEMENT identifié (assez net pour l'emporter sur un Current
# Learning Context déjà établi, voir intent_service._detect_chapter) d'une
# simple correspondance faible qui ne doit servir qu'en dernier recours (pas
# de sujet mémorisé du tout). Calibré empiriquement : une requête portant un
# vrai mot-clé de notion ("équation cartésienne", "puissances d'un nombre
# relatif") score entre 0.45 et 0.55 sur le corpus réel, largement au-dessus ;
# une collision fortuite (mots génériques partagés entre deux chapitres)
# dépasse rarement 0.15-0.18. Volontairement distinct du seuil déjà utilisé
# par knowledge_engine.try_answer_definition (0.22, contexte différent : une
# réponse directe sans aucun contexte conversationnel à préserver).
TFIDF_STRONG_THRESHOLD = 0.20

_exercise_index_by_class = {}  # {class_level: retrieval_engine.Index} — construit une seule fois par classe
_exercise_by_id_by_class = {}  # {class_level: {exercise_id: document}} — lookup exact
_exercise_index_by_chapter_by_class = {}  # {class_level: {chapter_id: retrieval_engine.Index}} — à la demande


def _load_exercise_documents(class_level=None):
    bank_path = _bank_path_for(class_level)
    raw_bank = []
    if bank_path is not None and bank_path.exists():
        with open(bank_path, "r", encoding="utf-8") as f:
            raw_bank = json.load(f)

    # Pool additif produit par un moteur symbolique (voir
    # webapp/exercise_generator/) — même fichier que celui fusionné dans
    # server.py::_class_bank(). Sans cette fusion, le chatbot ("donne-moi un
    # exercice sur les dérivées") ne pouvait jamais proposer un exercice
    # généré, même si le mode Exercices du site les propose déjà : deux
    # sources de vérité auraient divergé silencieusement (Phase 4 —
    # cohérence exercices/cours/chatbot).
    profile = curriculum_registry.CURRICULUM_REGISTRY[_resolve_class_level(class_level)]
    if profile.generated_exercise_bank is not None and profile.generated_exercise_bank.exists():
        with open(profile.generated_exercise_bank, "r", encoding="utf-8") as f:
            raw_bank = raw_bank + json.load(f)

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


def _get_exercise_index(class_level=None):
    key = _resolve_class_level(class_level)
    if key not in _exercise_index_by_class:
        _exercise_index_by_class[key] = retrieval_engine.build_index(_load_exercise_documents(key))
    return _exercise_index_by_class[key]


def _get_exercise_by_id(class_level=None):
    key = _resolve_class_level(class_level)
    if key not in _exercise_by_id_by_class:
        _exercise_by_id_by_class[key] = {d["exercise_id"]: d for d in _load_exercise_documents(key)}
    return _exercise_by_id_by_class[key]


def _get_exercise_index_for_chapter(chapter_id, class_level=None):
    key = _resolve_class_level(class_level)
    by_chapter = _exercise_index_by_chapter_by_class.setdefault(key, {})
    if chapter_id not in by_chapter:
        docs = [d for d in _load_exercise_documents(key) if d["chapter_id"] == chapter_id]
        by_chapter[chapter_id] = retrieval_engine.build_index(docs)
    return by_chapter[chapter_id]


def search_exercises_in_chapter(chapter_id, query=None, difficulty=None, limit=5, class_level=None):
    """Recherche d'exercices STRICTEMENT limitée à `chapter_id` — jamais de
    repli vers un autre chapitre, contrairement à `search()` (TF-IDF/flou sur
    toute la banque). Utilisée quand l'intention de l'élève cible un chapitre
    précis (intent_service.classify) : "donne-moi un exercice sur les
    valeurs absolues" ne doit jamais renvoyer un exercice d'un autre
    chapitre par simple proximité de vocabulaire. Renvoie [] si aucun
    exercice n'existe pour ce chapitre — à l'appelant de le dire
    explicitement plutôt que de changer de chapitre en silence."""
    if not chapter_id:
        return []
    chapter_docs = [d for d in _load_exercise_documents(class_level) if d["chapter_id"] == chapter_id]
    if difficulty:
        # Incohérence de vocabulaire corrigée (audit de généralisation KE v2) :
        # `difficulty` vient d'intent_service ("easy"/"hard"), `d["difficulty"]`
        # vient d'exercises_bank.json (entier 1-5) — une comparaison directe
        # ne matchait jamais (bug silencieux préexistant, jamais corrigé avant
        # cet audit). knowledge_engine expose les tables de correspondance
        # unifiées (DIFFICULTE_LEVELS/INTENT_DIFFICULTY_TO_LABEL/
        # EXERCISES_BANK_SCALE_TO_LABEL) introduites avec canonical_ids.
        target_label = knowledge_engine.INTENT_DIFFICULTY_TO_LABEL.get(difficulty, difficulty)
        narrowed = [
            d for d in chapter_docs
            if knowledge_engine.EXERCISES_BANK_SCALE_TO_LABEL.get(d.get("difficulty")) == target_label
        ]
        if narrowed:
            chapter_docs = narrowed
    if not chapter_docs:
        return []

    query = (query or "").strip()
    if query:
        index = _get_exercise_index_for_chapter(chapter_id, class_level=class_level)
        matches = retrieval_engine.search(index, query, top_k=limit, min_score=0.05)
        if matches:
            return [_exercice_result(m, class_level=class_level) for m in matches]

    # Pas de sujet précis (ou aucune correspondance dans le chapitre) :
    # sélection aléatoire, mais toujours à l'intérieur du même chapitre.
    # score=1.0 : ces documents bruts (_load_exercise_documents) n'ont pas de
    # champ "score" (contrairement aux résultats de retrieval_engine.search) —
    # bug préexistant (KeyError), découvert par la suite de tests fonctionnelle.
    picked = random.sample(chapter_docs, min(limit, len(chapter_docs)))
    return [_exercice_result(d, score=1.0, class_level=class_level) for d in picked]


def exercises_by_topic(chapter_id, topic_id, limit=5, class_level=None):
    """Exercices d'un topic_id EXACT (canonical_ids.py) — à utiliser dès que
    le topic_id est déjà connu (ex. context_builder.py::weak_topics), pour
    remplacer la recherche floue par texte libre qui restait jusqu'ici le
    seul pont entre l'historique de l'élève (texte libre) et la banque
    d'exercices. [] si le chapitre/topic n'a aucun exercice."""
    if not chapter_id or not topic_id:
        return []
    docs = [d for d in _load_exercise_documents(class_level) if d["chapter_id"] == chapter_id]
    matching = [
        d for d in docs
        if canonical_ids.resolve_topic_id(d["notion"], chapter_id=chapter_id, class_level=class_level) == topic_id
    ]
    return [_exercice_result(d, score=1.0, class_level=class_level) for d in matching[:limit]]


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


def _exercice_result(m, score=None, class_level=None):
    return {
        "type": SCOPE_EXERCICES,
        "chapter_id": m["chapter_id"],
        "notion": m["notion"],
        # Identifiant canonique (canonical_ids.py) — les exercices n'ont
        # jamais eu qu'un texte libre pour désigner leur notion ; ce champ
        # additif permet de les relier directement (sans recherche floue) à
        # une notion de cours (`notion_id` déjà canonique côté SCOPE_COURS).
        # None si le texte de la banque ne correspond à aucun topic connu.
        "topic_id": canonical_ids.resolve_topic_id(m["notion"], chapter_id=m["chapter_id"], class_level=class_level),
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


def _search_cours(query, limit, class_level=None):
    return [_cours_result(m) for m in knowledge_engine.search(query, top_k=limit, min_score=0.08, class_level=class_level)]


def _search_exercices(query, limit, class_level=None):
    matches = retrieval_engine.search(_get_exercise_index(class_level=class_level), query, top_k=limit, min_score=0.08)
    return [_exercice_result(m, class_level=class_level) for m in matches]


def _dedupe_key(r):
    return (r["type"], r.get("chapter_id"), r.get("notion_id") or r.get("exercise_id"))


def _fuzzy_fallback(query, scopes, limit, exclude_keys, cutoff=FUZZY_CUTOFF, class_level=None):
    """Repli tolérant aux fautes de frappe : compare `query` directement aux
    titres réels (notions de cours + notions d'exercice), sans exiger de mot
    commun exact comme le fait le TF-IDF. Utilisé quand la recherche normale
    est vide ou trop faible."""
    candidates = []  # (title, kind, document)
    if SCOPE_COURS in scopes:
        candidates.extend((d["title"], "cours", d) for d in knowledge_engine.all_documents(class_level=class_level))
    if SCOPE_EXERCICES in scopes:
        candidates.extend((d["notion"], "exercices", d) for d in _get_exercise_documents_cached(class_level=class_level))

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
            result = _cours_result(doc, score=ratio) if kind == "cours" else _exercice_result(doc, score=ratio, class_level=class_level)
            key = _dedupe_key(result)
            if key in exclude_keys:
                continue
            results.append(result)
            break
    results.sort(key=lambda r: r["score"], reverse=True)
    return results[:limit]


def _get_exercise_documents_cached(class_level=None):
    # Réutilise le même chargement que l'index TF-IDF (une seule lecture disque).
    return _get_exercise_index(class_level=class_level).documents


def search(query, scope=None, limit=10, class_level=None):
    """`scope` : None (tout) ou itérable parmi VALID_SCOPES. Renvoie une liste
    triée par score décroissant, tronquée à `limit` au total. Bascule sur un
    repli flou (fautes de frappe) si la recherche exacte est vide ou faible.
    `class_level` (optionnel, "seconde" par défaut) : scope à la fois la
    partie cours (knowledge_engine) ET la partie exercices, chacune via son
    propre cache par classe — jamais de mélange entre deux classes."""
    query = (query or "").strip()
    if not query:
        return []
    scopes = VALID_SCOPES if not scope else (set(scope) & VALID_SCOPES)
    if not scopes:
        return []

    results = []
    if SCOPE_COURS in scopes:
        results.extend(_search_cours(query, limit, class_level=class_level))
    if SCOPE_EXERCICES in scopes:
        results.extend(_search_exercices(query, limit, class_level=class_level))
    results.sort(key=lambda r: r["score"], reverse=True)

    if not results or results[0]["score"] < TFIDF_WEAK_THRESHOLD:
        seen = {_dedupe_key(r) for r in results}
        fuzzy = _fuzzy_fallback(query, scopes, limit, seen, class_level=class_level)
        results = (results + fuzzy)
        results.sort(key=lambda r: r["score"], reverse=True)

    return results[:limit]


def best_guess(query, scope=None, class_level=None):
    """Un seul candidat, même faible (utilisé pour le "Voulez-vous dire : X ?"
    des mentions "@" quand rien de solide n'a été trouvé). None si vraiment
    rien ne s'en approche."""
    query = (query or "").strip()
    if not query:
        return None
    scopes = VALID_SCOPES if not scope else (set(scope) & VALID_SCOPES)
    fuzzy = _fuzzy_fallback(query, scopes, 1, set(), cutoff=DID_YOU_MEAN_CUTOFF, class_level=class_level)
    return fuzzy[0] if fuzzy else None


def resolve(kind, chapter_id=None, notion_id=None, exercise_id=None, class_level=None):
    """Résolution exacte (pas une recherche) d'une ressource déjà identifiée
    par ses ids — utilisée par mentions_service.py pour injecter la vraie
    donnée dans le prompt système, jamais laisser le LLM deviner."""
    if kind == SCOPE_COURS and chapter_id and notion_id:
        doc = knowledge_engine.get_notion(chapter_id, notion_id, class_level=class_level)
        return _cours_result(doc, score=1.0) if doc else None
    if kind == SCOPE_EXERCICES and exercise_id is not None:
        doc = _get_exercise_by_id(class_level=class_level).get(exercise_id)
        return _exercice_result(doc, score=1.0, class_level=class_level) if doc else None
    return None
