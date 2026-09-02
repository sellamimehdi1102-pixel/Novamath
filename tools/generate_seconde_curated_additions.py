"""Ajoute des exercices aux deux chapitres les plus faibles de Seconde
(Chapitre_5 "vecteurs" et Chapitre_10 "pourcentages/évolutions", 121
exercices chacun avant cette mission, aucun générateur) directement dans
exercises_bank.json — la banque CURÉE de Seconde.

── Pourquoi pas exercises_generated_seconde.json ? ─────────────────────────
Contrairement à Première/Troisième, server.py::_class_bank("seconde") NE
fusionne PAS generated_exercise_bank (chemin historique — voir
curriculum_stats.py::_CLASS_LEVELS_WITHOUT_GENERATED_MERGE). Le fichier
exercises_generated_seconde.json existant (droites.py/Chapitre_6,
signes.py/Chapitre_9 — déjà les DEUX chapitres les plus fournis) a été
volontairement laissé non fusionné par la mission "rééquilibrage global de
toutes les classes" (2026-09-01) : le fusionner aurait fait grimper
Chapitre_6 de 242 à 368 et Chapitre_9 de 201 à 273, empirant le ratio
(2,0 → ~3,0) au lieu de l'améliorer. Activer la fusion générale pour
Seconde reste donc hors de portée de cette mission (voir rapport).

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

from exercise_generator_seconde import pourcentages_evolutions, vecteurs_seconde  # noqa: E402

BANK_PATH = ROOT / "exercises_bank.json"

# (module, per_family, seed) — Chapitre_5 (vecteurs_seconde) et Chapitre_10
# (pourcentages_evolutions), les deux chapitres les plus faibles de Seconde.
_NEW_POOLS = (
    (vecteurs_seconde, 18, 20260910),
    (pourcentages_evolutions, 18, 20260911),
)

# (module, per_family, seed) — pools de diversification NUMÉRIQUE
# (generate_extra_pool(), jamais generate_pool()) : mission 2026-09-02.
_NEW_EXTRA_POOLS = (
    (pourcentages_evolutions, 15, 20260950),
)

# Champs du schéma curé Seconde (voir exercises_bank.json) — les champs
# internes au générateur (family, family_label, declared_level,
# complexity_score, source) ne font pas partie de ce schéma et sont retirés
# avant écriture, pour ne jamais introduire un format hétérogène dans la
# banque curée.
_CURATED_FIELDS = ("enonce", "answer", "hint", "solution_steps", "chapter_id", "notion", "difficulty", "id")


def main() -> None:
    existing = json.loads(BANK_PATH.read_text(encoding="utf-8"))
    existing_ids = {e["id"] for e in existing}
    existing_enonces = {e["enonce"] for e in existing}

    additions: list[dict] = []
    for module, per_family, seed in _NEW_POOLS:
        pool = module.generate_pool(per_family=per_family, seed=seed)
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

    for module, per_family, seed in _NEW_EXTRA_POOLS:
        pool = module.generate_extra_pool(per_family=per_family, seed=seed)
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

    new_ids = [a["id"] for a in additions]
    if len(new_ids) != len(set(new_ids)):
        print("ERREUR — collision d'id entre les nouveaux exercices eux-mêmes", file=sys.stderr)
        sys.exit(1)

    combined = existing + additions
    BANK_PATH.write_text(json.dumps(combined, ensure_ascii=False, indent=2), encoding="utf-8")

    from collections import Counter
    print(f"OK — {len(additions)} exercices ajoutés -> {BANK_PATH} (total {len(combined)})")
    for module, _, _ in _NEW_POOLS:
        n = sum(1 for a in additions if a["chapter_id"] == module.CHAPTER_ID)
        print(f"  {module.__name__.split('.')[-1]} ({module.CHAPTER_ID}) : +{n}")
    diff_counts = Counter(a["difficulty"] for a in additions)
    print(f"  Répartition par difficulté : {dict(sorted(diff_counts.items()))}")


if __name__ == "__main__":
    main()
