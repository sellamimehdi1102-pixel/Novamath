"""
Validation du contenu des cours de CHAQUE programme du registre (chantier
"préparation de la Quatrième", 2026-10-24) — publiés ou en préparation.

Les validateurs existants restent la source de chaque règle et ne sont pas
modifiés : ce module les applique à tous les programmes de
curriculum_registry.CURRICULUM_REGISTRY_ALL (chatbot.validate_cours_schema
ne vérifie que la Seconde quand on l'appelle sans argument) et y ajoute les
contrôles transverses qui n'existaient nulle part.

Deux niveaux, jamais confondus :

- ERREURS (bloquantes, code de sortie 1) : ce qui casse ou fausse
  l'affichage réel — schéma invalide, LaTeX brut, chapterId incohérent avec
  le nom du fichier, identifiant de notion dupliqué dans la classe, figure de
  type inconnu du moteur de rendu, niveau d'accès invalide, référence de
  mini-quiz vers un exercice absent de la banque (cours.js charge les
  exercices du quiz avec Promise.all : une seule référence absente fait
  disparaître tout le mini-quiz de la notion).
- AVERTISSEMENTS (pédagogiques, n'affectent pas le code de sortie) :
  contenu générique (chatbot.check_cours_generic_content), notion sans
  figure, sans exemple gratuit ou sans mini-quiz, exercice de quiz rattaché
  à un autre chapitre, titre de chapitre de remplissage.

Limite connue : les références de quiz sont vérifiées contre l'union
exercise_bank + generated_exercise_bank du programme. Pour la Seconde,
server.py ne sert qu'une partie du pool généré (Chapitre_6/9) : une
référence vers un exercice généré non servi d'un autre chapitre de Seconde
ne serait pas détectée.

Lecture seule : ne modifie jamais aucun fichier.

Usage (depuis webapp/) :
    python -m validate_curriculum_content                 # tous les programmes
    python -m validate_curriculum_content troisieme       # un programme
    python -m validate_curriculum_content troisieme 14    # un chapitre
"""
import json
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

import curriculum_registry
from chatbot import check_cours_generic_content, validate_cours_schema

GEOM_SVG_JS = Path(__file__).resolve().parent / "static" / "js" / "geomSvg.js"
VALID_ACCESS_LEVELS = ("free", "premium", "ultra")
VALID_APERCU_LEVELS = ("premium", "ultra")
_PLACEHOLDER_TITLE_RE = re.compile(r"^\s*chapitre[\s_]*\d+\s*$", re.IGNORECASE)
_CHAPTER_FILE_RE = re.compile(r"^chapitre_(\d+)\.json$")


def supported_figure_kinds(geom_svg_js: Path = GEOM_SVG_JS) -> frozenset[str]:
    """Types de figures réellement rendus, lus dans l'objet RENDERERS de
    geomSvg.js (source unique : jamais une liste recopiée ici qui pourrait
    diverger du moteur de rendu)."""
    source = geom_svg_js.read_text(encoding="utf-8")
    match = re.search(r"const RENDERERS = \{(.*?)\};", source, re.DOTALL)
    if match is None:
        raise RuntimeError(f"Objet RENDERERS introuvable dans {geom_svg_js}")
    return frozenset(re.findall(r"^\s*\"?([\w-]+)\"?\s*:", match.group(1), re.MULTILINE))


def _chapter_number(arg: str) -> str:
    """"Chapitre_3" / "chapitre_3" / "3" -> "3"."""
    digits = re.findall(r"\d+", arg)
    if not digits:
        raise ValueError(f"Chapitre invalide : {arg!r}")
    return str(int(digits[0]))


def _load_bank_index(profile) -> Optional[dict]:
    """{id: chapter_id} de l'union exercise_bank + generated_exercise_bank,
    ou None si aucune banque n'existe encore (programme en préparation)."""
    index, found = {}, False
    for path in (profile.exercise_bank, profile.generated_exercise_bank):
        if path is None or not path.exists():
            continue
        found = True
        for i, ex in enumerate(json.loads(path.read_text(encoding="utf-8"))):
            # Même règle que server.py::_class_bank : id absent -> position.
            index[ex.get("id") if ex.get("id") is not None else i] = ex.get("chapter_id")
    return index if found else None


def _example_access_level(exemple, index):
    # Même règle que course_content_service._example_access_level (repli
    # positionnel quand niveauAcces est absent).
    level = exemple.get("niveauAcces")
    if level in VALID_ACCESS_LEVELS:
        return level
    return "free" if index == 0 else "premium"


@dataclass
class ClassReport:
    class_level: str
    status: str
    chapters: int = 0
    notions: int = 0
    errors: list = field(default_factory=list)
    warnings: list = field(default_factory=list)
    skipped: Optional[str] = None


def _check_notion(chapter_name, chapter_id, notion, figure_kinds, bank_index, seen_ids, report):
    nid = notion.get("id", "?")
    prefix = f"{chapter_name} / notion {nid}"

    if nid in seen_ids:
        report.errors.append(f"{prefix} : identifiant de notion déjà utilisé par {seen_ids[nid]}")
    else:
        seen_ids[nid] = chapter_name

    figure = notion.get("figure")
    if figure is None:
        report.warnings.append(f"{prefix} : aucune figure")
    elif not isinstance(figure, dict):
        report.errors.append(f"{prefix} : figure invalide (objet attendu, reçu {type(figure).__name__})")
    elif "kind" not in figure:
        report.warnings.append(f"{prefix} : figure sans « kind » (rendue par défaut comme « geom »)")
    elif figure["kind"] not in figure_kinds:
        report.errors.append(f"{prefix} : figure.kind={figure['kind']!r} inconnu du moteur de rendu (attendu : {sorted(figure_kinds)})")

    exemples = notion.get("exemples") or []
    for i, exemple in enumerate(exemples):
        level = exemple.get("niveauAcces")
        if level is not None and level not in VALID_ACCESS_LEVELS:
            report.errors.append(f"{prefix} : exemples[{i}].niveauAcces={level!r} invalide (attendu : {VALID_ACCESS_LEVELS})")
    if exemples and not any(_example_access_level(e, i) == "free" for i, e in enumerate(exemples)):
        report.warnings.append(f"{prefix} : aucun exemple accessible en Free")

    for i, apercu in enumerate(notion.get("apercus") or []):
        if apercu.get("niveau") not in VALID_APERCU_LEVELS:
            report.errors.append(f"{prefix} : apercus[{i}].niveau={apercu.get('niveau')!r} invalide (attendu : {VALID_APERCU_LEVELS})")

    quiz_ids = notion.get("quizExerciseIds") or []
    if not quiz_ids:
        report.warnings.append(f"{prefix} : aucun exercice de mini-quiz (quizExerciseIds vide)")
    elif bank_index is None:
        report.warnings.append(f"{prefix} : banque d'exercices absente — références de quiz non vérifiées")
    else:
        missing = [q for q in quiz_ids if q not in bank_index]
        if missing:
            report.errors.append(
                f"{prefix} : quizExerciseIds référence(nt) des exercices absents de la banque {missing} "
                "(le mini-quiz entier ne s'affichera pas)"
            )
        other = [q for q in quiz_ids if q in bank_index and bank_index[q] != chapter_id]
        if other:
            report.warnings.append(f"{prefix} : exercice(s) de quiz rattaché(s) à un autre chapitre {other}")


def validate_class(profile, chapter: Optional[str] = None, figure_kinds: Optional[frozenset] = None) -> ClassReport:
    """Valide les cours d'un programme (ou d'un seul chapitre)."""
    if profile.id in curriculum_registry.CURRICULUM_REGISTRY:
        status = "publié" if profile.published is True else "prévisualisé"
    else:
        status = "en préparation (non publié)"
    report = ClassReport(class_level=profile.id, status=status)
    courses_dir = profile.courses_dir

    if courses_dir is None or not courses_dir.is_dir() or not any(courses_dir.glob("chapitre_*.json")):
        if profile.published is True:
            report.errors.append(f"courses_dir absent ou vide pour un programme publié — {courses_dir}")
        else:
            report.skipped = "aucun contenu de cours pour l'instant"
        return report

    figure_kinds = figure_kinds if figure_kinds is not None else supported_figure_kinds()
    bank_index = _load_bank_index(profile)
    wanted = _chapter_number(chapter) if chapter is not None else None

    files = sorted(
        (p for p in courses_dir.glob("chapitre_*.json") if _CHAPTER_FILE_RE.match(p.name)),
        key=lambda p: int(_CHAPTER_FILE_RE.match(p.name).group(1)),
    )
    if wanted is not None:
        files = [p for p in files if _CHAPTER_FILE_RE.match(p.name).group(1) == wanted]
        if not files:
            report.errors.append(f"chapitre {wanted} introuvable dans {courses_dir}")
            return report
    selected_names = {p.name for p in files}

    # Règles existantes (schéma, invariants v2, LaTeX brut) : réutilisées
    # telles quelles, jamais réécrites ici.
    schema_errors, _ = validate_cours_schema.validate_all(courses_dir)
    report.errors.extend(e for e in schema_errors if e.split(" ", 1)[0] in selected_names)

    # Les identifiants de notion doivent être uniques dans TOUTE la classe,
    # même quand on ne valide qu'un chapitre.
    seen_ids = {}
    for path in sorted(courses_dir.glob("chapitre_*.json")):
        if path.name in selected_names:
            continue
        try:
            for notion in json.loads(path.read_text(encoding="utf-8")).get("notions", []):
                seen_ids.setdefault(notion.get("id", "?"), path.name)
        except (json.JSONDecodeError, OSError):
            continue

    for path in files:
        try:
            chapter_data = json.loads(path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            continue  # déjà signalé par validate_cours_schema
        report.chapters += 1
        expected_id = f"Chapitre_{_CHAPTER_FILE_RE.match(path.name).group(1)}"
        if chapter_data.get("chapterId") != expected_id:
            report.errors.append(f"{path.name} : chapterId={chapter_data.get('chapterId')!r}, attendu {expected_id!r} (le cours serait introuvable via /api/course-content)")
        title = (chapter_data.get("title") or "").strip()
        if not title:
            report.errors.append(f"{path.name} : titre de chapitre manquant")
        elif _PLACEHOLDER_TITLE_RE.match(title):
            report.warnings.append(f"{path.name} : titre de chapitre de remplissage {title!r}")
        notions = chapter_data.get("notions") or []
        if not notions:
            report.errors.append(f"{path.name} : aucune notion")
        for notion in notions:
            report.notions += 1
            _check_notion(path.name, expected_id, notion, figure_kinds, bank_index, seen_ids, report)

    findings = check_cours_generic_content.audit_dir(courses_dir)
    selected_chapter_ids = {f"Chapitre_{_CHAPTER_FILE_RE.match(n).group(1)}" for n in selected_names}
    for key in ("indice_definition", "generic_intro", "generic_objectif"):
        for label, text in findings[key]:
            if label.split("::", 1)[0] in selected_chapter_ids:
                report.warnings.append(f"{label} : contenu générique ({key}) — {text!r}")
    for label in findings["empty_erreurs"]:
        if label.split("::", 1)[0] in selected_chapter_ids:
            report.warnings.append(f"{label} : erreursFrequentes vide")
    for text, owners in findings["duplicate_definition"]:
        owners_in_scope = [o for o in owners if o.split("::", 1)[0] in selected_chapter_ids]
        if owners_in_scope:
            report.warnings.append(f"définition identique partagée par {owners} — {text!r}")
    return report


def validate(class_levels=None, chapter: Optional[str] = None) -> list[ClassReport]:
    """Un rapport par programme demandé (tous ceux de CURRICULUM_REGISTRY_ALL
    par défaut). Lève KeyError pour un programme inconnu."""
    registry = curriculum_registry.CURRICULUM_REGISTRY_ALL
    ids = list(class_levels) if class_levels else list(registry)
    unknown = [c for c in ids if c not in registry]
    if unknown:
        raise KeyError(f"Programme(s) inconnu(s) du registre : {unknown}")
    figure_kinds = supported_figure_kinds()
    return [validate_class(registry[c], chapter=chapter, figure_kinds=figure_kinds) for c in ids]


def main(argv: list[str]) -> int:
    if len(argv) > 2:
        print("Usage : python -m validate_curriculum_content [classe] [chapitre]")
        return 2
    class_levels = [argv[0]] if argv else None
    chapter = argv[1] if len(argv) == 2 else None
    try:
        reports = validate(class_levels, chapter=chapter)
    except (KeyError, ValueError) as exc:
        print(f"ERREUR : {exc}")
        return 2

    total_errors = 0
    for r in reports:
        print(f"\n=== {r.class_level} — {r.status} ===")
        if r.skipped:
            print(f"  ignoré : {r.skipped}")
            continue
        print(f"  {r.chapters} chapitre(s), {r.notions} notion(s)")
        print(f"  {len(r.errors)} erreur(s) bloquante(s)")
        for e in r.errors:
            print(f"    ✗ {e}")
        print(f"  {len(r.warnings)} avertissement(s) pédagogique(s)")
        for w in r.warnings:
            print(f"    ! {w}")
        total_errors += len(r.errors)
    print(f"\nTOTAL : {total_errors} erreur(s) bloquante(s)")
    return 1 if total_errors else 0


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    raise SystemExit(main(sys.argv[1:]))
