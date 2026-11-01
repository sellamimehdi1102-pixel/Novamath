"""Chantier 2 (2026-11-01) — compléments de niveaux de la Troisième.

Notions dont un niveau était absent ou réduit à moins de 4 questions dans le
pool servi (banque curée + banque générée) :
- Chapitre_10 :: "Déterminer la probabilité d'un événement" — seulement les
  niveaux 2 et 3 (banque générée) : ajout des niveaux 1, 4 et 5 ;
- Chapitre_3 :: "Simplification et forme irréductible d'une fraction" et
  Chapitre_4 :: "Factoriser une somme ou une différence" — 3 questions de
  niveau 5 : ajout de 2 questions chacune.

Même principe que tools/add_troisieme_handwritten.py (ajout à la banque
curée, identifiants libres après le plus grand existant), avec en plus :
- chaque valeur annoncée est recalculée (Fraction / SymPy) avant écriture ;
- idempotent : un exercice déjà présent (même identifiant, même contenu) est
  ignoré ; un identifiant déjà pris par un autre contenu bloque l'écriture ;
- aucun énoncé identique à un énoncé de la banque curée ou générée (sinon
  generate_troisieme_exercises.py pourrait écarter un exercice déjà servi).

Usage : python tools/add_troisieme_chantier2.py
"""
import json
import sys
from fractions import Fraction as F
from math import gcd
from pathlib import Path

import sympy as sp

ROOT = Path(__file__).resolve().parent.parent
BANK_PATH = ROOT / "exercises_bank_troisieme.json"
GENERATED_PATH = ROOT / "exercises_generated_troisieme.json"
FIRST_ID = 2152

_x = sp.symbols("x")
PROBA = ("Chapitre_10", "Probabilités", "Déterminer la probabilité d'un événement")
FRACTION = ("Chapitre_3", "Fractions", "Simplification et forme irréductible d'une fraction")
FACTO = ("Chapitre_4", "Calcul littéral", "Factoriser une somme ou une différence")


def _ex(where, difficulty, enonce, answer, hint, steps, check):
    assert check(), f"valeur fausse : {enonce[:60]}"
    chapter_id, chapter, notion = where
    return {
        "enonce": enonce, "answer": answer, "hint": hint,
        "solution_steps": [f"Étape {i} — {s}" for i, s in enumerate(steps, 1)],
        "chapter_id": chapter_id, "chapter": chapter, "notion": notion, "difficulty": difficulty,
    }


def _same(a, b):
    return sp.expand(sp.sympify(a) - sp.sympify(b)) == 0


_DEUX_DES = [(a, b) for a in range(1, 7) for b in range(1, 7)]

EXERCICES = [
    # ── Probabilité d'un événement : niveau 1 ──
    _ex(PROBA, 1,
        "Une urne contient $3$ boules rouges, $5$ boules bleues et $2$ boules vertes, indiscernables au toucher. On tire une boule au hasard. Quelle est la probabilité de tirer une boule rouge ?",
        "$P = \\dfrac{3}{10}$",
        "Compte le nombre total de boules.",
        ["Il y a $3 + 5 + 2 = 10$ boules, toutes ont la même chance d'être tirées.", "$3$ boules sont rouges : $P = \\dfrac{3}{10}$."],
        lambda: F(3, 3 + 5 + 2) == F(3, 10)),
    _ex(PROBA, 1,
        "On lance un dé équilibré à six faces. Quelle est la probabilité d'obtenir un nombre pair ?",
        "$P = \\dfrac{1}{2}$",
        "Liste les résultats pairs possibles.",
        ["Les $6$ résultats sont équiprobables.", "Résultats pairs : $2$, $4$, $6$, soit $3$ issues : $P = \\dfrac{3}{6} = \\dfrac{1}{2}$."],
        lambda: F(sum(1 for k in range(1, 7) if k % 2 == 0), 6) == F(1, 2)),
    _ex(PROBA, 1,
        "La probabilité qu'il pleuve demain est $0{,}35$. Quelle est la probabilité qu'il ne pleuve pas demain ?",
        "$P = 0{,}65$",
        "« Ne pas pleuvoir » est l'événement contraire de « pleuvoir ».",
        ["La somme des probabilités d'un événement et de son contraire vaut $1$.", "$P = 1 - 0{,}35 = 0{,}65$."],
        lambda: 1 - F(35, 100) == F(65, 100)),
    _ex(PROBA, 1,
        "Une roue est partagée en $8$ secteurs de même taille, numérotés de $1$ à $8$. On la fait tourner. Quelle est la probabilité que la flèche s'arrête sur un multiple de $3$ ?",
        "$P = \\dfrac{1}{4}$",
        "Quels numéros entre $1$ et $8$ sont des multiples de $3$ ?",
        ["Les $8$ secteurs sont équiprobables.", "Multiples de $3$ : $3$ et $6$, soit $2$ issues : $P = \\dfrac{2}{8} = \\dfrac{1}{4}$."],
        lambda: F(sum(1 for k in range(1, 9) if k % 3 == 0), 8) == F(1, 4)),
    # ── niveau 4 ──
    _ex(PROBA, 4,
        "On lance deux dés équilibrés à six faces et on additionne les résultats. Quelle est la probabilité d'obtenir une somme égale à $8$ ?",
        "$P = \\dfrac{5}{36}$",
        "Construis un tableau à double entrée des $36$ issues équiprobables.",
        ["Il y a $6 \\times 6 = 36$ issues équiprobables.", "Somme $8$ : $(2 ; 6)$, $(3 ; 5)$, $(4 ; 4)$, $(5 ; 3)$, $(6 ; 2)$, soit $5$ issues.", "$P = \\dfrac{5}{36}$."],
        lambda: F(sum(1 for a, b in _DEUX_DES if a + b == 8), 36) == F(5, 36)),
    _ex(PROBA, 4,
        "Un sac contient $4$ jetons verts et des jetons rouges. On tire un jeton au hasard ; la probabilité qu'il soit vert est $\\dfrac{1}{3}$. Combien le sac contient-il de jetons rouges ?",
        "Le sac contient $8$ jetons rouges.",
        "Appelle $n$ le nombre total de jetons : $\\dfrac{4}{n} = \\dfrac{1}{3}$.",
        ["$\\dfrac{4}{n} = \\dfrac{1}{3}$, donc $n = 12$ jetons au total.", "Jetons rouges : $12 - 4 = 8$."],
        lambda: F(4, 4 + 8) == F(1, 3)),
    _ex(PROBA, 4,
        "On tire une carte au hasard dans un jeu de $32$ cartes ($8$ cartes de chacune des $4$ couleurs, dont un as par couleur). Quelle est la probabilité de tirer un as ou un cœur ?",
        "$P = \\dfrac{11}{32}$",
        "Attention à ne pas compter deux fois l'as de cœur.",
        ["Il y a $4$ as et $8$ cœurs, dont l'as de cœur compté dans les deux.", "Cartes favorables : $4 + 8 - 1 = 11$.", "$P = \\dfrac{11}{32}$."],
        lambda: F(4 + 8 - 1, 32) == F(11, 32)),
    _ex(PROBA, 4,
        "Une urne contient $2$ boules rouges et $3$ boules noires. On tire une boule, on note sa couleur, on la remet, puis on tire une seconde boule. Quelle est la probabilité d'obtenir deux boules de la même couleur ?",
        "$P = \\dfrac{13}{25}$",
        "Utilise un arbre : deux rouges ou deux noires.",
        ["Avec remise, chaque tirage donne rouge avec la probabilité $\\dfrac{2}{5}$ et noir avec $\\dfrac{3}{5}$.", "Deux rouges : $\\dfrac{2}{5} \\times \\dfrac{2}{5} = \\dfrac{4}{25}$ ; deux noires : $\\dfrac{3}{5} \\times \\dfrac{3}{5} = \\dfrac{9}{25}$.",
         "$P = \\dfrac{4}{25} + \\dfrac{9}{25} = \\dfrac{13}{25}$."],
        lambda: F(2, 5) ** 2 + F(3, 5) ** 2 == F(13, 25)),
    # ── niveau 5 ──
    _ex(PROBA, 5,
        "Une urne contient $2$ boules rouges et $3$ boules noires. Combien faut-il ajouter, au minimum, de boules rouges pour que la probabilité de tirer une boule rouge soit au moins égale à $\\dfrac{3}{4}$ ?",
        "Il faut ajouter au moins $7$ boules rouges.",
        "Avec $n$ boules rouges ajoutées, la probabilité vaut $\\dfrac{2 + n}{5 + n}$.",
        ["On cherche $n$ tel que $\\dfrac{2 + n}{5 + n} \\geqslant \\dfrac{3}{4}$.", "Comme $5 + n > 0$ : $4(2 + n) \\geqslant 3(5 + n)$, soit $8 + 4n \\geqslant 15 + 3n$, donc $n \\geqslant 7$.",
         "Vérification : avec $7$ boules ajoutées, $P = \\dfrac{9}{12} = \\dfrac{3}{4}$ ; avec $6$, $P = \\dfrac{8}{11} < \\dfrac{3}{4}$."],
        lambda: min(n for n in range(100) if F(2 + n, 5 + n) >= F(3, 4)) == 7),
    _ex(PROBA, 5,
        "On lance deux dés équilibrés à six faces et on multiplie les deux résultats. Quelle est la probabilité que le produit soit pair ?",
        "$P = \\dfrac{3}{4}$",
        "Le produit est impair seulement si les deux résultats sont impairs.",
        ["Il y a $36$ issues équiprobables.", "Produit impair : les deux dés impairs, soit $3 \\times 3 = 9$ issues.", "Produit pair : $36 - 9 = 27$ issues, $P = \\dfrac{27}{36} = \\dfrac{3}{4}$."],
        lambda: F(sum(1 for a, b in _DEUX_DES if (a * b) % 2 == 0), 36) == F(3, 4)),
    _ex(PROBA, 5,
        "Quatre jetons portent les lettres $A$, $B$, $C$ et $D$. On en tire deux au hasard, simultanément. Quelle est la probabilité que le jeton $A$ fasse partie du tirage ?",
        "$P = \\dfrac{1}{2}$",
        "Liste toutes les paires de lettres possibles.",
        ["Paires possibles : $AB$, $AC$, $AD$, $BC$, $BD$, $CD$, soit $6$ paires équiprobables.", "Paires contenant $A$ : $AB$, $AC$, $AD$, soit $3$ paires.", "$P = \\dfrac{3}{6} = \\dfrac{1}{2}$."],
        lambda: F(sum(1 for i in range(4) for j in range(i + 1, 4) if 0 in (i, j)), 6) == F(1, 2)),
    _ex(PROBA, 5,
        "Jeu 1 : on lance un dé équilibré et on gagne si l'on obtient $6$. Jeu 2 : on lance deux pièces équilibrées et on gagne si l'on obtient deux fois « pile ». Jeu 3 : on tire une carte dans un jeu de $32$ cartes et on gagne si c'est un roi ou une dame. Quel jeu offre la meilleure chance de gagner ?",
        "Les jeux 2 et 3, à égalité avec une probabilité de gagner de $\\dfrac{1}{4}$ ; le jeu 1 ($\\dfrac{1}{6}$) est le moins favorable.",
        "Calcule les trois probabilités, puis compare-les.",
        ["Jeu 1 : $P = \\dfrac{1}{6}$.", "Jeu 2 : issues $PP$, $PF$, $FP$, $FF$ ; $P = \\dfrac{1}{4}$.", "Jeu 3 : $4$ rois et $4$ dames, $P = \\dfrac{8}{32} = \\dfrac{1}{4}$.",
         "$\\dfrac{1}{6} < \\dfrac{1}{4}$ : les jeux 2 et 3 sont à égalité et plus favorables que le jeu 1."],
        lambda: F(1, 6) < F(1, 4) == F(8, 32)),
    # ── Simplification d'une fraction : niveau 5 ──
    _ex(FRACTION, 5,
        "Montrer que, pour tout entier naturel $n$, la fraction $\\dfrac{6n + 4}{9n + 6}$ est égale à une même fraction irréductible, que l'on donnera.",
        "$\\dfrac{6n + 4}{9n + 6} = \\dfrac{2(3n + 2)}{3(3n + 2)} = \\dfrac{2}{3}$ pour tout $n$.",
        "Factorise le numérateur et le dénominateur.",
        ["$6n + 4 = 2(3n + 2)$ et $9n + 6 = 3(3n + 2)$.", "$3n + 2 \\neq 0$ pour tout entier naturel $n$ : on peut simplifier par $3n + 2$.", "La fraction vaut $\\dfrac{2}{3}$, qui est irréductible."],
        lambda: all(F(6 * n + 4, 9 * n + 6) == F(2, 3) for n in range(200))),
    _ex(FRACTION, 5,
        "Rendre irréductible la fraction $\\dfrac{1\\,386}{2\\,310}$ en décomposant le numérateur et le dénominateur en produits de facteurs premiers.",
        "$\\dfrac{1\\,386}{2\\,310} = \\dfrac{3}{5}$",
        "Commence par diviser chaque nombre par $2$, puis par $3$, $5$, $7$, $11$…",
        ["$1\\,386 = 2 \\times 3^2 \\times 7 \\times 11$.", "$2\\,310 = 2 \\times 3 \\times 5 \\times 7 \\times 11$.", "Facteurs communs : $2 \\times 3 \\times 7 \\times 11 = 462$ ; $\\dfrac{1\\,386}{2\\,310} = \\dfrac{3}{5}$."],
        lambda: 2 * 9 * 7 * 11 == 1386 and 2 * 3 * 5 * 7 * 11 == 2310 and gcd(1386, 2310) == 462 and F(1386, 2310) == F(3, 5)),
    # ── Factoriser : niveau 5 ──
    _ex(FACTO, 5,
        "Factoriser l'expression $E = (2x + 1)^2 - (x - 3)^2$.",
        "$E = (x + 4)(3x - 2)$",
        "Reconnais une différence de deux carrés $a^2 - b^2 = (a - b)(a + b)$.",
        ["$E = a^2 - b^2$ avec $a = 2x + 1$ et $b = x - 3$.", "$a - b = 2x + 1 - (x - 3) = x + 4$ et $a + b = 2x + 1 + x - 3 = 3x - 2$.", "$E = (x + 4)(3x - 2)$."],
        lambda: _same("(2*x+1)**2-(x-3)**2", "(x+4)*(3*x-2)")),
    _ex(FACTO, 5,
        "Factoriser l'expression $F = (x - 2)(3x + 1) - (x - 2)(x + 5)$, puis l'écrire sous la forme $k(x - 2)^2$.",
        "$F = (x - 2)(2x - 4) = 2(x - 2)^2$",
        "Repère le facteur commun aux deux termes.",
        ["Facteur commun : $(x - 2)$.", "$F = (x - 2)\\big[(3x + 1) - (x + 5)\\big] = (x - 2)(2x - 4)$.", "$2x - 4 = 2(x - 2)$, donc $F = 2(x - 2)^2$."],
        lambda: _same("(x-2)*(3*x+1)-(x-2)*(x+5)", "2*(x-2)**2")),
    # ── Finalisation (2026-11-01) : niveaux encore sous 4 exercices dans le pool servi ──
    # Probabilité d'un événement : aucun exercice de niveau 3.
    _ex(PROBA, 3,
        r"Une urne contient $4$ boules rouges, $6$ boules bleues et des boules vertes. La probabilité de tirer une boule rouge est $0{,}2$. Combien l'urne contient-elle de boules vertes ? Quelle est la probabilité de tirer une boule verte ?",
        r"$10$ boules vertes ; $P(\text{verte}) = \dfrac{1}{2}$",
        r"$P(\text{rouge}) = \dfrac{4}{\text{nombre total de boules}}$ : déduis-en le nombre total.",
        [r"$\dfrac{4}{n} = 0{,}2$, donc $n = 20$ boules en tout.", r"Boules vertes : $20 - 4 - 6 = 10$.", r"$P(\text{verte}) = \dfrac{10}{20} = \dfrac{1}{2}$."],
        lambda: 4 / F(1, 5) == 20 and F(20 - 4 - 6, 20) == F(1, 2)),
    _ex(PROBA, 3,
        r"On tire une carte au hasard dans un jeu de $32$ cartes ($8$ cartes par couleur, dont un roi par couleur). Quelle est la probabilité d'obtenir un cœur ou un roi ?",
        r"$P = \dfrac{11}{32}$",
        r"Attention au roi de cœur : il est à la fois un cœur et un roi.",
        [r"Il y a $8$ cœurs et $4$ rois, dont le roi de cœur compté deux fois.", r"Cartes favorables : $8 + 4 - 1 = 11$.", r"$P = \dfrac{11}{32}$."],
        lambda: F(sum(1 for c in range(4) for r in range(8) if c == 0 or r == 0), 32) == F(11, 32)),
    _ex(PROBA, 3,
        r"Un dé équilibré a six faces numérotées $1$, $1$, $2$, $2$, $2$ et $3$. On le lance une fois. Quelle est la probabilité d'obtenir $2$ ? Et celle d'obtenir un nombre impair ?",
        r"$P(2) = \dfrac{1}{2}$ et $P(\text{impair}) = \dfrac{1}{2}$",
        r"Les six faces sont équiprobables, mais plusieurs portent le même numéro.",
        [r"$3$ faces sur $6$ portent le $2$ : $P(2) = \dfrac{3}{6} = \dfrac{1}{2}$.", r"Faces impaires : les deux « $1$ » et le « $3$ », soit $3$ faces.", r"$P(\text{impair}) = \dfrac{3}{6} = \dfrac{1}{2}$."],
        lambda: F([1, 1, 2, 2, 2, 3].count(2), 6) == F(1, 2) and F(sum(1 for v in [1, 1, 2, 2, 2, 3] if v % 2), 6) == F(1, 2)),
    _ex(PROBA, 3,
        r"Un sac contient $20$ jetons numérotés de $1$ à $20$. On tire un jeton au hasard. Quelle est la probabilité que son numéro soit un nombre premier ?",
        r"$P = \dfrac{8}{20} = \dfrac{2}{5}$",
        r"Liste les nombres premiers inférieurs ou égaux à $20$ (attention : $1$ n'est pas premier).",
        [r"Nombres premiers de $1$ à $20$ : $2$, $3$, $5$, $7$, $11$, $13$, $17$, $19$, soit $8$ nombres.", r"$P = \dfrac{8}{20} = \dfrac{2}{5}$."],
        lambda: F(sum(1 for v in range(1, 21) if sp.isprime(v)), 20) == F(2, 5)),
    # Développer avec la simple distributivité : niveaux 1 et 3 (3 exercices chacun).
    _ex(("Chapitre_4", "Calcul littéral", "Développer un produit avec la simple distributivité"), 1,
        r"Développer l'expression $3(x + 2)$.", r"$3x + 6$", r"Multiplie $3$ par chacun des deux termes de la parenthèse.",
        [r"$3(x + 2) = 3 \times x + 3 \times 2$.", r"$= 3x + 6$."], lambda: _same("3*(x+2)", "3*x+6")),
    _ex(("Chapitre_4", "Calcul littéral", "Développer un produit avec la simple distributivité"), 3,
        r"Développer et réduire l'expression $A = 2(3x - 1) - 4(x - 5)$.", r"$A = 2x + 18$",
        r"Attention au signe $-$ devant $4$ : il change le signe de chaque terme de la seconde parenthèse.",
        [r"$2(3x - 1) = 6x - 2$.", r"$-4(x - 5) = -4x + 20$.", r"$A = 6x - 2 - 4x + 20 = 2x + 18$."], lambda: _same("2*(3*x-1)-4*(x-5)", "2*x+18")),
    # Calculer une image : niveau 3 (3 exercices).
    _ex(("Chapitre_7", "Fonctions", "Calculer une image à partir de l'expression d'une fonction"), 3,
        r"On donne $f(x) = -2x^2 + x - 3$. Calculer $f(-2)$.", r"$f(-2) = -13$",
        r"Calcule d'abord $(-2)^2$, puis multiplie par $-2$.",
        [r"$(-2)^2 = 4$, donc $-2 \times (-2)^2 = -8$.", r"$f(-2) = -8 + (-2) - 3 = -13$."], lambda: (-2 * _x**2 + _x - 3).subs(_x, -2) == -13),
]


def main() -> int:
    data = json.loads(BANK_PATH.read_text(encoding="utf-8"))
    generated = json.loads(GENERATED_PATH.read_text(encoding="utf-8"))
    by_id = {e["id"]: e for e in data}
    known_enonces = {e["enonce"] for e in data} | {e["enonce"] for e in generated}
    generated_ids = {e["id"] for e in generated}
    added = 0
    for i, ex in enumerate(EXERCICES):
        ex = {**ex, "id": FIRST_ID + i}
        if ex["id"] in generated_ids:
            print(f"ERREUR — identifiant {ex['id']} déjà utilisé par la banque générée", file=sys.stderr)
            return 1
        if ex["id"] in by_id:
            if by_id[ex["id"]] != ex:
                print(f"ERREUR — identifiant {ex['id']} déjà pris par un autre exercice", file=sys.stderr)
                return 1
            continue
        if ex["enonce"] in known_enonces:
            print(f"ERREUR — énoncé déjà présent : {ex['enonce'][:60]}", file=sys.stderr)
            return 1
        data.append(ex)
        added += 1
    BANK_PATH.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"OK — {added} exercice(s) ajouté(s) ; banque : {len(data)} exercices.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
