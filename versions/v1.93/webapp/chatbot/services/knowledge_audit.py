"""
Audit de la base de connaissances NovaMath — Phase 4, Missions 1 & 2.

Outil d'ANALYSE PURE (lecture seule) : ne modifie jamais un fichier de cours,
ne prend aucune décision de réponse, n'est appelé par aucun moteur du
pipeline. Source unique de données : `knowledge_engine.all_documents()`
(déjà la source de vérité pour tout le projet) et
`search_service.exercises_by_topic()` — aucune lecture directe de JSON ici,
aucune logique de correspondance dupliquée.

Mission 1 : score de complétude par chapitre (et global) sur 12 dimensions
pédagogiques (définitions, méthodes, exemples, propriétés, démonstrations,
formules, erreurs fréquentes, vocabulaire, synonymes, prérequis, liens entre
notions, exercices liés).

Mission 2 : liste détaillée et priorisée des manques (notion par notion,
champ par champ) — pour guider une curation humaine future, jamais pour
combler automatiquement un champ avec une donnée inventée.
"""
from collections import defaultdict

from .. import knowledge_engine
from . import search_service

# Poids de chaque dimension dans le score global (documentés, somme = 100) —
# reflète une priorité pédagogique : une définition manquante est plus grave
# qu'un synonyme manquant.
DIMENSION_WEIGHTS = {
    "definitions": 15,
    "methodes": 15,
    "exemples": 15,
    "formules": 10,
    "proprietes": 10,
    "erreurs": 10,
    "exercices": 10,
    "prerequis": 5,
    "liens": 5,
    "synonymes": 2,
    "vocabulaire": 2,
    "demonstrations": 1,
}
assert sum(DIMENSION_WEIGHTS.values()) == 100

# Priorité d'affichage pour Mission 2 (du plus grave au moins grave) — même
# ordre que les poids, explicite pour ne pas dépendre de l'ordre d'un dict.
GAP_PRIORITY_ORDER = [
    "definitions", "methodes", "exemples", "formules", "proprietes",
    "erreurs", "exercices", "prerequis", "liens", "synonymes", "vocabulaire", "demonstrations",
]


def _has_definition(doc):
    return bool(doc.get("definition"))


def _has_methode(doc):
    return bool((doc.get("methode") or {}).get("etapes"))


def _has_exemples(doc):
    return bool(doc.get("exemples"))


def _has_formules(doc):
    return bool(doc.get("formules"))


def _has_proprietes(doc):
    return bool(doc.get("proprietes"))


def _has_demonstration(doc):
    """Une "démonstration" n'a pas de champ dédié dans le schéma KE v2
    aujourd'hui — la donnée la plus proche est le champ `preuve` d'une
    propriété structurée (voir knowledge_engine.get_proprietes). Absent sur
    toutes les notions migrées à ce jour (voir rapport Knowledge Response
    Composer) — ce champ existera donc à 0% tant qu'aucune propriété n'aura
    été curée avec sa preuve, ce qui est honnête plutôt que de considérer une
    formule comme une démonstration."""
    return any((p.get("preuve") or "").strip() for p in (doc.get("proprietes") or []))


def _has_erreurs(doc):
    return bool(doc.get("erreurs_detail") or doc.get("erreurs"))


def _has_vocabulaire(doc):
    return bool(doc.get("vocabulaire_associe"))


def _has_synonymes(doc):
    return bool(doc.get("synonymes"))


def _has_prerequis(doc):
    return bool(doc.get("prerequis"))


def _has_liens(doc):
    return bool(doc.get("notions_liees"))


def _has_exercices(doc):
    return bool(search_service.exercises_by_topic(doc["chapter_id"], doc["topic_id"], limit=1))


_CHECKS = {
    "definitions": _has_definition,
    "methodes": _has_methode,
    "exemples": _has_exemples,
    "formules": _has_formules,
    "proprietes": _has_proprietes,
    "demonstrations": _has_demonstration,
    "erreurs": _has_erreurs,
    "vocabulaire": _has_vocabulaire,
    "synonymes": _has_synonymes,
    "prerequis": _has_prerequis,
    "liens": _has_liens,
    "exercices": _has_exercices,
}


def audit_notion(doc):
    """Renvoie `{dimension: bool}` pour UNE notion (document déjà normalisé
    par knowledge_engine)."""
    return {dimension: check(doc) for dimension, check in _CHECKS.items()}


def _chapter_scores(chapter_docs):
    n = len(chapter_docs)
    if n == 0:
        return {dim: 0.0 for dim in DIMENSION_WEIGHTS}, 0.0
    per_notion = [audit_notion(doc) for doc in chapter_docs]
    percentages = {}
    for dim in DIMENSION_WEIGHTS:
        present = sum(1 for result in per_notion if result[dim])
        percentages[dim] = round(100 * present / n, 1)
    score_global = round(sum(percentages[dim] * DIMENSION_WEIGHTS[dim] / 100 for dim in DIMENSION_WEIGHTS), 1)
    return percentages, score_global


def audit_chapter(chapter_id):
    """Score de complétude d'UN chapitre (Mission 1) : `{dimension: pct}`
    plus `score_global` et `notion_count`. `None` si le chapitre n'existe pas
    (jamais une exception)."""
    docs = [d for d in knowledge_engine.all_documents() if d["chapter_id"] == chapter_id]
    if not docs:
        return None
    percentages, score_global = _chapter_scores(docs)
    return {
        "chapter_id": chapter_id,
        "chapter_title": docs[0].get("chapter_title", ""),
        "notion_count": len(docs),
        **percentages,
        "score_global": score_global,
    }


def audit_all():
    """Mission 1, tous chapitres : liste de `audit_chapter(...)` (ordre des
    chapitres = ordre d'apparition dans le Knowledge Engine) plus un score
    global du projet (moyenne pondérée par le nombre de notions, pas une
    simple moyenne de moyennes — un chapitre à 3 notions ne doit pas peser
    autant qu'un chapitre à 12 notions)."""
    docs = knowledge_engine.all_documents()
    by_chapter = defaultdict(list)
    for doc in docs:
        by_chapter[doc["chapter_id"]].append(doc)

    chapters = [audit_chapter(chapter_id) for chapter_id in sorted(by_chapter, key=lambda c: by_chapter[c][0].get("chapter_title", c))]
    total_notions = sum(c["notion_count"] for c in chapters) or 1
    project_score = round(sum(c["score_global"] * c["notion_count"] for c in chapters) / total_notions, 1)
    return {
        "chapters": chapters,
        "total_chapters": len(chapters),
        "total_notions": total_notions,
        "project_score_global": project_score,
    }


def format_chapter_report(chapter_audit):
    """Rendu texte, format demandé par le cahier des charges ("Chapitre 1 /
    Définitions : 100% / ... / Score global : 73%")."""
    if chapter_audit is None:
        return "Chapitre introuvable."
    lines = [f"{chapter_audit['chapter_title']} ({chapter_audit['chapter_id']}, {chapter_audit['notion_count']} notions)"]
    for dim in GAP_PRIORITY_ORDER:
        lines.append(f"  {dim.capitalize()} : {chapter_audit[dim]}%")
    lines.append(f"  Score global : {chapter_audit['score_global']}%")
    return "\n".join(lines)


# ── Mission 2 : détection et priorisation des manques ───────────────────────
def list_gaps(chapter_id=None):
    """Liste détaillée des manques, notion par notion, classée par priorité
    pédagogique (voir GAP_PRIORITY_ORDER) puis par chapitre/notion. Chaque
    entrée : `{chapter_id, topic_id, title, dimension, priority}`.
    `chapter_id=None` (par défaut) : tout le projet."""
    docs = knowledge_engine.all_documents()
    if chapter_id:
        docs = [d for d in docs if d["chapter_id"] == chapter_id]

    gaps = []
    for doc in docs:
        result = audit_notion(doc)
        for dimension in GAP_PRIORITY_ORDER:
            if not result[dimension]:
                gaps.append({
                    "chapter_id": doc["chapter_id"],
                    "topic_id": doc["topic_id"],
                    "title": doc["title"],
                    "dimension": dimension,
                    "priority": GAP_PRIORITY_ORDER.index(dimension),
                })
    gaps.sort(key=lambda g: (g["priority"], g["chapter_id"], g["topic_id"]))
    return gaps


def gaps_summary():
    """Compte total de manques par dimension, sur tout le projet — vue
    d'ensemble avant de plonger dans le détail notion par notion."""
    gaps = list_gaps()
    summary = {dim: 0 for dim in GAP_PRIORITY_ORDER}
    for gap in gaps:
        summary[gap["dimension"]] += 1
    return summary


def format_gaps_report(chapter_id=None, limit=50):
    gaps = list_gaps(chapter_id)
    lines = [f"{len(gaps)} manque(s) détecté(s){' pour ' + chapter_id if chapter_id else ''} :"]
    for gap in gaps[:limit]:
        lines.append(f"  - [{gap['dimension']}] {gap['chapter_id']} / {gap['title']} ({gap['topic_id']})")
    if len(gaps) > limit:
        lines.append(f"  ... et {len(gaps) - limit} de plus.")
    return "\n".join(lines)
