"""Chapitre 14 — Proportionnalité et grandeurs composées (générateurs).

    quatrieme_proportionnelle  N1  n objets coûtent P € : prix de m objets
    appliquer_pourcentage      N1  t % d'une quantité, hausse ou baisse
    calculer_pourcentage       N1  part / total en pourcentage
    echelle                    N1  distance sur une carte -> distance réelle
    tableau_proportionnel      N2  tableau de proportionnalité ou non
    vitesse_distance_duree     N3  d = v × t avec des durées en h et min
    convertir_vitesse          N4  km/h <-> m/s
    debit_duree                N4  volume et débit -> durée, ou conversion de débit
"""
import random
from decimal import Decimal
from fractions import Fraction
from typing import Optional

from ._commun import Chapter, Family, frac, grp

N1 = "Calculer une quatrième proportionnelle"
N2 = "Reconnaître une situation de proportionnalité"
N3 = "Utiliser une formule de proportionnalité"
N4 = "Grandeurs composées : vitesses et débits"

# (pluriel, singulier avec son article, prix unitaire minimal et maximal en centimes) — prix réalistes.
_OBJETS = (("cahiers", "un cahier", 120, 450), ("croissants", "un croissant", 95, 180), ("stylos", "un stylo", 60, 350),
           ("places de cinéma", "une place", 650, 1350), ("bouteilles d'eau", "une bouteille", 40, 150),
           ("tickets de bus", "un ticket", 130, 250), ("pots de peinture", "un pot", 1200, 4500))


def euros(f: Fraction) -> str:
    """Montant en euros : entier, ou deux décimales (« 12{,}50 »)."""
    if f.denominator == 1:
        return grp(f.numerator)
    centimes = f * 100
    assert centimes.denominator == 1, f"{f} € n'est pas un nombre entier de centimes"
    e, c = divmod(centimes.numerator, 100)
    return f"{grp(e)}{{,}}{c:02d}"


def _dec(f: Fraction) -> Decimal:
    q = f.denominator
    for p in (2, 5):
        while q % p == 0:
            q //= p
    assert q == 1, f"{f} non décimal"
    return Decimal(f.numerator) / Decimal(f.denominator)


def _gen_quatrieme(rng: random.Random) -> Optional[dict]:
    plur, sing, lo, hi = rng.choice(_OBJETS)
    unit = Fraction(rng.randint(lo // 5, hi // 5) * 5, 100)     # prix unitaire au multiple de 0,05 €
    n, m = rng.sample(range(2, 16), 2)
    pn, pm = unit * n, unit * m
    return {
        "enonce": f"${n}$ {plur} identiques coûtent ${euros(pn)}$ €. Combien coûtent ${m}$ {plur} ?",
        "answer": f"${m}$ {plur} coûtent ${euros(pm)}$ €.",
        "hint": f"Calcule d'abord le prix d'{sing}.",
        "steps": [f"Prix d'{sing} : ${euros(pn)} \\div {n} = {euros(unit)}$ €.",
                  f"Prix de ${m}$ {plur} : ${m} \\times {euros(unit)} = {euros(pm)}$ €."],
        "notion": N1,
    }


def _gen_appliquer_pourcentage(rng: random.Random) -> Optional[dict]:
    t = rng.choice((5, 10, 15, 20, 25, 30, 40, 50, 60, 75))
    q = rng.randint(4, 120) * 5
    part = Fraction(t * q, 100)
    genre = rng.choice(("part", "hausse", "baisse"))
    if genre == "part":
        return {
            "enonce": f"Calculer ${t}\\,\\%$ de ${grp(q)}$.",
            "answer": f"${t}\\,\\%$ de ${grp(q)}$ valent ${grp(_dec(part))}$.",
            "hint": f"Multiplie par $\\dfrac{{{t}}}{{100}}$.",
            "steps": [f"$\\dfrac{{{t}}}{{100}} \\times {grp(q)} = {grp(_dec(part))}$."],
            "notion": N1,
        }
    final = q + part if genre == "hausse" else q - part
    coef = Fraction(100 + t, 100) if genre == "hausse" else Fraction(100 - t, 100)
    mot = "augmente" if genre == "hausse" else "baisse"
    return {
        "enonce": f"Un prix de ${grp(q)}$ € {mot} de ${t}\\,\\%$. Quel est le nouveau prix ?",
        "answer": f"Le nouveau prix est ${euros(final)}$ €.",
        "hint": "Calcule la variation, puis ajoute-la ou retire-la ; ou multiplie par le coefficient.",
        "steps": [f"Variation : $\\dfrac{{{t}}}{{100}} \\times {grp(q)} = {euros(part)}$ €.",
                  f"Nouveau prix : ${grp(q)} {'+' if genre == 'hausse' else '-'} {euros(part)} = {euros(final)}$ € "
                  f"(soit ${grp(q)} \\times {grp(_dec(coef))}$)."],
        "notion": N1,
    }


def _gen_calculer_pourcentage(rng: random.Random) -> Optional[dict]:
    total = rng.choice((20, 25, 40, 50, 80, 125, 200, 250, 400, 500, 800))
    part = rng.randint(1, total - 1)
    p = Fraction(part * 100, total)
    if p.denominator not in (1, 2, 4, 5, 10):
        return None
    contexte = rng.choice((("élèves d'un collège", "pratiquent un sport"), ("spectateurs", "ont moins de 18 ans"),
                           ("arbres d'un parc", "sont des chênes"), ("adhérents d'un club", "sont venus à la réunion")))
    return {
        "enonce": f"Parmi ${grp(total)}$ {contexte[0]}, ${grp(part)}$ {contexte[1]}. Quel pourcentage cela représente-t-il ?",
        "answer": f"Cela représente ${grp(_dec(p))}\\,\\%$.",
        "hint": "Calcule la proportion, puis multiplie par $100$.",
        "steps": [f"Proportion : $\\dfrac{{{part}}}{{{total}}} = {grp(_dec(Fraction(part, total)))}$.",
                  f"En pourcentage : ${grp(_dec(Fraction(part, total)))} \\times 100 = {grp(_dec(p))}$, soit ${grp(_dec(p))}\\,\\%$."],
        "notion": N1,
    }


def _gen_echelle(rng: random.Random) -> Optional[dict]:
    e = rng.choice((10_000, 20_000, 25_000, 50_000, 100_000, 200_000, 250_000, 1_000_000))
    d = Fraction(rng.randint(5, 150), 10)                 # cm sur la carte
    reel_cm = d * e
    km = reel_cm / 100_000
    return {
        "enonce": f"Sur une carte à l'échelle $\\dfrac{{1}}{{{grp(e)}}}$, deux points sont distants de ${grp(_dec(d))}$ cm. Quelle est la distance réelle, en km ?",
        "answer": f"La distance réelle est ${grp(_dec(km))}$ km.",
        "hint": f"$1$ cm sur la carte représente ${grp(e)}$ cm en réalité.",
        "steps": [f"Distance réelle : ${grp(_dec(d))} \\times {grp(e)} = {grp(_dec(reel_cm))}$ cm.",
                  f"$1$ km $= 100\\,000$ cm : ${grp(_dec(reel_cm))}$ cm $= {grp(_dec(km))}$ km."],
        "notion": N1,
    }


def _gen_tableau(rng: random.Random) -> Optional[dict]:
    k = Fraction(rng.randint(3, 60), 4)
    xs = sorted(rng.sample(range(1, 13), 3))
    ys = [k * x for x in xs]
    proportionnel = rng.random() < 0.5
    if not proportionnel:
        i = rng.randrange(3)
        ys[i] += rng.choice((-1, 1)) * Fraction(rng.randint(1, 4), 2)
        if ys[i] <= 0:
            return None
    cols = " ; ".join(f"${x} \\to {grp(_dec(y))}$" for x, y in zip(xs, ys))
    qs = [y / x for x, y in zip(xs, ys)]
    qtxt = " ; ".join(f"$\\dfrac{{{grp(_dec(y))}}}{{{x}}} {('= ' + grp(_dec(q))) if _is_dec(q) else _approx(q)}$" for x, y, q in zip(xs, ys, qs))
    if proportionnel:
        answer = f"Oui : tous les quotients valent ${grp(_dec(k))}$, c'est le coefficient de proportionnalité."
        concl = "Les quotients sont égaux : c'est un tableau de proportionnalité."
    else:
        answer = "Non : les quotients ne sont pas tous égaux."
        concl = "Les quotients ne sont pas tous égaux : ce n'est pas un tableau de proportionnalité."
    return {
        "enonce": f"Le tableau suivant est-il un tableau de proportionnalité ? {cols}.",
        "answer": answer,
        "hint": "Calcule le quotient de chaque colonne.",
        "steps": [f"Quotients : {qtxt}.", concl],
        "notion": N2,
    }


def _is_dec(f: Fraction) -> bool:
    q = f.denominator
    for p in (2, 5):
        while q % p == 0:
            q //= p
    return q == 1


def _approx(f: Fraction) -> str:
    return "\\approx " + grp((Decimal(f.numerator) / Decimal(f.denominator)).quantize(Decimal("0.01")))


def _hmin(minutes: int) -> str:
    h, m = divmod(minutes, 60)
    if h and m:
        return f"${h}$ h ${m}$ min"
    return f"${h}$ h" if h else f"${m}$ min"


def _gen_vitesse(rng: random.Random) -> Optional[dict]:
    v = rng.choice((4, 5, 6, 12, 15, 18, 20, 24, 30, 36, 40, 45, 48, 50, 60, 72, 75, 80, 90, 100, 110, 120, 130))
    minutes = rng.choice((15, 20, 30, 40, 45, 50, 75, 80, 90, 100, 105, 120, 135, 150, 160, 180, 200, 210, 240))
    t = Fraction(minutes, 60)
    d = v * t
    if not _is_dec(d):
        return None
    th = grp(_dec(t)) if _is_dec(t) else frac(t)  # durée en heures : 3{,}5 ou \dfrac{1}{3}
    cherche = rng.choice(("d", "v", "t"))
    if cherche == "d":
        enonce = f"Un véhicule roule à ${v}$ km/h pendant {_hmin(minutes)}. Quelle distance parcourt-il ?"
        answer = f"Il parcourt ${grp(_dec(d))}$ km."
        steps = [f"Durée : {_hmin(minutes)} $= \\dfrac{{{minutes}}}{{60}}$ h $= {th}$ h.", f"$d = v \\times t = {v} \\times {th} = {grp(_dec(d))}$ km."]
    elif cherche == "v":
        enonce = f"Un véhicule parcourt ${grp(_dec(d))}$ km en {_hmin(minutes)}. Quelle est sa vitesse moyenne, en km/h ?"
        answer = f"Sa vitesse moyenne est ${v}$ km/h."
        steps = [f"Durée : {_hmin(minutes)} $= \\dfrac{{{minutes}}}{{60}}$ h $= {th}$ h.", f"$v = \\dfrac{{d}}{{t}} = {grp(_dec(d))} \\div {th} = {v}$ km/h."]
    else:
        enonce = f"Un véhicule roule à ${v}$ km/h. Combien de temps lui faut-il pour parcourir ${grp(_dec(d))}$ km ? Donner la réponse en heures et minutes."
        answer = f"Il lui faut {_hmin(minutes)}."
        steps = [f"$t = \\dfrac{{d}}{{v}} = \\dfrac{{{grp(_dec(d))}}}{{{v}}}$ h $= {th}$ h.", f"${th}$ h $= \\dfrac{{{minutes}}}{{60}}$ h, soit {_hmin(minutes)}."]
    return {"enonce": enonce, "answer": answer, "hint": "Utilise $d = v \\times t$ avec une durée en heures.", "steps": steps, "notion": N3}


def _gen_convertir_vitesse(rng: random.Random) -> Optional[dict]:
    ms = Fraction(rng.randint(1, 80) * 5, 10)             # m/s, multiple de 0,5
    kmh = ms * Fraction(18, 5)                             # × 3,6
    if rng.random() < 0.5:
        return {
            "enonce": f"Convertir ${grp(_dec(kmh))}$ km/h en m/s.",
            "answer": f"${grp(_dec(kmh))}$ km/h $= {grp(_dec(ms))}$ m/s.",
            "hint": "$1$ km $= 1\\,000$ m et $1$ h $= 3\\,600$ s : on divise par $3{,}6$.",
            "steps": [f"${grp(_dec(kmh))}$ km/h $= \\dfrac{{{grp(_dec(kmh * 1000))} \\text{{ m}}}}{{3\\,600 \\text{{ s}}}}$.",
                      f"${grp(_dec(kmh))} \\div 3{{,}}6 = {grp(_dec(ms))}$ m/s."],
            "notion": N4,
        }
    return {
        "enonce": f"Convertir ${grp(_dec(ms))}$ m/s en km/h.",
        "answer": f"${grp(_dec(ms))}$ m/s $= {grp(_dec(kmh))}$ km/h.",
        "hint": "En une heure, il y a $3\\,600$ secondes : on multiplie par $3{,}6$.",
        "steps": [f"En $3\\,600$ s : ${grp(_dec(ms))} \\times 3\\,600 = {grp(_dec(ms * 3600))}$ m $= {grp(_dec(kmh))}$ km.",
                  f"${grp(_dec(ms))}$ m/s $= {grp(_dec(kmh))}$ km/h."],
        "notion": N4,
    }


def _gen_debit(rng: random.Random) -> Optional[dict]:
    if rng.random() < 0.5:
        q = rng.choice((5, 6, 8, 10, 12, 15, 20, 24, 25, 30, 40, 50, 60))        # L/min
        minutes = rng.randint(2, 90) * 5
        volume = q * minutes
        if volume % 1000 == 0:
            vtxt, conv = f"${grp(volume // 1000)}$ m³", f"${grp(volume // 1000)}$ m³ $= {grp(volume)}$ L."
        else:
            vtxt, conv = f"${grp(volume)}$ L", f"Volume : ${grp(volume)}$ L."
        return {
            "enonce": f"Un réservoir de {vtxt} est rempli avec un débit de ${q}$ L/min. Combien de temps faut-il pour le remplir ? Donner la réponse en heures et minutes.",
            "answer": f"Il faut {_hmin(minutes)}.",
            "hint": "Durée = volume ÷ débit, avec le volume en litres.",
            "steps": [conv, f"$t = \\dfrac{{{grp(volume)}}}{{{q}}} = {minutes}$ min."]
                     + ([f"${minutes}$ min $=$ {_hmin(minutes)}."] if minutes >= 60 else []),
            "notion": N4,
        }
    q = rng.randint(2, 120) * 5                        # L/min
    m3h = Fraction(q * 60, 1000)
    return {
        "enonce": f"Convertir un débit de ${q}$ L/min en m³/h.",
        "answer": f"${q}$ L/min $= {grp(_dec(m3h))}$ m³/h.",
        "hint": "En une heure, il s'écoule $60$ fois plus ; $1$ m³ $= 1\\,000$ L.",
        "steps": [f"En une heure : ${q} \\times 60 = {grp(q * 60)}$ L.", f"${grp(q * 60)}$ L $= {grp(_dec(m3h))}$ m³ : débit ${grp(_dec(m3h))}$ m³/h."],
        "notion": N4,
    }


FAMILIES_LIST = (
    Family("quatrieme_proportionnelle", 1, "Quatrième proportionnelle", N1, _gen_quatrieme,
           "un prix pour n objets", "passage à l'unité"),
    Family("appliquer_pourcentage", 1, "Appliquer un pourcentage", N1, _gen_appliquer_pourcentage,
           "une part, une hausse ou une baisse", "multiplier par t/100"),
    Family("calculer_pourcentage", 2, "Calculer un pourcentage", N1, _gen_calculer_pourcentage,
           "une part d'un effectif", "proportion × 100"),
    Family("echelle", 2, "Utiliser une échelle", N1, _gen_echelle,
           "une distance sur une carte", "coefficient d'échelle"),
    Family("tableau_proportionnel", 1, "Reconnaître un tableau de proportionnalité", N2, _gen_tableau,
           "un tableau de trois colonnes", "quotients égaux"),
    Family("vitesse_distance_duree", 2, "Distance, vitesse, durée", N3, _gen_vitesse,
           "un trajet à vitesse constante", "d = v × t"),
    Family("convertir_vitesse", 1, "Convertir une vitesse", N4, _gen_convertir_vitesse,
           "une vitesse en km/h ou en m/s", "diviser ou multiplier par 3,6"),
    Family("debit_duree", 2, "Débits", N4, _gen_debit,
           "un débit et un volume", "convertir puis diviser"),
)

CHAPTER = Chapter(14, FAMILIES_LIST)
CHAPTER_ID = CHAPTER.chapter_id
FAMILIES = CHAPTER.families
GENERATED_ID_OFFSET = CHAPTER.id_offset
generate_one = CHAPTER.generate_one
generate_pool = CHAPTER.generate_pool
