"""Génération d'exercices d'algorithmique et de programmation (Première,
Chapitre_12 : « Algorithmique et programmation : listes », programme 2026).

Chaque exercice montre un court programme Python et demande ce qu'il affiche
(ou la valeur d'une variable). Garantie de correction : le programme AFFICHÉ
est exactement celui qui est EXÉCUTÉ au moment du tirage (exec dans un espace
de noms restreint, sans import ni accès système) ; la réponse publiée est la
sortie réellement produite. Aucun résultat n'est saisi à la main.

Même contrat que les autres modules du programme 2026 (derivation_2026.py) :
une notion par famille, identifiants stables par famille
(GENERATED_ID_OFFSET + 1000 × rang + k).
"""
import random
from dataclasses import dataclass
from typing import Callable, Optional

CHAPTER_ID = "Chapitre_12"
N1 = "Variables, instructions conditionnelles et boucles"
N2 = "Fonctions et programmation modulaire"
N3 = "Générer une liste"
N4 = "Manipuler et parcourir une liste"

GENERATED_ID_OFFSET = 1_140_000

LEVEL_META = {
    1: {"emoji": "🟢", "label": "Niveau 1 — Fondamental"},
    2: {"emoji": "🟡", "label": "Niveau 2 — Intermédiaire"},
    3: {"emoji": "🟠", "label": "Niveau 3 — Avancé"},
    4: {"emoji": "🔴", "label": "Niveau 4 — Difficile"},
}

_ENT = (("&", "&amp;"), ("*", "&#42;"), ("/", "&#47;"), ("^", "&#94;"), ("<", "&lt;"), (">", "&gt;"))


def code(s: str) -> str:
    """Code affiché tel quel (voir tools/premiere/banque_commun.code) ;
    l'indentation est rendue par des espaces insécables."""
    body = s.lstrip(" ")
    indent = len(s) - len(body)
    for c, ent in _ENT:
        body = body.replace(c, ent)
    return f"<code>{'&nbsp;' * indent}{body}</code>"


def prog(src: str) -> str:
    """Programme sur plusieurs lignes (les sauts de ligne deviennent <br>)."""
    return "\n" + "\n".join(code(line) for line in src.strip("\n").split("\n")) + "\n"


_SAFE = {"range": range, "len": len, "sum": sum, "max": max, "min": min, "abs": abs, "round": round, "list": list}


def run(src: str) -> str:
    """Exécute le programme affiché et renvoie ce qu'il imprime."""
    out = []

    def _print(*args):
        out.append(" ".join(str(a) for a in args))

    # Un seul espace de noms : une fonction doit pouvoir appeler une autre
    # fonction définie dans le même programme.
    exec(src, {"__builtins__": dict(_SAFE, print=_print)})  # noqa: S102 — programme généré ou cité, jamais saisi par un élève
    return "\n".join(out)


def _plus(b) -> str:
    """« + 4 », « - 4 » ou rien (terme constant dans du code)."""
    return f" + {b}" if b > 0 else (f" - {-b}" if b < 0 else "")


def _p(v) -> str:
    return f"({v})" if v < 0 else f"{v}"


def _sortie(out: str) -> str:
    return " puis ".join(code(line) for line in out.split("\n"))


# ── Notion 1 — variables, conditions, boucles ────────────────────────────────

def _gen_affectations(rng):
    p, q = rng.randint(-9, 9), rng.randint(-9, 9)
    if p == q:
        return None
    src = f"a = {p}\nb = {q}\na = a + b\nb = a - b\na = a - b\nprint(a, b)"
    out = run(src)
    return dict(src=src, out=out, hint="Suis l'évolution de a et b ligne par ligne, dans un tableau.",
                steps=[f"Après les deux premières lignes : a = {p}, b = {q}.", f"a = a + b donne a = {p + q}.",
                       f"b = a - b donne b = {p + q} - {_p(q)} = {p}.",
                       f"a = a - b donne a = {p + q} - {_p(p)} = {q} : les valeurs ont été échangées."])


def _gen_boucle_somme(rng):
    a = rng.randint(0, 3)
    b = a + rng.randint(3, 7)
    c = rng.randint(1, 5)
    src = f"s = 0\nfor i in range({a}, {b}):\n    s = s + {c} * i\nprint(s)"
    out = run(src)
    vals = list(range(a, b))
    return dict(src=src, out=out, hint=f"range({a}, {b}) donne les entiers de {a} à {b - 1}.",
                steps=[f"i prend successivement les valeurs {', '.join(map(str, vals))}.",
                       f"s = {c} × ({' + '.join(map(str, vals))}) = {c} × {sum(vals)}.", f"Le programme affiche {out}."])


def _gen_boucle_while(rng):
    u0, q = rng.randint(1, 5), rng.choice([2, 3])
    seuil = rng.choice([50, 80, 100, 150, 200, 300, 500])
    src = f"u = {u0}\nn = 0\nwhile u < {seuil}:\n    u = u * {q}\n    n = n + 1\nprint(n, u)"
    out = run(src)
    n, u = map(int, out.split())
    termes = [u0 * q ** k for k in range(n + 1)]
    return dict(src=src, out=out, hint=f"On multiplie u par {q} tant que u est strictement inférieur à {seuil}.",
                steps=[f"Valeurs successives de u : {', '.join(map(str, termes))}.", f"La boucle s'arrête dès que u ≥ {seuil}, c'est-à-dire pour u = {u}.",
                       f"Elle a tourné {n} fois : affichage {out}."])


def _gen_condition(rng):
    a, b, c, d = rng.randint(-3, 4), rng.randint(2, 5), rng.randint(-5, 5), rng.randint(1, 9)
    k1, k2 = a - rng.randint(1, 4), a + rng.randint(0, 4)
    src = f"def f(x):\n    if x < {a}:\n        return {b} * x{_plus(c)}\n    else:\n        return x * x - {d}\nprint(f({k1}), f({k2}))"
    out = run(src)
    return dict(src=src, out=out, hint=f"Pour chaque appel, teste d'abord la condition x < {a}.",
                steps=[f"f({k1}) : {k1} < {a}, donc on calcule {b} × {_p(k1)}{_plus(c)} = {b * k1 + c}.", f"f({k2}) : {k2} ≥ {a}, donc on calcule {_p(k2)}² − {d} = {k2 * k2 - d}.",
                       f"Affichage : {out}."])


# ── Notion 2 — fonctions ─────────────────────────────────────────────────────

def _gen_composees(rng):
    a, b, c, k = rng.randint(2, 5), rng.randint(-6, 6), rng.randint(1, 9), rng.randint(-3, 4)
    src = f"def f(x):\n    return {a} * x{_plus(b)}\n\ndef g(x):\n    return x * x - {c}\n\nprint(g(f({k})), f(g({k})))"
    out = run(src)
    fk, gk = a * k + b, k * k - c
    return dict(src=src, out=out, hint="Calcule d'abord l'appel le plus intérieur.",
                steps=[f"f({k}) = {fk}, puis g({fk}) = {fk * fk - c}.", f"g({k}) = {gk}, puis f({gk}) = {a * gk + b}.", f"Affichage : {out}."])


def _gen_fonction_boucle(rng):
    n = rng.randint(12, 99)
    src = f"def nb_diviseurs(n):\n    c = 0\n    for d in range(1, n + 1):\n        if n % d == 0:\n            c = c + 1\n    return c\n\nprint(nb_diviseurs({n}))"
    out = run(src)
    divs = [d for d in range(1, n + 1) if n % d == 0]
    return dict(src=src, out=out, hint="n % d == 0 signifie que d divise n.",
                steps=[f"On teste tous les entiers d de 1 à {n}.", f"Diviseurs de {n} : {', '.join(map(str, divs))}.", f"Il y en a {len(divs)} : affichage {out}."])


# ── Notion 3 — générer une liste ─────────────────────────────────────────────

def _gen_comprehension(rng):
    a, b, n = rng.randint(-3, 5), rng.randint(-5, 5), rng.randint(4, 7)
    if a == 0:
        return None
    src = f"L = [{a} * k{_plus(b)} for k in range({n})]\nprint(L)"
    out = run(src)
    return dict(src=src, out=out, hint=f"k prend les valeurs 0, 1, …, {n - 1}.",
                steps=[f"Liste en compréhension : un terme {a} × k{_plus(b)} pour chaque k de 0 à {n - 1}.", f"Affichage : {out}."])


def _gen_comprehension_condition(rng):
    a, m = rng.randint(0, 10), rng.choice([2, 3, 4, 5])
    b, r = a + rng.randint(10, 20), rng.randint(0, m - 1)
    src = f"L = [k for k in range({a}, {b}) if k % {m} == {r}]\nprint(L, len(L))"
    out = run(src)
    return dict(src=src, out=out, hint=f"On garde les k dont le reste dans la division par {m} vaut {r}.",
                steps=[f"k parcourt les entiers de {a} à {b - 1}.", f"La condition k % {m} == {r} filtre les éléments.", f"Affichage : {out}."])


def _gen_ajouts(rng):
    n, c = rng.randint(4, 7), rng.randint(0, 9)
    op = rng.choice(["i * i - {c}", "2 * i + {c}", "i * (i + 1) - {c}"]).format(c=c).replace(" + 0", "").replace(" - 0", "")
    src = f"L = []\nfor i in range(1, {n + 1}):\n    L.append({op})\nprint(L)"
    out = run(src)
    return dict(src=src, out=out, hint="append ajoute un élément à la fin de la liste.",
                steps=[f"La liste part vide ; i va de 1 à {n}.", f"À chaque tour, on ajoute {op.replace('*', '×')}.", f"Affichage : {out}."])


def _gen_liste_suite(rng):
    u0, q, r, n = rng.randint(-3, 5), rng.choice([2, 3, -2]), rng.randint(-4, 4), rng.randint(3, 6)
    src = f"u = [{u0}]\nfor i in range({n}):\n    u.append({q} * u[i]{_plus(r)})\nprint(u)"
    out = run(src)
    return dict(src=src, out=out, hint="u[i] est le dernier terme calculé avant l'ajout.",
                steps=[f"La liste contient les termes de la suite définie par u0 = {u0} et u(n+1) = {q} × u(n){_plus(r)}.",
                       f"On ajoute {n} termes.", f"Affichage : {out}."])


# ── Notion 4 — manipuler et parcourir ────────────────────────────────────────

def _liste(rng, n):
    return [rng.randint(-9, 20) for _ in range(n)]


def _gen_indices(rng):
    L = _liste(rng, rng.randint(5, 8))
    i = rng.randint(0, len(L) - 1)
    src = f"L = {L}\nprint(L[{i}], L[-1], len(L))"
    out = run(src)
    return dict(src=src, out=out, hint="Les indices commencent à 0 ; L[-1] est le dernier élément.",
                steps=[f"L[{i}] est l'élément de rang {i + 1}.", "L[-1] est le dernier élément.", f"len(L) = {len(L)}.", f"Affichage : {out}."])


def _gen_modifier(rng):
    L = _liste(rng, rng.randint(4, 6))
    x, y, k, z = rng.randint(-5, 30), rng.choice(L), rng.randint(0, 2), rng.randint(-5, 30)
    src = f"L = {L}\nL.append({x})\nL.remove({y})\nL[{k}] = {z}\nprint(L)"
    out = run(src)
    return dict(src=src, out=out, hint="remove supprime la première occurrence de la valeur indiquée.",
                steps=[f"append({x}) ajoute {x} à la fin.", f"remove({y}) supprime la première valeur {y}.", f"L[{k}] = {z} remplace l'élément d'indice {k}.",
                       f"Affichage : {out}."])


def _gen_parcours(rng):
    L = _liste(rng, rng.randint(6, 9))
    s = rng.randint(0, 10)
    src = f"L = {L}\nm = L[0]\nc = 0\nfor x in L:\n    if x > m:\n        m = x\n    if x >= {s}:\n        c = c + 1\nprint(m, c)"
    out = run(src)
    return dict(src=src, out=out, hint="m garde le plus grand élément rencontré ; c compte les éléments supérieurs ou égaux au seuil.",
                steps=[f"m est le maximum de la liste : {max(L)}.", f"c compte les éléments ≥ {s} : {sum(1 for v in L if v >= s)}.", f"Affichage : {out}."])


def _gen_moyenne(rng):
    L = [rng.randint(0, 20) for _ in range(rng.choice([4, 5, 8]))]
    src = "def moyenne(L):\n    s = 0\n    for x in L:\n        s = s + x\n    return s / len(L)\n\n" + f"print(moyenne({L}))"
    out = run(src)
    return dict(src=src, out=out, hint="La fonction additionne les éléments, puis divise par leur nombre.",
                steps=[f"Somme des éléments : {sum(L)}.", f"Nombre d'éléments : {len(L)}.", f"Moyenne : {sum(L)} / {len(L)} ; affichage {out}."])


@dataclass(frozen=True)
class Family:
    id: str
    level: int
    label: str
    generate: Callable[[random.Random], Optional[dict]]
    notion: str
    score: float


FAMILIES: tuple[Family, ...] = (
    Family("affectations", 1, "Affectations successives", _gen_affectations, N1, 1.2),
    Family("boucle_somme", 2, "Boucle for et accumulateur", _gen_boucle_somme, N1, 2.0),
    Family("condition", 2, "Instruction conditionnelle", _gen_condition, N1, 2.3),
    Family("boucle_while", 3, "Boucle while et seuil", _gen_boucle_while, N1, 3.0),
    Family("fonctions_composees", 2, "Appels de fonctions", _gen_composees, N2, 2.2),
    Family("fonction_boucle", 3, "Fonction contenant une boucle", _gen_fonction_boucle, N2, 3.2),
    Family("comprehension", 1, "Liste en compréhension", _gen_comprehension, N3, 1.4),
    Family("comprehension_condition", 2, "Compréhension avec condition", _gen_comprehension_condition, N3, 2.4),
    Family("ajouts_successifs", 2, "Ajouts successifs", _gen_ajouts, N3, 2.0),
    Family("liste_suite", 3, "Liste des termes d'une suite", _gen_liste_suite, N3, 3.1),
    Family("indices", 1, "Éléments et indices", _gen_indices, N4, 1.3),
    Family("modifier_liste", 2, "Modifier une liste", _gen_modifier, N4, 2.5),
    Family("parcours", 3, "Parcourir une liste", _gen_parcours, N4, 3.3),
    Family("moyenne_liste", 4, "Fonction sur une liste", _gen_moyenne, N4, 4.0),
)
FAMILIES_BY_ID = {f.id: f for f in FAMILIES}


def _level_from_score(score: float) -> int:
    return 1 if score <= 1.5 else 2 if score <= 2.7 else 3 if score <= 3.8 else 4


_QUESTION = {
    N1: "Qu'affiche ce programme ?",
    N2: "Qu'affiche ce programme ?",
    N3: "Quelle liste ce programme construit-il ? Qu'affiche-t-il ?",
    N4: "Qu'affiche ce programme ?",
}


def build_exercise(family: Family, rng: random.Random) -> Optional[dict]:
    notes = family.generate(rng)
    if notes is None:
        return None
    assert run(notes["src"]) == notes["out"]  # contrôle : la sortie annoncée est celle de l'exécution
    level = _level_from_score(family.score)
    assert level == family.level, family.id
    enonce = f"On considère le programme Python suivant :{prog(notes['src'])}{_QUESTION[family.notion]}"
    answer = f"Le programme affiche {_sortie(notes['out'])}."
    steps = [f"Étape {k} — {s}" for k, s in enumerate(notes["steps"], 1)]
    return {"enonce": enonce, "answer": answer, "hint": notes["hint"], "solution_steps": steps,
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


def generate_pool(per_family: int = 32, seed: int = 20261027) -> list[dict]:
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
