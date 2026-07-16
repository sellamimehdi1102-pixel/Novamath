"""
Décide quelles "cartes d'action" proposer sous une réponse du chatbot (ex:
"Voir le cours", "Revoir cette notion", "Commencer un entraînement") — des
règles simples sur des données réelles déjà calculées ailleurs (résultats de
search_service, notions faibles de context_builder), jamais un appel IA
dédié ni une donnée inventée. Chaque carte est renvoyée avec une `label_key`
(jamais un texte figé) que le frontend résout via i18n.js (DICT.fr/DICT.en).

Types de carte (le frontend sait naviguer pour chacun, cf. chatbot.js) :
- "course"        : lien direct cours.html?chapter=&notion=
- "notion_series" : {chapter_id, notion, exercise_ids} — le frontend doit poser
                     localStorage "lumis:pending_series" avant de naviguer vers
                     exercice.html (même pattern que chapitres.js::launchNotionSeries),
                     une URL brute ne suffit pas pour ce parcours.
"""
from . import search_service

SCORE_THRESHOLD = 0.15
MAX_CARDS = 3


def _course_card(result):
    return {
        "label_key": "chatbot_card_view_course",
        "icon": "book",
        "type": "course",
        "chapter_id": result["chapter_id"],
        "notion_id": result["notion_id"],
        "title": result["title"],
        "url": result["url"],
    }


def _notion_series_card(chapter_id, notion, exercise_ids, label_key="chatbot_card_practice"):
    return {
        "label_key": label_key,
        "icon": "target",
        "type": "notion_series",
        "chapter_id": chapter_id,
        "notion": notion,
        "exercise_ids": exercise_ids[:5],
        "url": None,
    }


def _dedupe_key(card):
    return (card["type"], card.get("chapter_id"), card.get("notion_id") or card.get("notion"))


def build_cards(user_message, assistant_response, context_summary, search_results=None, intent_chapter_id=None):
    """`search_results` : résultats déjà obtenus par search_service.search sur
    `user_message` (évite un second appel identique — voir conversation_manager).
    `intent_chapter_id` : chapitre résolu par intent_service.classify() quand
    l'intention était explicitement "exercice" — sert de garde-fou : un
    résultat de recherche libre peut porter un chapter_id hors-sujet (simple
    proximité de vocabulaire), la carte "Continuer un entraînement" ne doit
    alors provenir QUE de ce chapitre, jamais d'un autre."""
    cards = []
    seen = set()

    def add(card):
        key = _dedupe_key(card)
        if key in seen or len(cards) >= MAX_CARDS:
            return
        seen.add(key)
        cards.append(card)

    for r in (search_results or []):
        if r["score"] < SCORE_THRESHOLD:
            continue
        if r["type"] == "cours":
            add(_course_card(r))
        elif r["type"] == "exercices":
            if intent_chapter_id and r["chapter_id"] != intent_chapter_id:
                continue
            add(_notion_series_card(r["chapter_id"], r["notion"], [r["exercise_id"]]))

    for weak_notion in (context_summary.get("weak_notions") or [])[:1]:
        matches = search_service.search(weak_notion, scope=["cours"], limit=1)
        if matches and matches[0]["score"] >= SCORE_THRESHOLD:
            card = _course_card(matches[0])
            card["label_key"] = "chatbot_card_review_weak"
            add(card)
        exercise_matches = search_service.search(weak_notion, scope=["exercices"], limit=5)
        if exercise_matches:
            add(_notion_series_card(
                exercise_matches[0]["chapter_id"],
                exercise_matches[0]["notion"],
                [m["exercise_id"] for m in exercise_matches],
                label_key="chatbot_card_redo_series",
            ))

    return cards
