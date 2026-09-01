"""Régénère exercises_generated_premiere.json à partir de TOUS les moteurs
symboliques déclarés dans webapp/exercise_generator/ (derivatives, suites,
exponentielle, variations, second_degre, tangente).

Contrairement à tools/legacy-pipeline/ (LLM, mort, contenu figé une fois
pour toutes), ces moteurs sont de vrais générateurs re-régénérables : relancer
produit un pool structurellement diversifié et mathématiquement correct par
construction (sympy). Le résultat reste un fichier JSON statique unique,
consommé additivement par curriculum_registry.py + server.py, pour ne changer
aucun contrat d'API existant (mêmes champs qu'un exercice de banque classique
: enonce/answer/hint/solution_steps/chapter_id/notion/difficulty).

Chaque module a un GENERATED_ID_OFFSET distinct (900_000/910_000/920_000/
930_000/940_000/950_000) fixé dans son propre fichier — jamais de collision
d'id entre pools, même après concaténation. Les familles compo_* de
derivatives.py (Phase 5, notion "Composition de fonctions et dérivation")
restent dans l'offset 900_000 du module derivatives : elles n'ont pas leur
propre offset, generate_pool() les inclut déjà dans son pool combiné.

── Rééquilibrage inter-chapitres (mission "rééquilibrage global", 2026-09-01)
────────────────────────────────────────────────────────────────────────────
Avant ce chantier, --per-family s'appliquait uniformément à TOUS les modules
(défaut 12), sans tenir compte du nombre de familles par module ni du volume
déjà présent dans exercises_bank_premiere.json (banque curée, jamais
modifiée). Or Chapitre_3 (derivatives: 24 familles + tangente: 9 familles =
33) et Chapitre_1/5 (suites: 30, exponentielle: 34) ont beaucoup plus de
familles que Chapitre_2/4 (second_degre/variations : 11 chacun) : à
per_family égal, ils recevaient mécaniquement 2 à 3× plus d'exercices
générés, ce qui, cumulé à une banque curée elle-même déjà inégale par
chapitre, produisait un écart extrême (jusqu'à ratio 12,6 entre Chapitre_3 et
Chapitre_10 en Première — voir rapport de mission).
Chapitre_6 à Chapitre_10 (trigonométrie, vecteurs, géométrie repère,
probabilités) n'ont ENCORE aucun module générateur : leur volume reste donc
plafonné à ce que contient exercises_bank_premiere.json (banque curée),
impossible à augmenter sans écrire de nouveaux générateurs symboliques —
hors périmètre de cette correction (voir rapport de mission, anomalie
documentée). PER_FAMILY_BY_MODULE ci-dessous a été calibré (voir
tools/audit_exercise_taxonomy.py, invoqué sans écriture, pour les comptages)
pour que Chapitre_1 à Chapitre_5 (les seuls que ce script peut influencer)
convergent vers un total proche les uns des autres (~223-245 exercices
chacun, banque curée incluse) plutôt que de laisser un chapitre dépasser les
autres d'un facteur 2 à 4 comme avant. --per-family (CLI) reste disponible
pour forcer une valeur UNIFORME (utile en test/débogage) ; par défaut, chaque
module utilise sa propre valeur calibrée.

Usage : python -m tools.generate_derivative_exercises [--per-family N]
"""
import argparse
import json
import sys
from collections import Counter
from pathlib import Path
from statistics import mean

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "webapp"))

from exercise_generator import (  # noqa: E402
    derivatives, exponentielle, second_degre, suites, tangente, variations,
)

OUTPUT_PATH = ROOT / "exercises_generated_premiere.json"

# Chaque module expose generate_pool(per_family=..., seed=...) — même contrat,
# seed distincte par module pour ne jamais partager le même flux aléatoire.
# Le 4e élément (per_family calibré) remplace l'ancien défaut uniforme (12) —
# voir le commentaire de rééquilibrage ci-dessus pour la méthode de calcul.
MODULES = (
    ("derivatives", derivatives, 20260818, 2),
    ("suites", suites, 20260820, 6),
    ("exponentielle", exponentielle, 20260821, 6),
    ("variations", variations, 20260822, 19),
    ("second_degre", second_degre, 20260823, 7),
    ("tangente", tangente, 20260824, 2),
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


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--per-family", type=int, default=None,
                         help="Force un nombre UNIFORME d'exercices générés par famille pour "
                              "tous les modules (débogage/test) ; par défaut, chaque module "
                              "utilise sa propre valeur calibrée dans MODULES pour équilibrer "
                              "le nombre d'exercices entre chapitres (voir docstring).")
    args = parser.parse_args()

    combined: list[dict] = []
    all_problems: list[str] = []
    per_module_counts: dict[str, int] = {}

    for name, module, seed, calibrated_per_family in MODULES:
        per_family = args.per_family if args.per_family is not None else calibrated_per_family
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
