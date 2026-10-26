"""Chapitre 4 — Divisibilité et nombres premiers (générateurs).

    critere_divisibilite N1  n divisible par 2, 3, 5, 9 ou 10 ? (critère)
    liste_diviseurs      N1  tous les diviseurs d'un entier ≤ 100
    est_premier          N2  premier ou non (avec un diviseur le cas échéant)
    reconstituer         N3  retrouver un nombre à partir de sa décomposition
    decomposer           N3  décomposition en facteurs premiers
    simplifier_premiers  N4  fraction irréductible par les décompositions
    lots_identiques      N4  plus grand nombre de lots identiques, composition
    rendez_vous          N4  premier instant commun (plus petit multiple commun)
"""
import random
from math import gcd
from typing import Optional

from ._commun import Chapter, Family

N1 = "Multiples, diviseurs et critères de divisibilité"
N2 = "Reconnaître un nombre premier"
N3 = "Décomposer un nombre en produit de facteurs premiers"
N4 = "Utiliser les nombres premiers : fractions et problèmes"

_PREMIERS = (2, 3, 5, 7, 11, 13)


def _facteurs(n):
    out, p = [], 2
    while p * p <= n:
        while n % p == 0:
            out.append(p)
            n //= p
        p += 1
    if n > 1:
        out.append(n)
    return out


def _dec(n):
    return " \\times ".join(str(p) for p in _facteurs(n))


def _milliers(n):
    s = str(n)
    return s if len(s) <= 3 else s[:-3] + "\\," + s[-3:]


def _gen_critere(rng: random.Random) -> Optional[dict]:
    k = rng.choice((2, 3, 5, 9, 10))
    n = rng.randint(100, 9999)
    divisible = n % k == 0
    if rng.random() < 0.5 and not divisible:
        n += (k - n % k) % k
        divisible = n % k == 0
    chiffres = [int(c) for c in str(n)]
    if k in (3, 9):
        somme = " + ".join(map(str, chiffres))
        just = f"Somme des chiffres : ${somme} = {sum(chiffres)}$, qui {'est' if sum(chiffres) % k == 0 else 'n est pas'} divisible par ${k}$."
    elif k == 2:
        just = f"Le chiffre des unités est ${chiffres[-1]}$ : le nombre {'est' if chiffres[-1] % 2 == 0 else 'n est pas'} pair."
    elif k == 5:
        just = f"Le chiffre des unités est ${chiffres[-1]}$ : {'c est' if chiffres[-1] in (0, 5) else 'ce n est pas'} $0$ ou $5$."
    else:
        just = f"Le chiffre des unités est ${chiffres[-1]}$ : {'c est' if chiffres[-1] == 0 else 'ce n est pas'} $0$."
    just = just.replace("n est", "n'est").replace("c est", "c'est")
    reponse = "Oui" if divisible else "Non"
    return {
        "enonce": f"Le nombre ${_milliers(n)}$ est-il divisible par ${k}$ ? Justifier avec un critère de divisibilité.",
        "answer": f"{reponse} : ${_milliers(n)}$ {'est' if divisible else 'n est pas'} divisible par ${k}$.".replace("n est", "n'est"),
        "hint": "Utilise le chiffre des unités (pour 2, 5, 10) ou la somme des chiffres (pour 3, 9).",
        "steps": [just, f"Conclusion : ${_milliers(n)}$ {'est' if divisible else 'n est pas'} divisible par ${k}$.".replace("n est", "n'est")],
        "notion": N1,
    }


def _gen_liste_diviseurs(rng: random.Random) -> Optional[dict]:
    n = rng.randint(12, 100)
    divs = [d for d in range(1, n + 1) if n % d == 0]
    if len(divs) < 4:
        return None
    paires = [(d, n // d) for d in divs if d * d <= n]
    texte_paires = ", ".join(f"${a} \\times {b}$" for a, b in paires)
    return {
        "enonce": f"Donner la liste de tous les diviseurs de ${n}$.",
        "answer": f"Diviseurs de ${n}$ : $" + ", ".join(map(str, divs)) + "$.",
        "hint": "Cherche les diviseurs par paires, en commençant par $1$ et le nombre lui-même.",
        "steps": [f"Paires de diviseurs : {texte_paires}.",
                  "On s'arrête quand le premier facteur de la paire dépasse le second.",
                  "Liste rangée : $" + ", ".join(map(str, divs)) + f"$ ({len(divs)} diviseurs)."],
        "notion": N1,
    }


def _gen_est_premier(rng: random.Random) -> Optional[dict]:
    n = rng.randint(20, 150)
    if n % 2 == 0 or n % 5 == 0:
        return None
    f = _facteurs(n)
    tests = [p for p in (2, 3, 5, 7, 11) if p * p <= n]
    if len(f) == 1:
        return {
            "enonce": f"Le nombre ${n}$ est-il premier ? Justifier.",
            "answer": f"Oui, ${n}$ est premier.",
            "hint": "Teste la divisibilité par les nombres premiers dont le carré ne dépasse pas le nombre.",
            "steps": ["Nombres premiers à tester : $" + ", ".join(map(str, tests)) + "$.",
                      f"Aucun d'eux ne divise ${n}$.",
                      f"${n}$ n'a que deux diviseurs, $1$ et lui-même : il est premier."],
            "notion": N2,
        }
    p = f[0]
    return {
        "enonce": f"Le nombre ${n}$ est-il premier ? Justifier.",
        "answer": f"Non : ${n} = {p} \\times {n // p}$.",
        "hint": "Teste la divisibilité par les nombres premiers dont le carré ne dépasse pas le nombre.",
        "steps": ["Nombres premiers à tester : $" + ", ".join(map(str, tests)) + "$.",
                  f"${n} = {p} \\times {n // p}$ : ${p}$ est un diviseur de ${n}$ autre que $1$ et ${n}$.",
                  f"${n}$ n'est donc pas premier."],
        "notion": N2,
    }


def _tirage_produit(rng, nmin=3, nmax=5, borne=3000):
    k = rng.randint(nmin, nmax)
    fs = sorted(rng.choice(_PREMIERS) for _ in range(k))
    n = 1
    for p in fs:
        n *= p
    if n > borne or len(set(fs)) < 2:
        return None, None
    return n, fs


def _gen_reconstituer(rng: random.Random) -> Optional[dict]:
    n, fs = _tirage_produit(rng, 3, 5, 2500)
    if n is None:
        return None
    ecrit = " \\times ".join(map(str, fs))
    return {
        "enonce": f"Quel nombre a pour décomposition en facteurs premiers ${ecrit}$ ?",
        "answer": f"Ce nombre est ${_milliers(n)}$.",
        "hint": "Effectue le produit en regroupant astucieusement les facteurs.",
        "steps": [f"On effectue le produit ${ecrit}$.",
                  f"Résultat : ${_milliers(n)}$."],
        "notion": N3,
    }


def _gen_decomposer(rng: random.Random) -> Optional[dict]:
    n, fs = _tirage_produit(rng, 3, 5, 3000)
    if n is None:
        return None
    etapes, m = [], n
    for p in fs:
        etapes.append(f"${_milliers(m)} \\div {p} = {_milliers(m // p)}$")
        m //= p
    return {
        "enonce": f"Décomposer ${_milliers(n)}$ en produit de facteurs premiers.",
        "answer": f"${_milliers(n)} = {_dec(n)}$",
        "hint": "Divise par $2$ tant que c'est possible, puis par $3$, $5$, $7$…",
        "steps": ["Divisions successives : " + " ; ".join(etapes) + ".",
                  f"Décomposition : ${_milliers(n)} = {_dec(n)}$."],
        "notion": N3,
    }


def _gen_simplifier_premiers(rng: random.Random) -> Optional[dict]:
    a, fa = _tirage_produit(rng, 2, 4, 600)
    b, fb = _tirage_produit(rng, 2, 4, 600)
    if a is None or b is None or a == b or gcd(a, b) == 1 or a >= b:
        return None
    g = gcd(a, b)
    return {
        "enonce": f"Simplifier $\\dfrac{{{a}}}{{{b}}}$ grâce aux décompositions en facteurs premiers.",
        "answer": f"$\\dfrac{{{a}}}{{{b}}} = \\dfrac{{{a // g}}}{{{b // g}}}$",
        "hint": "Décompose le numérateur et le dénominateur, puis barre les facteurs communs.",
        "steps": [f"${a} = {_dec(a)}$ et ${b} = {_dec(b)}$.",
                  f"Facteurs communs : ${_dec(g)}$, de produit ${g}$.",
                  f"$\\dfrac{{{a}}}{{{b}}} = \\dfrac{{{a // g}}}{{{b // g}}}$, fraction irréductible."],
        "notion": N4,
    }


_LOTS = (("roses", "tulipes", "bouquets", "chacun"), ("crayons", "gommes", "trousses", "chacune"),
         ("billes rouges", "billes bleues", "sachets", "chacun"), ("cartes vertes", "cartes jaunes", "paquets", "chacun"))


def _gen_lots_identiques(rng: random.Random) -> Optional[dict]:
    g = rng.randint(4, 30)
    x, y = rng.randint(2, 15), rng.randint(2, 15)
    if gcd(x, y) != 1 or x == y:
        return None
    a, b = g * x, g * y
    o1, o2, lot, chacun = rng.choice(_LOTS)
    return {
        "enonce": (f"On dispose de ${a}$ {o1} et de ${b}$ {o2}. On veut faire le plus grand nombre possible de {lot} "
                   "identiques en utilisant tout. Combien de " + lot + " peut-on faire, et que contient " + chacun + " ?"),
        "answer": f"On fait ${g}$ {lot}, contenant {chacun} ${x}$ {o1} et ${y}$ {o2}.",
        "hint": "Le nombre de lots doit diviser les deux quantités : cherche leurs facteurs premiers communs.",
        "steps": [f"${a} = {_dec(a)}$ et ${b} = {_dec(b)}$.",
                  f"Plus grand diviseur commun : ${g}$.",
                  f"Chaque lot contient ${a} \\div {g} = {x}$ {o1} et ${b} \\div {g} = {y}$ {o2}."],
        "notion": N4,
    }


def _gen_rendez_vous(rng: random.Random) -> Optional[dict]:
    p, q = rng.randint(4, 30), rng.randint(4, 30)
    if p == q or p % q == 0 or q % p == 0:
        return None
    m = p * q // gcd(p, q)
    if m > 240:
        return None
    return {
        "enonce": (f"Deux lampes clignotent : la première toutes les ${p}$ secondes, la seconde toutes les ${q}$ secondes. "
                   "Elles s'allument ensemble à l'instant $0$. Au bout de combien de secondes s'allumeront-elles de nouveau ensemble pour la première fois ?"),
        "answer": f"Au bout de ${m}$ secondes.",
        "hint": "Cherche le plus petit multiple commun non nul des deux durées.",
        "steps": [f"${p} = {_dec(p)}$ et ${q} = {_dec(q)}$.",
                  "Le plus petit multiple commun contient chaque facteur premier autant de fois qu'il apparaît au maximum dans l'une des décompositions.",
                  f"Plus petit multiple commun : ${m}$ secondes."],
        "notion": N4,
    }


FAMILIES_LIST = (
    Family("critere_divisibilite", 1, "Utiliser un critère de divisibilité", N1, _gen_critere,
           "un nombre à trois ou quatre chiffres", "dernier chiffre ou somme des chiffres"),
    Family("liste_diviseurs", 2, "Lister les diviseurs d'un nombre", N1, _gen_liste_diviseurs,
           "un nombre inférieur à 100", "diviseurs par paires"),
    Family("est_premier", 1, "Reconnaître un nombre premier", N2, _gen_est_premier,
           "un nombre impair entre 20 et 150", "tester 2, 3, 5, 7, 11"),
    Family("reconstituer", 1, "Retrouver un nombre à partir de sa décomposition", N3, _gen_reconstituer,
           "un produit de facteurs premiers", "effectuer le produit"),
    Family("decomposer", 2, "Décomposer en facteurs premiers", N3, _gen_decomposer,
           "un entier inférieur à 3 000", "divisions successives"),
    Family("simplifier_premiers", 2, "Simplifier grâce aux nombres premiers", N4, _gen_simplifier_premiers,
           "une fraction non irréductible", "barrer les facteurs communs"),
    Family("lots_identiques", 3, "Lots identiques", N4, _gen_lots_identiques,
           "deux quantités à partager", "plus grand diviseur commun"),
    Family("rendez_vous", 3, "Événements qui se répètent", N4, _gen_rendez_vous,
           "deux périodes", "plus petit multiple commun"),
)

CHAPTER = Chapter(4, FAMILIES_LIST)
CHAPTER_ID = CHAPTER.chapter_id
FAMILIES = CHAPTER.families
GENERATED_ID_OFFSET = CHAPTER.id_offset
generate_one = CHAPTER.generate_one
generate_pool = CHAPTER.generate_pool
