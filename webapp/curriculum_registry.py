"""
Registre central des programmes scolaires (curricula) de Mathadap.

Ce module ne fait QUE décrire où se trouvent les ressources propres à chaque
programme (classe, spécialité, matière, pays...). Il ne calcule rien, ne
transforme aucune donnée, ne décide d'aucun comportement. Toute décision
(comment charger un fichier, comment résoudre un identifiant, quel moteur
utiliser) reste dans les modules consommateurs (server.py, canonical_ids.py,
knowledge_engine.py, search_service.py, student_context_resolver.py...).

Aucun de ces consommateurs n'est modifié ni importé ici : ce module est
totalement indépendant, n'importe rien du projet (seulement la bibliothèque
standard), et n'est encore importé par personne. Tant qu'aucun composant ne
le consomme, le comportement actuel de Mathadap reste strictement identique.

Ajouter un programme (Terminale, Première NSI, Collège, un autre pays...) se
fait uniquement en ajoutant une entrée à `_PROFILES` ci-dessous — aucune
modification de structure n'est nécessaire.

Un champ à `None` signifie que la ressource n'existe pas encore pour ce
programme (ex. Première n'a pas encore de `program_file` ni de `models_dir`).
C'est un fait déclaré, pas une erreur : les futurs consommateurs décideront
eux-mêmes comment se dégrader dans ce cas.
"""
import os
import re
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
    # Publication (chantier "préparation de la Quatrième", 2026-10-24) :
    # `False` = programme en préparation — absent de CURRICULUM_REGISTRY (le
    # mapping servi aux élèves, voir plus bas), donc rejeté (404) par chaque
    # route qui valide déjà `class_level` contre ce mapping, absent de
    # /api/curricula et de ses statistiques. Seul CURRICULUM_REGISTRY_ALL le
    # contient (outils hors ligne, validation). `True` par défaut : les
    # programmes existants gardent exactement leur disponibilité actuelle.
    published: bool = True
    # Étape de scolarité ("college" | "lycee") — fait déclaratif utilisé
    # pour situer le niveau attendu (ex. consigne de niveau du prompt
    # système de l'assistant). `None` = non renseigné, aucune consigne.
    school_stage: Optional[str] = None
    # Ordre des notions d'un chapitre dans les listes d'exercices
    # (/api/chapters) : `False` (défaut) = ordre alphabétique historique,
    # inchangé pour les programmes existants ; `True` = ordre pédagogique
    # du cours (courses_dir/chapitre_N.json, "notions" dans l'ordre), les
    # notions absentes du cours restant ensuite par ordre alphabétique.
    # Réservé aux programmes dont les titres de notion des exercices sont
    # exactement ceux du cours (vérifié par leurs tests).
    notion_order_from_courses: bool = False
    # Titres des chapitres PRÉVUS mais pas encore rédigés (classe en cours de
    # rédaction). Jamais affichés comme disponibles : servent uniquement à ce
    # que l'assistant ne rattache pas une question sur l'un d'eux à une
    # notion rédigée sans rapport (voir knowledge_engine.py::
    # planned_chapter_subjects). Vide (défaut) = classe complète, aucun effet.
    planned_chapter_titles: tuple[str, ...] = ()


# Ordre officiel du système scolaire français (collège avant lycée) — c'est
# aussi l'ordre d'affichage du sélecteur de classe côté frontend (voir
# list_curricula() ci-dessous, qui parcourt CURRICULUM_REGISTRY dans l'ordre
# d'insertion) : ne jamais réordonner sans mettre à jour ce commentaire.
_PROFILES: tuple[CurriculumProfile, ...] = (
    CurriculumProfile(
        id="quatrieme",
        label="Quatrième",
        # Chantier "Quatrième — chapitre pilote Pythagore" (2026-10-24),
        # PUBLIÉE le 2026-10-27 (published=True, voir QUATRIEME_SUIVI.md).
        # Programme de référence : cycle 4 (BO n°31 du
        # 30 juillet 2020) et repères annuels de 4e (BO n°22 du 29 mai 2019),
        # applicables en 2026-2027. Cours rédigés à la main (jamais via
        # generate_cours_from_bank.py). Numérotation DÉFINITIVE (ordre annuel,
        # fixée après l'audit des attendus de fin de 4e — Eduscol, repères
        # 2019 —, voir QUATRIEME_SUIVI.md ; chapter_id, progression et
        # historique ne sont jamais renumérotés) :
        #   1 nombres relatifs · 2 fractions (comparaison, addition) ·
        #   3 fractions (produit, quotient) · 4 divisibilité et nombres
        #   premiers · 5 puissances · 6 calcul littéral · 7 équations ·
        #   8 théorème de Pythagore (et racines carrées, chapitre pilote) ·
        #   9 Thalès (triangles emboîtés, réciproque) · 10 cosinus ·
        #   11 translations · 12 triangles égaux · 13 espace (repérage,
        #   pyramides, cônes, volumes, agrandissement-réduction) ·
        #   14 proportionnalité et grandeurs · 15 notion de fonction ·
        #   16 statistiques · 17 probabilités.
        # Les identifiants de notion restent stables indépendamment du
        # numéro de chapitre.
        courses_dir=COURSE_CONTENT_DIR / "cours_quatrieme",
        # Banque curée : écrite par tools/build_quatrieme_bank.py (source
        # unique des exercices rédigés, avec leurs contrôles mathématiques) —
        # jamais éditée à la main. Identifiants 40 000 + 1 000 × chapitre + k
        # (Chapitre_8 : 48 000+), plage libre dans toutes les autres banques.
        exercise_bank=PROJECT_ROOT / "exercises_bank_quatrieme.json",
        # Aucune reformulation "langage naturel" pour l'instant : fichier
        # absent, toléré par server.py::_class_bank (dégradation propre).
        natural_bank=PROJECT_ROOT / "exercises_bank_quatrieme_natural.json",
        program_file=None,
        models_dir=None,
        metadata_dir=None,
        assets_dir=None,
        # Pool symbolique (webapp/exercise_generator_quatrieme/, identifiants
        # 4 000 000 + 10 000 × chapitre) — voir
        # tools/generate_quatrieme_exercises.py. Additif : les exercices
        # curés restent servis en premier et portent seuls les mini-quiz.
        generated_exercise_bank=PROJECT_ROOT / "exercises_generated_quatrieme.json",
        published=True,
        notion_order_from_courses=True,
        # Les 17 chapitres de la numérotation ci-dessus sont rédigés : plus
        # aucun chapitre « prévu » à annoncer.
        planned_chapter_titles=(),
        school_stage="college",
    ),
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
        school_stage="college",
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
        school_stage="lycee",
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
        school_stage="lycee",
    ),
    CurriculumProfile(
        id="premiere_specifique",
        label="Première spécifique",
        # Chantier « Première spécialité, programme 2026 » (BO n° 14 du
        # 2 avril 2026), séparé de "premiere" le 2026-10-26 (voir
        # PREMIERE_SPECIALITE_SUIVI.md) : classe INDÉPENDANTE de la Première
        # historique — ses propres cours, banques, pool généré
        # (webapp/exercise_generator_premiere_specifique/) et sa propre
        # progression (rangée par class_level). PUBLIÉE le 2026-10-27
        # (published=True). Adaptée au manuel « Première ES/L » le 2026-10-26
        # (voir PREMIERE_SPECIFIQUE_SUIVI.md) : 9 chapitres, 29 notions —
        # 1 pourcentages · 2 fonctions numériques · 3 polynômes du second
        # degré · 4 statistiques · 5 dérivation · 6 dérivation et variations ·
        # 7 suites numériques · 8 variables aléatoires · 9 loi de Bernoulli
        # et loi binomiale. Les identifiants
        # d'exercices et de notions reprennent ceux de la Première
        # historique : sans conflit, chaque banque et chaque progression
        # étant résolue par classe (voir server.py::_class_bank).
        courses_dir=COURSE_CONTENT_DIR / "cours_premiere_specifique",
        # Écrite par tools/build_premiere_specifique_bank.py (jamais à la main).
        exercise_bank=PROJECT_ROOT / "exercises_bank_premiere_specifique.json",
        # Aucune reformulation « langage naturel » : celles de la Première
        # historique décrivent les anciens énoncés. Fichier absent, toléré
        # par server.py::_class_bank (dégradation propre).
        natural_bank=PROJECT_ROOT / "exercises_bank_premiere_specifique_natural.json",
        program_file=None,
        models_dir=None,
        metadata_dir=None,
        assets_dir=None,
        # Écrit par tools/generate_premiere_specifique_exercises.py.
        generated_exercise_bank=PROJECT_ROOT / "exercises_generated_premiere_specifique.json",
        published=True,
        school_stage="lycee",
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


# ── Publication et prévisualisation (chantier "préparation de la Quatrième",
# 2026-10-24) ──────────────────────────────────────────────────────────────
# CURRICULUM_REGISTRY_ALL : TOUS les profils déclarés, publiés ou non — réservé
# aux outils hors ligne et à la validation (jamais à une route HTTP).
#
# CURRICULUM_REGISTRY : le seul mapping que les consommateurs d'exécution
# (server.py, course_content_service.py, curriculum_stats.py, knowledge_engine,
# search_service, canonical_ids, exercise_generator/registry.py...) lisent
# déjà pour valider/résoudre un `class_level`. Il ne contient que les
# programmes publiés (+ ceux explicitement prévisualisés, voir ci-dessous) :
# un programme non publié est donc rejeté par CHAQUE point d'entrée existant
# sans qu'aucun d'eux n'ait à connaître la notion de publication — y compris
# si le client force `class_level` (localStorage, URL, corps de requête), la
# décision étant prise côté serveur à partir de ce mapping uniquement.
#
# Prévisualisation : uniquement par la variable d'environnement du PROCESSUS
# serveur NOVAMATH_PREVIEW_CURRICULA (ids séparés par des virgules), lue une
# seule fois à l'import — jamais par un paramètre de requête, un cookie ou un
# en-tête : seul quelqu'un qui contrôle le déploiement peut l'activer, et
# elle vaut pour toute l'instance (poste de développement, pré-production).
# Refusée en production (FLASK_ENV=production) et pour un id inconnu ou déjà
# publié : voir validate_registry(), appelé au démarrage de server.py — une
# configuration de prévisualisation erronée empêche le démarrage plutôt que
# d'être ignorée en silence.
PREVIEW_ENV_VAR = "NOVAMATH_PREVIEW_CURRICULA"
SCHOOL_STAGES = ("college", "lycee")
_PROFILE_ID_RE = re.compile(r"^[a-z][a-z0-9_]*$")


def parse_preview_ids(raw: Optional[str]) -> frozenset[str]:
    """"quatrieme, terminale" -> frozenset({"quatrieme", "terminale"}) ;
    chaîne vide/absente -> frozenset() (aucune prévisualisation)."""
    return frozenset(part.strip() for part in (raw or "").split(",") if part.strip())


def served_registry(
    registry: Mapping[str, CurriculumProfile], preview_ids: frozenset[str] = frozenset(),
) -> Mapping[str, CurriculumProfile]:
    """Sous-ensemble de `registry` réellement servi : profils publiés, plus
    les profils non publiés explicitement prévisualisés. Ordre conservé
    (ordre d'affichage du sélecteur de classe). Strict : seul `True`
    publie — une valeur mal saisie ("false", 1...) ne publie jamais rien
    (et validate_registry() la signale comme configuration invalide)."""
    return MappingProxyType({
        profile_id: profile for profile_id, profile in registry.items()
        if profile.published is True or profile_id in preview_ids
    })


def _is_production(environ: Mapping[str, str]) -> bool:
    # Même règle que config.py::IS_PRODUCTION (FLASK_ENV, "development" par
    # défaut) — relue ici pour garder ce module sans aucun import du projet.
    return environ.get("FLASK_ENV", "development").strip().lower() == "production"


CURRICULUM_REGISTRY_ALL: Mapping[str, CurriculumProfile] = build_registry(_PROFILES)
PREVIEW_CURRICULA: frozenset[str] = parse_preview_ids(os.environ.get(PREVIEW_ENV_VAR))
CURRICULUM_REGISTRY: Mapping[str, CurriculumProfile] = served_registry(CURRICULUM_REGISTRY_ALL, PREVIEW_CURRICULA)


class CurriculumIntegrityError(RuntimeError):
    """Un profil du registre déclare une ressource qui n'existe pas sur
    disque. Lever cette erreur au démarrage (voir server.py) ou au build
    (voir package.json::validate:curricula) plutôt que de laisser un
    utilisateur découvrir un 404 en cliquant sur "Ouvrir" un chapitre —
    c'est précisément l'incident que ce garde-fou existe pour empêcher :
    "troisieme" avait été ajouté à _PROFILES avec un courses_dir déclaré,
    sans que webapp/static/data/cours_troisieme/ ait jamais été généré."""


def _config_problems(profile: CurriculumProfile) -> list[str]:
    """Erreurs de configuration du profil lui-même, vérifiées pour TOUS les
    profils, publiés ou non (un profil en préparation n'a pas le droit d'être
    mal déclaré : seule l'absence de contenu lui est tolérée)."""
    problems = []
    if not isinstance(profile.id, str) or not _PROFILE_ID_RE.match(profile.id):
        problems.append(f"{profile.id!r} : identifiant invalide (attendu : minuscules ASCII, chiffres, « _ »)")
    if not isinstance(profile.label, str) or not profile.label.strip():
        problems.append(f"{profile.id!r} : libellé vide")
    if not isinstance(profile.published, bool):
        problems.append(f"{profile.id!r} : published={profile.published!r} invalide (attendu : True ou False)")
    if profile.school_stage is not None and profile.school_stage not in SCHOOL_STAGES:
        problems.append(f"{profile.id!r} : school_stage={profile.school_stage!r} invalide (attendu : {SCHOOL_STAGES} ou None)")
    return problems


def _content_problems(profile: CurriculumProfile) -> list[str]:
    """Ressources minimales d'un programme SERVI (publié ou prévisualisé) :
    chaque `courses_dir` déclaré existe et contient au moins un chapitre —
    exactement la règle historique de validate_registry() (il ignore
    volontairement exercise_bank/natural_bank/program_file/models_dir/
    metadata_dir/assets_dir : ce ne sont pas des contrats de "programme
    utilisable", juste des ressources annexes dont l'absence est déjà un
    `None` explicite et assumé, voir CurriculumProfile)."""
    if profile.courses_dir is None:
        return []
    if not profile.courses_dir.is_dir():
        return [f"{profile.id!r} ({profile.label}) : courses_dir introuvable — {profile.courses_dir}"]
    if not any(profile.courses_dir.glob("chapitre_*.json")):
        return [f"{profile.id!r} ({profile.label}) : courses_dir vide (aucun chapitre_*.json) — {profile.courses_dir}"]
    return []


def validate_registry(
    registry: Optional[Mapping[str, CurriculumProfile]] = None,
    preview_ids: Optional[frozenset[str]] = None,
    environ: Optional[Mapping[str, str]] = None,
) -> None:
    """Vérifie le registre complet (CURRICULUM_REGISTRY_ALL par défaut) :

    - configuration de chaque profil, publié ou non (voir _config_problems) ;
    - ressources minimales de chaque profil SERVI — publié, ou non publié
      mais prévisualisé (voir _content_problems). Un profil non publié et
      non prévisualisé peut ne pas encore avoir de contenu : c'est l'état
      normal d'un programme en préparation, jamais servi à personne ;
    - cohérence de la prévisualisation : chaque id prévisualisé doit exister
      et ne pas être déjà publié, et aucune prévisualisation n'est permise
      en production.

    `preview_ids` : par défaut PREVIEW_CURRICULA (variable d'environnement)
    quand on valide le registre réel, et aucune prévisualisation quand un
    `registry` explicite est fourni (tests : jamais influencés par
    l'environnement du poste qui les exécute).

    Collecte TOUTES les erreurs avant de lever, pour ne jamais forcer un
    cycle "corrige un profil → relance → découvre le suivant"."""
    if registry is None:
        registry = CURRICULUM_REGISTRY_ALL
        if preview_ids is None:
            preview_ids = PREVIEW_CURRICULA
    preview_ids = preview_ids or frozenset()
    environ = os.environ if environ is None else environ

    config_problems, content_problems, preview_problems = [], [], []
    for profile in registry.values():
        config_problems.extend(_config_problems(profile))
        if profile.published is True or profile.id in preview_ids:
            content_problems.extend(_content_problems(profile))

    if preview_ids and _is_production(environ):
        preview_problems.append(
            f"{PREVIEW_ENV_VAR}={','.join(sorted(preview_ids))} interdit en production (FLASK_ENV=production)"
        )
    for preview_id in sorted(preview_ids):
        if preview_id not in registry:
            preview_problems.append(f"{PREVIEW_ENV_VAR} : programme inconnu {preview_id!r}")
        elif registry[preview_id].published is True:
            preview_problems.append(f"{PREVIEW_ENV_VAR} : {preview_id!r} est déjà publié (prévisualisation inutile)")

    if config_problems or content_problems or preview_problems:
        sections = []
        if config_problems:
            sections.append("Configuration invalide :\n" + "\n".join(f"  - {p}" for p in config_problems))
        if preview_problems:
            sections.append("Prévisualisation invalide :\n" + "\n".join(f"  - {p}" for p in preview_problems))
        if content_problems:
            sections.append(
                "Un programme servi n'a pas de contenu généré :\n"
                + "\n".join(f"  - {p}" for p in content_problems)
                + "\nGénère le contenu manquant avec : python -m generate_cours_from_bank <id>"
            )
        raise CurriculumIntegrityError("Registre des programmes incohérent.\n" + "\n".join(sections))


if __name__ == "__main__":
    # `python -m curriculum_registry` — utilisé par `npm run validate:curricula`
    # (voir package.json) avant chaque build, et par server.py au démarrage :
    # un registre incohérent doit faire échouer le build ou le démarrage du
    # serveur, jamais laisser un utilisateur cliquer dans le vide.
    validate_registry()
    print(f"OK — {len(CURRICULUM_REGISTRY)} programme(s) servi(s) : {', '.join(CURRICULUM_REGISTRY)}")
    en_preparation = [p for p in CURRICULUM_REGISTRY_ALL if p not in CURRICULUM_REGISTRY]
    if en_preparation:
        print(f"     {len(en_preparation)} programme(s) en préparation (non publiés) : {', '.join(en_preparation)}")
    if PREVIEW_CURRICULA:
        print(f"     Prévisualisation active ({PREVIEW_ENV_VAR}) : {', '.join(sorted(PREVIEW_CURRICULA))}")
