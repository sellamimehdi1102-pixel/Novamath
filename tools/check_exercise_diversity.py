"""Détecte les problèmes de diversité dans les banques d'exercices : doublons
exacts, quasi-doublons (même gabarit de phrase, seuls les nombres changent),
et notions dont la diversité réelle reste faible malgré un grand nombre
d'exercices.

Outil de RÉGRESSION pour le chantier de diversification des exercices —
à relancer après tout ajout de contenu pour vérifier qu'une notion ne
redevient pas une simple accumulation de variations numériques.

Usage : python -m tools.check_exercise_diversity [--threshold 0.5] [fichier ...]
Sans argument, audite les 3 banques curées (troisieme/seconde/premiere) et le
pool généré de Première.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

DEFAULT_FILES = [
    ROOT / "exercises_bank_troisieme.json",
    ROOT / "exercises_bank.json",
    ROOT / "exercises_bank_premiere.json",
    ROOT / "exercises_generated_premiere.json",
]

NUMBER_RE = re.compile(r"-?\d+(?:[.,]\d+)?")
WS_RE = re.compile(r"\s+")


def normalize(enonce: str) -> str:
    t = NUMBER_RE.sub("N", enonce or "")
    return WS_RE.sub(" ", t).strip()


def load(path: Path) -> list[dict]:
    data = json.loads(path.read_text(encoding="utf-8"))
    return data if isinstance(data, list) else data.get("exercises", [])


def audit_file(path: Path, threshold: float) -> dict:
    items = load(path)
    exact_groups: dict[str, list[dict]] = defaultdict(list)
    for ex in items:
        exact_groups[(ex.get("enonce") or "").strip()].append(ex)
    exact_dupes = sum(len(v) - 1 for v in exact_groups.values() if len(v) > 1)

    by_notion: dict[tuple, list[dict]] = defaultdict(list)
    for ex in items:
        by_notion[(ex.get("chapter_id"), ex.get("notion"))].append(ex)

    poor_diversity = []  # (chapter_id, notion, total, templates, ratio, n_families)
    total_quasi_dupes = 0
    for (ch, notion), exs in by_notion.items():
        templates = defaultdict(list)
        for ex in exs:
            templates[normalize(ex.get("enonce", ""))].append(ex)
        n_total = len(exs)
        n_templates = len(templates)
        redundant = n_total - n_templates
        total_quasi_dupes += redundant
        ratio = n_templates / n_total if n_total else 1.0

        # `family` (exercices générés symboliquement, exercise_generator/) :
        # une famille répète volontairement la même structure de phrase avec
        # des valeurs différentes — c'est UN type de raisonnement parmi
        # plusieurs, pas une redondance. Le vrai signal de diversité pour ce
        # contenu est le nombre de familles distinctes, pas le gabarit de
        # phrase (qui sous-estime massivement ce contenu, voir README/audit).
        families = {ex.get("family") for ex in exs if ex.get("family")}
        has_families = bool(families)
        signal_ratio = (len(families) / n_total) if has_families else ratio
        # Avec des familles connues, on ne signale que si le nombre de
        # familles distinctes est lui-même faible (peu importe qu'une famille
        # ait 12 variantes numériques, c'est voulu) — seuil absolu, pas un ratio.
        is_poor = (len(families) < 4) if has_families else (n_total >= 5 and ratio < threshold)
        if is_poor:
            poor_diversity.append((ch, notion, n_total, n_templates, ratio, len(families) if has_families else None))

    poor_diversity.sort(key=lambda r: r[4])

    return {
        "total": len(items),
        "exact_duplicates": exact_dupes,
        "quasi_duplicates": total_quasi_dupes,
        "notions_faible_diversite": poor_diversity,
        "n_notions": len(by_notion),
    }


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("files", nargs="*", help="Fichiers JSON à auditer (défaut : les 4 banques du projet).")
    parser.add_argument("--threshold", type=float, default=0.5,
                         help="Seuil (gabarits/total) en-dessous duquel une notion est signalée 'faible diversité'. Défaut 0.5.")
    args = parser.parse_args(argv)

    files = [Path(f) for f in args.files] if args.files else DEFAULT_FILES
    total_exact = total_quasi = 0
    total_poor_notions = 0

    for path in files:
        if not path.exists():
            print(f"\n=== {path} === (absent, ignoré)")
            continue
        report = audit_file(path, args.threshold)
        print(f"\n=== {path.name} ===")
        print(f"  {report['total']} exercices, {report['n_notions']} notions")
        print(f"  doublons exacts : {report['exact_duplicates']}")
        print(f"  quasi-doublons (même gabarit) : {report['quasi_duplicates']}")
        poor = report["notions_faible_diversite"]
        print(f"  notions à faible diversité (< {args.threshold:.0%} de gabarits distincts, ou < 4 familles distinctes, min. 5 ex.) : {len(poor)}")
        for ch, notion, n_total, n_templates, ratio, n_families in poor[:15]:
            if n_families is not None:
                print(f"    - {ch}::{notion[:45]:<45} {n_total:>4} ex. -> {n_families:>2} familles distinctes")
            else:
                print(f"    - {ch}::{notion[:45]:<45} {n_total:>4} ex. -> {n_templates:>3} gabarits ({ratio*100:.0f}%)")
        if len(poor) > 15:
            print(f"    ... (+{len(poor) - 15})")
        total_exact += report["exact_duplicates"]
        total_quasi += report["quasi_duplicates"]
        total_poor_notions += len(poor)

    print("\n=== TOTAL ===")
    print(f"  doublons exacts : {total_exact}")
    print(f"  quasi-doublons : {total_quasi}")
    print(f"  notions à faible diversité : {total_poor_notions}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
