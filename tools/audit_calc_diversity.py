"""Audit de la diversité des CALCULS (pas des énoncés) dans les banques
d'exercices : pour les notions liées aux fonctions, détecte quelle
proportion des exercices utilise chaque famille de fonction (affine,
linéaire, carrée, cube, racine, inverse, polynôme de degré >=2, composée...).

Complète check_exercise_diversity.py (redondance de gabarit de phrase) et
audit_exercise_taxonomy.py (types de raisonnement) : ici on regarde l'OBJET
MATHÉMATIQUE réellement manipulé. Une notion peut avoir des énoncés très
variés tout en ne faisant travailler qu'une seule mécanique de calcul
(ex. uniquement des fonctions affines) — c'est ce que cet outil détecte.

Heuristique par motif sur l'énoncé (français/LaTeX). Approximatif par
nature : sert à repérer vite les candidats à vérifier, pas une vérité
absolue.

Usage : python -m tools.audit_calc_diversity [fichier ...]
"""
from __future__ import annotations

import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

DEFAULT_FILES = [
    ROOT / "exercises_bank_troisieme.json",
    ROOT / "exercises_generated_troisieme.json",
    ROOT / "exercises_bank.json",
    ROOT / "exercises_generated_seconde.json",
    ROOT / "exercises_bank_premiere.json",
    ROOT / "exercises_generated_premiere.json",
]

# Ordre important : du plus spécifique au plus générique (une expression
# composée doit être détectée avant "carre" si elle contient x^2 imbriqué).
FUNCTION_PATTERNS: list[tuple[str, re.Pattern]] = [
    ("inverse", re.compile(r"\\frac\{1\}\{[^}]*x[^}]*\}|1\s*/\s*x\b")),
    ("racine", re.compile(r"\\sqrt")),
    ("exponentielle", re.compile(r"\\exp\b|e\^\{?x|e\^x")),
    ("cube", re.compile(r"x\^3\b|x\^\{3\}")),
    ("carre_ou_polynome_sup", re.compile(r"x\^2\b|x\^\{2\}|x\^[4-9]\b")),
    ("composee", re.compile(r"\\circ|f\(g\(|g\(f\(")),
    ("affine_ou_lineaire", re.compile(r"[a-z]\(x\)\s*=\s*-?\d*[.,]?\d*\s*x")),
]


def detect_forms(enonce: str) -> set[str]:
    found = set()
    for name, pat in FUNCTION_PATTERNS:
        if pat.search(enonce or ""):
            found.add(name)
    return found


def load(path: Path) -> list[dict]:
    data = json.loads(path.read_text(encoding="utf-8"))
    return data if isinstance(data, list) else data.get("exercises", [])


def audit_file(path: Path) -> None:
    items = load(path)
    by_notion: dict[tuple, list[dict]] = defaultdict(list)
    for ex in items:
        by_notion[(ex.get("chapter_id"), ex.get("notion"))].append(ex)

    rows = []
    for (ch, notion), exs in by_notion.items():
        with_fn = [e for e in exs if detect_forms(e.get("enonce", ""))]
        if len(with_fn) < 5:
            continue  # pas assez d'exercices "fonction" détectés pour juger
        counts = Counter()
        for e in with_fn:
            for f in detect_forms(e.get("enonce", "")):
                counts[f] += 1
        n = len(with_fn)
        dominant, dominant_n = counts.most_common(1)[0]
        ratio = dominant_n / n
        rows.append((ch, notion, n, len(counts), dominant, ratio, dict(counts)))

    rows.sort(key=lambda r: -r[5])
    print(f"\n=== {path.name} === ({len(items)} exercices, {len(rows)} notions à contenu 'fonction' détecté)")
    for ch, notion, n, n_forms, dominant, ratio, counts in rows:
        flag = "  <== UNE SEULE FORME DE FONCTION" if n_forms == 1 else ""
        label = f"{ch}::{notion}"[:55]
        print(f"  {label:<57} n_fn={n:>3}  formes={n_forms}  dominante={dominant}({ratio:.0%})  {counts}{flag}")


def main(argv: list[str]) -> int:
    files = [Path(f) for f in argv] if argv else DEFAULT_FILES
    for path in files:
        if not path.exists():
            print(f"\n=== {path} === (absent, ignoré)")
            continue
        audit_file(path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
