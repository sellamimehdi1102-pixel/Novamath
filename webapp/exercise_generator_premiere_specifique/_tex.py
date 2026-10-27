"""Lecture de LaTeX simple (polynômes, \\dfrac, \\sqrt, puissances) en SymPy,
pour CONTRÔLER une réponse rédigée par un générateur avant de la publier."""
import sympy as sp
from sympy.parsing.sympy_parser import implicit_multiplication_application, parse_expr, standard_transformations

_TR = standard_transformations + (implicit_multiplication_application,)


def _group(s, i):
    depth = 0
    for j in range(i, len(s)):
        if s[j] == "{":
            depth += 1
        elif s[j] == "}":
            depth -= 1
            if depth == 0:
                return s[i + 1:j], j + 1
    raise ValueError(s)


def tex2py(s):
    s = s.replace("\\left", "").replace("\\right", "").replace("\\,", "").replace("{,}", ".").replace(" ", "")
    out, i = "", 0
    while i < len(s):
        if s.startswith("\\dfrac", i) or s.startswith("\\frac", i):
            i += 6 if s.startswith("\\dfrac", i) else 5
            a, i = _group(s, i)
            b, i = _group(s, i)
            out += f" (({tex2py(a)})/({tex2py(b)})) "
        elif s.startswith("\\sqrt", i):
            a, i = _group(s, i + 5)
            out += f" sqrt({tex2py(a)}) "
        elif s.startswith("\\times", i):
            out += "*"
            i += 6
        elif s.startswith("\\pi", i):
            out += " pi "
            i += 3
        elif s.startswith("\\cos", i) or s.startswith("\\sin", i):
            out += f" {s[i + 1:i + 4]}"
            i += 4
        elif s[i] == "^":
            if s[i + 1] == "{":
                a, i = _group(s, i + 1)
            else:
                a, i = s[i + 1], i + 2
            out += f"**({tex2py(a)})"
        else:
            out += s[i]
            i += 1
    return out


def parse(s, symbols=("x",)):
    local = {name: sp.Symbol(name) for name in symbols}
    local["sqrt"] = sp.sqrt
    local.update(pi=sp.pi, cos=sp.cos, sin=sp.sin)
    return parse_expr(tex2py(s), local_dict=local, transformations=_TR)
