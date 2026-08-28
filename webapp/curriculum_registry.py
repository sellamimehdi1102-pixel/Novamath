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

# Chantier "Répartition du contenu des cours par plan" (2026-08-26) : le
# contenu pédagogique complet des notions (chapitre_*.json) ne doit plus être
# accessible tel quel via une URL statique (Flask sert tout webapp/static/ en
# clair, voir server.py::_STATIC_FOLDER) — sinon le filtrage Free/Premium/
# Ultra appliqué par la nouvelle route GET /api/course-content/... (voir
# server.py/course_content_service.py) serait purement cosmétique, contournable
# par un simple fetch direct de l'ancien chemin. Ce dossier vit donc HORS de
# webapp/static/ (jamais servi par Flask sans passer par une route), à ne pas
# confondre avec STATIC_DATA_DIR (topic_crosswalk.json, etc. — reste public,
# aucune donnée pédagogique sensible dedans).
COURSE_CONTENT_DIR = Path(__file__).resolve().parent / "course_content"


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
    # Pool additif produit par un moteur symbolique (voir
    # webapp/exercise_generator/) — regénérable via
    # tools/generate_derivative_exercises.py, jamais écrit à la main.
    # `None` = aucun pool généré pour ce programme (comportement inchangé :
    # seule la banque `exercise_bank` classique est servie).
    generated_exercise_bank: Optional[Path] = None


# Ordre officiel du système scolaire français (collège avant lycée) — c'est
# aussi l'ordre d'affichage du sélecteur de classe côté frontend (voir
# list_curricula() ci-dessous, qui parcourt CURRICULUM_REGISTRY dans l'ordre
# d'insertion) : ne jamais réordonner sans mettre à jour ce commentaire.
_PROFILES: tuple[CurriculumProfile, ...] = (
    CurriculumProfile(
        id="troisieme",
        label="Troisième",
        # Généré depuis exercise_bank (voir generate_cours_from_bank.py) —
        # même schéma que "premiere", aucun contenu recopié de Seconde/Première.
        courses_dir=COURSE_CONTENT_DIR / "cours_troisieme",
        exercise_bank=PROJECT_ROOT / "exercises_bank_troisieme.json",
        natural_bank=PROJECT_ROOT / "exercises_bank_troisieme_natural.json",
        program_file=None,
        models_dir=None,
        metadata_dir=None,
        assets_dir=None,
        # Pools symboliques (webapp/exercise_generator_troisieme/, pendant du
        # pilote Première) : équation du premier degré, divisibilité,
        # fractions (addition/simplification), fonction affine à partir de
        # deux images, distributivité simple, factorisation par facteur
        # commun, image d'une fonction — voir
        # tools/generate_troisieme_exercises.py. Additif uniquement (jamais
        # un remplacement : les exercices curés de exercise_bank restent
        # servis en premier).
        generated_exercise_bank=PROJECT_ROOT / "exercises_generated_troisieme.json",
    ),
    CurriculumProfile(
        id="seconde",
        label="Seconde",
        courses_dir=COURSE_CONTENT_DIR / "cours",
        exercise_bank=PROJECT_ROOT / "exercises_bank.json",
        natural_bank=PROJECT_ROOT / "exercises_bank_natural.json",
        program_file=PROJECT_ROOT / "Programme AI.json",
        models_dir=PROJECT_ROOT / "models",
        metadata_dir=STATIC_DATA_DIR,
        assets_dir=None,
        # Droites du plan (Chapitre_6) et inéquations/signe (Chapitre_9) : voir
        # tools/generate_seconde_exercises.py. Même patron additif que
        # "premiere" (jamais un remplacement : exercises_bank.json reste servi
        # tel quel, ce pool vient s'y ajouter pour diversifier les TYPES de
        # raisonnement de 6 notions ciblées par le chantier de diversification).
        generated_exercise_bank=PROJECT_ROOT / "exercises_generated_seconde.json",
    ),
    CurriculumProfile(
        id="premiere",
        label="Première spécialité Mathématiques",
        # Généré depuis exercise_bank (voir generate_cours_from_bank.py) —
        # même schéma que "seconde", aucun contenu recopié de Seconde.
        courses_dir=COURSE_CONTENT_DIR / "cours_premiere",
        exercise_bank=PROJECT_ROOT / "exercises_bank_premiere.json",
        natural_bank=PROJECT_ROOT / "exercises_bank_premiere_natural.json",
        program_file=None,
        models_dir=None,
        metadata_dir=None,
        assets_dir=None,
        # Fonction dérivée (Chapitre_3) : voir
        # tools/generate_derivative_exercises.py — pool à structure
        # mathématique réellement variable, en complément de exercise_bank
        # (jamais un remplacement : les exercices curés restent servis).
        generated_exercise_bank=PROJECT_ROOT / "exercises_generated_premiere.json",
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


class CurriculumIntegrityError(RuntimeError):
    """Un profil du registre déclare une ressource qui n'existe pas sur
    disque. Lever cette erreur au démarrage (voir server.py) ou au build
    (voir package.json::validate:curricula) plutôt que de laisser un
    utilisateur découvrir un 404 en cliquant sur "Ouvrir" un chapitre —
    c'est précisément l'incident que ce garde-fou existe pour empêcher :
    "troisieme" avait été ajouté à _PROFILES avec un courses_dir déclaré,
    sans que webapp/static/data/cours_troisieme/ ait jamais été généré."""


def validate_registry(registry: Mapping[str, CurriculumProfile] = CURRICULUM_REGISTRY) -> None:
    """Vérifie que chaque `courses_dir` déclaré existe et contient au moins
    un chapitre — la seule garantie que ce module peut faire sans dépendre
    d'aucun consommateur (il ignore volontairement exercise_bank/natural_bank/
    program_file/models_dir/metadata_dir/assets_dir : ce ne sont pas des
    contrats de "programme utilisable", juste des ressources annexes dont
    l'absence est déjà un `None` explicite et assumé, voir CurriculumProfile).

    Collecte TOUTES les erreurs avant de lever, pour ne jamais forcer un
    cycle "corrige un profil → relance → découvre le suivant"."""
    problems = []
    for profile in registry.values():
        if profile.courses_dir is None:
            continue
        if not profile.courses_dir.is_dir():
            problems.append(f"{profile.id!r} ({profile.label}) : courses_dir introuvable — {profile.courses_dir}")
            continue
        if not any(profile.courses_dir.glob("chapitre_*.json")):
            problems.append(f"{profile.id!r} ({profile.label}) : courses_dir vide (aucun chapitre_*.json) — {profile.courses_dir}")
    if problems:
        detail = "\n".join(f"  - {p}" for p in problems)
        raise CurriculumIntegrityError(
            "Registre des programmes incohérent : un programme déclaré n'a pas de contenu généré.\n"
            f"{detail}\n"
            "Génère le contenu manquant avec : python -m generate_cours_from_bank <id>"
        )


if __name__ == "__main__":
    # `python -m curriculum_registry` — utilisé par `npm run validate:curricula`
    # (voir package.json) avant chaque build, et par server.py au démarrage :
    # un registre incohérent doit faire échouer le build ou le démarrage du
    # serveur, jamais laisser un utilisateur cliquer dans le vide.
    validate_registry()
    print(f"OK — {len(CURRICULUM_REGISTRY)} programme(s) valide(s) : {', '.join(CURRICULUM_REGISTRY)}")
