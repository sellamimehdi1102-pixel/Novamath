"""Génération symbolique d'exercices sur le calcul d'une image à partir de
l'expression d'une fonction (Troisième, Chapitre_7, notion
"Calculer une image à partir de l'expression d'une fonction").

30 exercices existants, 93% calcul direct — ajoute l'exercice inversé
(retrouver un antécédent en résolvant une équation, ce qui reste algébrique
et distinct de la lecture GRAPHIQUE d'un antécédent traitée séparément dans
la notion "Lire graphiquement...") et le vrai/faux justifié. Toute image ou
antécédent annoncé est calculé par sympy, jamais tapé "en dur".

Chantier « diversification des calculs » : la version initiale ne générait
QUE des fonctions affines f(x)=ax+b (même mécanique de calcul partout,
malgré des énoncés variés). On ajoute ici la fonction carrée f(x)=x², qui
EST au programme de Troisième et introduit une mécanique réellement
différente : une image négative n'a AUCUN antécédent, une image positive en
a DEUX (±√img) au lieu d'un seul comme pour l'affine — ce n'est pas qu'une
question de nombres différents, c'est un raisonnement distinct. On
n'introduit pas cube/racine/inverse ici : ce ne sont pas des fonctions
étudiées comme telles au programme de Troisième (elles arrivent en
Seconde/Première) — la contrainte « rester dans le programme » prime sur la
diversité.
"""
import random
from dataclasses import dataclass
from typing import Callable, Optional

from sympy import Eq, Rational, latex, solve, symbols

x = symbols("x")

CHAPTER_ID = "Chapitre_7"
NOTION = "Calculer une image à partir de l'expression d'une fonction"

GENERATED_ID_OFFSET = 170_000

LEVEL_META = {
    1: {"emoji": "🟢", "label": "Niveau 1 — Fondamental"},
    2: {"emoji": "🟡", "label": "Niveau 2 — Intermédiaire"},
    3: {"emoji": "🟠", "label": "Niveau 3 — Avancé"},
    4: {"emoji": "🔴", "label": "Niveau 4 — Difficile"},
}


def _nz(rng, lo, hi):
    return rng.choice([n for n in range(lo, hi + 1) if n != 0])


def _fmt_affine(a, b) -> str:
    a_str = "" if a == 1 else ("-" if a == -1 else str(a))
    if b == 0:
        return f"{a_str}x"
    return f"{a_str}x {'+' if b > 0 else '-'} {abs(b)}"


NOMS = ["f", "g", "h", "p"]


# ── 1. Calcul direct de l'image (affine OU carrée) ──────────────────────────

def _gen_calcul_direct_affine(rng):
    nom = rng.choice(NOMS)
    a = _nz(rng, -8, 8)
    b = rng.randint(-10, 10)
    x0 = rng.randint(-8, 8)
    img = a * x0 + b
    enonce = f"On donne ${nom}(x) = {_fmt_affine(a, b)}$. Calculer ${nom}({x0})$."
    steps = [
        f"Étape 1 — On remplace $x$ par ${x0}$ dans l'expression : ${nom}({x0}) = {a}\\times({x0}) {'+' if b >= 0 else '-'} {abs(b)}$.",
        f"Étape 2 — ${nom}({x0}) = {img}$.",
    ]
    answer = f"${nom}({x0}) = {img}$"
    hint = "Remplacer x par la valeur demandée dans l'expression de la fonction, puis calculer."
    return {"enonce": enonce, "answer": answer, "steps": steps, "hint": hint}


def _gen_calcul_direct_carre(rng):
    nom = rng.choice(NOMS)
    x0 = _nz(rng, -12, 12)
    img = x0 * x0
    enonce = f"On donne ${nom}(x) = x^2$ (la fonction carrée). Calculer ${nom}({x0})$."
    steps = [
        f"Étape 1 — On remplace $x$ par ${x0}$ : ${nom}({x0}) = ({x0})^2$.",
        f"Étape 2 — Attention au signe : le carré d'un nombre négatif est positif. ${nom}({x0}) = {img}$.",
    ]
    answer = f"${nom}({x0}) = {img}$"
    hint = "Le carré d'un nombre, même négatif, est toujours positif ou nul : (-x)² = x²."
    return {"enonce": enonce, "answer": answer, "steps": steps, "hint": hint}


def _gen_calcul_direct(rng):
    return rng.choice([_gen_calcul_direct_affine, _gen_calcul_direct_carre])(rng)


# ── 2. Retrouver un antécédent (exercice inversé, algébrique) ──────────────

def _gen_antecedent_affine(rng):
    nom = rng.choice(NOMS)
    a = _nz(rng, -8, 8)
    b = rng.randint(-10, 10)
    x0 = rng.randint(-8, 8)
    img = a * x0 + b
    sols = solve(Eq(a * x + b, img), x)
    if not sols or sols[0] != x0:
        return None
    enonce = f"On donne ${nom}(x) = {_fmt_affine(a, b)}$. Déterminer l'antécédent de ${img}$ par ${nom}$."
    steps = [
        f"Étape 1 — On cherche $x$ tel que ${nom}(x) = {img}$, soit ${_fmt_affine(a, b)} = {img}$.",
        f"Étape 2 — On résout : ${a}x = {img} {'-' if b >= 0 else '+'} {abs(b)} = {img - b}$, donc $x = {latex(Rational(img - b, a))}$.",
    ]
    answer = f"$x = {latex(Rational(img - b, a))}$"
    hint = "Poser l'équation f(x) = valeur donnée, puis la résoudre comme une équation du premier degré."
    return {"enonce": enonce, "answer": answer, "steps": steps, "hint": hint}


def _gen_antecedent_carre(rng):
    # Mécanique distincte de l'affine : une image strictement positive a
    # DEUX antécédents opposés (±√img), pas un seul.
    nom = rng.choice(NOMS)
    x0 = _nz(rng, 1, 11)
    img = x0 * x0
    enonce = f"On donne ${nom}(x) = x^2$. Déterminer le ou les antécédents de ${img}$ par ${nom}$."
    steps = [
        f"Étape 1 — On cherche $x$ tel que $x^2 = {img}$.",
        f"Étape 2 — Comme ${img} > 0$, il existe DEUX solutions opposées : $x = {x0}$ et $x = {-x0}$.",
    ]
    answer = f"${nom}(x) = {img}$ pour $x = {x0}$ et $x = {-x0}$ (deux antécédents)."
    hint = "Pour la fonction carrée, une image strictement positive a toujours deux antécédents opposés."
    return {"enonce": enonce, "answer": answer, "steps": steps, "hint": hint}


def _gen_antecedent(rng):
    return rng.choice([_gen_antecedent_affine, _gen_antecedent_carre])(rng)


# ── 2bis. Existence/nombre d'antécédents par la fonction carrée (raisonnement,
#          pas de calcul à proprement parler — teste la compréhension du
#          signe du carré, distinct de tout ce qui précède) ─────────────────

def _gen_carre_existence(rng):
    nom = rng.choice(NOMS)
    img = rng.choice([n for n in range(-15, 16) if n != 0])
    if img > 0:
        # On reste sur des carrés parfaits pour donner une valeur exacte simple.
        racine = None
        for k in range(1, 13):
            if k * k == img:
                racine = k
                break
        if racine is not None:
            answer = f"Oui, deux antécédents : ${racine}$ et ${-racine}$."
            steps = [
                f"Étape 1 — On cherche $x$ tel que $x^2 = {img}$, avec ${img} > 0$.",
                f"Étape 2 — ${img} = {racine}^2$, donc $x = {racine}$ ou $x = {-racine}$.",
            ]
        else:
            answer = f"Oui, deux antécédents opposés existent (car ${img} > 0$), mais ce ne sont pas des nombres entiers."
            steps = [
                f"Étape 1 — On cherche $x$ tel que $x^2 = {img}$.",
                f"Étape 2 — Comme ${img} > 0$, une solution positive et une solution négative opposée existent forcément, même si elles ne sont pas entières.",
            ]
    else:
        answer = f"Non, aucun antécédent : un carré ne peut jamais être négatif (${img} < 0$)."
        steps = [
            f"Étape 1 — On cherche $x$ tel que $x^2 = {img}$.",
            f"Étape 2 — Or un carré est toujours positif ou nul, il ne peut jamais valoir ${img}$ (négatif). Aucune solution n'existe.",
        ]
    enonce = f"Le nombre ${img}$ a-t-il un ou des antécédents par la fonction carrée ? Justifier sans calculer de racine si ce n'est pas nécessaire."
    hint = "Un carré est toujours positif ou nul : un nombre négatif n'a jamais d'antécédent par la fonction carrée."
    return {"enonce": enonce, "answer": answer, "steps": steps, "hint": hint}


# ── 3. Vérifier une image annoncée (vrai/faux, affine OU carré) ─────────────

def _gen_verifier_affine(rng):
    nom = rng.choice(NOMS)
    a = _nz(rng, -8, 8)
    b = rng.randint(-10, 10)
    x0 = rng.randint(-8, 8)
    correct = a * x0 + b
    is_correct = rng.random() < 0.5
    proposed = correct if is_correct else correct + rng.choice([1, -1, 2, -2, 3])
    enonce = f"On donne ${nom}(x) = {_fmt_affine(a, b)}$. Un élève affirme que ${nom}({x0}) = {proposed}$. A-t-il raison ? Justifier."
    steps = [
        f"Étape 1 — On calcule soi-même : ${nom}({x0}) = {a}\\times({x0}) {'+' if b >= 0 else '-'} {abs(b)} = {correct}$.",
        "Étape 2 — On compare à la valeur annoncée.",
    ]
    answer = f"Vrai : ${nom}({x0}) = {correct}$." if is_correct else f"Faux : ${nom}({x0}) = {correct}$, pas ${proposed}$."
    hint = "Toujours recalculer soi-même l'image avant de juger une valeur annoncée."
    return {"enonce": enonce, "answer": answer, "steps": steps, "hint": hint}


def _gen_verifier_carre(rng):
    # Le piège classique testé ici : annoncer une image NÉGATIVE pour la
    # fonction carrée (impossible) — erreur de nature différente du vrai/faux
    # affine, qui ne porte que sur une valeur numérique inexacte.
    nom = rng.choice(NOMS)
    x0 = _nz(rng, -10, 10)
    correct = x0 * x0
    is_correct = rng.random() < 0.5
    if is_correct:
        proposed = correct
    else:
        proposed = rng.choice([-correct, correct + rng.choice([1, -1, 2, -2])])
    enonce = f"On donne ${nom}(x) = x^2$. Un élève affirme que ${nom}({x0}) = {proposed}$. A-t-il raison ? Justifier."
    steps = [
        f"Étape 1 — On calcule soi-même : ${nom}({x0}) = ({x0})^2 = {correct}$.",
        "Étape 2 — On compare à la valeur annoncée (un carré ne peut jamais être négatif).",
    ]
    answer = f"Vrai : ${nom}({x0}) = {correct}$." if is_correct else f"Faux : ${nom}({x0}) = {correct}$, pas ${proposed}$."
    hint = "Un carré est toujours positif ou nul : une image négative annoncée pour x² est automatiquement fausse."
    return {"enonce": enonce, "answer": answer, "steps": steps, "hint": hint}


def _gen_verifier(rng):
    return rng.choice([_gen_verifier_affine, _gen_verifier_carre])(rng)


# ── 4. Erreur à corriger (affine : priorité opératoire / carré : signe) ─────

def _gen_erreur_a_corriger_carre(rng):
    # Erreur classique et très fréquente en Troisième : un élève calcule
    # (-x0)^2 en écrivant -x0^2 (il oublie de mettre le signe entre
    # parenthèses), ce qui change le signe du résultat — erreur de nature
    # différente de la priorité opératoire affine ci-dessous.
    nom = rng.choice(NOMS)
    x0 = _nz(rng, -12, -2)  # toujours négatif : c'est là que l'erreur se produit
    correct = x0 * x0
    wrong = -(x0 * x0)
    enonce = (
        f"Un élève calcule ${nom}({x0})$ pour ${nom}(x) = x^2$ ainsi : "
        f"\"${nom}({x0}) = -{abs(x0)}^2 = {wrong}$\" (il oublie de mettre le signe négatif entre parenthèses). "
        "Identifier son erreur et donner le résultat correct."
    )
    steps = [
        f"Étape 1 — Il fallait calculer $({x0})^2$ (le signe fait partie du nombre élevé au carré), pas $-{abs(x0)}^2$ (qui calcule $-({abs(x0)}^2)$).",
        f"Étape 2 — Le calcul correct est $({x0})^2 = {correct}$ (un carré est toujours positif ou nul).",
    ]
    answer = f"Erreur de signe (parenthèses oubliées) ; le résultat correct est ${nom}({x0}) = {correct}$."
    hint = "Pour élever un nombre négatif au carré, toujours le mettre entre parenthèses : (-x)² ≠ -x²."
    return {"enonce": enonce, "answer": answer, "steps": steps, "hint": hint}


def _gen_erreur_a_corriger_affine(rng):
    nom = rng.choice(NOMS)
    a = _nz(rng, 2, 8)
    b = rng.randint(-10, 10)
    if b == 0:
        return None
    x0 = _nz(rng, -8, 8)
    correct = a * x0 + b
    # Erreur classique : additionner a et b d'abord, puis multiplier par x0.
    wrong = (a + b) * x0
    if wrong == correct:
        return None
    enonce = (
        f"Un élève calcule ${nom}({x0})$ pour ${nom}(x) = {_fmt_affine(a, b)}$ ainsi : "
        f"\"$({a}{'+' if b >= 0 else ''}{b})\\times({x0}) = {wrong}$\" (il additionne $a$ et $b$ avant de multiplier par $x$). "
        "Identifier son erreur et donner le résultat correct."
    )
    steps = [
        f"Étape 1 — Il faut d'abord multiplier ${a}$ par ${x0}$ (le terme en $x$), PUIS ajouter ${b}$ — pas l'inverse.",
        f"Étape 2 — Le calcul correct est ${a}\\times({x0}) {'+' if b >= 0 else '-'} {abs(b)} = {correct}$.",
    ]
    answer = f"Erreur de priorité opératoire ; le résultat correct est ${nom}({x0}) = {correct}$."
    hint = "Respecter les priorités opératoires : la multiplication par x se fait avant l'addition de la constante."
    return {"enonce": enonce, "answer": answer, "steps": steps, "hint": hint}


def _gen_erreur_a_corriger(rng):
    return rng.choice([_gen_erreur_a_corriger_affine, _gen_erreur_a_corriger_carre])(rng)


# ── 5. Contexte réel (tarif, calculer un prix) ───────────────────────────────

def _gen_contexte(rng):
    grandeur, unite, var, de_var, var_unite = rng.choice([
        ("le prix d'une course de taxi", "€", "le nombre de kilomètres", "du nombre de kilomètres", "km"),
        ("le coût total d'un abonnement", "€", "le nombre de mois", "du nombre de mois", "mois"),
        ("la masse totale d'un colis avec son emballage", "kg", "le nombre d'objets identiques ajoutés", "du nombre d'objets identiques ajoutés", "objet(s)"),
    ])
    a = _nz(rng, 1, 6)
    b = rng.randint(0, 15)
    x0 = rng.randint(1, 15)
    img = a * x0 + b
    enonce = (
        f"On modélise {grandeur} (en {unite}) en fonction {de_var} par $f(x) = {_fmt_affine(a, b)}$. "
        f"Calculer $f({x0})$ et interpréter le résultat dans ce contexte."
    )
    steps = [
        f"Étape 1 — $f({x0}) = {a}\\times({x0}) {'+' if b >= 0 else '-'} {abs(b)} = {img}$.",
        f"Étape 2 — Pour {x0} {var_unite}, {grandeur} vaut {img} {unite}.",
    ]
    answer = f"$f({x0}) = {img}$ {unite}."
    hint = "Remplacer x par la valeur donnée dans l'expression, puis relier le résultat obtenu à l'unité du contexte."
    return {"enonce": enonce, "answer": answer, "steps": steps, "hint": hint}


@dataclass(frozen=True)
class Family:
    id: str
    level: int
    label: str
    generate: Callable[[random.Random], Optional[dict]]
    structure_hint: str
    rule_hint: str


FAMILY_BASE_SCORE: dict[str, float] = {
    "calcul_direct": 1.0,
    "verifier": 2.0,
    "contexte": 2.4,
    "antecedent": 3.0,
    "carre_existence": 3.3,
    "erreur_a_corriger": 3.6,
}

FAMILIES: tuple[Family, ...] = (
    Family("calcul_direct", 1, "Calcul direct d'une image (affine ou carrée)", _gen_calcul_direct,
           "une valeur de x à substituer, avec f affine ou f(x)=x²", "remplacer x par la valeur donnée puis calculer"),
    Family("verifier", 2, "Vérifier une image annoncée (vrai/faux)", _gen_verifier,
           "une image annoncée, correcte ou non", "recalculer avant de juger"),
    Family("contexte", 2, "Problème contextualisé", _gen_contexte,
           "une situation concrète modélisée par une fonction affine", "calculer l'image puis l'interpréter avec l'unité du contexte"),
    Family("antecedent", 3, "Retrouver un/des antécédent(s) (affine ou carré)", _gen_antecedent,
           "une image donnée dont on cherche le ou les antécédents", "résoudre f(x) = valeur donnée (deux solutions possibles pour x²)"),
    Family("carre_existence", 3, "Existence d'antécédents par la fonction carrée", _gen_carre_existence,
           "un nombre dont on doit juger, sans calculer, s'il a des antécédents", "un carré est toujours positif ou nul"),
    Family("erreur_a_corriger", 4, "Détecter et corriger une erreur (priorité opératoire ou signe)", _gen_erreur_a_corriger,
           "un calcul erroné, affine ou carré", "multiplier avant d'ajouter la constante, ou mettre le signe entre parenthèses au carré"),
)

FAMILIES_BY_ID = {f.id: f for f in FAMILIES}


def _difficulty_bucket_from_score(score: float) -> int:
    if score <= 1.5:
        return 1
    if score <= 2.2:
        return 2
    if score <= 3.2:
        return 3
    return 4


def build_exercise(family: Family, rng: random.Random) -> Optional[dict]:
    notes = family.generate(rng)
    if notes is None:
        return None
    score = FAMILY_BASE_SCORE[family.id]
    real_level = _difficulty_bucket_from_score(score)
    hint = notes.get("hint") or f"Reconnais {family.structure_hint} : {family.rule_hint}."
    return {
        "enonce": notes["enonce"],
        "answer": notes["answer"],
        "hint": hint,
        "solution_steps": notes["steps"],
        "chapter_id": CHAPTER_ID,
        "notion": NOTION,
        "difficulty": real_level,
        "difficulty_label": LEVEL_META[real_level]["label"],
        "difficulty_emoji": LEVEL_META[real_level]["emoji"],
        "family": family.id,
        "family_label": family.label,
        "declared_level": family.level,
        "complexity_score": score,
        "source": "generated",
    }


def generate_one(family_id: str, seed: Optional[int] = None, max_attempts: int = 25) -> dict:
    rng = random.Random(seed)
    fam = FAMILIES_BY_ID[family_id]
    for _ in range(max_attempts):
        ex = build_exercise(fam, rng)
        if ex is not None:
            return ex
    raise RuntimeError(f"Impossible de générer un exercice valide pour la famille {family_id!r}")


def generate_pool(per_family: int = 6, seed: int = 30260108) -> list[dict]:
    rng = random.Random(seed)
    per_family_pool: dict[str, list[dict]] = {}
    for family in FAMILIES:
        seen_signatures = set()
        items = []
        attempts = 0
        while len(items) < per_family and attempts < per_family * 80:
            attempts += 1
            ex = build_exercise(family, rng)
            if ex is None:
                continue
            signature = (ex["family"], ex["enonce"])
            if signature in seen_signatures:
                continue
            seen_signatures.add(signature)
            items.append(ex)
        per_family_pool[family.id] = items

    pool: list[dict] = []
    idx = 0
    while any(per_family_pool.values()):
        family = FAMILIES[idx % len(FAMILIES)]
        bucket = per_family_pool.get(family.id) or []
        if bucket:
            pool.append(bucket.pop(0))
        idx += 1
        if idx > 200000:
            break
    for i, ex in enumerate(pool):
        ex["id"] = GENERATED_ID_OFFSET + i
    return pool
