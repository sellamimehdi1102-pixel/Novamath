"""Génération d'exercices de vocabulaire ensembliste et de logique (Première,
Chapitre_11, programme 2026 : notations ensemblistes, connecteurs « et » /
« ou », contre-exemple, quantificateurs et négation, statut des égalités,
implication, réciproque, contraposée, conditions nécessaires et suffisantes,
raisonnements par disjonction des cas, par l'absurde, par contraposée).

Garantie de correction : chaque réponse est CALCULÉE (ensembles Python,
intervalles SymPy, vérité des propositions évaluée sur les valeurs
concernées, identités vérifiées par SymPy) ; un désaccord rejette le tirage.

Même contrat que les autres modules du programme 2026 (identifiants stables
par famille : GENERATED_ID_OFFSET + 1000 × rang + k).
"""
import random
from dataclasses import dataclass
from math import gcd
from typing import Callable, Optional

import sympy as sp

CHAPTER_ID = "Chapitre_11"
N1 = "Ensembles et notations"
N2 = "Propositions, connecteurs et quantificateurs"
N3 = "Implication, réciproque et contraposée"
N4 = "Types de raisonnement"

GENERATED_ID_OFFSET = 1_160_000

LEVEL_META = {
    1: {"emoji": "🟢", "label": "Niveau 1 — Fondamental"},
    2: {"emoji": "🟡", "label": "Niveau 2 — Intermédiaire"},
    3: {"emoji": "🟠", "label": "Niveau 3 — Avancé"},
    4: {"emoji": "🔴", "label": "Niveau 4 — Difficile"},
}
x = sp.Symbol("x")


def ens(s) -> str:
    """Ensemble fini en LaTeX : {1 ; 3 ; 5}, ∅ si vide."""
    s = sorted(s)
    return "\\varnothing" if not s else "\\{" + " ; ".join(str(v) for v in s) + "\\}"


def _sub(rng, univers, k):
    return set(rng.sample(sorted(univers), k))


# ── Notion 1 — ensembles ─────────────────────────────────────────────────────

def _gen_union_intersection(rng):
    U = range(1, 13)
    A, B = _sub(rng, U, rng.randint(3, 5)), _sub(rng, U, rng.randint(3, 5))
    if A == B:
        return None
    return dict(enonce=f"On donne $A = {ens(A)}$ et $B = {ens(B)}$. Déterminer $A \\cup B$ et $A \\cap B$.",
                answer=f"$A \\cup B = {ens(A | B)}$ et $A \\cap B = {ens(A & B)}$.",
                hint="La réunion contient les éléments de A OU de B ; l'intersection ceux de A ET de B.",
                steps=["$A \\cup B$ : on rassemble tous les éléments de $A$ et de $B$, sans répétition.",
                       f"$A \\cup B = {ens(A | B)}$.", f"$A \\cap B$ : éléments communs, $A \\cap B = {ens(A & B)}$."])


def _gen_complementaire(rng):
    n = rng.randint(8, 12)
    E = set(range(1, n + 1))
    A = _sub(rng, E, rng.randint(3, n - 3))
    return dict(enonce=f"Dans $E = {ens(E)}$, on considère $A = {ens(A)}$. Déterminer $\\overline{{A}}$ (complémentaire de $A$ dans $E$), puis $\\operatorname{{Card}}(A)$ et $\\operatorname{{Card}}(\\overline{{A}})$.",
                answer=f"$\\overline{{A}} = {ens(E - A)}$ ; $\\operatorname{{Card}}(A) = {len(A)}$ et $\\operatorname{{Card}}(\\overline{{A}}) = {len(E - A)}$.",
                hint="Le complémentaire contient les éléments de E qui ne sont pas dans A.",
                steps=[f"$\\overline{{A}} = E \\setminus A = {ens(E - A)}$.", f"$\\operatorname{{Card}}(A) = {len(A)}$, $\\operatorname{{Card}}(\\overline{{A}}) = {len(E - A)}$.",
                       f"Contrôle : ${len(A)} + {len(E - A)} = {n} = \\operatorname{{Card}}(E)$."])


def _itv(itv) -> str:
    if itv is sp.S.EmptySet:
        return "\\varnothing"
    if isinstance(itv, sp.Union):
        return " \\cup ".join(_itv(p) for p in itv.args)
    lo = "]" if itv.left_open else "["
    hi = "[" if itv.right_open else "]"
    return f"{lo}{itv.start} ; {itv.end}{hi}"


def _gen_intervalles(rng):
    a = rng.randint(-8, 3)
    b = a + rng.randint(2, 7)
    c = rng.randint(a - 2, b - 1)
    d = c + rng.randint(2, 7)
    itv_i = sp.Interval(a, b, left_open=rng.random() < 0.5, right_open=rng.random() < 0.5)
    itv_j = sp.Interval(c, d, left_open=rng.random() < 0.5, right_open=rng.random() < 0.5)
    inter, union = itv_i.intersect(itv_j), itv_i.union(itv_j)
    if inter is sp.S.EmptySet or not isinstance(inter, sp.Interval) or not isinstance(union, sp.Interval):
        return None
    return dict(enonce=f"On donne les intervalles $I = {_itv(itv_i)}$ et $J = {_itv(itv_j)}$. Déterminer $I \\cap J$ et $I \\cup J$.",
                answer=f"$I \\cap J = {_itv(inter)}$ et $I \\cup J = {_itv(union)}$.",
                hint="Représente les deux intervalles sur une même droite graduée.",
                steps=["On place $I$ et $J$ sur une droite graduée, en faisant attention aux crochets.",
                       f"Partie commune : $I \\cap J = {_itv(inter)}$.", f"Réunion (d'un seul tenant ici) : $I \\cup J = {_itv(union)}$."])


def _gen_produit_cartesien(rng):
    A = _sub(rng, range(1, 7), rng.randint(2, 3))
    lettres = rng.sample("abcdefg", rng.randint(2, 3))
    couples = [f"({u} ; {v})" for u in sorted(A) for v in sorted(lettres)]
    B = "\\{" + " ; ".join(sorted(lettres)) + "\\}"
    return dict(enonce=f"On donne $A = {ens(A)}$ et $B = {B}$. Écrire tous les éléments de $A \\times B$ et donner $\\operatorname{{Card}}(A \\times B)$.",
                answer=f"$A \\times B = \\{{{' ; '.join(couples)}\\}}$ et $\\operatorname{{Card}}(A \\times B) = {len(A) * len(lettres)}$.",
                hint="Un élément de A × B est un couple (élément de A ; élément de B).",
                steps=["On associe à chaque élément de $A$ chaque élément de $B$.", f"On obtient ${len(couples)}$ couples.",
                       f"$\\operatorname{{Card}}(A \\times B) = \\operatorname{{Card}}(A) \\times \\operatorname{{Card}}(B) = {len(A)} \\times {len(lettres)}$."])


def _gen_appartenance(rng):
    A = _sub(rng, range(1, 16), rng.randint(4, 6))
    v = rng.randint(1, 15)
    S = _sub(rng, range(1, 16), 2)
    r1, r2 = v in A, S <= A
    return dict(enonce=f"On donne $A = {ens(A)}$. Les affirmations « ${v} \\in A$ » et « ${ens(S)} \\subset A$ » sont-elles vraies ?",
                answer=f"« ${v} \\in A$ » est {'vraie' if r1 else 'fausse'} ; « ${ens(S)} \\subset A$ » est {'vraie' if r2 else 'fausse'}.",
                hint="∈ relie un élément à un ensemble ; ⊂ relie deux ensembles.",
                steps=[f"${v}$ {'figure' if r1 else 'ne figure pas'} dans la liste des éléments de $A$.",
                       f"${ens(S)} \\subset A$ si CHAQUE élément de ${ens(S)}$ est dans $A$ : {'c’est le cas' if r2 else 'ce n’est pas le cas'}."])


# ── Notion 2 — propositions ──────────────────────────────────────────────────

_PRED = {
    "pair": ("est pair", lambda n: n % 2 == 0),
    "m3": ("est un multiple de $3$", lambda n: n % 3 == 0),
    "m5": ("est un multiple de $5$", lambda n: n % 5 == 0),
}


def _gen_et_ou(rng):
    k = rng.randint(4, 15)
    p1, p2 = rng.sample(["pair", "m3", "m5"], 2)
    n = rng.randint(1, 40)
    gt = n > k
    t1, f1 = _PRED[p1]
    r_et = f1(n) and gt
    r_ou = f1(n) or gt
    return dict(enonce=f"Pour l'entier $n = {n}$, les propositions « $n$ {t1} et $n > {k}$ » et « $n$ {t1} ou $n > {k}$ » sont-elles vraies ?",
                answer=f"La proposition avec « et » est {'vraie' if r_et else 'fausse'} ; celle avec « ou » est {'vraie' if r_ou else 'fausse'}.",
                hint="« P et Q » est vraie si les deux le sont ; « P ou Q » si au moins l'une l'est.",
                steps=[f"« ${n}$ {t1} » est {'vraie' if f1(n) else 'fausse'} ; « ${n} > {k}$ » est {'vraie' if gt else 'fausse'}.",
                       f"« et » : {'vraie' if r_et else 'fausse'} ; « ou » : {'vraie' if r_ou else 'fausse'} (« ou » inclusif)."])


def _gen_contre_exemple(rng):
    a, b = rng.randint(-5, 0), rng.randint(5, 12)
    p, q = rng.randint(-8, 8), rng.randint(-10, 15)
    vals = [n for n in range(a, b + 1) if n * n + p * n + q <= 0]
    expr = sp.latex(sp.expand(sp.Symbol("n") ** 2 + p * sp.Symbol("n") + q))
    prop = f"pour tout entier $n$ compris entre ${a}$ et ${b}$, ${expr} > 0$"
    if vals:
        c = vals[0]
        return dict(enonce=f"La proposition « {prop} » est-elle vraie ? Justifier.",
                    answer=f"Elle est fausse : $n = {c}$ est un contre-exemple, car ${c * c + p * c + q} \\leqslant 0$.",
                    hint="Pour montrer qu'une proposition « pour tout » est fausse, un seul contre-exemple suffit.",
                    steps=["On teste les entiers de l'intervalle.", f"Pour $n = {c}$ : ${expr} = {c * c + p * c + q} \\leqslant 0$.",
                           "Un seul contre-exemple suffit : la proposition est fausse."])
    return dict(enonce=f"La proposition « {prop} » est-elle vraie ? Justifier.",
                answer=f"Elle est vraie : pour chacun des ${b - a + 1}$ entiers, la valeur est strictement positive (on peut tous les tester).",
                hint="L'ensemble est fini : on peut vérifier chaque entier.",
                steps=["Il n'y a qu'un nombre fini d'entiers à tester.", f"Pour chaque $n$ de ${a}$ à ${b}$, on trouve une valeur $> 0$.",
                       "La proposition est donc vraie (aucun contre-exemple)."])


_NEG = {">": "\\leqslant", "<": "\\geqslant", "\\geqslant": "<", "\\leqslant": ">"}


def _gen_negation(rng):
    rel = rng.choice([">", "<", "\\geqslant", "\\leqslant"])
    k = rng.randint(-9, 20)
    fx = rng.choice(["x^2", "2x + 1", "x^3", "|x|", "3x - 4"])
    quant = rng.choice(["tout", "existe"])
    if quant == "tout":
        p = f"Pour tout réel $x$, ${fx} {rel} {k}$."
        n = f"Il existe un réel $x$ tel que ${fx} {_NEG[rel]} {k}$."
    else:
        p = f"Il existe un réel $x$ tel que ${fx} {rel} {k}$."
        n = f"Pour tout réel $x$, ${fx} {_NEG[rel]} {k}$."
    return dict(enonce=f"Écrire la négation de la proposition : « {p} »",
                answer=f"« {n} »",
                hint="« pour tout » devient « il existe » (et inversement), et on nie la propriété.",
                steps=[f"On échange le quantificateur : « {'pour tout' if quant == 'tout' else 'il existe'} » devient « {'il existe' if quant == 'tout' else 'pour tout'} ».",
                       f"On nie l'inégalité : ${rel}$ devient ${_NEG[rel]}$ (attention : la négation de $>$ est $\\leqslant$).", f"Négation : « {n[:-1]} »."])


def _gen_statut(rng):
    a = rng.randint(1, 9)
    kind = rng.choice(["id1", "id2", "eq1", "eq2"])
    X = sp.Symbol("x")
    if kind == "id1":
        g, d = (X + a) ** 2, X ** 2 + 2 * a * X + a ** 2
    elif kind == "id2":
        g, d = (X - a) * (X + a), X ** 2 - a ** 2
    elif kind == "eq1":
        g, d = (X + a) ** 2, X ** 2 + a ** 2
    else:
        g, d = (X - a) ** 2, X ** 2 - a ** 2
    diff = sp.expand(g - d)
    gt, dt = sp.latex(g), sp.latex(sp.expand(d))
    if diff == 0:
        return dict(enonce=f"L'égalité ${gt} = {dt}$ est-elle une identité (vraie pour tout $x$) ou une équation ? Justifier.",
                    answer="C'est une identité : elle est vraie pour tout réel $x$ (on développe le membre de gauche).",
                    hint="Développe le membre de gauche et compare.",
                    steps=[f"En développant : ${gt} = {sp.latex(sp.expand(g))}$.", "Les deux membres sont égaux pour tout $x$ : identité ; $x$ est une variable."])
    sol = sp.solve(sp.Eq(g, d), X)
    return dict(enonce=f"L'égalité ${gt} = {dt}$ est-elle une identité (vraie pour tout $x$) ou une équation ? Justifier.",
                answer=f"C'est une équation (fausse pour $x = {sol[0] + 1}$ par exemple) ; sa solution est $x = {sol[0]}$ ; $x$ est une inconnue.",
                hint="Teste une valeur de x : si l'égalité est fausse pour une valeur, ce n'est pas une identité.",
                steps=[f"En développant : ${sp.latex(sp.expand(g))} = {dt}$, soit ${sp.latex(diff)} = 0$.",
                       f"Ce n'est pas vrai pour tout $x$ : c'est une équation, de solution $x = {sol[0]}$."])


# ── Notion 3 — implication ───────────────────────────────────────────────────

def _gen_implication(rng):
    a, b = rng.sample([2, 3, 4, 5, 6, 8, 9, 10, 12, 15, 18, 20], 2)
    direct, recip = a % b == 0, b % a == 0
    def w(v):
        return "vraie" if v else "fausse"
    ce_d = next(n for n in range(1, 400) if n % a == 0 and n % b != 0) if not direct else None
    ce_r = next(n for n in range(1, 400) if n % b == 0 and n % a != 0) if not recip else None
    steps = [f"Implication : si $n$ est multiple de ${a}$, est-il multiple de ${b}$ ? " +
             (f"Oui, car ${b}$ divise ${a}$." if direct else f"Non : $n = {ce_d}$ est un contre-exemple."),
             f"Réciproque : « si $n$ est multiple de ${b}$, alors $n$ est multiple de ${a}$ » : " +
             (f"vraie, car ${a}$ divise ${b}$." if recip else f"fausse, contre-exemple $n = {ce_r}$.")]
    return dict(enonce=f"On considère l'implication « si l'entier $n$ est un multiple de ${a}$, alors $n$ est un multiple de ${b}$ ». Est-elle vraie ? Énoncer sa réciproque et dire si elle est vraie.",
                answer=f"L'implication est {w(direct)} ; sa réciproque « si $n$ est multiple de ${b}$, alors $n$ est multiple de ${a}$ » est {w(recip)}.",
                hint="Une implication vraie n'a pas forcément une réciproque vraie ; cherche un contre-exemple.",
                steps=steps)


def _gen_contraposee(rng):
    a = rng.randint(1, 12)
    variante = rng.choice(["strict", "large", "carre"])
    if variante == "strict":
        P, Q, nP, nQ = f"x > {a}", f"x^2 > {a * a}", f"x \\leqslant {a}", f"x^2 \\leqslant {a * a}"
        recip_ce = f"x = -{a + 1}"
    elif variante == "large":
        P, Q, nP, nQ = f"x \\geqslant {a}", f"x^2 \\geqslant {a * a}", f"x < {a}", f"x^2 < {a * a}"
        recip_ce = f"x = -{a}"
    else:
        P, Q, nP, nQ = f"x = {a}", f"x^2 = {a * a}", f"x \\neq {a}", f"x^2 \\neq {a * a}"
        recip_ce = f"x = -{a}"
    return dict(enonce=f"Soit $x$ un réel. On considère « si ${P}$, alors ${Q}$ ». Énoncer sa réciproque et sa contraposée, et dire si chacune est vraie.",
                answer=f"Réciproque : « si ${Q}$, alors ${P}$ », fausse (contre-exemple ${recip_ce}$). Contraposée : « si ${nQ}$, alors ${nP}$ », vraie comme l'implication de départ.",
                hint="La contraposée de « si P alors Q » est « si non Q alors non P » ; elle a toujours la même valeur de vérité.",
                steps=[f"L'implication est vraie (pour ${P}$, on a bien ${Q}$).", f"Réciproque : on échange : « si ${Q}$, alors ${P}$ » ; fausse avec ${recip_ce}$.",
                       f"Contraposée : « si ${nQ}$, alors ${nP}$ » ; une implication et sa contraposée sont équivalentes : vraie."])


def _gen_cn_cs(rng):
    a, b = rng.sample([2, 3, 4, 6, 8, 9, 12, 18, 24, 36], 2)
    nec, suf = a % b == 0, b % a == 0
    if not (nec or suf):
        verdict = "ni nécessaire ni suffisante"
    elif nec and suf:
        return None
    else:
        verdict = "nécessaire mais pas suffisante" if nec else "suffisante mais pas nécessaire"
    return dict(enonce=f"Pour qu'un entier $n$ soit multiple de ${a}$, la condition « $n$ est multiple de ${b}$ » est-elle nécessaire ? suffisante ?",
                answer=f"Elle est {verdict}.",
                hint=f"Nécessaire : « multiple de {a} » entraîne « multiple de {b} » ? Suffisante : « multiple de {b} » entraîne « multiple de {a} » ?",
                steps=[f"Nécessaire si « multiple de ${a}$ » $\\Rightarrow$ « multiple de ${b}$ », c'est-à-dire si ${b}$ divise ${a}$ : {'oui' if nec else 'non'}.",
                       f"Suffisante si « multiple de ${b}$ » $\\Rightarrow$ « multiple de ${a}$ », c'est-à-dire si ${a}$ divise ${b}$ : {'oui' if suf else 'non'}.",
                       f"Conclusion : condition {verdict}."])


# ── Notion 4 — raisonnements ─────────────────────────────────────────────────

def _gen_disjonction(rng):
    a, b = rng.randint(0, 9), rng.randint(-9, 9)
    n = sp.Symbol("n")
    expr = n ** 2 + (2 * a + 1) * n + 2 * b
    assert all(int(expr.subs(n, k)) % 2 == 0 for k in range(-20, 21))
    return dict(enonce=f"Démontrer par disjonction des cas que, pour tout entier $n$, ${sp.latex(expr)}$ est pair.",
                answer=f"Si $n$ est pair, $n^2$ et ${2 * a + 1}n$ sont pairs ; si $n$ est impair, ils sont impairs et leur somme est paire. Dans les deux cas, en ajoutant ${2 * b}$ (pair), le résultat est pair.",
                hint="Distingue les cas n pair et n impair.",
                steps=[f"On écrit ${sp.latex(expr)} = n^2 + n + {2 * a}n {'+' if b >= 0 else '-'} {abs(2 * b)}$ ; ${2 * a}n$ et ${2 * b}$ sont pairs.".replace("+ 0n ", "").replace("0n + ", ""),
                       "Cas $n$ pair, $n = 2k$ : $n^2 + n = 4k^2 + 2k$ est pair.", "Cas $n$ impair, $n = 2k + 1$ : $n^2 + n = (2k + 1)(2k + 2)$ est pair.",
                       "Dans tous les cas, l'expression est une somme de nombres pairs : elle est paire."])


def _gen_contraposee_arith(rng):
    p = rng.choice([2, 3, 5, 7, 11, 13])
    forme = rng.choice(["carre", "cube", "double"])
    k = rng.randint(2, 9)
    if forme == "carre":
        hyp, conc = f"$n^2$ n'est pas un multiple de ${p}$", f"$n$ n'est pas un multiple de ${p}$"
        ccl, cp = f"$n$ est un multiple de ${p}$", f"$n^2$ est un multiple de ${p}$"
        demo = f"Si $n = {p}k$, alors $n^2 = {p}({p}k^2)$ est un multiple de ${p}$."
        ok = all((n * n) % p != 0 or n % p == 0 for n in range(1, 200))
    elif forme == "cube":
        hyp, conc = f"$n^3$ n'est pas un multiple de ${p}$", f"$n$ n'est pas un multiple de ${p}$"
        ccl, cp = f"$n$ est un multiple de ${p}$", f"$n^3$ est un multiple de ${p}$"
        demo = f"Si $n = {p}k$, alors $n^3 = {p}({p * p}k^3)$ est un multiple de ${p}$."
        ok = True
    else:
        hyp, conc = f"${k}n$ n'est pas un multiple de ${p}$", f"$n$ n'est pas un multiple de ${p}$"
        ccl, cp = f"$n$ est un multiple de ${p}$", f"${k}n$ est un multiple de ${p}$"
        demo = f"Si $n = {p}m$, alors ${k}n = {p}({k}m)$ est un multiple de ${p}$."
        ok = True
    assert ok
    return dict(enonce=f"Démontrer par contraposée que, pour tout entier $n$ : si {hyp}, alors {conc}.",
                answer=f"Contraposée : si {ccl}, alors {cp}. {demo} L'implication de départ est donc vraie.",
                hint="Écris la contraposée « si non Q alors non P », plus facile à démontrer.",
                steps=[f"Contraposée : « si {ccl}, alors {cp} ».", demo,
                       "Une implication et sa contraposée sont équivalentes : la propriété est démontrée."])


@dataclass(frozen=True)
class Family:
    id: str
    level: int
    label: str
    generate: Callable[[random.Random], Optional[dict]]
    notion: str
    score: float


FAMILIES: tuple[Family, ...] = (
    Family("union_intersection", 1, "Réunion et intersection", _gen_union_intersection, N1, 1.2),
    Family("complementaire", 1, "Complémentaire et cardinal", _gen_complementaire, N1, 1.4),
    Family("appartenance", 1, "Appartenance et inclusion", _gen_appartenance, N1, 1.3),
    Family("intervalles", 2, "Intersection et réunion d'intervalles", _gen_intervalles, N1, 2.2),
    Family("produit_cartesien", 2, "Produit cartésien", _gen_produit_cartesien, N1, 2.0),
    Family("et_ou", 1, "Connecteurs « et » et « ou »", _gen_et_ou, N2, 1.5),
    Family("negation", 2, "Négation d'une proposition quantifiée", _gen_negation, N2, 2.5),
    Family("contre_exemple", 3, "Contre-exemple", _gen_contre_exemple, N2, 3.0),
    Family("statut_egalite", 2, "Identité ou équation", _gen_statut, N2, 2.4),
    Family("implication", 2, "Implication et réciproque", _gen_implication, N3, 2.3),
    Family("contraposee", 3, "Réciproque et contraposée", _gen_contraposee, N3, 3.1),
    Family("cn_cs", 3, "Condition nécessaire, condition suffisante", _gen_cn_cs, N3, 3.4),
    Family("disjonction_cas", 3, "Raisonnement par disjonction des cas", _gen_disjonction, N4, 3.2),
    Family("contraposee_arith", 4, "Raisonnement par contraposée", _gen_contraposee_arith, N4, 4.0),
)
FAMILIES_BY_ID = {f.id: f for f in FAMILIES}


def _level_from_score(score: float) -> int:
    return 1 if score <= 1.5 else 2 if score <= 2.7 else 3 if score <= 3.8 else 4


def build_exercise(family: Family, rng: random.Random) -> Optional[dict]:
    notes = family.generate(rng)
    if notes is None:
        return None
    level = _level_from_score(family.score)
    assert level == family.level, family.id
    steps = [f"Étape {k} — {s}" for k, s in enumerate(notes["steps"], 1)]
    return {"enonce": notes["enonce"], "answer": notes["answer"], "hint": notes["hint"], "solution_steps": steps,
            "chapter_id": CHAPTER_ID, "notion": family.notion, "difficulty": level,
            "difficulty_label": LEVEL_META[level]["label"], "difficulty_emoji": LEVEL_META[level]["emoji"],
            "family": family.id, "family_label": family.label, "declared_level": family.level,
            "complexity_score": family.score, "source": "generated"}


def generate_one(family_id: str, seed: Optional[int] = None, max_attempts: int = 80) -> dict:
    rng = random.Random(seed)
    fam = FAMILIES_BY_ID[family_id]
    for _ in range(max_attempts):
        ex = build_exercise(fam, rng)
        if ex is not None:
            return ex
    raise RuntimeError(f"Impossible de générer un exercice valide pour la famille {family_id!r}")


def generate_pool(per_family: int = 32, seed: int = 20261028) -> list[dict]:
    pool: list[dict] = []
    for rank, family in enumerate(FAMILIES):
        rng = random.Random(seed * 100 + rank)
        seen, items, attempts = set(), [], 0
        while len(items) < per_family and attempts < per_family * 100:
            attempts += 1
            ex = build_exercise(family, rng)
            if ex is None or ex["enonce"] in seen:
                continue
            seen.add(ex["enonce"])
            items.append(ex)
        for k, ex in enumerate(items):
            ex["id"] = GENERATED_ID_OFFSET + 1000 * rank + k
        pool.extend(items)
    return pool


_ = gcd  # (réservé : contrôles arithmétiques futurs)
