"""Chapitre 5 — Puissances (générateurs).

    calculer_puissance    N1  a^n (base entière, négative avec ou sans parenthèses, décimale)
    ecrire_puissance      N1  produit de facteurs égaux -> puissance
    puissance10_decimal   N2  10^n -> écriture décimale (n de -6 à 7)
    produit_puissances10  N2  (10^a × 10^b) / 10^c -> 10^n
    vers_scientifique     N3  décimal -> écriture scientifique
    depuis_scientifique   N3  écriture scientifique -> décimal
    comparer_scientifique N3  comparer deux nombres en écriture scientifique
    conversion_prefixe    N4  conversion entre préfixes (nano à giga)
"""
import random
from decimal import Decimal
from typing import Optional

from ._commun import Chapter, Family, num

N1 = "Puissances d'un nombre"
N2 = "Puissances de 10"
N3 = "Écriture scientifique d'un nombre"
N4 = "Préfixes, ordres de grandeur et comparaisons"

_PREFIXES = (("G", "giga", 9), ("M", "méga", 6), ("k", "kilo", 3), ("", "", 0),
             ("m", "milli", -3), ("µ", "micro", -6), ("n", "nano", -9))
# Préfixes réellement employés avec chaque unité.
_UNITES = {"m": ("k", "", "m", "µ", "n"), "g": ("k", "", "m", "µ"),
           "W": ("G", "M", "k", "", "m"), "o": ("G", "M", "k", ""), "L": ("", "m", "µ")}


def _grouper(d: Decimal) -> str:
    """Décimal -> écriture française avec espaces fines par tranches de trois."""
    s = num(d)
    signe = "-" if s.startswith("-") else ""
    s = s.lstrip("-")
    ent, _, dec = s.partition("{,}")
    ent = ",".join(ent[max(0, i - 3):i] for i in range(len(ent), 0, -3)[::-1]).replace(",", "\\,")
    if dec:
        dec = "\\,".join(dec[i:i + 3] for i in range(0, len(dec), 3))
        return f"{signe}{ent}{{,}}{dec}"
    return signe + ent


def _p10(e: int) -> str:
    return f"10^{{{e}}}"


def _sci(m: Decimal, e: int) -> str:
    return f"{num(m)} \\times {_p10(e)}"


def _mantisse(rng: random.Random) -> Decimal:
    chiffres = rng.choice((1, 2, 2, 3))
    entier = rng.randint(10 ** (chiffres - 1), 10 ** chiffres - 1)
    if chiffres > 1 and entier % 10 == 0:
        entier += rng.randint(1, 9)
    return (Decimal(entier).scaleb(1 - chiffres)).normalize()


def _gen_calculer(rng: random.Random) -> Optional[dict]:
    genre = rng.choice(("entier", "negatif_par", "negatif_sans", "decimal"))
    n = rng.randint(2, 5)
    if genre == "entier":
        a = rng.randint(2, 9)
        ecrit, val = f"{a}^{{{n}}}", Decimal(a) ** n
        steps = [f"${ecrit}$ est le produit de ${n}$ facteurs égaux à ${a}$.", f"${ecrit} = {_grouper(val)}$."]
    elif genre == "negatif_par":
        a = rng.randint(2, 6)
        ecrit, val = f"(-{a})^{{{n}}}", Decimal(-a) ** n
        signe = "positif" if n % 2 == 0 else "négatif"
        steps = [f"Il y a ${n}$ facteurs négatifs : le résultat est {signe}.",
                 f"${a}^{{{n}}} = {_grouper(Decimal(a) ** n)}$, donc ${ecrit} = {_grouper(val)}$."]
    elif genre == "negatif_sans":
        a = rng.randint(2, 6)
        ecrit, val = f"-{a}^{{{n}}}", -(Decimal(a) ** n)
        steps = [f"Sans parenthèses, l'exposant ne porte que sur ${a}$ : ${ecrit}$ est l'opposé de ${a}^{{{n}}}$.",
                 f"${a}^{{{n}}} = {_grouper(Decimal(a) ** n)}$, donc ${ecrit} = {_grouper(val)}$."]
    else:
        a = Decimal(rng.randint(1, 9)) / 10
        n = rng.randint(2, 3)
        ecrit, val = f"{num(a)}^{{{n}}}", a ** n
        steps = [f"${ecrit}$ est le produit de ${n}$ facteurs égaux à ${num(a)}$.",
                 f"Le résultat a ${n}$ chiffres après la virgule : ${ecrit} = {_grouper(val)}$."]
    return {
        "enonce": f"Calculer $A = {ecrit}$.",
        "answer": f"$A = {_grouper(val)}$",
        "hint": "Écris le produit de facteurs égaux ; attention aux parenthèses et au signe.",
        "steps": steps,
        "notion": N1,
    }


def _gen_ecrire(rng: random.Random) -> Optional[dict]:
    n = rng.randint(3, 7)
    genre = rng.choice(("entier", "negatif", "decimal"))
    if genre == "entier":
        a = str(rng.randint(2, 12))
    elif genre == "negatif":
        a = f"(-{rng.randint(2, 9)})"
    else:
        a = num(Decimal(rng.randint(11, 99)) / 10)
    produit = " \\times ".join([a] * n)
    return {
        "enonce": f"Écrire sous la forme d'une puissance : ${produit}$.",
        "answer": f"${produit} = {a}^{{{n}}}$",
        "hint": "L'exposant est le nombre de facteurs.",
        "steps": [f"Le facteur ${a}$ apparaît ${n}$ fois.", f"Le produit s'écrit ${a}^{{{n}}}$."],
        "notion": N1,
    }


def _gen_p10_decimal(rng: random.Random) -> Optional[dict]:
    e = rng.choice([k for k in range(-6, 8) if k not in (0, 1)])
    val = Decimal(1).scaleb(e)
    genre = rng.choice(("vers_decimal", "vers_puissance", "produit", "produit"))
    if genre == "produit":
        # a × 10^e avec a quelconque (pas forcément entre 1 et 10).
        a = Decimal(rng.randint(1, 9999)).scaleb(-rng.randint(0, 3)).normalize()
        x = (a * val).normalize()
        if x.adjusted() > 9 or x.adjusted() < -7:
            return None
        sens = "droite" if e > 0 else "gauche"
        gauche, droite = f"{_grouper(a)} \\times {_p10(e)}", _grouper(x)
        enonce = f"Donner l'écriture décimale de ${gauche}$."
        steps = [f"Multiplier par ${_p10(e)}$ décale la virgule de ${abs(e)}$ rangs vers la {sens}.",
                 f"${gauche} = {droite}$."]
    else:
        if e > 0:
            just = f"Exposant positif : un $1$ suivi de ${e}$ zéros."
        else:
            just = f"Exposant négatif : $10^{{{e}}} = \\dfrac{{1}}{{10^{{{-e}}}}}$, le chiffre $1$ est au rang ${-e}$ après la virgule."
        if genre == "vers_decimal":
            gauche, droite = _p10(e), _grouper(val)
            enonce = f"Donner l'écriture décimale de ${gauche}$."
        else:
            gauche, droite = _grouper(val), _p10(e)
            enonce = f"Écrire ${gauche}$ sous la forme d'une puissance de $10$."
        steps = [just, f"${gauche} = {droite}$."]
    return {
        "enonce": enonce,
        "answer": f"${gauche} = {droite}$",
        "hint": "L'exposant indique le nombre de zéros (positif) ou le rang du 1 après la virgule (négatif).",
        "steps": steps,
        "notion": N2,
    }


def _gen_produit_p10(rng: random.Random) -> Optional[dict]:
    a, b, c = (rng.randint(-8, 9) for _ in range(3))
    if 0 in (a, b, c):
        return None
    r = a + b - c
    if abs(r) > 15:
        return None
    s = f"{a} + {b}".replace("+ -", "+ (-") + (")" if b < 0 else "")
    return {
        "enonce": f"Écrire sous la forme d'une seule puissance de $10$ : $B = \\dfrac{{{_p10(a)} \\times {_p10(b)}}}{{{_p10(c)}}}$.",
        "answer": f"$B = {_p10(r)}$",
        "hint": "Au numérateur, on additionne les exposants ; pour le quotient, on soustrait celui du dénominateur.",
        "steps": [f"Numérateur : ${_p10(a)} \\times {_p10(b)} = 10^{{{s}}} = {_p10(a + b)}$.",
                  f"Quotient : $\\dfrac{{{_p10(a + b)}}}{{{_p10(c)}}} = 10^{{{a + b} - {f'({c})' if c < 0 else c}}} = {_p10(r)}$."],
        "notion": N2,
    }


def _gen_vers_sci(rng: random.Random) -> Optional[dict]:
    m = _mantisse(rng)
    e = rng.choice([k for k in range(-7, 10) if k not in (0,)])
    x = (m.scaleb(e)).normalize()
    sens = (f"la virgule a été déplacée de ${e}$ rangs vers la gauche" if e > 0
            else f"la virgule a été déplacée de ${-e}$ rangs vers la droite")
    return {
        "enonce": f"Donner l'écriture scientifique de ${_grouper(x)}$.",
        "answer": f"${_grouper(x)} = {_sci(m, e)}$",
        "hint": "Place la virgule juste après le premier chiffre non nul, puis compte les rangs.",
        "steps": [f"Premier chiffre non nul : on écrit ${num(m)}$, compris entre $1$ et $10$.",
                  f"Pour passer de ${_grouper(x)}$ à ${num(m)}$, {sens} : exposant ${e}$.",
                  f"${_grouper(x)} = {_sci(m, e)}$."],
        "notion": N3,
    }


def _gen_depuis_sci(rng: random.Random) -> Optional[dict]:
    m = _mantisse(rng)
    e = rng.choice([k for k in range(-6, 8) if k != 0])
    x = (m.scaleb(e)).normalize()
    sens = "droite" if e > 0 else "gauche"
    return {
        "enonce": f"Donner l'écriture décimale de ${_sci(m, e)}$.",
        "answer": f"${_sci(m, e)} = {_grouper(x)}$",
        "hint": "Exposant positif : virgule vers la droite ; négatif : vers la gauche.",
        "steps": [f"On décale la virgule de ${abs(e)}$ rangs vers la {sens}.",
                  f"${_sci(m, e)} = {_grouper(x)}$."],
        "notion": N3,
    }


def _gen_comparer_sci(rng: random.Random) -> Optional[dict]:
    m1, m2 = _mantisse(rng), _mantisse(rng)
    e1 = rng.randint(-8, 9)
    e2 = e1 + rng.choice((-2, -1, 0, 0, 1, 2))
    x1, x2 = m1.scaleb(e1), m2.scaleb(e2)
    if x1 == x2:
        return None
    signe = "<" if x1 < x2 else ">"
    if e1 != e2:
        just = f"Les exposants sont différents (${e1}$ et ${e2}$) : le nombre qui a le plus grand exposant est le plus grand."
    else:
        just = f"Les exposants sont égaux : on compare ${num(m1)}$ et ${num(m2)}$."
    return {
        "enonce": f"Comparer $a = {_sci(m1, e1)}$ et $b = {_sci(m2, e2)}$.",
        "answer": f"$a {signe} b$",
        "hint": "En écriture scientifique, compare d'abord les exposants.",
        "steps": [just, f"Donc $a {signe} b$."],
        "notion": N3,
    }


def _gen_conversion(rng: random.Random) -> Optional[dict]:
    sym = rng.choice(sorted(_UNITES))
    (s1, n1, e1), (s2, n2, e2) = rng.sample([p for p in _PREFIXES if p[0] in _UNITES[sym]], 2)
    if not 3 <= abs(e1 - e2) <= 9:
        return None
    x = Decimal(rng.randint(2, 950))
    if rng.random() < 0.4:
        x = (x / 10).normalize()
    d = e1 - e2
    resultat = (x.scaleb(d)).normalize()
    exp = resultat.adjusted()
    m = resultat.scaleb(-exp).normalize()
    u1, u2 = f"{s1}{sym}", f"{s2}{sym}"
    v1 = f"$1$ {u1} $= {_p10(e1)}$ {sym}" if s1 else f"$1$ {u1} $= 10^{{0}}$ {sym}"
    v2 = f"$1$ {u2} $= {_p10(e2)}$ {sym}" if s2 else f"$1$ {u2} $= 10^{{0}}$ {sym}"
    return {
        "enonce": f"Convertir ${num(x)}$ {u1} en {u2}. Donner le résultat en écriture scientifique.",
        "answer": f"${num(x)}$ {u1} $= {_sci(m, exp)}$ {u2}",
        "hint": "Écris chaque préfixe sous forme de puissance de $10$, puis compare les exposants.",
        "steps": [f"{v1} et {v2}.",
                  f"$1$ {u1} vaut $\\dfrac{{{_p10(e1)}}}{{{_p10(e2)}}} = {_p10(d)}$ {u2}.",
                  f"${num(x)} \\times {_p10(d)} = {_sci(m, exp)}$ : ${num(x)}$ {u1} $= {_sci(m, exp)}$ {u2}."],
        "notion": N4,
    }


FAMILIES_LIST = (
    Family("calculer_puissance", 1, "Calculer une puissance", N1, _gen_calculer,
           "une puissance d'exposant 2 à 5", "produit de facteurs égaux, signe"),
    Family("ecrire_puissance", 1, "Écrire un produit sous forme de puissance", N1, _gen_ecrire,
           "un produit de facteurs égaux", "compter les facteurs"),
    Family("puissance10_decimal", 1, "Écriture décimale d'une puissance de 10", N2, _gen_p10_decimal,
           "une puissance de 10 d'exposant relatif", "nombre de zéros ou rang du 1"),
    Family("produit_puissances10", 2, "Produits et quotients de puissances de 10", N2, _gen_produit_p10,
           "un quotient de puissances de 10", "additionner puis soustraire les exposants"),
    Family("vers_scientifique", 2, "Donner l'écriture scientifique", N3, _gen_vers_sci,
           "un nombre décimal grand ou petit", "déplacer la virgule"),
    Family("depuis_scientifique", 1, "Passer de l'écriture scientifique au décimal", N3, _gen_depuis_sci,
           "une écriture scientifique", "décaler la virgule"),
    Family("comparer_scientifique", 2, "Comparer en écriture scientifique", N3, _gen_comparer_sci,
           "deux écritures scientifiques", "exposants puis mantisses"),
    Family("conversion_prefixe", 3, "Convertir avec les préfixes", N4, _gen_conversion,
           "une mesure avec un préfixe", "puissances de 10 des préfixes"),
)

CHAPTER = Chapter(5, FAMILIES_LIST)
CHAPTER_ID = CHAPTER.chapter_id
FAMILIES = CHAPTER.families
GENERATED_ID_OFFSET = CHAPTER.id_offset
generate_one = CHAPTER.generate_one
generate_pool = CHAPTER.generate_pool
