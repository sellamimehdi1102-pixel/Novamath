"""Exercices curés de Quatrième : modèle commun, écriture des nombres et
contrôles recalculés.

Chaque module banque_chNN.py déclare :
    CHAPTER_NUMBER, NOTION_IDS (ordre du cours), NOTIONS (titres, même ordre),
    EXERCISES (liste de E), QUIZ ({notion_id: (id, id, id)}).

Identifiants : 40 000 + 1 000 × chapitre + 100 × rang de la notion + k
(même règle que le chapitre pilote ; plage 41 000 – 57 999 libre dans toutes
les autres banques). Ils sont écrits en dur, jamais positionnels.

Contrôles (`check_chapter`) : chaque valeur annoncée par un exercice est
recalculée par Python au moment de l'écriture du module — `checks` (chaînes
qui doivent figurer dans la réponse), `step_checks` (dans la correction),
`verify` (fonction libre qui renvoie un message d'erreur ou None).
"""
from dataclasses import dataclass, field
from decimal import ROUND_HALF_UP, Decimal
from fractions import Fraction
from math import gcd
from typing import Callable, Optional

ID_BASE = 40_000


@dataclass(frozen=True)
class E:
    id: int
    notion: str
    difficulty: int
    enonce: str
    answer: str
    hint: str
    steps: tuple
    checks: tuple = ()
    step_checks: tuple = ()
    verify: Optional[Callable[[], Optional[str]]] = field(default=None, compare=False)

    def to_json(self, chapter_number: int) -> dict:
        return {
            "id": self.id,
            "chapter_id": f"Chapitre_{chapter_number}",
            "notion": self.notion,
            "difficulty": self.difficulty,
            "enonce": self.enonce,
            "answer": self.answer,
            "hint": self.hint,
            "solution_steps": list(self.steps),
        }


def S(*steps):
    """Numérote les étapes de correction (« Étape n — ... »), comme les
    exercices générés."""
    return tuple(f"Étape {i} — {s}" for i, s in enumerate(steps, 1))


# ── Écriture française des nombres (LaTeX) ──────────────────────────────────


def D(x) -> Decimal:
    return x if isinstance(x, Decimal) else Decimal(str(x))


def num(x) -> str:
    """Décimal exact -> « 2{,}5 », « -3 », « 12 » (sans zéros inutiles)."""
    if isinstance(x, Fraction):
        assert is_decimal(x), f"{x} n'est pas décimal"
        x = Decimal(x.numerator) / Decimal(x.denominator)
    d = D(x).normalize()
    s = format(d, "f")
    if "." in s:
        s = s.rstrip("0").rstrip(".")
    if s in ("-0", ""):
        s = "0"
    return s.replace(".", "{,}")


def rnd(x, decimals: int) -> str:
    q = Decimal(1).scaleb(-decimals)
    v = D(x) if not isinstance(x, Fraction) else Decimal(x.numerator) / Decimal(x.denominator)
    return num(v.quantize(q, rounding=ROUND_HALF_UP)) if decimals else num(v.quantize(Decimal(1), rounding=ROUND_HALF_UP))


def is_decimal(f: Fraction) -> bool:
    q = f.denominator
    for p in (2, 5):
        while q % p == 0:
            q //= p
    return q == 1


def frac(f, display=True) -> str:
    """Fraction irréductible en LaTeX : « \\dfrac{3}{4} », « -\\dfrac{3}{4} »,
    entier si le dénominateur vaut 1."""
    f = Fraction(f)
    if f.denominator == 1:
        return str(f.numerator)
    sign = "-" if f < 0 else ""
    cmd = "\\dfrac" if display else "\\frac"
    return f"{sign}{cmd}{{{abs(f.numerator)}}}{{{f.denominator}}}"


def F(n, d=1) -> Fraction:
    return Fraction(n, d)


def irreducible(n: int, d: int) -> bool:
    return gcd(n, d) == 1


def par(x) -> str:
    """Nombre relatif entre parenthèses s'il est négatif : (-3)."""
    s = num(x) if not isinstance(x, str) else x
    return f"({s})" if s.startswith("-") else s


def prime_factors(n: int) -> list[int]:
    out, p = [], 2
    while p * p <= n:
        while n % p == 0:
            out.append(p)
            n //= p
        p += 1
    if n > 1:
        out.append(n)
    return out


def is_prime(n: int) -> bool:
    return n >= 2 and prime_factors(n) == [n]


# ── Contrôles ──────────────────────────────────────────────────────────────


def check_chapter(module) -> list[str]:
    """Rejoue tous les contrôles d'un module banque_chNN ; liste vide = OK."""
    problems = []
    ch = module.CHAPTER_NUMBER
    exercises = module.EXERCISES
    notions = list(module.NOTIONS)
    if len(module.NOTION_IDS) != len(notions):
        problems.append("NOTION_IDS et NOTIONS de longueurs différentes")
    ids = [e.id for e in exercises]
    if len(ids) != len(set(ids)):
        problems.append("identifiants dupliqués")
    enonces = [e.enonce for e in exercises]
    if len(enonces) != len(set(enonces)):
        problems.append("énoncés dupliqués")
    for e in exercises:
        p = f"exercice {e.id}"
        if e.notion not in notions:
            problems.append(f"{p} : notion inconnue {e.notion!r}")
            continue
        k = notions.index(e.notion) + 1
        low = ID_BASE + 1000 * ch + 100 * k
        if not (low < e.id < low + 100):
            problems.append(f"{p} : identifiant hors du bloc {low + 1}-{low + 99} de sa notion")
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
        if e.verify is not None:
            msg = e.verify()
            if msg:
                problems.append(f"{p} : {msg}")
        for name, text in (("enonce", e.enonce), ("answer", e.answer), ("hint", e.hint),
                           *((f"steps[{i}]", s) for i, s in enumerate(e.steps))):
            if text.count("$") % 2:
                problems.append(f"{p} : nombre impair de « $ » dans {name}")
            if text.count("{") != text.count("}"):
                problems.append(f"{p} : accolades déséquilibrées dans {name}")
        if e.hint.strip() in e.answer:
            problems.append(f"{p} : l'indice révèle la réponse")
    by_id = {e.id: e for e in exercises}
    if set(module.QUIZ) != set(module.NOTION_IDS):
        problems.append("QUIZ ne couvre pas exactement les notions du chapitre")
    for notion_id, quiz in module.QUIZ.items():
        if len(quiz) != 3 or len(set(quiz)) != 3:
            problems.append(f"quiz {notion_id} : 3 exercices distincts attendus")
        title = notions[list(module.NOTION_IDS).index(notion_id)] if notion_id in module.NOTION_IDS else None
        for q in quiz:
            if q not in by_id or by_id[q].difficulty > 2 or by_id[q].notion != title:
                problems.append(f"quiz {notion_id} : {q} absent, d'une autre notion ou trop difficile")
    return problems


def build_chapter(module) -> list[dict]:
    return [e.to_json(module.CHAPTER_NUMBER) for e in sorted(module.EXERCISES, key=lambda e: e.id)]
