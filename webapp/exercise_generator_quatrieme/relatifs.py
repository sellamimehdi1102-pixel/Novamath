"""Chapitre 1 — Nombres relatifs : générateurs (Quatrième).

    produit_deux          N1  produit de deux décimaux relatifs
    facteur_manquant      N1  retrouver un facteur (a × ? = p)
    signe_produit         N2  signe d'un produit de 4 à 7 facteurs (parité)
    produit_plusieurs     N2  produit de 3 ou 4 facteurs entiers
    quotient              N3  quotient exact de deux décimaux relatifs
    variation_moyenne     N3  variation totale partagée en parts égales
    priorites             N4  expression à priorités et parenthèses
    substitution          N4  valeur d'une expression pour un x négatif

Arithmétique exacte (fractions.Fraction) ; chaque énoncé est vérifié par un
contrôleur indépendant dans tests/test_quatrieme_programme.py.
"""
import random
from fractions import Fraction as Fr
from typing import Optional

from ._commun import Chapter, Family, num, par

N1 = "Multiplier deux nombres relatifs"
N2 = "Signe d'un produit de plusieurs facteurs"
N3 = "Diviser des nombres relatifs"
N4 = "Enchaîner des calculs avec des nombres relatifs"


def _rel(rng, low, high, decimals=0, nonzero=True):
    """Relatif aléatoire (décimal exact) de distance à zéro dans [low, high]."""
    scale = 10 ** decimals
    while True:
        v = Fr(rng.randint(int(low * scale), int(high * scale)), scale)
        if nonzero and v == 0:
            continue
        return v if rng.random() < 0.5 else -v


def _gen_produit_deux(rng: random.Random) -> Optional[dict]:
    a = _rel(rng, 1, 12, rng.choice((0, 1)))
    b = _rel(rng, 1, 12, rng.choice((0, 0, 1)))
    if a.denominator > 1 and b.denominator > 1 and rng.random() < 0.5:
        return None
    if a > 0 and b > 0:
        a = -a
    p = a * b
    signe = "positif" if p > 0 else "négatif"
    regle = "même signe" if (a > 0) == (b > 0) else "signes contraires"
    forme = rng.choice(("Calculer $%s \\times %s$.", "Donner la valeur du produit $%s \\times %s$.",
                        "Effectuer, sans calculatrice : $%s \\times %s$."))
    return {
        "enonce": forme % (par(a), par(b)),
        "answer": f"${par(a)} \\times {par(b)} = {num(p)}$",
        "hint": "Détermine d'abord le signe du produit, puis multiplie les distances à zéro.",
        "steps": [f"Les facteurs sont de {regle} : le produit est {signe}.",
                  f"Produit des distances à zéro : ${num(abs(a))} \\times {num(abs(b))} = {num(abs(p))}$.",
                  f"Conclusion : ${par(a)} \\times {par(b)} = {num(p)}$."],
        "notion": N1,
    }


def _gen_facteur_manquant(rng: random.Random) -> Optional[dict]:
    a = _rel(rng, 2, 9)
    x = _rel(rng, 1, 12, rng.choice((0, 1)))
    p = a * x
    signe_x = "positif" if x > 0 else "négatif"
    return {
        "enonce": f"Quel nombre faut-il multiplier par ${num(a)}$ pour obtenir ${num(p)}$ ?",
        "answer": f"Il faut multiplier ${num(a)}$ par ${num(x)}$.",
        "hint": "Cherche d'abord le signe du facteur manquant, puis sa distance à zéro par une division.",
        "steps": [f"On cherche $x$ tel que $x \\times {par(a)} = {num(p)}$ : $x$ est {signe_x}.",
                  f"Distance à zéro : ${num(abs(p))} \\div {num(abs(a))} = {num(abs(x))}$.",
                  f"Vérification : ${par(x)} \\times {par(a)} = {num(p)}$."],
        "notion": N1,
    }


def _gen_signe_produit(rng: random.Random) -> Optional[dict]:
    n = rng.randint(4, 7)
    facteurs = [_rel(rng, 1, 20, rng.choice((0, 1))) for _ in range(n)]
    nb_neg = sum(1 for f in facteurs if f < 0)
    if nb_neg == 0:
        return None
    signe = "positif" if nb_neg % 2 == 0 else "négatif"
    parite = "pair" if nb_neg % 2 == 0 else "impair"
    ecriture = " \\times ".join(par(f) for f in facteurs)
    return {
        "enonce": f"Sans calculer, donner le signe du produit $P = {ecriture}$.",
        "answer": f"$P$ est {signe}.",
        "hint": "Compte les facteurs négatifs : seule la parité de ce nombre compte.",
        "steps": [f"Le produit contient {nb_neg} facteur{'s' if nb_neg > 1 else ''} négatif{'s' if nb_neg > 1 else ''}.",
                  f"{nb_neg} est un nombre {parite} : le produit est {signe}."],
        "notion": N2,
    }


def _gen_produit_plusieurs(rng: random.Random) -> Optional[dict]:
    n = rng.choice((3, 4))
    facteurs = [_rel(rng, 1, 6) for _ in range(n)]
    if all(f > 0 for f in facteurs):
        return None
    p = Fr(1)
    for f in facteurs:
        p *= f
    nb_neg = sum(1 for f in facteurs if f < 0)
    signe = "positif" if p > 0 else "négatif"
    ecriture = " \\times ".join(par(f) for f in facteurs)
    distances = " \\times ".join(num(abs(f)) for f in facteurs)
    return {
        "enonce": f"Calculer $Q = {ecriture}$.",
        "answer": f"$Q = {num(p)}$",
        "hint": "Compte les facteurs négatifs pour le signe, puis multiplie les distances à zéro.",
        "steps": [f"{nb_neg} facteur{'s' if nb_neg > 1 else ''} négatif{'s' if nb_neg > 1 else ''} : le produit est {signe}.",
                  f"${distances} = {num(abs(p))}$.",
                  f"$Q = {num(p)}$."],
        "notion": N2,
    }


def _gen_quotient(rng: random.Random) -> Optional[dict]:
    b = _rel(rng, 1, 9, rng.choice((0, 0, 1)))
    q = _rel(rng, 1, 15, rng.choice((0, 1)))
    a = b * q
    if a.denominator > 10 or abs(a) > 200:
        return None
    signe = "positif" if q > 0 else "négatif"
    regle = "même signe" if (a > 0) == (b > 0) else "signes contraires"
    return {
        "enonce": f"Calculer ${par(a)} \\div {par(b)}$.",
        "answer": f"${par(a)} \\div {par(b)} = {num(q)}$",
        "hint": "Même règle des signes que pour le produit ; vérifie ensuite par une multiplication.",
        "steps": [f"Dividende et diviseur sont de {regle} : le quotient est {signe}.",
                  f"${num(abs(a))} \\div {num(abs(b))} = {num(abs(q))}$.",
                  f"Vérification : ${par(q)} \\times {par(b)} = {num(a)}$."],
        "notion": N3,
    }


def _gen_variation_moyenne(rng: random.Random) -> Optional[dict]:
    debut = rng.randint(-8, 9)
    heures = rng.choice((2, 4, 5, 8))
    pas = _rel(rng, 1, 4, 1)
    fin = debut + heures * pas
    if fin.denominator > 1 and fin.denominator != 2 and fin.denominator != 5 and fin.denominator != 10:
        return None
    total = fin - debut
    sens = "baissé" if pas < 0 else "augmenté"
    return {
        "enonce": (f"La température est passée de ${num(debut)}$ °C à ${num(fin)}$ °C en ${heures}$ heures, "
                   "de façon régulière. Calculer la variation de température par heure."),
        "answer": f"La variation est de ${num(pas)}$ °C par heure.",
        "hint": "Calcule la variation totale (arrivée moins départ), puis partage-la en parts égales.",
        "steps": [f"Variation totale : ${num(fin)} - {par(debut)} = {num(total)}$ °C.",
                  f"Par heure : ${par(total)} \\div {heures} = {num(pas)}$.",
                  f"La température a {sens} de ${num(abs(pas))}$ °C chaque heure."],
        "notion": N3,
    }


def _gen_priorites(rng: random.Random) -> Optional[dict]:
    a = rng.randint(-9, 9)
    b = rng.randint(-6, 6)
    c = rng.randint(-9, 9)
    dd = rng.randint(-9, 9)
    if b in (0, 1) or c == dd:
        return None
    inner = c - dd
    prodv = b * inner
    total = a + prodv
    return {
        "enonce": f"Calculer $A = {num(a)} + {par(b)} \\times ({num(c)} - {par(dd)})$.",
        "answer": f"$A = {num(total)}$",
        "hint": "Parenthèses d'abord, puis la multiplication, puis l'addition.",
        "steps": [f"Parenthèses : ${num(c)} - {par(dd)} = {num(inner)}$.",
                  f"Multiplication : ${par(b)} \\times {par(inner)} = {num(prodv)}$.",
                  f"Addition : $A = {num(a)} + {par(prodv)} = {num(total)}$."],
        "notion": N4,
    }


def _gen_substitution(rng: random.Random) -> Optional[dict]:
    a = rng.choice((-3, -2, 2, 3, 4, 5))
    b = rng.randint(-7, 7)
    c = rng.randint(-9, 9)
    x = rng.randint(-5, -1)
    if b == 0 or c == 0:
        return None
    carre = x * x
    t1, t2 = a * carre, b * x
    val = t1 + t2 + c
    expr = f"{num(a)}x^2 {'+' if b > 0 else '-'} {abs(b)}x {'+' if c >= 0 else '-'} {abs(c)}"
    return {
        "enonce": f"Calculer $E = {expr}$ pour $x = {num(x)}$.",
        "answer": f"$E = {num(val)}$",
        "hint": "Remplace $x$ par le nombre entre parenthèses ; le carré se calcule en premier.",
        "steps": [f"$E = {num(a)} \\times ({num(x)})^2 {'+' if b > 0 else '-'} {abs(b)} \\times ({num(x)}) {'+' if c >= 0 else '-'} {abs(c)}$.",
                  f"$({num(x)})^2 = {carre}$, donc ${num(a)} \\times {carre} = {num(t1)}$ ; et ${num(b)} \\times ({num(x)}) = {num(t2)}$.",
                  f"$E = {num(t1)} {'+' if t2 >= 0 else '-'} {num(abs(t2))} {'+' if c >= 0 else '-'} {abs(c)} = {num(val)}$."],
        "notion": N4,
    }


FAMILIES_LIST = (
    Family("produit_deux", 1, "Produit de deux relatifs", N1, _gen_produit_deux,
           "deux décimaux relatifs", "signe d'abord, puis produit des distances à zéro"),
    Family("facteur_manquant", 2, "Retrouver un facteur", N1, _gen_facteur_manquant,
           "un produit et un facteur connus", "le facteur manquant est un quotient"),
    Family("signe_produit", 1, "Signe d'un produit de plusieurs facteurs", N2, _gen_signe_produit,
           "un produit de 4 à 7 facteurs", "compter les facteurs négatifs"),
    Family("produit_plusieurs", 2, "Produit de plusieurs facteurs", N2, _gen_produit_plusieurs,
           "trois ou quatre facteurs entiers", "parité des facteurs négatifs"),
    Family("quotient", 2, "Quotient de deux relatifs", N3, _gen_quotient,
           "un quotient exact", "règle des signes puis vérification"),
    Family("variation_moyenne", 3, "Variation moyenne de température", N3, _gen_variation_moyenne,
           "une variation régulière", "variation totale divisée par la durée"),
    Family("priorites", 3, "Expression avec priorités", N4, _gen_priorites,
           "parenthèses, produit, somme", "respecter l'ordre des opérations"),
    Family("substitution", 4, "Valeur d'une expression pour x négatif", N4, _gen_substitution,
           "une expression du second degré", "remplacer x entre parenthèses"),
)

CHAPTER = Chapter(1, FAMILIES_LIST)
CHAPTER_ID = CHAPTER.chapter_id
FAMILIES = CHAPTER.families
GENERATED_ID_OFFSET = CHAPTER.id_offset
generate_one = CHAPTER.generate_one
generate_pool = CHAPTER.generate_pool
