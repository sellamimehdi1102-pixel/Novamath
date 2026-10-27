"""Vérificateurs INDÉPENDANTS des générateurs de Quatrième (hors Pythagore,
vérifié dans test_quatrieme_pythagore.py).

Chaque vérificateur relit les données dans l'ÉNONCÉ (expressions
régulières), refait le calcul en arithmétique exacte (fractions.Fraction)
avec sa propre mise en forme des nombres, et compare à la réponse annoncée.
Aucun code n'est partagé avec les générateurs : une erreur de logique dans
un générateur ne peut pas se reproduire à l'identique ici.

CHECKERS[family_id](exercice) lève AssertionError en cas d'incohérence.
"""
import re
from fractions import Fraction

NUM = r"-?\d+(?:\{,\}\d+)?"


def F(text: str) -> Fraction:
    return Fraction(text.replace("{,}", ".").replace("(", "").replace(")", "").strip())


def fmt(x) -> str:
    """Écriture française d'un décimal exact : -2{,}5."""
    x = Fraction(x)
    neg = x < 0
    x = abs(x)
    whole, rest = divmod(x.numerator, x.denominator)
    digits = ""
    seen = 0
    while rest and seen < 12:
        rest *= 10
        digits += str(rest // x.denominator)
        rest %= x.denominator
        seen += 1
    assert rest == 0, f"{x} n'est pas un décimal"
    s = str(whole) + ("{,}" + digits if digits else "")
    return ("-" if neg and s != "0" else "") + s


def maths(text: str) -> list[str]:
    return re.findall(r"\$([^$]*)\$", text)


def nums(text: str) -> list[Fraction]:
    return [F(m) for m in re.findall(NUM, text)]


def factors(expr: str) -> list[Fraction]:
    return [F(part) for part in expr.split("\\times")]


def need(cond, msg):
    if not cond:
        raise AssertionError(msg)


# ── Chapitre 1 — Nombres relatifs ───────────────────────────────────────────


def _produit_deux(ex):
    a, b = factors(maths(ex["enonce"])[0])
    need(f"= {fmt(a * b)}$" in ex["answer"], f"produit attendu {fmt(a * b)}")


def _facteur_manquant(ex):
    a, p = nums(ex["enonce"])
    x = p / a
    need(f"par ${fmt(x)}$" in ex["answer"], f"facteur attendu {fmt(x)}")
    need(x * a == p, "vérification")


def _signe_produit(ex):
    fs = factors(maths(ex["enonce"])[0].split("=", 1)[1])
    neg = sum(1 for f in fs if f < 0)
    attendu = "positif" if neg % 2 == 0 else "négatif"
    need(attendu in ex["answer"], f"signe attendu {attendu} ({neg} facteurs négatifs)")
    need(4 <= len(fs) <= 7 and all(f != 0 for f in fs), "facteurs")


def _produit_plusieurs(ex):
    fs = factors(maths(ex["enonce"])[0].split("=", 1)[1])
    p = Fraction(1)
    for f in fs:
        p *= f
    need(ex["answer"] == f"$Q = {fmt(p)}$", f"produit attendu {fmt(p)}")


def _quotient(ex):
    a, b = (F(x) for x in maths(ex["enonce"])[0].split("\\div"))
    need(b != 0, "division par zéro")
    need(f"= {fmt(a / b)}$" in ex["answer"], f"quotient attendu {fmt(a / b)}")


def _variation_moyenne(ex):
    m = re.search(rf"passée de \$({NUM})\$ °C à \$({NUM})\$ °C en \$(\d+)\$ heures", ex["enonce"])
    need(m, "énoncé illisible")
    debut, fin, h = F(m.group(1)), F(m.group(2)), int(m.group(3))
    need(f"${fmt((fin - debut) / h)}$ °C par heure" in ex["answer"], "variation horaire")


def _priorites(ex):
    m = re.fullmatch(rf"Calculer \$A = ({NUM}) \+ \(?({NUM})\)? \\times \(({NUM}) - \(?({NUM})\)?\)\$\.", ex["enonce"])
    need(m, "énoncé illisible")
    a, b, c, d = (F(g) for g in m.groups())
    need(ex["answer"] == f"$A = {fmt(a + b * (c - d))}$", "valeur de A")


def _substitution(ex):
    m = re.fullmatch(rf"Calculer \$E = ({NUM})x\^2 ([+-]) (\d+)x ([+-]) (\d+)\$ pour \$x = ({NUM})\$\.", ex["enonce"])
    need(m, "énoncé illisible")
    a = F(m.group(1))
    b = F(m.group(3)) * (1 if m.group(2) == "+" else -1)
    c = F(m.group(5)) * (1 if m.group(4) == "+" else -1)
    x = F(m.group(6))
    need(x < 0, "x doit être négatif")
    need(ex["answer"] == f"$E = {fmt(a * x * x + b * x + c)}$", "valeur de E")


# ── Chapitre 2 — Fractions : comparer, additionner, soustraire ──────────────
FRAC = r"(-?)\\dfrac\{(-?\d+)\}\{(-?\d+)\}"


def fracs(text: str) -> list[Fraction]:
    out = []
    for sign, n, d in re.findall(FRAC, text):
        v = Fraction(int(n), int(d))
        out.append(-v if sign else v)
    return out


def ffmt(x) -> str:
    """Écriture irréductible attendue : entier, ou ±\\dfrac{p}{q} avec q > 0."""
    x = Fraction(x)
    if x.denominator == 1:
        return str(x.numerator)
    return ("-" if x < 0 else "") + f"\\dfrac{{{abs(x.numerator)}}}{{{x.denominator}}}"


def _simplifier(ex):
    (v,) = fracs(maths(ex["enonce"])[0])
    need(ex["answer"].endswith(f"= {ffmt(v)}$"), f"forme irréductible attendue {ffmt(v)}")


def _completer_egalite(ex):
    m = re.search(r"\\dfrac\{(\d+)\}\{(\d+)\} = \\dfrac\{(\d+|\\ldots)\}\{(\d+|\\ldots)\}", ex["enonce"])
    need(m, "énoncé illisible")
    n, d = int(m.group(1)), int(m.group(2))
    if m.group(3) == "\\ldots":
        dd = int(m.group(4))
        need(dd % d == 0, "dénominateur non multiple")
        nn = n * dd // d
    else:
        nn = int(m.group(3))
        need(nn % n == 0, "numérateur non multiple")
        dd = d * nn // n
    need(Fraction(nn, dd) == Fraction(n, d), "égalité fausse")
    need(f"\\dfrac{{{nn}}}{{{dd}}}$" in ex["answer"], f"attendu {nn}/{dd}")


def _comparer_deux(ex):
    a, b = fracs(ex["enonce"])
    s = "<" if a < b else (">" if a > b else "=")
    need(ex["answer"] == f"${ffmt(a)} {s} {ffmt(b)}$", f"symbole attendu {s}")


def _encadrer(ex):
    (v,) = fracs(ex["enonce"])
    low = v.numerator // v.denominator  # partie entière inférieure (floor)
    need(v.denominator != 1, "fraction entière")
    need(ex["answer"].startswith(f"${low} <") and ex["answer"].endswith(f"< {low + 1}$"), f"encadrement attendu {low} ; {low + 1}")


def _ranger_trois(ex):
    vals = fracs(ex["enonce"])
    ordre = sorted(vals)
    need(len(vals) == 3 and len(set(vals)) == 3, "trois nombres distincts")
    need(ex["answer"] == "$" + " < ".join(ffmt(v) for v in ordre) + "$", "ordre faux")


def _somme(ex):
    m = re.search(r"\$(-?\\dfrac\{\d+\}\{\d+\}) ([+-]) (\\dfrac\{\d+\}\{\d+\})\$", ex["enonce"])
    need(m, "énoncé illisible")
    (a,), (c,) = fracs(m.group(1)), fracs(m.group(3))
    res = a + c if m.group(2) == "+" else a - c
    need(ex["answer"].endswith(f"= {ffmt(res)}$"), f"résultat attendu {ffmt(res)}")


def _part_restante(ex):
    parts = fracs(ex["enonce"])
    need(len(parts) == 2 and all(0 < p < 1 for p in parts) and sum(parts) < 1, "parts incohérentes")
    need(ex["answer"].startswith(f"${ffmt(1 - sum(parts))}$"), f"reste attendu {ffmt(1 - sum(parts))}")


# ── Chapitre 3 — Fractions : multiplier et diviser ──────────────────────────


def _produit_fractions(ex):
    a, b = fracs(ex["enonce"])
    need(ex["answer"] == f"Le produit vaut ${ffmt(a * b)}$.", f"produit attendu {ffmt(a * b)}")


def _fraction_quantite(ex):
    (p,) = fracs(ex["enonce"])
    q = [int(x) for x in re.findall(r"\$(\d+)\$", ex["enonce"])]
    need(len(q) == 1, "quantité illisible")
    res = p * q[0]
    need(res.denominator == 1 and f"${res.numerator}$" in ex["answer"], f"résultat attendu {res}")


def _inverse_nombre(ex):
    m = re.search(r"l'inverse de \$([^$]*)\$", ex["enonce"])
    need(m, "énoncé illisible")
    expr = m.group(1)
    vals = fracs(expr)
    v = vals[0] if vals else Fraction(int(expr))
    need(v != 0, "zéro n'a pas d'inverse")
    need(ex["answer"].endswith(f"est ${ffmt(1 / v)}$."), f"inverse attendu {ffmt(1 / v)}")


def _quotient_fractions(ex):
    a, b = fracs(ex["enonce"])
    need(ex["answer"].endswith(f"= {ffmt(a / b)}$"), f"quotient attendu {ffmt(a / b)}")


def _combien_de_fois(ex):
    (p,) = fracs(ex["enonce"])
    total = [int(x) for x in re.findall(r"\$(\d+)\$", ex["enonce"])]
    need(len(total) == 1, "quantité illisible")
    k = total[0] / p
    need(k.denominator == 1 and f"${k.numerator}$" in ex["answer"], f"nombre attendu {k}")


def _priorites_fractions(ex):
    m = re.search(rf"\$A = ({FRAC.replace('(', '(?:')}) ([+-]) (\\dfrac\{{\d+\}}\{{\d+\}}) \\times (\\dfrac\{{\d+\}}\{{\d+\}})\$", ex["enonce"])
    need(m, "énoncé illisible")
    (a,), (b,), (c,) = fracs(m.group(1)), fracs(m.group(3)), fracs(m.group(4))
    res = a + b * c if m.group(2) == "+" else a - b * c
    need(ex["answer"] == f"$A = {ffmt(res)}$", f"résultat attendu {ffmt(res)}")


def _fraction_du_reste(ex):
    p, q = fracs(ex["enonce"])
    need(0 < p < 1 and 0 < q < 1, "fractions hors de ]0 ; 1[")
    need(ex["answer"].startswith(f"Il lui reste ${ffmt((1 - p) * (1 - q))}$"), "reste final")


def _retrouver_tout(ex):
    p, q = fracs(ex["enonce"])
    reste = int(re.search(r"reste alors \$(\d+)\$ km", ex["enonce"]).group(1))
    total = reste / ((1 - p) * (1 - q))
    need(total.denominator == 1 and ex["answer"] == f"Le trajet mesure ${total.numerator}$ km.", f"total attendu {total}")


# ── Chapitre 4 — Divisibilité et nombres premiers ───────────────────────────


def ints(text: str) -> list[int]:
    return [int(x.replace("\\,", "")) for x in re.findall(r"\d+(?:\\,\d{3})*", text)]


def _premier(n: int) -> bool:
    return n >= 2 and all(n % d for d in range(2, int(n ** 0.5) + 1))


def _decomposition(n: int) -> list[int]:
    out, d = [], 2
    while n > 1:
        while n % d == 0:
            out.append(d)
            n //= d
        d += 1
    return out


def _critere_divisibilite(ex):
    n, k = ints(maths(ex["enonce"])[0])[0], ints(maths(ex["enonce"])[1])[0]
    need(ex["answer"].startswith("Oui" if n % k == 0 else "Non"), f"{n} divisible par {k} : {n % k == 0}")


def _liste_diviseurs(ex):
    n = ints(ex["enonce"])[0]
    divs = [d for d in range(1, n + 1) if n % d == 0]
    need(ex["answer"] == f"Diviseurs de ${n}$ : $" + ", ".join(map(str, divs)) + "$.", "liste des diviseurs")


def _est_premier(ex):
    n = ints(ex["enonce"])[0]
    if _premier(n):
        need(ex["answer"].startswith("Oui"), f"{n} est premier")
    else:
        m = re.search(r"\$(\d+) = (\d+) \\times (\d+)\$", ex["answer"])
        need(ex["answer"].startswith("Non") and m and int(m.group(2)) * int(m.group(3)) == n and int(m.group(2)) > 1, "diviseur annoncé")


def _reconstituer(ex):
    fs = ints(maths(ex["enonce"])[0])
    n = 1
    for p in fs:
        need(_premier(p), "facteur non premier")
        n *= p
    need(ints(maths(ex["answer"])[0]) == [n], f"produit attendu {n}")


def _decomposer(ex):
    n = ints(maths(ex["enonce"])[0])[0]
    m = re.fullmatch(r"\$[\d\\,]+ = ([\d \\times]+)\$", ex["answer"])
    need(m, "réponse illisible")
    need([int(x) for x in m.group(1).split("\\times")] == _decomposition(n), "décomposition fausse")


def _simplifier_premiers(ex):
    (v,) = fracs(ex["enonce"])
    a, b = (int(x) for x in re.search(r"= \\dfrac\{(\d+)\}\{(\d+)\}\$$", ex["answer"]).groups())
    need(Fraction(a, b) == v and Fraction(a, b).denominator == b, "fraction irréductible attendue")


def _lots_identiques(ex):
    a, b = ints(ex["enonce"])[:2]
    from math import gcd as _g
    g = _g(a, b)
    need(f"${g}$" in ex["answer"] and f"${a // g}$" in ex["answer"] and f"${b // g}$" in ex["answer"], f"{g} lots attendus")


def _rendez_vous(ex):
    p, q = ints(ex["enonce"])[:2]
    from math import gcd as _g
    m = p * q // _g(p, q)
    need(ex["answer"] == f"Au bout de ${m}$ secondes.", f"plus petit multiple commun {m}")


# ── Chapitre 5 — Puissances ─────────────────────────────────────────────────

PREF = {"G": 9, "M": 6, "k": 3, "": 0, "m": -3, "µ": -6, "n": -9}


def D(text: str) -> Fraction:
    """« 1\\,234{,}5 » -> Fraction exacte (espaces fines ignorées)."""
    return F(text.replace("\\,", "").replace(" ", ""))


def SCI(text: str) -> Fraction:
    m, e = re.fullmatch(r"\s*(-?[\d{},]+) \\times 10\^\{(-?\d+)\}\s*", text).groups()
    return D(m) * Fraction(10) ** int(e)


def is_sci(text: str) -> bool:
    m = re.fullmatch(r"\s*([\d{},]+) \\times 10\^\{(-?\d+)\}\s*", text)
    return bool(m) and 1 <= D(m.group(1)) < 10


def _calculer_puissance(ex):
    expr = maths(ex["enonce"])[0].split("=", 1)[1].strip()
    m = re.fullmatch(r"(\(-\d+\)|-?[\d{},]+)\^\{(\d+)\}", expr)
    need(m, f"énoncé illisible {expr}")
    base, n = m.group(1), int(m.group(2))
    if base.startswith("-") and not base.startswith("("):
        val = -(F(base[1:]) ** n)          # -a^n : l'exposant ne porte que sur a
    else:
        val = F(base) ** n
    need(D(maths(ex["answer"])[0].split("=", 1)[1]) == val, f"valeur attendue {fmt(val)}")


def _ecrire_puissance(ex):
    produit = maths(ex["enonce"])[0]
    fs = [f.strip() for f in produit.split("\\times")]
    need(len(set(fs)) == 1, "facteurs différents")
    need(ex["answer"].endswith(f"= {fs[0]}^{{{len(fs)}}}$"), f"puissance attendue {fs[0]}^{len(fs)}")


def VAL(text: str) -> Fraction:
    """« 10^{e} », « a \\times 10^{e} » (a quelconque) ou un décimal."""
    text = text.strip()
    m = re.fullmatch(r"(?:([\d{},\\]+) \\times )?10\^\{(-?\d+)\}", text)
    if m:
        return (D(m.group(1)) if m.group(1) else 1) * Fraction(10) ** int(m.group(2))
    return D(text)


def _puissance10_decimal(ex):
    donne = maths(ex["enonce"])[0]
    gauche, droite = maths(ex["answer"])[0].split("=")
    need(gauche.strip() == donne.strip(), "expression recopiée")
    need("10^" in donne or re.fullmatch(r"10\^\{-?\d+\}", droite.strip()), "puissance de 10 attendue")
    need(VAL(gauche) == VAL(droite), f"{gauche} ≠ {droite}")


def _produit_puissances10(ex):
    a, b, c = (int(x) for x in re.findall(r"10\^\{(-?\d+)\}", ex["enonce"]))
    val = Fraction(10) ** a * Fraction(10) ** b / Fraction(10) ** c
    r = int(re.fullmatch(r"\$B = 10\^\{(-?\d+)\}\$", ex["answer"]).group(1))
    need(Fraction(10) ** r == val, f"exposant attendu {a + b - c}")


def _vers_scientifique(ex):
    x = D(maths(ex["enonce"])[0])
    gauche, droite = maths(ex["answer"])[0].split("=")
    need(D(gauche) == x, "nombre recopié")
    need(is_sci(droite), "pas une écriture scientifique")
    need(SCI(droite) == x, "valeur différente")


def _depuis_scientifique(ex):
    s = maths(ex["enonce"])[0]
    need(is_sci(s), "énoncé non scientifique")
    need(D(maths(ex["answer"])[0].split("=")[1]) == SCI(s), "valeur décimale")


def _comparer_scientifique(ex):
    a, b = (SCI(m.split("=")[1]) for m in maths(ex["enonce"])[:2])
    attendu = "<" if a < b else ">"
    need(a != b and ex["answer"] == f"$a {attendu} b$", f"attendu a {attendu} b")


def _conversion_prefixe(ex):
    m = re.fullmatch(r"Convertir \$([\d{},]+)\$ (\S*?)(m|g|W|L|o) en (\S*?)(m|g|W|L|o)\. .*", ex["enonce"])
    need(m, "énoncé illisible")
    x, p1, u1, p2, u2 = m.groups()
    need(u1 == u2 and p1 in PREF and p2 in PREF, "unités")
    val = F(x) * Fraction(10) ** (PREF[p1] - PREF[p2])
    res = maths(ex["answer"])[1].lstrip("= ")
    need(is_sci(res) and SCI(res) == val, f"conversion attendue {val}")


# ── Chapitre 6 — Calcul littéral ────────────────────────────────────────────

VALEURS = (Fraction(-3), Fraction(-1), Fraction(0), Fraction(1), Fraction(2), Fraction(5), Fraction(7, 3))


def EV(expr: str):
    """Expression en x écrite à la française (3x^2 - 2(x + 1)) -> fonction exacte."""
    s = expr.replace("\\times", "*").replace(" ", "")
    s = re.sub(r"(\d)(x|\()", r"\1*\2", s)
    s = re.sub(r"(x|\))(\(|x)", r"\1*\2", s)
    s = s.replace("^", "**")
    need(re.fullmatch(r"[\dx+\-*()]+", s), f"expression illisible {expr}")
    return lambda v: eval(s, {"__builtins__": {}}, {"x": v})


def egales(e1: str, e2: str) -> bool:
    f, g = EV(e1), EV(e2)
    return all(f(v) == g(v) for v in VALEURS)


def apres_egal(text: str) -> str:
    return text.split("=", 1)[1].strip()


# Forme réduite d'une expression du premier degré : « ax + b », « ax », « b ».
REDUITE = re.compile(r"-?\d*x(?: [+-] \d+)?|-?\d+")


def _substituer(ex):
    m = re.fullmatch(r"Calculer \$A = (.+)\$ pour \$x = (-?\d+)\$\.", ex["enonce"])
    need(m, "énoncé illisible")
    v = Fraction(int(m.group(2)))
    r = EV(m.group(1))(v)
    need(ex["answer"] == f"$A = {fmt(r)}$", f"valeur attendue {fmt(r)}")
    need(f"$A = {fmt(r)}$." in ex["solution_steps"][-1], "dernière étape")
    if v < 0:
        need(f"({fmt(v)})" in ex["solution_steps"][0], "valeur négative sans parenthèses")


def _traduire_programme(ex):
    t = ex["enonce"]
    n = [int(v) for v in re.findall(r"\$(\d+)\$", t)]
    need(len(n) == 2 and "Contrôler avec $x = 1$" in t, "données du programme")
    if "lui ajouter" in t:
        f = lambda x: (x + n[0]) * n[1]
    elif "lui soustraire" in t:
        f = lambda x: (x - n[0]) * n[1]
    elif "puis ajouter" in t:
        f = lambda x: x * n[0] + n[1]
    else:
        need("puis soustraire" in t, "programme inconnu")
        f = lambda x: x * n[0] - n[1]
    expr = maths(ex["answer"])[0]
    g = EV(expr)
    need(all(f(v) == g(v) for v in VALEURS), f"traduction fausse {expr}")
    need(f"on obtient ${fmt(f(1))}$" in ex["answer"], "contrôle pour x = 1")
    need(("(" in expr) == ("le résultat par" in t), "parenthèses incohérentes avec le programme")


def _forme_reduite(ex):
    depart, res = apres_egal(maths(ex["enonce"])[0]), apres_egal(maths(ex["answer"])[0])
    need(egales(depart, res), f"{depart} ≠ {res}")
    need(REDUITE.fullmatch(res), f"forme non réduite {res}")
    need(not re.search(r"\b0x|\b1x|\+ -|- -", res), f"écriture non conventionnelle {res}")
    for s in ex["solution_steps"]:
        for m in maths(s):
            if m.count("=") == 1 and "(" not in m and "\\times" not in m and "x" in m:
                g, d = (p.strip() for p in m.split("="))
                if g in ("B", "C", "D", "E"):
                    continue
                need(egales(g, d), f"étape fausse : {m}")


def _factoriser(ex):
    from math import gcd
    somme, prod = apres_egal(maths(ex["enonce"])[0]), apres_egal(maths(ex["answer"])[0])
    need(egales(somme, prod), f"{somme} ≠ {prod}")
    m = re.fullmatch(r"(\d+)(x?)\((.+)\)", prod)
    need(m, f"pas un produit {prod}")
    inner = [int(c) for c in re.findall(r"\d+", m.group(3).replace("x^2", "x"))]
    if re.match(r"-?x", m.group(3)):
        inner.append(1)                      # coefficient 1 implicite
    g = 0
    for c in inner:
        g = gcd(g, c)
    need(g == 1 and int(m.group(1)) > 1, f"facteur non maximal {prod}")
    sans_constante = not re.search(r"[+-] \d+$", somme)
    need(bool(m.group(2)) == sans_constante, "la lettre x doit être mise en facteur si elle est commune")


def _tester_egalite(ex):
    m = re.fullmatch(r"L'égalité \$(.+) = (.+)\$ est-elle vraie pour \$x = (-?\d+)\$ \?", ex["enonce"])
    need(m, "énoncé illisible")
    v = Fraction(int(m.group(3)))
    g, d = EV(m.group(1))(v), EV(m.group(2))(v)
    need(not egales(m.group(1), m.group(2)), "égalité vraie pour tout x : test sans intérêt")
    if g == d:
        need(ex["answer"] == f"Oui : les deux membres valent ${fmt(g)}$.", "réponse Oui attendue")
    else:
        need(ex["answer"] == f"Non : le membre de gauche vaut ${fmt(g)}$ et celui de droite ${fmt(d)}$.",
             "réponse Non attendue")


def _programme_constant(ex):
    k, ka, k2 = (int(v) for v in re.findall(r"\$(\d+)\$", ex["enonce"])[:3])
    need(k == k2 and k > 1, "même facteur pour multiplier et diviser")
    res = {(v * k + ka) / k - v for v in VALEURS}
    need(len(res) == 1, "le programme n'est pas constant")
    need(ex["answer"] == f"Le résultat est toujours ${fmt(res.pop())}$.", "valeur constante")


# ── Chapitre 7 — Équations ──────────────────────────────────────────────────


def lire_nombre(text: str) -> Fraction:
    """« -\\dfrac{3}{4} », « 12 » ou « -5 » -> Fraction ; refuse une fraction non irréductible."""
    t = text.strip()
    m = re.fullmatch(r"(-?)\\dfrac\{(\d+)\}\{(\d+)\}", t)
    if m:
        p, q = int(m.group(2)), int(m.group(3))
        need(q > 1 and Fraction(p, q).denominator == q, f"fraction non irréductible {t}")
        return Fraction(-p if m.group(1) else p, q)
    need(re.fullmatch(r"-?\d+", t), f"nombre illisible {t}")
    return Fraction(int(t))


def resoudre_lineaire(gauche: str, droite: str) -> Fraction:
    """Solution unique de gauche = droite (équation du premier degré), en arithmétique exacte."""
    f, g = EV(gauche), EV(droite)
    h = lambda v: f(v) - g(v)
    a, b = h(Fraction(1)) - h(Fraction(0)), h(Fraction(0))
    need(all(h(v) == a * v + b for v in VALEURS), "équation non du premier degré")
    need(a != 0, "pas de solution unique")
    return -b / a


def _tester_solution(ex):
    m = re.fullmatch(r"Le nombre \$(-?\d+)\$ est-il solution de l'équation \$(.+) = (.+)\$ \?", ex["enonce"])
    need(m, "énoncé illisible")
    v = Fraction(int(m.group(1)))
    g, d = EV(m.group(2))(v), EV(m.group(3))(v)
    if g == d:
        need(ex["answer"] == f"Oui : pour $x = {m.group(1)}$, les deux membres valent ${fmt(g)}$.", "réponse Oui attendue")
    else:
        need(ex["answer"] == f"Non : pour $x = {m.group(1)}$, le premier membre vaut ${fmt(g)}$ et le second ${fmt(d)}$.",
             "réponse Non attendue")


def _resoudre_equation(ex):
    m = re.fullmatch(r"Résoudre l'équation \$(.+) = (.+)\$\.", ex["enonce"])
    need(m, "énoncé illisible")
    x = resoudre_lineaire(m.group(1), m.group(2))
    r = re.fullmatch(r"La solution est \$(.+)\$\.", ex["answer"])
    need(r, "réponse illisible")
    need(lire_nombre(r.group(1)) == x, f"solution attendue {x}")
    if ex["family"] == "resoudre_fraction":
        need(x.denominator != 1, "la solution devait être non entière")
    else:
        need(x.denominator == 1, "la solution devait être entière")
    if ex["family"] == "resoudre_parentheses":
        need("(" in m.group(1), "parenthèse attendue")
    if ex["family"] in ("resoudre_deux_membres", "resoudre_parentheses"):
        need("x" in m.group(2), "x attendu dans le second membre")


def _probleme_nombre(ex):
    m = re.fullmatch(r"Je pense à un nombre\. Je le multiplie par \$(\d+)\$, puis (j'ajoute|je retire) \$(\d+)\$ : "
                     r"j'obtiens \$(-?\d+)\$\. Quel est ce nombre \?", ex["enonce"])
    need(m, "énoncé illisible")
    a, b, c = int(m.group(1)), int(m.group(3)), int(m.group(4))
    b = b if m.group(2) == "j'ajoute" else -b
    x = Fraction(c - b, a)
    need(ex["answer"] == f"Le nombre est ${fmt(x)}$.", f"nombre attendu {x}")


def _probleme_tarifs(ex):
    p, f, q = (int(v) for v in re.findall(r"\$(\d+)\$", ex["enonce"])[:3])
    need(p > q, "le tarif A doit être plus cher à l'unité")
    n = Fraction(f, p - q)
    need(n.denominator == 1 and n > 0, "nombre d'entrées non entier")
    need(ex["answer"] == f"Pour ${n}$ entrées (prix commun : ${p * n}$ €).", f"{n} entrées")
    need(p * n == q * n + f, "prix communs")


def _probleme_perimetre(ex):
    t = ex["enonce"]
    a = int(re.search(r"x [+-] (\d+)", t).group(1))
    if "rectangle" in t:
        b = int(re.search(r"cm et \$(\d+)\$ cm", t).group(1))
        x = resoudre_lineaire("4x", f"2(x + {a} + {b})")
        per = 4 * x
    elif t.startswith("Un carré"):
        x = resoudre_lineaire("4x", f"3(x + {a})")
        per = 4 * x
    else:
        x = resoudre_lineaire("3x", f"4(x - {a})")
        per = 3 * x
        need(x - a > 0, "côté du carré positif")
    need(x > 0 and ex["answer"] == f"Pour $x = {fmt(x)}$ cm (périmètre commun : ${fmt(per)}$ cm).", f"x = {x}")


def _probleme_ages(ex):
    pere, fils = (int(v) for v in re.findall(r"\$(\d+)\$", ex["enonce"])[:2])
    k = {"le double": 2, "le triple": 3, "le quadruple": 4}[re.search(r"(le double|le triple|le quadruple)", ex["enonce"]).group(1)]
    n = resoudre_lineaire(f"{pere} + x", f"{k}({fils} + x)")
    need(n.denominator == 1 and n > 0, "durée non entière ou négative")
    need(pere - fils >= 18, "écart d'âge réaliste")
    need(ex["answer"] == f"Dans ${n}$ ans (le père aura ${pere + n}$ ans et le fils ${fils + n}$ ans).", f"{n} ans")


# ── Chapitre 14 — Proportionnalité et grandeurs composées ───────────────────

NB = r"[\d\\,{}]+"   # nombre écrit à la française : 1\,234{,}5


def montant(text: str) -> Fraction:
    """Montant en euros : entier, ou EXACTEMENT deux décimales."""
    v = D(text)
    if v.denominator != 1:
        need(re.fullmatch(r"[\d\\,]+\{,\}\d\d", text), f"montant mal écrit {text}")
    return v


def duree_min(text: str) -> int:
    """« $2$ h $30$ min », « $4$ h » ou « $45$ min » -> minutes."""
    m = re.fullmatch(r"(?:\$(\d+)\$ h)? ?(?:\$(\d+)\$ min)?", text.strip())
    need(m and (m.group(1) or m.group(2)), f"durée illisible {text}")
    h, mi = int(m.group(1) or 0), int(m.group(2) or 0)
    need(mi < 60, "minutes ≥ 60")
    return 60 * h + mi


def _quatrieme_proportionnelle(ex):
    m = re.fullmatch(rf"\$(\d+)\$ (.+) identiques coûtent \$({NB})\$ €\. Combien coûtent \$(\d+)\$ (.+) \?", ex["enonce"])
    need(m and m.group(2) == m.group(5), "énoncé illisible")
    n, total, k = int(m.group(1)), montant(m.group(3)), int(m.group(4))
    unite = total / n
    need(Fraction(2, 5) <= unite <= 45, f"prix unitaire irréaliste {unite}")
    r = re.fullmatch(rf"\$(\d+)\$ (.+) coûtent \$({NB})\$ €\.", ex["answer"])
    need(r and int(r.group(1)) == k, "réponse illisible")
    need(montant(r.group(3)) == unite * k, f"prix attendu {unite * k}")


def _appliquer_pourcentage(ex):
    t = ex["enonce"]
    m = re.fullmatch(rf"Calculer \$(\d+)\\,\\%\$ de \$({NB})\$\.", t)
    if m:
        p, q = int(m.group(1)), D(m.group(2))
        r = re.fullmatch(rf"\$(\d+)\\,\\%\$ de \$({NB})\$ valent \$({NB})\$\.", ex["answer"])
        need(r and D(r.group(3)) == q * p / 100, "part attendue")
        return
    m = re.fullmatch(rf"Un prix de \$({NB})\$ € (augmente|baisse) de \$(\d+)\\,\\%\$\. Quel est le nouveau prix \?", t)
    need(m, "énoncé illisible")
    q, p = D(m.group(1)), int(m.group(3))
    attendu = q * (100 + p) / 100 if m.group(2) == "augmente" else q * (100 - p) / 100
    r = re.fullmatch(rf"Le nouveau prix est \$({NB})\$ €\.", ex["answer"])
    need(r and montant(r.group(1)) == attendu, f"nouveau prix attendu {attendu}")


def _calculer_pourcentage(ex):
    m = re.fullmatch(rf"Parmi \$({NB})\$ .+, \$({NB})\$ .+\. Quel pourcentage cela représente-t-il \?", ex["enonce"])
    need(m, "énoncé illisible")
    total, part = D(m.group(1)), D(m.group(2))
    need(0 < part < total, "part incohérente")
    r = re.fullmatch(rf"Cela représente \$({NB})\\,\\%\$\.", ex["answer"])
    need(r and D(r.group(1)) == part * 100 / total, f"pourcentage attendu {part * 100 / total}")


def _echelle(ex):
    m = re.fullmatch(rf"Sur une carte à l'échelle \$\\dfrac\{{1\}}\{{({NB})\}}\$, deux points sont distants de \$({NB})\$ cm\. "
                     r"Quelle est la distance réelle, en km \?", ex["enonce"])
    need(m, "énoncé illisible")
    e, d = D(m.group(1)), D(m.group(2))
    r = re.fullmatch(rf"La distance réelle est \$({NB})\$ km\.", ex["answer"])
    need(r and D(r.group(1)) == d * e / 100_000, f"distance attendue {d * e / 100_000} km")


def _tableau_proportionnel(ex):
    paires = re.findall(rf"\$(\d+) \\to ({NB})\$", ex["enonce"])
    need(len(paires) == 3, "trois colonnes attendues")
    qs = {D(y) / int(x) for x, y in paires}
    if len(qs) == 1:
        k = qs.pop()
        need(ex["answer"].startswith("Oui") and f"${fmt(k)}$" in ex["answer"], f"Oui, coefficient {fmt(k)}")
    else:
        need(ex["answer"].startswith("Non"), "réponse Non attendue")


def _vitesse_distance_duree(ex):
    t = ex["enonce"]
    m = re.fullmatch(r"Un véhicule roule à \$(\d+)\$ km/h pendant (.+)\. Quelle distance parcourt-il \?", t)
    if m:
        v, mn = int(m.group(1)), duree_min(m.group(2))
        r = re.fullmatch(rf"Il parcourt \$({NB})\$ km\.", ex["answer"])
        need(r and D(r.group(1)) == Fraction(v * mn, 60), "distance attendue")
        return
    m = re.fullmatch(rf"Un véhicule parcourt \$({NB})\$ km en (.+)\. Quelle est sa vitesse moyenne, en km/h \?", t)
    if m:
        d, mn = D(m.group(1)), duree_min(m.group(2))
        r = re.fullmatch(r"Sa vitesse moyenne est \$(\d+)\$ km/h\.", ex["answer"])
        need(r and int(r.group(1)) == d * 60 / mn, "vitesse attendue")
        return
    m = re.fullmatch(rf"Un véhicule roule à \$(\d+)\$ km/h\. Combien de temps lui faut-il pour parcourir \$({NB})\$ km \? "
                     r"Donner la réponse en heures et minutes\.", t)
    need(m, "énoncé illisible")
    v, d = int(m.group(1)), D(m.group(2))
    r = re.fullmatch(r"Il lui faut (.+)\.", ex["answer"])
    need(r and duree_min(r.group(1)) == d * 60 / v, "durée attendue")


def _convertir_vitesse(ex):
    m = re.fullmatch(rf"Convertir \$({NB})\$ (km/h|m/s) en (km/h|m/s)\.", ex["enonce"])
    need(m and m.group(2) != m.group(3), "énoncé illisible")
    x = D(m.group(1))
    attendu = x * 1000 / 3600 if m.group(2) == "km/h" else x * 3600 / 1000
    r = re.fullmatch(rf"\$({NB})\$ (km/h|m/s) \$= ({NB})\$ (km/h|m/s)\.", ex["answer"])
    need(r and D(r.group(1)) == x and r.group(4) == m.group(3), "réponse illisible")
    need(D(r.group(3)) == attendu, f"vitesse attendue {attendu}")


def _debit_duree(ex):
    t = ex["enonce"]
    m = re.fullmatch(r"Convertir un débit de \$(\d+)\$ L/min en m³/h\.", t)
    if m:
        q = int(m.group(1))
        r = re.fullmatch(rf"\$(\d+)\$ L/min \$= ({NB})\$ m³/h\.", ex["answer"])
        need(r and D(r.group(2)) == Fraction(q * 60, 1000), "débit attendu")
        return
    m = re.fullmatch(rf"Un réservoir de \$({NB})\$ (L|m³) est rempli avec un débit de \$(\d+)\$ L/min\. .+", t)
    need(m, "énoncé illisible")
    vol = D(m.group(1)) * (1000 if m.group(2) == "m³" else 1)
    q = int(m.group(3))
    r = re.fullmatch(r"Il faut (.+)\.", ex["answer"])
    need(r and duree_min(r.group(1)) == vol / q, f"durée attendue {vol / q} min")


# ── Chapitre 9 — Théorème de Thalès (triangles emboîtés) ────────────────────


def config_thales(text: str):
    """Lit « $M \\in [AB]$ … $N \\in [AC]$ » et « $(MN) \\parallel (BC)$ » ; renvoie (A, B, C, M, N)."""
    m = re.search(r"\$(\w) \\in \[(\w)(\w)\]\$,? (?:et )?\$(\w) \\in \[(\w)(\w)\]\$", text)
    if m:
        p1, a1, b, p2, a2, c = m.groups()
    else:
        m = re.search(r"les points \$(\w)\$, \$(\w)\$, \$(\w)\$ sont alignés dans cet ordre, ainsi que \$(\w)\$, \$(\w)\$, \$(\w)\$", text)
        need(m, "configuration illisible")
        a1, p1, b, a2, p2, c = m.groups()
    need(a1 == a2, "pas de sommet commun")
    par = re.search(r"\$\((\w)(\w)\) \\parallel \((\w)(\w)\)\$", text)
    if par:
        need({par.group(1), par.group(2)} == {p1, p2} and {par.group(3), par.group(4)} == {b, c}, "parallèles incohérentes")
    return a1, b, c, p1, p2


def egalite_thales(a, b, c, m, n) -> str:
    return f"\\dfrac{{{a}{m}}}{{{a}{b}}} = \\dfrac{{{a}{n}}}{{{a}{c}}} = \\dfrac{{{m}{n}}}{{{b}{c}}}"


def longueurs(text: str) -> dict:
    return {nom: D(v) for nom, v in re.findall(rf"\$(\w\w) = ({NB})\$", text)}


def _rapports_thales(ex):
    a, b, c, m, n = config_thales(ex["enonce"])
    need(ex["answer"] == f"${egalite_thales(a, b, c, m, n)}$", "égalité attendue")


def _longueur_thales(ex):
    a, b, c, m, n = config_thales(ex["enonce"])
    connues = longueurs(ex["enonce"])
    cible = re.search(r"Calculer \$(\w\w)\$", ex["enonce"]).group(1)
    paires = [(a + m, a + b), (a + n, a + c), (m + n, b + c)]
    k = next((connues[p] / connues[g] for p, g in paires if p in connues and g in connues), None)
    need(k is not None and 0 < k < 1, "aucun rapport complet ou rapport incohérent")
    for p, g in paires:
        if cible == p:
            need(ex["family"] == "longueur_petit", "la cible devait être du grand triangle")
            attendu = k * connues[g]
        elif cible == g:
            need(ex["family"] == "longueur_grand", "la cible devait être du petit triangle")
            attendu = connues[p] / k
        else:
            continue
        need(ex["answer"] == f"${cible} = {grp_v(attendu)}$ cm.", f"{cible} = {attendu}")
        return
    raise AssertionError("cible introuvable")


def grp_v(x) -> str:
    """Écriture française avec espaces fines (indépendante de _commun.grp)."""
    s = fmt(x)
    ent, _, dec = s.partition("{,}")
    signe = "-" if ent.startswith("-") else ""
    ent = ent.lstrip("-")
    groupes = []
    while len(ent) > 3:
        groupes.insert(0, ent[-3:])
        ent = ent[:-3]
    groupes.insert(0, ent)
    return signe + "\\,".join(groupes) + ("{,}" + dec if dec else "")


def _longueur_difference(ex):
    a, b, c, m, n = config_thales(ex["enonce"])
    L = longueurs(ex["enonce"])
    ab = L[a + m] + L[m + b]
    ac = L[a + n] * ab / L[a + m]
    need(ex["answer"] == f"${a}{c} = {grp_v(ac)}$ cm et ${n}{c} = {grp_v(ac - L[a + n])}$ cm.", f"{a}{c} = {ac}")


def _ombre(ex):
    h, s, S = (D(v) for v in re.findall(rf"\$({NB})\$ m", ex["enonce"])[:3])
    H = S * h / s
    need(H > h, "l'objet doit être plus grand que le bâton")
    need(ex["answer"] == f"La hauteur est ${grp_v(H)}$ m.", f"hauteur {H}")


def _reciproque_thales(ex):
    a, b, c, m, n = config_thales(ex["enonce"])
    L = longueurs(ex["enonce"])
    r1, r2 = L[a + m] / L[a + b], L[a + n] / L[a + c]
    need(0 < r1 < 1 and 0 < r2 < 1, "points hors des segments")
    if r1 == r2:
        need(ex["answer"].startswith("Oui") and "réciproque" in ex["answer"], "Oui (réciproque) attendu")
        need(f"= {grp_v(r1)}$, donc" in ex["answer"], f"rapport commun {r1}")
    else:
        need(ex["answer"].startswith("Non") and "ne sont pas parallèles" in ex["answer"], "Non attendu")
        need(f"= {grp_v(r1)}$ et" in ex["answer"] and f"= {grp_v(r2)}$ sont différents" in ex["answer"], "valeurs des rapports")


def _rapport_k(ex):
    l1, l1b, l2 = (D(v) for v in re.findall(rf"\$({NB})\$ cm", ex["enonce"])[:3])
    k = l1b / l1
    nature = "un agrandissement" if k > 1 else "une réduction"
    need(k != 1, "rapport égal à 1")
    need(ex["answer"] == f"Rapport $k = {grp_v(k)}$ : c'est {nature} ; le segment de ${grp_v(l2)}$ cm devient ${grp_v(k * l2)}$ cm.",
         f"k = {k}")


def _aire_k2(ex):
    m = re.search(rf"d'aire \$({NB})\$ cm² est (agrandi|réduit) avec le rapport \$({NB})\$", ex["enonce"])
    need(m, "énoncé illisible")
    aire, k = D(m.group(1)), D(m.group(3))
    need((k > 1) == (m.group(2) == "agrandi"), "nature incohérente avec k")
    need(f"${grp_v(aire * k * k)}$ cm²" in ex["answer"], f"aire attendue {aire * k * k}")


# ── Chapitre 10 — Cosinus ───────────────────────────────────────────────────
import math as _math


def arrondi_v(x: float, d: int) -> str:
    """Arrondi indépendant (Decimal, demi vers le haut), écriture française."""
    from decimal import ROUND_HALF_UP, Decimal
    q = Decimal(repr(x)).quantize(Decimal(1).scaleb(-d), rounding=ROUND_HALF_UP)
    return grp_v(Fraction(q))


def triangle_rect(text: str):
    m = re.search(r"Le triangle \$(\w)(\w)(\w)\$ est rectangle en \$(\w)\$", text)
    need(m and m.group(4) in m.group(1, 2, 3), "triangle rectangle illisible")
    return m.groups()


def _nommer_cotes(ex):
    _, _, _, droit = triangle_rect(ex["enonce"])
    ang = re.search(r"\\widehat\{(\w)(\w)(\w)\}", ex["enonce"]).group(2)
    autre = next(l for l in triangle_rect(ex["enonce"])[:3] if l not in (droit, ang))
    hyp = {ang, autre}
    m = re.fullmatch(r"Hypoténuse \$\[(\w)(\w)\]\$ ; côté adjacent \$\[(\w)(\w)\]\$\.", ex["answer"])
    need(m and {m.group(1), m.group(2)} == hyp and {m.group(3), m.group(4)} == {ang, droit}, "côtés mal nommés")


def _angle_complementaire(ex):
    a = D(re.search(rf"= ({NB})°\$", ex["enonce"]).group(1))
    need(0 < a < 90, "angle non aigu")
    need(ex["answer"].endswith(f"= {grp_v(90 - a)}°$."), f"attendu {90 - a}")


def _calculer_cos(ex):
    L = longueurs(ex["enonce"])
    a, b, c, droit = triangle_rect(ex["enonce"])
    q = L[a + c] / L[a + b]
    need(0 < q < 1, "cosinus hors de ]0 ; 1[")
    attendu = f"\\dfrac{{{q.numerator}}}{{{q.denominator}}}" if q.denominator != 1 else str(q.numerator)
    need(f"= {attendu}" in ex["answer"], f"fraction irréductible {q}")
    if "écriture décimale" in ex["enonce"]:
        need(ex["answer"].endswith(f"= {grp_v(q)}$"), "écriture décimale")


def _cos_pythagore(ex):
    L = longueurs(ex["enonce"])
    a, b, c, droit = triangle_rect(ex["enonce"])
    hyp2 = L[a + c] ** 2 + L[b + c] ** 2
    hyp = Fraction(_math.isqrt(hyp2.numerator))
    need(hyp * hyp == hyp2, "hypoténuse non entière")
    q = L[a + c] / hyp
    need(ex["answer"] == f"${a}{b} = {fmt(hyp)}$ cm et $\\cos \\widehat{{{b}{a}{c}}} = \\dfrac{{{q.numerator}}}{{{q.denominator}}}$.", "réponse")


def _cote_adjacent(ex):
    L = longueurs(ex["enonce"])
    a, b, c, _ = triangle_rect(ex["enonce"])
    ang = int(re.search(r"= (\d+)°\$", ex["enonce"]).group(1))
    v = float(L[a + b]) * _math.cos(_math.radians(ang))
    need(ex["answer"] == f"${a}{c} \\approx {arrondi_v(v, 1)}$ cm.", f"{a}{c} ≈ {v}")


def _hypotenuse_cos(ex):
    L = longueurs(ex["enonce"])
    a, b, c, _ = triangle_rect(ex["enonce"])
    ang = int(re.search(r"= (\d+)°\$", ex["enonce"]).group(1))
    v = float(L[a + c]) / _math.cos(_math.radians(ang))
    need(v > float(L[a + c]), "hypoténuse plus courte que le côté adjacent")
    need(ex["answer"] == f"${a}{b} \\approx {arrondi_v(v, 1)}$ cm.", f"{a}{b} ≈ {v}")


def _angle_depuis_cotes(ex):
    L = longueurs(ex["enonce"])
    a, b, c, _ = triangle_rect(ex["enonce"])
    d = 0 if "au degré près" in ex["enonce"] else 1
    v = _math.degrees(_math.acos(float(L[a + c] / L[a + b])))
    need(ex["answer"] == f"$\\widehat{{{b}{a}{c}}} \\approx {arrondi_v(v, d)}°$.", f"angle ≈ {v}")


def _probleme_echelle(ex):
    longueur, pied = (D(x) for x in re.findall(rf"\$({NB})\$ m", ex["enonce"])[:2])
    v = _math.degrees(_math.acos(float(pied / longueur)))
    need(ex["answer"].startswith(f"Environ ${arrondi_v(v, 0)}°$ :"), f"angle ≈ {v}")
    conseille = 65 <= v <= 75
    need(("n'est pas" not in ex["answer"]) == conseille, "interprétation de la plage conseillée")


# ── Chapitre 12 — Triangles égaux ───────────────────────────────────────────


def correspondance(text: str) -> dict:
    paires = re.findall(r"\$(\w) \\to (\w)\$", text)
    need(len(paires) == 3 and len({b for _, b in paires}) == 3, "correspondance illisible")
    return dict(paires)


def _cotes_homologues(ex):
    corr = correspondance(ex["enonce"])
    a, b = re.search(r"même longueur que \$\[(\w)(\w)\]\$", ex["enonce"]).groups()
    need(ex["answer"] == f"Le côté $[{corr[a]}{corr[b]}]$ : ${a}{b} = {corr[a]}{corr[b]}$.", "côté homologue")


def _reporter_angle(ex):
    corr = correspondance(ex["enonce"])
    inverse = {v: k for k, v in corr.items()}
    connus = {s: int(v) for s, v in re.findall(r"\\widehat\{(\w)\} = (\d+)°", ex["enonce"])}
    need(len(connus) == 2 and sum(connus.values()) < 180, "deux angles connus")
    cible = re.search(r"Calculer \$\\widehat\{(\w)\}\$", ex["enonce"]).group(1)
    source = inverse[cible]
    valeur = connus.get(source, 180 - sum(connus.values()))
    need(ex["answer"] == f"$\\widehat{{{cible}}} = {valeur}°$.", f"angle attendu {valeur}")


def _perimetre_egal(ex):
    corr = correspondance(ex["enonce"])
    inverse = {v: k for k, v in corr.items()}
    cotes = {frozenset(n): int(v) for n, v in re.findall(r"\$(\w\w) = (\d+)\$ cm", ex["enonce"])}
    p = int(re.search(r"le périmètre de \$\w+\$ vaut \$(\d+)\$ cm", ex["enonce"]).group(1))
    x, y = re.search(r"Calculer \$(\w)(\w)\$", ex["enonce"]).groups()
    need(frozenset((inverse[x], inverse[y])) not in cotes, "le côté cherché est déjà donné")
    attendu = p - sum(cotes.values())
    need(attendu > 0 and ex["answer"] == f"${x}{y} = {attendu}$ cm.", f"côté attendu {attendu}")
    cs = sorted([*cotes.values(), attendu])
    need(cs[0] + cs[1] > cs[2], "inégalité triangulaire")


def _reconnaitre_cas(ex):
    m = re.fullmatch(r"Dans le triangle \$(\w{3})\$ : (.+)\. Dans le triangle \$(\w{3})\$ : (.+)\. "
                     r"Les triangles \$\w{3}\$ et \$\w{3}\$ sont-ils égaux \?", ex["enonce"])
    need(m, "énoncé illisible")
    t1, d1, t2, d2 = m.groups()
    corr = dict(zip(t1, t2))

    def lire(d):
        cotes = {frozenset(n): int(v) for n, v in re.findall(r"\$(\w\w) = (\d+)\$", d)}
        angles = {s: int(v) for s, v in re.findall(r"\\widehat\{(\w)\} = (\d+)°", d)}
        if len(angles) == 2:
            reste = next(s for s in (t1 if set(angles) <= set(t1) else t2) if s not in angles)
            angles[reste] = 180 - sum(angles.values())
        return cotes, angles

    c1, a1 = lire(d1)
    c2, a2 = lire(d2)
    image = {frozenset(corr[x] for x in k): v for k, v in c1.items()}
    if any(k in c2 and c2[k] != v for k, v in image.items()):
        need(ex["answer"].startswith("Non"), "côtés différents : réponse Non attendue")
        return
    cotes_eg = [k for k, v in image.items() if c2.get(k) == v]
    angles_eg = {s for s, v in a1.items() if a2.get(corr[s]) == v}
    cas = None
    if len(cotes_eg) == 3:
        cas = "côté – côté – côté"
    elif len(cotes_eg) >= 2 and any(next(iter(set(k1) & set(k2))) in {corr[s] for s in angles_eg}
                                    for k1 in cotes_eg for k2 in cotes_eg if k1 != k2 and set(k1) & set(k2)):
        cas = "côté – angle – côté"
    elif any(all(s in {corr[x] for x in angles_eg} for s in k) for k in cotes_eg):
        cas = "angle – côté – angle"
    if cas:
        need(ex["answer"].startswith("Oui") and cas in ex["answer"], f"cas {cas} attendu")
    else:
        need(ex["answer"].startswith("On ne peut pas conclure"), "aucun cas : on ne peut pas conclure")


def _milieu_commun(ex):
    m = re.search(r"\$\[(\w)(\w)\]\$ et \$\[(\w)(\w)\]\$ se coupent en leur milieu \$(\w)\$, et \$(\w)(\w) = ([\d{},]+)\$ cm", ex["enonce"])
    need(m, "énoncé illisible")
    a, c, b, d, o, x, y, v = m.groups()
    need((x, y) == (a, b), "longueur donnée : AB")
    need(ex["answer"] == f"Les triangles sont égaux (cas côté – angle – côté), donc ${c}{d} = {a}{b} = {v}$ cm.", "CD = AB")


def _mediatrice_calcul(ex):
    L = {n: int(v) for n, v in re.findall(r"\$(\w\w) = (\d+)\$ cm", ex["enonce"])}
    (n1, v1), (n2, v2) = L.items()
    r2 = v1 * v1 + v2 * v2
    r = _math.isqrt(r2)
    need(r * r == r2, "longueur non entière")
    m = re.search(r"\$(\w)\$ est le milieu de \$\[(\w)(\w)\]\$ et \$(\w)\$", ex["enonce"])
    h, a, b, mm = m.groups()
    need(ex["answer"].endswith(f"${mm}{b} = {r}$ cm.") and "côté – angle – côté" in ex["answer"], f"MB = {r}")


# ── Chapitre 11 — Translations ──────────────────────────────────────────────

_DIR = {"droite": (1, 0), "gauche": (-1, 0), "haut": (0, 1), "bas": (0, -1)}


def points_nommes(text: str) -> dict:
    return {n: (int(x), int(y)) for n, x, y in re.findall(r"\$(\w'?)\((-?\d+) ; (-?\d+)\)\$?", text)}


def deplacement_mots(text: str):
    dx = dy = 0
    for v, sens in re.findall(r"\$(\d+)\$ unités? vers (?:la|le) (droite|gauche|haut|bas)", text):
        ux, uy = _DIR[sens]
        dx, dy = dx + ux * int(v), dy + uy * int(v)
    return dx, dy


def _image_point(ex):
    (nom, p), = points_nommes(ex["enonce"]).items()
    dx, dy = deplacement_mots(ex["enonce"])
    need((dx, dy) != (0, 0), "déplacement nul")
    need(ex["answer"] == f"${nom}'({p[0] + dx} ; {p[1] + dy})$", "image attendue")


def _image_par_couple(ex):
    pts = points_nommes(ex["enonce"])
    m = re.search(r"transforme \$(\w)\(.*?\)\$ en \$(\w)\(.*?\)\$ transforme \$(\w)\(", ex["enonce"])
    M, N, A = m.groups()
    d = (pts[N][0] - pts[M][0], pts[N][1] - pts[M][1])
    need(ex["answer"] == f"${A}'({pts[A][0] + d[0]} ; {pts[A][1] + d[1]})$", "image attendue")


def _antecedent(ex):
    pts = points_nommes(ex["enonce"])
    (nom, img), = pts.items()
    dx, dy = deplacement_mots(ex["enonce"])
    r = nom.rstrip("'")
    need(ex["answer"] == f"${r}({img[0] - dx} ; {img[1] - dy})$", "antécédent attendu")


def _quatrieme_sommet(ex):
    pts = points_nommes(ex["enonce"])
    m = re.search(r"Le point \$(\w)\$ est l'image de \$(\w)\$ par la translation qui transforme \$(\w)\$ en \$(\w)\$", ex["enonce"])
    D, C, A, B = m.groups()
    (ax, ay), (bx, by), (cx, cy) = pts[A], pts[B], pts[C]
    need((bx - ax) * (cy - ay) - (by - ay) * (cx - ax) != 0, "points alignés")
    d = (cx + bx - ax, cy + by - ay)
    need(ex["answer"] == f"${D}({d[0]} ; {d[1]})$ ; ${A}{B}{D}{C}$ est un parallélogramme.", "sommet attendu")
    # contrôle géométrique : diagonales [AD] et [BC] de même milieu
    need((ax + d[0], ay + d[1]) == (bx + cx, by + cy), "diagonales de milieux différents")


def _conservation_mesure(ex):
    m = re.search(rf"(mesure|vaut) \$({NB})(°?)\$", ex["enonce"])
    need(m, "mesure illisible")
    v = m.group(2) + m.group(3)
    need(f"${v}$" in ex["answer"].split(":", 1)[1], "mesure recopiée")
    need(ex["answer"].startswith("Une translation conserve"), "propriété citée")
    nature = "°" if m.group(3) else ("cm²" if "aire" in ex["enonce"] else "cm")
    attendu = {"°": "les angles", "cm²": "les aires", "cm": "les longueurs"}[nature]
    need(attendu in ex["answer"], f"propriété attendue : {attendu}")


def _longueur_image(ex):
    L = {n: D(v) for n, v in re.findall(rf"\$(\w\w) = ({NB})\$ cm", ex["enonce"])}
    (n1, v1), (n2, v2) = L.items()
    h2 = v1 * v1 + v2 * v2
    num, den = h2.numerator, h2.denominator
    rn, rd = _math.isqrt(num), _math.isqrt(den)
    need(rn * rn == num and rd * rd == den, "hypoténuse non décimale")
    need(ex["answer"].endswith(f"= {grp_v(Fraction(rn, rd))}$ cm."), f"hypoténuse {Fraction(rn, rd)}")


def _frise_position(ex):
    x0, pas = (D(v) for v in re.findall(rf"\$(?:x = )?({NB})\$ cm", ex["enonce"])[:2])
    n = int(re.search(r"motif numéro \$(\d+)\$", ex["enonce"]).group(1))
    need(ex["answer"] == f"En $x = {grp_v(x0 + (n - 1) * pas)}$ cm.", "position attendue")


def _frise_rang(ex):
    x0, pas, pos = (D(v) for v in re.findall(rf"\$(?:x = )?({NB})\$ cm", ex["enonce"])[:3])
    n = (pos - x0) / pas + 1
    need(n.denominator == 1 and n >= 1, "rang non entier")
    need(ex["answer"] == f"C'est le motif numéro ${n}$.", f"rang {n}")


# ── Chapitre 13 — Espace : repérage, pyramides, cônes, volumes ──────────────

_PAVE = {"A": (0, 0, 0), "B": (1, 0, 0), "C": (1, 1, 0), "D": (0, 1, 0),
         "E": (0, 0, 1), "F": (1, 0, 1), "G": (1, 1, 1), "H": (0, 1, 1)}


def _coordonnees_sommet(ex):
    L, l, h = (int(v) for v in re.findall(r"\$A[BDE] = (\d+)\$", ex["enonce"]))
    s = re.search(r"coordonnées de \$(\w)\$", ex["enonce"]).group(1)
    fx, fy, fz = _PAVE[s]
    need(ex["answer"] == f"${s}({fx * L} ; {fy * l} ; {fz * h})$", "coordonnées attendues")


def _diagonale_pave(ex):
    a, b, c = (int(v) for v in re.findall(r"= (\d+)\$ cm", ex["enonce"])[:3])
    n = a * a + b * b + c * c
    r = _math.isqrt(n)
    attendu = str(r) if r * r == n else f"\\sqrt{{{n}}}"
    need(ex["answer"] == f"$AG = {attendu}$ cm.", f"AG = √{n}")


def _elements_pyramide(ex):
    n = int(re.search(r"\(\$(\d+)\$ côtés\)", ex["enonce"]).group(1))
    need(ex["answer"] == f"${n + 1}$ faces, ${2 * n}$ arêtes et ${n + 1}$ sommets.", "dénombrement")
    need(n + 1 + n + 1 - 2 * n == 2, "relation d'Euler")


def _generatrice_cone(ex):
    a, b = (D(v) for v in re.findall(rf"\$({NB})\$ cm", ex["enonce"])[:2])
    if "génératrice de" in ex["enonce"]:            # génératrice a, rayon b : hauteur
        x2, cible = a * a - b * b, "La hauteur mesure"
    else:                                           # hauteur a, rayon b : génératrice
        x2, cible = a * a + b * b, "La génératrice mesure"
    need(x2 > 0, "longueurs incohérentes")
    xn, xd = _math.isqrt(x2.numerator), _math.isqrt(x2.denominator)
    need(xn * xn == x2.numerator and xd * xd == x2.denominator, "longueur non décimale")
    need(ex["answer"] == f"{cible} ${grp_v(Fraction(xn, xd))}$ cm.", "longueur attendue")


def _volume_pyramide(ex):
    t = ex["enonce"]
    h = int(re.search(r"une hauteur de \$(\d+)\$ cm", t).group(1))
    if "base carrée" in t:
        c = int(re.search(r"côté \$(\d+)\$ cm", t).group(1))
        base = Fraction(c * c)
    elif "rectangulaire" in t:
        a, b = (int(v) for v in re.findall(r"\$(\d+)\$ cm sur \$(\d+)\$ cm", t)[0])
        base = Fraction(a * b)
    else:
        a, b = (int(v) for v in re.search(r"mesurent \$(\d+)\$ cm et \$(\d+)\$ cm", t).groups())
        base = Fraction(a * b, 2)
    need(ex["answer"] == f"$V = {grp_v(base * h / 3)}$ cm³.", f"volume {base * h / 3}")


def _volume_cone(ex):
    r, h = (int(v) for v in re.search(r"rayon \$(\d+)\$ cm et de hauteur \$(\d+)\$ cm", ex["enonce"]).groups())
    k = Fraction(r * r * h, 3)
    need(k.denominator == 1, "coefficient de π non entier")
    approx = arrondi_v(float(k) * _math.pi, 1)
    need(ex["answer"] == f"$V = {k}\\pi \\approx {approx}$ cm³.", f"V = {k}π ≈ {approx}")


def _hauteur_pyramide(ex):
    c, v = (int(x) for x in re.search(r"côté \$(\d+)\$ cm a un volume de \$(\d+)\$ cm³", ex["enonce"]).groups())
    h = Fraction(3 * v, c * c)
    need(h.denominator == 1 and ex["answer"] == f"La hauteur est ${h}$ cm.", f"hauteur {h}")


def _volume_k3(ex):
    m = re.search(rf"de volume \$({NB})\$ cm³ est (agrandie?|réduite?) avec le rapport \$({NB}|\\dfrac\{{\d+\}}\{{\d+\}})\$", ex["enonce"])
    need(m, "énoncé illisible")
    v, k = D(m.group(1)), (lire_nombre(m.group(3)) if "dfrac" in m.group(3) else D(m.group(3)))
    need((k > 1) == m.group(2).startswith("agrandi"), "nature incohérente avec k")
    need(ex["answer"] == f"Le nouveau volume est ${grp_v(v * k ** 3)}$ cm³.", f"volume {v * k ** 3}")


# ── Chapitre 15 — Notion de fonction ───────────────────────────────────────


def _calculer_valeur(ex):
    m = re.fullmatch(r"La grandeur \$y\$ est donnée en fonction de \$x\$ par la formule \$y = (.+)\$\. Calculer \$y\$ pour \$x = (-?\d+)\$\.", ex["enonce"])
    need(m, "énoncé illisible")
    y = EV(m.group(1))(Fraction(int(m.group(2))))
    need(ex["answer"] == f"Pour $x = {m.group(2)}$, $y = {fmt(y)}$.", f"y = {y}")


def _traduire_situation(ex):
    f, u = (D(v) for v in re.findall(rf"\$({NB})\$ (?:€|L|cm)", ex["enonce"])[:2])
    k = int(re.search(r"pour \$\w = (\d+)\$\.", ex["enonce"]).group(1))
    nom = re.search(r"Exprimer \$(\w)\$ en fonction", ex["enonce"]).group(1)
    need(ex["answer"].startswith(f"${nom} = {grp_v(u)}n + {grp_v(f)}$"), "formule attendue")
    need(f"${nom} = {grp_v(f + u * k)}$" in ex["answer"], f"valeur {f + u * k}")


def _tableau_valeurs(ex):
    m = re.fullmatch(r"Compléter le tableau de valeurs de \$y = (.+)\$ pour \$x = (.+)\$\.", ex["enonce"])
    need(m, "énoncé illisible")
    f = EV(m.group(1))
    xs = [int(v) for v in m.group(2).split(" ; ")]
    need(ex["answer"] == "$y = " + " ; ".join(fmt(f(Fraction(x))) for x in xs) + "$.", "valeurs du tableau")


def _point_sur_graphique(ex):
    m = re.fullmatch(r"Le point \$\((-?\d+) ; (-?\d+)\)\$ appartient-il au graphique représentant \$y = (.+)\$ \?", ex["enonce"])
    need(m, "énoncé illisible")
    x, y = int(m.group(1)), int(m.group(2))
    yc = EV(m.group(3))(Fraction(x))
    if yc == y:
        need(ex["answer"] == f"Oui : pour $x = {x}$, $y = {fmt(yc)}$.", "réponse Oui attendue")
    else:
        need(ex["answer"] == f"Non : pour $x = {x}$, $y = {fmt(yc)}$ et non ${y}$.", "réponse Non attendue")


def _graduation(ex):
    maxi, carreaux = (int(v) for v in re.search(r"de \$0\$ à \$(\d+)\$ sur un axe de \$(\d+)\$ carreaux", ex["enonce"]).groups())
    pas = min(p for p in (1, 2, 5, 10, 20, 25, 50, 100, 200) if p * carreaux >= maxi)
    need(ex["answer"] == f"Le pas de ${pas}$ par carreau.", f"pas {pas}")


def _lecture_points(ex):
    pts = [(int(a), int(b)) for a, b in re.findall(r"\$\((-?\d+) ; (-?\d+)\)\$", ex["enonce"])]
    table = dict(pts)
    m = re.search(r"Lire la valeur de \$y\$ pour \$x = (-?\d+)\$", ex["enonce"])
    if m:
        x = int(m.group(1))
        need(ex["answer"] == f"Pour $x = {x}$, $y = {table[x]}$.", "lecture directe")
        return
    y = int(re.search(r"a-t-on \$y = (-?\d+)\$", ex["enonce"]).group(1))
    sol = [x for x, v in pts if v == y]
    need(sol and ex["answer"] == "Pour " + " et ".join(f"$x = {s}$" for s in sol) + ".", "toutes les solutions")


def _lecture_segment(ex):
    x0y0, x1y1 = re.findall(r"\$\((-?\d+) ; (-?\d+)\)\$", ex["enonce"])[:2]
    (xa, ya), (xb, yb) = (tuple(int(v) for v in p) for p in (x0y0, x1y1))
    pente = Fraction(yb - ya, xb - xa)
    m = re.search(r"valeur de \$y\$ pour \$x = (\d+)\$", ex["enonce"])
    if m:
        t = int(m.group(1))
        need(ex["answer"] == f"Pour $x = {t}$, $y = {grp_v(ya + pente * (t - xa))}$.", "lecture directe")
        return
    v = int(re.search(r"a-t-on \$y = (-?\d+)\$", ex["enonce"]).group(1))
    t = xa + (v - ya) / pente
    need(xa <= t <= xb and ex["answer"] == f"Pour $x = {grp_v(t)}$.", f"x = {t}")


# ── Chapitre 16 — Statistiques ──────────────────────────────────────────────


def mediane_v(valeurs) -> Fraction:
    v = sorted(valeurs)
    n = len(v)
    milieu = n // 2
    return Fraction(v[milieu]) if n % 2 == 1 else (Fraction(v[milieu - 1]) + Fraction(v[milieu])) / 2


def _angles_diagramme(ex):
    total = int(re.search(r"auprès de \$(\d+)\$ personnes", ex["enonce"]).group(1))
    eff = [int(v) for v in re.findall(r" : \$(\d+)\$", ex["enonce"])]
    need(sum(eff) == total, "effectifs incohérents avec le total")
    angles = [int(v) for v in re.findall(r"\$(\d+)°\$", ex["answer"])]
    need(angles == [e * 360 // total for e in eff] and all(e * 360 % total == 0 for e in eff), "angles attendus")
    need(sum(angles) == 360, "somme des angles")


def _effectif_depuis_angle(ex):
    total, angle = (int(v) for v in re.search(r"représentant \$(\d+)\$ personnes, un secteur mesure \$(\d+)°\$", ex["enonce"]).groups())
    eff = Fraction(angle * total, 360)
    need(eff.denominator == 1 and ex["answer"] == f"Il représente ${eff}$ personnes.", f"effectif {eff}")


def _frequence_pourcentage(ex):
    total, e = (int(v) for v in re.search(r"Parmi \$(\d+)\$ \w+, \$(\d+)\$ ont", ex["enonce"]).groups())
    need(0 < e < total, "effectif incohérent")
    need(ex["answer"] == f"La fréquence est ${grp_v(Fraction(100 * e, total))}\\,\\%$.", "fréquence attendue")


def _mediane_liste(ex):
    liste = ex["enonce"].split("personnes :", 1)[1]
    vals = [int(v) for v in re.findall(r"\$(-?\d+)\$", liste)]
    n = int(re.search(r"de \$(\d+)\$ personnes", ex["enonce"]).group(1))
    need(len(vals) == n, "effectif annoncé")
    need(ex["answer"] == f"La médiane est ${grp_v(mediane_v(vals))}$.", f"médiane {mediane_v(vals)}")


def _serie_tableau(text):
    paires = [(int(v), int(e)) for v, e in re.findall(r"\$(-?\d+)\$ \((\d+)\)", text)]
    need(paires, "tableau illisible")
    return [v for v, e in paires for _ in range(e)]


def _mediane_tableau(ex):
    serie = _serie_tableau(ex["enonce"])
    need(len(serie) <= 30, "effectif total > 30")
    need(ex["answer"] == f"La médiane est ${grp_v(mediane_v(serie))}$.", f"médiane {mediane_v(serie)}")


def _moyenne_tableau(ex):
    serie = _serie_tableau(ex["enonce"])
    m = Fraction(sum(serie), len(serie))
    need(ex["answer"] == f"La moyenne est ${grp_v(m)}$.", f"moyenne {m}")


def _comparer_frequences(ex):
    e1, n1, e2, n2 = (int(v) for v in re.search(r"groupe A, \$(\d+)\$ personnes sur \$(\d+)\$ .+groupe B, \$(\d+)\$ sur \$(\d+)\$", ex["enonce"]).groups())
    f1, f2 = Fraction(100 * e1, n1), Fraction(100 * e2, n2)
    need(f1 != f2, "proportions égales")
    g = "A" if f1 > f2 else "B"
    need(ex["answer"] == f"Dans le groupe {g} : A ${grp_v(f1)}\\,\\%$ et B ${grp_v(f2)}\\,\\%$.", f"groupe {g}")


# ── Chapitre 17 — Probabilités ──────────────────────────────────────────────


def _issues_lues(text, n):
    """Issues favorables recalculées à partir du libellé de l'événement."""
    m = re.search(r"multiple de \$(\d+)\$", text)
    if m:
        return [x for x in range(1, n + 1) if x % int(m.group(1)) == 0]
    m = re.search(r"strictement supérieur à \$(\d+)\$", text)
    if m:
        return [x for x in range(1, n + 1) if x > int(m.group(1))]
    m = re.search(r"inférieur ou égal à \$(\d+)\$", text)
    if m:
        return [x for x in range(1, n + 1) if x <= int(m.group(1))]
    m = re.search(r"diviseur de \$(\d+)\$", text)
    need(m, "événement illisible")
    return [x for x in range(1, n + 1) if int(m.group(1)) % x == 0]


def _roue_n(ex):
    n = int(re.search(r"à? ?\$(\d+)\$ secteurs identiques numérotés de \$1\$ à \$(\d+)\$", ex["enonce"]).group(2))
    return n, _issues_lues(ex["enonce"].split("«", 1)[1], n)


def _proba_reponse(ex) -> Fraction:
    m = re.fullmatch(r"\$P(?:\(\d\))? = (.+)\$\.", ex["answer"])
    need(m, "réponse illisible")
    return m.group(1)


def _issues_evenement(ex):
    n, fav = _roue_n(ex)
    need(0 < len(fav) < n, "événement certain ou impossible")
    lues = [int(v) for v in re.findall(r"\$(\d+)\$", ex["answer"].split(", soit")[0])]
    need(lues == fav, f"issues attendues {fav}")
    need(ex["answer"].endswith(f"soit ${len(fav)}$ issues."), "nombre d'issues")


def _proba_roue(ex):
    n, fav = _roue_n(ex)
    need(0 < len(fav) < n, "événement certain ou impossible")
    need(lire_nombre(_proba_reponse(ex)) == Fraction(len(fav), n), f"probabilité {Fraction(len(fav), n)}")


def _urne_lue(ex):
    boules = [(int(e), c) for e, c in re.findall(r"\$(\d+)\$ boules (\w+)", ex["enonce"])]
    need(len(boules) >= 2, "urne illisible")
    couleur = re.search(r"tirer une boule (\w+) \?", ex["enonce"]).group(1)
    favorables = [e for e, c in boules if c == couleur + "s"]
    need(len(favorables) == 1, f"couleur {couleur} absente")
    return favorables[0], sum(e for e, _ in boules)


def _proba_urne(ex):
    e, total = _urne_lue(ex)
    need(lire_nombre(_proba_reponse(ex)) == Fraction(e, total), f"probabilité {Fraction(e, total)}")


def _contraire_urne(ex):
    need("ne pas tirer" in ex["enonce"], "énoncé du contraire")
    e, total = _urne_lue(ex)
    need(lire_nombre(_proba_reponse(ex)) == 1 - Fraction(e, total), f"probabilité {1 - Fraction(e, total)}")


def _contraire_decimal(ex):
    p = D(re.search(r"est \$([\d{},]+)\$\.", ex["enonce"]).group(1))
    need(0 < p < 1, "probabilité hors de ]0 ; 1[")
    need(ex["answer"] == f"La probabilité de l'événement contraire est ${fmt(1 - p)}$.", f"contraire {fmt(1 - p)}")


def _proba_manquante(ex):
    faces = int(re.search(r"numérotées de \$1\$ à \$(\d+)\$", ex["enonce"]).group(1))
    need(faces == (4 if "osselet" in ex["enonce"] else 6), "nombre de faces")
    connues = {int(k): D(v) for k, v in re.findall(r"\$P\((\d)\) = ([\d{},]+)\$", ex["enonce"])}
    need(sorted(connues) == list(range(1, faces)), "probabilités données")
    reste = 1 - sum(connues.values())
    need(0 < reste < 1 and all(0 < q < 1 for q in connues.values()), "probabilités incohérentes")
    need(ex["answer"] == f"$P({faces}) = {fmt(reste)}$.", f"P({faces}) = {fmt(reste)}")


def _roue_angles(ex):
    a, b = (int(v) for v in re.search(r"rouge \(\$(\d+)°\$\), bleu \(\$(\d+)°\$\)", ex["enonce"]).groups())
    need(0 < a and 0 < b and a + b < 360, "angles incohérents")
    cible = re.search(r"s'arrête sur le (\w+) \?", ex["enonce"]).group(1)
    angle = {"rouge": a, "bleu": b, "vert": 360 - a - b}[cible]
    need(lire_nombre(_proba_reponse(ex)) == Fraction(angle, 360), f"probabilité {Fraction(angle, 360)}")


def _cible_carres(ex):
    a, b = (int(v) for v in re.search(r"côté \$(\d+)\$ cm contient en son centre un carré de côté \$(\d+)\$ cm", ex["enonce"]).groups())
    need(0 < b < a, "carré central plus grand que la cible")
    p = Fraction(b * b, a * a)
    if "hors du carré central" in ex["enonce"]:
        p = 1 - p
    need(lire_nombre(_proba_reponse(ex)) == p, f"probabilité {p}")


CHECKERS = {
    "issues_evenement": _issues_evenement,
    "proba_roue": _proba_roue,
    "proba_urne": _proba_urne,
    "contraire_decimal": _contraire_decimal,
    "contraire_urne": _contraire_urne,
    "proba_manquante": _proba_manquante,
    "roue_angles": _roue_angles,
    "cible_carres": _cible_carres,
    "angles_diagramme": _angles_diagramme,
    "effectif_depuis_angle": _effectif_depuis_angle,
    "frequence_pourcentage": _frequence_pourcentage,
    "mediane_liste": _mediane_liste,
    "mediane_tableau": _mediane_tableau,
    "moyenne_tableau": _moyenne_tableau,
    "comparer_frequences": _comparer_frequences,
    "calculer_valeur": _calculer_valeur,
    "traduire_situation": _traduire_situation,
    "tableau_valeurs": _tableau_valeurs,
    "point_sur_graphique": _point_sur_graphique,
    "graduation": _graduation,
    "lecture_points": _lecture_points,
    "lecture_segment": _lecture_segment,
    "coordonnees_sommet": _coordonnees_sommet,
    "diagonale_pave": _diagonale_pave,
    "elements_pyramide": _elements_pyramide,
    "generatrice_cone": _generatrice_cone,
    "volume_pyramide": _volume_pyramide,
    "volume_cone": _volume_cone,
    "hauteur_pyramide": _hauteur_pyramide,
    "volume_k3": _volume_k3,
    "image_point": _image_point,
    "image_par_couple": _image_par_couple,
    "antecedent": _antecedent,
    "quatrieme_sommet": _quatrieme_sommet,
    "conservation_mesure": _conservation_mesure,
    "longueur_image": _longueur_image,
    "frise_position": _frise_position,
    "frise_rang": _frise_rang,
    "cotes_homologues": _cotes_homologues,
    "reporter_angle": _reporter_angle,
    "perimetre_egal": _perimetre_egal,
    "reconnaitre_cas": _reconnaitre_cas,
    "milieu_commun": _milieu_commun,
    "mediatrice_calcul": _mediatrice_calcul,
    "nommer_cotes": _nommer_cotes,
    "angle_complementaire": _angle_complementaire,
    "calculer_cos": _calculer_cos,
    "cos_pythagore": _cos_pythagore,
    "cote_adjacent": _cote_adjacent,
    "hypotenuse_cos": _hypotenuse_cos,
    "angle_depuis_cotes": _angle_depuis_cotes,
    "probleme_echelle": _probleme_echelle,
    "rapports_thales": _rapports_thales,
    "longueur_petit": _longueur_thales,
    "longueur_grand": _longueur_thales,
    "longueur_difference": _longueur_difference,
    "ombre": _ombre,
    "reciproque": _reciproque_thales,
    "rapport_k": _rapport_k,
    "aire_k2": _aire_k2,
    "quatrieme_proportionnelle": _quatrieme_proportionnelle,
    "appliquer_pourcentage": _appliquer_pourcentage,
    "calculer_pourcentage": _calculer_pourcentage,
    "echelle": _echelle,
    "tableau_proportionnel": _tableau_proportionnel,
    "vitesse_distance_duree": _vitesse_distance_duree,
    "convertir_vitesse": _convertir_vitesse,
    "debit_duree": _debit_duree,
    "tester_solution": _tester_solution,
    "resoudre_simple": _resoudre_equation,
    "resoudre_fraction": _resoudre_equation,
    "resoudre_deux_membres": _resoudre_equation,
    "resoudre_parentheses": _resoudre_equation,
    "probleme_nombre": _probleme_nombre,
    "probleme_tarifs": _probleme_tarifs,
    "probleme_perimetre": _probleme_perimetre,
    "probleme_ages": _probleme_ages,
    "substituer": _substituer,
    "traduire_programme": _traduire_programme,
    "reduire_somme": _forme_reduite,
    "reduire_parentheses": _forme_reduite,
    "developper": _forme_reduite,
    "developper_reduire": _forme_reduite,
    "factoriser": _factoriser,
    "tester_egalite": _tester_egalite,
    "programme_constant": _programme_constant,
    "calculer_puissance": _calculer_puissance,
    "ecrire_puissance": _ecrire_puissance,
    "puissance10_decimal": _puissance10_decimal,
    "produit_puissances10": _produit_puissances10,
    "vers_scientifique": _vers_scientifique,
    "depuis_scientifique": _depuis_scientifique,
    "comparer_scientifique": _comparer_scientifique,
    "conversion_prefixe": _conversion_prefixe,
    "critere_divisibilite": _critere_divisibilite,
    "liste_diviseurs": _liste_diviseurs,
    "est_premier": _est_premier,
    "reconstituer": _reconstituer,
    "decomposer": _decomposer,
    "simplifier_premiers": _simplifier_premiers,
    "lots_identiques": _lots_identiques,
    "rendez_vous": _rendez_vous,
    "produit_fractions": _produit_fractions,
    "fraction_quantite": _fraction_quantite,
    "inverse_nombre": _inverse_nombre,
    "quotient_fractions": _quotient_fractions,
    "combien_de_fois": _combien_de_fois,
    "priorites_fractions": _priorites_fractions,
    "fraction_du_reste": _fraction_du_reste,
    "retrouver_tout": _retrouver_tout,
    "simplifier": _simplifier,
    "completer_egalite": _completer_egalite,
    "comparer_deux": _comparer_deux,
    "encadrer": _encadrer,
    "ranger_trois": _ranger_trois,
    "somme_multiple": _somme,
    "somme_quelconque": _somme,
    "part_restante": _part_restante,
    "produit_deux": _produit_deux,
    "facteur_manquant": _facteur_manquant,
    "signe_produit": _signe_produit,
    "produit_plusieurs": _produit_plusieurs,
    "quotient": _quotient,
    "variation_moyenne": _variation_moyenne,
    "priorites": _priorites,
    "substitution": _substitution,
}
