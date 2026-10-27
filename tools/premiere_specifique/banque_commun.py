"""Exercices curés de Première : modèle commun et contrôles.

Reprend le modèle de la Quatrième (quatrieme.banque_commun : E, S, écriture
des nombres) avec deux différences :
- identifiants : un chapitre repris garde les identifiants historiques de ses
  exercices (listés dans LEGACY_IDS du module) ; les nouveaux exercices sont
  dans le bloc 60 000 + 1 000 × chapitre + 100 × rang de la notion + k ;
- adaptation au manuel « Première ES/L » (2026-10-26) : tout identifiant de la
  banque d'avant l'adaptation (ids_avant_adaptation.py) reste valable quel que
  soit le nouveau numéro de son chapitre ; les exercices créés ensuite sont
  dans le bloc 80 000 + 1 000 × chapitre + 100 × rang + k. Un exercice retiré
  du curriculum actif est déplacé dans EXERCICES_HORS_PERIMETRE (jamais
  supprimé du module) : son identifiant peut alors quitter la banque servie ;
- chaque module banque_chNN.py peut fournir `verify` (recalcul SymPy ou
  Fraction) pour CHAQUE exercice paramétré : une valeur annoncée qui ne se
  recalcule pas fait échouer l'écriture.
"""
from fractions import Fraction
from math import isqrt

from premiere_specifique.ids_avant_adaptation import IDS_AVANT_ADAPTATION
from quatrieme.banque_commun import E, S, frac, num  # noqa: F401  (réexportés)

ID_BASE = 80_000


def check_chapter(module) -> list[str]:
    problems = []
    ch = module.CHAPTER_NUMBER
    exercises = module.EXERCISES
    notions = list(module.NOTIONS)
    retires = {e.id for e in getattr(module, "EXERCICES_HORS_PERIMETRE", ())}
    legacy = set(getattr(module, "LEGACY_IDS", ())) - retires
    if retires & {e.id for e in exercises}:
        problems.append(f"exercices à la fois servis et hors périmètre : {sorted(retires & {e.id for e in exercises})[:10]}")
    if len(module.NOTION_IDS) != len(notions):
        problems.append("NOTION_IDS et NOTIONS de longueurs différentes")
    ids = [e.id for e in exercises]
    if len(ids) != len(set(ids)):
        problems.append("identifiants dupliqués")
    if legacy - set(ids):
        problems.append(f"identifiants historiques perdus : {sorted(legacy - set(ids))[:10]}")
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
        if e.id not in legacy and e.id not in IDS_AVANT_ADAPTATION and not (low < e.id < low + 100):
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
            for bad in ("+ -", "- -", "+ +", "(x - -", "+0$", "+ 0$", "-1(", " 1(x"):
                if bad in text:
                    problems.append(f"{p} : écriture fautive {bad!r} dans {name}")
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


# ── Écriture des expressions (LaTeX) ─────────────────────────────────────────


def fr(q) -> str:
    q = Fraction(q)
    return frac(q)


def coef(a, mono) -> str:
    """Premier terme « a·mono » : 1 et -1 implicites."""
    a = Fraction(a)
    if a == 1:
        return mono
    if a == -1:
        return "-" + mono
    return fr(a) + mono


def poly_tex(coefs, var="x") -> str:
    """Polynôme (coefficients du plus haut degré au terme constant)."""
    n = len(coefs) - 1
    out = ""
    for i, c in enumerate(coefs):
        c = Fraction(c)
        if c == 0:
            continue
        deg = n - i
        mono = f"{var}^{deg}" if deg > 1 else (var if deg == 1 else "")
        mag = abs(c)
        body = (fr(mag) if (mag != 1 or not mono) else "") + mono
        if not out:
            out = ("-" if c < 0 else "") + body
        else:
            out += (" - " if c < 0 else " + ") + body
    return out or "0"


def tri(a, b, c, var="x") -> str:
    return poly_tex([a, b, c], var)


def lin(r, var="x") -> str:
    """x − r écrit proprement : « x - 3 », « x + 2 », « x »."""
    r = Fraction(r)
    if r == 0:
        return var
    return f"{var} - {fr(r)}" if r > 0 else f"{var} + {fr(-r)}"


def factored(a, roots, var="x") -> str:
    """a(x − x1)(x − x2) ; un facteur « x » seul s'écrit sans parenthèses en tête."""
    a = Fraction(a)
    lead = "" if a == 1 else ("-" if a == -1 else fr(a))
    if len(roots) == 2 and roots[0] == roots[1]:
        return f"{lead}({lin(roots[0], var)})^2"
    # Racine nulle : le facteur « x » s'écrit en tête, sans parenthèses (x(x - 3)).
    roots = sorted(roots, key=lambda r: Fraction(r) != 0)
    out = lead
    for r in roots:
        f = lin(r, var)
        out += f if f == var else f"({f})"
    return out


def sq(q) -> str:
    """Carré d'un rationnel écrit avec sa valeur absolue : (3/2)², 4²."""
    q = abs(Fraction(q))
    return f"\\left({fr(q)}\\right)^2" if q.denominator != 1 else f"{q}^2"


def canonical(a, alpha, beta, var="x") -> str:
    a, alpha, beta = Fraction(a), Fraction(alpha), Fraction(beta)
    lead = "" if a == 1 else ("-" if a == -1 else fr(a))
    if alpha == 0:
        square = f"{var}^2"
    elif alpha.denominator == 1:
        square = f"({lin(alpha, var)})^2"
    else:
        square = f"\\left({lin(alpha, var)}\\right)^2"
    out = lead + square
    if beta:
        out += (" - " if beta < 0 else " + ") + fr(abs(beta))
    return out


def par(q) -> str:
    s = fr(q)
    return f"({s})" if Fraction(q) < 0 else s


def pw(q) -> str:
    """Base d'une puissance : entre parenthèses si négative ou fractionnaire."""
    q = Fraction(q)
    if q.denominator != 1:
        return f"\\left({fr(q)}\\right)"
    return f"({q})" if q < 0 else str(q)


def ratio(n, d) -> str:
    """« \\dfrac{n}{d} = valeur », sans l'égalité si la fraction est déjà irréductible."""
    raw = f"\\dfrac{{{n}}}{{{d}}}"
    val = fr(Fraction(n, d))
    return raw if (val == raw and d > 0) else f"{raw} = {val}"


def sqrt_parts(n: int):
    """n = k² · m avec m sans facteur carré."""
    k, m = 1, n
    d = 2
    while d * d <= m:
        while m % (d * d) == 0:
            m //= d * d
            k *= d
        d += 1
    return k, m


def roots_tex(a, b, c):
    """Racines de ax² + bx + c (coefficients entiers) en LaTeX exact :
    (liste de chaînes, liste de valeurs float), dans l'ordre croissant."""
    a, b, c = int(a), int(b), int(c)
    d = b * b - 4 * a * c
    if d < 0:
        return [], []
    r = isqrt(d)
    if r * r == d:
        vals = sorted({Fraction(-b - r, 2 * a), Fraction(-b + r, 2 * a)})
        return [fr(v) for v in vals], [float(v) for v in vals]
    k, m = sqrt_parts(d)
    p, q, den = -b, k, 2 * a
    if den < 0:
        p, den = -p, -den
    from math import gcd
    g = gcd(gcd(abs(p), q), den)
    p, q, den = p // g, q // g, den // g
    rad = f"\\sqrt{{{m}}}" if q == 1 else f"{q}\\sqrt{{{m}}}"
    lo = (p - q * m ** 0.5) / den
    hi = (p + q * m ** 0.5) / den
    if den == 1:
        texts = [f"{p} - {rad}" if p else f"-{rad}", f"{p} + {rad}" if p else rad]
    else:
        texts = [f"\\dfrac{{{p} - {rad}}}{{{den}}}" if p else f"-\\dfrac{{{rad}}}{{{den}}}",
                 f"\\dfrac{{{p} + {rad}}}{{{den}}}" if p else f"\\dfrac{{{rad}}}{{{den}}}"]
    return texts, [lo, hi]


def code(s: str) -> str:
    """Code Python affiché tel quel : balise <code> (ignorée par KaTeX) et
    caractères que la mise en forme automatique du texte réécrirait
    (mathrender.js::prettify : 2*u → 2u, 1/2 → 1 ÷ 2, x^2 → exposant)
    encodés en entités HTML."""
    for c, ent in (("&", "&amp;"), ("*", "&#42;"), ("/", "&#47;"), ("^", "&#94;"), ("<", "&lt;"), (">", "&gt;")):
        s = s.replace(c, ent)
    return f"<code>{s}</code>"
