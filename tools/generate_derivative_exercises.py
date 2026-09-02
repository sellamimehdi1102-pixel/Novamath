"""Régénère exercises_generated_premiere.json à partir de TOUS les moteurs
symboliques déclarés dans webapp/exercise_generator/ (derivatives, suites,
exponentielle, variations, second_degre, tangente, trigonometrie,
produit_scalaire, geometrie_reperee, probabilites_conditionnelles,
variables_aleatoires — chapitres 1 à 10).

Chaque module a un GENERATED_ID_OFFSET distinct (900_000 à 1_000_000 par pas
de 10_000) fixé dans son propre fichier — jamais de collision d'id entre
pools, même après concaténation.

── RÈGLE ABSOLUE — missions "rééquilibrage additif" (2026-09-01) et
"équilibrage définitif de toutes les classes" (2026-09-01) ────────────────
Ce script ne DOIT JAMAIS faire disparaître un exercice déjà généré
précédemment (ancienne règle violée par une mission antérieure, qui avait
réduit --per-family pour "équilibrer" et fait chuter le total Première de
2217 à 1547 — explicitement interdit désormais). Le seul mode d'équilibrage
autorisé est ADDITIF :

1. BASELINE (`_BASELINE_MODULES`) — les 11 modules déjà COMMITTÉS/SERVIS en
   production (6 historiques Chapitre_1-5 + 5 issus de la mission
   "rééquilibrage additif" pour Chapitre_6-10) sont TOUJOURS régénérés avec
   leur per_family/seed ORIGINAL, figé pour toujours : reproduit bit pour
   bit le pool actuellement en production (2900 exercices, vérifié avant
   toute modification de ce fichier), jamais réduit.

2. EXTENSION (`_EXTENSION_MODULES`) — pour les chapitres dont la baseline
   seule reste sous la cible d'équilibrage (ratio ≤1,5 par rapport au
   chapitre le plus fourni), on génère un pool supplémentaire avec un SEED
   DIFFÉRENT (distinct de la baseline ET de toute extension précédente du
   même module — `main()` cumule les énoncés déjà produits par module au fil
   des extensions), on écarte tout exercice dont l'énoncé existe déjà,
   puis on numérote les survivants à partir de GENERATED_ID_OFFSET +
   id_block (bloc dédié et jamais réutilisé pour une extension différente du
   même module) — donc toujours un AJOUT, jamais un remplacement.

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

# Chapitre_6 à Chapitre_10 (trigonometrie/produit_scalaire/geometrie_reperee/
# probabilites_conditionnelles/variables_aleatoires) : générateurs créés par
# la mission "rééquilibrage additif" (2026-09-01) et déjà COMMITTÉS/SERVIS —
# ils rejoignent donc la BASELINE au même titre que les 6 modules historiques
# ci-dessus : per_family/seed figés pour toujours reproduire bit pour bit le
# pool actuellement en production, jamais réduits. Toute croissance
# ultérieure de ces chapitres passe exclusivement par _EXTENSION_MODULES
# (mission "équilibrage définitif de toutes les classes", 2026-09-01).
_BASELINE_MODULES = _BASELINE_MODULES + (
    ("trigonometrie", trigonometrie, 20260901, 205),
    ("produit_scalaire", produit_scalaire, 20260902, 38),
    ("geometrie_reperee", geometrie_reperee, 20260903, 35),
    ("probabilites_conditionnelles", probabilites_conditionnelles, 20260904, 45),
    ("variables_aleatoires", variables_aleatoires, 20260905, 60),
)

# Chapitre_2/4/7/8/9/10 restent sous la cible d'équilibrage (ratio ≤1,5 par
# rapport à Chapitre_3=567) même avec la baseline ci-dessus — extension
# ADDITIVE : nouveau seed (distinct de la baseline ET, pour second_degre/
# variations, de leur extension déjà existante), dédupliquée contre TOUT ce
# qui a déjà été généré pour le même module, jamais de remplacement. Voir
# règle 2. (module, seed_extension, per_family_large, n_extra_cible)
_EXTENSION_MODULES = (
    ("second_degre", second_degre, 920260823, 40, 22, 5000),
    ("variations", variations, 920260822, 60, 154, 5000),
    ("second_degre", second_degre, 921260823, 90, 117, 5200),
    ("variations", variations, 921260822, 90, 120, 5200),
    ("produit_scalaire", produit_scalaire, 921260902, 90, 117, 5000),
    ("geometrie_reperee", geometrie_reperee, 921260903, 90, 119, 5000),
    ("probabilites_conditionnelles", probabilites_conditionnelles, 921260904, 90, 110, 5000),
    ("variables_aleatoires", variables_aleatoires, 921260905, 90, 75, 5000),
)

# ── Mission "diversification structurelle" (2026-09-02) ────────────────────
# Modules dotés d'un generate_extra_pool() (nouvelles FAMILLES à structure
# réellement différente, pas des extensions numériques d'une famille
# existante) — voir l'audit de diversité qui a identifié 40 familles à
# quasi-doublon ≥90% (une seule structure malgré des coefficients variés).
# (nom, module, seed, per_family)
_DIVERSITY_MODULES = (
    ("second_degre", second_degre, 20260946, 12),
    ("variations", variations, 20260930, 12),
    ("trigonometrie", trigonometrie, 20260945, 12),
    ("produit_scalaire", produit_scalaire, 20260947, 12),
    ("geometrie_reperee", geometrie_reperee, 20260948, 12),
    ("probabilites_conditionnelles", probabilites_conditionnelles, 20260949, 12),
    ("variables_aleatoires", variables_aleatoires, 20260950, 12),
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
                      baseline_enonces: set[str], id_block: int = 5000) -> list[dict]:
    """Génère un pool supplémentaire (seed distinct de la baseline), écarte
    tout exercice dont l'énoncé existe déjà dans `baseline_enonces` (baseline
    du module + toute extension déjà traitée pour ce même module — voir
    main(), qui met à jour cet ensemble après chaque extension), puis
    renumérote les survivants à partir de GENERATED_ID_OFFSET + id_block.
    `id_block` doit être distinct pour chaque extension d'un même module
    (jamais dans une plage déjà utilisée par la baseline ou une extension
    précédente) — voir les valeurs choisies dans _EXTENSION_MODULES, chacune
    espacée de 200 pour ne jamais chevaucher la suivante, donc toujours un
    AJOUT, jamais un remplacement."""
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

    for name, module, seed, per_family in _BASELINE_MODULES:
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
        # Cumule pour que l'extension SUIVANTE du même module (ex. la 2e
        # extension de second_degre) déduplique aussi contre celle-ci, pas
        # seulement contre la baseline — sinon risque de doublon d'énoncé
        # entre deux extensions successives.
        baseline_enonces_by_module.setdefault(name, set()).update(e["enonce"] for e in extra_pool)

    # ── Mission "diversification structurelle" (2026-09-02) ────────────────
    # Pools de nouvelles FAMILLES (structures de raisonnement réellement
    # différentes, pas des variantes numériques d'une famille existante) —
    # voir generate_extra_pool() dans chaque module. IDs dans un bloc dédié
    # (GENERATED_ID_OFFSET + 8000) au sein de chaque module, jamais mélangés
    # à generate_pool()/FAMILIES (baseline figée).
    for name, module, seed_div, per_family_div in _DIVERSITY_MODULES:
        diversity_pool = module.generate_extra_pool(per_family=per_family_div, seed=seed_div)
        seen = baseline_enonces_by_module.get(name, set())
        diversity_pool = [ex for ex in diversity_pool if ex["enonce"] not in seen]
        all_problems.extend(_check_family_calibration(diversity_pool, f"{name} (diversité)"))
        per_module_counts[f"{name} (diversité)"] = len(diversity_pool)
        combined.extend(diversity_pool)

    # ── Mission "chantier final : diversification numérique maximale"
    # (2026-09-02) ── La famille vecteur_normal_unitaire (geometrie_reperee)
    # est volontairement placée EN DERNIER dans EXTRA_FAMILIES (voir sa
    # docstring) pour ne jamais décaler la séquence rng des 5 autres familles
    # déjà committées. Pour la même raison, on ne peut PAS simplement monter
    # le per_family PARTAGÉ de l'appel ci-dessus à 36 (cela décalerait aussi
    # la séquence rng des 5 autres familles, qui consommeraient plus
    # d'essais avant de s'arrêter) : un second appel 100% indépendant
    # (seed dédié) sert uniquement à compléter CETTE famille au-delà des 12
    # déjà produites, avec un bloc d'ID dédié (+8500) et une déduplication
    # contre tout ce qui existe déjà dans `combined`.
    _existing_enonces_global = {ex["enonce"] for ex in combined}
    _vnu_top_up = geometrie_reperee.generate_extra_pool(per_family=40, seed=920260951)
    _vnu_top_up = [
        ex for ex in _vnu_top_up
        if ex["family"] == "vecteur_normal_unitaire" and ex["enonce"] not in _existing_enonces_global
    ]
    _seen_vnu = set()
    _vnu_dedup = []
    for ex in _vnu_top_up:
        if ex["enonce"] in _seen_vnu:
            continue
        _seen_vnu.add(ex["enonce"])
        _vnu_dedup.append(ex)
    _vnu_offset = geometrie_reperee.GENERATED_ID_OFFSET + 8500
    for i, ex in enumerate(_vnu_dedup):
        ex["id"] = _vnu_offset + i
    per_module_counts["geometrie_reperee (vecteur_normal_unitaire, complément)"] = len(_vnu_dedup)
    combined.extend(_vnu_dedup)

    # ── Mission "audit final et exhaustif de la diversité mathématique"
    # (2026-09-02) ── `combinaison_lineaire` (baseline figée, FAMILIES)
    # représente 205/438 de Chapitre_6 avec un raisonnement unique (lire
    # cos/sin d'un angle dans la table). `combinaison_deux_angles` (12
    # exemplaires) a un espace combinatoire large (42 paires ordonnées
    # d'angles × 8 × 8 coefficients = 2688 combinaisons possibles) et une
    # structure réellement différente — on l'enrichit donc pour réduire le
    # poids relatif de combinaison_lineaire sans jamais y toucher. Même
    # patron que le complément vecteur_normal_unitaire ci-dessus : appel
    # indépendant (seed dédié), bloc d'ID séparé, dédupliqué contre tout ce
    # qui existe déjà. `expression_carre` (7/7 angles déjà couverts) et
    # `formule_duplication` (14 combinaisons déterministes max, angle×type)
    # sont structurellement plafonnées : les gonfler produirait des doublons
    # ou une fausse diversité, donc aucun complément ne leur est appliqué.
    _existing_enonces_global = {ex["enonce"] for ex in combined}
    _cda_top_up = trigonometrie.generate_extra_pool(per_family=80, seed=920260952)
    _cda_top_up = [
        ex for ex in _cda_top_up
        if ex["family"] == "combinaison_deux_angles" and ex["enonce"] not in _existing_enonces_global
    ]
    _seen_cda = set()
    _cda_dedup = []
    for ex in _cda_top_up:
        if ex["enonce"] in _seen_cda:
            continue
        _seen_cda.add(ex["enonce"])
        _cda_dedup.append(ex)
    _cda_offset = trigonometrie.GENERATED_ID_OFFSET + 8500
    for i, ex in enumerate(_cda_dedup):
        ex["id"] = _cda_offset + i
    per_module_counts["trigonometrie (combinaison_deux_angles, complément)"] = len(_cda_dedup)
    combined.extend(_cda_dedup)

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
