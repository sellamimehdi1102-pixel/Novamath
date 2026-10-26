"""Source unique de la banque d'exercices CURÉS de Quatrième
(exercises_bank_quatrieme.json) — chantier "Quatrième — chapitre pilote
Pythagore" (2026-10-24).

Pourquoi un module Python plutôt qu'un JSON édité à la main : chaque exercice
est rédigé individuellement (énoncé, indice, correction), mais toutes les
valeurs numériques qu'il annonce (carrés, sommes, racines, arrondis, verdict
« rectangle ou non ») sont RECALCULÉES ici par des contrôles explicites
(`checks`, `step_checks`, `rect`). `main()` refuse d'écrire le fichier si un
seul contrôle échoue ; tests/test_quatrieme_pythagore.py rejoue les mêmes
contrôles et vérifie que le JSON servi est identique à ce module.

Conventions (voir aussi le profil "quatrieme" de curriculum_registry.py) :
- identifiants : 40 000 + 1 000 × chapitre + 100 × notion + k (Chapitre_8,
  notion 1 → 48 101...), écrits en dur, jamais positionnels : un exercice
  garde son identifiant si l'on en insère un autre (stabilité des
  mini-quiz, de l'historique et de la progression) ;
- `notion` = titre EXACT de la notion dans cours_quatrieme/chapitre_8.json
  (même convention que les autres classes : lien cours ↔ exercices, bouton
  « Passer à la pratique », chatbot) ;
- `difficulty` 1 à 4 : 1 découverte, 2 application, 3 raisonnement,
  4 problème à plusieurs étapes ;
- programme de 4e : racines carrées laissées sous la forme $\\sqrt{n}$ (pas de
  simplification $a\\sqrt{b}$, hors programme), valeurs approchées à la
  précision demandée, virgule décimale française ($2{,}5$).

Usage : python tools/build_quatrieme_bank.py
"""
import json
import sys
from dataclasses import dataclass, field
from decimal import ROUND_HALF_UP, Decimal, getcontext
from pathlib import Path
from typing import Optional

ROOT = Path(__file__).resolve().parent.parent
OUTPUT_PATH = ROOT / "exercises_bank_quatrieme.json"
CHAPTER_ID = "Chapitre_8"

getcontext().prec = 60

N1 = "Triangle rectangle et égalité de Pythagore"
N2 = "Carrés et racines carrées"
N3 = "Calculer une longueur avec le théorème de Pythagore"
N4 = "Démontrer qu'un triangle est rectangle ou non"
N5 = "Résoudre un problème avec le théorème de Pythagore"
NOTIONS = (N1, N2, N3, N4, N5)


# ── Outils de contrôle (jamais utilisés pour écrire le texte des exercices,
# uniquement pour vérifier les valeurs qu'il annonce) ────────────────────────

def D(x) -> Decimal:
    return x if isinstance(x, Decimal) else Decimal(str(x))


def num(x) -> str:
    """Écriture LaTeX française d'une valeur exacte : 16 -> "16",
    2.5 -> "2{,}5"."""
    x = D(x)
    if x == x.to_integral_value():
        return str(int(x))
    return format(x.normalize(), "f").replace(".", "{,}")


def rnd(x, decimals: int) -> str:
    """Arrondi (au plus proche) à `decimals` décimales, écrit en français."""
    return num(D(x).quantize(Decimal(1).scaleb(-decimals), rounding=ROUND_HALF_UP))


def sq(x) -> Decimal:
    return D(x) * D(x)


def root(x) -> Decimal:
    x = D(x)
    if x < 0:
        raise ValueError(f"racine carrée d'un nombre négatif : {x}")
    return x.sqrt()


def exact_root(x) -> Optional[Decimal]:
    """Racine exacte si `x` est le carré d'un décimal, sinon None."""
    r = root(x)
    r = r.quantize(Decimal(1).scaleb(-20)).normalize()
    return r if r * r == D(x) else None


def hyp(a, b) -> Decimal:
    return root(sq(a) + sq(b))


def leg(c, a) -> Decimal:
    if not D(c) > D(a):
        raise ValueError(f"l'hypoténuse {c} doit être strictement plus longue que {a}")
    return root(sq(c) - sq(a))


@dataclass(frozen=True)
class R:
    """Longueur √n représentée EXACTEMENT (son carré vaut n) : un verdict
    « rectangle ou non » ne doit jamais dépendre d'une racine approchée."""
    n: object


def _square(x) -> Decimal:
    return D(x.n) if isinstance(x, R) else sq(x)


def is_right(a, b, c) -> bool:
    x, y, z = sorted(_square(s) for s in (a, b, c))
    return x + y == z


@dataclass(frozen=True)
class E:
    id: int
    notion: str
    difficulty: int
    enonce: str
    answer: str
    hint: str
    steps: tuple
    # Chaînes (calculées par les outils ci-dessus) qui DOIVENT apparaître
    # dans `answer` / dans la correction.
    checks: tuple = ()
    step_checks: tuple = ()
    # (a, b, c, attendu) : le triangle de côtés a, b, c est-il rectangle ?
    # `answer` doit alors commencer par "Oui" ou "Non" en conséquence.
    rect: Optional[tuple] = None
    extra: dict = field(default_factory=dict)

    def to_json(self) -> dict:
        return {
            "id": self.id,
            "chapter_id": CHAPTER_ID,
            "notion": self.notion,
            "difficulty": self.difficulty,
            "enonce": self.enonce,
            "answer": self.answer,
            "hint": self.hint,
            "solution_steps": list(self.steps),
        }


def S(*steps):
    """Numérote les étapes de correction (même présentation que les
    exercices générés : « Étape n — ... »)."""
    return tuple(f"Étape {i} — {s}" for i, s in enumerate(steps, 1))


# ═════════════════════════════════════════════════════════════════════════
# Notion 1 — Triangle rectangle et égalité de Pythagore (48 1xx)
# ═════════════════════════════════════════════════════════════════════════
EXERCISES = [
    E(48101, N1, 1,
      "Le triangle $ABC$ est rectangle en $A$. Quel côté est son hypoténuse ?",
      "L'hypoténuse est le côté $[BC]$.",
      "L'hypoténuse est le côté situé en face de l'angle droit.",
      S("L'angle droit est au sommet $A$.",
        "Le côté opposé au sommet $A$ est le seul côté qui ne passe pas par $A$ : c'est $[BC]$.",
        "Conclusion : l'hypoténuse du triangle $ABC$ est $[BC]$.")),
    E(48102, N1, 1,
      "Le triangle $EFG$ est rectangle en $F$. Nommer son hypoténuse, puis les deux côtés de l'angle droit.",
      "Hypoténuse : $[EG]$. Côtés de l'angle droit : $[FE]$ et $[FG]$.",
      "Les deux côtés de l'angle droit partent du sommet de l'angle droit.",
      S("L'angle droit est en $F$.",
        "Les côtés de l'angle droit sont les deux côtés qui partent de $F$ : $[FE]$ et $[FG]$.",
        "Le troisième côté, $[EG]$, est opposé à l'angle droit : c'est l'hypoténuse.")),
    E(48103, N1, 1,
      "Dans le triangle $MNP$, le codage de la figure indique un angle droit au sommet $P$. Écrire l'égalité de Pythagore de ce triangle.",
      "$MN^2 = PM^2 + PN^2$",
      "Commence par repérer l'hypoténuse : elle doit être seule d'un côté du signe $=$.",
      S("Le triangle $MNP$ est rectangle en $P$ : son hypoténuse est le côté opposé à $P$, c'est-à-dire $[MN]$.",
        "Les côtés de l'angle droit sont $[PM]$ et $[PN]$.",
        "D'après le théorème de Pythagore : $MN^2 = PM^2 + PN^2$.")),
    E(48104, N1, 1,
      "Le triangle $RST$ est rectangle en $T$. Parmi les trois égalités suivantes, laquelle est l'égalité de Pythagore de ce triangle ? (a) $RT^2 = RS^2 + ST^2$ ; (b) $RS^2 = RT^2 + TS^2$ ; (c) $ST^2 = SR^2 + RT^2$.",
      "L'égalité (b) : $RS^2 = RT^2 + TS^2$.",
      "Quel côté ne contient pas la lettre $T$ ?",
      S("Le triangle est rectangle en $T$, donc l'hypoténuse est le côté opposé à $T$ : $[RS]$.",
        "Dans l'égalité de Pythagore, l'hypoténuse est seule dans un membre : c'est le cas de l'égalité (b) seulement.",
        "Les égalités (a) et (c) isolent un côté de l'angle droit : elles sont fausses.")),
    E(48105, N1, 1,
      "Le triangle $DEF$ est rectangle et ses côtés mesurent $3$ cm, $4$ cm et $5$ cm. Sans aucun calcul, donner la longueur de son hypoténuse.",
      "L'hypoténuse mesure $5$ cm.",
      "Que sait-on de la longueur de l'hypoténuse par rapport aux deux autres côtés ?",
      S("Dans un triangle rectangle, l'hypoténuse est le plus long des trois côtés.",
        "Le plus long côté mesure $5$ cm.",
        "Conclusion : l'hypoténuse mesure $5$ cm.")),
    E(48106, N1, 1,
      "Le triangle $IJK$ est rectangle en $J$, avec $IJ = 3$ cm et $JK = 4$ cm. Calculer $IK^2$.",
      "$IK^2 = 25$",
      "Écris d'abord l'égalité de Pythagore, en isolant l'hypoténuse $[IK]$.",
      S("Le triangle $IJK$ est rectangle en $J$, donc son hypoténuse est $[IK]$.",
        "D'après le théorème de Pythagore : $IK^2 = IJ^2 + JK^2$.",
        "$IK^2 = 3^2 + 4^2 = 9 + 16 = 25$."),
      checks=(num(sq(3) + sq(4)),)),
    E(48107, N1, 2,
      "Le triangle $ABC$ est rectangle en $C$, avec $AC = 2{,}5$ cm et $BC = 6$ cm. Calculer $AB^2$.",
      "$AB^2 = 42{,}25$",
      "Attention au carré d'un nombre décimal : $2{,}5^2 = 2{,}5 \\times 2{,}5$.",
      S("Le triangle $ABC$ est rectangle en $C$, donc son hypoténuse est $[AB]$.",
        "D'après le théorème de Pythagore : $AB^2 = AC^2 + BC^2$.",
        "$AB^2 = 2{,}5^2 + 6^2 = 6{,}25 + 36 = 42{,}25$."),
      checks=(num(sq("2.5") + sq(6)),), step_checks=(num(sq("2.5")),)),
    E(48108, N1, 2,
      "Le triangle $GHI$ est rectangle en $H$. On sait que $GI^2 = 100$ et $GH^2 = 36$. Calculer $HI^2$.",
      "$HI^2 = 64$",
      "Écris l'égalité de Pythagore, puis cherche ce qu'il faut ajouter à $36$ pour obtenir $100$.",
      S("Le triangle est rectangle en $H$ : l'hypoténuse est $[GI]$ et $GI^2 = GH^2 + HI^2$.",
        "On remplace : $100 = 36 + HI^2$.",
        "Donc $HI^2 = 100 - 36 = 64$."),
      checks=(num(100 - 36),)),
    E(48109, N1, 2,
      "$ABCD$ est un rectangle. Écrire l'égalité de Pythagore dans le triangle $ABC$, puis dans le triangle $ACD$.",
      "$AC^2 = AB^2 + BC^2$ et $AC^2 = AD^2 + DC^2$.",
      "Les quatre angles d'un rectangle sont droits : repère l'angle droit de chaque triangle.",
      S("Dans le rectangle $ABCD$, l'angle en $B$ est droit : le triangle $ABC$ est rectangle en $B$, d'hypoténuse $[AC]$, donc $AC^2 = AB^2 + BC^2$.",
        "L'angle en $D$ est droit : le triangle $ACD$ est rectangle en $D$, d'hypoténuse $[AC]$, donc $AC^2 = AD^2 + DC^2$.",
        "La diagonale $[AC]$ est l'hypoténuse des deux triangles.")),
    E(48110, N1, 2,
      "Écrire l'égalité de Pythagore pour un triangle $LMN$ rectangle en $L$, puis l'écrire sous la forme qui permet de calculer $LM^2$.",
      "$MN^2 = LM^2 + LN^2$, donc $LM^2 = MN^2 - LN^2$.",
      "Pour isoler $LM^2$, il faut retirer $LN^2$ aux deux membres.",
      S("Le triangle est rectangle en $L$ : l'hypoténuse est $[MN]$, et $MN^2 = LM^2 + LN^2$.",
        "On soustrait $LN^2$ aux deux membres : $MN^2 - LN^2 = LM^2$.",
        "Conclusion : $LM^2 = MN^2 - LN^2$ (on soustrait quand on cherche un côté de l'angle droit).")),
    E(48111, N1, 2,
      "Le triangle $PQR$ est isocèle et rectangle en $P$, avec $PQ = 7$ cm. Calculer $QR^2$.",
      "$QR^2 = 98$",
      "Dans un triangle isocèle en $P$, les deux côtés issus de $P$ ont la même longueur.",
      S("Le triangle est isocèle en $P$, donc $PR = PQ = 7$ cm.",
        "Il est rectangle en $P$ : l'hypoténuse est $[QR]$ et $QR^2 = PQ^2 + PR^2$.",
        "$QR^2 = 7^2 + 7^2 = 49 + 49 = 98$."),
      checks=(num(sq(7) * 2),)),
    E(48112, N1, 2,
      "Sacha étudie un triangle $XYZ$ rectangle en $X$ et écrit : $XY^2 = XZ^2 + YZ^2$. Son égalité est-elle correcte ? Si non, la corriger.",
      "Non. L'hypoténuse est $[YZ]$ : l'égalité correcte est $YZ^2 = XY^2 + XZ^2$.",
      "Quel est le côté opposé au sommet de l'angle droit ?",
      S("Le triangle est rectangle en $X$ : l'hypoténuse est le côté opposé à $X$, c'est-à-dire $[YZ]$.",
        "Sacha a isolé $XY^2$, qui est le carré d'un côté de l'angle droit : son égalité est fausse.",
        "Égalité correcte : $YZ^2 = XY^2 + XZ^2$.")),
    E(48113, N1, 3,
      "Dans un triangle $ABC$ rectangle en $A$, on sait que $AB^2 = 20$ et $AC^2 = 29$. Calculer $BC^2$, puis ranger les longueurs $AB$, $AC$ et $BC$ dans l'ordre croissant, sans calculer aucune racine.",
      "$BC^2 = 49$ et $AB < AC < BC$.",
      "Pour des longueurs, le plus petit carré correspond à la plus petite longueur.",
      S("Le triangle est rectangle en $A$ : $BC^2 = AB^2 + AC^2 = 20 + 29 = 49$.",
        "On compare les carrés : $20 < 29 < 49$, c'est-à-dire $AB^2 < AC^2 < BC^2$.",
        "Des longueurs positives sont rangées dans le même ordre que leurs carrés : $AB < AC < BC$."),
      checks=(num(20 + 29),)),
    E(48114, N1, 3,
      "On sait que le triangle $KLM$ est rectangle, et que $KL = 8$ cm, $LM = 15$ cm et $KM = 17$ cm. En quel sommet est l'angle droit ? Écrire l'égalité de Pythagore correspondante.",
      "L'angle droit est en $L$ et $KM^2 = KL^2 + LM^2$.",
      "L'hypoténuse est le plus long côté ; l'angle droit est le sommet qui lui est opposé.",
      S("Le triangle est rectangle, donc son hypoténuse est son plus long côté : $[KM]$, qui mesure $17$ cm.",
        "Le sommet opposé à $[KM]$ est $L$ : l'angle droit est en $L$.",
        "Égalité de Pythagore : $KM^2 = KL^2 + LM^2$ (on vérifie : $289 = 64 + 225$)."),
      step_checks=(num(sq(17)), num(sq(8)), num(sq(15)))),
    E(48115, N1, 3,
      "Dans un triangle $ABC$, $H$ est le point du segment $[BC]$ tel que les droites $(AH)$ et $(BC)$ sont perpendiculaires. Écrire l'égalité de Pythagore dans le triangle $ABH$, puis dans le triangle $AHC$.",
      "$AB^2 = AH^2 + HB^2$ et $AC^2 = AH^2 + HC^2$.",
      "Les deux triangles ont leur angle droit au même point.",
      S("Comme $(AH) \\perp (BC)$, les triangles $ABH$ et $AHC$ sont rectangles en $H$.",
        "Dans $ABH$, l'hypoténuse est $[AB]$ : $AB^2 = AH^2 + HB^2$.",
        "Dans $AHC$, l'hypoténuse est $[AC]$ : $AC^2 = AH^2 + HC^2$.")),
    E(48116, N1, 3,
      "Les côtés de l'angle droit d'un triangle rectangle mesurent $6$ cm et $8$ cm. Un élève affirme : « l'hypoténuse mesure $6 + 8 = 14$ cm ». Montrer que c'est faux, puis donner la longueur de l'hypoténuse.",
      "C'est faux : le carré de l'hypoténuse vaut $100$, alors que $14^2 = 196$. L'hypoténuse mesure $10$ cm.",
      "Le théorème relie les carrés des longueurs, pas les longueurs elles-mêmes.",
      S("D'après le théorème de Pythagore, le carré de l'hypoténuse vaut $6^2 + 8^2 = 36 + 64 = 100$.",
        "Or $14^2 = 196 \\neq 100$ : l'hypoténuse ne mesure pas $14$ cm.",
        "Le nombre positif dont le carré est $100$ est $10$ : l'hypoténuse mesure $10$ cm."),
      checks=(num(sq(6) + sq(8)), num(sq(14)), num(hyp(6, 8)))),
    E(48117, N1, 4,
      "Le triangle $ABC$ est rectangle en $A$, avec $AB = x$ et $AC = 3x$ (en cm, $x$ est un nombre positif). Exprimer $BC^2$ en fonction de $x$, puis calculer $BC^2$ pour $x = 2$.",
      "$BC^2 = 10x^2$ ; pour $x = 2$, $BC^2 = 40$.",
      "$(3x)^2 = 3x \\times 3x$ : calcule ce produit avant d'additionner.",
      S("Le triangle est rectangle en $A$ : $BC^2 = AB^2 + AC^2 = x^2 + (3x)^2$.",
        "$(3x)^2 = 3x \\times 3x = 9x^2$, donc $BC^2 = x^2 + 9x^2 = 10x^2$.",
        "Pour $x = 2$ : $BC^2 = 10 \\times 2^2 = 10 \\times 4 = 40$."),
      checks=(num(10 * sq(2)),)),
    E(48118, N1, 4,
      "$ABCD$ est un carré de côté $5$ cm et $O$ est son centre. On rappelle que les diagonales d'un carré sont perpendiculaires, de même longueur et se coupent en leur milieu. Écrire l'égalité de Pythagore dans le triangle $AOB$, puis montrer que $OA^2 = 12{,}5$.",
      "$AB^2 = OA^2 + OB^2$ ; comme $OA = OB$, $2 \\times OA^2 = 25$, donc $OA^2 = 12{,}5$.",
      "Commence par justifier que le triangle $AOB$ est rectangle, et repère son hypoténuse.",
      S("Les diagonales sont perpendiculaires en $O$ : le triangle $AOB$ est rectangle en $O$, d'hypoténuse $[AB]$.",
        "D'après le théorème de Pythagore : $AB^2 = OA^2 + OB^2$.",
        "Les diagonales ont la même longueur et se coupent en leur milieu, donc $OA = OB$, et $5^2 = 2 \\times OA^2$, soit $25 = 2 \\times OA^2$.",
        "Donc $OA^2 = 25 \\div 2 = 12{,}5$."),
      checks=(num(sq(5) / 2),)),

    # ═════════════════════════════════════════════════════════════════════
    # Notion 2 — Carrés et racines carrées (48 2xx)
    # ═════════════════════════════════════════════════════════════════════
    E(48201, N2, 1,
      "Calculer $7^2$, $11^2$ et $12^2$.",
      "$7^2 = 49$ ; $11^2 = 121$ ; $12^2 = 144$.",
      "Le carré d'un nombre est ce nombre multiplié par lui-même.",
      S("$7^2 = 7 \\times 7 = 49$.",
        "$11^2 = 11 \\times 11 = 121$.",
        "$12^2 = 12 \\times 12 = 144$."),
      checks=(num(sq(7)), num(sq(11)), num(sq(12)))),
    E(48202, N2, 1,
      "Donner la valeur de $\\sqrt{64}$ et de $\\sqrt{81}$, en justifiant.",
      "$\\sqrt{64} = 8$ et $\\sqrt{81} = 9$.",
      "Cherche le nombre positif dont le carré vaut $64$, puis $81$.",
      S("$8$ est positif et $8^2 = 64$, donc $\\sqrt{64} = 8$.",
        "$9$ est positif et $9^2 = 81$, donc $\\sqrt{81} = 9$."),
      checks=(num(root(64)), num(root(81)))),
    E(48203, N2, 1,
      "Parmi les nombres $36$, $50$, $121$, $90$ et $144$, lesquels sont des carrés parfaits (carrés d'un nombre entier) ?",
      "$36$, $121$ et $144$.",
      "Récite les carrés des entiers de $1$ à $12$.",
      S("$36 = 6^2$, $121 = 11^2$ et $144 = 12^2$ sont des carrés parfaits.",
        "$7^2 = 49 < 50 < 64 = 8^2$ : $50$ n'est pas un carré parfait.",
        "$9^2 = 81 < 90 < 100 = 10^2$ : $90$ n'est pas un carré parfait."),
      checks=("36", "121", "144")),
    E(48204, N2, 1,
      "Calculer $1{,}5^2$ et $0{,}3^2$.",
      "$1{,}5^2 = 2{,}25$ et $0{,}3^2 = 0{,}09$.",
      "$0{,}3^2 = 0{,}3 \\times 0{,}3$ : compte les chiffres après la virgule dans le résultat.",
      S("$1{,}5^2 = 1{,}5 \\times 1{,}5 = 2{,}25$.",
        "$0{,}3^2 = 0{,}3 \\times 0{,}3 = 0{,}09$ (et non $0{,}9$ : deux chiffres après la virgule, car $3 \\times 3 = 9$ et $0{,}1 \\times 0{,}1 = 0{,}01$)."),
      checks=(num(sq("1.5")), num(sq("0.3")))),
    E(48205, N2, 1,
      "Compléter : $\\sqrt{\\dots} = 10$ et $\\sqrt{49} = \\dots$",
      "$\\sqrt{100} = 10$ et $\\sqrt{49} = 7$.",
      "$\\sqrt{a} = b$ signifie que $b$ est positif et que $b^2 = a$.",
      S("$10^2 = 100$ et $10$ est positif, donc $\\sqrt{100} = 10$.",
        "$7^2 = 49$ et $7$ est positif, donc $\\sqrt{49} = 7$."),
      checks=(num(sq(10)), num(root(49)))),
    E(48206, N2, 1,
      "Le carré d'un nombre positif vaut $1$. Quel est ce nombre ? Même question si le carré vaut $0$.",
      "Ce nombre est $1$ dans le premier cas, et $0$ dans le second.",
      "Pense à $1 \\times 1$ et à $0 \\times 0$.",
      S("$1^2 = 1$ et $1$ est positif, donc $\\sqrt{1} = 1$.",
        "$0^2 = 0$, donc $\\sqrt{0} = 0$.")),
    E(48208, N2, 1,
      "Un carré a une aire de $49$ cm$^2$. Quelle est la longueur de son côté ?",
      "Le côté mesure $7$ cm.",
      "L'aire d'un carré de côté $c$ est $c^2$.",
      S("Si le côté mesure $c$ cm, l'aire est $c^2$ cm$^2$, donc $c^2 = 49$.",
        "$c$ est une longueur, donc un nombre positif : $c = \\sqrt{49} = 7$.",
        "Le côté mesure $7$ cm."),
      checks=(num(root(49)),)),
    E(48207, N2, 2,
      "Calculer $\\sqrt{9} + \\sqrt{16}$, puis $\\sqrt{9 + 16}$. Que constate-t-on ?",
      "$\\sqrt{9} + \\sqrt{16} = 7$ et $\\sqrt{9 + 16} = 5$ : les résultats sont différents.",
      "Dans $\\sqrt{9 + 16}$, on calcule d'abord la somme sous la racine.",
      S("$\\sqrt{9} + \\sqrt{16} = 3 + 4 = 7$.",
        "$\\sqrt{9 + 16} = \\sqrt{25} = 5$.",
        "$7 \\neq 5$ : la racine carrée d'une somme n'est pas la somme des racines carrées."),
      checks=(num(root(9) + root(16)), num(root(9 + 16)))),
    E(48209, N2, 2,
      "Encadrer $\\sqrt{30}$ entre deux nombres entiers consécutifs.",
      "$5 < \\sqrt{30} < 6$",
      "Cherche les deux carrés parfaits consécutifs qui encadrent $30$.",
      S("$5^2 = 25$ et $6^2 = 36$, donc $25 < 30 < 36$.",
        "Les racines carrées sont rangées dans le même ordre que les nombres : $\\sqrt{25} < \\sqrt{30} < \\sqrt{36}$.",
        "Donc $5 < \\sqrt{30} < 6$."),
      checks=(str(int(root(30))), str(int(root(30)) + 1))),
    E(48210, N2, 2,
      "À l'aide de la calculatrice, donner la valeur arrondie au dixième, puis au centième, de $\\sqrt{20}$.",
      "$\\sqrt{20} \\approx 4{,}5$ au dixième et $\\sqrt{20} \\approx 4{,}47$ au centième.",
      "Regarde le chiffre qui suit celui de la précision demandée pour savoir s'il faut arrondir au-dessus.",
      S("La calculatrice affiche $\\sqrt{20} \\approx 4{,}4721$.",
        "Au dixième : le chiffre des centièmes est $7 \\geq 5$, on arrondit au-dessus : $4{,}5$.",
        "Au centième : le chiffre des millièmes est $2 < 5$, on garde : $4{,}47$."),
      checks=(rnd(root(20), 1), rnd(root(20), 2)), step_checks=(rnd(root(20), 4),)),
    E(48211, N2, 2,
      "Calculer $\\sqrt{0{,}25}$ et $\\sqrt{1{,}44}$ sans calculatrice.",
      "$\\sqrt{0{,}25} = 0{,}5$ et $\\sqrt{1{,}44} = 1{,}2$.",
      "Pense à $5^2 = 25$ et à $12^2 = 144$, puis place la virgule.",
      S("$0{,}5^2 = 0{,}25$ et $0{,}5$ est positif, donc $\\sqrt{0{,}25} = 0{,}5$.",
        "$1{,}2^2 = 1{,}44$ et $1{,}2$ est positif, donc $\\sqrt{1{,}44} = 1{,}2$."),
      checks=(num(exact_root("0.25")), num(exact_root("1.44")))),
    E(48212, N2, 2,
      "Calculer $(\\sqrt{13})^2$ et $\\sqrt{13^2}$.",
      "$(\\sqrt{13})^2 = 13$ et $\\sqrt{13^2} = 13$.",
      "Reviens à la définition : $\\sqrt{13}$ est le nombre positif dont le carré vaut $13$.",
      S("Par définition, le carré de $\\sqrt{13}$ est $13$ : $(\\sqrt{13})^2 = 13$.",
        "$13^2 = 169$ et $\\sqrt{169} = 13$ car $13$ est positif et $13^2 = 169$.",
        "Pour tout nombre positif $a$ : $(\\sqrt{a})^2 = a$ et $\\sqrt{a^2} = a$."),
      step_checks=(num(sq(13)),)),
    E(48213, N2, 2,
      "Le nombre $\\sqrt{-9}$ existe-t-il ? Justifier.",
      "Non, $\\sqrt{-9}$ n'existe pas.",
      "Un carré peut-il être négatif ?",
      S("Le carré d'un nombre est toujours positif ou nul (par exemple $3^2 = 9$ et $(-3)^2 = 9$).",
        "Aucun nombre n'a donc pour carré $-9$.",
        "La racine carrée n'est définie que pour les nombres positifs : $\\sqrt{-9}$ n'existe pas.")),
    E(48214, N2, 2,
      "Ranger dans l'ordre croissant les nombres $\\sqrt{50}$ ; $7$ ; $7{,}2$, sans calculatrice.",
      "$7 < \\sqrt{50} < 7{,}2$",
      "Compare les carrés de ces trois nombres positifs.",
      S("$7^2 = 49$, $(\\sqrt{50})^2 = 50$ et $7{,}2^2 = 51{,}84$.",
        "$49 < 50 < 51{,}84$.",
        "Des nombres positifs sont rangés dans le même ordre que leurs carrés : $7 < \\sqrt{50} < 7{,}2$."),
      step_checks=(num(sq("7.2")),)),
    E(48215, N2, 3,
      "Un carré a une aire de $32$ cm$^2$. Donner la valeur exacte de la longueur de son côté, puis sa valeur arrondie au millimètre.",
      "Le côté mesure $\\sqrt{32}$ cm, soit environ $5{,}7$ cm.",
      "Au millimètre près en centimètres, c'est un arrondi au dixième.",
      S("Si le côté mesure $c$ cm, alors $c^2 = 32$ et, comme $c$ est positif, $c = \\sqrt{32}$.",
        "La calculatrice donne $\\sqrt{32} \\approx 5{,}657$.",
        "$1$ mm $= 0{,}1$ cm : on arrondit au dixième, $c \\approx 5{,}7$ cm."),
      checks=(rnd(root(32), 1),), step_checks=(rnd(root(32), 3),)),
    E(48216, N2, 3,
      "Sans calculatrice, trouver l'entier le plus proche de $\\sqrt{90}$.",
      "L'entier le plus proche de $\\sqrt{90}$ est $9$.",
      "Encadre d'abord $\\sqrt{90}$ entre deux entiers, puis compare $90$ au carré de leur milieu.",
      S("$9^2 = 81 < 90 < 100 = 10^2$, donc $9 < \\sqrt{90} < 10$.",
        "Le milieu de $9$ et $10$ est $9{,}5$, et $9{,}5^2 = 90{,}25 > 90$, donc $\\sqrt{90} < 9{,}5$.",
        "$\\sqrt{90}$ est entre $9$ et $9{,}5$ : l'entier le plus proche est $9$."),
      checks=(rnd(root(90), 0),), step_checks=(num(sq("9.5")),)),
    E(48217, N2, 3,
      "Trouver tous les nombres entiers $n$ tels que $\\sqrt{n}$ soit strictement compris entre $4$ et $5$.",
      "Les entiers de $17$ à $24$ : $17$, $18$, $19$, $20$, $21$, $22$, $23$ et $24$.",
      "$4 < \\sqrt{n} < 5$ revient à comparer $n$ à $4^2$ et à $5^2$.",
      S("Comme les nombres sont positifs, $4 < \\sqrt{n} < 5$ équivaut à $4^2 < n < 5^2$, soit $16 < n < 25$.",
        "Les entiers strictement compris entre $16$ et $25$ sont $17, 18, \\dots, 24$.",
        "Il y a $8$ entiers qui conviennent."),
      checks=tuple(str(n) for n in range(17, 25) if 16 < n < 25)),
    E(48218, N2, 3,
      "Calculer la valeur exacte, puis la valeur arrondie au dixième, de $\\sqrt{3^2 + 5^2}$.",
      "$\\sqrt{3^2 + 5^2} = \\sqrt{34} \\approx 5{,}8$",
      "Calcule d'abord ce qu'il y a sous la racine, en respectant les priorités.",
      S("Sous la racine : $3^2 + 5^2 = 9 + 25 = 34$.",
        "La valeur exacte est donc $\\sqrt{34}$ (ce n'est pas $3 + 5 = 8$).",
        "La calculatrice donne $\\sqrt{34} \\approx 5{,}83$, soit $5{,}8$ au dixième."),
      checks=(num(sq(3) + sq(5)), rnd(root(34), 1))),
    E(48219, N2, 3,
      "Un terrain carré a une aire de $2\\,025$ m$^2$. Sans calculatrice, trouver la longueur de son côté. Indice : $40^2 = 1\\,600$ et $50^2 = 2\\,500$.",
      "Le côté mesure $45$ m.",
      "Un carré qui se termine par $5$ est le carré d'un nombre qui se termine par $5$.",
      S("$1\\,600 < 2\\,025 < 2\\,500$, donc le côté est compris entre $40$ m et $50$ m.",
        "$2\\,025$ se termine par $5$ : le côté est un entier qui se termine par $5$, on essaie $45$.",
        "$45^2 = 45 \\times 45 = 2\\,025$ : le côté mesure $45$ m."),
      checks=(num(root(2025)),)),
    E(48220, N2, 3,
      "Le côté d'un carré mesure $\\sqrt{7}$ cm. Calculer son aire.",
      "L'aire du carré est $7$ cm$^2$.",
      "L'aire d'un carré est le carré de son côté.",
      S("Aire $= (\\sqrt{7})^2$ cm$^2$.",
        "Par définition de la racine carrée, $(\\sqrt{7})^2 = 7$.",
        "L'aire vaut exactement $7$ cm$^2$ (aucune valeur approchée n'est nécessaire)."),
      checks=(num(sq(root(7)).quantize(Decimal(1))),)),
    E(48222, N2, 3,
      "Un carré a la même aire qu'un rectangle de longueur $12$ cm et de largeur $3$ cm. Quelle est la longueur du côté du carré ?",
      "Le côté du carré mesure $6$ cm.",
      "Calcule d'abord l'aire du rectangle.",
      S("Aire du rectangle : $12 \\times 3 = 36$ cm$^2$.",
        "Le côté $c$ du carré vérifie $c^2 = 36$, avec $c$ positif.",
        "$c = \\sqrt{36} = 6$ : le côté mesure $6$ cm."),
      checks=(num(root(12 * 3)),)),
    E(48221, N2, 4,
      "Le carré $A$ a une aire de $18$ cm$^2$ ; le carré $B$ a un côté de $4{,}2$ cm. Lequel a le plus grand côté ? Justifier sans utiliser de valeur approchée.",
      "Le carré $A$ a le plus grand côté.",
      "Compare les aires des deux carrés plutôt que leurs côtés.",
      S("Le côté du carré $A$ mesure $\\sqrt{18}$ cm.",
        "L'aire du carré $B$ vaut $4{,}2^2 = 17{,}64$ cm$^2$.",
        "$17{,}64 < 18$ : le carré $B$ a la plus petite aire, donc le plus petit côté.",
        "Conclusion : $4{,}2 < \\sqrt{18}$, le carré $A$ a le plus grand côté."),
      step_checks=(num(sq("4.2")),)),
    E(48223, N2, 4,
      "Un carré a la même aire qu'un rectangle de $8$ cm sur $5$ cm. Calculer le côté du carré au millimètre près, puis comparer le périmètre du carré à celui du rectangle.",
      "Le côté mesure $\\sqrt{40}$ cm, soit environ $6{,}3$ cm ; le périmètre du carré (environ $25{,}3$ cm) est inférieur à celui du rectangle ($26$ cm).",
      "Pour le périmètre du carré, calcule $4 \\times \\sqrt{40}$ avec la valeur donnée par la calculatrice, puis arrondis seulement à la fin.",
      S("Aire du rectangle : $8 \\times 5 = 40$ cm$^2$ ; le côté du carré vaut $\\sqrt{40}$ cm.",
        "La calculatrice donne $\\sqrt{40} \\approx 6{,}325$, soit $6{,}3$ cm au millimètre près.",
        "Périmètre du carré : $4 \\times \\sqrt{40} \\approx 25{,}30$ cm, soit environ $25{,}3$ cm.",
        "Périmètre du rectangle : $2 \\times (8 + 5) = 26$ cm. Le carré a le plus petit périmètre."),
      checks=(rnd(root(40), 1), rnd(4 * root(40), 1), num(2 * (8 + 5))),
      step_checks=(rnd(root(40), 3), rnd(4 * root(40), 2))),
    E(48224, N2, 4,
      "Le nombre $\\sqrt{2}$ n'est pas un nombre décimal : on cherche à l'approcher. Calculer $1{,}4^2$ et $1{,}5^2$, puis $1{,}41^2$ et $1{,}42^2$. En déduire un encadrement de $\\sqrt{2}$ entre deux nombres ayant deux chiffres après la virgule.",
      "$1{,}41 < \\sqrt{2} < 1{,}42$",
      "Cherche à chaque fois deux nombres dont les carrés encadrent $2$.",
      S("$1{,}4^2 = 1{,}96$ et $1{,}5^2 = 2{,}25$ : comme $1{,}96 < 2 < 2{,}25$, on a $1{,}4 < \\sqrt{2} < 1{,}5$.",
        "$1{,}41^2 = 1{,}9881$ et $1{,}42^2 = 2{,}0164$ : comme $1{,}9881 < 2 < 2{,}0164$, on a $1{,}41 < \\sqrt{2} < 1{,}42$.",
        "Conclusion : $1{,}41 < \\sqrt{2} < 1{,}42$."),
      checks=(num(root(2).quantize(Decimal("0.01"), rounding="ROUND_FLOOR")),
              num(root(2).quantize(Decimal("0.01"), rounding="ROUND_CEILING"))),
      step_checks=(num(sq("1.4")), num(sq("1.5")), num(sq("1.41")), num(sq("1.42")))),

    # ═════════════════════════════════════════════════════════════════════
    # Notion 3 — Calculer une longueur avec le théorème de Pythagore (48 3xx)
    # ═════════════════════════════════════════════════════════════════════
    E(48301, N3, 1,
      "Le triangle $ABC$ est rectangle en $A$, avec $AB = 6$ cm et $AC = 8$ cm. Calculer $BC$.",
      "$BC = 10$ cm",
      "Écris l'égalité de Pythagore avec l'hypoténuse seule, puis termine par une racine carrée.",
      S("Le triangle $ABC$ est rectangle en $A$ : son hypoténuse est $[BC]$.",
        "D'après le théorème de Pythagore : $BC^2 = AB^2 + AC^2 = 6^2 + 8^2 = 36 + 64 = 100$.",
        "$BC$ est une longueur, donc $BC = \\sqrt{100} = 10$ cm."),
      checks=(num(hyp(6, 8)),), step_checks=(num(sq(6) + sq(8)),)),
    E(48302, N3, 1,
      "Sur une figure, un triangle $EFG$ est codé avec un angle droit en $G$ ; on y lit $EG = 9$ cm et $FG = 12$ cm. Nommer son hypoténuse, puis calculer sa longueur.",
      "L'hypoténuse est $[EF]$ et $EF = 15$ cm.",
      "Quel est le côté opposé au sommet $G$ ?",
      S("Le triangle est rectangle en $G$ : l'hypoténuse est $[EF]$.",
        "D'après le théorème de Pythagore : $EF^2 = EG^2 + FG^2 = 81 + 144 = 225$.",
        "$EF = \\sqrt{225} = 15$ cm."),
      checks=(num(hyp(9, 12)),), step_checks=(num(sq(9) + sq(12)),)),
    E(48303, N3, 1,
      "Le triangle $KLM$ est rectangle en $K$. Son hypoténuse mesure $LM = 13$ cm et $KL = 5$ cm. Calculer $KM$.",
      "$KM = 12$ cm",
      "On cherche un côté de l'angle droit : il faudra soustraire.",
      S("Le triangle est rectangle en $K$ : $LM^2 = KL^2 + KM^2$.",
        "Donc $KM^2 = LM^2 - KL^2 = 13^2 - 5^2 = 169 - 25 = 144$.",
        "$KM = \\sqrt{144} = 12$ cm."),
      checks=(num(leg(13, 5)),), step_checks=(num(sq(13) - sq(5)),)),
    E(48304, N3, 1,
      "Le triangle $RST$ est rectangle en $S$, avec $RT = 10$ cm et $ST = 6$ cm. Calculer $RS$.",
      "$RS = 8$ cm",
      "Repère d'abord l'hypoténuse parmi les longueurs données.",
      S("Le triangle est rectangle en $S$ : l'hypoténuse est $[RT]$, donc $RT^2 = RS^2 + ST^2$.",
        "$RS^2 = RT^2 - ST^2 = 100 - 36 = 64$.",
        "$RS = \\sqrt{64} = 8$ cm."),
      checks=(num(leg(10, 6)),), step_checks=(num(sq(10) - sq(6)),)),
    E(48305, N3, 1,
      "Le triangle $UVW$ est rectangle en $V$, avec $UV = 20$ mm et $VW = 21$ mm. Calculer $UW$.",
      "$UW = 29$ mm",
      "L'hypoténuse est le côté qui ne contient pas la lettre $V$.",
      S("Le triangle est rectangle en $V$ : $UW^2 = UV^2 + VW^2$.",
        "$UW^2 = 20^2 + 21^2 = 400 + 441 = 841$.",
        "$UW = \\sqrt{841} = 29$ mm."),
      checks=(num(hyp(20, 21)),), step_checks=(num(sq(20) + sq(21)),)),
    E(48306, N3, 1,
      "Le triangle $DEF$ est rectangle en $E$, avec $DF = 25$ m et $DE = 24$ m. Calculer $EF$.",
      "$EF = 7$ m",
      "$[DF]$ est-il un côté de l'angle droit ou l'hypoténuse ?",
      S("Le triangle est rectangle en $E$ : l'hypoténuse est $[DF]$ et $DF^2 = DE^2 + EF^2$.",
        "$EF^2 = DF^2 - DE^2 = 625 - 576 = 49$.",
        "$EF = \\sqrt{49} = 7$ m."),
      checks=(num(leg(25, 24)),), step_checks=(num(sq(25) - sq(24)),)),
    E(48307, N3, 1,
      "Le triangle $PQR$ est rectangle en $Q$, avec $PQ = 1{,}5$ m et $QR = 2$ m. Calculer $PR$.",
      "$PR = 2{,}5$ m",
      "Calcule soigneusement $1{,}5^2$.",
      S("Le triangle est rectangle en $Q$ : $PR^2 = PQ^2 + QR^2$.",
        "$PR^2 = 1{,}5^2 + 2^2 = 2{,}25 + 4 = 6{,}25$.",
        "$PR = \\sqrt{6{,}25} = 2{,}5$ m."),
      checks=(num(hyp("1.5", 2)),), step_checks=(num(sq("1.5") + sq(2)),)),
    E(48308, N3, 2,
      "Le triangle $ABC$ est rectangle en $B$, avec $AB = 4$ cm et $BC = 7$ cm. Calculer $AC$ : donner la valeur exacte, puis la valeur arrondie au dixième.",
      "$AC = \\sqrt{65}$ cm, soit $AC \\approx 8{,}1$ cm.",
      "$65$ n'est pas un carré parfait : la valeur exacte s'écrit avec une racine carrée.",
      S("Le triangle est rectangle en $B$ : $AC^2 = AB^2 + BC^2 = 16 + 49 = 65$.",
        "Valeur exacte : $AC = \\sqrt{65}$ cm.",
        "La calculatrice donne $\\sqrt{65} \\approx 8{,}06$, donc $AC \\approx 8{,}1$ cm au dixième."),
      checks=(num(sq(4) + sq(7)), rnd(hyp(4, 7), 1))),
    E(48309, N3, 2,
      "Le triangle $GHI$ est rectangle en $H$, avec $GI = 9$ cm et $GH = 5$ cm. Calculer $HI$ : valeur exacte, puis arrondi au millimètre.",
      "$HI = \\sqrt{56}$ cm, soit $HI \\approx 7{,}5$ cm.",
      "Au millimètre près, une longueur en centimètres s'arrondit au dixième.",
      S("Le triangle est rectangle en $H$ : $GI^2 = GH^2 + HI^2$, donc $HI^2 = 81 - 25 = 56$.",
        "Valeur exacte : $HI = \\sqrt{56}$ cm.",
        "$\\sqrt{56} \\approx 7{,}48$, donc $HI \\approx 7{,}5$ cm au millimètre."),
      checks=(num(sq(9) - sq(5)), rnd(leg(9, 5), 1))),
    E(48310, N3, 2,
      "Le triangle $JKL$ est rectangle en $J$, avec $JK = 2{,}4$ cm et $JL = 3{,}2$ cm. Sans calculatrice, montrer que $KL$ est un nombre entier de centimètres.",
      "$KL = 4$ cm",
      "Les longueurs sont décimales, mais le résultat peut être exact : calcule avant de conclure.",
      S("Le triangle est rectangle en $J$ : $KL^2 = JK^2 + JL^2$.",
        "$KL^2 = 2{,}4^2 + 3{,}2^2 = 5{,}76 + 10{,}24 = 16$.",
        "$KL = \\sqrt{16} = 4$ cm."),
      checks=(num(hyp("2.4", "3.2")),), step_checks=(num(sq("2.4")), num(sq("3.2")))),
    E(48311, N3, 2,
      "L'hypoténuse d'un triangle rectangle mesure $6{,}5$ cm et l'un des côtés de l'angle droit mesure $2{,}5$ cm. Quelle est la longueur du troisième côté ?",
      "Le troisième côté mesure $6$ cm.",
      "Le troisième côté est l'autre côté de l'angle droit : appelle sa longueur $x$ et écris l'égalité de Pythagore.",
      S("Notons $x$ la longueur cherchée (en cm) : c'est un côté de l'angle droit, donc $6{,}5^2 = 2{,}5^2 + x^2$.",
        "$x^2 = 6{,}5^2 - 2{,}5^2 = 42{,}25 - 6{,}25 = 36$.",
        "$x$ est positif, donc $x = \\sqrt{36} = 6$ : le troisième côté mesure $6$ cm."),
      checks=(num(leg("6.5", "2.5")),), step_checks=(num(sq("6.5")), num(sq("2.5")))),
    E(48312, N3, 2,
      "Le triangle $XYZ$ est rectangle en $Y$, avec $XY = 30$ cm et $YZ = 0{,}4$ m. Calculer $XZ$ en centimètres.",
      "$XZ = 50$ cm",
      "Avant tout calcul, exprime les deux longueurs dans la même unité.",
      S("On convertit : $YZ = 0{,}4$ m $= 40$ cm.",
        "Le triangle est rectangle en $Y$ : $XZ^2 = XY^2 + YZ^2 = 900 + 1\\,600 = 2\\,500$.",
        "$XZ = \\sqrt{2\\,500} = 50$ cm."),
      checks=(num(hyp(30, 40)),)),
    E(48313, N3, 2,
      "Le triangle $ABC$ est rectangle en $C$, avec $AC = 3$ cm et $BC = 3$ cm. Calculer $AB$ : valeur exacte, puis arrondi au centième.",
      "$AB = \\sqrt{18}$ cm, soit $AB \\approx 4{,}24$ cm.",
      "Le triangle est isocèle, mais la méthode ne change pas.",
      S("Le triangle est rectangle en $C$ : $AB^2 = AC^2 + BC^2 = 9 + 9 = 18$.",
        "Valeur exacte : $AB = \\sqrt{18}$ cm.",
        "$\\sqrt{18} \\approx 4{,}243$, donc $AB \\approx 4{,}24$ cm au centième."),
      checks=(num(sq(3) + sq(3)), rnd(hyp(3, 3), 2))),
    E(48314, N3, 2,
      "Le triangle $DEF$ est rectangle en $D$, avec $EF = 11$ cm et $DF = 7$ cm. Calculer $DE$, arrondie au dixième.",
      "$DE = \\sqrt{72}$ cm, soit $DE \\approx 8{,}5$ cm.",
      "On cherche un côté de l'angle droit.",
      S("Le triangle est rectangle en $D$ : $EF^2 = DE^2 + DF^2$, donc $DE^2 = 121 - 49 = 72$.",
        "$DE = \\sqrt{72}$ cm.",
        "$\\sqrt{72} \\approx 8{,}49$, donc $DE \\approx 8{,}5$ cm au dixième."),
      checks=(num(sq(11) - sq(7)), rnd(leg(11, 7), 1))),
    E(48315, N3, 2,
      "Le triangle $RST$ est rectangle en $R$. On donne $RS = 12$ cm, $RT = 9$ cm et la mesure de l'angle $\\widehat{RST} \\approx 37°$. Calculer $ST$.",
      "$ST = 15$ cm",
      "Toutes les données ne sont pas utiles : le théorème de Pythagore n'utilise que des longueurs.",
      S("La mesure de l'angle n'est pas utile ici.",
        "Le triangle est rectangle en $R$ : $ST^2 = RS^2 + RT^2 = 144 + 81 = 225$.",
        "$ST = \\sqrt{225} = 15$ cm."),
      checks=(num(hyp(12, 9)),), step_checks=(num(sq(12) + sq(9)),)),
    E(48317, N3, 2,
      "Le triangle $LMN$ est rectangle en $M$, avec $LM = 1{,}2$ km et $MN = 0{,}5$ km. Calculer $LN$.",
      "$LN = 1{,}3$ km",
      "Garde les kilomètres : les deux longueurs sont déjà dans la même unité.",
      S("Le triangle est rectangle en $M$ : $LN^2 = LM^2 + MN^2$.",
        "$LN^2 = 1{,}2^2 + 0{,}5^2 = 1{,}44 + 0{,}25 = 1{,}69$.",
        "$LN = \\sqrt{1{,}69} = 1{,}3$ km."),
      checks=(num(hyp("1.2", "0.5")),), step_checks=(num(sq("1.2") + sq("0.5")),)),
    E(48316, N3, 3,
      "On cherche un triangle $IJK$ rectangle en $I$, d'hypoténuse $JK = 8$ cm, avec $IJ = 8$ cm. Peut-on calculer $IK$ ?",
      "Non : un tel triangle n'existe pas.",
      "Compare la longueur de l'hypoténuse à celle d'un côté de l'angle droit.",
      S("Dans un triangle rectangle, l'hypoténuse est strictement plus longue que chacun des deux autres côtés.",
        "Ici, $JK = IJ = 8$ cm : c'est impossible.",
        "Le calcul le confirme : on obtiendrait $IK^2 = 8^2 - 8^2 = 0$, donc $IK = 0$ : il n'y aurait pas de triangle.")),
    E(48318, N3, 3,
      "Le triangle $ABC$ est rectangle et isocèle en $A$, avec $BC = 10$ cm. Calculer $AB$ : valeur exacte, puis arrondi au dixième.",
      "$AB = \\sqrt{50}$ cm, soit $AB \\approx 7{,}1$ cm.",
      "Les deux côtés de l'angle droit ont la même longueur : appelle-la $x$ dans l'égalité de Pythagore.",
      S("Le triangle est rectangle en $A$ : $BC^2 = AB^2 + AC^2$, et $AB = AC$.",
        "Donc $10^2 = 2 \\times AB^2$, soit $AB^2 = 100 \\div 2 = 50$.",
        "$AB = \\sqrt{50}$ cm $\\approx 7{,}07$ cm, soit $7{,}1$ cm au dixième."),
      checks=(num(sq(10) / 2), rnd(root(50), 1))),
    E(48319, N3, 3,
      "Le triangle $ABC$ est rectangle en $B$, avec $AB = 3$ cm et $BC = 4$ cm. Le triangle $ACD$ est rectangle en $C$, avec $CD = 12$ cm. Calculer $AC$, puis $AD$.",
      "$AC = 5$ cm et $AD = 13$ cm.",
      "La longueur $AC$ calculée dans le premier triangle sert dans le second.",
      S("Dans $ABC$, rectangle en $B$ : $AC^2 = 3^2 + 4^2 = 25$, donc $AC = 5$ cm.",
        "Dans $ACD$, rectangle en $C$ : l'hypoténuse est $[AD]$ et $AD^2 = AC^2 + CD^2$.",
        "$AD^2 = 25 + 144 = 169$, donc $AD = \\sqrt{169} = 13$ cm."),
      checks=(num(hyp(3, 4)), num(hyp(hyp(3, 4), 12)))),
    E(48320, N3, 3,
      "Le triangle $MNP$ est rectangle en $N$, avec $MP = 7{,}3$ cm et $MN = 4{,}8$ cm. Calculer $NP$.",
      "$NP = 5{,}5$ cm",
      "Fais les carrés des décimaux avec soin, puis vérifie si le résultat est un carré connu.",
      S("Le triangle est rectangle en $N$ : $MP^2 = MN^2 + NP^2$.",
        "$NP^2 = 7{,}3^2 - 4{,}8^2 = 53{,}29 - 23{,}04 = 30{,}25$.",
        "$NP = \\sqrt{30{,}25} = 5{,}5$ cm (car $5{,}5^2 = 30{,}25$)."),
      checks=(num(leg("7.3", "4.8")),), step_checks=(num(sq("7.3")), num(sq("4.8")), num(sq("7.3") - sq("4.8")))),
    E(48321, N3, 3,
      "Voici la rédaction de Lina pour un triangle $RST$ rectangle en $T$, avec $RS = 13$ cm et $RT = 5$ cm : « $RS^2 = RT^2 + ST^2$, donc $ST^2 = 13^2 + 5^2 = 194$. » Trouver son erreur et donner la longueur $ST$.",
      "Lina aurait dû soustraire : $ST^2 = 13^2 - 5^2 = 144$, donc $ST = 12$ cm.",
      "Lina cherche-t-elle l'hypoténuse ou un côté de l'angle droit ?",
      S("L'égalité $RS^2 = RT^2 + ST^2$ est juste : l'hypoténuse est $[RS]$.",
        "Pour isoler $ST^2$, on soustrait $RT^2$ : $ST^2 = RS^2 - RT^2$. Lina a additionné.",
        "$ST^2 = 169 - 25 = 144$, donc $ST = 12$ cm."),
      checks=(num(sq(13) - sq(5)), num(leg(13, 5)))),
    E(48322, N3, 3,
      "Le triangle $ABC$ est rectangle en $A$, avec $AB = 15$ cm et $BC = 17$ cm. Calculer le périmètre du triangle.",
      "Le périmètre est $40$ cm.",
      "Il manque une longueur pour calculer le périmètre.",
      S("Le triangle est rectangle en $A$ : $BC^2 = AB^2 + AC^2$, donc $AC^2 = 289 - 225 = 64$ et $AC = 8$ cm.",
        "Périmètre : $AB + AC + BC = 15 + 8 + 17$.",
        "Le périmètre vaut $40$ cm."),
      checks=(num(15 + leg(17, 15) + 17),)),
    E(48323, N3, 3,
      "Le triangle $DEF$ est rectangle en $D$, avec $EF = 26$ cm et $DE = 10$ cm. Calculer l'aire du triangle $DEF$.",
      "L'aire est $120$ cm$^2$.",
      "Pour un triangle rectangle, les côtés de l'angle droit servent de base et de hauteur.",
      S("Le triangle est rectangle en $D$ : $DF^2 = EF^2 - DE^2 = 676 - 100 = 576$, donc $DF = 24$ cm.",
        "Les côtés de l'angle droit sont $[DE]$ et $[DF]$ : aire $= \\dfrac{DE \\times DF}{2} = \\dfrac{10 \\times 24}{2}$.",
        "L'aire vaut $120$ cm$^2$."),
      checks=(num(10 * leg(26, 10) / 2),)),
    E(48324, N3, 3,
      "Le triangle $GHK$ est rectangle en $H$, avec $GH = 2$ cm et $HK = 5$ cm. Un élève trouve $GK \\approx 5{,}4$ cm, puis calcule $5{,}4^2 = 29{,}16$. Pourquoi n'obtient-il pas exactement $GH^2 + HK^2 = 29$ ?",
      "Parce que $5{,}4$ n'est qu'une valeur approchée de $GK = \\sqrt{29}$ : seule la valeur exacte vérifie $GK^2 = 29$.",
      "Quelle est la valeur exacte de $GK$ ?",
      S("$GK^2 = GH^2 + HK^2 = 4 + 25 = 29$, donc la valeur exacte est $GK = \\sqrt{29}$ cm.",
        "$\\sqrt{29} \\approx 5{,}385$ : $5{,}4$ est un arrondi au dixième, pas la valeur exacte.",
        "Le carré d'une valeur arrondie ($5{,}4^2 = 29{,}16$) ne redonne pas exactement $29$ : on fait les calculs avec les valeurs exactes et on arrondit à la fin."),
      checks=(num(sq(2) + sq(5)),), step_checks=(rnd(hyp(2, 5), 3), num(sq("5.4")))),
    E(48325, N3, 4,
      "Le triangle $ABC$ est isocèle en $A$, avec $AB = AC = 10$ cm et $BC = 12$ cm. On note $H$ le milieu de $[BC]$ ; dans ce triangle isocèle, la droite $(AH)$ est perpendiculaire à $(BC)$. Calculer $AH$, puis l'aire du triangle $ABC$.",
      "$AH = 8$ cm et l'aire du triangle $ABC$ est $48$ cm$^2$.",
      "Travaille dans le triangle $ABH$ : quelles longueurs connais-tu ?",
      S("$H$ est le milieu de $[BC]$, donc $BH = 12 \\div 2 = 6$ cm.",
        "Le triangle $ABH$ est rectangle en $H$, d'hypoténuse $[AB]$ : $AH^2 = AB^2 - BH^2 = 100 - 36 = 64$, donc $AH = 8$ cm.",
        "$[AH]$ est la hauteur relative à $[BC]$ : aire $= \\dfrac{BC \\times AH}{2} = \\dfrac{12 \\times 8}{2} = 48$ cm$^2$."),
      checks=(num(leg(10, 6)), num(12 * leg(10, 6) / 2))),
    E(48326, N3, 4,
      "Le triangle $ABC$ est équilatéral de côté $6$ cm. On note $H$ le milieu de $[BC]$ ; la droite $(AH)$ est perpendiculaire à $(BC)$. Calculer la hauteur $AH$ : valeur exacte, puis arrondi au millimètre.",
      "$AH = \\sqrt{27}$ cm, soit $AH \\approx 5{,}2$ cm.",
      "Tous les côtés mesurent $6$ cm, et $H$ coupe $[BC]$ en deux.",
      S("$BH = 6 \\div 2 = 3$ cm et le triangle $ABH$ est rectangle en $H$, d'hypoténuse $[AB]$.",
        "$AH^2 = AB^2 - BH^2 = 36 - 9 = 27$, donc $AH = \\sqrt{27}$ cm.",
        "$\\sqrt{27} \\approx 5{,}196$, soit $AH \\approx 5{,}2$ cm au millimètre."),
      checks=(num(sq(6) - sq(3)), rnd(leg(6, 3), 1))),
    E(48327, N3, 4,
      "$ABCD$ est un losange dont les diagonales mesurent $AC = 16$ cm et $BD = 12$ cm. On rappelle que les diagonales d'un losange sont perpendiculaires et se coupent en leur milieu $O$. Calculer la longueur d'un côté du losange, puis son périmètre.",
      "Le côté mesure $10$ cm et le périmètre $40$ cm.",
      "Place-toi dans le triangle $AOB$.",
      S("$O$ est le milieu des diagonales : $AO = 16 \\div 2 = 8$ cm et $BO = 12 \\div 2 = 6$ cm.",
        "Les diagonales sont perpendiculaires : $AOB$ est rectangle en $O$, d'hypoténuse $[AB]$, et $AB^2 = 64 + 36 = 100$.",
        "$AB = 10$ cm ; les quatre côtés d'un losange sont égaux, donc le périmètre vaut $4 \\times 10 = 40$ cm."),
      checks=(num(hyp(8, 6)), num(4 * hyp(8, 6)))),
    E(48328, N3, 4,
      "Le triangle $ABC$ est rectangle en $A$. Le côté $[AC]$ mesure $2$ cm de plus que le côté $[AB]$, et $BC = 10$ cm. On note $x$ la longueur $AB$ en centimètres. Écrire l'égalité de Pythagore en fonction de $x$, puis vérifier que $x = 6$ convient.",
      "$10^2 = x^2 + (x + 2)^2$ ; pour $x = 6$ : $6^2 + 8^2 = 100 = 10^2$, donc $x = 6$ convient ($AB = 6$ cm et $AC = 8$ cm).",
      "Exprime $AC$ en fonction de $x$, puis remplace $x$ par $6$ dans chaque membre.",
      S("$AC = x + 2$ et le triangle est rectangle en $A$ : $BC^2 = AB^2 + AC^2$, soit $10^2 = x^2 + (x + 2)^2$.",
        "Pour $x = 6$ : $AC = 8$ et $x^2 + (x + 2)^2 = 36 + 64 = 100$.",
        "On a bien $100 = 10^2$ : $x = 6$ convient, donc $AB = 6$ cm et $AC = 8$ cm."),
      checks=(num(sq(6) + sq(8)),)),
    E(48329, N3, 4,
      "$ABCD$ est un trapèze rectangle : les angles en $A$ et en $D$ sont droits et $(AB) \\parallel (DC)$. On donne $AB = 7$ cm, $DC = 4$ cm et $AD = 4$ cm. Le point $H$ de $[AB]$ est tel que $ADCH$ est un rectangle. Calculer $BC$.",
      "$BC = 5$ cm",
      "Le rectangle $ADCH$ donne deux longueurs du triangle $HBC$.",
      S("$ADCH$ est un rectangle : $AH = DC = 4$ cm et $CH = AD = 4$ cm, et l'angle en $H$ est droit.",
        "$HB = AB - AH = 7 - 4 = 3$ cm.",
        "Le triangle $HBC$ est rectangle en $H$ : $BC^2 = HB^2 + HC^2 = 9 + 16 = 25$, donc $BC = 5$ cm."),
      checks=(num(hyp(7 - 4, 4)),)),
    E(48330, N3, 4,
      "Le triangle $OAB$ est rectangle en $A$ avec $OA = AB = 1$ cm ; le triangle $OBC$ est rectangle en $B$ avec $BC = 1$ cm ; le triangle $OCD$ est rectangle en $C$ avec $CD = 1$ cm. Calculer les valeurs exactes de $OB$, $OC$ et $OD$.",
      "$OB = \\sqrt{2}$ cm, $OC = \\sqrt{3}$ cm et $OD = 2$ cm.",
      "Chaque hypoténuse calculée devient un côté de l'angle droit du triangle suivant.",
      S("Dans $OAB$ : $OB^2 = 1^2 + 1^2 = 2$, donc $OB = \\sqrt{2}$ cm.",
        "Dans $OBC$ : $OC^2 = OB^2 + BC^2 = 2 + 1 = 3$, donc $OC = \\sqrt{3}$ cm.",
        "Dans $OCD$ : $OD^2 = OC^2 + CD^2 = 3 + 1 = 4$, donc $OD = \\sqrt{4} = 2$ cm."),
      checks=(num(root(4)),), step_checks=(num(1 + 1), num(2 + 1), num(3 + 1))),

    # ═════════════════════════════════════════════════════════════════════
    # Notion 4 — Démontrer qu'un triangle est rectangle ou non (48 4xx)
    # ═════════════════════════════════════════════════════════════════════
    E(48401, N4, 1,
      "Le triangle $ABC$ est tel que $AB = 9$ cm, $AC = 12$ cm et $BC = 15$ cm. Est-il rectangle ?",
      "Oui, le triangle $ABC$ est rectangle en $A$.",
      "Compare le carré du plus long côté à la somme des carrés des deux autres.",
      S("Le plus long côté est $[BC]$ : $BC^2 = 15^2 = 225$.",
        "$AB^2 + AC^2 = 81 + 144 = 225$.",
        "On constate que $BC^2 = AB^2 + AC^2$ : d'après la réciproque du théorème de Pythagore, le triangle $ABC$ est rectangle en $A$."),
      rect=(9, 12, 15, True), step_checks=(num(sq(15)), num(sq(9) + sq(12)))),
    E(48402, N4, 1,
      "Le triangle $DEF$ est tel que $DE = 4$ cm, $EF = 6$ cm et $DF = 7$ cm. Est-il rectangle ?",
      "Non, le triangle $DEF$ n'est pas rectangle.",
      "Calcule séparément $DF^2$ et $DE^2 + EF^2$.",
      S("Le plus long côté est $[DF]$ : $DF^2 = 49$.",
        "$DE^2 + EF^2 = 16 + 36 = 52$.",
        "$DF^2 \\neq DE^2 + EF^2$. Si le triangle était rectangle, ce serait en $E$ et on aurait l'égalité : d'après le théorème de Pythagore, $DEF$ n'est pas rectangle."),
      rect=(4, 6, 7, False), step_checks=(num(sq(7)), num(sq(4) + sq(6)))),
    E(48403, N4, 1,
      "Dans le triangle $GHI$, on a calculé $GH^2 + HI^2 = 74$ et $GI^2 = 74$. Ce triangle est-il rectangle ? Si oui, en quel sommet ?",
      "Oui, le triangle $GHI$ est rectangle en $H$.",
      "L'angle droit est opposé au côté dont le carré est égal à la somme des deux autres.",
      S("On a $GI^2 = GH^2 + HI^2$.",
        "D'après la réciproque du théorème de Pythagore, le triangle est rectangle.",
        "L'angle droit est opposé à $[GI]$ : il est en $H$.")),
    E(48404, N4, 1,
      "Le triangle $KLM$ a pour côtés $KL = 8$ cm, $LM = 17$ cm et $KM = 15$ cm. Quel côté faut-il considérer seul ? Le triangle est-il rectangle ?",
      "Oui : on isole $[LM]$, le plus long côté, et le triangle $KLM$ est rectangle en $K$.",
      "Ce n'est pas forcément le dernier côté de la liste qui est le plus long.",
      S("Le plus long côté est $[LM]$ : $LM^2 = 289$.",
        "$KL^2 + KM^2 = 64 + 225 = 289$.",
        "$LM^2 = KL^2 + KM^2$ : d'après la réciproque du théorème de Pythagore, $KLM$ est rectangle en $K$."),
      rect=(8, 17, 15, True), step_checks=(num(sq(17)), num(sq(8) + sq(15)))),
    E(48405, N4, 1,
      "Le triangle $NOP$ est tel que $NO = 5$ cm, $OP = 5$ cm et $NP = 7$ cm. Sur un dessin, il semble rectangle en $O$. L'est-il vraiment ?",
      "Non, le triangle $NOP$ n'est pas rectangle.",
      "Un dessin ne suffit jamais : fais le calcul.",
      S("Le plus long côté est $[NP]$ : $NP^2 = 49$.",
        "$NO^2 + OP^2 = 25 + 25 = 50$.",
        "$49 \\neq 50$ : d'après le théorème de Pythagore, s'il était rectangle (en $O$), on aurait l'égalité ; donc $NOP$ n'est pas rectangle, même s'il en a l'air."),
      rect=(5, 5, 7, False), step_checks=(num(sq(7)), num(sq(5) + sq(5)))),
    E(48406, N4, 1,
      "On connaît les trois longueurs d'un triangle. Quel théorème permet de démontrer qu'il est rectangle ? Lequel permet de démontrer qu'il ne l'est pas ?",
      "Pour démontrer qu'il est rectangle : la réciproque du théorème de Pythagore. Pour démontrer qu'il ne l'est pas : le théorème de Pythagore lui-même (sous la forme de sa contraposée).",
      "Dans quel sens chaque énoncé fonctionne-t-il : « si rectangle, alors égalité » ou « si égalité, alors rectangle » ?",
      S("La réciproque dit : si le carré du plus long côté est égal à la somme des carrés des deux autres, alors le triangle est rectangle.",
        "Le théorème dit : si le triangle est rectangle, alors l'égalité est vraie.",
        "Donc si l'égalité est fausse, le triangle ne peut pas être rectangle : c'est la contraposée du théorème.")),
    E(48407, N4, 2,
      "Le triangle $ABC$ est tel que $AB = 2{,}8$ cm, $BC = 4{,}5$ cm et $AC = 5{,}3$ cm. Est-il rectangle ?",
      "Oui, le triangle $ABC$ est rectangle en $B$.",
      "Calcule les carrés des décimaux sans arrondir.",
      S("Le plus long côté est $[AC]$ : $AC^2 = 5{,}3^2 = 28{,}09$.",
        "$AB^2 + BC^2 = 7{,}84 + 20{,}25 = 28{,}09$.",
        "$AC^2 = AB^2 + BC^2$ : d'après la réciproque du théorème de Pythagore, $ABC$ est rectangle en $B$."),
      rect=("2.8", "4.5", "5.3", True), step_checks=(num(sq("5.3")), num(sq("2.8")), num(sq("4.5")))),
    E(48408, N4, 2,
      "Un triangle $RST$ a pour côtés $RS = 6{,}1$ cm, $ST = 6$ cm et $RT = 1{,}1$ cm. Est-il rectangle ? Si oui, quels sont les deux côtés qui forment l'angle droit ?",
      "Oui, le triangle $RST$ est rectangle en $T$ : l'angle droit est formé par les côtés $[ST]$ et $[RT]$.",
      "Un côté très court n'empêche pas le triangle d'être rectangle.",
      S("Le plus long côté est $[RS]$ : $RS^2 = 6{,}1^2 = 37{,}21$.",
        "$ST^2 + RT^2 = 36 + 1{,}21 = 37{,}21$.",
        "$RS^2 = ST^2 + RT^2$ : d'après la réciproque du théorème de Pythagore, $RST$ est rectangle en $T$."),
      rect=("6.1", 6, "1.1", True), step_checks=(num(sq("6.1")), num(sq(6) + sq("1.1")))),
    E(48409, N4, 2,
      "Peut-on construire un triangle rectangle $UVW$ dont les côtés mesurent $UV = 3{,}5$ cm, $VW = 8{,}5$ cm et $UW = 7{,}5$ cm ?",
      "Non : un triangle de ces dimensions existe, mais il n'est pas rectangle.",
      "Range d'abord les trois longueurs.",
      S("Le triangle existe : le plus long côté est plus court que la somme des deux autres ($8{,}5 < 3{,}5 + 7{,}5 = 11$).",
        "Le plus long côté est $[VW]$ : $VW^2 = 72{,}25$.",
        "$UV^2 + UW^2 = 12{,}25 + 56{,}25 = 68{,}5$.",
        "$VW^2 \\neq UV^2 + UW^2$ : d'après le théorème de Pythagore (contraposée), $UVW$ n'est pas rectangle."),
      rect=("3.5", "8.5", "7.5", False), step_checks=(num(sq("8.5")), num(sq("3.5") + sq("7.5")))),
    E(48410, N4, 2,
      "Le triangle $XYZ$ est tel que $XY = 0{,}6$ m, $YZ = 80$ cm et $XZ = 1$ m. Est-il rectangle ?",
      "Oui, le triangle $XYZ$ est rectangle en $Y$.",
      "Convertis toutes les longueurs dans la même unité avant de comparer.",
      S("En centimètres : $XY = 60$ cm, $YZ = 80$ cm et $XZ = 100$ cm.",
        "$XZ^2 = 10\\,000$ et $XY^2 + YZ^2 = 3\\,600 + 6\\,400 = 10\\,000$.",
        "$XZ^2 = XY^2 + YZ^2$ : d'après la réciproque du théorème de Pythagore, $XYZ$ est rectangle en $Y$."),
      rect=(60, 80, 100, True)),
    E(48411, N4, 2,
      "Inès affirme que le triangle $EFG$, de côtés $EF = 10$ cm, $FG = 24$ cm et $EG = 25$ cm, est rectangle « parce qu'il ressemble beaucoup au triangle rectangle de côtés $10$, $24$ et $26$ ». A-t-elle raison ?",
      "Non, Inès a tort : le triangle $EFG$ n'est pas rectangle.",
      "Ne te fie pas à la ressemblance avec un triangle connu : calcule.",
      S("Le plus long côté est $[EG]$ : $EG^2 = 625$.",
        "$EF^2 + FG^2 = 100 + 576 = 676$.",
        "$625 \\neq 676$ : d'après le théorème de Pythagore (contraposée), $EFG$ n'est pas rectangle."),
      rect=(10, 24, 25, False), step_checks=(num(sq(25)), num(sq(10) + sq(24)))),
    E(48412, N4, 2,
      "Compléter la rédaction : « Dans le triangle $IJK$, le plus long côté est $[IK]$. D'une part, $IK^2 = 13^2 = 169$. D'autre part, $IJ^2 + JK^2 = 5^2 + 12^2 = \\dots$ On constate que $\\dots$ D'après $\\dots$, le triangle $IJK$ est $\\dots$ »",
      "Oui : $IJ^2 + JK^2 = 169$, donc $IK^2 = IJ^2 + JK^2$ ; d'après la réciproque du théorème de Pythagore, le triangle $IJK$ est rectangle en $J$.",
      "Termine le calcul, compare, puis cite le bon théorème et précise le sommet de l'angle droit.",
      S("$IJ^2 + JK^2 = 25 + 144 = 169$.",
        "On constate que $IK^2 = IJ^2 + JK^2$.",
        "D'après la réciproque du théorème de Pythagore, $IJK$ est rectangle en $J$, le sommet opposé à $[IK]$."),
      rect=(5, 12, 13, True), checks=(num(sq(5) + sq(12)),)),
    E(48413, N4, 2,
      "Pour savoir si le triangle $LMN$ ($LM = 7$ cm, $MN = 24$ cm, $LN = 26$ cm) est rectangle, quelle égalité faut-il tester ? Conclure.",
      "Non : il faut tester $LN^2 = LM^2 + MN^2$, qui est fausse ; le triangle $LMN$ n'est pas rectangle.",
      "Le côté seul dans l'égalité à tester est le plus long.",
      S("Le plus long côté est $[LN]$ : $LN^2 = 676$.",
        "$LM^2 + MN^2 = 49 + 576 = 625$.",
        "$676 \\neq 625$ : d'après le théorème de Pythagore (contraposée), $LMN$ n'est pas rectangle."),
      rect=(7, 24, 26, False), step_checks=(num(sq(26)), num(sq(7) + sq(24)))),
    E(48414, N4, 2,
      "On a calculé, pour un triangle $ABC$ : $AB^2 = 45$, $AC^2 = 20$ et $BC^2 = 25$. Est-il rectangle ?",
      "Oui, le triangle $ABC$ est rectangle en $C$.",
      "Le plus long côté est celui qui a le plus grand carré.",
      S("Le plus grand carré est $AB^2 = 45$ : $[AB]$ est le plus long côté.",
        "$AC^2 + BC^2 = 20 + 25 = 45$.",
        "$AB^2 = AC^2 + BC^2$ : d'après la réciproque du théorème de Pythagore, $ABC$ est rectangle en $C$."),
      rect=(R(45), R(20), R(25), True)),
    E(48415, N4, 3,
      "Le triangle $DEF$ a pour longueurs exactes $DE = 4{,}1$ cm, $EF = 5{,}4$ cm et $DF = 6{,}8$ cm. Sur un dessin, l'angle en $E$ semble droit. Le triangle est-il rectangle ?",
      "Non, le triangle $DEF$ n'est pas rectangle, même si l'angle en $E$ en a l'air.",
      "Le dessin peut tromper : seule la comparaison des carrés permet de conclure.",
      S("Le plus long côté est $[DF]$ : $DF^2 = 46{,}24$.",
        "$DE^2 + EF^2 = 16{,}81 + 29{,}16 = 45{,}97$.",
        "$46{,}24 \\neq 45{,}97$ : d'après le théorème de Pythagore (contraposée), $DEF$ n'est pas rectangle. L'angle en $E$ est seulement proche d'un angle droit."),
      rect=("4.1", "5.4", "6.8", False), step_checks=(num(sq("6.8")), num(sq("4.1") + sq("5.4")))),
    E(48416, N4, 3,
      "Le triangle $GHI$ a pour côtés $GH = 5$ cm, $HI = 7$ cm et $GI = \\sqrt{74}$ cm. Est-il rectangle ?",
      "Oui, le triangle $GHI$ est rectangle en $H$.",
      "$(\\sqrt{74})^2$ se calcule sans calculatrice.",
      S("$GI^2 = (\\sqrt{74})^2 = 74$ ; c'est le plus grand carré, car $GH^2 = 25$ et $HI^2 = 49$.",
        "$GH^2 + HI^2 = 25 + 49 = 74$.",
        "$GI^2 = GH^2 + HI^2$ : d'après la réciproque du théorème de Pythagore, $GHI$ est rectangle en $H$."),
      rect=(5, 7, R(74), True)),
    E(48417, N4, 3,
      "Un triangle a pour côtés $9$ cm, $12$ cm et $x$ cm, avec $x > 12$. Pour quelle valeur de $x$ ce triangle est-il rectangle ?",
      "$x = 15$",
      "Le côté de longueur $x$ est le plus long : c'est lui qui doit être l'hypoténuse.",
      S("$x > 12$, donc le côté de longueur $x$ est le plus long.",
        "D'après la réciproque du théorème de Pythagore, le triangle est rectangle si $x^2 = 9^2 + 12^2 = 81 + 144 = 225$.",
        "$x$ est positif, donc $x = \\sqrt{225} = 15$."),
      checks=(num(hyp(9, 12)),)),
    E(48418, N4, 3,
      "Pour le triangle $ABC$ tel que $AB = 6$ cm, $AC = 8$ cm et $BC = 10$ cm, Tom calcule $AB^2 + BC^2 = 136$ et $AC^2 = 64$, puis conclut que le triangle n'est pas rectangle. Expliquer son erreur et conclure correctement.",
      "Oui, le triangle $ABC$ est rectangle en $A$ : Tom aurait dû isoler le plus long côté, $[BC]$.",
      "Quel côté doit être seul dans la comparaison ?",
      S("Tom a isolé $[AC]$, qui n'est pas le plus long côté : sa comparaison ne permet pas de conclure.",
        "Le plus long côté est $[BC]$ : $BC^2 = 100$ et $AB^2 + AC^2 = 36 + 64 = 100$.",
        "$BC^2 = AB^2 + AC^2$ : d'après la réciproque du théorème de Pythagore, $ABC$ est rectangle en $A$."),
      rect=(6, 8, 10, True), step_checks=(num(sq(10)), num(sq(6) + sq(8)))),
    E(48419, N4, 3,
      "Les côtés d'un triangle mesurent $\\sqrt{5}$ cm, $\\sqrt{11}$ cm et $4$ cm. Ce triangle est-il rectangle ?",
      "Oui, ce triangle est rectangle ; l'angle droit est opposé au côté de $4$ cm.",
      "Les carrés de ces trois longueurs se calculent sans calculatrice.",
      S("Les carrés des côtés valent $5$, $11$ et $16$ : le plus long côté mesure $4$ cm.",
        "$5 + 11 = 16$.",
        "D'après la réciproque du théorème de Pythagore, le triangle est rectangle, et l'angle droit est opposé au côté de $4$ cm."),
      rect=(R(5), R(11), 4, True)),
    E(48420, N4, 3,
      "Un triangle $KLM$ a pour côtés $KL = 2$ cm, $LM = 3$ cm et $KM = 3{,}6$ cm. Un élève écrit : « $\\sqrt{2^2 + 3^2} = \\sqrt{13} \\approx 3{,}6$, donc le triangle est rectangle. » A-t-il raison ?",
      "Non, le triangle $KLM$ n'est pas rectangle : il faut comparer les valeurs exactes des carrés.",
      "Compare $KM^2$ et $KL^2 + LM^2$ sans arrondir.",
      S("$KM^2 = 3{,}6^2 = 12{,}96$ et $KL^2 + LM^2 = 4 + 9 = 13$.",
        "$12{,}96 \\neq 13$ : les carrés ne sont pas égaux.",
        "D'après le théorème de Pythagore (contraposée), $KLM$ n'est pas rectangle. Un arrondi ne permet jamais de démontrer une égalité."),
      rect=(2, 3, "3.6", False), step_checks=(num(sq("3.6")),)),
    E(48421, N4, 3,
      "Le triangle $NOP$ est tel que $NO = 20$ cm, $OP = 99$ cm et $NP = 101$ cm. Est-il rectangle ?",
      "Oui, le triangle $NOP$ est rectangle en $O$.",
      "Les grands nombres ne changent pas la méthode.",
      S("Le plus long côté est $[NP]$ : $NP^2 = 10\\,201$.",
        "$NO^2 + OP^2 = 400 + 9\\,801 = 10\\,201$.",
        "$NP^2 = NO^2 + OP^2$ : d'après la réciproque du théorème de Pythagore, $NOP$ est rectangle en $O$."),
      rect=(20, 99, 101, True)),
    E(48422, N4, 3,
      "Le triangle $QRS$ est tel que $QR = 12$ cm, $RS = 16$ cm et $QS = 21$ cm. Est-il rectangle ? Sinon, quelle longueur aurait dû avoir $[QS]$ pour qu'il soit rectangle en $R$ ?",
      "Non, le triangle $QRS$ n'est pas rectangle ; il aurait fallu $QS = 20$ cm.",
      "Pour la seconde question, calcule l'hypoténuse d'un triangle rectangle en $R$.",
      S("$QS^2 = 441$ et $QR^2 + RS^2 = 144 + 256 = 400$.",
        "$441 \\neq 400$ : d'après le théorème de Pythagore (contraposée), $QRS$ n'est pas rectangle.",
        "Pour un triangle rectangle en $R$, il faudrait $QS^2 = 400$, soit $QS = 20$ cm."),
      rect=(12, 16, 21, False), checks=(num(hyp(12, 16)),)),
    E(48423, N4, 4,
      "$ABCD$ est un parallélogramme tel que $AB = 12$ cm, $BC = 5$ cm et $AC = 13$ cm. Démontrer que $ABCD$ est un rectangle.",
      "$ABCD$ est un rectangle : le triangle $ABC$ est rectangle en $B$, et un parallélogramme qui a un angle droit est un rectangle.",
      "Étudie d'abord le triangle $ABC$, puis utilise une propriété des parallélogrammes.",
      S("Dans le triangle $ABC$, le plus long côté est $[AC]$ : $AC^2 = 169$ et $AB^2 + BC^2 = 144 + 25 = 169$.",
        "D'après la réciproque du théorème de Pythagore, $ABC$ est rectangle en $B$ : l'angle $\\widehat{ABC}$ est droit.",
        "Un parallélogramme qui possède un angle droit est un rectangle : $ABCD$ est un rectangle."),
      step_checks=(num(sq(13)), num(sq(12) + sq(5))), extra={"rect_check": (12, 5, 13, True)}),
    E(48424, N4, 4,
      "Les points $A$, $H$ et $B$ sont alignés dans cet ordre, avec $AH = 9$ cm et $HB = 16$ cm. Le point $C$ est tel que $CH = 12$ cm et $(CH) \\perp (AB)$. Démontrer que le triangle $ABC$ est rectangle en $C$.",
      "On calcule $AC = 15$ cm et $BC = 20$ cm ; comme $AB^2 = AC^2 + BC^2$, le triangle $ABC$ est rectangle en $C$.",
      "Calcule d'abord $AC$ et $BC$ dans les triangles rectangles en $H$.",
      S("$ACH$ est rectangle en $H$ : $AC^2 = 9^2 + 12^2 = 225$, donc $AC = 15$ cm.",
        "$BCH$ est rectangle en $H$ : $BC^2 = 16^2 + 12^2 = 400$, donc $BC = 20$ cm.",
        "$AB = 9 + 16 = 25$ cm : $AB^2 = 625$ et $AC^2 + BC^2 = 225 + 400 = 625$.",
        "D'après la réciproque du théorème de Pythagore, $ABC$ est rectangle en $C$."),
      checks=(num(hyp(9, 12)), num(hyp(16, 12))), extra={"rect_check": (hyp(9, 12), hyp(16, 12), 25, True)}),
    E(48425, N4, 4,
      "Soit $n$ un nombre strictement positif. Démontrer qu'un triangle dont les côtés mesurent $3n$, $4n$ et $5n$ est toujours rectangle.",
      "Pour tout $n > 0$ : $(3n)^2 + (4n)^2 = 25n^2 = (5n)^2$, donc d'après la réciproque du théorème de Pythagore, le triangle est rectangle.",
      "Calcule $(3n)^2$, $(4n)^2$ et $(5n)^2$ en fonction de $n^2$.",
      S("Le plus long côté mesure $5n$ : $(5n)^2 = 25n^2$.",
        "$(3n)^2 + (4n)^2 = 9n^2 + 16n^2 = 25n^2$.",
        "L'égalité est vraie quel que soit $n$ : d'après la réciproque du théorème de Pythagore, le triangle est toujours rectangle."),
      extra={"rect_check": (3 * 7, 4 * 7, 5 * 7, True)}),
    E(48426, N4, 4,
      "Un triangle a des côtés de $10$ cm, $24$ cm et $26$ cm. On allonge chacun de ses côtés de $1$ cm. Le nouveau triangle est-il encore rectangle ?",
      "Non : le premier triangle est rectangle, mais le nouveau (côtés $11$ cm, $25$ cm et $27$ cm) ne l'est pas.",
      "Teste séparément les deux triangles.",
      S("Premier triangle : $10^2 + 24^2 = 100 + 576 = 676 = 26^2$ : il est rectangle (réciproque du théorème de Pythagore).",
        "Nouveau triangle : $11^2 + 25^2 = 121 + 625 = 746$ et $27^2 = 729$.",
        "$746 \\neq 729$ : d'après le théorème de Pythagore (contraposée), le nouveau triangle n'est pas rectangle."),
      rect=(11, 25, 27, False), step_checks=(num(sq(11) + sq(25)), num(sq(27))),
      extra={"rect_check": (10, 24, 26, True)}),
    E(48427, N4, 4,
      "Sur un quadrillage à carreaux de $1$ cm de côté, le point $B$ est situé $4$ carreaux à droite et $2$ carreaux au-dessus du point $A$ ; le point $C$ est situé $2$ carreaux à droite et $6$ carreaux au-dessus de $A$. Le triangle $ABC$ est-il rectangle ? Si oui, préciser en quel sommet et sa nature exacte.",
      "Oui, le triangle $ABC$ est rectangle et isocèle en $B$.",
      "Chaque segment est l'hypoténuse d'un triangle rectangle tracé sur les lignes du quadrillage.",
      S("$AB^2 = 4^2 + 2^2 = 20$ (déplacement de $4$ horizontalement et $2$ verticalement).",
        "De $B$ à $C$ : $2$ carreaux vers la gauche et $4$ vers le haut, donc $BC^2 = 2^2 + 4^2 = 20$. De $A$ à $C$ : $AC^2 = 2^2 + 6^2 = 40$.",
        "$AC^2 = AB^2 + BC^2$ ($40 = 20 + 20$) : d'après la réciproque du théorème de Pythagore, $ABC$ est rectangle en $B$.",
        "De plus $AB^2 = BC^2$, donc $AB = BC$ : le triangle est rectangle et isocèle en $B$."),
      rect=(R(20), R(20), R(40), True)),
    E(48428, N4, 4,
      "Le triangle $MNP$ est tel que $MN = 4{,}5$ cm, $NP = 6$ cm et $MP = 7{,}5$ cm. Démontrer qu'il est rectangle, puis calculer son aire et la longueur de la hauteur issue de $N$.",
      "Oui, $MNP$ est rectangle en $N$ ; son aire est $13{,}5$ cm$^2$ et la hauteur issue de $N$ mesure $3{,}6$ cm.",
      "L'aire peut se calculer de deux façons : avec les côtés de l'angle droit, ou avec $[MP]$ et la hauteur cherchée.",
      S("$MP^2 = 56{,}25$ et $MN^2 + NP^2 = 20{,}25 + 36 = 56{,}25$ : d'après la réciproque du théorème de Pythagore, $MNP$ est rectangle en $N$.",
        "Aire $= \\dfrac{MN \\times NP}{2} = \\dfrac{4{,}5 \\times 6}{2} = 13{,}5$ cm$^2$.",
        "Avec la base $[MP]$ et la hauteur $h$ issue de $N$ : $\\dfrac{7{,}5 \\times h}{2} = 13{,}5$, donc $7{,}5 \\times h = 27$ et $h = 27 \\div 7{,}5 = 3{,}6$ cm."),
      rect=("4.5", 6, "7.5", True),
      checks=(num(D("4.5") * 6 / 2), num(2 * (D("4.5") * 6 / 2) / D("7.5")))),

    # ═════════════════════════════════════════════════════════════════════
    # Notion 5 — Résoudre un problème avec le théorème de Pythagore (48 5xx)
    # ═════════════════════════════════════════════════════════════════════
    E(48501, N5, 1,
      "Une échelle de $2{,}5$ m est appuyée contre un mur vertical. Son pied est posé sur le sol horizontal, à $0{,}7$ m du mur. À quelle hauteur le haut de l'échelle touche-t-il le mur ?",
      "Le haut de l'échelle touche le mur à $2{,}4$ m de hauteur.",
      "Le mur et le sol forment un angle droit : l'échelle est l'hypoténuse.",
      S("Le mur est perpendiculaire au sol : le triangle formé par le mur, le sol et l'échelle est rectangle, d'hypoténuse l'échelle.",
        "Hauteur$^2 = 2{,}5^2 - 0{,}7^2 = 6{,}25 - 0{,}49 = 5{,}76$.",
        "Hauteur $= \\sqrt{5{,}76} = 2{,}4$ m."),
      checks=(num(leg("2.5", "0.7")),), step_checks=(num(sq("2.5") - sq("0.7")),)),
    E(48502, N5, 1,
      "Un écran rectangulaire mesure $48$ cm de large et $36$ cm de haut. Calculer la longueur de sa diagonale.",
      "La diagonale mesure $60$ cm.",
      "La diagonale partage le rectangle en deux triangles rectangles.",
      S("La largeur, la hauteur et la diagonale forment un triangle rectangle, dont la diagonale est l'hypoténuse.",
        "Diagonale$^2 = 48^2 + 36^2 = 2\\,304 + 1\\,296 = 3\\,600$.",
        "Diagonale $= \\sqrt{3\\,600} = 60$ cm."),
      checks=(num(hyp(48, 36)),)),
    E(48503, N5, 1,
      "Un jardin rectangulaire mesure $15$ m sur $8$ m. Quelle distance parcourt-on en le traversant en ligne droite d'un coin au coin opposé ?",
      "On parcourt $17$ m.",
      "Le trajet en ligne droite est une diagonale du rectangle.",
      S("Deux côtés consécutifs du jardin et la diagonale forment un triangle rectangle.",
        "Diagonale$^2 = 15^2 + 8^2 = 225 + 64 = 289$.",
        "Diagonale $= \\sqrt{289} = 17$ m."),
      checks=(num(hyp(15, 8)),)),
    E(48504, N5, 1,
      "Un câble de $10$ m relie le sommet d'un poteau vertical à un point du sol horizontal situé à $6$ m du pied du poteau. Quelle est la hauteur du poteau ?",
      "Le poteau mesure $8$ m de haut.",
      "Ici on connaît l'hypoténuse : c'est la hauteur qui manque.",
      S("Le poteau est perpendiculaire au sol : poteau, sol et câble forment un triangle rectangle d'hypoténuse le câble.",
        "Hauteur$^2 = 10^2 - 6^2 = 100 - 36 = 64$.",
        "Hauteur $= \\sqrt{64} = 8$ m."),
      checks=(num(leg(10, 6)),)),
    E(48505, N5, 2,
      "Une rampe d'accès s'élève de $0{,}5$ m sur une distance horizontale de $6$ m. Calculer la longueur de la rampe, arrondie au centimètre.",
      "La rampe mesure environ $6{,}02$ m.",
      "Au centimètre près, une longueur en mètres s'arrondit au centième.",
      S("La hauteur et la distance horizontale sont perpendiculaires : la rampe est l'hypoténuse d'un triangle rectangle.",
        "Longueur$^2 = 6^2 + 0{,}5^2 = 36 + 0{,}25 = 36{,}25$.",
        "Longueur $= \\sqrt{36{,}25} \\approx 6{,}021$ m, soit environ $6{,}02$ m au centimètre."),
      checks=(rnd(hyp(6, "0.5"), 2),), step_checks=(num(sq(6) + sq("0.5")), rnd(hyp(6, "0.5"), 3))),
    E(48506, N5, 2,
      "Un randonneur marche $3$ km vers le nord, puis $4$ km vers l'est. À quelle distance à vol d'oiseau se trouve-t-il de son point de départ ?",
      "Il est à $5$ km de son point de départ.",
      "Les directions nord et est sont perpendiculaires.",
      S("Le nord et l'est sont perpendiculaires : les deux trajets forment les côtés de l'angle droit d'un triangle rectangle.",
        "Distance$^2 = 3^2 + 4^2 = 9 + 16 = 25$.",
        "Distance $= \\sqrt{25} = 5$ km."),
      checks=(num(hyp(3, 4)),)),
    E(48507, N5, 2,
      "Le fond rectangulaire d'un tiroir mesure $40$ cm sur $30$ cm. Peut-on y poser à plat une règle rigide de $45$ cm ?",
      "Oui : la diagonale du fond mesure $50$ cm, la règle peut être posée en diagonale.",
      "La plus grande longueur possible à plat est celle de la diagonale du fond.",
      S("La diagonale du fond est l'hypoténuse d'un triangle rectangle de côtés $40$ cm et $30$ cm.",
        "Diagonale$^2 = 1\\,600 + 900 = 2\\,500$, donc diagonale $= 50$ cm.",
        "$45 < 50$ : la règle peut être posée à plat, en diagonale (mais pas parallèlement à un bord)."),
      checks=(num(hyp(40, 30)),)),
    E(48508, N5, 2,
      "Un cerf-volant est relié à la main de Nina par un fil tendu de $50$ m. Il se trouve à la verticale d'un point du sol situé à $30$ m de Nina. On considère que la main de Nina est au niveau du sol. À quelle hauteur vole le cerf-volant ?",
      "Le cerf-volant vole à $40$ m de hauteur.",
      "Le fil tendu est l'hypoténuse.",
      S("La verticale du cerf-volant est perpendiculaire au sol : le fil, le sol et la verticale forment un triangle rectangle.",
        "Hauteur$^2 = 50^2 - 30^2 = 2\\,500 - 900 = 1\\,600$.",
        "Hauteur $= \\sqrt{1\\,600} = 40$ m."),
      checks=(num(leg(50, 30)),)),
    E(48509, N5, 2,
      "Une nappe carrée a une diagonale de $14$ dm. Calculer la longueur de son côté, arrondie au centimètre.",
      "Le côté mesure $\\sqrt{98}$ dm, soit environ $9{,}9$ dm (c'est-à-dire $99$ cm).",
      "Les deux côtés de l'angle droit d'un carré ont la même longueur $c$.",
      S("Un côté, un côté consécutif et la diagonale forment un triangle rectangle isocèle d'hypoténuse la diagonale : $c^2 + c^2 = 14^2$.",
        "$2c^2 = 196$, donc $c^2 = 98$ et $c = \\sqrt{98}$ dm.",
        "$\\sqrt{98} \\approx 9{,}899$ dm ; $1$ cm $= 0{,}1$ dm, donc $c \\approx 9{,}9$ dm, soit $99$ cm."),
      checks=(num(sq(14) / 2), rnd(root(98), 1))),
    E(48510, N5, 2,
      "Une piscine rectangulaire mesure $25$ m de long et $10$ m de large. Léa la traverse en diagonale ; Hugo nage une longueur puis une largeur pour arriver au même coin. Combien de mètres Hugo nage-t-il de plus que Léa ? Arrondir au mètre.",
      "Hugo nage environ $8$ m de plus que Léa.",
      "Calcule la diagonale avec sa valeur exacte, puis fais la différence avant d'arrondir.",
      S("Hugo nage $25 + 10 = 35$ m.",
        "Diagonale$^2 = 25^2 + 10^2 = 625 + 100 = 725$, donc Léa nage $\\sqrt{725} \\approx 26{,}93$ m.",
        "Différence : $35 - \\sqrt{725} \\approx 8{,}07$ m, soit environ $8$ m."),
      checks=(rnd(35 - hyp(25, 10), 0),), step_checks=(rnd(hyp(25, 10), 2), rnd(35 - hyp(25, 10), 2))),
    E(48511, N5, 3,
      "Un menuisier fabrique un cadre de $60$ cm sur $80$ cm. Pour vérifier que l'angle entre ces deux côtés est droit, il mesure la diagonale qui joint leurs extrémités : $99$ cm. L'angle est-il droit ?",
      "Non : l'angle n'est pas droit.",
      "Quelle devrait être la longueur de la diagonale si l'angle était droit ?",
      S("On étudie le triangle formé par les côtés de $60$ cm et $80$ cm et la diagonale de $99$ cm, qui est son plus long côté.",
        "$60^2 + 80^2 = 3\\,600 + 6\\,400 = 10\\,000$ et $99^2 = 9\\,801$.",
        "$9\\,801 \\neq 10\\,000$ : d'après le théorème de Pythagore (contraposée), le triangle n'est pas rectangle, l'angle n'est pas droit (il faudrait une diagonale de $100$ cm)."),
      rect=(60, 80, 99, False)),
    E(48512, N5, 3,
      "Pour tracer un angle droit sur un chantier, un maçon tend une corde de façon à former un triangle de côtés $3$ m, $4$ m et $5$ m. Pourquoi obtient-il un angle droit ? Où est-il situé ?",
      "Oui, l'angle est droit : $3^2 + 4^2 = 5^2$, donc d'après la réciproque du théorème de Pythagore, le triangle est rectangle ; l'angle droit est entre les côtés de $3$ m et de $4$ m.",
      "Teste l'égalité de Pythagore sur ces trois longueurs.",
      S("Le plus long côté mesure $5$ m : $5^2 = 25$.",
        "$3^2 + 4^2 = 9 + 16 = 25$.",
        "D'après la réciproque du théorème de Pythagore, le triangle est rectangle ; l'angle droit est opposé au côté de $5$ m, donc entre les côtés de $3$ m et $4$ m."),
      extra={"rect_check": (3, 4, 5, True)}),
    E(48513, N5, 3,
      "Un mât vertical est maintenu par un câble fixé sur le mât à $4{,}5$ m de hauteur et au sol à $2$ m du pied du mât. Il faut prévoir $30$ cm de câble en plus pour les fixations. Quelle longueur de câble faut-il au minimum ? Donner le résultat arrondi par excès au dixième de mètre.",
      "Il faut au minimum $5{,}3$ m de câble.",
      "Calcule d'abord la longueur tendue entre les deux points de fixation, puis ajoute $0{,}3$ m.",
      S("Le mât est perpendiculaire au sol : la partie tendue du câble est l'hypoténuse d'un triangle rectangle de côtés $4{,}5$ m et $2$ m.",
        "Longueur tendue$^2 = 4{,}5^2 + 2^2 = 20{,}25 + 4 = 24{,}25$, donc longueur tendue $= \\sqrt{24{,}25} \\approx 4{,}924$ m.",
        "Avec les fixations : $4{,}924 + 0{,}3 \\approx 5{,}224$ m.",
        "Arrondi par excès au dixième (pour ne pas manquer de câble) : $5{,}3$ m."),
      step_checks=(num(sq("4.5") + sq(2)), rnd(hyp("4.5", 2), 3), rnd(hyp("4.5", 2) + D("0.3"), 3)),
      extra={"ceil_tenth": (hyp("4.5", 2) + D("0.3"), "5{,}3")}),
    E(48514, N5, 3,
      "Dans un repère orthonormé d'unité $1$ cm, on place les points $A(1 ; 2)$ et $B(7 ; 10)$. Calculer la distance $AB$.",
      "$AB = 10$ cm",
      "Place le point $C(7 ; 2)$ : que dire du triangle $ABC$ ?",
      S("Le point $C(7 ; 2)$ a la même ordonnée que $A$ et la même abscisse que $B$ : le triangle $ABC$ est rectangle en $C$.",
        "$AC = 7 - 1 = 6$ cm et $BC = 10 - 2 = 8$ cm.",
        "$AB^2 = 6^2 + 8^2 = 100$, donc $AB = 10$ cm."),
      checks=(num(hyp(7 - 1, 10 - 2)),)),
    E(48515, N5, 3,
      "L'écran rectangulaire d'un téléphone a une diagonale de $15$ cm et une largeur de $7$ cm. Calculer sa hauteur, arrondie au millimètre.",
      "La hauteur de l'écran mesure environ $13{,}3$ cm.",
      "La diagonale est l'hypoténuse : on cherche un côté de l'angle droit.",
      S("Largeur, hauteur et diagonale forment un triangle rectangle d'hypoténuse la diagonale.",
        "Hauteur$^2 = 15^2 - 7^2 = 225 - 49 = 176$.",
        "Hauteur $= \\sqrt{176} \\approx 13{,}27$ cm, soit environ $13{,}3$ cm au millimètre."),
      checks=(rnd(leg(15, 7), 1),), step_checks=(num(sq(15) - sq(7)),)),
    E(48516, N5, 3,
      "Un bateau part du port $P$ et navigue $12$ km plein est jusqu'à une bouée $B$, puis $5$ km plein sud jusqu'à une île $I$. Il revient ensuite directement au port. Quelle distance totale a-t-il parcourue ?",
      "Il a parcouru $30$ km au total.",
      "Il manque la distance du retour $IP$.",
      S("L'est et le sud sont perpendiculaires : le triangle $PBI$ est rectangle en $B$.",
        "$PI^2 = 12^2 + 5^2 = 144 + 25 = 169$, donc $PI = 13$ km.",
        "Distance totale : $12 + 5 + 13 = 30$ km."),
      checks=(num(12 + 5 + hyp(12, 5)),)),
    E(48517, N5, 3,
      "La façade d'une tente est un triangle isocèle : sa base, posée au sol, mesure $2{,}4$ m et ses deux autres côtés mesurent $2$ m. Calculer la hauteur de la tente.",
      "La tente mesure $1{,}6$ m de haut.",
      "La hauteur issue du sommet coupe la base en son milieu et lui est perpendiculaire.",
      S("Dans un triangle isocèle, la hauteur issue du sommet principal coupe la base en son milieu : chaque moitié mesure $1{,}2$ m.",
        "On obtient un triangle rectangle d'hypoténuse $2$ m : hauteur$^2 = 2^2 - 1{,}2^2 = 4 - 1{,}44 = 2{,}56$.",
        "Hauteur $= \\sqrt{2{,}56} = 1{,}6$ m."),
      checks=(num(leg(2, "1.2")),)),
    E(48518, N5, 4,
      "Une échelle de $6{,}5$ m est appuyée contre un mur vertical, son pied étant à $2{,}5$ m du mur. Le pied glisse et s'éloigne encore de $1{,}4$ m du mur. De combien le haut de l'échelle est-il descendu ?",
      "Le haut de l'échelle est descendu de $0{,}8$ m.",
      "Calcule la hauteur atteinte avant, puis après le glissement.",
      S("Avant : hauteur$^2 = 6{,}5^2 - 2{,}5^2 = 42{,}25 - 6{,}25 = 36$, donc l'échelle atteint $6$ m.",
        "Après : le pied est à $2{,}5 + 1{,}4 = 3{,}9$ m du mur, et hauteur$^2 = 42{,}25 - 15{,}21 = 27{,}04$, donc hauteur $= 5{,}2$ m.",
        "Le haut de l'échelle est descendu de $6 - 5{,}2 = 0{,}8$ m."),
      checks=(num(leg("6.5", "2.5") - leg("6.5", "3.9")),),
      step_checks=(num(leg("6.5", "2.5")), num(leg("6.5", "3.9")), num(sq("3.9")))),
    E(48519, N5, 4,
      "Un champ rectangulaire a une aire de $1\\,200$ m$^2$ et une largeur de $30$ m. Un chemin le traverse en diagonale. Calculer la longueur de ce chemin.",
      "Le chemin mesure $50$ m.",
      "Utilise l'aire pour trouver la longueur du champ.",
      S("Longueur du champ : $1\\,200 \\div 30 = 40$ m.",
        "La diagonale est l'hypoténuse d'un triangle rectangle de côtés $40$ m et $30$ m : diagonale$^2 = 1\\,600 + 900 = 2\\,500$.",
        "Diagonale $= \\sqrt{2\\,500} = 50$ m."),
      checks=(num(hyp(D(1200) / 30, 30)),)),
    E(48520, N5, 4,
      "Un poteau vertical de $9$ m se brise à une hauteur $h$ (en mètres) : la partie haute bascule sans se détacher et son sommet touche le sol à $3$ m du pied du poteau. Expliquer pourquoi $h^2 + 3^2 = (9 - h)^2$, puis vérifier que $h = 4$ convient.",
      "La partie restée debout, le sol et la partie brisée forment un triangle rectangle d'hypoténuse $9 - h$ ; pour $h = 4$ : $4^2 + 3^2 = 25 = 5^2$, donc $h = 4$ m convient.",
      "La partie brisée mesure $9 - h$ : quel rôle joue-t-elle dans le triangle ?",
      S("La partie debout (hauteur $h$) est perpendiculaire au sol ; la partie brisée, de longueur $9 - h$, relie son sommet au point du sol.",
        "Le triangle est rectangle au pied du poteau, d'hypoténuse la partie brisée : $h^2 + 3^2 = (9 - h)^2$.",
        "Pour $h = 4$ : $4^2 + 3^2 = 16 + 9 = 25$ et $(9 - 4)^2 = 5^2 = 25$. L'égalité est vraie : le poteau s'est brisé à $4$ m de hauteur."),
      checks=(num(sq(4) + sq(3)), num(sq(9 - 4)))),
    E(48521, N5, 4,
      "Dans un repère orthonormé d'unité $1$ cm, on donne $A(1 ; 2)$, $B(4 ; 6)$ et $C(8 ; 3)$. Démontrer que le triangle $ABC$ est rectangle et isocèle.",
      "Oui : $AB^2 = BC^2 = 25$ et $AC^2 = 50 = AB^2 + BC^2$, donc le triangle $ABC$ est rectangle et isocèle en $B$.",
      "Calcule $AB^2$, $BC^2$ et $AC^2$ à l'aide de triangles rectangles tracés parallèlement aux axes.",
      S("De $A$ à $B$ : $3$ unités horizontalement et $4$ verticalement, donc $AB^2 = 3^2 + 4^2 = 25$.",
        "De $B$ à $C$ : $4$ unités horizontalement et $3$ verticalement, donc $BC^2 = 4^2 + 3^2 = 25$. De $A$ à $C$ : $7$ et $1$, donc $AC^2 = 49 + 1 = 50$.",
        "$AC^2 = AB^2 + BC^2$ : d'après la réciproque du théorème de Pythagore, $ABC$ est rectangle en $B$.",
        "$AB^2 = BC^2$, donc $AB = BC = 5$ cm : le triangle est aussi isocèle en $B$."),
      rect=(R(3 * 3 + 4 * 4), R(4 * 4 + 3 * 3), R(7 * 7 + 1 * 1), True)),
    E(48522, N5, 4,
      "Un coffre a la forme d'un pavé droit : son fond est un rectangle de $1{,}2$ m sur $0{,}5$ m et sa hauteur est $0{,}84$ m. On admet que la diagonale du fond, une arête verticale et la grande diagonale du coffre forment un triangle rectangle. Un tuyau rigide de $1{,}5$ m peut-il tenir dans le coffre fermé ?",
      "Oui : la grande diagonale du coffre mesure environ $1{,}55$ m, plus que $1{,}5$ m.",
      "Calcule d'abord la diagonale du fond, puis utilise-la dans le triangle admis par l'énoncé.",
      S("Diagonale du fond : $d^2 = 1{,}2^2 + 0{,}5^2 = 1{,}44 + 0{,}25 = 1{,}69$, donc $d = 1{,}3$ m.",
        "Grande diagonale $D$ : $D^2 = d^2 + 0{,}84^2 = 1{,}69 + 0{,}7056 = 2{,}3956$.",
        "$D = \\sqrt{2{,}3956} \\approx 1{,}548$ m $> 1{,}5$ m : le tuyau peut être placé selon la grande diagonale."),
      checks=(rnd(hyp(hyp("1.2", "0.5"), "0.84"), 2),),
      step_checks=(num(hyp("1.2", "0.5")), num(sq("0.84")), num(sq(hyp("1.2", "0.5")) + sq("0.84")), rnd(hyp(hyp("1.2", "0.5"), "0.84"), 3))),
    E(48523, N5, 4,
      "Le triangle $ABC$ est rectangle en $A$. Son aire est de $24$ cm$^2$ et $AB = 6$ cm. Calculer $BC$.",
      "$BC = 10$ cm",
      "L'aire d'un triangle rectangle se calcule avec ses deux côtés de l'angle droit.",
      S("Aire $= \\dfrac{AB \\times AC}{2}$, donc $\\dfrac{6 \\times AC}{2} = 24$, soit $3 \\times AC = 24$ et $AC = 8$ cm.",
        "Le triangle est rectangle en $A$ : $BC^2 = AB^2 + AC^2 = 36 + 64 = 100$.",
        "$BC = \\sqrt{100} = 10$ cm."),
      checks=(num(hyp(6, D(2 * 24) / 6)),)),
    E(48524, N5, 4,
      "Un randonneur part du point $A$. Il marche $6$ km vers l'est jusqu'à $B$, puis $8$ km vers le nord jusqu'à $C$, puis $2{,}5$ km vers l'ouest jusqu'à $D$. À quelle distance de $A$ se trouve-t-il ? Arrondir au dixième de kilomètre.",
      "Il se trouve à environ $8{,}7$ km du point $A$.",
      "Cherche de combien il s'est déplacé au total vers l'est et vers le nord par rapport à $A$.",
      S("Par rapport à $A$, le point $D$ est à $6 - 2{,}5 = 3{,}5$ km vers l'est et à $8$ km vers le nord.",
        "Ces deux déplacements sont perpendiculaires : $AD^2 = 3{,}5^2 + 8^2 = 12{,}25 + 64 = 76{,}25$.",
        "$AD = \\sqrt{76{,}25} \\approx 8{,}73$ km, soit environ $8{,}7$ km."),
      checks=(rnd(hyp(D(6) - D("2.5"), 8), 1),), step_checks=(num(sq("3.5") + sq(8)), rnd(hyp("3.5", 8), 2))),
]

# Mini-quiz (quizExerciseIds de cours_quatrieme/chapitre_8.json) : uniquement
# des exercices curés (identifiants stables, jamais régénérés), de difficulté
# 1-2, couvrant des compétences complémentaires de la notion.
QUIZ = {
    "pythagore-hypotenuse-et-egalite": (48101, 48104, 48108),
    "carres-et-racines-carrees": (48202, 48209, 48210),
    "pythagore-calculer-une-longueur": (48301, 48304, 48308),
    "triangle-rectangle-ou-non": (48401, 48402, 48412),
    "problemes-avec-pythagore": (48501, 48502, 48506),
}


def check_all(exercises=EXERCISES) -> list[str]:
    """Rejoue tous les contrôles ; renvoie la liste des problèmes (vide si
    tout est cohérent). Utilisé par main() et par les tests."""
    problems = []
    ids = [e.id for e in exercises]
    if len(ids) != len(set(ids)):
        problems.append("identifiants dupliqués")
    enonces = [e.enonce for e in exercises]
    if len(enonces) != len(set(enonces)):
        problems.append("énoncés dupliqués")
    for e in exercises:
        p = f"exercice {e.id}"
        notion_index = NOTIONS.index(e.notion) + 1
        if not (48_000 + 100 * notion_index < e.id < 48_000 + 100 * (notion_index + 1)):
            problems.append(f"{p} : identifiant hors du bloc de sa notion")
        if e.difficulty not in (1, 2, 3, 4):
            problems.append(f"{p} : difficulté {e.difficulty} invalide")
        if not (e.enonce and e.answer and e.hint and e.steps):
            problems.append(f"{p} : champ vide")
        steps_text = "\n".join(e.steps)
        for s in e.checks:
            if s not in e.answer:
                problems.append(f"{p} : valeur calculée {s!r} absente de la réponse")
        for s in e.step_checks:
            if s not in steps_text:
                problems.append(f"{p} : valeur calculée {s!r} absente de la correction")
        rect = e.rect or e.extra.get("rect_check")
        if rect is not None:
            *sides, expected = rect
            if is_right(*sides) is not expected:
                problems.append(f"{p} : verdict rectangle={expected} contredit par le calcul {sides}")
        if e.rect is not None:
            prefix = "Oui" if e.rect[3] else "Non"
            if not e.answer.startswith(prefix):
                problems.append(f"{p} : la réponse devrait commencer par « {prefix} »")
        if "ceil_tenth" in e.extra:
            value, expected = e.extra["ceil_tenth"]
            ceil = num(D(value).quantize(Decimal("0.1"), rounding="ROUND_CEILING"))
            if ceil != expected or expected not in e.answer:
                problems.append(f"{p} : arrondi par excès attendu {ceil!r}")
        for field_name in ("enonce", "answer", "hint", *(f"steps[{i}]" for i in range(len(e.steps)))):
            text = getattr(e, field_name) if not field_name.startswith("steps") else e.steps[int(field_name[6:-1])]
            if text.count("$") % 2:
                problems.append(f"{p} : nombre impair de « $ » dans {field_name}")
        if e.hint.strip() in e.answer:
            problems.append(f"{p} : l'indice révèle la réponse")
    by_id = {e.id: e for e in exercises}
    for notion_id, quiz in QUIZ.items():
        for q in quiz:
            if q not in by_id or by_id[q].difficulty > 2:
                problems.append(f"quiz {notion_id} : {q} absent ou trop difficile")
    return problems


def build() -> list[dict]:
    """Exercices du chapitre 8 (pilote) seulement."""
    return [e.to_json() for e in sorted(EXERCISES, key=lambda e: e.id)]


# ── Autres chapitres (tools/quatrieme/banque_chNN.py) ─────────────────────────
sys.path.insert(0, str(Path(__file__).resolve().parent))
from quatrieme import banque_commun  # noqa: E402
from quatrieme.chapitres import modules as chapter_modules  # noqa: E402


def check_all_chapters() -> list[str]:
    """Contrôles du chapitre 8 puis de chaque chapitre rédigé."""
    problems = list(check_all())
    for number, _cours, banque in chapter_modules():
        problems += [f"[Chapitre_{number}] {p}" for p in banque_commun.check_chapter(banque)]
    return problems


def build_all() -> list[dict]:
    """Banque complète écrite dans exercises_bank_quatrieme.json."""
    out = build()
    for _number, _cours, banque in chapter_modules():
        out += banque_commun.build_chapter(banque)
    return sorted(out, key=lambda e: e["id"])


def main() -> int:
    problems = check_all_chapters()
    data = build_all()
    ids = [e["id"] for e in data]
    if len(ids) != len(set(ids)):
        problems.append("identifiants dupliqués entre chapitres")
    if problems:
        print("ERREUR — banque non écrite :", file=sys.stderr)
        for p in problems:
            print(f"  - {p}", file=sys.stderr)
        return 1
    OUTPUT_PATH.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"OK — {len(data)} exercices -> {OUTPUT_PATH}")
    return 0


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    raise SystemExit(main())
