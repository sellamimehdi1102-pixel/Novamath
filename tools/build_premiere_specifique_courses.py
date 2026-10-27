"""Écrit les cours de la classe « Première spécifique » (course_content/cours_premiere_specifique/chapitre_N.json)
à partir des modules tools/premiere_specifique/cours_chNN.py (voir premiere_specifique/chapitres.py).
N'écrit jamais dans la Première historique (cours_premiere/).

Garde-fou (adaptation au manuel « Première ES/L », 2026-10-26 : les notions
changent de chapitre) : vérification GLOBALE — un identifiant de notion
présent dans les JSON actuels ne peut disparaître de la classe que s'il est
déclaré dans `NOTIONS_RETIREES` d'un module de cours, ou s'il appartient à
un chapitre mis en réserve (chapitres.RESERVE). Sinon rien n'est écrit.

Sans argument, tous les chapitres sont écrits et les fichiers chapitre_N.json
qui ne correspondent plus à aucun chapitre sont listés (jamais supprimés
automatiquement). Avec des numéros, seuls ces chapitres sont écrits.

Usage : python tools/build_premiere_specifique_courses.py [numéro ...]
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))

from premiere_specifique.chapitres import modules, reserve_modules  # noqa: E402

OUT_DIR = ROOT / "webapp" / "course_content" / "cours_premiere_specifique"


def main(argv) -> int:
    wanted = {int(a) for a in argv}
    chapters = modules()
    problems = []
    for number, cours, _banque in chapters:
        chapter = cours.CHAPTER
        if chapter["chapterId"] != f"Chapitre_{number}":
            problems.append(f"{cours.__name__} : chapterId {chapter['chapterId']} au lieu de Chapitre_{number}")

    # Garde-fou global sur les identifiants de notions.
    old_ids = set()
    for path in OUT_DIR.glob("chapitre_*.json"):
        old_ids |= {n["id"] for n in json.loads(path.read_text(encoding="utf-8"))["notions"]}
    new_ids = {n["id"] for _n, cours, _b in chapters for n in cours.CHAPTER["notions"]}
    declared = set()
    for _n, cours, _b in chapters:
        declared |= set(getattr(cours, "NOTIONS_RETIREES", {}))
    for _n, cours, _b in reserve_modules():
        declared |= {n["id"] for n in cours.CHAPTER["notions"]} | set(getattr(cours, "NOTIONS_RETIREES", {}))
    lost = old_ids - new_ids - declared
    if lost:
        problems.append(f"notions supprimées sans justification : {sorted(lost)}")
    if problems:
        for p in problems:
            print("ERREUR —", p, file=sys.stderr)
        return 1

    written = 0
    for number, cours, _banque in chapters:
        if wanted and number not in wanted:
            continue
        path = OUT_DIR / f"chapitre_{number}.json"
        path.write_text(json.dumps(cours.CHAPTER, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(f"OK — {path.name} : {cours.CHAPTER['title']} ({len(cours.CHAPTER['notions'])} notions)")
        written += 1
    if not wanted:
        stale = sorted(p.name for p in OUT_DIR.glob("chapitre_*.json")
                       if int(p.stem.split("_")[1]) not in {n for n, _c, _b in chapters})
        if stale:
            print("Fichiers hors curriculum (à retirer manuellement après sauvegarde) :", ", ".join(stale))
    if not written:
        print("Aucun chapitre écrit.")
    return 0


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    raise SystemExit(main(sys.argv[1:]))
