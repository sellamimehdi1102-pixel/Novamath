"""Régénère exercises_generated_troisieme.json à partir de TOUS les moteurs
symboliques déclarés dans webapp/exercise_generator_troisieme/ (pendant de
tools/generate_derivative_exercises.py pour Première).

── RÈGLE ABSOLUE — missions "rééquilibrage global de toutes les classes"
(2026-09-01) et "équilibrage définitif de toutes les classes" (2026-09-01),
même contrat que tools/generate_derivative_exercises.py ──────────────────
Ce script ne doit JAMAIS faire disparaître un exercice déjà généré :

1. BASELINE (`_BASELINE_MODULES`) — les 8 modules historiques (Chapitre_1/3/
   4/5/7/8) ET les 5 modules créés par la mission "rééquilibrage global"
   (nombres_relatifs/Chapitre_2, proportionnalite/Chapitre_6,
   statistiques/Chapitre_9, probabilites_troisieme/Chapitre_10,
   thales/Chapitre_14, déjà COMMITTÉS/SERVIS) sont TOUJOURS régénérés avec
   leurs per_family/seed d'origine : reproduit bit pour bit le pool en
   production (592 exercices, vérifié avant toute modification). Rejoint
   également volumes_espace (Chapitre_15, nouveau — voir point 3).

2. EXTENSION (`_EXTENSION_MODULES`) — Chapitre_2/4/5/6/9/10/14 restent sous
   la cible d'équilibrage (ratio ≤1,5 par rapport à Chapitre_7=242) même
   avec la baseline : extension ADDITIVE (seed distinct de la baseline ET
   de toute extension précédente du même module, dédupliquée contre tout ce
   qui a déjà été généré, IDs à partir de GENERATED_ID_OFFSET + id_block,
   bloc dédié par extension).

3. NOUVEAU MODULE — volumes_espace (Chapitre_15) : ce chapitre n'avait
   AUCUN générateur avant la mission "équilibrage définitif" (150
   exercices, le plus faible de Troisième) ; son pool entier est nouveau.

Chapitre_7 reste au niveau de sa banque curée + baseline (déjà ≥242, ratio
cible respecté sans générateur supplémentaire — voir rapport de mission).

4. "audit final et rééquilibrage additif global" (2026-09-02) : Chapitre_11/
   12/13 n'avaient AUCUN générateur (banques purement curées) — 3 nouveaux
   modules (geometrie_transformations, geometrie_triangles,
   pythagore_trigonometrie) rejoignent la baseline. Chapitre_1/3/8 reçoivent
   en plus une extension (divisibilite/fractions_addition/
   fonction_affine_deux_points) pour atteindre la cible de ratio ≤1,5.

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
    fonction_affine_deux_points, fractions_addition, fractions_simplification, geometrie_transformations,
    geometrie_triangles, image_fonction, nombres_relatifs, probabilites_troisieme, proportionnalite,
    pythagore_trigonometrie, statistiques, thales, volumes_espace,
)

OUTPUT_PATH = ROOT / "exercises_generated_troisieme.json"

# (nom, module, per_family_origine, seed_origine) — jamais modifié : les 8
# modules historiques ET les 5 modules créés par la mission "rééquilibrage
# global de toutes les classes" (2026-09-01, Chapitre_2/6/9/10/14) sont tous
# déjà COMMITTÉS/SERVIS en production, donc figés au même titre — voir
# tools/generate_derivative_exercises.py pour le même principe côté
# Première. Reproduit bit pour bit le pool actuellement en production (592
# exercices générés, vérifié avant toute modification de ce fichier).
_BASELINE_MODULES = (
    ("equation_premier_degre", equation_premier_degre, 6, 30260101),
    ("divisibilite", divisibilite, 6, 30260102),
    ("fractions_addition", fractions_addition, 6, 30260103),
    ("fractions_simplification", fractions_simplification, 7, 30260104),
    ("fonction_affine_deux_points", fonction_affine_deux_points, 7, 30260105),
    ("developper_distributivite", developper_distributivite, 6, 30260106),
    ("factoriser_somme", factoriser_somme, 7, 30260107),
    ("image_fonction", image_fonction, 6, 30260108),
    ("nombres_relatifs", nombres_relatifs, 9, 30260301),
    ("proportionnalite", proportionnalite, 15, 30260302),
    ("statistiques", statistiques, 13, 30260303),
    ("probabilites_troisieme", probabilites_troisieme, 11, 30260304),
    ("thales", thales, 15, 30260305),
)

# ── Mission "équilibrage définitif de toutes les classes" (2026-09-01) ─────
# Chapitre_2/4/5/6/9/10/14 restent sous la cible d'équilibrage (ratio ≤1,5
# par rapport à Chapitre_7=242) même avec la baseline ci-dessus — extension
# ADDITIVE : nouveau seed (distinct de la baseline ET de toute extension
# précédente du même module), dédupliquée contre TOUT ce qui a déjà été
# généré pour le même module, jamais de remplacement.
# (nom, module, seed_extension, per_family_large, n_extra_cible, id_block)
_EXTENSION_MODULES = (
    ("equation_premier_degre", equation_premier_degre, 930260101, 30, 45, 5000),
    ("developper_distributivite", developper_distributivite, 930260106, 20, 15, 5000),
    ("factoriser_somme", factoriser_somme, 930260107, 20, 15, 5000),
    ("equation_premier_degre", equation_premier_degre, 931260101, 60, 50, 5200),
    ("developper_distributivite", developper_distributivite, 931260106, 60, 40, 5200),
    ("factoriser_somme", factoriser_somme, 931260107, 60, 35, 5200),
    ("nombres_relatifs", nombres_relatifs, 931260301, 60, 74, 5000),
    ("proportionnalite", proportionnalite, 931260302, 60, 77, 5000),
    ("statistiques", statistiques, 931260303, 60, 75, 5000),
    ("probabilites_troisieme", probabilites_troisieme, 931260304, 60, 77, 5000),
    ("thales", thales, 931260305, 60, 75, 5000),
    # Mission "audit final et rééquilibrage additif global" (2026-09-02) :
    # Chapitre_1/3/8 sous la cible d'équilibrage (ratio ≤1,5 par rapport à
    # Chapitre_4=298) même après les 3 nouveaux modules ci-dessus.
    ("divisibilite", divisibilite, 932260102, 60, 40, 6000),
    ("fractions_addition", fractions_addition, 932260103, 60, 15, 6000),
    ("fonction_affine_deux_points", fonction_affine_deux_points, 932260105, 60, 36, 6000),
)

# Chapitre_15 : aucun générateur n'existait avant cette mission (150
# exercices, chapitre le plus faible de Troisième) — pool entièrement
# nouveau, rejoint la baseline dès sa création.
_BASELINE_MODULES = _BASELINE_MODULES + (
    ("volumes_espace", volumes_espace, 18, 30260306),
)

# ── Mission "audit final et rééquilibrage additif global" (2026-09-02) ─────
# Chapitre_11/12/13 n'avaient AUCUN générateur (banques purement curées,
# 180/210/181 exercices) — 3 nouveaux modules entièrement nouveaux, rejoignent
# la baseline dès leur création (même patron que volumes_espace ci-dessus).
_BASELINE_MODULES = _BASELINE_MODULES + (
    ("geometrie_transformations", geometrie_transformations, 10, 30260111),
    ("geometrie_triangles", geometrie_triangles, 8, 30260112),
    ("pythagore_trigonometrie", pythagore_trigonometrie, 10, 30260113),
)

# ── Mission "diversification structurelle" (2026-09-02) ────────────────────
# Modules dotés d'un generate_extra_pool() (nouvelles FAMILLES à structure
# réellement différente) — voir l'audit de diversité (40 familles à
# quasi-doublon ≥90% détectées, une seule structure malgré des coefficients
# variés). (nom, module, seed, per_family)
_DIVERSITY_MODULES = (
    ("factoriser_somme", factoriser_somme, 30260350, 12),
    ("nombres_relatifs", nombres_relatifs, 30260150, 12),
    ("proportionnalite", proportionnalite, 30260250, 12),
    ("statistiques", statistiques, 30260250, 12),
    ("probabilites_troisieme", probabilites_troisieme, 30260450, 12),
    ("thales", thales, 30260350, 12),
    ("volumes_espace", volumes_espace, 30260350, 12),
    # Mission "chantier final : diversification numérique maximale"
    # (2026-09-02) — per_family=20 : ce module n'avait AUCUNE famille dans
    # EXTRA_FAMILIES avant cette mission, donc rien n'est décalé (voir
    # geometrie_reperee.py pour le cas inverse). Volume plafonné à 20 (pas
    # 36-50) pour respecter RATIO_MAX_PAR_CLASSE["troisieme"]=1.7 déjà
    # verrouillé par test_exercise_chapter_balance.py — Chapitre_4 ne doit
    # jamais dépasser 1,7 × min(chapitres) = 1,7 × 177 ≈ 300.
    ("developper_distributivite", developper_distributivite, 30260550, 20),
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
                      baseline_enonces: set[str], id_block: int = 5000) -> list[dict]:
    """Voir tools/generate_derivative_exercises.py::_build_extension — même
    contrat : seed distinct, dédupliqué contre TOUT ce qui a déjà été généré
    pour ce module (baseline + extensions précédentes, cumulées par
    main()), IDs à partir de GENERATED_ID_OFFSET + id_block (bloc dédié et
    jamais réutilisé pour une extension différente du même module)."""
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
    offset = module.GENERATED_ID_OFFSET + id_block
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

    extension_counter: dict[str, int] = {}
    for name, module, seed_ext, per_family_large, n_extra, id_block in _EXTENSION_MODULES:
        extra_pool = _build_extension(module, seed_ext, per_family_large, n_extra,
                                       baseline_enonces_by_module.get(name, set()), id_block)
        all_problems.extend(_check_family_calibration(extra_pool, f"{name} (extension)"))
        extension_counter[name] = extension_counter.get(name, 0) + 1
        label = f"{name} (extension {extension_counter[name]})" if extension_counter[name] > 1 else f"{name} (extension)"
        per_module_counts[label] = len(extra_pool)
        combined.extend(extra_pool)
        baseline_enonces_by_module.setdefault(name, set()).update(e["enonce"] for e in extra_pool)

    # ── Mission "diversification structurelle" (2026-09-02) ────────────────
    for name, module, seed_div, per_family_div in _DIVERSITY_MODULES:
        diversity_pool = module.generate_extra_pool(per_family=per_family_div, seed=seed_div)
        seen = baseline_enonces_by_module.get(name, set())
        diversity_pool = [ex for ex in diversity_pool if ex["enonce"] not in seen]
        all_problems.extend(_check_family_calibration(diversity_pool, f"{name} (diversité)"))
        per_module_counts[f"{name} (diversité)"] = len(diversity_pool)
        combined.extend(diversity_pool)

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
