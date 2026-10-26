"""Écrit les cours de Quatrième (course_content/cours_quatrieme/chapitre_N.json)
à partir des modules tools/quatrieme/cours_chNN.py.

Chaque module expose CHAPTER (dictionnaire construit par
quatrieme.cours_commun.chapter). Le chapitre 8 (Pythagore, chapitre pilote)
n'est pas concerné : son JSON est la source historique.

Usage : python tools/build_quatrieme_courses.py [numéro ...]
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))

from quatrieme.chapitres import modules  # noqa: E402

OUT_DIR = ROOT / "webapp" / "course_content" / "cours_quatrieme"


def main(argv) -> int:
    wanted = {int(a) for a in argv}
    written = 0
    for number, cours, _banque in modules():
        if wanted and number not in wanted:
            continue
        chapter = cours.CHAPTER
        assert chapter["chapterId"] == f"Chapitre_{number}", chapter["chapterId"]
        path = OUT_DIR / f"chapitre_{number}.json"
        path.write_text(json.dumps(chapter, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(f"OK — {path.name} : {chapter['title']} ({len(chapter['notions'])} notions)")
        written += 1
    if not written:
        print("Aucun chapitre écrit.")
    return 0


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    raise SystemExit(main(sys.argv[1:]))
