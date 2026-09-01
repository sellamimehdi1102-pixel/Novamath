"""Régénère exercises_generated_troisieme.json à partir de TOUS les moteurs
symboliques déclarés dans webapp/exercise_generator_troisieme/ (pendant de
tools/generate_derivative_exercises.py pour Première).

── RÈGLE ABSOLUE — mission "rééquilibrage global de toutes les classes"
(2026-09-01), même contrat que tools/generate_derivative_exercises.py ────
Ce script ne doit JAMAIS faire disparaître un exercice déjà généré. Trois
niveaux :

1. BASELINE (`_BASELINE_MODULES`) — les 8 modules historiques (Chapitre_1/3/
   4/5/7/8) sont TOUJOURS régénérés avec leurs per_family/seed d'origine :
   reproduit bit pour bit le pool historique (246 exercices, vérifié).

2. EXTENSION (`_EXTENSION_MODULES`) — Chapitre_4 (developper_distributivite,
   factoriser_somme) et Chapitre_5 (equation_premier_degre) restent sous la
   cible d'équilibrage même avec la baseline : extension ADDITIVE (seed
   distinct, dédupliquée contre la baseline, IDs à partir de
   GENERATED_ID_OFFSET + 5000).

3. NOUVEAUX MODULES (`_NEW_MODULES`) — nombres_relatifs (Chapitre_2),
   proportionnalite (Chapitre_6), statistiques (Chapitre_9),
   probabilites_troisieme (Chapitre_10), thales (Chapitre_14) : ces 5
   chapitres n'avaient AUCUN générateur avant cette mission.

Chapitre_1/3/7/8/11/12/13/15 restent au niveau de leur banque curée +
baseline (déjà ≥150, pas de générateur nécessaire pour respecter le ratio
cible — voir rapport de mission).

Usage : python -m tools.generate_troisieme_exercises
"""
import json
import sys
from collections import Counter
from pathlib import Path
from statistics import mean

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "webapp"))

from exercise_generator_troisieme import (  # noqa: E402
    developper_distributivite, divisibilite, equation_premier_degre, factoriser_somme,
    fonction_affine_deux_points, fractions_addition, fractions_simplification, image_fonction,
    nombres_relatifs, probabilites_troisieme, proportionnalite, statistiques, thales,
)

OUTPUT_PATH = ROOT / "exercises_generated_troisieme.json"

# (nom, module, per_family_origine, seed_origine) — jamais modifié.
_BASELINE_MODULES = (
    ("equation_premier_degre", equation_premier_degre, 6, 30260101),
    ("divisibilite", divisibilite, 6, 30260102),
    ("fractions_addition", fractions_addition, 6, 30260103),
    ("fractions_simplification", fractions_simplification, 7, 30260104),
    ("fonction_affine_deux_points", fonction_affine_deux_points, 7, 30260105),
    ("developper_distributivite", developper_distributivite, 6, 30260106),
    ("factoriser_somme", factoriser_somme, 7, 30260107),
    ("image_fonction", image_fonction, 6, 30260108),
)

# (nom, module, seed_extension, per_family_large, n_extra_cible)
_EXTENSION_MODULES = (
    ("equation_premier_degre", equation_premier_degre, 930260101, 30, 45),
    ("developper_distributivite", developper_distributivite, 930260106, 20, 15),
    ("factoriser_somme", factoriser_somme, 930260107, 20, 15),
)

# Chapitre_2/6/9/10/14 : générateurs entièrement nouveaux.
_NEW_MODULES = (
    ("nombres_relatifs", nombres_relatifs, 30260301, 9),
    ("proportionnalite", proportionnalite, 30260302, 15),
    ("statistiques", statistiques, 30260303, 13),
    ("probabilites_troisieme", probabilites_troisieme, 30260304, 11),
    ("thales", thales, 30260305, 15),
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


def _build_extension(module, seed_extension: int, per_family_large: int, n_extra: int,
                      baseline_enonces: set[str]) -> list[dict]:
    """Voir tools/generate_derivative_exercises.py::_build_extension — même
    contrat : seed distinct, dédupliqué contre la baseline, IDs à partir de
    GENERATED_ID_OFFSET + 5000 (jamais dans la plage déjà utilisée)."""
    raw = module.generate_pool(per_family=per_family_large, seed=seed_extension)
    seen = set(baseline_enonces)
    survivors = []
    for ex in raw:
        if ex["enonce"] in seen:
            continue
        seen.add(ex["enonce"])
        survivors.append(ex)
        if len(survivors) >= n_extra:
            break
    offset = module.GENERATED_ID_OFFSET + 5000
    for i, ex in enumerate(survivors):
        ex["id"] = offset + i
    return survivors


def main() -> None:
    combined: list[dict] = []
    all_problems: list[str] = []
    per_module_counts: dict[str, int] = {}
    baseline_enonces_by_module: dict[str, set[str]] = {}

    for name, module, per_family, seed in _BASELINE_MODULES:
        pool = module.generate_pool(per_family=per_family, seed=seed)
        all_problems.extend(_check_family_calibration(pool, name))
        per_module_counts[name] = len(pool)
        baseline_enonces_by_module.setdefault(name, set()).update(e["enonce"] for e in pool)
        combined.extend(pool)

    for name, module, seed_ext, per_family_large, n_extra in _EXTENSION_MODULES:
        extra_pool = _build_extension(module, seed_ext, per_family_large, n_extra,
                                       baseline_enonces_by_module.get(name, set()))
        all_problems.extend(_check_family_calibration(extra_pool, f"{name} (extension)"))
        per_module_counts[f"{name} (extension)"] = len(extra_pool)
        combined.extend(extra_pool)

    for name, module, seed, per_family in _NEW_MODULES:
        pool = module.generate_pool(per_family=per_family, seed=seed)
        all_problems.extend(_check_family_calibration(pool, name))
        per_module_counts[name] = len(pool)
        combined.extend(pool)

    ids = [ex["id"] for ex in combined]
    if len(ids) != len(set(ids)):
        dupes = sorted({i for i in ids if ids.count(i) > 1})
        print(f"ERREUR — collision d'id entre pools générés : {dupes[:10]}", file=sys.stderr)
        sys.exit(1)

    enonces = [ex["enonce"] for ex in combined]
    if len(enonces) != len(set(enonces)):
        dup_enonces = len(enonces) - len(set(enonces))
        print(f"ERREUR — {dup_enonces} doublon(s) d'énoncé détecté(s) entre pools", file=sys.stderr)
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
