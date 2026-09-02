"""Ajoute des exercices aux deux chapitres les plus faibles de Seconde
(Chapitre_5 "vecteurs" et Chapitre_10 "pourcentages/évolutions", 121
exercices chacun avant cette mission, aucun générateur) directement dans
exercises_bank.json — la banque CURÉE de Seconde.

── Pourquoi pas exercises_generated_seconde.json ? ─────────────────────────
Contrairement à Première/Troisième, server.py::_class_bank("seconde") NE
fusionne PAS génériquement generated_exercise_bank (chemin historique — voir
curriculum_stats.py::_CLASS_LEVELS_WITHOUT_GENERATED_MERGE) : seuls
Chapitre_6 (droites.py) et Chapitre_9 (signes.py) y sont explicitement
mergés en dur (voir webapp/server.py, mission "porter à 300 exercices
minimum par chapitre", 2026-09-02 — Chapitre_6 avait été laissé non fusionné
par la mission "rééquilibrage global" du 2026-09-01 pour préserver un ratio
qui n'est plus la contrainte prioritaire). Tout AUTRE générateur créé pour
Seconde reste donc hors de ce mécanisme de fusion générique, et le seul
moyen ADDITIF de servir réellement du nouveau contenu à l'utilisateur de
Seconde pour ces chapitres-là est de l'ajouter directement dans
exercises_bank.json (la banque curée elle-même).

Le seul moyen ADDITIF de servir réellement du nouveau contenu à l'utilisateur
de Seconde est donc de l'ajouter à la fin d'exercises_bank.json, avec le
même schéma que les exercices curés existants (enonce/answer/hint/
solution_steps/chapter_id/notion/difficulty/id) et des id > 500_000 (jamais
dans la plage 0-2102 déjà utilisée).

RÈGLE ABSOLUE : ce script ne modifie et ne supprime AUCUNE entrée
existante — il charge exercises_bank.json, vérifie qu'aucun id généré ne
collisionne, puis ÉCRIT LA CONCATÉNATION (existant + nouveau), jamais un
remplacement.

── Mission "audit et renforcement de la diversité NUMÉRIQUE" (2026-09-02) ──
`pourcentages_evolutions.generate_extra_pool()` (nouvelle famille
evolution_taux_decimal, IDs à GENERATED_ID_OFFSET+8000, jamais mélangée à
generate_pool()/FAMILIES) comble un vrai manque vérifié dans le code : le
taux d'évolution y était TOUJOURS un entier de %, jamais un taux décimal
(7,5% par ex.). Ajoutée à `_NEW_EXTRA_POOLS` ci-dessous, avec le même
contrat additif que `_NEW_POOLS` (dédupliquée par énoncé, jamais un
remplacement).

Usage : python -m tools.generate_seconde_curated_additions
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "webapp"))

from exercise_generator_seconde import (  # noqa: E402
    calcul_litteral_seconde, fonctions_generalites_seconde, intervalles_seconde, nombres_seconde,
    pourcentages_evolutions, probabilites_seconde, signes, statistiques_seconde,
    variations_seconde, vecteurs_seconde, vecteurs_sans_repere,
)

BANK_PATH = ROOT / "exercises_bank.json"
# webapp/server.py fusionne EN MÉMOIRE Chapitre_6 (droites.py) et Chapitre_9
# (signes.py) depuis ce fichier — jamais écrits dans exercises_bank.json.
# Leurs IDs/énoncés doivent donc être connus du anti-doublon ci-dessous,
# sinon une extension de signes.py pourrait régénérer par hasard un énoncé
# déjà réellement servi (et donc entrer en collision d'ID puisque son bloc
# d'extension est calculé à partir du MÊME GENERATED_ID_OFFSET).
GENERATED_SECONDE_PATH = ROOT / "exercises_generated_seconde.json"

# (module, per_family, seed) — Chapitre_5 (vecteurs_seconde) et Chapitre_10
# (pourcentages_evolutions), les deux chapitres les plus faibles de Seconde.
_NEW_POOLS = (
    (vecteurs_seconde, 18, 20260910),
    (pourcentages_evolutions, 18, 20260911),
    # Mission "audit final et rééquilibrage additif global" (2026-09-02) :
    # Chapitre_1/3/4/8/11 n'avaient AUCUN générateur (banques purement
    # curées) — 5 nouveaux modules pour atteindre la cible de ratio ≤1,5.
    (nombres_seconde, 8, 940520101),
    (calcul_litteral_seconde, 8, 940530101),
    (vecteurs_sans_repere, 10, 940540101),
    (variations_seconde, 8, 940550101),
    (statistiques_seconde, 8, 940560101),
    # Mission "porter à 300 exercices minimum par chapitre + diversité
    # mathématique réelle" (2026-09-02) : Chapitre_2/7/12 restaient purement
    # curés (aucun générateur) — 3 nouveaux modules entièrement nouveaux.
    (intervalles_seconde, 32, 950570101),
    (fonctions_generalites_seconde, 30, 950580101),
    (probabilites_seconde, 30, 950590101),
)

# (module, per_family, seed) — pools de diversification NUMÉRIQUE
# (generate_extra_pool(), jamais generate_pool()) : mission 2026-09-02.
_NEW_EXTRA_POOLS = (
    (pourcentages_evolutions, 15, 20260950),
)

# ── Mission "porter à 300 exercices minimum par chapitre" (2026-09-02) ─────
# Extension ADDITIVE des générateurs déjà servis : seed distinct de leur(s)
# pool(s) d'origine ET id_offset dédié (GENERATED_ID_OFFSET + 400_000, une
# zone qui ne chevauche AUCUN autre module ni AUCUN pool orphelin — voir
# webapp/exercise_generator_seconde/*.py, offsets 500_000-810_000) — jamais
# une régénération de generate_pool() de base, jamais un remplacement.
# Même contrat que tools/generate_troisieme_exercises.py::_EXTENSION_MODULES.
# (module, per_family_extension, seed_extension)
_EXTENSION_POOLS = (
    (nombres_seconde, 35, 920000101),
    (calcul_litteral_seconde, 35, 920000103),
    (vecteurs_sans_repere, 45, 920000104),
    (vecteurs_seconde, 25, 920000100),
    (variations_seconde, 45, 920000105),
    (signes, 10, 920000109),
    (pourcentages_evolutions, 22, 920000110),
    (statistiques_seconde, 35, 920000106),
)

# Second bloc d'extension (id_offset + 410_000, distinct du premier bloc
# ci-dessus) — Chapitre_4 (vecteurs_sans_repere, +104 seulement, 3 familles)
# et Chapitre_10 (pourcentages_evolutions, +78 seulement) restaient de
# quelques exercices sous le plancher de 300 après le premier bloc : léger
# complément, même contrat additif (seed et bloc d'IDs dédiés).
_EXTENSION_POOLS_2 = (
    (vecteurs_sans_repere, 15, 921000104),
    (pourcentages_evolutions, 10, 921000110),
)

# Champs du schéma curé Seconde (voir exercises_bank.json) — les champs
# internes au générateur (family, family_label, declared_level,
# complexity_score, source) ne font pas partie de ce schéma et sont retirés
# avant écriture, pour ne jamais introduire un format hétérogène dans la
# banque curée.
_CURATED_FIELDS = ("enonce", "answer", "hint", "solution_steps", "chapter_id", "notion", "difficulty", "id")


def _merge_pool(pool, existing, existing_ids, existing_enonces, additions):
    for ex in pool:
        if ex["id"] in existing_ids:
            # Script rejouable : si un run précédent a déjà écrit CE MÊME
            # exercice (id et énoncé identiques), ce n'est pas une
            # collision réelle -- seule une divergence id/énoncé est une
            # vraie erreur d'intégrité.
            already = next((e for e in existing if e["id"] == ex["id"]), None)
            if already is not None and already.get("enonce") == ex["enonce"]:
                continue
            print(f"ERREUR — collision d'id avec la banque existante : {ex['id']}", file=sys.stderr)
            sys.exit(1)
        if ex["enonce"] in existing_enonces:
            continue  # doublon avec un exercice curé déjà présent : ignoré, jamais écrasé
        curated = {field: ex[field] for field in _CURATED_FIELDS}
        additions.append(curated)
        existing_ids.add(curated["id"])
        existing_enonces.add(curated["enonce"])


def main() -> None:
    existing = json.loads(BANK_PATH.read_text(encoding="utf-8"))
    existing_ids = {e["id"] for e in existing}
    existing_enonces = {e["enonce"] for e in existing}

    if GENERATED_SECONDE_PATH.exists():
        served_generated = [
            e for e in json.loads(GENERATED_SECONDE_PATH.read_text(encoding="utf-8"))
            if e.get("chapter_id") in ("Chapitre_6", "Chapitre_9")
        ]
        existing_ids.update(e["id"] for e in served_generated)
        existing_enonces.update(e["enonce"] for e in served_generated)

    additions: list[dict] = []
    for module, per_family, seed in _NEW_POOLS:
        pool = module.generate_pool(per_family=per_family, seed=seed)
        _merge_pool(pool, existing, existing_ids, existing_enonces, additions)

    for module, per_family, seed in _NEW_EXTRA_POOLS:
        pool = module.generate_extra_pool(per_family=per_family, seed=seed)
        _merge_pool(pool, existing, existing_ids, existing_enonces, additions)

    for module, per_family, seed in _EXTENSION_POOLS:
        pool = module.generate_pool(per_family=per_family, seed=seed, id_offset=module.GENERATED_ID_OFFSET + 400_000)
        _merge_pool(pool, existing, existing_ids, existing_enonces, additions)

    # IDs absolus dédiés (999_000+) plutôt qu'un décalage fixe par module : un
    # décalage fixe (ex. OFFSET + 410_000) ferait collisionner deux modules
    # dont les OFFSET de base ne sont espacés que de 10_000 (ex. 540_000 et
    # 550_000 retomberaient tous deux sur 950_000) — vu en pratique lors de
    # cette mission, corrigé ici avant tout commit.
    for (module, per_family, seed), id_offset in zip(_EXTENSION_POOLS_2, (999_000, 999_100)):
        pool = module.generate_pool(per_family=per_family, seed=seed, id_offset=id_offset)
        _merge_pool(pool, existing, existing_ids, existing_enonces, additions)

    new_ids = [a["id"] for a in additions]
    if len(new_ids) != len(set(new_ids)):
        print("ERREUR — collision d'id entre les nouveaux exercices eux-mêmes", file=sys.stderr)
        sys.exit(1)

    combined = existing + additions
    BANK_PATH.write_text(json.dumps(combined, ensure_ascii=False, indent=2), encoding="utf-8")

    from collections import Counter
    print(f"OK — {len(additions)} exercices ajoutés -> {BANK_PATH} (total {len(combined)})")
    for module, _, _ in _NEW_POOLS + _EXTENSION_POOLS + _EXTENSION_POOLS_2:
        n = sum(1 for a in additions if a["chapter_id"] == module.CHAPTER_ID)
        print(f"  {module.__name__.split('.')[-1]} ({module.CHAPTER_ID}) : +{n}")
    by_chapter = Counter(a["chapter_id"] for a in additions)
    print(f"  Total ajouté par chapitre : {dict(sorted(by_chapter.items(), key=lambda kv: kv[0]))}")
    diff_counts = Counter(a["difficulty"] for a in additions)
    print(f"  Répartition par difficulté : {dict(sorted(diff_counts.items()))}")


if __name__ == "__main__":
    main()
