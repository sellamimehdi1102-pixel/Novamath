"""Chapitre 9 — Théorème de Thalès, triangles emboîtés (générateurs).

Nom de module distinct de exercise_generator_troisieme.thales (même registre).

    rapports_thales     N1  écrire l'égalité des trois rapports (lettres variées)
    longueur_petit      N2  longueur du petit triangle
    longueur_grand      N2  longueur du grand triangle
    longueur_difference N2  données AM, MB, AN : calculer AC puis NC
    ombre               N2  hauteur d'un objet grâce aux ombres
    reciproque          N3  les droites sont-elles parallèles ?
    rapport_k           N4  rapport d'agrandissement-réduction et longueur
    aire_k2             N4  aire après agrandissement ou réduction
"""
import random
from fractions import Fraction
from typing import Optional

from ._commun import Chapter, Family, grp

N1 = "Configuration de Thalès et égalité des rapports"
N2 = "Calculer une longueur avec le théorème de Thalès"
N3 = "Réciproque du théorème de Thalès : démontrer un parallélisme"
N4 = "Agrandissement et réduction"

# (sommet commun, B, C, M sur [AB], N sur [AC])
_LETTRES = (("A", "B", "C", "M", "N"), ("R", "S", "T", "E", "F"), ("O", "P", "Q", "K", "L"),
            ("E", "F", "G", "H", "K"), ("D", "E", "F", "U", "V"), ("S", "T", "U", "I", "J"))
_K = (Fraction(1, 5), Fraction(1, 4), Fraction(2, 5), Fraction(1, 2), Fraction(3, 5), Fraction(3, 4), Fraction(4, 5))


def _l(f) -> str:
    return grp(Fraction(f))


def _config(rng):
    a, b, c, m, n = rng.choice(_LETTRES)
    k = rng.choice(_K)
    # grandes longueurs multiples de 0,5 telles que les petites soient décimales
    grands = [Fraction(rng.randint(6, 30), 2) for _ in range(3)]
    ab, ac, bc = grands
    if not (ab + ac > bc and ab + bc > ac and ac + bc > ab):
        return None
    return (a, b, c, m, n), k, ab, ac, bc


def _hyp(a, b, c, m, n):
    return f"Dans le triangle ${a}{b}{c}$, ${m} \\in [{a}{b}]$, ${n} \\in [{a}{c}]$ et $({m}{n}) \\parallel ({b}{c})$."


def _egalite(a, b, c, m, n):
    return f"\\dfrac{{{a}{m}}}{{{a}{b}}} = \\dfrac{{{a}{n}}}{{{a}{c}}} = \\dfrac{{{m}{n}}}{{{b}{c}}}"


def _gen_rapports(rng: random.Random) -> Optional[dict]:
    a, b, c, m, n = rng.sample("ABCDEFGHIJKLMNPRSTUVWXYZ", 5)
    ordre = rng.random() < 0.5
    alignements = (f"les points ${a}$, ${m}$, ${b}$ sont alignés dans cet ordre, ainsi que ${a}$, ${n}$, ${c}$"
                   if ordre else f"${m} \\in [{a}{b}]$ et ${n} \\in [{a}{c}]$")
    return {
        "enonce": f"Dans une figure, {alignements} ; de plus, $({m}{n}) \\parallel ({b}{c})$. Écrire l'égalité des rapports de Thalès.",
        "answer": f"${_egalite(a, b, c, m, n)}$",
        "hint": f"Le sommet commun est ${a}$ ; petit triangle ${a}{m}{n}$ au numérateur, grand triangle ${a}{b}{c}$ au dénominateur.",
        "steps": [f"Sommet commun : ${a}$ ; petit triangle ${a}{m}{n}$, grand triangle ${a}{b}{c}$.",
                  f"Côtés correspondants : ${a}{m}$ et ${a}{b}$, ${a}{n}$ et ${a}{c}$, ${m}{n}$ et ${b}{c}$.",
                  f"${_egalite(a, b, c, m, n)}$."],
        "notion": N1,
    }


def _gen_longueur(rng: random.Random, petit: bool) -> Optional[dict]:
    cfg = _config(rng)
    if cfg is None:
        return None
    (a, b, c, m, n), k, ab, ac, bc = cfg
    paires = [((a + m), (a + b), ab), ((a + n), (a + c), ac), ((m + n), (b + c), bc)]
    i_connu, i_cherche = rng.sample(range(3), 2)
    pc, gc, vc = paires[i_connu]
    pi, gi, vi = paires[i_cherche]
    donnees = [f"${pc} = {_l(k * vc)}$ cm", f"${gc} = {_l(vc)}$ cm"]
    if petit:
        donnees.append(f"${gi} = {_l(vi)}$ cm")
        cible, res = pi, k * vi
        calc = f"${pi} = \\dfrac{{{_l(k * vc)} \\times {_l(vi)}}}{{{_l(vc)}}} = {_l(res)}$ cm."
        rapport = f"\\dfrac{{{_l(k * vc)}}}{{{_l(vc)}}} = \\dfrac{{{pi}}}{{{_l(vi)}}}"
    else:
        donnees.append(f"${pi} = {_l(k * vi)}$ cm")
        cible, res = gi, vi
        calc = f"${gi} = \\dfrac{{{_l(vc)} \\times {_l(k * vi)}}}{{{_l(k * vc)}}} = {_l(res)}$ cm."
        rapport = f"\\dfrac{{{_l(k * vc)}}}{{{_l(vc)}}} = \\dfrac{{{_l(k * vi)}}}{{{gi}}}"
    rng.shuffle(donnees)
    return {
        "enonce": f"{_hyp(a, b, c, m, n)} On donne {', '.join(donnees[:-1])} et {donnees[-1]}. Calculer ${cible}$.",
        "answer": f"${cible} = {_l(res)}$ cm.",
        "hint": "Écris l'égalité des trois rapports, garde le rapport complet et celui de l'inconnue, puis fais un produit en croix.",
        "steps": [f"D'après le théorème de Thalès : ${_egalite(a, b, c, m, n)}$.",
                  f"On garde : ${rapport}$.",
                  calc],
        "notion": N2,
    }


def _gen_petit(rng):
    return _gen_longueur(rng, True)


def _gen_grand(rng):
    return _gen_longueur(rng, False)


def _gen_difference(rng: random.Random) -> Optional[dict]:
    cfg = _config(rng)
    if cfg is None:
        return None
    (a, b, c, m, n), k, ab, ac, bc = cfg
    am, mb, an = k * ab, ab - k * ab, k * ac
    return {
        "enonce": (f"{_hyp(a, b, c, m, n)} On donne ${a}{m} = {_l(am)}$ cm, ${m}{b} = {_l(mb)}$ cm et ${a}{n} = {_l(an)}$ cm. "
                   f"Calculer ${a}{c}$, puis ${n}{c}$."),
        "answer": f"${a}{c} = {_l(ac)}$ cm et ${n}{c} = {_l(ac - an)}$ cm.",
        "hint": f"Calcule d'abord ${a}{b} = {a}{m} + {m}{b}$.",
        "steps": [f"${a}{b} = {_l(am)} + {_l(mb)} = {_l(ab)}$ cm.",
                  f"Thalès : $\\dfrac{{{_l(am)}}}{{{_l(ab)}}} = \\dfrac{{{_l(an)}}}{{{a}{c}}}$, donc ${a}{c} = \\dfrac{{{_l(ab)} \\times {_l(an)}}}{{{_l(am)}}} = {_l(ac)}$ cm.",
                  f"${n}{c} = {_l(ac)} - {_l(an)} = {_l(ac - an)}$ cm."],
        "notion": N2,
    }


def _gen_ombre(rng: random.Random) -> Optional[dict]:
    le_objet, de_objet = rng.choice((("l'arbre", "de l'arbre"), ("l'immeuble", "de l'immeuble"), ("le pylône", "du pylône"),
                                     ("la tour", "de la tour"), ("le clocher", "du clocher")))
    h = Fraction(rng.randint(8, 20), 10)                  # bâton de 0,8 à 2 m
    s = Fraction(rng.randint(4, 30), 10)                  # ombre du bâton
    facteur = Fraction(rng.randint(8, 40), 2)
    S = s * facteur
    H = h * facteur
    if H > 80:
        return None
    return {
        "enonce": (f"Un bâton vertical de ${_l(h)}$ m a une ombre de ${_l(s)}$ m. Au même moment, l'ombre {de_objet} mesure ${_l(S)}$ m. "
                   f"Les rayons du soleil sont parallèles et le bâton comme {le_objet} sont verticaux. Quelle est la hauteur {de_objet} ?"),
        "answer": f"La hauteur est ${_l(H)}$ m.",
        "hint": f"Le bâton et {le_objet} sont verticaux, donc parallèles : configuration de Thalès dont le sommet est l'extrémité des ombres.",
        "steps": [f"Rapports : $\\dfrac{{{_l(s)}}}{{{_l(S)}}} = \\dfrac{{{_l(h)}}}{{H}}$.",
                  f"$H = \\dfrac{{{_l(S)} \\times {_l(h)}}}{{{_l(s)}}} = {_l(H)}$ m."],
        "notion": N2,
    }


def _gen_reciproque(rng: random.Random) -> Optional[dict]:
    cfg = _config(rng)
    if cfg is None:
        return None
    (a, b, c, m, n), k, ab, ac, bc = cfg
    am = k * ab
    parallele = rng.random() < 0.5
    if parallele:
        an = k * ac
    else:
        k2 = rng.choice([x for x in _K if x != k])
        an = k2 * ac
    r1, r2 = am / ab, an / ac
    vrai = r1 == r2
    p1, p2 = am * ac, ab * an
    return {
        "enonce": (f"Dans le triangle ${a}{b}{c}$, ${m} \\in [{a}{b}]$ et ${n} \\in [{a}{c}]$, avec ${a}{m} = {_l(am)}$, ${a}{b} = {_l(ab)}$, "
                   f"${a}{n} = {_l(an)}$ et ${a}{c} = {_l(ac)}$. Les droites $({m}{n})$ et $({b}{c})$ sont-elles parallèles ?"),
        "answer": (f"Oui : $\\dfrac{{{a}{m}}}{{{a}{b}}} = \\dfrac{{{a}{n}}}{{{a}{c}}} = {_l(r1)}$, donc $({m}{n}) \\parallel ({b}{c})$ d'après la réciproque du théorème de Thalès."
                   if vrai else
                   f"Non : $\\dfrac{{{a}{m}}}{{{a}{b}}} = {_l(r1)}$ et $\\dfrac{{{a}{n}}}{{{a}{c}}} = {_l(r2)}$ sont différents, donc $({m}{n})$ et $({b}{c})$ ne sont pas parallèles."),
        "hint": f"Calcule séparément $\\dfrac{{{a}{m}}}{{{a}{b}}}$ et $\\dfrac{{{a}{n}}}{{{a}{c}}}$.",
        "steps": [f"$\\dfrac{{{a}{m}}}{{{a}{b}}} = \\dfrac{{{_l(am)}}}{{{_l(ab)}}} = {_l(r1)}$.",
                  f"$\\dfrac{{{a}{n}}}{{{a}{c}}} = \\dfrac{{{_l(an)}}}{{{_l(ac)}}} = {_l(r2)}$.",
                  (f"Les rapports sont égaux (produits en croix : ${_l(p1)} = {_l(p2)}$) : réciproque du théorème de Thalès."
                   if vrai else
                   "Si les droites étaient parallèles, ces rapports seraient égaux (théorème de Thalès) : elles ne le sont donc pas.")],
        "notion": N3,
    }


def _gen_rapport_k(rng: random.Random) -> Optional[dict]:
    k = rng.choice((Fraction(1, 2), Fraction(3, 2), Fraction(2), Fraction(5, 2), Fraction(3), Fraction(3, 4), Fraction(2, 5), Fraction(4)))
    l1 = Fraction(rng.randint(4, 40), 2)
    l2 = Fraction(rng.randint(4, 40), 2)
    if l1 == l2:
        return None
    nature = "agrandissement" if k > 1 else "réduction"
    objet = rng.choice(("d'une figure", "d'un polygone", "d'un triangle", "d'un logo", "d'un plan"))
    return {
        "enonce": (f"Par un agrandissement ou une réduction, un segment de ${_l(l1)}$ cm {objet} devient un segment de ${_l(k * l1)}$ cm. "
                   f"Quel est le rapport ? S'agit-il d'un agrandissement ou d'une réduction ? Que devient un segment de ${_l(l2)}$ cm ?"),
        "answer": f"Rapport $k = {_l(k)}$ : c'est {'un' if k > 1 else 'une'} {nature} ; le segment de ${_l(l2)}$ cm devient ${_l(k * l2)}$ cm.",
        "hint": "$k$ = longueur obtenue ÷ longueur de départ.",
        "steps": [f"$k = \\dfrac{{{_l(k * l1)}}}{{{_l(l1)}}} = {_l(k)}$ : {'supérieur' if k > 1 else 'inférieur'} à $1$, c'est {'un' if k > 1 else 'une'} {nature}.",
                  f"${_l(l2)} \\times {_l(k)} = {_l(k * l2)}$ cm."],
        "notion": N4,
    }


def _gen_aire_k2(rng: random.Random) -> Optional[dict]:
    k = rng.choice((Fraction(1, 2), Fraction(3, 2), Fraction(2), Fraction(5, 2), Fraction(3), Fraction(2, 5), Fraction(3, 5), Fraction(4, 5), Fraction(1, 4)))
    aire = Fraction(rng.randint(4, 200))
    nature = "agrandie" if k > 1 else "réduite"
    figure = rng.choice(("Un triangle", "Un rectangle", "Un parallélogramme", "Un trapèze", "Un hexagone"))
    return {
        "enonce": f"{figure} d'aire ${_l(aire)}$ cm² est {'agrandi' if k > 1 else 'réduit'} avec le rapport ${_l(k)}$. Quelle est l'aire de la figure {nature} ?",
        "answer": f"L'aire de la figure {nature} est ${_l(aire * k * k)}$ cm².",
        "hint": "Les aires sont multipliées par $k^2$.",
        "steps": [f"$k^2 = {_l(k)}^2 = {_l(k * k)}$.", f"${_l(aire)} \\times {_l(k * k)} = {_l(aire * k * k)}$ cm²."],
        "notion": N4,
    }


FAMILIES_LIST = (
    Family("rapports_thales", 1, "Écrire l'égalité de Thalès", N1, _gen_rapports,
           "deux triangles emboîtés", "petit sur grand"),
    Family("longueur_petit", 1, "Longueur du petit triangle", N2, _gen_petit,
           "trois longueurs connues", "produit en croix"),
    Family("longueur_grand", 2, "Longueur du grand triangle", N2, _gen_grand,
           "trois longueurs connues", "produit en croix"),
    Family("longueur_difference", 2, "Longueur par différence", N2, _gen_difference,
           "AM, MB et AN", "AB = AM + MB"),
    Family("ombre", 3, "Hauteur grâce aux ombres", N2, _gen_ombre,
           "un bâton et un objet", "rayons parallèles"),
    Family("reciproque", 2, "Réciproque de Thalès", N3, _gen_reciproque,
           "quatre longueurs", "comparer deux rapports"),
    Family("rapport_k", 1, "Rapport d'agrandissement-réduction", N4, _gen_rapport_k,
           "deux longueurs correspondantes", "k = obtenue / départ"),
    Family("aire_k2", 2, "Aire et rapport k", N4, _gen_aire_k2,
           "une aire et un rapport", "aires × k²"),
)

CHAPTER = Chapter(9, FAMILIES_LIST)
CHAPTER_ID = CHAPTER.chapter_id
FAMILIES = CHAPTER.families
GENERATED_ID_OFFSET = CHAPTER.id_offset
generate_one = CHAPTER.generate_one
generate_pool = CHAPTER.generate_pool
