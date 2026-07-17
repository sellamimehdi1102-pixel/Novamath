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

── Multi-classe (class_level) ────────────────────────────────────────────
Toutes les fonctions publiques acceptent un paramètre optionnel
`class_level` (défaut `None` → "seconde", exactement comme
student_context_resolver.resolve()). "Chapitre_1" existe indépendamment
pour Seconde et pour Première (voir exercises_bank_premiere.json) : sans
distinction de classe, les deux se mélangeraient dans le même cache. Ce
module ne renomme ni ne préfixe jamais "Chapitre_1" — le namespace vit
uniquement dans la structure des caches Python (voir _crosswalk_by_class /
_topics_by_chapter_by_class ci-dessous), jamais dans la donnée elle-même.

Les chemins ne sont plus des constantes de module (DATA_DIR/COURS_DIR
figées) : ils sont lus par classe dans curriculum_registry.CURRICULUM_REGISTRY,
seule source de vérité des emplacements de fichiers. Une classe dont les
ressources ne sont pas encore disponibles (ex. Première, `courses_dir`/
`metadata_dir` valent None dans le registre à ce stade) résout simplement
vers "aucune correspondance trouvée" (comportement déjà existant pour un
texte/chapitre inconnu), jamais une exception.
"""
import json
import re
import unicodedata

import curriculum_registry

_CHAPTER_RE = re.compile(r"chapitre[_ ]?(\d+)", re.IGNORECASE)

_DEFAULT_CLASS_LEVEL = "seconde"

# Caches à deux niveaux : class_level -> (structure strictement identique à
# l'ancien cache global, inchangée à l'intérieur). Voir le rapport d'étape
# pour la justification de ce choix (dict imbriqué) plutôt qu'une clé tuple
# (class_level, chapter_id).
_crosswalk_by_class = {}       # class_level -> {chapter_id: {label_normalisé: topic_id}}
_crosswalk_raw_by_class = {}   # class_level -> {chapter_id: {label_original: topic_id}}
_topics_by_chapter_by_class = {}  # class_level -> {chapter_id: [{"id":..., "title":...}, ...]}


def _resolve_class_level(class_level):
    """Normalise `class_level` vers sa valeur effective : la valeur fournie
    si non vide, sinon "seconde" — jamais None au-delà de cette fonction."""
    return class_level or _DEFAULT_CLASS_LEVEL


def _profile_for(class_level):
    """Profil déclaratif du registre pour cette classe. Lève KeyError si
    `class_level` n'est pas un identifiant connu de curriculum_registry —
    erreur de programmation (typo, classe jamais déclarée), volontairement
    non avalée : contrairement à une donnée absente pour une classe connue
    (dégradation silencieuse vers "aucun résultat"), une classe inconnue ne
    doit jamais être confondue avec une simple absence de contenu."""
    return curriculum_registry.CURRICULUM_REGISTRY[class_level]


def _normalize_label(text):
    """Aplati accents/casse/espaces pour un lookup exact tolérant aux
    variations superficielles ("Valeur absolue" / "valeur absolue" /
    "  Valeur   absolue  ") — pas un vrai matching flou, juste une
    normalisation de surface avant le lookup exact."""
    folded = "".join(c for c in unicodedata.normalize("NFKD", text or "") if not unicodedata.combining(c))
    return " ".join(folded.lower().split())


def resolve_chapter_id(raw, class_level=None):
    """Normalise une valeur de chapitre arbitraire ("Chapitre_1", "chapitre 1",
    "Chapitre_01", 1, "1"...) vers la forme canonique "Chapitre_N" déjà
    utilisée partout dans le projet. Renvoie None si non reconnaissable.

    `class_level` est accepté (et ignoré) uniquement pour l'uniformité de
    signature avec les autres fonctions publiques de ce module : la
    normalisation syntaxique "Chapitre_N" est identique pour toutes les
    classes (même convention de nommage dans exercises_bank.json et
    exercises_bank_premiere.json, confirmé lors de l'audit), donc cette
    fonction ne lit aucune donnée et n'a rien à distinguer par classe."""
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


def _load_crosswalk(class_level):
    class_level = _resolve_class_level(class_level)
    if class_level not in _crosswalk_by_class:
        profile = _profile_for(class_level)
        raw = {}
        if profile.metadata_dir is not None:
            crosswalk_path = profile.metadata_dir / "topic_crosswalk.json"
            if crosswalk_path.exists():
                raw = json.loads(crosswalk_path.read_text(encoding="utf-8"))
        _crosswalk_raw_by_class[class_level] = raw
        _crosswalk_by_class[class_level] = {
            chapter_id: {_normalize_label(label): topic_id for label, topic_id in labels.items()}
            for chapter_id, labels in raw.items()
        }
    return _crosswalk_by_class[class_level]


def _load_topics_by_chapter(class_level):
    class_level = _resolve_class_level(class_level)
    if class_level not in _topics_by_chapter_by_class:
        profile = _profile_for(class_level)
        by_chapter = {}
        if profile.courses_dir is not None and profile.courses_dir.exists():
            for path in profile.courses_dir.glob("chapitre_*.json"):
                chapter = json.loads(path.read_text(encoding="utf-8"))
                by_chapter[chapter["chapterId"]] = [
                    {"id": n["id"], "title": n.get("title", "")} for n in chapter.get("notions", [])
                ]
        _topics_by_chapter_by_class[class_level] = by_chapter
    return _topics_by_chapter_by_class[class_level]


def _fuzzy_topic_id(text, chapter_id=None, class_level=None):
    """Repli flou quand le lookup exact échoue — réutilise le même
    tokenizer/normalisation que retrieval_engine.py (léger, pas un vrai
    stemmer) via une comparaison de similarité de chaînes simple (difflib),
    scopée au chapitre si connu pour éviter un faux positif inter-chapitre."""
    import difflib

    by_chapter = _load_topics_by_chapter(class_level)
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


def resolve_topic_id(text, chapter_id=None, class_level=None):
    """Renvoie le topic_id canonique correspondant à un texte libre de
    notion, ou None si introuvable même en repli flou. `chapter_id` (recommandé)
    restreint la recherche à ce chapitre — sans lui, un texte ambigu entre
    deux chapitres renvoie le premier trouvé (voir docstring du module).

    `class_level` (optionnel, "seconde" par défaut) : scope la recherche au
    crosswalk et aux cours de cette classe. Une classe dont les données ne
    sont pas encore disponibles (ex. Première tant que son crosswalk/ses
    cours n'existent pas) ne trouve simplement rien, comme un texte inconnu
    — jamais une exception."""
    if not text:
        return None
    crosswalk = _load_crosswalk(class_level)
    normalized = _normalize_label(text)
    if chapter_id:
        exact = crosswalk.get(chapter_id, {}).get(normalized)
        if exact:
            return exact
        return _fuzzy_topic_id(text, chapter_id=chapter_id, class_level=class_level)
    for labels in crosswalk.values():
        if normalized in labels:
            return labels[normalized]
    return _fuzzy_topic_id(text, chapter_id=None, class_level=class_level)


def synonyms_for_topic(chapter_id, topic_id, class_level=None):
    """Tous les libellés texte libre de topic_crosswalk.json qui résolvent
    vers ce topic_id, dans ce chapitre (pour cette classe) — réellement
    observés dans les données du projet (jamais inventés). Utilisé par
    migrate_ke_v2.py pour peupler `notion["synonymes"]` automatiquement."""
    if not chapter_id:
        return []
    class_level = _resolve_class_level(class_level)
    _load_crosswalk(class_level)  # garantit que _crosswalk_raw_by_class[class_level] est chargé
    return sorted(
        label for label, tid in _crosswalk_raw_by_class[class_level].get(chapter_id, {}).items() if tid == topic_id
    )


def get_topic_title(chapter_id, topic_id, class_level=None):
    """Titre pédagogique du topic (pour affichage) pour cette classe, ou
    None si introuvable."""
    for topic in _load_topics_by_chapter(class_level).get(chapter_id, []):
        if topic["id"] == topic_id:
            return topic["title"]
    return None
