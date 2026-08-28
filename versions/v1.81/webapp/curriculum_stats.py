"""
Statistiques par programme scolaire, calculées à la volée depuis la banque
d'exercices déclarée dans curriculum_registry.py — jamais une valeur codée
en dur. Consommé par server.py (routes /api/site/stats et /api/curricula)
pour alimenter le sélecteur de classe et la landing page.

Volontairement indépendant de tout le reste (BANK/MODEL/chatbot) : ce module
ne charge QUE ce qui est nécessaire pour compter (exercise_bank.json d'une
classe), jamais les modèles ML, jamais les moteurs du chatbot, jamais les
routes d'exercices elles-mêmes — aucun risque d'impacter la sélection ou la
notation d'un exercice réel (server.py continue de servir les exercices
Seconde exactement comme avant, via ses propres structures BANK/BANK_BY_ID).

Honnêteté des champs exposés : le schéma réel d'un exercice (voir
exercises_bank.json / exercises_bank_premiere.json) ne contient que
{enonce, answer, hint, solution_steps, chapter_id, notion, difficulty} — pas
de distinction QCM/ouvert, pas de champ "méthode" ou "compétence". Ce module
n'expose donc QUE ce qui est réellement dérivable de ces données ; aucun
champ n'est inventé pour correspondre à une maquette.
"""
import json

from curriculum_registry import CURRICULUM_REGISTRY

_cache = {}  # class_level -> dict de statistiques, calculé une seule fois


def _load_bank(exercise_bank_path):
    if exercise_bank_path is None or not exercise_bank_path.exists():
        return []
    return json.loads(exercise_bank_path.read_text(encoding="utf-8"))


def compute_stats(class_level):
    """Statistiques d'un programme, mises en cache après le premier calcul
    (voir clear_cache() pour les tests). Une classe déclarée mais sans banque
    disponible renvoie des compteurs à zéro plutôt qu'une exception — cohérent
    avec la dégradation déjà choisie dans canonical_ids.py pour Première."""
    if class_level not in _cache:
        profile = CURRICULUM_REGISTRY[class_level]
        bank = _load_bank(profile.exercise_bank)
        _cache[class_level] = {
            "classLevel": profile.id,
            "label": profile.label,
            "totalExercises": len(bank),
            "chapters": len({e["chapter_id"] for e in bank if e.get("chapter_id")}),
            "notions": len({e["notion"] for e in bank if e.get("notion")}),
            "difficultyLevels": len({e["difficulty"] for e in bank if e.get("difficulty") is not None}),
            "exercisesWithSolution": sum(1 for e in bank if e.get("solution_steps")),
            # Fait déclaré directement par curriculum_registry.py (courses_dir) —
            # jamais déduit du contenu d'une autre classe. Permet à la page Cours
            # de savoir, sans en lire le contenu, si elle doit afficher un état
            # vide plutôt que les chapitres d'une autre classe.
            "hasCourses": profile.courses_dir is not None,
        }
    return _cache[class_level]


def list_curricula():
    """Un profil par entrée de curriculum_registry, dans l'ordre déclaré —
    seule liste que le frontend doit parcourir pour afficher N cartes, sans
    jamais nommer une classe en particulier (extensible à Terminale, Première
    NSI... par simple ajout d'un profil dans curriculum_registry.py)."""
    return [compute_stats(class_level) for class_level in CURRICULUM_REGISTRY]


def clear_cache():
    """Vide le cache — utilisé par les tests pour repartir d'un état connu,
    jamais nécessaire en usage normal (les banques ne changent pas en cours
    d'exécution du serveur)."""
    _cache.clear()
