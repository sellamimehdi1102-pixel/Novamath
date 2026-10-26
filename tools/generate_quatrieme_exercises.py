"""Régénère exercises_generated_quatrieme.json à partir des moteurs
symboliques de webapp/exercise_generator_quatrieme/ (pendant de
tools/generate_troisieme_exercises.py).

Chantier "Quatrième — chapitre pilote Pythagore" (2026-10-24) : un seul
module (pythagore, Chapitre_8). Le pool est DÉTERMINISTE (seed fixe) : le
relancer reproduit bit pour bit le même fichier, donc les mêmes
identifiants. Les mini-quiz ne référencent jamais ce pool (uniquement des
exercices curés de exercises_bank_quatrieme.json, identifiants écrits en
dur) : une évolution future d'un générateur ne peut pas casser un quiz.

Garde-fous (fichier non écrit si l'un échoue) :
- identifiants uniques et dans le bloc réservé du module ;
- aucun énoncé en double, ni avec la banque curée ;
- difficulté réelle croissante avec le niveau déclaré des familles.

Usage : python tools/generate_quatrieme_exercises.py
"""
import json
import sys
from collections import Counter
from pathlib import Path
from statistics import mean

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "webapp"))

from exercise_generator_quatrieme import pythagore, relatifs, fractions_sommes, fractions_produits, arithmetique, puissances, calcul_litteral, equations, proportionnalite_grandeurs, thales_emboites, cosinus, triangles_egaux, translations_plan, espace_volumes, notion_fonction, statistiques_quatrieme, probabilites_quatrieme  # noqa: E402

OUTPUT_PATH = ROOT / "exercises_generated_quatrieme.json"
CURATED_PATH = ROOT / "exercises_bank_quatrieme.json"

# (nom, module, per_family, seed) — figé dès la première écriture : changer
# un de ces paramètres change les identifiants servis.
MODULES = (
    ("pythagore", pythagore, 25, 40080001),
    ("relatifs", relatifs, 25, 40010001),
    ("fractions_sommes", fractions_sommes, 25, 40020001),
    ("fractions_produits", fractions_produits, 25, 40030001),
    ("arithmetique", arithmetique, 25, 40040001),
    ("puissances", puissances, 25, 40050001),
    ("calcul_litteral", calcul_litteral, 25, 40060001),
    ("equations", equations, 25, 40070001),
    ("proportionnalite_grandeurs", proportionnalite_grandeurs, 25, 40140001),
    ("thales_emboites", thales_emboites, 25, 40090001),
    ("cosinus", cosinus, 25, 40100001),
    ("triangles_egaux", triangles_egaux, 25, 40120001),
    ("translations_plan", translations_plan, 25, 40110001),
    ("espace_volumes", espace_volumes, 25, 40130001),
    ("notion_fonction", notion_fonction, 25, 40150001),
    ("statistiques_quatrieme", statistiques_quatrieme, 25, 40160001),
    ("probabilites_quatrieme", probabilites_quatrieme, 25, 40170001),
)


def build_pool() -> tuple[list[dict], list[str]]:
    problems: list[str] = []
    combined: list[dict] = []
    for name, module, per_family, seed in MODULES:
        pool = module.generate_pool(per_family=per_family, seed=seed)
        lo, hi = module.GENERATED_ID_OFFSET, module.GENERATED_ID_OFFSET + 10_000
        if any(not (lo <= ex["id"] < hi) for ex in pool):
            problems.append(f"[{name}] identifiant hors du bloc {lo}–{hi - 1}")
        by_level: dict[int, list[float]] = {}
        for ex in pool:
            by_level.setdefault(ex["declared_level"], []).append(ex["complexity_score"])
        avgs = [mean(by_level[lvl]) for lvl in sorted(by_level)]
        if avgs != sorted(avgs):
            problems.append(f"[{name}] difficulté réelle non croissante avec le niveau déclaré")
        combined.extend(pool)

    ids = [ex["id"] for ex in combined]
    if len(ids) != len(set(ids)):
        problems.append("collision d'identifiants entre pools générés")
    enonces = [ex["enonce"] for ex in combined]
    if len(enonces) != len(set(enonces)):
        problems.append("énoncés dupliqués dans le pool généré")
    if CURATED_PATH.exists():
        curated = json.loads(CURATED_PATH.read_text(encoding="utf-8"))
        curated_ids = {e["id"] for e in curated}
        if curated_ids & set(ids):
            problems.append("identifiant commun avec la banque curée")
        if {e["enonce"] for e in curated} & set(enonces):
            problems.append("énoncé identique à un exercice de la banque curée")
    return combined, problems


def main() -> int:
    combined, problems = build_pool()
    if problems:
        print("ERREUR — pool non écrit :", file=sys.stderr)
        for p in problems:
            print(f"  - {p}", file=sys.stderr)
        return 1
    OUTPUT_PATH.write_text(json.dumps(combined, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"OK — {len(combined)} exercices générés -> {OUTPUT_PATH}")
    for family, count in Counter(ex["family"] for ex in combined).items():
        print(f"  {family}: {count}")
    print(f"  Répartition par difficulté : {dict(sorted(Counter(ex['difficulty'] for ex in combined).items()))}")
    return 0


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    raise SystemExit(main())
