"""Audit heuristique de la couverture taxonomique (types de raisonnement) des
banques d'exercices, en complément de check_exercise_diversity.py qui mesure
la redondance textuelle mais pas la variété des TYPES de question.

Détecte, par mot-clé/motif regex sur l'énoncé (français), la présence
probable de chacune des catégories suivantes : vrai/faux justifié, erreur à
corriger, problème contextualisé, exercice inversé (retrouver une donnée),
interprétation d'un résultat, comparaison, choix de méthode, multi-étapes
(proxy : >=4 étapes de solution), démonstration. Un exercice peut appartenir
à plusieurs catégories ; ce qui reste non catégorisé est classé "calcul
direct/à étapes" par défaut.

C'est un outil d'AUDIT (signal, pas vérité absolue) : les regex sont
imparfaites, notamment pour "contexte" qui repose sur du vocabulaire du
monde réel. Objectif : repérer vite les notions où AUCUNE catégorie hors
calcul direct n'apparaît, signe probable d'un manque de diversité de
raisonnement, à vérifier ensuite manuellement.

Usage : python -m tools.audit_exercise_taxonomy [fichier ...]
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
    ROOT / "exercises_bank.json",
    ROOT / "exercises_bank_premiere.json",
    ROOT / "exercises_generated_premiere.json",
]

PATTERNS: dict[str, re.Pattern] = {
    "vrai_faux": re.compile(
        r"vrai ou faux|vrai/faux|cette affirmation|est-elle (vraie|correcte|exacte)|"
        r"est-il (vrai|correct|exact)|r[ée]pondre par vrai ou faux",
        re.IGNORECASE,
    ),
    "erreur_correction": re.compile(
        r"\berreurs?\b|se trompe|corriger|\bun[e]? [ée]l[èe]ve\b.{0,20}(affirme|calcule|r[ée]sout|pense|propose)|"
        r"cette r[ée]solution est-elle correcte|d[ée]tecter",
        re.IGNORECASE,
    ),
    "contexte_reel": re.compile(
        r"\b(m[èe]tres?|km|kilom[èe]tres?|euros?|€|kg|kilogrammes?|litres?|population|entreprise|salari[ée]|"
        r"vitesse|trajet|prix|salaire|budget|b[ée]n[ée]fice|jardin|terrain|rectangle|piscine|r[ée]servoir|"
        r"voyage|distance parcourue|client|magasin|production|stock|voiture|v[ée]hicule|m[ée]decin|"
        r"patient|banque|placement|int[ée]r[êe]t|capital|assurance|sondage|[ée]chantillon)\b",
        re.IGNORECASE,
    ),
    "inverse_retrouver": re.compile(
        r"retrouver|d[ée]terminer .{0,15}sachant|pour quelle valeur|pour quel(le)?s? valeurs?|"
        r"quel(le)? doit [êe]tre|trouver .{0,10}tel(le)? que",
        re.IGNORECASE,
    ),
    "interpretation": re.compile(
        r"interpr[ée]ter|que peut-on en conclure|qu.en d[ée]duire|\bconclure\b|"
        r"que signifie|donner (une |la )?signification",
        re.IGNORECASE,
    ),
    "comparaison": re.compile(
        r"\bcomparer\b|lequel|quel est le plus|plus (grand|petit|avantageux|rentable|risqu[ée])|"
        r"quel(le)? (jeu|option|m[ée]thode|solution) est",
        re.IGNORECASE,
    ),
    "choix_methode": re.compile(
        r"deux m[ée]thodes|choisir une m[ée]thode|quelle m[ée]thode|deux fa[çc]ons",
        re.IGNORECASE,
    ),
    "demonstration": re.compile(
        r"^d[ée]montrer|\bmontrer que\b|\bprouver que\b|d[ée]montrer que",
        re.IGNORECASE,
    ),
}


def categorize(ex: dict) -> set[str]:
    text = ex.get("enonce", "") or ""
    cats = {name for name, pat in PATTERNS.items() if pat.search(text)}
    steps = ex.get("solution_steps") or []
    if isinstance(steps, list) and len(steps) >= 4:
        cats.add("multi_etapes")
    if not cats:
        cats.add("calcul_direct_ou_a_etapes")
    return cats


def load(path: Path) -> list[dict]:
    data = json.loads(path.read_text(encoding="utf-8"))
    return data if isinstance(data, list) else data.get("exercises", [])


def audit_file(path: Path) -> None:
    items = load(path)
    by_notion: dict[tuple, list[dict]] = defaultdict(list)
    for ex in items:
        by_notion[(ex.get("chapter_id"), ex.get("notion"))].append(ex)

    print(f"\n=== {path.name} === ({len(items)} exercices, {len(by_notion)} notions)")
    rows = []
    for (ch, notion), exs in by_notion.items():
        cat_counts = Counter()
        for ex in exs:
            for c in categorize(ex):
                cat_counts[c] += 1
        n_total = len(exs)
        # Score de variété = nb de catégories distinctes représentées (hors calcul_direct seul).
        distinct_cats = len(cat_counts)
        only_calcul = set(cat_counts) <= {"calcul_direct_ou_a_etapes"}
        rows.append((ch, notion, n_total, distinct_cats, only_calcul, cat_counts))

    rows.sort(key=lambda r: (r[4], r[3]))
    print(f"  {'Notion':<55} {'n':>4}  {'cat.':>4}  répartition")
    for ch, notion, n_total, distinct_cats, only_calcul, cat_counts in rows:
        flag = "  <== PEU/PAS DE VARIÉTÉ" if only_calcul or distinct_cats <= 1 else ""
        summary = ", ".join(f"{k}:{v}" for k, v in cat_counts.most_common())
        label = f"{ch}::{notion}"[:55]
        print(f"  {label:<55} {n_total:>4}  {distinct_cats:>4}  {summary}{flag}")


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
