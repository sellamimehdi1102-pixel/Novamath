"""
Validateur du schéma des cours NovaMath (static/data/cours/chapitre_*.json).
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
import sys
from pathlib import Path

from .knowledge_engine import COURS_DIR, DIFFICULTE_LEVELS

REQUIRED_NOTION_FIELDS = ("id", "title", "definition")

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
