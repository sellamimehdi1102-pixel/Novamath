"""Construction des cours de Quatrième au schéma v2.

`notion()` remplit les champs que le schéma duplique (definitions,
etapesParNiveau.normal, erreursFrequentes, topic_id...) à partir d'une seule
saisie : les invariants vérifiés par les validateurs ne peuvent donc pas
diverger. Les aides de figures calculent les coordonnées et vérifient par
assertion ce que la figure prétend montrer (angle droit, parallélisme,
longueurs à l'échelle) : une figure ne peut pas suggérer une propriété fausse.
"""
import math

# ── Figures ──────────────────────────────────────────────────────────────────


def P(x, y):
    return {"x": round(x, 3), "y": round(y, 3)}


def pt(x, y, label, **kw):
    p = {"x": round(x, 3), "y": round(y, 3), "label": label}
    p.update(kw)
    return p


def dist(a, b):
    return math.hypot(a[0] - b[0], a[1] - b[1])


def mid(a, b, dx=0.0, dy=0.0):
    return ((a[0] + b[0]) / 2 + dx, (a[1] + b[1]) / 2 + dy)


def text(at, label, reveal=None, **kw):
    t = {"x": round(at[0], 3), "y": round(at[1], 3), "label": label}
    if reveal:
        t["reveal"] = reveal
    t.update(kw)
    return t


def seg(a, b, variant=None, reveal=None, tooltip=None):
    s = {"from": a, "to": b}
    if variant:
        s["variant"] = variant
    if reveal:
        s["reveal"] = reveal
    if tooltip:
        s["tooltip"] = tooltip
    return s


def poly(labels, tooltip=None, reveal=None, variant=None):
    p = {"points": list(labels)}
    if variant:
        p["variant"] = variant
    if tooltip:
        p["tooltip"] = tooltip
    if reveal:
        p["reveal"] = reveal
    return p


def right_marker(v, p, q, size=0.32, reveal=None):
    """Petit carré codant l'angle droit en `v` entre [vp] et [vq] — refuse un
    angle qui n'est pas réellement droit (produit scalaire nul)."""
    ux, uy = p[0] - v[0], p[1] - v[1]
    wx, wy = q[0] - v[0], q[1] - v[1]
    assert abs(ux * wx + uy * wy) < 1e-9, f"angle non droit en {v}"
    nu, nw = math.hypot(ux, uy), math.hypot(wx, wy)
    ux, uy, wx, wy = ux / nu * size, uy / nu * size, wx / nw * size, wy / nw * size
    marker = {
        "points": [P(*v), P(v[0] + ux, v[1] + uy), P(v[0] + ux + wx, v[1] + uy + wy), P(v[0] + wx, v[1] + wy)],
        "variant": "marker",
        "tooltip": "Codage de l'angle droit",
    }
    if reveal:
        marker["reveal"] = reveal
    return marker


def assert_parallel(a, b, c, d, tol=1e-9):
    """(ab) // (cd) : produit vectoriel nul."""
    assert abs((b[0] - a[0]) * (d[1] - c[1]) - (b[1] - a[1]) * (d[0] - c[0])) < tol, "droites non parallèles"


def assert_aligned(a, b, c, tol=1e-9):
    assert abs((b[0] - a[0]) * (c[1] - a[1]) - (b[1] - a[1]) * (c[0] - a[0])) < tol, "points non alignés"


def view_box(points, margin=1.0):
    """viewBox de geomSvg.js : [xmin, ymin, largeur, hauteur]."""
    xs = [p[0] for p in points]
    ys = [p[1] for p in points]
    return [round(min(xs) - margin, 2), round(min(ys) - margin, 2),
            round(max(xs) - min(xs) + 2 * margin, 2), round(max(ys) - min(ys) + 2 * margin, 2)]


def arc(center, radius, start_deg, end_deg, label=None, reveal=None, tooltip=None):
    """Arc d'angle (secteur) de centre `center` (nom de point), angles en degrés
    dans le sens trigonométrique."""
    a = {"center": center, "radius": radius, "startDeg": round(start_deg, 2), "endDeg": round(end_deg, 2)}
    if label:
        a["label"] = label
    if reveal:
        a["reveal"] = reveal
    if tooltip:
        a["tooltip"] = tooltip
    return a


def direction_deg(a, b):
    return math.degrees(math.atan2(b[1] - a[1], b[0] - a[0]))


def figure_geom(*, points, steps, alt, relation, explication, view, polygons=(), segments=(), texts=(), arcs=(),
                vectors=(), circles=(), grid=False, axes=False, emphasis=True, **extra):
    """Figure `geom` avec ses 3 étapes de révélation et sa fiche d'explication.
    `emphasis` (vrai par défaut) : colonne graphique élargie (cours.css,
    .cours-figure-layout--xl) — les libellés du SVG ont une taille fixe et
    deviennent illisibles quand une figure large est réduite à 44 % de la page
    (constaté sur les droites graduées et tableaux du lot A)."""
    assert len(steps) == 3, "une figure se déroule en 3 étapes"
    fig = {"kind": "geom", "viewBox": view, "grid": grid, "axes": axes, "points": list(points)}
    for key, value in (("polygons", polygons), ("segments", segments), ("texts", texts), ("arcs", arcs),
                       ("vectors", vectors), ("circles", circles)):
        if value:
            fig[key] = list(value)
    if emphasis:
        fig["emphasis"] = True
    fig.update(extra)
    fig.update({"steps": list(steps), "relation": relation, "alt": alt, "explication": explication})
    return fig


def explication(resume, lecture, observations, pieges, a_retenir, comprendre=None, etapes=None, astuce=None):
    """Fiche d'explication de la figure (cartes de cours.js, voir
    renderFigureBlock) : resume, comprendre, lecture[], observations[],
    etapes[{titre, texte}], astuce, pieges[], aRetenir[]."""
    e = {"resume": resume}
    if comprendre:
        e["comprendre"] = comprendre
    e["lecture"] = list(lecture)
    e["observations"] = list(observations)
    if etapes:
        e["etapes"] = [{"titre": t, "texte": x} for t, x in etapes]
    if astuce:
        e["astuce"] = astuce
    e["pieges"] = list(pieges)
    e["aRetenir"] = list(a_retenir)
    return e


# ── Notions ──────────────────────────────────────────────────────────────────


def step(icone, couleur, texte):
    return {"icone": icone, "couleur": couleur, "texte": texte}


def calc(texte, expr=""):
    return {"expr": expr, "texte": texte}


def formule(id, nom, expression, quand, erreur, astuce):
    return {"id": id, "nom": nom, "expression": expression, "quand_utiliser": quand,
            "erreur_frequente": erreur, "astuce": astuce}


def ex(id, titre, enonce, calcul, reponse, difficulte, niveau, **extra):
    """Exemple résolu. `niveau` : free | premium | ultra."""
    assert niveau in ("free", "premium", "ultra")
    assert difficulte in ("facile", "moyen", "difficile")
    e = {"id": id, "titre": titre, "enonce": enonce}
    e.update({k: v for k, v in extra.items() if k in ("analyse", "choixMethode", "explication")})
    e["calcul"] = calcul
    e["reponse"] = reponse
    for k in ("conclusion", "interpretation"):
        if k in extra:
            e[k] = extra[k]
    e["difficulte"] = difficulte
    e["niveauAcces"] = niveau
    return e


def demonstration(titre, etapes, conclusion):
    return {"titre": titre, "etapes": [{"titre": t, "texte": x} for t, x in etapes], "conclusion": conclusion}


def notion(*, id, title, intro, pourquoi, objectif, definition, definition_college, regles, formules, methode_titre,
           etapes, debutant, rapide, exemples, erreurs, astuce, a_retenir, explication_simple, intuition,
           exemples_concrets, figure, quiz, prerequis, notions_liees, objectifs, vocabulaire, synonymes, proprietes,
           tags, difficulte, apercu_premium, apercu_ultra, questions_eclair, demonstration=None, tableau=None):
    """`erreurs` : liste de (description, pourquoi, comment_detecter, comment_eviter).
    `apercu_premium` / `apercu_ultra` : (titre, description) — décrivent
    UNIQUEMENT ce que les exemples verrouillés (et la démonstration) contiennent."""
    niveaux = [e["niveauAcces"] for e in exemples]
    assert niveaux.count("free") >= 2 and niveaux.count("premium") >= 2 and niveaux.count("ultra") >= 1, id
    assert len({e["id"] for e in exemples}) == len(exemples), id
    assert len(regles) >= 3 and len(erreurs) >= 3 and len(etapes) >= 3, id
    assert difficulte in ("facile", "moyen", "difficile")
    n = {
        "id": id,
        "title": title,
        "schemaVersion": 2,
        "intro": intro,
        "pourquoi": pourquoi,
        "explicationSimple": explication_simple,
        "objectif": objectif,
        "definition": definition,
        "definitions": {"college": definition_college, "lycee": definition},
        "intuition": intuition,
        "reglesImportantes": list(regles),
        "formules": list(formules),
        "methode": {
            "titre": methode_titre,
            "etapes": list(etapes),
            "etapesParNiveau": {"normal": list(etapes), "debutant": list(debutant), "rapide": list(rapide)},
        },
        "exemples": list(exemples),
        "exemplesConcrets": list(exemples_concrets),
        "erreursFrequentes": [e[0] for e in erreurs],
        "erreursFrequentesDetail": [
            {"description": d, "pourquoi": p, "comment_detecter": c, "comment_eviter": v} for d, p, c, v in erreurs
        ],
        "astuce": astuce,
        "aRetenir": list(a_retenir),
        "figure": figure,
        "quizExerciseIds": list(quiz),
        "topic_id": id,
        "proprietes": list(proprietes),
        "vocabulaire_associe": list(vocabulaire),
        "synonymes": list(synonymes),
        "objectifs_pedagogiques": list(objectifs),
        "prerequis": list(prerequis),
        "notions_liees": list(notions_liees),
        "difficulte": difficulte,
        "tags": list(tags),
        "champsLibresForces": [],
        "apercus": [
            {"id": f"{id}-premium", "section": "exemple", "niveau": "premium",
             "titre": apercu_premium[0], "description": apercu_premium[1]},
            {"id": f"{id}-ultra", "section": "exemple", "niveau": "ultra",
             "titre": apercu_ultra[0], "description": apercu_ultra[1]},
        ],
        "questionsEclair": [{"apres": a, "question": q, "piste": r} for a, q, r in questions_eclair],
    }
    if tableau:
        n["tableauComparatif"] = tableau
    if demonstration:
        n["demonstration"] = demonstration
    return n


def chapter(number, title, icon, notions):
    ids = [n["id"] for n in notions]
    assert len(ids) == len(set(ids))
    for n in notions:
        for lie in n["notions_liees"]:
            assert lie != n["id"], n["id"]
    return {"chapterId": f"Chapitre_{number}", "title": title, "icon": icon, "notions": list(notions)}
