"""Recalibrage des exercices historiques de la Première spécialité
(exercises_bank_premiere.json, identifiants < 2 281) — chantier 2, 2026-11-01.

Défaut démontré : dans cette banque, un même gabarit d'exercice est réparti
artificiellement sur les cinq niveaux (par exemple 12 dérivées de polynôme à
chacun des niveaux 1 à 5, ou « Calculer $u_{4}$ pour $u_n = n + 6$ » au niveau
Défi). Le niveau ne dépendait pas du raisonnement demandé.

Correction : chaque gabarit reçoit le niveau de la compétence qu'il mobilise
(règles ci-dessous, décidées en lisant les énoncés), et les exercices rédigés
individuellement dont le niveau était manifestement faux reçoivent un niveau
explicite (NIVEAUX_PAR_ID, relus un par un). Les exercices non concernés
(démonstrations, problèmes rédigés) gardent leur niveau. Seul le champ
`difficulty` change ; identifiants, énoncés, réponses et corrections sont
intacts. Idempotent.

Usage : python tools/recalibrer_premiere_historique.py
"""
import json
import re
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BANK_PATH = ROOT / "exercises_bank_premiere.json"
LIMITE_HISTORIQUE = 2281  # les identifiants suivants viennent du chantier 2


def _derivee_operations(t):
    if "\\dfrac" in t:
        return 3   # règle du quotient
    if re.search(r"\)\s*\(", t):
        return 2   # règle du produit
    return 1       # somme de termes usuels


def _canonique(t):
    m = re.search(r"f\(x\) = (-?)(\d*)x\^2", t)
    return 2 if m and m.group(2) in ("", "1") else 3  # a = ±1 : complétion directe


# (notion, motif de l'énoncé, niveau ou fonction de l'énoncé)
REGLES = [
    ("Généralités sur les suites", r"définie pour tout entier naturel \$n\$ par \$u_n = .*Calculer \$u_", 1),
    ("Généralités sur les suites", r"^Soit \$\(u_n\)\$ la suite définie par \$u_0", 2),
    ("Généralités sur les suites", r"^En 20\d\d, .*modélise", 2),
    ("Sens de variation d'une suite", r"^Étudier le sens de variation de la suite", lambda t: 3 if "n^2" in t else 2),
    ("Notion de limite d'une suite", r"^On donne un tableau de valeurs", 1),
    ("Suite arithmétique", r"est-elle arithmétique \? Justifier", 2),
    ("Fonction polynôme de degré 2", r"Donner les coefficients", 1),
    ("Fonction polynôme de degré 2", r"^Déterminer la forme canonique", _canonique),
    ("Fonction polynôme de degré 2", r"Dresser le tableau de variations", 2),
    ("Propriétés d'un trinôme", r"qui admet deux racines distinctes", 2),
    ("Propriétés d'un trinôme", r"sachant que .* est une racine", 3),
    ("Propriétés d'un trinôme", r"^Résoudre dans .* l'inéquation", 3),
    ("Équations du second degré", r"^Résoudre dans \$\\mathbb\{R\}\$ l'équation", 2),
    ("Fonction dérivée", r"^Calculer la dérivée de la fonction \$f\$ définie sur",
     lambda t: 2 if ("\\sqrt" in t or "\\dfrac" in t) else 1),
    ("Opérations et dérivation", r"^Calculer la dérivée de la fonction \$f\$ définie sur", _derivee_operations),
    ("Composition de fonctions et dérivation", r"^Calculer la dérivée de la fonction", 2),
    ("Nombre dérivé. Tangente", r"Exprimer le taux de variation", 2),
    ("Nombre dérivé. Tangente", r"Déterminer une équation de la tangente", 2),
    ("Nombre dérivé et extremums locaux", r"Calculer \$f'\(x\)\$ et la factoriser", 3),
    ("Fonction exponentielle", r"^(D'après la définition|En utilisant les propriétés fondamentales|Rappeler)", 1),
    ("Nouvelle notation et nombre e", r"^Résoudre dans \$\\mathbb\{R\}\$ l'équation \$e\^\{x\} = e\^\{\d+\}\$\.$", 1),
    ("Coordonnées d'un point du cercle trigonométrique", r"^On sait que .*En utilisant les symétries", 2),
    ("Repérage sur le cercle trigonométrique", r"^Un angle a pour mesure .*Déterminer sa mesure principale", 2),
    ("Fonctions cosinus et sinus", r"^Résoudre dans .* l'équation",
     lambda t: 2 if "]-\\pi ; \\pi]" in t else 3),  # intervalle d'une période : 2 ; plusieurs périodes : 3
    ("Autres définitions et propriétés", r"^Deux vecteurs .*\(angle géométrique\)", 2),
    ("Équation d'un cercle", r"Montrer qu'il s'agit de l'équation d'un cercle", 3),
]

# Exercices rédigés individuellement, relus un par un.
NIVEAUX_PAR_ID = {
    # Problèmes guidés de probabilités et d'espérance (calculs directs en plusieurs questions).
    2016: 4, 2017: 3, 2036: 3, 2037: 3, 2040: 3, 2041: 3, 2052: 3, 2053: 3, 2054: 3, 2055: 4,
    2071: 3, 2072: 3, 2073: 3, 2081: 3, 2086: 3, 2088: 3, 2089: 4, 2090: 3, 2091: 3,
    # Trigonométrie : tours complets, mesures principales, valeurs remarquables.
    2212: 3, 2216: 3, 2217: 3, 2218: 3, 2219: 3, 2220: 3, 2231: 2, 2233: 2, 2234: 2, 2244: 3, 2245: 3,
    # Second degré : paramètre retrouvé, erreur de factorisation à corriger.
    2260: 3, 2261: 3, 2262: 3, 2267: 3, 2268: 3, 2269: 3,
    # Produit scalaire et vecteur normal : erreur à analyser, deux méthodes comparées.
    2113: 3, 2157: 3,
}


def niveau(e):
    if e["id"] in NIVEAUX_PAR_ID:
        return NIVEAUX_PAR_ID[e["id"]]
    for notion, motif, lvl in REGLES:
        if e["notion"] == notion and re.search(motif, e["enonce"]):
            return lvl(e["enonce"]) if callable(lvl) else lvl
    return e["difficulty"]


def main() -> int:
    data = json.loads(BANK_PATH.read_text(encoding="utf-8"))
    changes = Counter()
    for e in data:
        if e["id"] >= LIMITE_HISTORIQUE:
            continue
        lvl = niveau(e)
        if lvl != e["difficulty"]:
            changes[(e["difficulty"], lvl)] += 1
            e["difficulty"] = lvl
    if changes:
        BANK_PATH.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"OK — {sum(changes.values())} niveau(x) corrigé(s) (ancien -> nouveau : {dict(sorted(changes.items()))})")
    return 0


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    raise SystemExit(main())
