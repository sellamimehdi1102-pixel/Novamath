"""
Student Context Resolver v2 (Response Engine v2, Phase 2) — point d'entrée
UNIQUE pour tout ce qu'un moteur de réponse doit savoir sur l'élève avant de
composer une réponse : niveau, paramètres, chapitre/notion courants,
notions maîtrisées/faibles, statistiques, dashboard, mentions "@", progression,
préférences, historique de conversation récent.

Entièrement découplé du LLM (aucun import de provider_manager/prompt_builder
ni d'aucun fournisseur IA) — ce module ne fait qu'agréger et normaliser des
données déjà présentes dans le projet.

ADDITIF, PAS UN REMPLACEMENT : n'importe quel appelant existant
(conversation_manager.py, action_cards_service.py...) continue d'utiliser
directement context_builder.py/variable_resolver.py comme avant, sans aucun
changement de comportement — ce module se contente de les APPELER et de
composer leurs résultats en un seul objet normalisé, plus un cache et la
résolution des mentions/de l'historique de conversation qu'aucun des deux
n'agrégeait jusqu'ici. Le câblage dans le pipeline live est prévu pour la
Phase 6 (cablage du Response Engine v2 dans conversation_manager.py).
"""
import time

import canonical_ids
from auth import read_user_course_progress, read_user_settings, read_user_stats

from . import context_builder
from .services import search_service, variable_resolver

_CACHE_TTL_SECONDS = 5
_MAX_CACHE_ENTRIES = 500
_MAX_HISTORY_TURNS = 10

_cache = {}  # (user_id, class_level) -> (timestamp, StudentContext dict)


def _cache_key(user_id, class_level):
    return (user_id, class_level or "seconde")


# ── Cache (TTL court, mémoire process — même esprit que chatbot/cache.py) ───
# Clé (user_id, class_level) : un StudentContext calculé pour Seconde ne doit
# jamais être servi tel quel à une requête faite en Première (et inversement)
# pendant la fenêtre de 5s — voir audit multi-classe du chatbot.
def _cache_get(user_id, class_level=None):
    key = _cache_key(user_id, class_level)
    entry = _cache.get(key)
    if not entry:
        return None
    ts, value = entry
    if time.monotonic() - ts > _CACHE_TTL_SECONDS:
        del _cache[key]
        return None
    return value


def _cache_set(user_id, value, class_level=None):
    key = _cache_key(user_id, class_level)
    _cache[key] = (time.monotonic(), value)
    if len(_cache) > _MAX_CACHE_ENTRIES:
        oldest_key = min(_cache, key=lambda k: _cache[k][0])
        del _cache[oldest_key]


def invalidate(user_id, class_level=None):
    """À appeler après une écriture qui doit être immédiatement visible
    (nouvelle réponse à un exercice, changement de paramètre) si attendre le
    TTL (5s) n'est pas acceptable. Sans appel explicite, le cache expire de
    lui-même — aucune invalidation n'est requise pour un usage normal.
    `class_level` omis : invalide toutes les classes connues pour ce user_id
    (repli sûr si l'appelant ne connaît pas la classe active)."""
    if class_level is not None:
        _cache.pop(_cache_key(user_id, class_level), None)
        return
    for key in [k for k in _cache if k[0] == user_id]:
        del _cache[key]


def clear_cache():
    """Vide tout le cache — utilisé par les tests pour repartir d'un état
    connu, jamais nécessaire en usage normal (le TTL suffit)."""
    _cache.clear()


# ── Normalisation ────────────────────────────────────────────────────────────
def _normalize_parametres(chatbot_settings):
    """Vocabulaire stable, indépendant des noms de champs bruts du frontend
    (camelCase) — les phases suivantes lisent ce dict, jamais chatbot_settings
    directement. Note honnête (voir rapport de phase) : "difficulté" comme
    préférence PERSISTANTE n'existe pas encore dans chatbot_settings
    aujourd'hui (seule une difficulté PAR MESSAGE existe, voir
    intent_service.classify()["difficulty"]) ; "mode coach"/"mode révision"
    ne sont pas non plus des valeurs de `mode` actuellement supportées par
    pedagogy_templates.py (seuls professeur/rapide/pas_a_pas/visuel/examen le
    sont) — ce normalisateur reflète fidèlement ce qui existe, sans en
    inventer davantage."""
    cs = chatbot_settings or {}
    return {
        "longueur": cs.get("responseLength", "normal"),
        "niveau_explication": cs.get("explanationLevel", "auto"),
        "mode": cs.get("mode"),
        "memoire_activee": cs.get("memoryEnabled", True),
        "historique_active": cs.get("historyEnabled", True),
        "provider": cs.get("provider"),
        "modele": cs.get("model"),
        "temperature": cs.get("temperature", 0.6),
    }


def _normalize_mentions(mentions, class_level=None):
    """Résout chaque mention "@" (même forme que mentions_service.
    build_grounding_block : {type, chapter_id?, notion_id?, exercise_id?,
    data_key?, label?}) en données réelles, avec chapter_id/topic_id toujours
    canoniques. Une mention invalide/périmée est ignorée silencieusement
    (même comportement que build_grounding_block), jamais une erreur."""
    if not mentions:
        return []
    resolved = []
    for m in mentions:
        if m.get("type") == "data":
            resolved.append({"type": "data", "data_key": m.get("data_key"), "label": m.get("label")})
            continue
        result = search_service.resolve(
            m.get("type"), chapter_id=m.get("chapter_id"),
            notion_id=m.get("notion_id"), exercise_id=m.get("exercise_id"),
            class_level=class_level,
        )
        if not result:
            continue
        resolved.append({
            "type": result["type"],
            "chapter_id": canonical_ids.resolve_chapter_id(result.get("chapter_id")),
            "topic_id": result.get("notion_id") or result.get("topic_id"),
            "title": result.get("title"),
        })
    return resolved


def _normalize_history(history_rows):
    """Historique de CONVERSATION récent (messages chat, db.list_messages) —
    à ne pas confondre avec l'historique d'EXERCICES de l'élève (auth.
    read_user_stats, utilisé pour les statistiques). Tronqué aux derniers
    tours, jamais l'historique complet."""
    if not history_rows:
        return []
    trimmed = history_rows[-_MAX_HISTORY_TURNS:]
    return [{"role": h.get("role"), "content": h.get("content")} for h in trimmed]


def _resolve_current_topic(current_chapter_ref, current_topic_ref, context_summary, class_level=None):
    chapter_id = canonical_ids.resolve_chapter_id(current_chapter_ref, class_level=class_level) if current_chapter_ref else None
    topic_id = None
    if current_topic_ref:
        topic_id = canonical_ids.resolve_topic_id(current_topic_ref, chapter_id=chapter_id, class_level=class_level)
    if not chapter_id and context_summary.get("chapters_in_progress"):
        chapter_id = context_summary["chapters_in_progress"][0]
    return chapter_id, topic_id


# ── API publique ─────────────────────────────────────────────────────────────
def resolve(
    user, chapters_summary=None, chatbot_settings=None, mentions=None,
    current_chapter_ref=None, current_topic_ref=None, history_rows=None,
    use_cache=True, class_level=None,
):
    """Construit le StudentContext complet (dict, voir REQUIRED_FIELDS dans
    validate_student_context.py pour la forme exacte). Toutes les entrées
    sont optionnelles sauf `user` ({id, pseudo, level}, même forme que dans
    conversation_manager.py) — un champ non fourni reste vide plutôt que de
    faire planter la résolution.

    `class_level` (optionnel, "seconde" par défaut) : identifiant de
    programme scolaire (voir curriculum_registry.py), transporté tel quel
    dans le StudentContext. Ce resolver ne le CHOISIT jamais lui-même — il
    ne fait que le propager si on le lui fournit, sinon "seconde" pour que
    tout appelant existant (aucun ne fournit ce paramètre aujourd'hui)
    continue d'obtenir exactement le même contexte qu'avant l'ajout de ce
    paramètre. La résolution réelle (session/profil/cookie) est une étape
    future, hors périmètre ici.

    `use_cache=True` (par défaut) : réutilise un contexte déjà calculé pour
    ce user_id il y a moins de 5s (évite de relire 3 fichiers JSON à chaque
    appel dans un même tour de conversation — voir attach_action_cards() et
    stream_reply() dans conversation_manager.py, qui appellent aujourd'hui
    séparément context_builder.build_context_summary pour la même requête).
    `chatbot_settings`/`mentions`/`current_chapter_ref`/`current_topic_ref`/
    `history_rows` ne sont PAS mis en cache indépendamment : un contexte
    caché est réutilisé tel quel, ce qui suppose un appel très rapproché avec
    les mêmes paramètres (même tour de conversation) — sinon passer
    use_cache=False."""
    user_id = user["id"]
    if use_cache:
        cached = _cache_get(user_id, class_level)
        if cached is not None:
            return cached

    # Chaque fichier JSON n'est lu qu'UNE FOIS ici, puis injecté dans
    # context_builder/variable_resolver (paramètres additifs, Phase 2) — sans
    # ça, stats/settings étaient chacun relus 2 à 3 fois pour un seul appel
    # (context_builder ET variable_resolver appelaient séparément auth.py).
    stats = read_user_stats(user_id)
    settings = read_user_settings(user_id)
    course_progress = read_user_course_progress(user_id, class_level=class_level)
    effective_settings = chatbot_settings if chatbot_settings is not None else settings.get("chatbot", {})

    context_summary = context_builder.build_context_summary(
        user, chapters_summary, stats=stats, settings=settings, course_progress=course_progress,
        class_level=class_level,
    )
    variables = variable_resolver.resolve(
        user, context_summary, effective_settings, stats=stats, settings=settings, class_level=class_level,
    )
    chapter_id, topic_id = _resolve_current_topic(current_chapter_ref, current_topic_ref, context_summary, class_level=class_level)

    student_context = {
        "user_id": user_id,
        "class_level": class_level or "seconde",
        "pseudo": user.get("pseudo"),
        "niveau": context_summary["level_label"],
        "niveau_brut": user.get("level"),
        "parametres": _normalize_parametres(effective_settings),
        "chapitre_courant": chapter_id,
        "topic_courant": topic_id,
        "notions_maitrisees": context_summary["mastered_notions"],
        "notions_faibles": context_summary["weak_notions"],
        "topics_maitrises": context_summary["mastered_topics"],
        "topics_faibles": context_summary["weak_topics"],
        "statistiques": {
            "accuracy": context_summary["accuracy_pct"],
            "total_exercices": context_summary["total_exercises"],
            "temps_total": variables["temps_total"],
            "temps_jour": variables["temps_jour"],
            "temps_semaine": variables["temps_semaine"],
        },
        "dashboard": {
            "objectif_du_jour": context_summary["daily_goals"],
            "chapitres_en_cours": context_summary["chapters_in_progress"],
            "meilleur_chapitre": variables["meilleur_chapitre"],
            "chapitre_le_plus_faible": variables["chapitre_le_plus_faible"],
        },
        "progression": course_progress,
        "preferences": {
            "langue": context_summary["language"],
            "niveau_explication": context_summary["explanation_level"],
            "favoris": settings.get("favorites") or [],
        },
        "mentions": _normalize_mentions(mentions, class_level=class_level),
        "historique_conversation": _normalize_history(history_rows),
    }

    if use_cache:
        _cache_set(user_id, student_context, class_level)
    return student_context
