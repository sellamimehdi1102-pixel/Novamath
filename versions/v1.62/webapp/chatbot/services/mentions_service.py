"""
Système de mentions "@" du chatbot : une seule route (GET /api/chatbot/mentions)
sert à la fois les raccourcis de page (catégories statiques, réelles) et la
recherche de ressources (cours/exercices, via search_service — TF-IDF +
repli flou pour les fautes de frappe). Le frontend (chatbot-mentions.js)
n'implémente aucune logique de correspondance : il affiche ce que renvoie
cette route et laisse le backend décider de la pertinence.

Quand l'élève envoie un message contenant des mentions résolues (chapter_id/
notion_id/exercise_id connus), build_grounding_block() injecte la vraie
donnée de la ressource dans le prompt système (voir conversation_manager.py)
— le LLM ne devine jamais le contenu d'une notion ou d'un exercice mentionné.
"""
import unicodedata

from . import intent_service, search_service
from .. import context_builder

# Catégories réelles du site. "search"/"data" récupèrent une vraie donnée et
# restent dans la conversation (grounding, voire réponse 100% locale — voir
# single_data_mention_intent ci-dessous, Phase R) ; "action" déclenche une
# action UI (ouvrir le vrai popup Paramètres pour ÉDITER, pas seulement lire).
CATEGORIES = [
    {"key": "cours", "label": "Cours", "kind": "search", "scope": [search_service.SCOPE_COURS]},
    {"key": "exercices", "label": "Exercices", "kind": "search", "scope": [search_service.SCOPE_EXERCICES]},
    {"key": "notions", "label": "Notions", "kind": "search", "scope": [search_service.SCOPE_COURS]},
    {"key": "series", "label": "Séries", "kind": "data", "data_key": "series"},
    {"key": "dashboard", "label": "Dashboard", "kind": "data", "data_key": "dashboard"},
    {"key": "progression", "label": "Progression", "kind": "data", "data_key": "progression"},
    {"key": "statistiques", "label": "Statistiques", "kind": "data", "data_key": "statistiques"},
    {"key": "objectifs", "label": "Objectifs", "kind": "goals"},
    {"key": "quiz", "label": "Quiz", "kind": "data", "data_key": "quiz"},
    {"key": "profil", "label": "Profil", "kind": "data", "data_key": "profil"},
    {"key": "parametres", "label": "Paramètres", "kind": "data", "data_key": "parametres"},
    {"key": "chatbot", "label": "Chatbot", "kind": "action", "action": "new-conversation", "url": "chatbot.html"},
]

_DATA_TITLES = {
    "dashboard": "Tableau de bord",
    "progression": "Progression",
    "statistiques": "Statistiques",
    "quiz": "Résultats récents",
    "profil": "Profil",
    "parametres": "Paramètres",
    "series": "Séries",
}

# data_key -> intent local (intent_service.py) répondable par
# local_knowledge_service.py (Phase Q/R) — permet à conversation_manager.py
# de traiter une mention "@" seule ("@Progression") comme une intention
# directe, sans jamais passer par le LLM, plutôt que par le grounding
# textuel générique de build_grounding_block() ci-dessous (toujours utilisé
# quand la mention accompagne une vraie question ouverte).
DATA_INTENT_BY_KEY = {
    "dashboard": intent_service.DASHBOARD,
    "progression": intent_service.PROGRESSION,
    "statistiques": intent_service.STATISTIQUE,
    "profil": intent_service.PROFIL,
    "parametres": intent_service.PARAMETRES,
    "series": intent_service.SERIE,
}

MAX_ITEMS = 8


def _normalize(s):
    s = unicodedata.normalize("NFKD", s or "").encode("ascii", "ignore").decode("ascii")
    return s.lower().strip()


def _matching_categories(query):
    q = _normalize(query)
    if not q:
        return list(CATEGORIES)
    return [c for c in CATEGORIES if _normalize(c["label"]).startswith(q) or c["key"].startswith(q)]


def _dedupe_resources(results):
    """Une notion peut être reliée à de nombreux exercices quasi identiques
    (même intitulé de notion) : pour un menu de mention, un seul représentant
    par (type, titre) suffit — le meilleur score gagne. Sans ce filtre, une
    requête large ("puissances") peut noyer le menu sous 8 exercices au même
    intitulé et masquer la notion de cours correspondante."""
    best = {}
    for r in results:
        # topic_id (canonical_ids.py) unifie désormais les deux vocabulaires
        # (notion_id des résultats "cours", texte libre des résultats
        # "exercices") — repli sur l'ancien texte si le topic_id n'a pas pu
        # être résolu (notion pas encore couverte par la crosswalk).
        key = (r["type"], r.get("notion_id") or r.get("topic_id") or r.get("notion") or r["title"])
        if key not in best or r["score"] > best[key]["score"]:
            best[key] = r
    return sorted(best.values(), key=lambda r: r["score"], reverse=True)


def search_mentions(query, limit=MAX_ITEMS):
    query = (query or "").strip()
    categories = _matching_categories(query)
    items = [{**c, "item_kind": "category"} for c in categories]

    remaining = max(0, limit - len(items))
    resources = []
    if query and remaining:
        # Cours et exercices interrogés séparément (pas un seul top-N partagé) :
        # une notion couvrant des dizaines d'exercices ("Puissances entières
        # relatives") écraserait sinon systématiquement la notion de cours
        # correspondante dans un classement mêlé dès le départ.
        cours = search_service.search(query, scope=[search_service.SCOPE_COURS], limit=remaining)
        exercices_raw = search_service.search(query, scope=[search_service.SCOPE_EXERCICES], limit=remaining * 6)
        exercices = _dedupe_resources(exercices_raw)
        resources = sorted(cours + exercices, key=lambda r: r["score"], reverse=True)[:remaining]
    items.extend({"item_kind": "resource", **r} for r in resources)

    if items or not query or len(query) < 2:
        return {"items": items[:limit], "did_you_mean": None}

    guess = search_service.best_guess(query)
    if guess:
        return {"items": [], "did_you_mean": {"item_kind": "resource", **guess}}
    return {"items": [], "did_you_mean": None}


def single_data_mention_intent(user_message, mentions):
    """Si `user_message` ne contient QUE une mention "@" de type "data" avec
    un data_key routable localement (pas de question ouverte autour), renvoie
    l'intent local correspondant (intent_service.PROGRESSION, etc.) — sinon
    None. Permet à conversation_manager.py de traiter "@Progression" seul
    comme une intention directe (réponse composée par local_knowledge_service,
    jamais par le LLM) plutôt que par le grounding textuel générique de
    build_grounding_block ci-dessous (toujours utilisé quand la mention
    accompagne une vraie question ouverte, ex. "@Progression pourquoi je
    stagne sur ce chapitre ?")."""
    if not mentions or len(mentions) != 1:
        return None
    only = mentions[0]
    if only.get("type") != "data":
        return None
    intent = DATA_INTENT_BY_KEY.get(only.get("data_key"))
    if not intent:
        return None
    label = only.get("label") or ""
    residual = (user_message or "").replace(f"@{label}", "", 1).strip()
    return intent if not residual else None


def build_grounding_block(mentions, user=None, chapters_summary=None):
    """`mentions` : liste de dicts {type, chapter_id?, notion_id?, exercise_id?,
    data_key?, label?} envoyés par le frontend (une par badge inséré dans le
    message). Résout chacune en vraie donnée — ignore silencieusement une
    mention invalide/périmée plutôt que de faire échouer toute la réponse.
    `user`/`chapters_summary` : nécessaires uniquement pour résoudre les
    mentions de type "data" (@Progression, @Statistiques...), qui recyclent
    exactement le résumé déjà utilisé pour le profil élève du prompt système
    (context_builder.build_context_summary) — aucune donnée dupliquée."""
    if not mentions:
        return ""
    blocks = []
    for m in mentions:
        if m.get("type") == "data":
            if not user:
                continue
            summary = context_builder.build_context_summary(user, chapters_summary)
            text = context_builder.summary_to_text(summary)
            title = _DATA_TITLES.get(m.get("data_key"), "Progression")
            blocks.append(f"### {title} — données réelles de l'élève\n{text}")
            continue
        resolved = search_service.resolve(
            m.get("type"),
            chapter_id=m.get("chapter_id"),
            notion_id=m.get("notion_id"),
            exercise_id=m.get("exercise_id"),
        )
        if not resolved:
            continue
        if resolved["type"] == search_service.SCOPE_COURS:
            blocks.append(f"### {resolved['title']}\n{resolved['snippet']}")
        else:
            blocks.append(f"### Exercice — {resolved['title']}\n{resolved['snippet']}")
    if not blocks:
        return ""
    return (
        "RESSOURCES MENTIONNÉES PAR L'ÉLÈVE AVEC \"@\" (utilise ces données réelles pour "
        "répondre, ne les invente jamais, ne les recopie pas mot pour mot) :\n\n"
        + "\n\n".join(blocks)
    )
