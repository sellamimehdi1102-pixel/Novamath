"""Régénère exercises_generated_premiere.json à partir de TOUS les moteurs
symboliques déclarés dans webapp/exercise_generator/ (derivatives, suites,
exponentielle, variations, second_degre, tangente, et les 5 nouveaux modules
trigonometrie/produit_scalaire/geometrie_reperee/
probabilites_conditionnelles/variables_aleatoires — chapitres 6 à 10).

Chaque module a un GENERATED_ID_OFFSET distinct (900_000 à 1_000_000 par pas
de 10_000) fixé dans son propre fichier — jamais de collision d'id entre
pools, même après concaténation.

── RÈGLE ABSOLUE — mission "rééquilibrage additif" (2026-09-01) ────────────
Ce script ne DOIT JAMAIS faire disparaître un exercice déjà généré
précédemment (ancienne règle violée par une mission antérieure, qui avait
réduit --per-family pour "équilibrer" et fait chuter le total Première de
2217 à 1547 — explicitement interdit désormais). Le seul mode d'équilibrage
autorisé est ADDITIF :

1. BASELINE (`_BASELINE_MODULES`) — les 6 modules historiques (Chapitre_1 à
   5) sont TOUJOURS régénérés avec leur per_family ORIGINAL (12, seed
   d'origine) : reproduit bit pour bit le pool historique (1402 exercices,
   vérifié par tests/test_exercise_regeneration_additive.py), jamais réduit.

2. EXTENSION (`_EXTENSION_MODULES`) — pour les chapitres dont la baseline
   seule reste sous la cible d'équilibrage (Chapitre_2/second_degre,
   Chapitre_4/variations), on génère un pool supplémentaire avec un SEED
   DIFFÉRENT, on écarte tout exercice dont l'énoncé existe déjà dans la
   baseline (déduplication stricte), puis on numérote les survivants à
   partir de GENERATED_ID_OFFSET + 5000 (jamais dans la plage 0-999 déjà
   utilisée par la baseline du même module) — donc toujours un AJOUT, jamais
   un remplacement.

3. NOUVEAUX MODULES (`_NEW_MODULES`) — trigonometrie/produit_scalaire/
   geometrie_reperee/probabilites_conditionnelles/variables_aleatoires
   couvrent Chapitre_6 à Chapitre_10, qui n'avaient AUCUN générateur avant
   cette mission : leur pool entier est nouveau, aucune notion de baseline à
   préserver.

Usage : python -m tools.generate_derivative_exercises
(le flag --per-family historique a été retiré : le calibrage par module est
désormais un contrat figé, voir ci-dessus — le forcer uniformément
réintroduirait le bug de la mission précédente.)
"""
import json
import sys
from collections import Counter
from pathlib import Path
from statistics import mean

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "webapp"))

from exercise_generator import (  # noqa: E402
    derivatives, exponentielle, geometrie_reperee, probabilites_conditionnelles,
    produit_scalaire, second_degre, suites, tangente, trigonometrie, variables_aleatoires,
    variations,
)

OUTPUT_PATH = ROOT / "exercises_generated_premiere.json"

# Chapitre_1 à Chapitre_5 : per_family ORIGINAL (12), seeds d'origine —
# jamais modifié, reproduit exactement le pool historique. Voir règle 1.
_BASELINE_MODULES = (
    ("derivatives", derivatives, 20260818, 12),
    ("suites", suites, 20260820, 12),
    ("exponentielle", exponentielle, 20260821, 12),
    ("variations", variations, 20260822, 12),
    ("second_degre", second_degre, 20260823, 12),
    ("tangente", tangente, 20260824, 12),
)

# Chapitre_2 (second_degre) et Chapitre_4 (variations) restent sous la cible
# d'équilibrage (~300) même avec leur banque curée + baseline ci-dessus —
# extension ADDITIVE : nouveau seed, dédupliquée contre la baseline, jamais
# de remplacement. Voir règle 2. (module, seed_extension, per_family_large,
# n_extra_cible)
_EXTENSION_MODULES = (
    ("second_degre", second_degre, 920260823, 40, 22),
    ("variations", variations, 920260822, 60, 154),
)

# Chapitre_6 à Chapitre_10 : générateurs entièrement nouveaux (mission
# "rééquilibrage additif", 2026-09-01) — voir règle 3.
_NEW_MODULES = (
    ("trigonometrie", trigonometrie, 20260901, 205),
    ("produit_scalaire", produit_scalaire, 20260902, 38),
    ("geometrie_reperee", geometrie_reperee, 20260903, 35),
    ("probabilites_conditionnelles", probabilites_conditionnelles, 20260904, 45),
    ("variables_aleatoires", variables_aleatoires, 20260905, 60),
)


def _check_family_calibration(pool: list[dict], module_name: str) -> list[str]:
    """Vérifie que la difficulté réelle moyenne croît avec le niveau déclaré
    de la famille — garde-fou contre une famille "difficile" qui génèrerait
    en réalité des exercices triviaux."""
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
    """Génère un pool supplémentaire (seed distinct de la baseline), écarte
    tout exercice dont l'énoncé existe déjà dans la baseline (même module),
    puis renumérote les survivants à partir de
    GENERATED_ID_OFFSET + 5000 — jamais dans la plage déjà utilisée par la
    baseline (0 à per_family_baseline*n_familles-1), donc toujours un AJOUT."""
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

    for name, module, seed, per_family in _BASELINE_MODULES:
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

    # Collision d'id : garde-fou explicite (ne devrait jamais se déclencher
    # tant que les GENERATED_ID_OFFSET restent distincts et suffisamment
    # espacés — voir docstring de chaque module).
    ids = [ex["id"] for ex in combined]
    if len(ids) != len(set(ids)):
        dupes = sorted({i for i in ids if ids.count(i) > 1})
        print(f"ERREUR — collision d'id entre pools générés : {dupes[:10]}", file=sys.stderr)
        sys.exit(1)

    # Doublon d'énoncé entre pools distincts (garde-fou global, en plus de la
    # déduplication déjà faite à l'intérieur de chaque generate_pool et de
    # _build_extension) : ne devrait jamais se déclencher, mais bloque
    # l'écriture plutôt que de laisser passer un doublon silencieux.
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
