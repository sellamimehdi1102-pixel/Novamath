"""
Identifiants canoniques de NovaMath — point d'entrée unique pour tout système
(chatbot, dashboard, séries, recommandations, futur système de mémoire) qui a
besoin de désigner un chapitre ou une notion sans ambiguïté.

chapter_id : la valeur "Chapitre_N" est DÉJÀ stable et universelle dans le
projet (exercises_bank.json, static/data/cours/chapitre_*.json, Programme
AI.json, historique élève, séries) — ce module ne renomme AUCUNE valeur
existante. Il normalise seulement les variantes de saisie/de nom de champ
("chapitre 1", "Chapitre_01", 1, "Chapitre_1"...) vers cette forme unique.

topic_id : nouveau canonique = le slug déjà présent dans
static/data/cours/chapitre_*.json (`notions[].id`, ex. "puissances-entieres-
relatives") — le seul identifiant de notion stable qui existait déjà avant ce
module. Partout ailleurs (exercises_bank.json, Programme AI.json, historique
élève), la notion n'est connue que par un texte libre ("Puissances entières
relatives"). TOPIC_CROSSWALK (static/data/topic_crosswalk.json, validé par
validate_topic_crosswalk.py) relie ces textes à leur topic_id, SCOPÉ par
chapter_id : un même texte libre peut désigner deux notions différentes
selon le chapitre (voir Chapitre_4/5 "Condition de colinéarité").

Résolution d'un texte libre en topic_id, en 2 temps (resolve_topic_id) :
1. Lookup exact (normalisé accents/casse) dans TOPIC_CROSSWALK — fiable à
   100% sur les textes déjà répertoriés.
2. Repli flou (retrieval_engine, déjà utilisé par chatbot/services/
   search_service.py) pour un texte inédit : synonyme, faute de frappe,
   formulation d'élève jamais vue.
"""
import json
import re
import unicodedata
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parent / "static" / "data"
COURS_DIR = DATA_DIR / "cours"

_CHAPTER_RE = re.compile(r"chapitre[_ ]?(\d+)", re.IGNORECASE)

_crosswalk = None  # dict {chapter_id: {label_normalisé: topic_id}} — chargé une fois
_crosswalk_raw = None  # dict {chapter_id: {label_original: topic_id}} — pour les erreurs lisibles
_topics_by_chapter = None  # dict {chapter_id: [{"id":..., "title":...}, ...]} — pour le repli flou


def _normalize_label(text):
    """Aplati accents/casse/espaces pour un lookup exact tolérant aux
    variations superficielles ("Valeur absolue" / "valeur absolue" /
    "  Valeur   absolue  ") — pas un vrai matching flou, juste une
    normalisation de surface avant le lookup exact."""
    folded = "".join(c for c in unicodedata.normalize("NFKD", text or "") if not unicodedata.combining(c))
    return " ".join(folded.lower().split())


def resolve_chapter_id(raw):
    """Normalise une valeur de chapitre arbitraire ("Chapitre_1", "chapitre 1",
    "Chapitre_01", 1, "1"...) vers la forme canonique "Chapitre_N" déjà
    utilisée partout dans le projet. Renvoie None si non reconnaissable."""
    if raw is None:
        return None
    if isinstance(raw, int):
        return f"Chapitre_{raw}"
    text = str(raw).strip()
    if not text:
        return None
    if text.isdigit():
        return f"Chapitre_{int(text)}"
    m = _CHAPTER_RE.search(text)
    if m:
        return f"Chapitre_{int(m.group(1))}"
    return None


def _load_crosswalk():
    global _crosswalk, _crosswalk_raw
    if _crosswalk is None:
        raw = json.loads((DATA_DIR / "topic_crosswalk.json").read_text(encoding="utf-8"))
        _crosswalk_raw = raw
        _crosswalk = {
            chapter_id: {_normalize_label(label): topic_id for label, topic_id in labels.items()}
            for chapter_id, labels in raw.items()
        }
    return _crosswalk


def _load_topics_by_chapter():
    global _topics_by_chapter
    if _topics_by_chapter is None:
        by_chapter = {}
        for path in COURS_DIR.glob("chapitre_*.json"):
            chapter = json.loads(path.read_text(encoding="utf-8"))
            by_chapter[chapter["chapterId"]] = [
                {"id": n["id"], "title": n.get("title", "")} for n in chapter.get("notions", [])
            ]
        _topics_by_chapter = by_chapter
    return _topics_by_chapter


def _fuzzy_topic_id(text, chapter_id=None):
    """Repli flou quand le lookup exact échoue — réutilise le même
    tokenizer/normalisation que retrieval_engine.py (léger, pas un vrai
    stemmer) via une comparaison de similarité de chaînes simple (difflib),
    scopée au chapitre si connu pour éviter un faux positif inter-chapitre."""
    import difflib

    by_chapter = _load_topics_by_chapter()
    candidates = by_chapter.get(chapter_id, []) if chapter_id else [
        t for topics in by_chapter.values() for t in topics
    ]
    if not candidates:
        return None
    normalized_text = _normalize_label(text)
    best_id, best_score = None, 0.0
    for topic in candidates:
        for candidate_text in (topic["id"].replace("-", " "), topic["title"]):
            score = difflib.SequenceMatcher(None, normalized_text, _normalize_label(candidate_text)).ratio()
            if score > best_score:
                best_id, best_score = topic["id"], score
    return best_id if best_score >= 0.6 else None


def resolve_topic_id(text, chapter_id=None):
    """Renvoie le topic_id canonique correspondant à un texte libre de
    notion, ou None si introuvable même en repli flou. `chapter_id` (recommandé)
    restreint la recherche à ce chapitre — sans lui, un texte ambigu entre
    deux chapitres renvoie le premier trouvé (voir docstring du module)."""
    if not text:
        return None
    crosswalk = _load_crosswalk()
    normalized = _normalize_label(text)
    if chapter_id:
        exact = crosswalk.get(chapter_id, {}).get(normalized)
        if exact:
            return exact
        return _fuzzy_topic_id(text, chapter_id=chapter_id)
    for labels in crosswalk.values():
        if normalized in labels:
            return labels[normalized]
    return _fuzzy_topic_id(text, chapter_id=None)


def synonyms_for_topic(chapter_id, topic_id):
    """Tous les libellés texte libre de topic_crosswalk.json qui résolvent
    vers ce topic_id, dans ce chapitre — réellement observés dans
    exercises_bank.json/Programme AI.json (jamais inventés). Utilisé par
    migrate_ke_v2.py pour peupler `notion["synonymes"]` automatiquement."""
    if not chapter_id:
        return []
    _load_crosswalk()  # garantit que _crosswalk_raw est chargé
    return sorted(label for label, tid in _crosswalk_raw.get(chapter_id, {}).items() if tid == topic_id)


def get_topic_title(chapter_id, topic_id):
    """Titre pédagogique du topic (pour affichage), ou None si introuvable."""
    for topic in _load_topics_by_chapter().get(chapter_id, []):
        if topic["id"] == topic_id:
            return topic["title"]
    return None
