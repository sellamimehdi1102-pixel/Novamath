"""
Registre central des programmes scolaires (curricula) de NovaMath.

Ce module ne fait QUE décrire où se trouvent les ressources propres à chaque
programme (classe, spécialité, matière, pays...). Il ne calcule rien, ne
transforme aucune donnée, ne décide d'aucun comportement. Toute décision
(comment charger un fichier, comment résoudre un identifiant, quel moteur
utiliser) reste dans les modules consommateurs (server.py, canonical_ids.py,
knowledge_engine.py, search_service.py, student_context_resolver.py...).

Aucun de ces consommateurs n'est modifié ni importé ici : ce module est
totalement indépendant, n'importe rien du projet (seulement la bibliothèque
standard), et n'est encore importé par personne. Tant qu'aucun composant ne
le consomme, le comportement actuel de NovaMath reste strictement identique.

Ajouter un programme (Terminale, Première NSI, Collège, un autre pays...) se
fait uniquement en ajoutant une entrée à `_PROFILES` ci-dessous — aucune
modification de structure n'est nécessaire.

Un champ à `None` signifie que la ressource n'existe pas encore pour ce
programme (ex. Première n'a pas encore de `program_file` ni de `models_dir`).
C'est un fait déclaré, pas une erreur : les futurs consommateurs décideront
eux-mêmes comment se dégrader dans ce cas.
"""
from dataclasses import dataclass
from pathlib import Path
from types import MappingProxyType
from typing import Mapping, Optional

PROJECT_ROOT = Path(__file__).resolve().parent.parent
STATIC_DATA_DIR = Path(__file__).resolve().parent / "static" / "data"


@dataclass(frozen=True)
class CurriculumProfile:
    """Description purement déclarative des ressources d'un programme scolaire.

    `id` est l'identifiant interne stable (utilisé par exemple comme premier
    élément d'une clé composite `(profile.id, chapter_id)` par les futurs
    consommateurs qui doivent distinguer un `chapter_id` par programme — ce
    module ne construit lui-même aucune clé composite ni aucune chaîne de
    namespace : il fournit uniquement la donnée `id` nécessaire pour que
    n'importe quel appelant la construise lui-même, à sa convenance).
    """

    id: str
    label: str
    courses_dir: Optional[Path]
    exercise_bank: Path
    natural_bank: Path
    program_file: Optional[Path]
    models_dir: Optional[Path]
    metadata_dir: Optional[Path]
    assets_dir: Optional[Path]


_PROFILES: tuple[CurriculumProfile, ...] = (
    CurriculumProfile(
        id="seconde",
        label="Seconde",
        courses_dir=STATIC_DATA_DIR / "cours",
        exercise_bank=PROJECT_ROOT / "exercises_bank.json",
        natural_bank=PROJECT_ROOT / "exercises_bank_natural.json",
        program_file=PROJECT_ROOT / "Programme AI.json",
        models_dir=PROJECT_ROOT / "models",
        metadata_dir=STATIC_DATA_DIR,
        assets_dir=None,
    ),
    CurriculumProfile(
        id="premiere",
        label="Première spécialité Mathématiques",
        # Généré depuis exercise_bank (voir generate_cours_from_bank.py) —
        # même schéma que "seconde", aucun contenu recopié de Seconde.
        courses_dir=STATIC_DATA_DIR / "cours_premiere",
        exercise_bank=PROJECT_ROOT / "exercises_bank_premiere.json",
        natural_bank=PROJECT_ROOT / "exercises_bank_premiere_natural.json",
        program_file=None,
        models_dir=None,
        metadata_dir=None,
        assets_dir=None,
    ),
    CurriculumProfile(
        id="troisieme",
        label="Troisième",
        # Généré depuis exercise_bank (voir generate_cours_from_bank.py) —
        # même schéma que "premiere", aucun contenu recopié de Seconde/Première.
        courses_dir=STATIC_DATA_DIR / "cours_troisieme",
        exercise_bank=PROJECT_ROOT / "exercises_bank_troisieme.json",
        natural_bank=PROJECT_ROOT / "exercises_bank_troisieme_natural.json",
        program_file=None,
        models_dir=None,
        metadata_dir=None,
        assets_dir=None,
    ),
)


def build_registry(profiles: tuple[CurriculumProfile, ...]) -> Mapping[str, CurriculumProfile]:
    """Assemble une séquence de profils en un mapping id -> profil, en
    garantissant qu'aucun `id` n'apparaît deux fois. C'est une vérification
    d'intégrité structurelle du registre lui-même (pas une décision métier) :
    exposée en fonction publique, indépendamment de `_PROFILES`, pour rester
    testable sans dépendre de l'état du module."""
    registry: dict[str, CurriculumProfile] = {}
    for profile in profiles:
        if profile.id in registry:
            raise ValueError(f"Identifiant de programme dupliqué dans le registre : {profile.id!r}")
        registry[profile.id] = profile
    return MappingProxyType(registry)


CURRICULUM_REGISTRY: Mapping[str, CurriculumProfile] = build_registry(_PROFILES)
