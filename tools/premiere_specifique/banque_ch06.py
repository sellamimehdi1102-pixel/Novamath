"""Chapitre 6 (ancien chapitre 4) — Variations et courbes représentatives : banque curée.

Exercices historiques (identifiants conservés) : textes réécrits — les
fonctions étaient écrites « (x)^3 - 12(x) +0 » ou « −[(x+3)^3 - 3(x+3)] +0 »
(signe moins Unicode, crochets, « + 0 ») ; elles sont maintenant données sous
forme développée, avec une correction complète (dérivée factorisée, signe,
tableau, extremums). Valeurs recalculées par SymPy.

Nouveaux exercices : bloc 64 000.
"""
import sympy as sp

from premiere_specifique.banque_commun import E, S, code, fr, lin, par, poly_tex

CHAPTER_NUMBER = 6  # ancien chapitre 4 (adaptation au manuel « Première ES/L », 2026-10-26)
N1 = "Variations d'une fonction"
N2 = "Nombre dérivé et extremums locaux"
N3 = "Fonctions paires et impaires"
N4 = "Inégalités et position relative de courbes"
N5 = "Étude d'une fonction et méthode de Newton"
NOTIONS = (N1, N2, N3, N4, N5)
NOTION_IDS = (
    "variations-d-une-fonction",
    "nombre-derive-et-extremums-locaux",
    "fonctions-paires-et-impaires",
    "inegalites-et-position-relative-de-courbes",
    "etude-d-une-fonction-et-methode-de-newton",
)

x = sp.symbols("x")


def P(expr):
    return poly_tex([sp.Rational(c) for c in sp.Poly(sp.expand(expr), x).all_coeffs()])


def _fac(k, r1, r2):
    lead = "" if k == 1 else ("-" if k == -1 else str(k))
    return f"{lead}({lin(r1)})({lin(r2)})"


def _interval(a, b):
    left = "]-\\infty" if a is None else f"[{fr(a)}"
    right = "+\\infty[" if b is None else f"{fr(b)}]"
    return f"${left} ; {right}$"


def _signe_connu(i, k, r1, r2):
    r1, r2 = sorted((r1, r2))
    out = "croissante" if k > 0 else "décroissante"
    inn = "décroissante" if k > 0 else "croissante"
    return E(i, N1, 1,
             f"Soit $f$ une fonction dérivable sur $\\mathbb{{R}}$ telle que, pour tout réel $x$, $f'(x) = {_fac(k, r1, r2)}$. "
             f"Étudier le signe de $f'(x)$, puis en déduire les variations de $f$.",
             f"$f$ est {out} sur {_interval(None, r1)}, {inn} sur {_interval(r1, r2)}, puis {out} sur {_interval(r2, None)}.",
             "Le signe d'un trinôme factorisé se lit avec ses racines et le signe du coefficient.",
             S(f"$f'(x)$ s'annule en ${r1}$ et ${r2}$ ; le coefficient vaut ${k}$.",
               f"$f'(x)$ est du signe de ${k}$ ({'positif' if k > 0 else 'négatif'}) à l'extérieur des racines et du signe contraire entre elles.",
               f"Là où $f' > 0$, $f$ est croissante ; là où $f' < 0$, elle est décroissante : {out}, puis {inn}, puis {out}."),
             checks=(out,))


_CUBIQUES = {826: (1, 0, 12, 0), 827: (-1, 0, 12, 0), 838: (-1, -3, 3, 0), 839: (1, -1, 147, 0), 840: (-1, 2, 147, 0),
             848: (1, 4, 12, 0), 851: (-1, 0, 75, -6), 852: (-1, 3, 75, -6), 854: (-1, -1, 3, -2), 857: (1, 1, 192, -2),
             871: (1, -3, 108, -4)}


def _cubique(i, s, h, m, c):
    f = sp.expand(s * ((x - h) ** 3 - m * (x - h)) + c)
    d = sp.diff(f, x)
    r = int(sp.sqrt(m / 3))
    a, b = h - r, h + r
    fa, fb = f.subs(x, a), f.subs(x, b)
    if s > 0:
        mx, mn = (a, fa), (b, fb)
    else:
        mx, mn = (b, fb), (a, fa)
    assert set(sp.solve(d, x)) == {a, b}
    k = 3 * s
    return E(i, N2, 2,
             f"Soit $f$ la fonction définie sur $\\mathbb{{R}}$ par $f(x) = {P(f)}$. 1) Calculer $f'(x)$ et le factoriser. "
             f"2) Étudier le signe de $f'(x)$ et en déduire les extremums locaux de $f$.",
             f"Maximum local ${mx[1]}$ en $x = {mx[0]}$ ; minimum local ${mn[1]}$ en $x = {mn[0]}$.",
             "Factorise $f'(x)$ : c'est un trinôme dont les racines annoncent les extremums possibles.",
             S(f"$f'(x) = {P(d)} = {_fac(k, a, b)}$.",
               f"$f'(x)$ est du signe de ${k}$ à l'extérieur de ${a}$ et ${b}$, du signe contraire entre.",
               f"$f'$ change de signe en ${a}$ et en ${b}$ : extremums locaux.",
               f"$f({a}) = {fa}$ et $f({b}) = {fb}$ : maximum local ${mx[1]}$ en ${mx[0]}$, minimum local ${mn[1]}$ en ${mn[0]}$."),
             checks=(str(mx[1]), str(mn[1])))


HIST = ([_signe_connu(i, *p) for i, p in {767: (-2, -5, -3), 768: (2, -2, 5), 775: (-1, 2, 5)}.items()]
        + [_cubique(i, *p) for i, p in _CUBIQUES.items()])
LEGACY_IDS = tuple(e.id for e in HIST)


def _chk(cond_fn):
    return lambda: None if cond_fn() else "valeur fausse"


NOUVEAUX = [
    # N1 — variations
    E(64101, N1, 1,
      "Soit $f(x) = x^2 - 8x + 3$. Calculer $f'(x)$, étudier son signe et dresser le tableau de variations de $f$.",
      "$f'(x) = 2x - 8$ ; $f$ est décroissante sur $]-\\infty ; 4]$, croissante sur $[4 ; +\\infty[$, minimum $-13$ en $4$.",
      "$f'(x) > 0 \\iff x > 4$.",
      S("$f'(x) = 2x - 8$, négatif pour $x < 4$, positif pour $x > 4$.", "$f(4) = 16 - 32 + 3 = -13$.",
        "On retrouve le résultat du second degré : sommet $(4 ; -13)$."),
      checks=("-13",), verify=_chk(lambda: (x**2 - 8 * x + 3).subs(x, 4) == -13)),
    E(64102, N1, 2,
      "Étudier les variations de $f(x) = x^3 - 3x^2 - 9x + 1$ sur $\\mathbb{R}$.",
      "$f$ est croissante sur $]-\\infty ; -1]$, décroissante sur $[-1 ; 3]$, croissante sur $[3 ; +\\infty[$ ; $f(-1) = 6$ et $f(3) = -26$.",
      "Factorise $f'(x) = 3x^2 - 6x - 9$.",
      S("$f'(x) = 3x^2 - 6x - 9 = 3(x^2 - 2x - 3) = 3(x + 1)(x - 3)$.", "$f' > 0$ hors de $[-1 ; 3]$ et $f' < 0$ entre.",
        "$f(-1) = -1 - 3 + 9 + 1 = 6$ et $f(3) = 27 - 27 - 27 + 1 = -26$."),
      checks=("$f(-1) = 6$", "$f(3) = -26$"), verify=_chk(lambda: sp.expand(sp.diff(x**3 - 3 * x**2 - 9 * x + 1, x) - 3 * (x + 1) * (x - 3)) == 0)),
    E(64103, N1, 2,
      "Étudier les variations de $f(x) = \\dfrac{2x - 1}{x + 3}$ sur $]-3 ; +\\infty[$.",
      "$f'(x) = \\dfrac{7}{(x + 3)^2} > 0$ : $f$ est strictement croissante sur $]-3 ; +\\infty[$.",
      "Règle du quotient, puis signe du numérateur.",
      S("$f'(x) = \\dfrac{2(x + 3) - (2x - 1)}{(x + 3)^2} = \\dfrac{7}{(x + 3)^2}$.", "Numérateur et dénominateur positifs : $f'(x) > 0$.",
        "$f$ est strictement croissante sur $]-3 ; +\\infty[$."),
      checks=("\\dfrac{7}{(x + 3)^2}",), verify=_chk(lambda: sp.simplify(sp.diff((2 * x - 1) / (x + 3), x) - 7 / (x + 3) ** 2) == 0)),
    E(64104, N1, 1,
      "Une fonction $f$ dérivable sur $[0 ; 10]$ vérifie $f'(x) = 0$ pour tout $x$ et $f(2) = 5$. Que vaut $f(7)$ ?",
      "$f(7) = 5$ : une fonction de dérivée nulle sur un intervalle est constante.",
      "Que peut-on dire d'une fonction dont la dérivée est nulle sur tout un intervalle ?",
      S("$f'(x) = 0$ sur l'intervalle $[0 ; 10]$ : $f$ est constante sur cet intervalle.", "Donc $f(7) = f(2) = 5$."),
      checks=("f(7) = 5",)),
    E(64105, N1, 3,
      "Étudier les variations de $f(x) = x + \\dfrac{4}{x}$ sur $]0 ; +\\infty[$.",
      "$f$ est décroissante sur $]0 ; 2]$ et croissante sur $[2 ; +\\infty[$ ; minimum $4$ en $x = 2$.",
      "Mets $f'(x)$ au même dénominateur.",
      S("$f'(x) = 1 - \\dfrac{4}{x^2} = \\dfrac{x^2 - 4}{x^2} = \\dfrac{(x - 2)(x + 2)}{x^2}$.", "Sur $]0 ; +\\infty[$ : $x + 2 > 0$ et $x^2 > 0$, le signe est celui de $x - 2$.",
        "Minimum $f(2) = 2 + 2 = 4$."),
      checks=("4",), verify=_chk(lambda: (x + 4 / x).subs(x, 2) == 4)),
    E(64106, N1, 2,
      "Vrai ou faux : « si $f'(x) > 0$ pour tout $x$ de $\\mathbb{R} \\setminus \\{0\\}$, alors $f$ est croissante sur $\\mathbb{R} \\setminus \\{0\\}$ ». "
      "Utiliser $f(x) = -\\dfrac{1}{x}$.",
      "Faux : $f'(x) = \\dfrac{1}{x^2} > 0$ mais $f(-1) = 1 > f(1) = -1$. Le théorème s'applique sur un INTERVALLE ; ici $f$ est croissante sur chacun des intervalles $]-\\infty ; 0[$ et $]0 ; +\\infty[$.",
      "$\\mathbb{R} \\setminus \\{0\\}$ n'est pas un intervalle.",
      S("$f'(x) = \\dfrac{1}{x^2} > 0$.", "$-1 < 1$ mais $f(-1) = 1 > -1 = f(1)$ : $f$ n'est pas croissante sur $\\mathbb{R} \\setminus \\{0\\}$.",
        "Le lien signe de $f'$ / variations est valable sur un intervalle."),
      checks=()),
    E(64107, N1, 3,
      "Soit $f(x) = \\sqrt{x} - x$ sur $[0 ; +\\infty[$. Étudier ses variations sur $]0 ; +\\infty[$ et donner son maximum.",
      "$f$ est croissante sur $\\left]0 ; \\dfrac{1}{4}\\right]$, décroissante sur $\\left[\\dfrac{1}{4} ; +\\infty\\right[$ ; maximum $\\dfrac{1}{4}$ en $\\dfrac{1}{4}$.",
      "$f'(x) = \\dfrac{1}{2\\sqrt{x}} - 1 = \\dfrac{1 - 2\\sqrt{x}}{2\\sqrt{x}}$.",
      S("$f'(x) = \\dfrac{1 - 2\\sqrt{x}}{2\\sqrt{x}}$, du signe de $1 - 2\\sqrt{x}$.", "$1 - 2\\sqrt{x} > 0 \\iff \\sqrt{x} < \\dfrac{1}{2} \\iff x < \\dfrac{1}{4}$.",
        "$f\\left(\\dfrac{1}{4}\\right) = \\dfrac{1}{2} - \\dfrac{1}{4} = \\dfrac{1}{4}$."),
      checks=("\\dfrac{1}{4}",), verify=_chk(lambda: (sp.sqrt(x) - x).subs(x, sp.Rational(1, 4)) == sp.Rational(1, 4))),

    # N2 — extremums, optimisation
    E(64201, N2, 1,
      "La fonction $f(x) = x^3$ vérifie $f'(0) = 0$. Admet-elle un extremum local en $0$ ?",
      "Non : $f'(x) = 3x^2 \\geqslant 0$ ne change pas de signe en $0$, $f$ est croissante sur $\\mathbb{R}$.",
      "Un extremum exige un changement de signe de $f'$.",
      S("$f'(x) = 3x^2$ s'annule en $0$ mais reste positif de part et d'autre.", "$f$ est croissante : pas de maximum ni de minimum local en $0$.",
        "$f'(a) = 0$ est nécessaire pour un extremum (à l'intérieur), mais pas suffisant."),
      checks=()),
    E(64202, N2, 2,
      "Un rectangle a un périmètre de $20$ cm. On note $x$ sa largeur. Montrer que son aire est $A(x) = x(10 - x)$ et trouver l'aire maximale par dérivation.",
      "$A'(x) = 10 - 2x$ ; aire maximale $25$ cm² pour $x = 5$ (un carré).",
      "Longueur = demi-périmètre − largeur.",
      S("Longueur $10 - x$, avec $0 < x < 10$ : $A(x) = 10x - x^2$.", "$A'(x) = 10 - 2x$, positif avant $5$, négatif après.", "Maximum $A(5) = 25$."),
      checks=("25",)),
    E(64203, N2, 3,
      "On découpe aux quatre coins d'une plaque carrée de $12$ cm de côté quatre carrés de côté $x$, puis on relève les bords pour former une boîte. "
      "Exprimer son volume $V(x)$ et trouver la valeur de $x$ qui le rend maximal.",
      "$V(x) = x(12 - 2x)^2$ ; maximum pour $x = 2$ cm, $V(2) = 128$ cm³.",
      "Le fond est un carré de côté $12 - 2x$, avec $0 < x < 6$.",
      S("$V(x) = x(12 - 2x)^2 = 4x^3 - 48x^2 + 144x$.", "$V'(x) = 12x^2 - 96x + 144 = 12(x - 2)(x - 6)$.",
        "Sur $]0 ; 6[$ : $V' > 0$ avant $2$, $V' < 0$ après : maximum $V(2) = 2 \\times 64 = 128$."),
      checks=("128",), verify=_chk(lambda: sp.expand(sp.diff(x * (12 - 2 * x) ** 2, x) - 12 * (x - 6) * (x - 2)) == 0)),
    E(64204, N2, 2,
      "Soit $f(x) = -x^3 + 3x + 1$. Déterminer les extremums locaux de $f$ et préciser leur nature.",
      "Minimum local $-1$ en $x = -1$ ; maximum local $3$ en $x = 1$.",
      "$f'(x) = -3x^2 + 3 = -3(x - 1)(x + 1)$.",
      S("$f'(x) = -3(x - 1)(x + 1)$ : négatif hors de $[-1 ; 1]$, positif entre.", "$f$ décroît puis croît en $-1$ : minimum local $f(-1) = -1$.",
        "$f$ croît puis décroît en $1$ : maximum local $f(1) = 3$."),
      checks=("-1", "3"), verify=_chk(lambda: (-x**3 + 3 * x + 1).subs(x, -1) == -1 and (-x**3 + 3 * x + 1).subs(x, 1) == 3)),
    E(64205, N2, 3,
      "Le bénéfice d'une entreprise produisant $x$ centaines d'objets ($0 \\leqslant x \\leqslant 10$) est $B(x) = -x^3 + 12x^2 - 21x$ (en milliers d'euros). "
      "Pour quelle production le bénéfice est-il maximal ?",
      "Pour $x = 7$ (700 objets) : $B(7) = 98$ milliers d'euros.",
      "$B'(x) = -3x^2 + 24x - 21 = -3(x - 1)(x - 7)$.",
      S("$B'(x) = -3(x - 1)(x - 7)$ : négatif sur $[0 ; 1[$, positif sur $]1 ; 7[$, négatif sur $]7 ; 10]$.",
        "Candidats au maximum : $x = 7$ et la borne $x = 0$.", "$B(7) = -343 + 588 - 147 = 98$ et $B(0) = 0$ : maximum en $7$."),
      checks=("98",), verify=_chk(lambda: (-x**3 + 12 * x**2 - 21 * x).subs(x, 7) == 98)),
    E(64206, N2, 4,
      "Montrer qu'une fonction $f(x) = ax^3 + bx$ avec $a > 0$ et $b > 0$ n'admet aucun extremum local.",
      "$f'(x) = 3ax^2 + b > 0$ pour tout $x$ : $f$ est strictement croissante, donc sans extremum local.",
      "Étudie le signe de $f'$.",
      S("$f'(x) = 3ax^2 + b$.", "$3ax^2 \\geqslant 0$ et $b > 0$ : $f'(x) > 0$ pour tout réel $x$.",
        "Une fonction strictement croissante sur $\\mathbb{R}$ n'a ni maximum ni minimum local."),
      checks=()),
    E(64207, N2, 2,
      "La courbe de $f(x) = x^2 + bx + 3$ a une tangente horizontale au point d'abscisse $2$. Déterminer $b$ et la nature de cet extremum.",
      "$b = -4$ ; c'est un minimum, égal à $-1$.",
      "Traduis « tangente horizontale » par $f'(2) = 0$.",
      S("$f'(x) = 2x + b$ et $f'(2) = 4 + b = 0$, donc $b = -4$.", "$f'(x) = 2x - 4$ change de signe (de $-$ à $+$) en $2$ : minimum.", "$f(2) = 4 - 8 + 3 = -1$."),
      checks=("b = -4",)),

    # N3 — parité
    E(64301, N3, 1,
      "Étudier la parité de $f(x) = 3x^4 - 2x^2 + 1$ et de $g(x) = x^3 - 5x$ sur $\\mathbb{R}$.",
      "$f$ est paire ; $g$ est impaire.",
      "Calcule $f(-x)$ et compare à $f(x)$ et à $-f(x)$.",
      S("$\\mathbb{R}$ est symétrique par rapport à $0$.", "$f(-x) = 3x^4 - 2x^2 + 1 = f(x)$ : $f$ est paire.", "$g(-x) = -x^3 + 5x = -g(x)$ : $g$ est impaire."),
      checks=("paire", "impaire")),
    E(64302, N3, 1,
      "La fonction $h(x) = x^2 + x$ est-elle paire ? impaire ?",
      "Ni l'une ni l'autre : $h(1) = 2$ et $h(-1) = 0$.",
      "Un seul contre-exemple suffit.",
      S("$h(-1) = 0 \\neq h(1) = 2$ : $h$ n'est pas paire.", "$h(-1) = 0 \\neq -h(1) = -2$ : $h$ n'est pas impaire."),
      checks=()),
    E(64303, N3, 2,
      "Étudier la parité de $f(x) = \\dfrac{x}{x^2 + 1}$ et interpréter graphiquement.",
      "$f$ est impaire : sa courbe est symétrique par rapport à l'origine.",
      "$x^2 + 1$ ne s'annule jamais : $f$ est définie sur $\\mathbb{R}$.",
      S("$f(-x) = \\dfrac{-x}{(-x)^2 + 1} = -\\dfrac{x}{x^2 + 1} = -f(x)$.", "Le point $M(x ; f(x))$ et $M'(-x ; -f(x))$ sont symétriques par rapport à $O$."),
      checks=("impaire",)),
    E(64304, N3, 2,
      "La fonction $f(x) = \\sqrt{x}$ peut-elle être paire ou impaire ?",
      "Non : son ensemble de définition $[0 ; +\\infty[$ n'est pas symétrique par rapport à $0$.",
      "Avant de calculer $f(-x)$, vérifie que $-x$ est dans l'ensemble de définition.",
      S("$f(1)$ existe mais $f(-1)$ n'existe pas.", "La parité exige un ensemble de définition symétrique : ni paire ni impaire."),
      checks=()),
    E(64305, N3, 3,
      "Une fonction impaire $f$ définie sur $\\mathbb{R}$ vérifie $f(2) = 5$ et elle est croissante sur $[0 ; +\\infty[$. Que vaut $f(0)$ ? $f(-2)$ ? "
      "Quel est son sens de variation sur $]-\\infty ; 0]$ ?",
      "$f(0) = 0$, $f(-2) = -5$ et $f$ est croissante sur $]-\\infty ; 0]$.",
      "Écris $f(-0) = -f(0)$.",
      S("$f(0) = -f(0)$ donc $f(0) = 0$.", "$f(-2) = -f(2) = -5$.",
        "Si $u < v \\leqslant 0$, alors $0 \\leqslant -v < -u$ et $f(-v) < f(-u)$, soit $-f(v) < -f(u)$, d'où $f(u) < f(v)$ : $f$ croissante."),
      checks=("f(-2) = -5",)),
    E(64306, N3, 2,
      "Une fonction paire a pour tableau de variations sur $[0 ; 5]$ : décroissante de $f(0) = 3$ à $f(2) = -1$, puis croissante jusqu'à $f(5) = 4$. "
      "Donner son tableau de variations sur $[-5 ; 5]$.",
      "Sur $[-5 ; -2]$ : décroissante de $4$ à $-1$ ; sur $[-2 ; 0]$ : croissante de $-1$ à $3$ ; sur $[0 ; 2]$ : décroissante de $3$ à $-1$ ; sur $[2 ; 5]$ : croissante de $-1$ à $4$.",
      "La courbe d'une fonction paire est symétrique par rapport à l'axe des ordonnées : les variations s'inversent.",
      S("Par symétrie d'axe $(Oy)$ : $f(-5) = 4$, $f(-2) = -1$, $f(0) = 3$.", "Sur $[-5 ; -2]$ : décroissante ; sur $[-2 ; 0]$ : croissante.",
        "Puis comme donné sur $[0 ; 5]$."),
      checks=()),

    # N4 — inégalités, position relative
    E(64401, N4, 2,
      "Démontrer que pour tout réel $x \\geqslant 0$, $x^3 - 3x + 2 \\geqslant 0$, en étudiant $f(x) = x^3 - 3x + 2$.",
      "$f$ admet sur $[0 ; +\\infty[$ un minimum égal à $f(1) = 0$, donc $f(x) \\geqslant 0$.",
      "Cherche le minimum de $f$ sur $[0 ; +\\infty[$.",
      S("$f'(x) = 3x^2 - 3 = 3(x - 1)(x + 1)$ : sur $[0 ; +\\infty[$, négatif avant $1$, positif après.", "Minimum $f(1) = 1 - 3 + 2 = 0$.",
        "Donc $f(x) \\geqslant 0$ pour tout $x \\geqslant 0$."),
      checks=()),
    E(64402, N4, 2,
      "Étudier la position relative des courbes de $f(x) = x^3$ et $g(x) = x$.",
      "$\\mathcal{C}_f$ est au-dessus de $\\mathcal{C}_g$ sur $]-1 ; 0[ \\cup ]1 ; +\\infty[$, en dessous sur $]-\\infty ; -1[ \\cup ]0 ; 1[$ ; elles se coupent en $x = -1$, $0$, $1$.",
      "Étudie le signe de $f(x) - g(x) = x^3 - x$.",
      S("$x^3 - x = x(x - 1)(x + 1)$.", "Tableau de signes avec les facteurs $x + 1$, $x$, $x - 1$.",
        "Positif sur $]-1 ; 0[ \\cup ]1 ; +\\infty[$, négatif sur $]-\\infty ; -1[ \\cup ]0 ; 1[$."),
      checks=()),
    E(64403, N4, 3,
      "Démontrer que pour tout $x > 0$, $x + \\dfrac{1}{x} \\geqslant 2$.",
      "$f(x) = x + \\dfrac{1}{x}$ a pour minimum $f(1) = 2$ sur $]0 ; +\\infty[$.",
      "Étudie les variations de $f(x) = x + \\dfrac{1}{x}$.",
      S("$f'(x) = 1 - \\dfrac{1}{x^2} = \\dfrac{(x - 1)(x + 1)}{x^2}$, du signe de $x - 1$ sur $]0 ; +\\infty[$.", "Minimum $f(1) = 2$.",
        "Autre preuve : $x + \\dfrac{1}{x} - 2 = \\dfrac{(x - 1)^2}{x} \\geqslant 0$."),
      checks=()),
    E(64404, N4, 3,
      "Démontrer que la courbe de $f(x) = x^2$ est au-dessus de chacune de ses tangentes.",
      "La tangente en $a$ est $y = 2ax - a^2$ et $x^2 - (2ax - a^2) = (x - a)^2 \\geqslant 0$.",
      "Écris la tangente en un point d'abscisse $a$ et étudie la différence.",
      S("Tangente en $a$ : $y = 2a(x - a) + a^2 = 2ax - a^2$.", "$x^2 - 2ax + a^2 = (x - a)^2 \\geqslant 0$.", "La parabole est au-dessus de toutes ses tangentes."),
      checks=("(x - a)^2",)),
    E(64405, N4, 4,
      "Démontrer que pour tout $x \\geqslant 0$, $\\sqrt{x} \\leqslant \\dfrac{x + 1}{2}$, et interpréter graphiquement.",
      "$\\dfrac{x + 1}{2} - \\sqrt{x} = \\dfrac{(\\sqrt{x} - 1)^2}{2} \\geqslant 0$ : la courbe de $\\sqrt{x}$ est sous sa tangente en $1$, d'équation $y = \\dfrac{x + 1}{2}$.",
      "Pense à $(\\sqrt{x} - 1)^2$.",
      S("$(\\sqrt{x} - 1)^2 = x - 2\\sqrt{x} + 1$.", "Donc $\\dfrac{x + 1}{2} - \\sqrt{x} = \\dfrac{(\\sqrt{x} - 1)^2}{2} \\geqslant 0$.",
        "La droite $y = \\dfrac{x + 1}{2}$ est la tangente en $1$ (pente $\\dfrac{1}{2}$, passe par $(1 ; 1)$)."),
      checks=()),
    E(64406, N4, 2,
      "Étudier la position relative de la courbe de $f(x) = \\dfrac{1}{x}$ et de la droite $y = -x + 2$ sur $]0 ; +\\infty[$.",
      "La courbe est au-dessus de la droite, sauf au point $(1 ; 1)$ où elles se touchent.",
      "$\\dfrac{1}{x} - (-x + 2) = \\dfrac{x^2 - 2x + 1}{x}$.",
      S("$d(x) = \\dfrac{1}{x} + x - 2 = \\dfrac{(x - 1)^2}{x}$.", "Sur $]0 ; +\\infty[$, $d(x) \\geqslant 0$, nul seulement en $1$.",
        "La droite est la tangente en $1$ : elle touche la courbe sans la traverser."),
      checks=()),

    # N5 — étude complète, Newton
    E(64501, N5, 2,
      "Étudier, par la dérivation, la fonction $f(x) = -2x^2 + 6x + 1$ : variations, extremum, allure de la courbe.",
      "$f'(x) = -4x + 6$ ; $f$ croissante sur $]-\\infty ; \\dfrac{3}{2}]$, décroissante ensuite ; maximum $\\dfrac{11}{2}$ en $\\dfrac{3}{2}$ ; parabole tournée vers le bas.",
      "$a = -2 < 0$ : la dérivée passe du positif au négatif.",
      S("$f'(x) = -4x + 6 > 0 \\iff x < \\dfrac{3}{2}$.", "$f\\left(\\dfrac{3}{2}\\right) = -\\dfrac{9}{2} + 9 + 1 = \\dfrac{11}{2}$.",
        "On retrouve le sommet $\\left(-\\dfrac{b}{2a} ; f\\left(-\\dfrac{b}{2a}\\right)\\right)$ du chapitre 2."),
      checks=("\\dfrac{11}{2}",), verify=_chk(lambda: (-2 * x**2 + 6 * x + 1).subs(x, sp.Rational(3, 2)) == sp.Rational(11, 2))),
    E(64502, N5, 3,
      "Méthode de Newton pour $f(x) = x^2 - 2$ : à partir de $x_0 = 2$, on définit $x_{n+1} = x_n - \\dfrac{f(x_n)}{f'(x_n)}$. Calculer $x_1$ et $x_2$. "
      "De quel nombre ces valeurs s'approchent-elles ?",
      "$x_1 = 1{,}5$ et $x_2 = \\dfrac{17}{12} \\approx 1{,}41667$ : elles s'approchent de $\\sqrt{2} \\approx 1{,}41421$.",
      "$f'(x) = 2x$, donc $x_{n+1} = x_n - \\dfrac{x_n^2 - 2}{2x_n}$.",
      S("$x_1 = 2 - \\dfrac{2}{4} = 1{,}5$.", "$x_2 = 1{,}5 - \\dfrac{0{,}25}{3} = \\dfrac{17}{12}$.",
        "Ce sont les abscisses où les tangentes successives coupent l'axe : elles convergent vers la racine positive $\\sqrt{2}$."),
      checks=("\\dfrac{17}{12}",)),
    E(64503, N5, 3,
      "Compléter la fonction Python qui applique $n$ fois la méthode de Newton à $f(x) = x^3 - x - 1$ à partir de $a$ : "
      + code("def newton(a, n):") + " " + code("for k in range(n): a = a - (a**3 - a - 1) / (...)") + " " + code("return a") + ".",
      "Il faut " + code("3*a**2 - 1") + " (la dérivée $f'(a) = 3a^2 - 1$) ; " + code("newton(1.5, 5)") + " renvoie environ $1{,}3247$.",
      "La méthode divise $f(a)$ par $f'(a)$.",
      S("$f'(x) = 3x^2 - 1$.", "Chaque passage remplace $a$ par l'abscisse où la tangente en $a$ coupe l'axe des abscisses.",
        "À partir de $1{,}5$ : $1{,}3478$ ; $1{,}3252$ ; $1{,}3247$ ; puis la valeur se stabilise."),
      checks=()),
    E(64504, N5, 4,
      "Étude complète de $f(x) = \\dfrac{x^2}{x - 1}$ sur $]1 ; +\\infty[$ : dérivée, variations, minimum.",
      "$f'(x) = \\dfrac{x(x - 2)}{(x - 1)^2}$ ; $f$ décroissante sur $]1 ; 2]$, croissante sur $[2 ; +\\infty[$ ; minimum $f(2) = 4$.",
      "Règle du quotient puis factorisation du numérateur.",
      S("$f'(x) = \\dfrac{2x(x - 1) - x^2}{(x - 1)^2} = \\dfrac{x^2 - 2x}{(x - 1)^2} = \\dfrac{x(x - 2)}{(x - 1)^2}$.",
        "Sur $]1 ; +\\infty[$ : $x > 0$ et $(x - 1)^2 > 0$, le signe est celui de $x - 2$.", "Minimum $f(2) = \\dfrac{4}{1} = 4$."),
      checks=("4",), verify=_chk(lambda: sp.simplify(sp.diff(x**2 / (x - 1), x) - x * (x - 2) / (x - 1) ** 2) == 0)),
    E(64505, N5, 2,
      "Pour $a \\neq 0$, comment l'allure de la parabole de $f(x) = ax^2 + bx + c$ se déduit-elle du signe de $f'$ ? Illustrer avec $f(x) = 3x^2 - 12x$.",
      "$f'(x) = 2ax + b$ s'annule en $-\\dfrac{b}{2a}$ ; si $a > 0$, $f'$ passe de $-$ à $+$ (minimum), sinon de $+$ à $-$ (maximum). Pour $3x^2 - 12x$ : minimum $-12$ en $2$.",
      "$f'$ est affine de coefficient $2a$.",
      S("$f'(x) = 2ax + b$, du signe de $a$ après $-\\dfrac{b}{2a}$.", "Ici $f'(x) = 6x - 12$, nul en $2$, $a = 3 > 0$ : minimum.", "$f(2) = 12 - 24 = -12$."),
      checks=("-12",)),
    E(64506, N5, 1,
      "Remettre dans l'ordre les étapes de l'étude d'une fonction : (a) dresser le tableau de variations ; (b) calculer $f'(x)$ ; "
      "(c) préciser l'ensemble de définition ; (d) étudier le signe de $f'(x)$ ; (e) calculer les valeurs aux bornes et aux extremums.",
      "(c), (b), (d), (a), (e) — les valeurs (e) se placent ensuite dans le tableau.",
      "On ne peut pas étudier un signe avant d'avoir calculé la dérivée.",
      S("On commence par l'ensemble de définition (c), puis la dérivée (b).", "Le signe de la dérivée (d) donne les variations (a).",
        "On complète le tableau avec les valeurs remarquables (e)."),
      checks=()),
]

EXERCISES = HIST + NOUVEAUX

QUIZ = {
    "variations-d-une-fonction": (767, 64101, 64104),
    "nombre-derive-et-extremums-locaux": (64201, 64202, 64207),
    "fonctions-paires-et-impaires": (64301, 64302, 64303),
    "inegalites-et-position-relative-de-courbes": (64401, 64402, 64406),
    "etude-d-une-fonction-et-methode-de-newton": (64501, 64505, 64506),
}

# ── Adaptation au manuel « Première ES/L » (2026-10-26) ─────────────────────
# Voir PREMIERE_SPECIFIQUE_SUIVI.md. Notions hors manuel retirées de la banque
# servie (exercices conservés ici) : parité, inégalités et position relative,
# méthode de Newton.
EXERCICES_HORS_PERIMETRE = [e for e in EXERCISES if e.notion in (N3, N4, N5)]
EXERCISES = [e for e in EXERCISES if e.notion in (N1, N2)]
NOTIONS = (N1, N2)
NOTION_IDS = ("variations-d-une-fonction", "nombre-derive-et-extremums-locaux")
QUIZ = {k: v for k, v in QUIZ.items() if k in NOTION_IDS}
