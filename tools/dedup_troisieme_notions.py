"""Dédoublonne, au sein des 10 notions ciblées par le chantier de
diversification Troisième (lot 2026-08), les exercices EXISTANTS de
exercises_bank_troisieme.json dont l'énoncé suit le même gabarit normalisé
(numéros -> N, comme tools/check_exercise_diversity.py::normalize).

Un seul exemplaire est conservé par gabarit (le premier rencontré, dans
l'ordre du fichier) — jamais réordonné ni renuméroté : tous les autres
exercices (notions non ciblées, ou hors des 10) et leurs `id` (assignés en
amont, id = index d'origine) restent strictement inchangés.

Usage : python -m tools.dedup_troisieme_notions [--dry-run]
"""
import argparse
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BANK_PATH = ROOT / "exercises_bank_troisieme.json"

NUMBER_RE = re.compile(r"-?\d+(?:[.,]\d+)?")
WS_RE = re.compile(r"\s+")

TARGET_NOTIONS = {
    ("Chapitre_8", "Déterminer une fonction affine à partir de deux images"),
    ("Chapitre_4", "Développer un produit avec la simple distributivité"),
    ("Chapitre_4", "Factoriser une somme ou une différence"),
    ("Chapitre_5", "Résoudre une équation du premier degré"),
    ("Chapitre_1", "Critères de divisibilité"),
    ("Chapitre_3", "Addition et soustraction de fractions"),
    ("Chapitre_3", "Simplification et forme irréductible d'une fraction"),
    ("Chapitre_7", "Calculer une image à partir de l'expression d'une fonction"),
    ("Chapitre_7", "Lire graphiquement une image ou un antécédent"),
    ("Chapitre_10", "Construire et utiliser un arbre de probabilités"),
}


def normalize(enonce: str) -> str:
    t = NUMBER_RE.sub("N", enonce or "")
    return WS_RE.sub(" ", t).strip()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    data = json.loads(BANK_PATH.read_text(encoding="utf-8"))
    kept: list[dict] = []
    removed_ids: list[int] = []
    seen: dict[tuple, set] = {}

    for ex in data:
        key = (ex.get("chapter_id"), ex.get("notion"))
        if key not in TARGET_NOTIONS:
            kept.append(ex)
            continue
        tmpl = normalize(ex.get("enonce", ""))
        seen_set = seen.setdefault(key, set())
        if tmpl in seen_set:
            removed_ids.append(ex["id"])
            continue
        seen_set.add(tmpl)
        kept.append(ex)

    print(f"Avant : {len(data)} exercices")
    print(f"Après dédoublonnage des 10 notions ciblées : {len(kept)} exercices ({len(removed_ids)} supprimés)")
    for key in sorted(TARGET_NOTIONS):
        before = sum(1 for ex in data if (ex.get("chapter_id"), ex.get("notion")) == key)
        after = sum(1 for ex in kept if (ex.get("chapter_id"), ex.get("notion")) == key)
        print(f"  {key[0]}::{key[1][:50]:<50} {before:>3} -> {after:>3}")

    if not args.dry_run:
        BANK_PATH.write_text(json.dumps(kept, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"Écrit -> {BANK_PATH}")
    else:
        print("(dry-run, rien écrit)")


if __name__ == "__main__":
    main()
