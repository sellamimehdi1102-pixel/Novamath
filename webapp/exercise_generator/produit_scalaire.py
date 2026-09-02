"""Génération symbolique d'exercices sur le produit scalaire (Première,
Chapitre_7 : "Produit scalaire, colinéarité et orthogonalité de vecteurs",
"Autres définitions et propriétés").

Même patron que webapp/exercise_generator/second_degre.py : familles à score
fixe (profondeur de raisonnement, pas taille des nombres), tout résultat
annoncé calculé par sympy. Voir webapp/exercise_generator/trigonometrie.py
pour le contexte de la mission "rééquilibrage additif" (2026-09-01).
"""
import random
from dataclasses import dataclass
from typing import Callable, Optional

import sympy
from sympy import Rational, cos, latex, pi, sqrt, symbols

CHAPTER_ID = "Chapitre_7"
NOTION_PRODUIT_SCALAIRE = "Produit scalaire, colinéarité et orthogonalité de vecteurs"
NOTION_AUTRES = "Autres définitions et propriétés"

GENERATED_ID_OFFSET = 970_000

LEVEL_META = {
    1: {"emoji": "🟢", "label": "Niveau 1 — Fondamental"},
    2: {"emoji": "🟡", "label": "Niveau 2 — Intermédiaire"},
    3: {"emoji": "🟠", "label": "Niveau 3 — Avancé"},
    4: {"emoji": "🔴", "label": "Niveau 4 — Difficile"},
    5: {"emoji": "🟣", "label": "Niveau 5 — Défi"},
}

_ANGLES_REMARQUABLES = [
    ("\\dfrac{\\pi}{3}", pi / 3, Rational(1, 2)),
    ("\\dfrac{\\pi}{4}", pi / 4, sqrt(2) / 2),
    ("\\dfrac{\\pi}{6}", pi / 6, sqrt(3) / 2),
    ("\\dfrac{2\\pi}{3}", 2 * pi / 3, Rational(-1, 2)),
    ("\\dfrac{3\\pi}{4}", 3 * pi / 4, -sqrt(2) / 2),
    ("\\dfrac{\\pi}{2}", pi / 2, sympy.Integer(0)),
]


def _nz(rng: random.Random, lo: int, hi: int) -> int:
    choices = [n for n in range(lo, hi + 1) if n != 0]
    return rng.choice(choices)


def _vec_latex(x, y) -> str:
    return f"\\begin{{pmatrix}} {x} \\\\ {y} \\end{{pmatrix}}"


@dataclass(frozen=True)
class Family:
    id: str
    level: int
    label: str
    notion: str
    generate: Callable[[random.Random], Optional[dict]]
    structure_hint: str
    rule_hint: str


# ── Famille 1 — Produit scalaire à partir des coordonnées ──────────────────

def _gen_produit_coordonnees(rng: random.Random) -> Optional[dict]:
    x1, y1, x2, y2 = (_nz(rng, -8, 8) for _ in range(4))
    resultat = x1 * x2 + y1 * y2
    enonce = (
        f"Dans un repère orthonormé, on donne $\\vec{{u}}{_vec_latex(x1, y1)}$ et "
        f"$\\vec{{v}}{_vec_latex(x2, y2)}$. Calculer $\\vec{{u}} \\cdot \\vec{{v}}$."
    )
    answer = f"$\\vec{{u}} \\cdot \\vec{{v}} = {resultat}$"
    steps = [
        f"Étape 1 — On utilise la formule $\\vec{{u}} \\cdot \\vec{{v}} = x_u x_v + y_u y_v$.",
        f"Étape 2 — $\\vec{{u}} \\cdot \\vec{{v}} = {x1} \\times {x2} + {y1} \\times {y2} = {x1*x2} + {y1*y2}$.",
        f"Étape 3 — {answer}.",
    ]
    return {"enonce": enonce, "answer": answer, "steps": steps, "notion": NOTION_PRODUIT_SCALAIRE}


# ── Famille 2 — Norme d'un vecteur ──────────────────────────────────────────

def _gen_norme(rng: random.Random) -> Optional[dict]:
    x1, y1 = _nz(rng, -9, 9), _nz(rng, -9, 9)
    carre = x1**2 + y1**2
    norme = sqrt(carre)
    enonce = f"Dans un repère orthonormé, on donne $\\vec{{u}}{_vec_latex(x1, y1)}$. Calculer $\\|\\vec{{u}}\\|$ (valeur exacte)."
    answer = f"$\\|\\vec{{u}}\\| = {latex(sympy.simplify(norme))}$"
    steps = [
        f"Étape 1 — On utilise la formule $\\|\\vec{{u}}\\| = \\sqrt{{x_u^2 + y_u^2}}$.",
        f"Étape 2 — $\\|\\vec{{u}}\\| = \\sqrt{{{x1}^2 + {y1}^2}} = \\sqrt{{{carre}}}$.",
        f"Étape 3 — {answer}.",
    ]
    return {"enonce": enonce, "answer": answer, "steps": steps, "notion": NOTION_AUTRES}


# ── Famille 3 — Test d'orthogonalité ────────────────────────────────────────

def _gen_orthogonalite(rng: random.Random) -> Optional[dict]:
    x1, y1 = _nz(rng, -8, 8), _nz(rng, -8, 8)
    force_ortho = rng.random() < 0.5
    if force_ortho and x1 != 0:
        # v orthogonal exact : (y1, -x1) (à un facteur près)
        k = _nz(rng, -3, 3)
        x2, y2 = k * y1, -k * x1
    else:
        x2, y2 = _nz(rng, -8, 8), _nz(rng, -8, 8)
    produit = x1 * x2 + y1 * y2
    est_ortho = produit == 0
    enonce = (
        f"Dans un repère orthonormé, on donne $\\vec{{u}}{_vec_latex(x1, y1)}$ et "
        f"$\\vec{{v}}{_vec_latex(x2, y2)}$. Les vecteurs $\\vec{{u}}$ et $\\vec{{v}}$ sont-ils orthogonaux ? Justifier."
    )
    if est_ortho:
        answer = f"Oui, $\\vec{{u}} \\cdot \\vec{{v}} = 0$, donc $\\vec{{u}}$ et $\\vec{{v}}$ sont orthogonaux."
    else:
        answer = f"Non, $\\vec{{u}} \\cdot \\vec{{v}} = {produit} \\neq 0$, donc $\\vec{{u}}$ et $\\vec{{v}}$ ne sont pas orthogonaux."
    steps = [
        f"Étape 1 — Deux vecteurs sont orthogonaux si et seulement si leur produit scalaire est nul.",
        f"Étape 2 — $\\vec{{u}} \\cdot \\vec{{v}} = {x1} \\times {x2} + {y1} \\times {y2} = {produit}$.",
        f"Étape 3 — {answer}",
    ]
    return {"enonce": enonce, "answer": answer, "steps": steps, "notion": NOTION_PRODUIT_SCALAIRE}


# ── Famille 4 — Test de colinéarité (déterminant) ──────────────────────────

def _gen_colinearite(rng: random.Random) -> Optional[dict]:
    x1, y1 = _nz(rng, -7, 7), _nz(rng, -7, 7)
    force_colin = rng.random() < 0.5
    if force_colin:
        k = _nz(rng, -3, 3)
        x2, y2 = k * x1, k * y1
    else:
        x2, y2 = _nz(rng, -7, 7), _nz(rng, -7, 7)
    det = x1 * y2 - x2 * y1
    est_colin = det == 0
    enonce = (
        f"Dans un repère, on donne $\\vec{{u}}{_vec_latex(x1, y1)}$ et "
        f"$\\vec{{v}}{_vec_latex(x2, y2)}$. Les vecteurs $\\vec{{u}}$ et $\\vec{{v}}$ sont-ils colinéaires ? Justifier."
    )
    if est_colin:
        answer = f"Oui, $x_u y_v - x_v y_u = 0$, donc $\\vec{{u}}$ et $\\vec{{v}}$ sont colinéaires."
    else:
        answer = f"Non, $x_u y_v - x_v y_u = {det} \\neq 0$, donc $\\vec{{u}}$ et $\\vec{{v}}$ ne sont pas colinéaires."
    steps = [
        f"Étape 1 — Deux vecteurs sont colinéaires si et seulement si $x_u y_v - x_v y_u = 0$.",
        f"Étape 2 — $x_u y_v - x_v y_u = {x1} \\times {y2} - {x2} \\times {y1} = {det}$.",
        f"Étape 3 — {answer}",
    ]
    return {"enonce": enonce, "answer": answer, "steps": steps, "notion": NOTION_PRODUIT_SCALAIRE}


# ── Famille 5 — Produit scalaire via normes et angle ───────────────────────

def _gen_produit_norme_angle(rng: random.Random) -> Optional[dict]:
    label, theta, c = rng.choice(_ANGLES_REMARQUABLES)
    n1, n2 = rng.randint(1, 9), rng.randint(1, 9)
    resultat = sympy.simplify(n1 * n2 * c)
    enonce = (
        f"On donne deux vecteurs $\\vec{{u}}$ et $\\vec{{v}}$ tels que $\\|\\vec{{u}}\\| = {n1}$, "
        f"$\\|\\vec{{v}}\\| = {n2}$ et $\\left(\\vec{{u}},\\vec{{v}}\\right) = {label}$. "
        f"Calculer $\\vec{{u}} \\cdot \\vec{{v}}$ (valeur exacte)."
    )
    answer = f"$\\vec{{u}} \\cdot \\vec{{v}} = {latex(resultat)}$"
    steps = [
        f"Étape 1 — On utilise la formule $\\vec{{u}} \\cdot \\vec{{v}} = \\|\\vec{{u}}\\| \\times \\|\\vec{{v}}\\| \\times \\cos\\left(\\vec{{u}},\\vec{{v}}\\right)$.",
        f"Étape 2 — $\\vec{{u}} \\cdot \\vec{{v}} = {n1} \\times {n2} \\times \\cos\\left({label}\\right) = {n1*n2} \\times {latex(c)}$.",
        f"Étape 3 — {answer}.",
    ]
    return {"enonce": enonce, "answer": answer, "steps": steps, "notion": NOTION_AUTRES}


# ── Famille 6 — Trouver une coordonnée pour l'orthogonalité ────────────────

def _gen_trouver_coordonnee_orthogonale(rng: random.Random) -> Optional[dict]:
    x1, y1 = _nz(rng, -7, 7), _nz(rng, -7, 7)
    x2 = _nz(rng, -7, 7)
    if y1 == 0:
        return None
    solutions = sympy.solve(sympy.Eq(x1 * x2 + y1 * symbols("m"), 0), symbols("m"))
    if not solutions:
        return None
    m_val = solutions[0]
    enonce = (
        f"Dans un repère orthonormé, on donne $\\vec{{u}}{_vec_latex(x1, y1)}$ et "
        f"$\\vec{{v}}\\begin{{pmatrix}} {x2} \\\\ m \\end{{pmatrix}}$, où $m$ est un réel inconnu. "
        f"Déterminer $m$ pour que $\\vec{{u}}$ et $\\vec{{v}}$ soient orthogonaux."
    )
    answer = f"$m = {latex(m_val)}$"
    steps = [
        f"Étape 1 — $\\vec{{u}}$ et $\\vec{{v}}$ orthogonaux $\\iff \\vec{{u}} \\cdot \\vec{{v}} = 0$.",
        f"Étape 2 — $\\vec{{u}} \\cdot \\vec{{v}} = {x1} \\times {x2} + {y1} \\times m = {x1*x2} + {y1}m$.",
        f"Étape 3 — On résout ${x1*x2} + {y1}m = 0$ : {answer}.",
    ]
    return {"enonce": enonce, "answer": answer, "steps": steps, "notion": NOTION_PRODUIT_SCALAIRE}


# ── Familles supplémentaires — mission "diversification structurelle"
# (2026-09-02) : les 6 familles ci-dessus manipulent toujours des vecteurs
# donnés DIRECTEMENT par leurs coordonnées (structure unique, auditée à
# 96-98% de quasi-doublon). Nouvelles familles : vecteurs à calculer à partir
# de points (une étape de plus), sommes de vecteurs, et problèmes inverses —
# jamais mélangées à FAMILIES/generate_pool (baseline figée).

def _gen_produit_points(rng: random.Random) -> Optional[dict]:
    """Contexte géométrique : A, B, C donnés par leurs coordonnées, il faut
    D'ABORD calculer les vecteurs AB et AC avant d'appliquer le produit
    scalaire (structure différente de _gen_produit_coordonnees)."""
    xa, ya = _nz(rng, -6, 6), _nz(rng, -6, 6)
    xb, yb = _nz(rng, -6, 6), _nz(rng, -6, 6)
    xc, yc = _nz(rng, -6, 6), _nz(rng, -6, 6)
    if (xa, ya) in {(xb, yb), (xc, yc)}:
        return None
    xab, yab = xb - xa, yb - ya
    xac, yac = xc - xa, yc - ya
    resultat = xab * xac + yab * yac
    enonce = (
        f"Dans un repère orthonormé, on donne $A({xa} ; {ya})$, $B({xb} ; {yb})$ et $C({xc} ; {yc})$. "
        f"Calculer $\\vec{{AB}} \\cdot \\vec{{AC}}$."
    )
    answer = f"$\\vec{{AB}} \\cdot \\vec{{AC}} = {resultat}$"
    steps = [
        f"Étape 1 — $\\vec{{AB}}{_vec_latex(xab, yab)}$ et $\\vec{{AC}}{_vec_latex(xac, yac)}$.",
        f"Étape 2 — $\\vec{{AB}} \\cdot \\vec{{AC}} = {xab} \\times {xac} + {yab} \\times {yac} = {resultat}$.",
    ]
    return {"enonce": enonce, "answer": answer, "steps": steps, "notion": NOTION_PRODUIT_SCALAIRE}


def _gen_norme_somme(rng: random.Random) -> Optional[dict]:
    """Norme d'une SOMME de deux vecteurs : il faut d'abord additionner les
    coordonnées (structure différente de _gen_norme, qui porte sur un seul
    vecteur donné directement)."""
    x1, y1 = _nz(rng, -6, 6), _nz(rng, -6, 6)
    x2, y2 = _nz(rng, -6, 6), _nz(rng, -6, 6)
    xs, ys = x1 + x2, y1 + y2
    carre = xs ** 2 + ys ** 2
    norme = sympy.simplify(sqrt(carre))
    enonce = (
        f"Dans un repère orthonormé, on donne $\\vec{{u}}{_vec_latex(x1, y1)}$ et $\\vec{{v}}{_vec_latex(x2, y2)}$. "
        f"Calculer $\\|\\vec{{u}} + \\vec{{v}}\\|$ (valeur exacte)."
    )
    answer = f"$\\|\\vec{{u}} + \\vec{{v}}\\| = {latex(norme)}$"
    steps = [
        f"Étape 1 — $\\vec{{u}} + \\vec{{v}}{_vec_latex(xs, ys)}$ (on additionne les coordonnées).",
        f"Étape 2 — $\\|\\vec{{u}} + \\vec{{v}}\\| = \\sqrt{{{xs}^2 + {ys}^2}} = \\sqrt{{{carre}}} = {latex(norme)}$.",
    ]
    return {"enonce": enonce, "answer": answer, "steps": steps, "notion": NOTION_AUTRES}


def _gen_orthogonalite_triangle(rng: random.Random) -> Optional[dict]:
    """Contexte géométrique : montrer qu'un triangle est rectangle en A à
    partir des coordonnées de A, B, C (structure différente de
    _gen_orthogonalite, où les vecteurs sont donnés directement)."""
    xa, ya = _nz(rng, -6, 6), _nz(rng, -6, 6)
    if rng.random() < 0.5:
        k = _nz(rng, -3, 3)
        dx, dy = _nz(rng, -5, 5), _nz(rng, -5, 5)
        xb, yb = xa + dx, ya + dy
        xc, yc = xa + k * dy, ya - k * dx
    else:
        xb, yb = xa + _nz(rng, -6, 6), ya + _nz(rng, -6, 6)
        xc, yc = xa + _nz(rng, -6, 6), ya + _nz(rng, -6, 6)
    xab, yab = xb - xa, yb - ya
    xac, yac = xc - xa, yc - ya
    produit = xab * xac + yab * yac
    est_rect = produit == 0
    enonce = (
        f"On donne $A({xa} ; {ya})$, $B({xb} ; {yb})$ et $C({xc} ; {yc})$. Le triangle $ABC$ est-il "
        f"rectangle en $A$ ? Justifier."
    )
    if est_rect:
        answer = f"Oui, $\\vec{{AB}} \\cdot \\vec{{AC}} = 0$, donc le triangle est rectangle en $A$."
    else:
        answer = f"Non, $\\vec{{AB}} \\cdot \\vec{{AC}} = {produit} \\neq 0$, donc le triangle n'est pas rectangle en $A$."
    steps = [
        f"Étape 1 — $\\vec{{AB}}{_vec_latex(xab, yab)}$ et $\\vec{{AC}}{_vec_latex(xac, yac)}$.",
        f"Étape 2 — Le triangle est rectangle en $A$ si et seulement si $\\vec{{AB}} \\cdot \\vec{{AC}} = 0$.",
        f"Étape 3 — $\\vec{{AB}} \\cdot \\vec{{AC}} = {xab} \\times {xac} + {yab} \\times {yac} = {produit}$. {answer}",
    ]
    return {"enonce": enonce, "answer": answer, "steps": steps, "notion": NOTION_PRODUIT_SCALAIRE}


def _gen_alignement_points(rng: random.Random) -> Optional[dict]:
    """Alignement de trois points via colinéarité de AB et AC (structure
    différente de _gen_colinearite, qui teste directement deux vecteurs)."""
    xa, ya = _nz(rng, -6, 6), _nz(rng, -6, 6)
    if rng.random() < 0.5:
        k = _nz(rng, -3, 3)
        dx, dy = _nz(rng, -5, 5), _nz(rng, -5, 5)
        xb, yb = xa + dx, ya + dy
        xc, yc = xa + k * dx, ya + k * dy
    else:
        xb, yb = xa + _nz(rng, -6, 6), ya + _nz(rng, -6, 6)
        xc, yc = xa + _nz(rng, -6, 6), ya + _nz(rng, -6, 6)
    xab, yab = xb - xa, yb - ya
    xac, yac = xc - xa, yc - ya
    det = xab * yac - xac * yab
    aligne = det == 0
    enonce = f"On donne $A({xa} ; {ya})$, $B({xb} ; {yb})$ et $C({xc} ; {yc})$. Les points $A$, $B$, $C$ sont-ils alignés ?"
    if aligne:
        answer = f"Oui, $\\vec{{AB}}$ et $\\vec{{AC}}$ sont colinéaires, donc $A$, $B$, $C$ sont alignés."
    else:
        answer = f"Non, le déterminant vaut ${det} \\neq 0$, donc $A$, $B$, $C$ ne sont pas alignés."
    steps = [
        f"Étape 1 — $\\vec{{AB}}{_vec_latex(xab, yab)}$ et $\\vec{{AC}}{_vec_latex(xac, yac)}$.",
        "Étape 2 — $A$, $B$, $C$ sont alignés si et seulement si $\\vec{AB}$ et $\\vec{AC}$ sont colinéaires, "
        "c'est-à-dire $x_{AB} y_{AC} - x_{AC} y_{AB} = 0$.",
        f"Étape 3 — $x_{{AB}} y_{{AC}} - x_{{AC}} y_{{AB}} = {xab} \\times {yac} - {xac} \\times {yab} = {det}$. {answer}",
    ]
    return {"enonce": enonce, "answer": answer, "steps": steps, "notion": NOTION_PRODUIT_SCALAIRE}


def _gen_angle_inverse(rng: random.Random) -> Optional[dict]:
    """Problème INVERSE : le produit scalaire et les normes sont donnés, il
    faut retrouver l'angle (structure différente de
    _gen_produit_norme_angle, qui va dans le sens direct)."""
    label, theta, c = rng.choice(_ANGLES_REMARQUABLES)
    n1, n2 = rng.randint(1, 6), rng.randint(1, 6)
    produit = sympy.simplify(n1 * n2 * c)
    enonce = (
        f"On donne deux vecteurs $\\vec{{u}}$ et $\\vec{{v}}$ tels que $\\|\\vec{{u}}\\| = {n1}$, "
        f"$\\|\\vec{{v}}\\| = {n2}$ et $\\vec{{u}} \\cdot \\vec{{v}} = {latex(produit)}$. "
        f"Déterminer une mesure de l'angle $\\left(\\vec{{u}},\\vec{{v}}\\right)$."
    )
    answer = f"$\\left(\\vec{{u}},\\vec{{v}}\\right) = {label}$"
    steps = [
        f"Étape 1 — $\\cos\\left(\\vec{{u}},\\vec{{v}}\\right) = \\dfrac{{\\vec{{u}} \\cdot \\vec{{v}}}}{{\\|\\vec{{u}}\\| \\times \\|\\vec{{v}}\\|}} "
        f"= \\dfrac{{{latex(produit)}}}{{{n1} \\times {n2}}} = {latex(sympy.simplify(produit / (n1 * n2)))}$.",
        f"Étape 2 — On reconnaît un cosinus remarquable : {answer}.",
    ]
    return {"enonce": enonce, "answer": answer, "steps": steps, "notion": NOTION_AUTRES}


def _gen_coordonnee_norme_donnee(rng: random.Random) -> Optional[dict]:
    """Retrouver une coordonnée connaissant la NORME (équation avec racine
    carrée), pas l'orthogonalité — structure différente de
    _gen_trouver_coordonnee_orthogonale."""
    x1 = _nz(rng, -6, 6)
    m_positif = rng.randint(1, 8)
    carre = x1 ** 2 + m_positif ** 2
    if int(sqrt(carre)) ** 2 != carre:
        return None
    norme_cible = int(sqrt(carre))
    enonce = (
        f"Dans un repère orthonormé, on donne $\\vec{{u}}\\begin{{pmatrix}} {x1} \\\\ m \\end{{pmatrix}}$, où $m > 0$. "
        f"Sachant que $\\|\\vec{{u}}\\| = {norme_cible}$, déterminer $m$."
    )
    answer = f"$m = {m_positif}$"
    steps = [
        f"Étape 1 — $\\|\\vec{{u}}\\|^2 = {x1}^2 + m^2$, donc ${norme_cible}^2 = {x1**2} + m^2$.",
        f"Étape 2 — $m^2 = {norme_cible**2} - {x1**2} = {m_positif**2}$, donc (avec $m>0$) $m = {m_positif}$.",
    ]
    return {"enonce": enonce, "answer": answer, "steps": steps, "notion": NOTION_PRODUIT_SCALAIRE}


EXTRA_FAMILY_BASE_SCORE: dict[str, float] = {
    "produit_points": 1.8,
    "norme_somme": 2.0,
    "coordonnee_norme_donnee": 2.4,
    "alignement_points": 2.8,
    "orthogonalite_triangle": 3.2,
    "angle_inverse": 3.6,
}

EXTRA_FAMILIES: tuple[Family, ...] = (
    Family("produit_points", 2, "Produit scalaire à partir de points", NOTION_PRODUIT_SCALAIRE,
           _gen_produit_points, "trois points dont on doit déduire les vecteurs",
           "calculer AB et AC à partir des coordonnées de A, B, C avant d'appliquer u·v"),
    Family("norme_somme", 2, "Norme d'une somme de vecteurs", NOTION_AUTRES, _gen_norme_somme,
           "deux vecteurs à additionner avant de calculer la norme", "additionner les coordonnées, puis appliquer √(x²+y²)"),
    Family("coordonnee_norme_donnee", 3, "Retrouver une coordonnée à partir de la norme", NOTION_PRODUIT_SCALAIRE,
           _gen_coordonnee_norme_donnee, "une coordonnée inconnue et une norme cible",
           "résoudre x²+m²=norme² d'inconnue m"),
    Family("alignement_points", 3, "Alignement de trois points", NOTION_PRODUIT_SCALAIRE, _gen_alignement_points,
           "trois points dont on teste l'alignement", "AB et AC colinéaires ⟺ A, B, C alignés"),
    Family("orthogonalite_triangle", 3, "Triangle rectangle via le produit scalaire", NOTION_PRODUIT_SCALAIRE,
           _gen_orthogonalite_triangle, "un triangle dont on teste l'angle droit en un sommet",
           "calculer AB et AC puis tester AB·AC=0"),
    Family("angle_inverse", 4, "Retrouver un angle connaissant le produit scalaire", NOTION_AUTRES,
           _gen_angle_inverse, "un produit scalaire et deux normes donnés",
           "cos(u,v) = u·v / (||u||×||v||), puis identifier l'angle remarquable"),
)

EXTRA_FAMILIES_BY_ID: dict[str, Family] = {f.id: f for f in EXTRA_FAMILIES}


def generate_extra_pool(per_family: int = 12, seed: int = 20260947) -> list[dict]:
    """Pool de diversification structurelle (mission 2026-09-02) — jamais
    mélangé à generate_pool()/FAMILIES (baseline figée). IDs à partir de
    GENERATED_ID_OFFSET + 8000."""
    rng = random.Random(seed)
    per_family_pool: dict[str, list[dict]] = {}
    for family in EXTRA_FAMILIES:
        seen_signatures = set()
        items = []
        attempts = 0
        while len(items) < per_family and attempts < per_family * 60:
            attempts += 1
            ex = _build_extra_exercise(family, rng)
            if ex is None:
                continue
            signature = (ex["family"], ex["enonce"])
            if signature in seen_signatures:
                continue
            seen_signatures.add(signature)
            items.append(ex)
        per_family_pool[family.id] = items

    pool: list[dict] = []
    idx = 0
    while any(per_family_pool.values()):
        family = EXTRA_FAMILIES[idx % len(EXTRA_FAMILIES)]
        bucket = per_family_pool.get(family.id) or []
        if bucket:
            pool.append(bucket.pop(0))
        idx += 1
        if idx > 200000:
            break
    offset = GENERATED_ID_OFFSET + 8000
    for i, ex in enumerate(pool):
        ex["id"] = offset + i
    return pool


def _build_extra_exercise(family: Family, rng: random.Random) -> Optional[dict]:
    notes = family.generate(rng)
    if notes is None:
        return None
    score = EXTRA_FAMILY_BASE_SCORE[family.id]
    real_level = _difficulty_bucket_from_score(score)
    return {
        "enonce": notes["enonce"],
        "answer": notes["answer"],
        "hint": f"Reconnais {family.structure_hint} : {family.rule_hint}.",
        "solution_steps": notes["steps"],
        "chapter_id": CHAPTER_ID,
        "notion": notes["notion"],
        "difficulty": real_level,
        "difficulty_label": LEVEL_META[real_level]["label"],
        "difficulty_emoji": LEVEL_META[real_level]["emoji"],
        "family": family.id,
        "family_label": family.label,
        "declared_level": family.level,
        "complexity_score": score,
        "source": "generated",
    }


FAMILY_BASE_SCORE: dict[str, float] = {
    "produit_coordonnees": 1.0,
    "norme": 1.4,
    "orthogonalite": 2.0,
    "colinearite": 2.2,
    "produit_norme_angle": 3.0,
    "trouver_coordonnee_orthogonale": 4.0,
}

FAMILIES: tuple[Family, ...] = (
    Family("produit_coordonnees", 1, "Produit scalaire à partir des coordonnées", NOTION_PRODUIT_SCALAIRE,
           _gen_produit_coordonnees, "deux vecteurs donnés par leurs coordonnées",
           "u·v = x_u x_v + y_u y_v"),
    Family("norme", 1, "Norme d'un vecteur", NOTION_AUTRES, _gen_norme,
           "un vecteur donné par ses coordonnées", "||u|| = √(x_u²+y_u²)"),
    Family("orthogonalite", 2, "Test d'orthogonalité", NOTION_PRODUIT_SCALAIRE, _gen_orthogonalite,
           "deux vecteurs dont on teste l'orthogonalité", "u⊥v ⟺ u·v=0"),
    Family("colinearite", 2, "Test de colinéarité", NOTION_PRODUIT_SCALAIRE, _gen_colinearite,
           "deux vecteurs dont on teste la colinéarité", "u,v colinéaires ⟺ x_u y_v - x_v y_u = 0"),
    Family("produit_norme_angle", 3, "Produit scalaire via normes et angle", NOTION_AUTRES,
           _gen_produit_norme_angle, "deux normes et un angle entre les vecteurs",
           "u·v = ||u|| ||v|| cos(u,v)"),
    Family("trouver_coordonnee_orthogonale", 4, "Retrouver une coordonnée inconnue", NOTION_PRODUIT_SCALAIRE,
           _gen_trouver_coordonnee_orthogonale, "une coordonnée inconnue à déterminer pour l'orthogonalité",
           "poser u·v=0 et résoudre l'équation obtenue"),
)

FAMILIES_BY_ID: dict[str, Family] = {f.id: f for f in FAMILIES}


def _difficulty_bucket_from_score(score: float) -> int:
    if score <= 1.2:
        return 1
    if score <= 2.1:
        return 2
    if score <= 2.6:
        return 3
    if score <= 3.5:
        return 4
    return 5


def build_exercise(family: Family, rng: random.Random) -> Optional[dict]:
    notes = family.generate(rng)
    if notes is None:
        return None
    score = FAMILY_BASE_SCORE[family.id]
    real_level = _difficulty_bucket_from_score(score)
    return {
        "enonce": notes["enonce"],
        "answer": notes["answer"],
        "hint": f"Reconnais {family.structure_hint} : {family.rule_hint}.",
        "solution_steps": notes["steps"],
        "chapter_id": CHAPTER_ID,
        "notion": notes["notion"],
        "difficulty": real_level,
        "difficulty_label": LEVEL_META[real_level]["label"],
        "difficulty_emoji": LEVEL_META[real_level]["emoji"],
        "family": family.id,
        "family_label": family.label,
        "declared_level": family.level,
        "complexity_score": score,
        "source": "generated",
    }


def generate_one(family_id: str, seed: Optional[int] = None, max_attempts: int = 25) -> dict:
    rng = random.Random(seed)
    fam = FAMILIES_BY_ID[family_id]
    for _ in range(max_attempts):
        ex = build_exercise(fam, rng)
        if ex is not None:
            return ex
    raise RuntimeError(f"Impossible de générer un exercice valide pour la famille {family_id!r}")


def generate_pool(per_family: int = 12, seed: int = 20260902) -> list[dict]:
    rng = random.Random(seed)
    per_family_pool: dict[str, list[dict]] = {}
    for family in FAMILIES:
        seen_signatures = set()
        items = []
        attempts = 0
        while len(items) < per_family and attempts < per_family * 60:
            attempts += 1
            ex = build_exercise(family, rng)
            if ex is None:
                continue
            signature = (ex["family"], ex["enonce"])
            if signature in seen_signatures:
                continue
            seen_signatures.add(signature)
            items.append(ex)
        per_family_pool[family.id] = items

    pool: list[dict] = []
    idx = 0
    while any(per_family_pool.values()):
        family = FAMILIES[idx % len(FAMILIES)]
        bucket = per_family_pool.get(family.id) or []
        if bucket:
            pool.append(bucket.pop(0))
        idx += 1
        if idx > 200000:
            break
    for i, ex in enumerate(pool):
        ex["id"] = GENERATED_ID_OFFSET + i
    return pool
