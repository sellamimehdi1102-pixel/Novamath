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
from pathlib import Path

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

COURS_DIR = Path(__file__).resolve().parent.parent / "static" / "data" / "cours"

DEFINITION_RE = re.compile(
    r"\b(c'est quoi|qu'est[- ]ce que|définition de|défini[st]|que veut dire|"
    r"rappelle[- ]moi|propriété de|règle de|théorème de|formule de)\b",
    re.IGNORECASE,
)

_index = None  # retrieval_engine.Index — construit une seule fois, en mémoire
_by_ids = None  # dict {(chapter_id, notion_id): document} — lookup exact, pour les mentions "@"


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


def _get_index():
    global _index
    if _index is None:
        _index = retrieval_engine.build_index(_load_notions())
    return _index


def _get_by_ids():
    global _by_ids
    if _by_ids is None:
        _by_ids = {(d["chapter_id"], d["notion_id"]): d for d in _load_notions()}
    return _by_ids


def get_notion(chapter_id, notion_id):
    """Lookup exact (pas une recherche) — utilisé pour résoudre une mention "@"
    déjà identifiée (chapter_id/notion_id connus), afin d'injecter la vraie
    définition dans le prompt sans jamais laisser le LLM deviner."""
    return _get_by_ids().get((chapter_id, notion_id))


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


def get_exemple(notion, difficulte=None):
    """Un exemple adapté à la difficulté demandée ("facile"/"moyen"/
    "difficile"), tiré au sort parmi les exemples correspondants (jamais
    toujours le même — même esprit que response_composer.compose). Repli sur
    un tirage parmi tous les exemples si aucun ne correspond à la difficulté
    demandée, ou si la notion n'a pas encore de champ `difficulte`."""
    exemples = notion.get("exemples") or []
    if not exemples:
        return None
    if difficulte:
        matching = [ex for ex in exemples if ex.get("difficulte") == difficulte]
        if matching:
            return random.choice(matching)
    return random.choice(exemples)


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


def all_documents():
    """Tous les documents indexés (cours), pour un usage externe (fallback
    flou de search_service.py) — jamais copiés, la liste est reconstruite
    depuis les mêmes fichiers sources."""
    return _load_notions()


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
