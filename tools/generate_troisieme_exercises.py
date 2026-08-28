"""Régénère exercises_generated_troisieme.json à partir de TOUS les moteurs
symboliques déclarés dans webapp/exercise_generator_troisieme/ (pendant de
tools/generate_derivative_exercises.py pour Première).

Chaque module couvre une notion de Chapitre_1/3/4/5/7/8 (voir docstring de
chaque module) et déclare son propre GENERATED_ID_OFFSET (100_000, 110_000,
... 170_000), distinct des offsets 900_000+ utilisés par
webapp/exercise_generator/ (Première) — les deux pools ne sont jamais
fusionnés dans le même fichier, mais la distinction reste documentée pour
éviter toute confusion en cas de futur besoin de fusion.

Usage : python -m tools.generate_troisieme_exercises [--per-family N]
"""
import argparse
import json
import sys
from collections import Counter
from pathlib import Path
from statistics import mean

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "webapp"))

from exercise_generator_troisieme import (  # noqa: E402
    developper_distributivite, divisibilite, equation_premier_degre,
    factoriser_somme, fonction_affine_deux_points, fractions_addition,
    fractions_simplification, image_fonction,
)

OUTPUT_PATH = ROOT / "exercises_generated_troisieme.json"

MODULES = (
    ("equation_premier_degre", equation_premier_degre, 6, 30260101),
    ("divisibilite", divisibilite, 6, 30260102),
    ("fractions_addition", fractions_addition, 6, 30260103),
    ("fractions_simplification", fractions_simplification, 7, 30260104),
    ("fonction_affine_deux_points", fonction_affine_deux_points, 7, 30260105),
    ("developper_distributivite", developper_distributivite, 6, 30260106),
    ("factoriser_somme", factoriser_somme, 7, 30260107),
    ("image_fonction", image_fonction, 6, 30260108),
)


def _check_family_calibration(pool: list[dict], module_name: str) -> list[str]:
    problems = []
    by_declared_level: dict[int, list[float]] = {}
    for ex in pool:
        by_declared_level.setdefault(ex["declared_level"], []).append(ex["complexity_score"])
    levels = sorted(by_declared_level)
    avgs = [mean(by_declared_level[lvl]) for lvl in levels]
    for i in range(1, len(avgs)):
        if avgs[i] < avgs[i - 1]:
            problems.append(
                f"[{module_name}] Difficulté réelle non croissante : niveau {levels[i]} "
                f"(score moyen {avgs[i]:.2f}) < niveau {levels[i - 1]} (score moyen {avgs[i - 1]:.2f})"
            )
    return problems


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--per-family", type=int, default=None,
                         help="Nombre d'exercices générés par famille, par module (défaut : valeur propre à chaque module).")
    args = parser.parse_args()

    combined: list[dict] = []
    all_problems: list[str] = []
    per_module_counts: dict[str, int] = {}

    for name, module, default_per_family, seed in MODULES:
        per_family = args.per_family or default_per_family
        pool = module.generate_pool(per_family=per_family, seed=seed)
        all_problems.extend(_check_family_calibration(pool, name))
        per_module_counts[name] = len(pool)
        combined.extend(pool)

    ids = [ex["id"] for ex in combined]
    if len(ids) != len(set(ids)):
        dupes = sorted({i for i in ids if ids.count(i) > 1})
        print(f"ERREUR — collision d'id entre pools générés : {dupes[:10]}", file=sys.stderr)
        sys.exit(1)

    if all_problems:
        print("ERREUR — calibration de difficulté incohérente, fichier non écrit :", file=sys.stderr)
        for p in all_problems:
            print(f"  - {p}", file=sys.stderr)
        sys.exit(1)

    OUTPUT_PATH.write_text(
        json.dumps(combined, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    diff_counts = Counter(e["difficulty"] for e in combined)
    print(f"OK — {len(combined)} exercices générés -> {OUTPUT_PATH}")
    for name, count in per_module_counts.items():
        print(f"  {name}: {count} exercices")
    print(f"  Répartition par difficulté réelle : {dict(sorted(diff_counts.items()))}")


if __name__ == "__main__":
    main()
