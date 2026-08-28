"""Génération symbolique d'exercices sur les équations du premier degré
(Troisième, Chapitre_5, notion "Résoudre une équation du premier degré").

Profil identique à "Équations du second degré" en Première
(`webapp/exercise_generator/second_degre.py`, patron de référence) : un
diagnostic (87% calcul direct, 67% gabarits) très proche justifie le même
traitement adapté au premier degré — reconnaître le nombre de solutions
selon le coefficient, retrouver une équation à partir de sa solution,
vérifier une résolution, corriger une erreur classique (mauvaise inversion
de signe), comparer deux méthodes. Toute solution annoncée est calculée par
sympy — jamais tapée "en dur" sans contrôle.
"""
import random
from dataclasses import dataclass
from typing import Callable, Optional

from sympy import Eq, Rational, latex, solve, symbols

x = symbols("x")

CHAPTER_ID = "Chapitre_5"
NOTION = "Résoudre une équation du premier degré"

GENERATED_ID_OFFSET = 100_000

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


def _small(rng: random.Random, lo=-12, hi=12) -> int:
    return rng.randint(lo, hi)


def _fmt_ax_b(a, b) -> str:
    """Rend $ax+b$ (ou $ax-b$) en LaTeX avec des signes propres."""
    a_str = "" if a == 1 else ("-" if a == -1 else str(a))
    term = f"{a_str}x"
    if b == 0:
        return term
    return f"{term} {'+' if b > 0 else '-'} {abs(b)}"


def _solve_ax_b_eq_c(a, b, c):
    """Résout ax+b=c par sympy.solve — seule source de vérité."""
    sols = solve(Eq(a * x + b, c), x)
    return sols[0] if sols else None


# ── 1. Résolution directe ax+b=c ─────────────────────────────────────────────

def _gen_resolution_simple(rng):
    a = _nz(rng, -9, 9)
    b = _small(rng, -15, 15)
    c = _small(rng, -15, 15)
    sol = _solve_ax_b_eq_c(a, b, c)
    if sol is None:
        return None
    enonce = f"Résoudre l'équation ${_fmt_ax_b(a, b)} = {c}$."
    steps = [
        f"Étape 1 — On isole le terme en $x$ : ${a}x = {c} {'-' if b >= 0 else '+'} {abs(b)} = {c - b}$.",
        f"Étape 2 — On divise par ${a}$ : $x = \\dfrac{{{c - b}}}{{{a}}} = {latex(sol)}$.",
    ]
    answer = f"$x = {latex(sol)}$"
    hint = "Isoler le terme en x d'un côté, la constante de l'autre, puis diviser par le coefficient de x."
    return {"enonce": enonce, "answer": answer, "steps": steps, "hint": hint}


# ── 1bis. Résolution nécessitant de développer d'abord : k(ax+b) = c ────────
# Mécanique réellement différente : une étape de distributivité est
# obligatoire avant de pouvoir isoler x — pas un simple ax+b=c déguisé.

def _gen_resolution_parentheses(rng):
    k = _nz(rng, 2, 6)
    a = _nz(rng, -5, 5)
    b = _small(rng, -8, 8)
    c = _small(rng, -20, 20)
    dev_a, dev_b = k * a, k * b
    sol = _solve_ax_b_eq_c(dev_a, dev_b, c)
    if sol is None:
        return None
    inner = _fmt_ax_b(a, b)
    enonce = f"Résoudre l'équation ${k}({inner}) = {c}$."
    steps = [
        f"Étape 1 — On développe d'abord le membre de gauche : ${k}({inner}) = {_fmt_ax_b(dev_a, dev_b)}$.",
        f"Étape 2 — On isole le terme en $x$ : ${dev_a}x = {c} {'-' if dev_b >= 0 else '+'} {abs(dev_b)} = {c - dev_b}$.",
        f"Étape 3 — On divise par ${dev_a}$ : $x = {latex(sol)}$.",
    ]
    answer = f"$x = {latex(sol)}$"
    hint = "Développer entièrement le membre de gauche avant de chercher à isoler x."
    return {"enonce": enonce, "answer": answer, "steps": steps, "hint": hint}


# ── 1ter. Inconnue des deux côtés : ax+b = cx+d ──────────────────────────────
# Mécanique encore différente : il faut regrouper les termes en x d'un même
# côté avant de pouvoir isoler x, alors que ax+b=c ne demande qu'une seule
# opération de ce type.

def _gen_resolution_deux_cotes(rng):
    a = _nz(rng, -8, 8)
    c = _nz(rng, -8, 8)
    if a == c:
        return None  # (a-c)x = ... dégénère si a=c
    b = _small(rng, -12, 12)
    d = _small(rng, -12, 12)
    sol = solve(Eq(a * x + b, c * x + d), x)
    if not sol:
        return None
    sol = sol[0]
    enonce = f"Résoudre l'équation ${_fmt_ax_b(a, b)} = {_fmt_ax_b(c, d)}$."
    diff_a = a - c
    diff_d = d - b
    steps = [
        f"Étape 1 — On regroupe les termes en $x$ à gauche et les constantes à droite : "
        f"${a}x {'-' if c >= 0 else '+'} {abs(c)}x = {d} {'-' if b >= 0 else '+'} {abs(b)}$.",
        f"Étape 2 — Cela donne ${diff_a}x = {diff_d}$.",
        f"Étape 3 — On divise par ${diff_a}$ : $x = {latex(sol)}$.",
    ]
    answer = f"$x = {latex(sol)}$"
    hint = "Regrouper d'abord tous les termes en x d'un même côté de l'égalité, avant d'isoler x."
    return {"enonce": enonce, "answer": answer, "steps": steps, "hint": hint}


def _gen_resolution(rng):
    return rng.choice([
        _gen_resolution_simple, _gen_resolution_simple,  # forme de base majoritaire (50%)
        _gen_resolution_parentheses,
        _gen_resolution_deux_cotes,
    ])(rng)


# ── 2. Nombre de solutions selon le coefficient (a=0 : aucune / infinité) ───

def _gen_nombre_solutions(rng):
    kind = rng.choice(["une_solution", "aucune_solution", "infinite_solutions"])
    if kind == "une_solution":
        a = _nz(rng, -8, 8)
        b = _small(rng, -10, 10)
        c = _small(rng, -10, 10)
        sol = _solve_ax_b_eq_c(a, b, c)
        if sol is None:
            return None
        enonce = (
            f"L'équation ${_fmt_ax_b(a, b)} = {c}$ admet-elle une solution unique, aucune solution, "
            "ou une infinité de solutions ? Justifier sans nécessairement calculer la solution."
        )
        answer = f"Une solution unique (le coefficient de $x$, ${a}$, est non nul), $x = {latex(sol)}$."
        steps = [
            f"Étape 1 — Le coefficient de $x$ vaut ${a} \\neq 0$ : l'équation se ramène à $x = \\dots$, "
            "elle admet donc exactement une solution.",
            f"Étape 2 — On la calcule : $x = \\dfrac{{{c - b}}}{{{a}}} = {latex(sol)}$.",
        ]
    elif kind == "aucune_solution":
        b = _small(rng, -10, 10)
        c = b
        while c == b:
            c = _small(rng, -10, 10)
        # 0x + b = c avec b != c : aucune solution
        enonce = f"L'équation ${_fmt_ax_b(0, b).replace('0x ', '').strip() or str(b)} = {c}$, où le terme en $x$ a un coefficient nul, admet-elle une solution ?"
        # Reformulation propre : on écrit explicitement 0x+b=c pour que ce soit lisible.
        enonce = f"L'équation $0x {'+' if b >= 0 else '-'} {abs(b)} = {c}$ admet-elle une solution ? Justifier."
        answer = f"Aucune solution : l'équation équivaut à ${b} = {c}$, ce qui est faux quel que soit $x$."
        steps = [
            "Étape 1 — Le coefficient de $x$ est nul : $x$ disparaît de l'équation.",
            f"Étape 2 — Il reste ${b} = {c}$, une égalité fausse : aucune valeur de $x$ ne peut convenir.",
        ]
    else:
        b = _small(rng, -10, 10)
        c = b
        enonce = f"L'équation $0x {'+' if b >= 0 else '-'} {abs(b)} = {c}$ admet-elle une solution ? Justifier."
        answer = f"Une infinité de solutions : l'équation équivaut à ${b} = {c}$, qui est toujours vraie."
        steps = [
            "Étape 1 — Le coefficient de $x$ est nul : $x$ disparaît de l'équation.",
            f"Étape 2 — Il reste ${b} = {c}$, une égalité toujours vraie : tout réel $x$ convient.",
        ]
    hint = "Regarder d'abord le coefficient de x : s'il est non nul l'équation a une solution unique ; s'il est nul, tout dépend de l'égalité restante entre les constantes."
    return {"enonce": enonce, "answer": answer, "steps": steps, "hint": hint}


# ── 3. Retrouver une équation à partir de sa solution ───────────────────────

def _gen_equation_depuis_solution(rng):
    x0 = Rational(_small(rng, -9, 9), rng.choice([1, 1, 1, 2, 3]))
    a = _nz(rng, -8, 8)
    b = _small(rng, -12, 12)
    c = a * x0 + b
    if c != int(c) and rng.random() < 0.5:
        return None  # on préfère majoritairement un second membre entier, pas systématique
    check = _solve_ax_b_eq_c(a, b, c)
    if check != x0:
        return None
    enonce = (
        f"Déterminer un nombre entier $c$ tel que l'équation ${_fmt_ax_b(a, b)} = c$ ait pour solution "
        f"$x = {latex(x0)}$."
    ) if c == int(c) else (
        f"Vérifier que $x = {latex(x0)}$ est bien solution de l'équation ${_fmt_ax_b(a, b)} = {latex(c)}$."
    )
    steps = [
        f"Étape 1 — On remplace $x$ par ${latex(x0)}$ dans le membre de gauche : "
        f"${a}\\times{latex(x0)} {'+' if b >= 0 else '-'} {abs(b)} = {latex(c)}$.",
        f"Étape 2 — Le second membre doit donc valoir ${latex(c)}$ pour que ${latex(x0)}$ soit solution.",
    ]
    answer = f"$c = {latex(c)}$" if c == int(c) else f"Oui : les deux membres valent bien ${latex(c)}$."
    hint = "Substituer la solution donnée dans le membre de gauche pour retrouver la valeur manquante."
    return {"enonce": enonce, "answer": answer, "steps": steps, "hint": hint}


# ── 4. Vérifier une résolution proposée (vrai/faux justifié) ───────────────

def _gen_verifier_resolution(rng):
    a = _nz(rng, -9, 9)
    b = _small(rng, -12, 12)
    c = _small(rng, -12, 12)
    sol = _solve_ax_b_eq_c(a, b, c)
    if sol is None:
        return None
    is_correct = rng.random() < 0.5
    proposed = sol if is_correct else sol + rng.choice([1, -1, 2, -2])
    enonce = (
        f"Un élève affirme que $x = {latex(proposed)}$ est solution de l'équation "
        f"${_fmt_ax_b(a, b)} = {c}$. A-t-il raison ? Justifier."
    )
    if is_correct:
        answer = f"Vrai : en remplaçant, on retrouve bien ${c}$ dans les deux membres."
        steps = [
            f"Étape 1 — On substitue $x={latex(proposed)}$ dans ${_fmt_ax_b(a, b)}$ : "
            f"on obtient ${c}$, qui correspond au second membre.",
            "Étape 2 — L'affirmation de l'élève est donc correcte.",
        ]
    else:
        computed = a * proposed + b
        answer = f"Faux : en remplaçant, on obtient ${latex(computed)}$, pas ${c}$. La solution correcte est $x={latex(sol)}$."
        steps = [
            f"Étape 1 — On substitue $x={latex(proposed)}$ dans ${_fmt_ax_b(a, b)}$ : "
            f"on obtient ${latex(computed)} \\neq {c}$.",
            f"Étape 2 — La proposition est donc fausse ; en résolvant réellement l'équation, $x = {latex(sol)}$.",
        ]
    hint = "Ne jamais faire confiance à une solution annoncée sans la vérifier par substitution directe."
    return {"enonce": enonce, "answer": answer, "steps": steps, "hint": hint}


# ── 5. Détecter et corriger une erreur (inversion de signe classique) ───────

def _gen_corriger_erreur(rng):
    a = _nz(rng, -9, 9)
    b = _small(rng, -12, 12)
    c = _small(rng, -12, 12)
    sol = _solve_ax_b_eq_c(a, b, c)
    if sol is None or b == 0:
        return None
    # Erreur classique : l'élève "passe" b de l'autre côté SANS changer de signe.
    wrong = Rational(c + b, a)
    if wrong == sol:
        return None
    enonce = (
        f"Un élève résout ${_fmt_ax_b(a, b)} = {c}$ ainsi : "
        f"\"${a}x = {c} {'+' if b >= 0 else '-'} {abs(b)}$, donc $x = {latex(wrong)}$\" "
        "(il n'a pas changé le signe du terme constant en le faisant passer de l'autre côté). "
        "Identifier son erreur et donner la résolution correcte."
    )
    steps = [
        f"Étape 1 — Pour isoler ${a}x$, il faut soustraire ${b}$ aux deux membres, pas l'ajouter : "
        f"${a}x = {c} {'-' if b >= 0 else '+'} {abs(b)} = {c - b}$.",
        f"Étape 2 — L'élève a changé le signe de $b$ dans le mauvais sens : il fallait "
        f"${c} {'-' if b >= 0 else '+'} {abs(b)}$, pas ${c} {'+' if b >= 0 else '-'} {abs(b)}$.",
        f"Étape 3 — La solution correcte est $x = \\dfrac{{{c - b}}}{{{a}}} = {latex(sol)}$.",
    ]
    answer = f"Erreur de signe en isolant le terme en $x$ ; la solution correcte est $x = {latex(sol)}$."
    hint = "Quand un terme change de membre dans une égalité, il change de signe — vérifier ce point en premier."
    return {"enonce": enonce, "answer": answer, "steps": steps, "hint": hint}


# ── 6. Comparer deux méthodes de résolution ──────────────────────────────────

def _gen_comparer_methodes(rng):
    a = rng.choice([2, 3, 4, 5, -2, -3, -4])
    x0 = _small(rng, -8, 8)
    b = _small(rng, -10, 10)
    c = a * x0 + b
    check = _solve_ax_b_eq_c(a, b, c)
    if check != x0:
        return None
    enonce = (
        f"On considère l'équation ${_fmt_ax_b(a, b)} = {c}$. "
        "Inès la résout en isolant d'abord le terme en $x$ puis en divisant par le coefficient ; "
        "Yanis multiplie d'abord les deux membres par un nombre pour éliminer les éventuelles fractions. "
        "Mener la méthode d'Inès et vérifier le résultat."
    )
    steps = [
        f"Méthode d'Inès — On isole le terme en $x$ : ${a}x = {c} {'-' if b >= 0 else '+'} {abs(b)} = {c - b}$, "
        f"puis on divise par ${a}$ : $x = {latex(Rational(c - b, a))}$.",
        f"Vérification — On substitue $x={latex(Rational(c - b, a))}$ dans l'équation de départ : "
        f"on retrouve bien ${c}$ dans les deux membres, donc les deux méthodes mèneraient au même résultat.",
    ]
    answer = f"$x = {latex(Rational(c - b, a))}$"
    hint = "Les deux méthodes (isoler puis diviser, ou multiplier pour éliminer les fractions) doivent conduire exactement à la même solution."
    return {"enonce": enonce, "answer": answer, "steps": steps, "hint": hint}


@dataclass(frozen=True)
class Family:
    id: str
    level: int
    label: str
    generate: Callable[[random.Random], Optional[dict]]
    structure_hint: str
    rule_hint: str


FAMILY_BASE_SCORE: dict[str, float] = {
    "resolution": 1.0,
    "nombre_solutions": 2.0,
    "verifier_resolution": 2.3,
    "equation_depuis_solution": 3.0,
    "comparer_methodes": 3.3,
    "corriger_erreur": 4.0,
}

FAMILIES: tuple[Family, ...] = (
    Family("resolution", 1, "Résolution directe (ax+b=c, avec parenthèses, ou inconnue des deux côtés)", _gen_resolution,
           "une équation du premier degré à résoudre, sous une forme simple, à développer, ou avec x des deux côtés",
           "isoler x, en développant ou en regroupant les termes en x si nécessaire, puis diviser par son coefficient"),
    Family("nombre_solutions", 2, "Nombre de solutions selon le coefficient", _gen_nombre_solutions,
           "une équation dont le coefficient de x peut être nul", "un coefficient de x nul change la nature du problème"),
    Family("verifier_resolution", 2, "Vérifier une résolution proposée", _gen_verifier_resolution,
           "une solution proposée, correcte ou non", "substituer avant de juger"),
    Family("equation_depuis_solution", 3, "Retrouver une équation depuis sa solution", _gen_equation_depuis_solution,
           "une solution imposée", "substituer la solution pour retrouver le paramètre manquant"),
    Family("comparer_methodes", 3, "Comparer deux méthodes de résolution", _gen_comparer_methodes,
           "une équation résoluble de plusieurs façons", "isoler puis diviser, ou multiplier pour éliminer des fractions"),
    Family("corriger_erreur", 4, "Détecter et corriger une erreur", _gen_corriger_erreur,
           "une résolution contenant une erreur classique de signe", "comparer chaque étape à la méthode correcte"),
)

FAMILIES_BY_ID = {f.id: f for f in FAMILIES}


def _difficulty_bucket_from_score(score: float) -> int:
    if score <= 1.5:
        return 1
    if score <= 2.6:
        return 2
    if score <= 3.6:
        return 3
    return 4


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
        "notion": NOTION,
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


def generate_pool(per_family: int = 6, seed: int = 30260101) -> list[dict]:
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
