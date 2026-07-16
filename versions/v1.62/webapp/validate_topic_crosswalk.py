"""
Valide static/data/topic_crosswalk.json contre les deux sources qu'il relie :
- exercises_bank.json (chapter_id/notion en texte libre) : chaque paire réellement
  présente dans la banque doit avoir une entrée dans la crosswalk (couverture).
- static/data/cours/chapitre_*.json (notions[].id) : chaque topic_id de la
  crosswalk doit exister réellement comme id de notion dans le bon chapitre
  (pas de faute de frappe pointant vers un slug inexistant).

Lecture seule. Sort avec un code non nul si des erreurs sont trouvées.
Usage : python validate_topic_crosswalk.py (depuis webapp/).
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CROSSWALK_PATH = Path(__file__).resolve().parent / "static" / "data" / "topic_crosswalk.json"
COURS_DIR = Path(__file__).resolve().parent / "static" / "data" / "cours"
BANK_PATH = ROOT / "exercises_bank.json"


def validate():
    crosswalk = json.loads(CROSSWALK_PATH.read_text(encoding="utf-8"))
    bank = json.loads(BANK_PATH.read_text(encoding="utf-8"))

    cours_ids_by_chapter = {}
    for path in COURS_DIR.glob("chapitre_*.json"):
        chapter = json.loads(path.read_text(encoding="utf-8"))
        cours_ids_by_chapter[chapter["chapterId"]] = {n["id"] for n in chapter.get("notions", [])}

    errors = []

    # 1. Chaque topic_id de la crosswalk existe réellement dans le bon chapitre.
    for chapter_id, labels in crosswalk.items():
        real_ids = cours_ids_by_chapter.get(chapter_id, set())
        for label, topic_id in labels.items():
            if topic_id not in real_ids:
                errors.append(
                    f"crosswalk[{chapter_id}][{label!r}] -> {topic_id!r} : "
                    f"cet id n'existe pas dans chapitre_{chapter_id.split('_')[1]}.json"
                )

    # 2. Chaque paire (chapter_id, notion texte) réellement utilisée dans
    #    exercises_bank.json est couverte par la crosswalk.
    bank_pairs = {(e["chapter_id"], e["notion"]) for e in bank}
    for chapter_id, label in sorted(bank_pairs):
        if label not in crosswalk.get(chapter_id, {}):
            errors.append(f"exercises_bank.json utilise ({chapter_id}, {label!r}) sans entrée dans la crosswalk")

    # 3. Signalement (pas une erreur) : notions de cours jamais référencées
    #    par un exercice — utile pour prioriser l'ajout d'exercices, pas un bug.
    warnings = []
    crosswalk_topic_ids = {
        (chapter_id, topic_id) for chapter_id, labels in crosswalk.items() for topic_id in labels.values()
    }
    for chapter_id, real_ids in cours_ids_by_chapter.items():
        for topic_id in real_ids:
            if (chapter_id, topic_id) not in crosswalk_topic_ids:
                warnings.append(f"{chapter_id} / {topic_id} : aucun exercice de la banque ne référence cette notion")

    return errors, warnings, {"chapters": len(crosswalk), "entries": sum(len(v) for v in crosswalk.values())}


if __name__ == "__main__":
    errors, warnings, stats = validate()
    print(f"{stats['chapters']} chapitres, {stats['entries']} entrées dans la crosswalk")
    if warnings:
        print(f"\n{len(warnings)} avertissement(s) (notions sans exercice) :")
        for w in warnings:
            print(f"  - {w}")
    if errors:
        print(f"\n{len(errors)} erreur(s) :")
        for e in errors:
            print(f"  - {e}")
        sys.exit(1)
    print("\nAucune erreur.")
