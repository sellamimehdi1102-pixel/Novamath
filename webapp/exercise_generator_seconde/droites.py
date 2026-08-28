"""Génération symbolique d'exercices sur les droites du plan (Seconde,
Chapitre_6), couvrant les 4 notions ciblées par le chantier de
diversification de type (voir docstring du package) : "Vecteur directeur
d'une droite", "Equation réduite d'une droite", "Positions relatives de deux
droites", "Equation cartésienne d'une droite".

Ces notions avaient déjà un gabarit textuel élevé (peu de quasi-doublons,
voir tools/check_exercise_diversity.py) : ce module n'ajoute donc PAS de
variations numériques d'un même type déjà bien couvert, seulement des types
de raisonnement absents (vrai/faux justifié, erreur à corriger, exercice
inversé, choix de méthode, comparaison, contexte léger) — voir
tools/audit_exercise_taxonomy.py pour le diagnostic initial.

Chaque famille est rattachée à UNE SEULE notion (`Family.notion`), toutes
les 4 notions restant dans `Chapitre_6`. Toute valeur annoncée (déterminant,
pente, ordonnée à l'origine, point d'intersection...) est recalculée par
sympy pour garantir la justesse indépendamment du texte de l'énoncé.
"""
import random
from dataclasses import dataclass
from typing import Callable, Optional

from sympy import Eq, Matrix, Rational, solve, symbols

x_sym, y_sym, m_sym = symbols("x y m")

CHAPTER_ID = "Chapitre_6"
NOTION_VECTEUR = "Vecteur directeur d'une droite"
NOTION_EQ_REDUITE = "Equation réduite d'une droite"
NOTION_POSITIONS = "Positions relatives de deux droites"
NOTION_EQ_CART = "Equation cartésienne d'une droite"

# Distinct de exercises_generated_premiere.json (900_000+) et du module
# frère signes.py (810_000) — voir tools/generate_seconde_exercises.py qui
# liste tous les offsets et garantit l'absence de collision d'id.
GENERATED_ID_OFFSET = 800_000

LEVEL_META = {
    1: {"emoji": "🟢", "label": "Niveau 1 — Fondamental"},
    2: {"emoji": "🟡", "label": "Niveau 2 — Intermédiaire"},
    3: {"emoji": "🟠", "label": "Niveau 3 — Avancé"},
    4: {"emoji": "🔴", "label": "Niveau 4 — Difficile"},
    5: {"emoji": "🟣", "label": "Niveau 5 — Défi"},
}


def _nz(rng: random.Random, lo: int, hi: int) -> int:
    choices = [n for n in range(lo, hi + 1) if n != 0]
    return rng.choice(choices)


def _small(rng: random.Random, lo=-9, hi=9) -> int:
    return rng.randint(lo, hi)


def _fmt_num(r) -> str:
    r = Rational(r)
    if r.q == 1:
        return str(r.p)
    return f"{r.p}/{r.q}"


def _disp(n) -> str:
    """Affiche un nombre en le parenthésant s'il est négatif — évite les
    doubles signes ambigus ("− -3" ou "×-7") dans les formules affichées."""
    s = _fmt_num(n) if hasattr(n, "q") else str(n)
    return f"({s})" if s.startswith("-") else s


def _fmt_affine(a, b, var="x") -> str:
    """Formate a*var + b façon "2x + 4" / "(2/3)x - 1" (style déjà utilisé
    dans exercises_bank.json — voir scan des exemples existants)."""
    a = Rational(a)
    if a == 1:
        head = var
    elif a == -1:
        head = f"-{var}"
    else:
        a_s = _fmt_num(a)
        head = f"({a_s}){var}" if a.q != 1 else f"{a_s}{var}"
    b = Rational(b)
    if b == 0:
        return head
    b_s = _fmt_num(abs(b))
    return f"{head} {'+' if b > 0 else '-'} {b_s}"


def _fmt_cart(p: int, q: int, r: int) -> str:
    parts = [f"{'' if p == 1 else ('-' if p == -1 else p)}x"]
    if q != 0:
        q_coeff = "" if abs(q) == 1 else abs(q)
        parts.append(f"{'+' if q > 0 else '-'} {q_coeff}y")
    if r != 0:
        parts.append(f"{'+' if r > 0 else '-'} {abs(r)}")
    return " ".join(parts) + " = 0"


def _det(vx, vy, wx, wy):
    return Matrix([[vx, vy], [wx, wy]]).det()


# ═════════════════════ Notion : Vecteur directeur d'une droite ═════════════

def _gen_vecteur_vrai_faux(rng):
    p, q = _nz(rng, -6, 6), _nz(rng, -6, 6)
    is_true = rng.random() < 0.5
    if is_true:
        k = rng.choice([-3, -2, 2, 3])
        cand = (k * p, k * q)
    else:
        for _ in range(50):
            cx, cy = _small(rng, -8, 8), _small(rng, -8, 8)
            if (cx, cy) != (0, 0) and _det(p, q, cx, cy) != 0:
                cand = (cx, cy)
                break
        else:
            return None
    det = _det(p, q, cand[0], cand[1])
    colin = det == 0
    enonce = (
        f"Vrai ou faux : la droite D a pour vecteur directeur $\\vec{{d}}$ = ({p}, {q}) ; le vecteur "
        f"$\\vec{{u}}$ = ({cand[0]}, {cand[1]}) est aussi un vecteur directeur de D. Justifier."
    )
    steps = [
        "Deux vecteurs dirigent la même droite si et seulement si ils sont colinéaires, "
        "c'est-à-dire si leur déterminant est nul.",
        f"det($\\vec{{d}}$, $\\vec{{u}}$) = {p}×{_disp(cand[1])} − {_disp(q)}×{_disp(cand[0])} = {det}.",
        f"Comme det = {det} {'= 0' if colin else '≠ 0'}, les deux vecteurs sont "
        f"{'colinéaires' if colin else 'non colinéaires'}.",
    ]
    est_ou_pas = "est" if colin else "n'est pas"
    answer = (
        f"{'Vrai' if colin else 'Faux'} : $\\vec{{u}}$ "
        f"{est_ou_pas} un vecteur directeur de D "
        f"(déterminant {'nul' if colin else 'non nul'})."
    )
    hint = "Deux vecteurs dirigent la même droite si et seulement si ils sont colinéaires (déterminant nul)."
    return {"enonce": enonce, "answer": answer, "steps": steps, "hint": hint}


def _gen_vecteur_erreur_normal(rng):
    p, q = _nz(rng, -6, 6), _nz(rng, -6, 6)
    r = _small(rng, -8, 8)
    correct = (-q, p)
    verif_det = _det(p, q, correct[0], correct[1])
    enonce = (
        f"La droite D a pour équation cartésienne {_fmt_cart(p, q, r)}. Un élève affirme que "
        f"$\\vec{{u}}$ = ({p}, {q}) est un vecteur directeur de D. A-t-il raison ? Sinon, donner "
        "un vecteur directeur correct."
    )
    steps = [
        f"Pour une droite d'équation ax + by + c = 0, le vecteur ({p}, {q}) = (a, b) est le vecteur "
        "NORMAL de la droite, pas un vecteur directeur.",
        f"Un vecteur directeur s'obtient en échangeant les coordonnées et en changeant un signe : "
        f"$\\vec{{d}}$ = (-b, a) = ({correct[0]}, {correct[1]}).",
        f"Vérification : det(({p},{q}), ({correct[0]},{correct[1]})) = "
        f"{p}×{_disp(correct[1])} − {_disp(q)}×{_disp(correct[0])} = {verif_det} ≠ 0 : le vecteur "
        "normal (a,b) proposé par l'élève et le vrai vecteur directeur (-b,a) ne sont PAS colinéaires "
        "(ils sont même perpendiculaires) — ce qui confirme que (a,b) n'est pas un vecteur directeur de D.",
    ]
    answer = (
        f"Faux : ({p}, {q}) est le vecteur NORMAL de D, pas un vecteur directeur. Un vecteur "
        f"directeur correct est ({correct[0]}, {correct[1]})."
    )
    hint = "Pour ax + by + c = 0, le vecteur normal est (a, b) et un vecteur directeur est (-b, a) — ne pas confondre les deux."
    return {"enonce": enonce, "answer": answer, "steps": steps, "hint": hint}


def _gen_vecteur_inverse(rng):
    a = _nz(rng, -5, 5)
    b = _small(rng, -6, 6)
    q0 = _nz(rng, -6, 6)
    m_val = solve(Eq(1 * q0 - a * m_sym, 0), m_sym)
    if not m_val:
        return None
    m_val = m_val[0]
    enonce = (
        f"La droite D a pour équation réduite y = {_fmt_affine(a, b)}. Pour quelle valeur du réel m "
        f"le vecteur $\\vec{{u}}$ = (m, {q0}) est-il un vecteur directeur de D ?"
    )
    steps = [
        f"Un vecteur directeur de D (équation y = ax + b) est $\\vec{{d}}$ = (1, {a}).",
        f"$\\vec{{u}}$ est directeur de D ssi $\\vec{{u}}$ est colinéaire à $\\vec{{d}}$, donc si "
        f"det($\\vec{{d}}$, $\\vec{{u}}$) = 1×{_disp(q0)} − {_disp(a)}×m = 0.",
        f"On résout {q0} − {_disp(a)}m = 0, soit m = {_fmt_num(m_val)}.",
    ]
    answer = f"m = {_fmt_num(m_val)}"
    hint = "Le vecteur directeur naturel de y = ax + b est (1, a) : écrire que u est colinéaire à ce vecteur."
    return {"enonce": enonce, "answer": answer, "steps": steps, "hint": hint}


def _gen_vecteur_contexte(rng):
    x0, y0 = _small(rng, -6, 6), _small(rng, -6, 6)
    vx, vy = _nz(rng, -5, 5), _nz(rng, -5, 5)
    enonce = (
        f"Un point mobile se déplace en ligne droite à vitesse constante. A l'instant t = 0 s, il se "
        f"trouve au point A({x0}, {y0}) (coordonnées en mètres). Son vecteur vitesse est "
        f"$\\vec{{v}}$ = ({vx}, {vy}) m/s. Donner un vecteur directeur de sa trajectoire, puis exprimer "
        "sa position M(t) en fonction de t."
    )
    steps = [
        "Un mobile se déplaçant en ligne droite à vitesse constante suit une trajectoire rectiligne dont "
        "le vecteur vitesse est justement un vecteur directeur.",
        f"Vecteur directeur de la trajectoire : $\\vec{{v}}$ = ({vx}, {vy}).",
        f"Position à l'instant t : M(t) = A + t·$\\vec{{v}}$ = ({x0} + {vx}t, {y0} + {vy}t).",
    ]
    answer = f"Vecteur directeur : ({vx}, {vy}). Position : M(t) = ({x0} + {vx}t ; {y0} + {vy}t)."
    hint = "Le vecteur vitesse (constant) d'un mouvement rectiligne est un vecteur directeur de la trajectoire."
    return {"enonce": enonce, "answer": answer, "steps": steps, "hint": hint}


# ═════════════════════ Notion : Equation réduite d'une droite ══════════════

def _gen_eq_reduite_erreur(rng):
    a = _nz(rng, -6, 6)
    b = _nz(rng, -5, 5)
    c = _small(rng, -10, 10)
    correct_slope = Rational(-a, b)
    correct_intercept = Rational(-c, b)
    wrong_slope = Rational(a, b)
    wrong_intercept = Rational(c, b)
    if (wrong_slope, wrong_intercept) == (correct_slope, correct_intercept):
        return None
    enonce = (
        f"Un élève transforme l'équation {a}x + {b}y + {c} = 0 sous forme réduite et obtient "
        f"y = {_fmt_affine(wrong_slope, wrong_intercept)}. A-t-il raison ? Sinon, donner la bonne "
        "équation réduite."
    )
    steps = [
        f"On isole y : {b}y = -{a}x - {c}.",
        f"On divise par {b} : y = ({-a}/{b})x + ({-c}/{b}) = {_fmt_affine(correct_slope, correct_intercept)}.",
        "L'élève a oublié de changer le signe de a et de c en les faisant passer de l'autre côté de "
        "l'égalité.",
    ]
    answer = f"Faux : la bonne équation réduite est y = {_fmt_affine(correct_slope, correct_intercept)}."
    hint = "Isoler y : by = -ax - c, donc y = (-a/b)x - c/b — le signe change en passant a et c de l'autre côté."
    return {"enonce": enonce, "answer": answer, "steps": steps, "hint": hint}


def _gen_eq_reduite_vf(rng):
    a = _nz(rng, -6, 6)
    b = _small(rng, -8, 8)
    x0 = _small(rng, -8, 8)
    true_y = a * x0 + b
    is_true = rng.random() < 0.5
    y_test = true_y if is_true else true_y + rng.choice([1, -1, 2, -2, 3])
    enonce = (
        f"Vrai ou faux : la droite D a pour équation y = {_fmt_affine(a, b)} ; le point M({x0}, {y_test}) "
        "appartient à D. Justifier."
    )
    steps = [
        f"On remplace x par {x0} dans l'équation de D : y = {a}×{_disp(x0)} + {b} = {true_y}.",
        f"Le point de D d'abscisse {x0} a pour ordonnée {true_y}, "
        f"{'ce qui correspond' if is_true else 'à comparer'} à l'ordonnée {y_test} de M.",
    ]
    if is_true:
        answer = f"Vrai : M({x0}, {y_test}) appartient à D, car {a}×{_disp(x0)}+{b} = {y_test}."
    else:
        answer = f"Faux : M({x0}, {y_test}) n'appartient pas à D, car {a}×{_disp(x0)}+{b} = {true_y} ≠ {y_test}."
    hint = "Un point (x0, y0) appartient à D : y = ax+b si et seulement si y0 = a×x0 + b."
    return {"enonce": enonce, "answer": answer, "steps": steps, "hint": hint}


def _gen_eq_reduite_inverse(rng):
    a = _nz(rng, -5, 5)
    b = _small(rng, -6, 6)
    cx, cy = _small(rng, -6, 6), _small(rng, -6, 6)
    perpendicular = rng.random() < 0.5
    if perpendicular:
        slope = Rational(-1, a)
        relation = "perpendiculaire"
    else:
        offset = rng.choice([n for n in range(-4, 5) if n != 0])
        slope = Rational(a)
        relation = "parallèle"
        b = b + offset if b + offset != b else b  # évite D' = D (garde b différent, cosmétique)
    intercept = Rational(cy) - slope * Rational(cx)
    enonce = (
        f"Déterminer D' sachant que D' est {relation} à la droite D d'équation y = {_fmt_affine(a, b)} "
        f"et passe par le point C({cx}, {cy}). Donner l'équation réduite de D'."
    )
    steps = (
        [
            "Deux droites perpendiculaires ont des coefficients directeurs dont le produit vaut -1 : "
            f"le coefficient directeur de D' est donc -1/{a} = {_fmt_num(slope)}.",
        ]
        if perpendicular
        else [
            f"Deux droites parallèles ont le même coefficient directeur : celui de D' est donc {a}.",
        ]
    ) + [
        f"D' : y = {_fmt_num(slope)}x + p. Comme C({cx},{cy}) ∈ D' : {cy} = {_fmt_num(slope)}×{_disp(cx)} + p, "
        f"donc p = {_fmt_num(intercept)}.",
        f"Equation de D' : y = {_fmt_affine(slope, intercept)}.",
    ]
    answer = f"y = {_fmt_affine(slope, intercept)}"
    hint = "Parallèle : même coefficient directeur. Perpendiculaire : produit des coefficients directeurs = -1. Puis utiliser le point C pour trouver p."
    return {"enonce": enonce, "answer": answer, "steps": steps, "hint": hint}


def _gen_eq_reduite_choix_methode(rng):
    ax, ay = _small(rng, -6, 6), _small(rng, -6, 6)
    bx = ax + _nz(rng, -6, 6)
    if bx == ax:
        return None
    by = ay + _nz(rng, -8, 8)
    slope = Rational(by - ay, bx - ax)
    intercept = Rational(ay) - slope * Rational(ax)
    enonce = (
        f"Deux méthodes permettent de déterminer l'équation réduite de la droite D passant par "
        f"A({ax}, {ay}) et B({bx}, {by}) : calculer d'abord le coefficient directeur puis utiliser un "
        "point, ou résoudre un système de deux équations à deux inconnues (a et b). Quelle méthode est "
        "la plus directe ici, sachant qu'on connaît deux points ? Appliquez-la."
    )
    steps = [
        "Comme on connaît deux points (et non un point + une contrainte de pente), la méthode "
        "'coefficient directeur puis point' est la plus directe — le système à deux inconnues donnerait "
        "le même résultat mais demande plus de calcul.",
        f"Coefficient directeur : a = (yB-yA)/(xB-xA) = ({by}-{_disp(ay)})/({bx}-{_disp(ax)}) = {_fmt_num(slope)}.",
        f"Avec A({ax},{ay}) : {ay} = {_fmt_num(slope)}×{_disp(ax)} + b, donc b = {_fmt_num(intercept)}.",
        f"Equation réduite : y = {_fmt_affine(slope, intercept)}.",
    ]
    answer = f"Méthode la plus directe : coefficient directeur puis point. y = {_fmt_affine(slope, intercept)}"
    hint = "Avec deux points donnés, calculer la pente a = (yB-yA)/(xB-xA) est plus rapide que résoudre un système."
    return {"enonce": enonce, "answer": answer, "steps": steps, "hint": hint}


def _gen_eq_reduite_comparaison(rng):
    a1 = _nz(rng, -6, 6)
    b1 = _small(rng, -6, 6)
    a2 = _nz(rng, -6, 6)
    while a2 == a1:
        a2 = _nz(rng, -6, 6)
    b2 = _small(rng, -6, 6)
    plus_grand = "D1" if a1 > a2 else "D2"
    enonce = (
        f"Comparer les droites D1 : y = {_fmt_affine(a1, b1)} et D2 : y = {_fmt_affine(a2, b2)}. "
        "Quel est le plus grand coefficient directeur, et que peut-on en déduire sur l'inclinaison des "
        "deux droites ?"
    )
    steps = [
        f"Coefficient directeur de D1 : {a1}. Coefficient directeur de D2 : {a2}.",
        f"{a1} {'>' if a1 > a2 else '<'} {a2}, donc {plus_grand} a le plus grand coefficient directeur.",
        f"Plus le coefficient directeur est grand (en valeur), plus la droite est pentue : {plus_grand} "
        "est donc la plus pentue des deux (en valeur absolue de la pente, à comparer si les signes diffèrent).",
    ]
    answer = f"Le plus grand coefficient directeur est celui de {plus_grand} ({max(a1, a2)})."
    hint = "Comparer directement les deux coefficients directeurs a1 et a2 : le plus grand correspond à la droite qui 'monte' le plus vite."
    return {"enonce": enonce, "answer": answer, "steps": steps, "hint": hint}


# ═════════════════════ Notion : Positions relatives de deux droites ════════

def _gen_positions_vf(rng):
    a1 = _nz(rng, -6, 6)
    b1 = _small(rng, -6, 6)
    is_parallel = rng.random() < 0.5
    if is_parallel:
        a2 = a1
        b2 = b1 + _nz(rng, -5, 5)
    else:
        a2 = _nz(rng, -6, 6)
        while a2 == a1:
            a2 = _nz(rng, -6, 6)
        b2 = _small(rng, -6, 6)
    enonce = (
        f"Vrai ou faux : les droites D1 : y = {_fmt_affine(a1, b1)} et D2 : y = {_fmt_affine(a2, b2)} "
        "sont parallèles."
    )
    steps = [
        f"Deux droites y=ax+b sont parallèles si et seulement si elles ont le même coefficient directeur.",
        f"Coefficient directeur de D1 : {a1}. Coefficient directeur de D2 : {a2}.",
        f"{a1} {'=' if a1 == a2 else '≠'} {a2}, donc D1 et D2 {'sont' if a1 == a2 else 'ne sont pas'} parallèles.",
    ]
    answer = f"{'Vrai' if a1 == a2 else 'Faux'} : D1 et D2 {'sont' if a1 == a2 else 'ne sont pas'} parallèles."
    hint = "Comparer les coefficients directeurs : égaux → parallèles (ou confondues), différents → sécantes."
    return {"enonce": enonce, "answer": answer, "steps": steps, "hint": hint}


def _gen_positions_erreur(rng):
    a1 = _nz(rng, -5, 5)
    b1 = _small(rng, -6, 6)
    a2 = _nz(rng, -5, 5)
    while a2 == a1:
        a2 = _nz(rng, -5, 5)
    b2 = _small(rng, -6, 6)
    sol = solve([Eq(y_sym, a1 * x_sym + b1), Eq(y_sym, a2 * x_sym + b2)], [x_sym, y_sym])
    x_true, y_true = sol[x_sym], sol[y_sym]
    wrong_point = (x_true + rng.choice([1, -1, 2]), y_true)
    if wrong_point == (x_true, y_true):
        return None
    enonce = (
        f"Un élève cherche le point d'intersection de D1 : y = {_fmt_affine(a1, b1)} et "
        f"D2 : y = {_fmt_affine(a2, b2)}, et trouve le point ({_fmt_num(wrong_point[0])}, "
        f"{_fmt_num(wrong_point[1])}). Vérifier ce résultat et corriger si besoin."
    )
    steps = [
        f"Vérification sur D1 : y = {a1}×{_disp(wrong_point[0])} + {b1} = "
        f"{_fmt_num(a1 * wrong_point[0] + b1)}, à comparer à {_fmt_num(wrong_point[1])}.",
        f"Résolution correcte du système : {a1}x+{b1} = {a2}x+{b2}, donc "
        f"({a1}-{_disp(a2)})x = {b2}-{_disp(b1)}, x = {_fmt_num(x_true)}.",
        f"y = {a1}×{_disp(x_true)}+{b1} = {_fmt_num(y_true)}.",
    ]
    answer = f"Le point proposé est incorrect. Le vrai point d'intersection est ({_fmt_num(x_true)}, {_fmt_num(y_true)})."
    hint = "Recalculer soi-même le système en égalant les deux expressions de y, plutôt que de faire confiance au résultat proposé."
    return {"enonce": enonce, "answer": answer, "steps": steps, "hint": hint}


def _gen_positions_inverse(rng):
    a2 = _nz(rng, -6, 6)
    b1 = _small(rng, -6, 6)
    b2 = _small(rng, -6, 6)
    relation = rng.choice(["parallèles", "perpendiculaires"])
    if relation == "parallèles":
        target = solve(Eq(m_sym, a2), m_sym)[0]
    else:
        target = solve(Eq(m_sym * a2, -1), m_sym)[0]
    enonce = (
        f"Déterminer la valeur de m sachant que les droites D1 : y = mx + {b1} et "
        f"D2 : y = {_fmt_affine(a2, b2)} sont {relation}."
    )
    if relation == "parallèles":
        steps = [
            "Deux droites sont parallèles ssi elles ont le même coefficient directeur.",
            f"Il faut donc m = {a2}.",
        ]
    else:
        steps = [
            "Deux droites sont perpendiculaires ssi le produit de leurs coefficients directeurs vaut -1.",
            f"Il faut donc m × {a2} = -1, soit m = {_fmt_num(target)}.",
        ]
    answer = f"m = {_fmt_num(target)}"
    hint = "Parallèles : mêmes coefficients directeurs. Perpendiculaires : produit des coefficients directeurs égal à -1."
    return {"enonce": enonce, "answer": answer, "steps": steps, "hint": hint}


def _gen_positions_comparaison(rng):
    a1 = _nz(rng, -5, 5)
    b1 = _small(rng, -6, 6)
    a2 = a1  # D1 et D2 volontairement parallèles
    b2 = b1 + _nz(rng, -5, 5)
    a3 = _nz(rng, -5, 5)
    while a3 == a1:
        a3 = _nz(rng, -5, 5)
    b3 = _small(rng, -6, 6)
    enonce = (
        f"Comparer deux à deux les droites D1 : y = {_fmt_affine(a1, b1)}, D2 : y = {_fmt_affine(a2, b2)} "
        f"et D3 : y = {_fmt_affine(a3, b3)}. Lesquelles sont parallèles entre elles ?"
    )
    steps = [
        f"Coefficients directeurs : D1 → {a1}, D2 → {a2}, D3 → {a3}.",
        f"D1 et D2 ont le même coefficient directeur ({a1} = {a2}) : elles sont parallèles.",
        f"D3 a un coefficient directeur différent ({a3}) : elle n'est parallèle ni à D1 ni à D2.",
    ]
    answer = "D1 et D2 sont parallèles entre elles ; D3 n'est parallèle à aucune des deux."
    hint = "Comparer les coefficients directeurs deux à deux : égaux → parallèles."
    return {"enonce": enonce, "answer": answer, "steps": steps, "hint": hint}


def _gen_positions_contexte(rng):
    a1 = _nz(rng, -4, 4)
    b1 = _small(rng, 0, 10)
    a2 = _nz(rng, -4, 4)
    while a2 == a1:
        a2 = _nz(rng, -4, 4)
    b2 = _small(rng, 0, 10)
    sol = solve([Eq(y_sym, a1 * x_sym + b1), Eq(y_sym, a2 * x_sym + b2)], [x_sym, y_sym])
    enonce = (
        "Deux voitures roulent sur des routes rectilignes modélisées, dans un repère (en kilomètres), "
        f"par D1 : y = {_fmt_affine(a1, b1)} et D2 : y = {_fmt_affine(a2, b2)}. Ces deux routes se "
        "croisent-elles ? Si oui, en quel point ?"
    )
    steps = [
        f"Les routes se croisent si les droites sont sécantes, c'est-à-dire si {a1} ≠ {a2} (coefficients "
        "directeurs différents), ce qui est le cas ici.",
        f"On résout {a1}x+{b1} = {a2}x+{b2} : x = {_fmt_num(sol[x_sym])}.",
        f"y = {a1}×{_disp(sol[x_sym])}+{b1} = {_fmt_num(sol[y_sym])}.",
    ]
    answer = f"Oui, les routes se croisent au point ({_fmt_num(sol[x_sym])}, {_fmt_num(sol[y_sym])})."
    hint = "Deux routes rectilignes se croisent ssi les droites qui les modélisent sont sécantes (coefficients directeurs différents)."
    return {"enonce": enonce, "answer": answer, "steps": steps, "hint": hint}


# ═════════════════════ Notion : Equation cartésienne d'une droite ══════════

def _gen_eq_cart_vf(rng):
    p, q = _nz(rng, -6, 6), _nz(rng, -6, 6)
    r = _small(rng, -8, 8)
    x0 = _small(rng, -6, 6)
    true_y = solve(Eq(p * x0 + q * y_sym + r, 0), y_sym)
    if not true_y:
        return None
    true_y = true_y[0]
    is_true = rng.random() < 0.5
    y_test = true_y if is_true else true_y + rng.choice([1, -1, 2])
    lhs = p * x0 + q * y_test + r
    enonce = (
        f"Vrai ou faux : la droite D a pour équation cartésienne {_fmt_cart(p, q, r)} ; le point M({x0}, "
        f"{_fmt_num(y_test)}) appartient à D. Justifier."
    )
    steps = [
        f"On remplace x et y par {x0} et {_fmt_num(y_test)} dans l'équation : "
        f"{p}×{_disp(x0)} + {q}×{_disp(y_test)} + {r} = {lhs}.",
        f"Ce résultat est {'nul' if lhs == 0 else 'non nul'}, donc M {'vérifie' if lhs == 0 else 'ne vérifie pas'} "
        "l'équation de D.",
    ]
    appartient_ou_pas = "appartient" if lhs == 0 else "n'appartient pas"
    answer = f"{'Vrai' if lhs == 0 else 'Faux'} : M {appartient_ou_pas} à D."
    hint = "Un point appartient à une droite d'équation cartésienne px+qy+r=0 si et seulement s'il vérifie l'équation (résultat nul)."
    return {"enonce": enonce, "answer": answer, "steps": steps, "hint": hint}


def _gen_eq_cart_erreur(rng):
    ax, ay = _small(rng, -6, 6), _small(rng, -6, 6)
    bx = ax + _nz(rng, -6, 6)
    if bx == ax:
        return None
    by = ay + _nz(rng, -6, 6)
    ux, uy = bx - ax, by - ay
    normal = (-uy, ux)
    wrong_c = -(ux * ax + uy * ay)
    correct_c = -(normal[0] * ax + normal[1] * ay)
    enonce = (
        f"Pour trouver l'équation cartésienne de la droite D passant par A({ax}, {ay}) et "
        f"B({bx}, {by}), un élève calcule $\\vec{{AB}}$ = ({ux}, {uy}) et l'utilise directement comme "
        f"vecteur normal, obtenant {_fmt_cart(ux, uy, wrong_c)}. Identifier son erreur et donner "
        "l'équation correcte."
    )
    steps = [
        f"$\\vec{{AB}}$ = ({ux}, {uy}) est un vecteur DIRECTEUR de D, pas un vecteur normal — l'élève a "
        "confondu les deux.",
        f"Le vecteur normal s'obtient à partir du vecteur directeur (u,v) par (-v, u) : ici "
        f"({normal[0]}, {normal[1]}).",
        f"Equation : {normal[0]}x + {normal[1]}y + c = 0, avec A({ax},{ay}) : "
        f"{normal[0]}×{_disp(ax)} + {normal[1]}×{_disp(ay)} + c = 0, donc c = {correct_c}.",
        f"Equation correcte : {_fmt_cart(normal[0], normal[1], correct_c)}.",
    ]
    answer = f"Erreur : AB est un vecteur directeur, pas normal. Equation correcte : {_fmt_cart(normal[0], normal[1], correct_c)}"
    hint = "Le vecteur (AB) est directeur, pas normal — le vecteur normal (a,b) d'une équation cartésienne ax+by+c=0 est perpendiculaire au vecteur directeur."
    return {"enonce": enonce, "answer": answer, "steps": steps, "hint": hint}


def _gen_eq_cart_inverse(rng):
    p, q = _nz(rng, -6, 6), _nz(rng, -6, 6)
    r0 = _small(rng, -8, 8)
    ax, ay = _small(rng, -6, 6), _small(rng, -6, 6)
    new_c = -(p * ax + q * ay)
    enonce = (
        f"Déterminer D sachant que D est parallèle à la droite Δ d'équation {_fmt_cart(p, q, r0)} "
        f"et passe par le point A({ax}, {ay}). Donner l'équation cartésienne de D."
    )
    steps = [
        f"Deux droites parallèles ont le même vecteur normal (à un facteur près) : celui de D est donc "
        f"({p}, {q}), comme pour Δ.",
        f"Equation de D : {p}x + {q}y + c = 0. Avec A({ax},{ay}) : {p}×{_disp(ax)} + {q}×{_disp(ay)} + c = 0, "
        f"donc c = {new_c}.",
        f"Equation de D : {_fmt_cart(p, q, new_c)}.",
    ]
    answer = _fmt_cart(p, q, new_c)
    hint = "Deux droites parallèles ont le même vecteur normal (a,b) — seul le c change, à déterminer avec le point donné."
    return {"enonce": enonce, "answer": answer, "steps": steps, "hint": hint}


def _gen_eq_cart_choix_methode(rng):
    ax, ay = _small(rng, -6, 6), _small(rng, -6, 6)
    ux, uy = _nz(rng, -6, 6), _nz(rng, -6, 6)
    normal = (-uy, ux)
    c = -(normal[0] * ax + normal[1] * ay)
    enonce = (
        f"On connaît un point A({ax}, {ay}) de la droite D et un vecteur directeur "
        f"$\\vec{{d}}$ = ({ux}, {uy}) de D. Deux méthodes existent pour écrire une équation cartésienne "
        "de D : passer par l'équation réduite d'abord, ou construire directement le vecteur normal à "
        "partir du vecteur directeur. Quelle méthode est la plus directe ici, sachant que le vecteur "
        "directeur est déjà donné ? Appliquez-la."
    )
    steps = [
        "Le vecteur directeur étant déjà connu, la méthode la plus directe consiste à en déduire "
        "immédiatement le vecteur normal, sans passer par l'équation réduite (qui échouerait de plus "
        "si ux = 0, cas d'une droite verticale).",
        f"Vecteur normal : (-v, u) = ({normal[0]}, {normal[1]}).",
        f"Equation : {normal[0]}x + {normal[1]}y + c = 0. Avec A({ax},{ay}) : c = {c}.",
        f"Equation cartésienne de D : {_fmt_cart(normal[0], normal[1], c)}.",
    ]
    answer = f"Méthode la plus directe : déduire le vecteur normal du vecteur directeur. {_fmt_cart(normal[0], normal[1], c)}"
    hint = "Quand un vecteur directeur (u,v) est déjà connu, le vecteur normal (-v,u) s'en déduit directement — inutile de passer par l'équation réduite."
    return {"enonce": enonce, "answer": answer, "steps": steps, "hint": hint}


@dataclass(frozen=True)
class Family:
    id: str
    level: int
    notion: str
    label: str
    generate: Callable[[random.Random], Optional[dict]]
    structure_hint: str
    rule_hint: str


FAMILY_BASE_SCORE: dict[str, float] = {
    "vecteur_vrai_faux": 1.5,
    "vecteur_erreur_normal": 3.5,
    "vecteur_inverse": 3.0,
    "vecteur_contexte": 2.5,
    "eq_reduite_vf": 1.5,
    "eq_reduite_erreur": 3.3,
    "eq_reduite_inverse": 3.8,
    "eq_reduite_choix_methode": 3.0,
    "eq_reduite_comparaison": 2.0,
    "positions_vf": 1.3,
    "positions_erreur": 3.5,
    "positions_inverse": 3.3,
    "positions_comparaison": 2.7,
    "positions_contexte": 3.0,
    "eq_cart_vf": 1.8,
    "eq_cart_erreur": 4.0,
    "eq_cart_inverse": 3.5,
    "eq_cart_choix_methode": 4.3,
}

FAMILIES: tuple[Family, ...] = (
    Family("vecteur_vrai_faux", 1, NOTION_VECTEUR, "Vrai/faux : colinéarité de deux vecteurs",
           _gen_vecteur_vrai_faux, "un vecteur candidat à comparer au vecteur directeur donné",
           "colinéarité <=> déterminant nul"),
    Family("vecteur_erreur_normal", 4, NOTION_VECTEUR, "Erreur à corriger : confusion normal/directeur",
           _gen_vecteur_erreur_normal, "une confusion entre vecteur normal et vecteur directeur",
           "pour ax+by+c=0, normal=(a,b), directeur=(-b,a)"),
    Family("vecteur_inverse", 3, NOTION_VECTEUR, "Exercice inversé : retrouver une coordonnée",
           _gen_vecteur_inverse, "une coordonnée inconnue d'un vecteur directeur",
           "colinéarité avec le vecteur directeur naturel (1,a)"),
    Family("vecteur_contexte", 3, NOTION_VECTEUR, "Problème contextualisé (trajectoire rectiligne)",
           _gen_vecteur_contexte, "un mobile en mouvement rectiligne uniforme",
           "le vecteur vitesse est un vecteur directeur de la trajectoire"),
    Family("eq_reduite_vf", 1, NOTION_EQ_REDUITE, "Vrai/faux : appartenance d'un point",
           _gen_eq_reduite_vf, "un point à tester dans une équation réduite",
           "substituer x et comparer à y"),
    Family("eq_reduite_erreur", 4, NOTION_EQ_REDUITE, "Erreur à corriger : signe lors de l'isolement de y",
           _gen_eq_reduite_erreur, "une isolation de y avec erreur de signe",
           "by = -ax - c, donc y = (-a/b)x - c/b"),
    Family("eq_reduite_inverse", 4, NOTION_EQ_REDUITE, "Exercice inversé : parallèle ou perpendiculaire",
           _gen_eq_reduite_inverse, "une droite définie par une relation (parallèle/perpendiculaire) à une autre",
           "utiliser la relation entre coefficients directeurs puis le point donné"),
    Family("eq_reduite_choix_methode", 3, NOTION_EQ_REDUITE, "Choix de méthode : deux points",
           _gen_eq_reduite_choix_methode, "deux points connus, deux méthodes possibles",
           "pente puis point est la méthode la plus directe"),
    Family("eq_reduite_comparaison", 2, NOTION_EQ_REDUITE, "Comparaison de deux coefficients directeurs",
           _gen_eq_reduite_comparaison, "deux droites à comparer", "comparer directement a1 et a2"),
    Family("positions_vf", 1, NOTION_POSITIONS, "Vrai/faux : parallélisme", _gen_positions_vf,
           "deux droites, une affirmation de parallélisme", "comparer les coefficients directeurs"),
    Family("positions_erreur", 4, NOTION_POSITIONS, "Erreur à corriger : intersection",
           _gen_positions_erreur, "un point d'intersection proposé", "recalculer le système soi-même"),
    Family("positions_inverse", 3, NOTION_POSITIONS, "Exercice inversé : retrouver un paramètre",
           _gen_positions_inverse, "un paramètre inconnu m et une relation de position donnée",
           "parallèles: m=a2 ; perpendiculaires: m×a2=-1"),
    Family("positions_comparaison", 2, NOTION_POSITIONS, "Comparaison de trois droites",
           _gen_positions_comparaison, "trois droites à comparer deux à deux",
           "comparer les coefficients directeurs deux à deux"),
    Family("positions_contexte", 3, NOTION_POSITIONS, "Problème contextualisé (routes rectilignes)",
           _gen_positions_contexte, "deux trajectoires modélisées par des droites",
           "sécantes <=> coefficients directeurs différents"),
    Family("eq_cart_vf", 2, NOTION_EQ_CART, "Vrai/faux : appartenance d'un point",
           _gen_eq_cart_vf, "un point à tester dans une équation cartésienne",
           "substituer x et y, résultat nul <=> appartenance"),
    Family("eq_cart_erreur", 4, NOTION_EQ_CART, "Erreur à corriger : confusion directeur/normal",
           _gen_eq_cart_erreur, "un vecteur directeur utilisé à tort comme normal",
           "le normal (-v,u) se déduit du directeur (u,v)"),
    Family("eq_cart_inverse", 4, NOTION_EQ_CART, "Exercice inversé : droite parallèle donnée",
           _gen_eq_cart_inverse, "une droite définie comme parallèle à une autre, passant par un point",
           "même vecteur normal, c à déterminer avec le point"),
    Family("eq_cart_choix_methode", 5, NOTION_EQ_CART, "Choix de méthode : vecteur directeur déjà connu",
           _gen_eq_cart_choix_methode, "un point et un vecteur directeur déjà donnés",
           "déduire directement le normal du directeur"),
)

FAMILIES_BY_ID = {f.id: f for f in FAMILIES}


def _difficulty_bucket_from_score(score: float) -> int:
    if score <= 1.6:
        return 1
    if score <= 2.6:
        return 2
    if score <= 3.4:
        return 3
    if score <= 4.1:
        return 4
    return 5


def build_exercise(family: Family, rng: random.Random) -> Optional[dict]:
    notes = family.generate(rng)
    if notes is None:
        return None
    score = FAMILY_BASE_SCORE[family.id]
    real_level = _difficulty_bucket_from_score(score)
    hint = notes.get("hint") or f"Reconnais {family.structure_hint} : {family.rule_hint}."
    return {
        "enonce": notes["enonce"],
        "answer": notes["answer"],
        "hint": hint,
        "solution_steps": notes["steps"],
        "chapter_id": CHAPTER_ID,
        "notion": family.notion,
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


def generate_pool(per_family: int = 7, seed: int = 20260830) -> list[dict]:
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
