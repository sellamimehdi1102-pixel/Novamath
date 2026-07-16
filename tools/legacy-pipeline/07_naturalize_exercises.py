"""
Convertisseur déterministe LaTeX -> notation mathématique lisible, pour
exercises_bank.json.

Objectif (révisé le 2026-07-13) : que l'élève lise "A = 7⁵ × 7⁻² / 7⁴" ou
"√75", comme dans un manuel scolaire, PLUTÔT que "A = 7 puissance 5 fois 7
puissance (-2) sur 7 puissance 4" (ancienne approche : tout épeler en mots
français). Le langage mathématique (×, ÷, √, exposants en exposant réel,
fractions simples "a/b", ∈, ≥, ℝ...) est toujours préférable à une phrase qui
décrit le calcul — sauf pour les constructions trop complexes pour du texte
brut (vecteurs, systèmes d'équations, coordonnées indexées non simplifiables
comme x_A), qui sont alors isolées entre $...$ pour que KaTeX les affiche
correctement (déjà utilisé partout ailleurs sur le site), sans jamais
entraîner tout le reste de la phrase française dans le rendu mathématique.

Note d'implémentation : exercises_bank.json n'entoure pas systématiquement
les seuls jetons mathématiques de $...$ — parfois c'est la phrase entière
(prose comprise) qui est encadrée, parfois rien ne l'est. On ignore donc ces
délimiteurs d'origine (retirés en tout début de traitement) et on ré-encadre
nous-mêmes, précisément, uniquement les fragments qui doivent réellement
passer par KaTeX.

Ce script :
- NE MODIFIE PAS exercises_bank.json (lecture seule).
- Écrit exercises_bank_natural.json (nouveau fichier), consommé par le
  backend Flask (webapp/server.py) de façon additive et optionnelle : si ce
  fichier est absent, l'application continue de fonctionner avec les
  énoncés originaux.
"""
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
SOURCE_PATH = ROOT / "exercises_bank.json"
OUTPUT_PATH = ROOT / "exercises_bank_natural.json"

SUP_DIGITS = {"0": "⁰", "1": "¹", "2": "²", "3": "³", "4": "⁴", "5": "⁵",
              "6": "⁶", "7": "⁷", "8": "⁸", "9": "⁹", "+": "⁺", "-": "⁻"}
SUP_LETTERS = {"a": "ᵃ", "b": "ᵇ", "c": "ᶜ", "d": "ᵈ", "e": "ᵉ", "f": "ᶠ",
               "g": "ᵍ", "h": "ʰ", "i": "ⁱ", "j": "ʲ", "k": "ᵏ", "l": "ˡ",
               "m": "ᵐ", "n": "ⁿ", "o": "ᵒ", "p": "ᵖ", "r": "ʳ", "s": "ˢ",
               "t": "ᵗ", "u": "ᵘ", "v": "ᵛ", "w": "ʷ", "x": "ˣ", "y": "ʸ",
               "z": "ᶻ"}
SUP_MAP = {**SUP_DIGITS, **SUP_LETTERS}

SIMPLE_EXPONENT_RE = re.compile(r"^-?[0-9]+$|^[A-Za-z]$")
# Un "jeton simple" peut déjà contenir un exposant Unicode (ex: "7⁴", produit
# par l'étape 3 avant que \frac ne soit traité) : accepté tel quel, sans
# parenthèses superflues.
_SUP_CHARS = "".join(SUP_MAP.values())
SIMPLE_TOKEN_RE = re.compile(r"^[+-]?[A-Za-z0-9" + re.escape(_SUP_CHARS) + r"]+$")

# Marqueurs de zone protégée (rendu LaTeX/KaTeX intact) : caractères de la
# zone privée Unicode, garantis absents du contenu source, donc invisibles
# aux regex suivantes (aucun \, ^ ou _ dedans).
_PROTECT_OPEN, _PROTECT_CLOSE = "", ""


def _to_superscript(exponent):
    out = []
    for ch in exponent:
        sup = SUP_MAP.get(ch)
        if sup is None:
            return None
        out.append(sup)
    return "".join(out)


def _fix_known_artifacts(text):
    """Corrige des artefacts de génération déjà connus dans exercises_bank.json
    (ex: "\\fracrac{" au lieu de "\\frac{"), avant toute autre transformation."""
    text = re.sub(r"\\fracrac\{", r"\\frac{", text)
    text = re.sub(r"\\dfrac", r"\\frac", text)
    text = re.sub(r"\{,\}", ",", text)  # virgule décimale protégée LaTeX -> virgule normale
    return text


SAFE_SYMBOL_RULES = [
    (re.compile(r"\\times|\\cdot"), "×"),
    (re.compile(r"\\div"), "÷"),
    (re.compile(r"\\pm"), "±"),
    (re.compile(r"\\geq|\\ge\b"), "≥"),
    (re.compile(r"\\leq|\\le\b"), "≤"),
    (re.compile(r"\\neq|\\ne\b"), "≠"),
    (re.compile(r"\\notin"), "∉"),
    (re.compile(r"\\in\b"), "∈"),
    (re.compile(r"\\cap"), "∩"),
    (re.compile(r"\\cup"), "∪"),
    (re.compile(r"\\mapsto"), "↦"),
    (re.compile(r"\\Rightarrow|\\Leftrightarrow"), "⇒"),
    (re.compile(r"\\mathbb\{N\}"), "ℕ"),
    (re.compile(r"\\mathbb\{Z\}"), "ℤ"),
    (re.compile(r"\\mathbb\{Q\}"), "ℚ"),
    (re.compile(r"\\mathbb\{R\}"), "ℝ"),
    (re.compile(r"\\mathbb\{C\}"), "ℂ"),
    (re.compile(r"\\mathbb\{D\}"), "𝔻"),
    (re.compile(r"\+\\infty"), "+∞"),
    (re.compile(r"-\\infty"), "-∞"),
    (re.compile(r"\\infty"), "∞"),
    (re.compile(r"\\%"), "%"),
    (re.compile(r"\\approx"), "≈"),
    (re.compile(r"\\emptyset"), "∅"),
    (re.compile(r"\\parallel"), "∥"),
    (re.compile(r"\\perp"), "⊥"),
    (re.compile(r"\\subset"), "⊂"),
    (re.compile(r"\\setminus"), "∖"),
    (re.compile(r"\\to(?![A-Za-z])"), "→"),
    (re.compile(r"\\circ"), "∘"),
    (re.compile(r"\\lceil"), "⌈"),
    (re.compile(r"\\rceil"), "⌉"),
    (re.compile(r"\\lfloor"), "⌊"),
    (re.compile(r"\\rfloor"), "⌋"),
    (re.compile(r"\\pi\b"), "π"),
    (re.compile(r"\\alpha\b"), "α"),
    (re.compile(r"\\beta\b"), "β"),
    (re.compile(r"\\sigma\b"), "σ"),
    (re.compile(r"\\Delta\b"), "Δ"),
    (re.compile(r"\\Omega\b"), "Ω"),
    (re.compile(r"\\ldots"), "…"),
    (re.compile(r"\\sin\b"), "sin"),
    (re.compile(r"\\cos\b"), "cos"),
    (re.compile(r"\\tan\b"), "tan"),
    (re.compile(r"\\max\b"), "max"),
    (re.compile(r"\\min\b"), "min"),
    (re.compile(r"\\left|\\right|\\,|\\!|\\;"), ""),
    (re.compile(r"\\text\{([^{}\\]*)\}"), r"\1"),
    (re.compile(r"\\\{"), "{"),
    (re.compile(r"\\\}"), "}"),
]

NESTED_BRACES = r"[^{}]*(?:\{[^{}]*\}[^{}]*)*"


def naturalize_text(text):
    if not isinstance(text, str) or not text:
        return text

    text = _fix_known_artifacts(text)
    text = text.replace("$", "")  # délimiteurs d'origine incohérents (voir docstring) : ignorés.

    protected = []

    def protect(s):
        protected.append(s)
        return f"{_PROTECT_OPEN}{len(protected) - 1}{_PROTECT_CLOSE}"

    # 1) Systèmes d'équations : toujours confiés à KaTeX en bloc.
    text = re.sub(r"\\begin\{cases\}.*?\\end\{cases\}",
                  lambda m: protect(f"${m.group(0)}$"), text, flags=re.S)

    # 2) Vecteurs : toujours confiés à KaTeX (pas d'équivalent Unicode fiable
    #    pour la flèche au-dessus d'un nom à 1-2 lettres).
    text = re.sub(r"[0-9A-Za-z]*\\(?:vec|overrightarrow)\{[^{}]+\}",
                  lambda m: protect(f"${m.group(0)}$"), text)
    text = re.sub(r"[0-9A-Za-z]*\\(?:vec|overrightarrow)\s*[0-9A-Za-z]+",
                  lambda m: protect(f"${m.group(0)}$"), text)

    # 2bis) Barre statistique (moyenne), accent circonflexe (angle), sommes :
    #    diacritiques combinants non fiables en texte brut (même problème que
    #    la flèche vectorielle) -> toujours confiés à KaTeX.
    text = re.sub(r"\\(?:bar|overline)\{" + NESTED_BRACES + r"\}",
                  lambda m: protect(f"${m.group(0)}$"), text)
    text = re.sub(r"\\widehat\{[^{}]+\}",
                  lambda m: protect(f"${m.group(0)}$"), text)
    text = re.sub(r"\\mathcal\{[^{}]+\}",
                  lambda m: protect(f"${m.group(0)}$"), text)
    # \sigma_x, \sigma^2, \sigma_{...} : protégé EN ENTIER avant toute autre
    # règle, sinon l'attrapeur d'indices/exposants générique (étapes 3 et 7)
    # ne verrait que le "a" final de "sigma" et couperait la commande en un
    # artefact "\sigm" + "a_x" / "a²".
    text = re.sub(r"\\sigma(?:_\{[^{}]+\}|_[A-Za-z0-9])?(?:\^\{[^{}]+\}|\^[A-Za-z0-9])?",
                  lambda m: protect(f"${m.group(0)}$") if (m.group(0) != "\\sigma") else m.group(0),
                  text)
    text = re.sub(r"\\sum(?:_(?:\{[^{}]+\}|[A-Za-z0-9]))?(?:\^(?:\{[^{}]+\}|[A-Za-z0-9]))?",
                  lambda m: protect(f"${m.group(0)}$"), text)

    # 3) Exposants simples (entier relatif ou lettre seule) -> Unicode réel ;
    #    exposants complexes -> confiés à KaTeX (juste "base^{exposant}").
    def power_repl(m):
        base, exp_raw = m.group(1), m.group(2)
        exp = exp_raw.strip("{}")
        if SIMPLE_EXPONENT_RE.match(exp):
            sup = _to_superscript(exp)
            if sup is not None:
                return f"{base}{sup}"
        return protect(f"${m.group(0)}$")

    # Le groupe accolade accepte n'importe quel contenu (\{[^{}]+\}) et pas
    # seulement un jeton simple : un exposant composé (ex: "a^{n+m}") doit
    # être VU par power_repl pour être protégé -> KaTeX, plutôt que d'être
    # ignoré silencieusement (et laissé en LaTeX cassé, sans $...$).
    text = re.sub(r"(\))\s*\^\s*(\{[^{}]+\}|-?[0-9A-Za-z])", power_repl, text)
    text = re.sub(r"([0-9A-Za-z])\s*\^\s*(\{[^{}]+\}|-?[0-9A-Za-z])", power_repl, text)
    # R^+ / R^- : notation d'ensemble usuelle (pas un exposant algébrique).
    text = re.sub(r"([A-Z])\^([+\-])", lambda m: f"{m.group(1)}{SUP_MAP[m.group(2)]}", text)

    # 4) Symboles simples, sans ambiguïté (opérateurs, ensembles, infini...).
    #    Fait AVANT \frac et \sqrt pour que leur contenu (souvent "7^5 \times
    #    7^{-2}") soit déjà propre au moment de juger s'il est "simple".
    for pattern, replacement in SAFE_SYMBOL_RULES:
        text = pattern.sub(replacement, text)

    # 5) Racines : presque toujours aplatissables en texte ("√75", "√(a+b)") ;
    #    seul un contenu encore complexe (backslash résiduel) est protégé.
    def sqrt_repl(m):
        inner = m.group(1)
        if "\\" in inner:
            return protect(f"$\\sqrt{{{inner}}}$")
        return f"√{inner}" if SIMPLE_TOKEN_RE.match(inner) else f"√({inner})"

    text = re.sub(r"\\sqrt\{(" + NESTED_BRACES + r")\}", sqrt_repl, text)
    text = re.sub(r"\\sqrt\s*([^\s\\{}^_$]+)", lambda m: f"√{m.group(1)}", text)
    text = re.sub(r"sqrt\(([^()]+)\)",
                  lambda m: (f"√{m.group(1)}" if SIMPLE_TOKEN_RE.match(m.group(1)) else f"√({m.group(1)})"),
                  text)

    # 6) Fractions : "a/b" si numérateur ET dénominateur sont déjà propres
    #    (aucun \, ^ ou _ restant après les étapes précédentes) ; sinon
    #    confiées à KaTeX en bloc.
    def _needs_parens(operand):
        return not SIMPLE_TOKEN_RE.match(operand)

    def frac_repl(m):
        a, b = m.group(1), m.group(2)
        if any(c in a or c in b for c in ("\\", "^", "_")):
            return protect(f"${m.group(0)}$")
        num = f"({a})" if _needs_parens(a) else a
        den = f"({b})" if _needs_parens(b) else b
        frac = f"{num}/{den}"
        after = text[m.end():m.end() + 1]
        if after and re.match(r"[A-Za-z0-9(]", after):
            return f"({frac})"
        return frac

    text = re.sub(r"\\frac\{(" + NESTED_BRACES + r")\}\{(" + NESTED_BRACES + r")\}", frac_repl, text)
    # Formes mixtes : un seul côté sans accolades (ex: \frac1{12}, \frac{1}2).
    text = re.sub(r"\\frac\{(" + NESTED_BRACES + r")\}([0-9A-Za-z])", frac_repl, text)
    text = re.sub(r"\\frac([0-9A-Za-z])\{(" + NESTED_BRACES + r")\}", frac_repl, text)
    # \fracXY (raccourci LaTeX sans accolades pour un numérateur/dénominateur
    # d'un seul caractère, ex: \frac12 = \frac{1}{2}).
    text = re.sub(r"\\frac([0-9A-Za-z])([0-9A-Za-z])", frac_repl, text)

    # 7) Coordonnées/indices isolés restants (ex: x_A, y_1) non absorbés par
    #    une fraction ou un vecteur ci-dessus -> confiés à KaTeX.
    text = re.sub(r"[A-Za-z](?:_\{[^{}]+\}|_[A-Za-z0-9])",
                  lambda m: protect(f"${m.group(0)}$"), text)

    # 8) Restauration des zones protégées.
    text = re.sub(f"{_PROTECT_OPEN}(\\d+){_PROTECT_CLOSE}",
                  lambda m: protected[int(m.group(1))], text)

    return re.sub(r"\s{2,}", " ", text).strip()


def _flatten_steps(steps):
    """Certains exercices de la banque ont solution_steps sous forme de dict
    (ex: {'produit': '...', 'quotient': '...'}) plutôt que de liste — on
    aplatit en liste ordonnée, sans changer le contenu pédagogique."""
    if isinstance(steps, list):
        return steps
    if isinstance(steps, dict):
        flat = []
        for value in steps.values():
            if isinstance(value, list):
                flat.extend(value)
            else:
                flat.append(value)
        return flat
    return []


def naturalize_exercise(ex):
    natural = dict(ex)
    for field in ("enonce", "hint", "answer"):
        if field in ex:
            natural[field] = naturalize_text(ex[field])
    steps = _flatten_steps(ex.get("solution_steps"))
    natural["solution_steps"] = [naturalize_text(step) for step in steps]
    return natural


def main():
    with open(SOURCE_PATH, "r", encoding="utf-8") as f:
        bank = json.load(f)

    natural_bank = []
    for i, ex in enumerate(bank):
        ex_with_id = dict(ex)
        ex_with_id["id"] = ex.get("id") if ex.get("id") is not None else i
        natural_bank.append(naturalize_exercise(ex_with_id))

    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(natural_bank, f, ensure_ascii=False, indent=2)

    print(f"{len(natural_bank)} exercices convertis -> {OUTPUT_PATH.name}")
    print("Apercu :")
    for ex in natural_bank[:3]:
        print(f"  [{ex['chapter_id']}] {ex['enonce']}")


if __name__ == "__main__":
    main()
