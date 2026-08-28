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
import random
import re

import curriculum_registry

from . import retrieval_engine

# Vocabulaire de difficulté unifié (KE v2) — le projet a jusqu'ici TROIS
# échelles incompatibles : intent_service.py ("easy"/"hard", 2 niveaux),
# exercises_bank.json (entier 1-5, voir search_service.py) et les nouveaux
# `exemples[].difficulte` ci-dessous ("facile"/"moyen"/"difficile"). Ces
# tables de correspondance centralisent la conversion plutôt que de laisser
# chaque appelant deviner — voir get_exemple() et la comparaison (aujourd'hui
# cassée, jamais vraie) `d.get("difficulty") == difficulty` dans
# search_service.search_exercises_in_chapter().
DIFFICULTE_LEVELS = ("facile", "moyen", "difficile")
INTENT_DIFFICULTY_TO_LABEL = {"easy": "facile", "hard": "difficile"}
EXERCISES_BANK_SCALE_TO_LABEL = {1: "facile", 2: "facile", 3: "moyen", 4: "difficile", 5: "difficile"}

DEFINITION_RE = re.compile(
    r"\b(c'est quoi|qu'est[- ]ce que|définition de|défini[st]|que veut dire|"
    r"rappelle[- ]moi|propriété de|règle de|théorème de|formule de)\b",
    re.IGNORECASE,
)

_DEFAULT_CLASS_LEVEL = "seconde"

# Alias rétrocompatible : validate_cours_schema.py (hors périmètre de ce
# chantier) importe encore COURS_DIR directement. Pointe vers exactement le
# même dossier qu'avant (courses_dir de "seconde"), aucune valeur différente.
COURS_DIR = curriculum_registry.CURRICULUM_REGISTRY[_DEFAULT_CLASS_LEVEL].courses_dir

# Caches à deux niveaux (class_level -> ...), même principe que
# canonical_ids.py : une classe dont les cours ne sont pas encore disponibles
# (courses_dir=None dans curriculum_registry.py) dégrade vers un index/lookup
# vide plutôt que de planter — jamais d'exception pour Première tant que ses
# cours ne sont pas branchés.
_index_by_class = {}  # class_level -> retrieval_engine.Index
_by_ids_by_class = {}  # class_level -> dict {(chapter_id, notion_id): document}


def _resolve_class_level(class_level):
    return class_level or _DEFAULT_CLASS_LEVEL


def _load_notions(class_level=None):
    """Construit les documents à indexer à partir des cours NovaMath existants
    (source unique de vérité) — aucune copie persistée nulle part."""
    class_level = _resolve_class_level(class_level)
    profile = curriculum_registry.CURRICULUM_REGISTRY[class_level]
    cours_dir = profile.courses_dir
    notions = []
    if cours_dir is None or not cours_dir.exists():
        return notions
    for path in sorted(cours_dir.glob("chapitre_*.json")):
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
                # Champs KE v2 (additifs, absents sur les notions pas encore
                # enrichies — voir get_definition/get_formules/get_exemple/
                # get_methode_etapes/get_erreurs_detail ci-dessous, qui savent
                # retomber sur les champs historiques ci-dessus).
                "definitions": notion.get("definitions") or {},
                "formules": notion.get("formules") or [],
                "exemples": notion.get("exemples") or [],
                "methode": notion.get("methode") or {},
                "erreurs_detail": notion.get("erreursFrequentesDetail") or [],
                # Champs KE v2 — généralisation aux 12 chapitres (voir
                # migrate_ke_v2.py). Structure toujours présente après
                # migration (liste/chaîne vide si non enrichi), jamais
                # absente : voir get_proprietes/get_vocabulaire/etc.
                "topic_id": notion.get("topic_id") or notion.get("id", ""),
                "proprietes": notion.get("proprietes") or [],
                "vocabulaire_associe": notion.get("vocabulaire_associe") or [],
                "synonymes": notion.get("synonymes") or [],
                "objectifs_pedagogiques": notion.get("objectifs_pedagogiques") or [],
                "prerequis": notion.get("prerequis") or [],
                "notions_liees": notion.get("notions_liees") or [],
                "difficulte": notion.get("difficulte") or "",
                "tags": notion.get("tags") or [],
                "schema_version": notion.get("schemaVersion") or 1,
            })
    return notions


def _get_index(class_level=None):
    class_level = _resolve_class_level(class_level)
    if class_level not in _index_by_class:
        _index_by_class[class_level] = retrieval_engine.build_index(_load_notions(class_level))
    return _index_by_class[class_level]


def _get_by_ids(class_level=None):
    class_level = _resolve_class_level(class_level)
    if class_level not in _by_ids_by_class:
        _by_ids_by_class[class_level] = {(d["chapter_id"], d["notion_id"]): d for d in _load_notions(class_level)}
    return _by_ids_by_class[class_level]


def get_notion(chapter_id, notion_id, class_level=None):
    """Lookup exact (pas une recherche) — utilisé pour résoudre une mention "@"
    déjà identifiée (chapter_id/notion_id connus), afin d'injecter la vraie
    définition dans le prompt sans jamais laisser le LLM deviner. `class_level`
    optionnel ("seconde" par défaut) : une classe sans cours disponibles
    renvoie None ici, comme une notion introuvable — jamais d'exception."""
    return _get_by_ids(class_level).get((chapter_id, notion_id))


# ── Accès structuré KE v2 (schéma enrichi, additif) ─────────────────────────
# Une notion pas encore migrée n'a que les champs historiques (`definition`,
# `exemples` sans `difficulte`, `methode.etapes` sans `etapesParNiveau`,
# `erreursFrequentes` en texte brut) : chaque accesseur retombe alors sur ce
# champ historique plutôt que de renvoyer du vide, pour que le pipeline
# fonctionne à l'identique sur les notions non enrichies.
def get_definition(notion, level=None):
    """`level` : "college" | "lycee" | "expert", ou None. Renvoie la
    définition du niveau demandé si elle existe, sinon la définition unique
    historique (`notion["definition"]`)."""
    if level:
        by_level = notion.get("definitions") or {}
        if by_level.get(level):
            return by_level[level]
    return notion.get("definition", "")


def get_formules(notion):
    """Liste de formules structurées (nom/expression/quand_utiliser/
    quand_ne_pas_utiliser/erreur_frequente/astuce). Vide si la notion n'en a
    pas encore (les règles restent alors dans `notion["regles"]`, en texte)."""
    return notion.get("formules") or []


def get_exemple(notion, difficulte=None, exclude_ids=None):
    """Un exemple adapté à la difficulté demandée ("facile"/"moyen"/
    "difficile"), tiré au sort parmi les exemples correspondants (jamais
    toujours le même — même esprit que response_composer.compose). Repli sur
    un tirage parmi tous les exemples si aucun ne correspond à la difficulté
    demandée, ou si la notion n'a pas encore de champ `difficulte`.

    `exclude_ids` (chantier "répétition des exemples", 2026-08-23) : ids
    d'exemples déjà montrés dans la conversation (voir
    conversation_manager._commit_used_exemple / learning_context.
    used_exemple_ids) — exclus du tirage en priorité. Si TOUS les exemples de
    la notion figurent déjà dans `exclude_ids` (stock épuisé), le tirage
    retombe sur l'ensemble complet plutôt que de renvoyer None (mieux vaut
    répéter un exemple que ne rien montrer) — voir exemple_pool_exhausted()
    pour que l'appelant sache PRÉALABLEMENT que ce repli va se produire et le
    dise honnêtement plutôt que de prétendre un exemple inédit."""
    exemples = notion.get("exemples") or []
    if not exemples:
        return None
    exclude_ids = set(exclude_ids or ())
    pool = [ex for ex in exemples if ex.get("id") not in exclude_ids] or exemples
    if difficulte:
        matching = [ex for ex in pool if ex.get("difficulte") == difficulte]
        if matching:
            return random.choice(matching)
    return random.choice(pool)


def exemple_pool_exhausted(notion, exclude_ids):
    """True si `notion` n'a AUCUN exemple, ou si tous ses exemples figurent
    déjà dans `exclude_ids` — c'est-à-dire si le prochain appel à
    get_exemple(notion, exclude_ids=exclude_ids) va nécessairement RÉPÉTER un
    exemple déjà montré, faute d'alternative réelle dans les données. Permet
    à l'appelant de le dire honnêtement plutôt que de prétendre un exemple
    inédit (jamais de fausse variante fabriquée)."""
    exemples = notion.get("exemples") or []
    if not exemples:
        return True
    ids = {ex.get("id") for ex in exemples}
    return ids.issubset(set(exclude_ids or ()))


def get_methode_etapes(notion, niveau=None):
    """`niveau` : "debutant" | "normal" | "rapide", ou None. Renvoie les
    étapes du niveau demandé si `methode.etapesParNiveau` existe, sinon les
    étapes historiques uniques (`methode.etapes`)."""
    methode = notion.get("methode") or {}
    if niveau:
        par_niveau = methode.get("etapesParNiveau") or {}
        if par_niveau.get(niveau):
            return par_niveau[niveau]
    return methode.get("etapes") or []


def get_erreurs_detail(notion):
    """Erreurs fréquentes structurées (description/pourquoi/comment_detecter/
    comment_eviter). Vide si la notion n'a pas encore ce champ (les erreurs
    restent alors en texte brut dans `notion["erreurs"]`)."""
    return notion.get("erreurs_detail") or []


# ── Champs KE v2 généralisés (migrate_ke_v2.py) ─────────────────────────────
# Structure toujours présente après migration (liste/chaîne vide si pas
# encore enrichi par un contenu réel) — jamais absente. Ces accesseurs
# existent pour que les futurs moteurs (Exercise/Course/Quiz/Recommendation
# Engine) aient un point d'entrée stable dès aujourd'hui, sans dépendre du
# taux de remplissage réel du contenu.
def get_proprietes(notion):
    """Propriétés structurées (nom/explication/preuve/importance/niveau/
    erreurs_frequentes/contre_exemple/applications). [] tant qu'aucune
    propriété n'a été rédigée pour cette notion (curation humaine future)."""
    return notion.get("proprietes") or []


def get_regles(notion):
    """Règles en texte brut — repli historique de get_formules() tant qu'une
    notion n'a pas encore de formules structurées. [] si absent."""
    return notion.get("regles") or []


def get_a_retenir(notion):
    """Point(s) clé(s) à retenir pour un résumé rapide de la notion. [] si
    non renseigné."""
    return notion.get("a_retenir") or []


def get_vocabulaire_associe(notion):
    """Lexique associé à la notion (terme/definition). []  tant que non
    renseigné."""
    return notion.get("vocabulaire_associe") or []


def get_synonymes(notion):
    """Formulations alternatives connues de cette notion — dérivées de
    static/data/topic_crosswalk.json (canonical_ids.py) lors de la migration,
    donc réellement observées dans exercises_bank.json/Programme AI.json,
    jamais inventées."""
    return notion.get("synonymes") or []


def get_objectifs_pedagogiques(notion):
    """Liste d'objectifs pédagogiques — reprend le champ historique
    `objectif` (singulier) s'il existait, sous forme de liste à un élément."""
    return notion.get("objectifs_pedagogiques") or []


def get_prerequis(notion):
    """Liste de topic_id prérequis. [] tant qu'aucun enchaînement
    pédagogique n'a été curé par un professeur (aucune donnée source ne
    permet de le déduire automatiquement sans risque d'erreur)."""
    return notion.get("prerequis") or []


def get_notions_liees(notion):
    """Liste de topic_id de notions proches/complémentaires. [] tant que non
    curé (même limitation que get_prerequis)."""
    return notion.get("notions_liees") or []


def get_difficulte(notion):
    """Difficulté globale de la notion (DIFFICULTE_LEVELS), distincte de la
    difficulté par exemple (get_exemple). "" tant que non évaluée."""
    return notion.get("difficulte") or ""


def get_tags(notion):
    """Tags de recherche/filtrage. [] tant que non renseignés."""
    return notion.get("tags") or []


def all_documents(class_level=None):
    """Tous les documents indexés (cours), pour un usage externe (fallback
    flou de search_service.py) — jamais copiés, la liste est reconstruite
    depuis les mêmes fichiers sources."""
    return _load_notions(class_level)


def search(query, top_k=3, min_score=0.12, class_level=None):
    return retrieval_engine.search(_get_index(class_level), query, top_k=top_k, min_score=min_score)


def try_answer_definition(user_message, class_level=None):
    """Réponse directe (sans IA) si la question est clairement une demande
    de définition/rappel ET qu'une notion correspond nettement mieux que les
    autres. Sinon None (le pipeline continue vers le contexte + le fournisseur actif)."""
    text = (user_message or "").strip()
    if not text or not DEFINITION_RE.search(text):
        return None
    # min_score=0 ici : on a besoin du DEUXIÈME résultat même faible pour
    # juger de l'ambiguïté (un filtrage précoce le ferait disparaître et
    # romprait la comparaison d'écart ci-dessous).
    matches = search(text, top_k=2, min_score=0.0, class_level=class_level)
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


def _format_notion_block(m):
    block = [f"### {m['title']} ({m['chapter_title']})", m["definition"]]
    if m["regles"]:
        block.append("Règles : " + " ; ".join(m["regles"]))
    if m["erreurs"]:
        block.append("Erreurs fréquentes : " + " ; ".join(m["erreurs"]))
    return "\n".join(block)


def context_block(user_message, top_k=3, class_level=None):
    """Bloc de contexte compact (RAG) par RECHERCHE sur `user_message` :
    quelques notions pertinentes, jamais le cours entier. Chaîne vide si rien
    de pertinent n'est trouvé. Pour un message ambigu ("réexplique", "encore"...
    voir intent_service.REFORMULATION_RE), préférer notion_context_block()
    ci-dessous : une recherche ici n'a plus aucun mot-clé de sujet à exploiter
    et peut remonter une notion sans rapport avec un score faible mais réel."""
    matches = search(user_message, top_k=top_k, class_level=class_level)
    if not matches:
        return ""
    return "\n\n".join(_format_notion_block(m) for m in matches)


def notion_context_block(chapter_id, notion_id, class_level=None):
    """Bloc de contexte (RAG) par LOOKUP EXACT (chapter_id/notion_id déjà
    connus — ex: Current Learning Context mémorisé par conversation_manager.py
    pour un message ambigu), jamais une recherche floue : ne peut donc jamais
    se tromper de notion, contrairement à context_block() sur un message qui
    ne contient plus aucun mot permettant une recherche fiable. Chaîne vide si
    la notion est introuvable (identifiants périmés, classe sans ce cours...)."""
    if not notion_id:
        return ""
    notion = get_notion(chapter_id, notion_id, class_level=class_level)
    if not notion:
        return ""
    return _format_notion_block(notion)


def get_chapter_title(chapter_id, class_level=None):
    """Titre du chapitre `chapter_id`, ou None si introuvable (identifiant
    périmé, classe sans ce cours...). Utilisé quand le Current Learning
    Context connaît le chapitre mais pas la notion précise (voir
    conversation_manager.py::_update_learning_context) — permet quand même de
    nommer explicitement le sujet dans l'instruction système, plutôt que de
    l'omettre faute de notion exacte."""
    for doc in _get_by_ids(class_level).values():
        if doc["chapter_id"] == chapter_id:
            return doc["chapter_title"]
    return None


def chapter_context_block(chapter_id, class_level=None, max_notions=3):
    """Bloc de contexte (RAG) pour tout un CHAPITRE (pas une notion précise) —
    utilisé quand le Current Learning Context connaît le chapitre mais pas la
    notion exacte (ex: le tout premier message de la conversation n'a matché
    aucune notion par recherche, voir intent_service._detect_chapter, repli
    `context_summary["chapters_in_progress"]`). Sans ce repli, un message
    ambigu ("réexplique"...) qui hérite d'un chapitre sans notion précise
    retombait sur une recherche floue non fiable (context_block) sur le
    message ambigu lui-même — souvent vide ou hors-sujet (voir audit
    Current Learning Context). Compile jusqu'à `max_notions` notions de ce
    chapitre (ordre du fichier source) ; chaîne vide si le chapitre est
    introuvable ou n'a aucune notion indexée."""
    notions = [doc for doc in _get_by_ids(class_level).values() if doc["chapter_id"] == chapter_id]
    if not notions:
        return ""
    return "\n\n".join(_format_notion_block(m) for m in notions[:max_notions])
