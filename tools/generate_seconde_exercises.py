"""Régénère exercises_generated_seconde.json à partir des moteurs symboliques
déclarés dans webapp/exercise_generator_seconde/ (droites, signes).

Même principe que tools/generate_derivative_exercises.py (Première) : un
pool structurellement diversifié et mathématiquement correct par
construction (sympy), consommé ADDITIVEMENT par curriculum_registry.py +
server.py via `CurriculumProfile.generated_exercise_bank`, sans changer
exercises_bank.json ni aucun contrat d'API existant.

Chaque module a un GENERATED_ID_OFFSET distinct (800_000 pour droites.py,
810_000 pour signes.py) — jamais de collision d'id entre pools, même après
concaténation, et distincts de exercises_generated_premiere.json (900_000+).

Usage : python -m tools.generate_seconde_exercises [--per-family-droites N] [--per-family-signes N]
"""
import argparse
import json
import sys
from collections import Counter
from pathlib import Path
from statistics import mean

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "webapp"))

from exercise_generator_seconde import droites, signes  # noqa: E402

OUTPUT_PATH = ROOT / "exercises_generated_seconde.json"

MODULES = (
    ("droites", droites, 20260830),
    ("signes", signes, 20260831),
)


def _check_family_calibration(pool: list[dict], module_name: str) -> list[str]:
    """Garde-fou : la difficulté réelle moyenne doit croître avec le niveau
    déclaré de la famille (même contrôle que pour Première)."""
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
    parser.add_argument("--per-family-droites", type=int, default=7,
                         help="Nombre d'exercices générés par famille pour droites.py.")
    parser.add_argument("--per-family-signes", type=int, default=9,
                         help="Nombre d'exercices générés par famille pour signes.py.")
    args = parser.parse_args()

    per_family = {"droites": args.per_family_droites, "signes": args.per_family_signes}

    combined: list[dict] = []
    all_problems: list[str] = []
    per_module_counts: dict[str, int] = {}

    for name, module, seed in MODULES:
        pool = module.generate_pool(per_family=per_family[name], seed=seed)
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
