"""
Validateur du schéma des cours Mathadap (static/data/cours/chapitre_*.json).
Deux niveaux de contrôle :

1. Structurel (toutes les notions, migrées ou non) : champs de base présents,
   types corrects — attrape une faute de frappe dans un futur chapitre avant
   qu'elle ne casse silencieusement le frontend (cours.js) ou le chatbot.
2. Invariants KE v2 (notions avec "schemaVersion": 2 uniquement) : les champs
   historiques (`definition`, `methode.etapes`, `erreursFrequentes`) doivent
   rester synchronisés avec leur équivalent enrichi (`definitions.lycee`,
   `methode.etapesParNiveau.normal`, `erreursFrequentesDetail[].description`)
   — cette redondance est nécessaire (le frontend lit le fichier JSON brut,
   voir static/js/cours.js) mais ne doit jamais diverger silencieusement.
   Vérifie aussi l'unicité des ids d'exemples/formules et la validité des
   valeurs de `difficulte` (voir DIFFICULTE_LEVELS, knowledge_engine.py).

Usage : python -m chatbot.validate_cours_schema (depuis webapp/), ou
appelé par une future étape CI avant de committer un chapitre migré.
Ne modifie jamais les fichiers : lecture seule, sort avec un code non nul si
des erreurs sont trouvées.
"""
import json
import re
import sys
from pathlib import Path

from .knowledge_engine import COURS_DIR, DIFFICULTE_LEVELS

REQUIRED_NOTION_FIELDS = ("id", "title", "definition")

# ── Détection de LaTeX brut dans le contenu des cours (chantier "audit LaTeX
# brut", 2026-10-24) — causé par du contenu JSON jamais prévu pour être rendu
# tel quel, pas par le pipeline de rendu (mathrender.js), qui est correct.
# Trois signaux fiables, sans faux positif connu dans ce projet :
#   1. `\og` / `\fg{}` : commandes LaTeX de guillemets français (babel-french),
#      jamais reconnues par KaTeX et jamais entourées de $...$ — toujours une
#      erreur de contenu, aucun usage légitime possible ici.
#   2. Un nombre impair de `$` dans une chaîne : un délimiteur mathématique
#      resté ouvert, donc un texte qui bascule entre LaTeX et texte français
#      au mauvais endroit.
#   3. Des accolades déséquilibrées À L'INTÉRIEUR d'un segment $...$/$$...$$ :
#      KaTeX (throwOnError: false) affiche alors une erreur ou rien du tout.
# Les champs `calcul[].expr` et `figure.relation`/`figure.explication.*` sont
# volontairement inclus : ce sont des chaînes JSON comme les autres, le seul
# traitement spécial (`calcul[].expr` auto-entouré de $...$ par cours.js) ne
# change rien à l'équilibrage interne des accolades ni à la légitimité de
# \og/\fg.
_OG_FG_RE = re.compile(r"\\og\b|\\fg\{?\}?")
_MATH_SEGMENT_RE = re.compile(r"\$\$([^$]+)\$\$|\$([^$]+)\$")


def _braces_balanced(expr):
    depth = 0
    for ch in expr:
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth < 0:
                return False
    return depth == 0


def _scan_string_for_raw_latex(path_desc, value, issues):
    if _OG_FG_RE.search(value):
        issues.append(f"{path_desc} : commande LaTeX « \\og »/« \\fg{{}} » non supportée par KaTeX (jamais de rendu) — {value[:120]!r}")
    if value.count("$") % 2 != 0:
        issues.append(f"{path_desc} : nombre impair de « $ » (délimiteur mathématique non fermé) — {value[:120]!r}")
        return
    for m in _MATH_SEGMENT_RE.finditer(value):
        expr = m.group(1) or m.group(2) or ""
        if not _braces_balanced(expr):
            issues.append(f"{path_desc} : accolades déséquilibrées dans un segment $...$ — {expr[:120]!r}")


def find_raw_latex_issues(notion, prefix):
    """Parcourt récursivement tous les champs texte d'une notion et signale
    tout ce qui s'afficherait comme du LaTeX brut à l'élève (voir les 3
    signaux ci-dessus). Lecture seule, aucun faux positif connu — utilisé par
    validate_all() et par les tests de non-régression (webapp/tests)."""
    issues = []

    def walk(path_desc, v):
        if isinstance(v, str):
            if "\\" in v or "$" in v:
                _scan_string_for_raw_latex(path_desc, v, issues)
        elif isinstance(v, dict):
            for k, vv in v.items():
                walk(f"{path_desc}.{k}", vv)
        elif isinstance(v, list):
            for i, vv in enumerate(v):
                walk(f"{path_desc}[{i}]", vv)

    walk(prefix, notion)
    return issues

# Schéma complet KE v2 (généralisation aux 12 chapitres, migrate_ke_v2.py) :
# chaque notion en schemaVersion 2 doit posséder TOUS ces champs, avec le bon
# type — vide (liste/chaîne vide) est valide, ABSENT ne l'est pas. Uniformité
# du schéma explicitement demandée : mieux vaut un champ vide partout qu'un
# schéma qui varie selon le chapitre.
REQUIRED_V2_LIST_FIELDS = (
    "proprietes", "vocabulaire_associe", "synonymes", "objectifs_pedagogiques",
    "prerequis", "notions_liees", "tags",
)
REQUIRED_V2_STRING_FIELDS = ("difficulte", "topic_id")


def _check_base_structure(chapter_file, notion, errors):
    prefix = f"{chapter_file.name} / notion {notion.get('id', '?')}"
    for field in REQUIRED_NOTION_FIELDS:
        if not notion.get(field):
            errors.append(f"{prefix} : champ requis manquant ou vide « {field} »")

    for ex in notion.get("exemples") or []:
        difficulte = ex.get("difficulte")
        if difficulte is not None and difficulte not in DIFFICULTE_LEVELS:
            errors.append(
                f"{prefix} : exemple « {ex.get('titre')} » a difficulte={difficulte!r}, "
                f"attendu un de {DIFFICULTE_LEVELS}"
            )


def _check_v2_invariants(chapter_file, notion, errors):
    prefix = f"{chapter_file.name} / notion {notion.get('id', '?')}"

    definitions = notion.get("definitions") or {}
    if definitions.get("lycee") and definitions["lycee"] != notion.get("definition"):
        errors.append(f"{prefix} : definitions.lycee ne correspond pas à definition (contenu divergent)")

    methode = notion.get("methode") or {}
    par_niveau = methode.get("etapesParNiveau") or {}
    if par_niveau.get("normal") is not None and par_niveau["normal"] != methode.get("etapes"):
        errors.append(f"{prefix} : methode.etapesParNiveau.normal ne correspond pas à methode.etapes")

    erreurs = notion.get("erreursFrequentes") or []
    erreurs_detail = notion.get("erreursFrequentesDetail") or []
    if erreurs_detail:
        if len(erreurs_detail) != len(erreurs):
            errors.append(f"{prefix} : erreursFrequentesDetail ({len(erreurs_detail)}) et erreursFrequentes ({len(erreurs)}) n'ont pas la même longueur")
        else:
            for i, (texte, detail) in enumerate(zip(erreurs, erreurs_detail)):
                if detail.get("description") != texte:
                    errors.append(f"{prefix} : erreursFrequentesDetail[{i}].description ne correspond pas à erreursFrequentes[{i}]")

    seen_ids = set()
    for kind in ("exemples", "formules"):
        for item in notion.get(kind) or []:
            item_id = item.get("id")
            if not item_id:
                errors.append(f"{prefix} : un élément de « {kind} » n'a pas d'id (requis en schemaVersion 2)")
                continue
            if item_id in seen_ids:
                errors.append(f"{prefix} : id dupliqué « {item_id }» dans la notion")
            seen_ids.add(item_id)

    # Schéma complet : tous les champs doivent être PRÉSENTS (vides tolérés,
    # absents non) et du bon type.
    for field in REQUIRED_V2_LIST_FIELDS:
        if field not in notion:
            errors.append(f"{prefix} : champ KE v2 manquant « {field} » (schemaVersion 2 exige la structure, même vide)")
        elif not isinstance(notion[field], list):
            errors.append(f"{prefix} : « {field} » doit être une liste, reçu {type(notion[field]).__name__}")

    for field in REQUIRED_V2_STRING_FIELDS:
        if field not in notion:
            errors.append(f"{prefix} : champ KE v2 manquant « {field} »")
        elif not isinstance(notion[field], str):
            errors.append(f"{prefix} : « {field} » doit être une chaîne, reçu {type(notion[field]).__name__}")

    if notion.get("difficulte") and notion["difficulte"] not in DIFFICULTE_LEVELS:
        errors.append(f"{prefix} : difficulte={notion['difficulte']!r} invalide, attendu un de {DIFFICULTE_LEVELS} ou vide")

    if "topic_id" in notion and notion["topic_id"] != notion.get("id"):
        errors.append(f"{prefix} : topic_id ({notion['topic_id']!r}) doit toujours être identique à id ({notion.get('id')!r})")


def validate_all(cours_dir=None):
    cours_dir = Path(cours_dir) if cours_dir else COURS_DIR
    errors = []
    chapter_count = notion_count = v2_count = 0
    for chapter_file in sorted(cours_dir.glob("chapitre_*.json")):
        chapter_count += 1
        try:
            chapter = json.loads(chapter_file.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError) as exc:
            errors.append(f"{chapter_file.name} : JSON invalide ({exc})")
            continue
        for notion in chapter.get("notions", []):
            notion_count += 1
            _check_base_structure(chapter_file, notion, errors)
            errors.extend(find_raw_latex_issues(notion, f"{chapter_file.name} / notion {notion.get('id', '?')}"))
            if notion.get("schemaVersion") == 2:
                v2_count += 1
                _check_v2_invariants(chapter_file, notion, errors)
    return errors, {"chapters": chapter_count, "notions": notion_count, "schema_v2_notions": v2_count}


if __name__ == "__main__":
    errors, stats = validate_all()
    print(f"{stats['chapters']} chapitres, {stats['notions']} notions ({stats['schema_v2_notions']} en schemaVersion 2)")
    if errors:
        print(f"\n{len(errors)} erreur(s) :")
        for e in errors:
            print(f"  - {e}")
        sys.exit(1)
    print("Aucune erreur.")
