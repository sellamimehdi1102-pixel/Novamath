"""
Règle de progression centralisée côté backend (Phase N) — mêmes seuils que le
frontend (webapp/static/js/store.js::getChapterStatus, MASTERY_ACCURACY_THRESHOLD/
MASTERY_MIN_ATTEMPTS) : un chapitre ou une notion n'est "maîtrisé(e)" que si
l'accuracy dépasse ce seuil ET qu'il y a eu au moins ce nombre de tentatives.
Sans ce garde-fou, un chapitre à 90% de réussite sur seulement 2 questions
serait annoncé "maîtrisé" par le chatbot alors que le reste du site le
classerait encore "En cours" — la même incohérence que celle qui existait
avant cette phase (4 seuils différents selon la page).
"""
MASTERY_ACCURACY_THRESHOLD = 0.70
MASTERY_MIN_ATTEMPTS = 10


def is_mastered(correct, total):
    if not total:
        return False
    return total >= MASTERY_MIN_ATTEMPTS and (correct / total) >= MASTERY_ACCURACY_THRESHOLD
