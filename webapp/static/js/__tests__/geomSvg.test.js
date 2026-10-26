import { describe, it, expect } from "vitest";
import { renderFigure, toKatexSource } from "../geomSvg.js";

// Chantier "cours" (refonte visuelle) : renderFigure ne doit JAMAIS lever
// d'exception, quel que soit le spec reçu — une figure malformée ne doit
// jamais casser l'affichage du reste de la notion (voir audit du système
// de figures : computeLayout plantait sur un spec "geom" sans viewBox).
describe("geomSvg.js — renderFigure", () => {
  it("rend un SVG pour un spec geom valide avec viewBox", () => {
    const svg = renderFigure({ viewBox: [-1, -1, 8, 8], points: [{ x: 1, y: 1, label: "A" }] });
    expect(svg).toContain("<svg");
    expect(svg).toContain("geom-point");
  });

  it("ne lève jamais d'exception sur un spec geom sans viewBox", () => {
    expect(() => renderFigure({ points: [{ x: 1, y: 1, label: "A" }] })).not.toThrow();
  });

  it("ne lève jamais d'exception sur un kind inconnu (typo)", () => {
    expect(() => renderFigure({ kind: "arbre-de-probabilite" })).not.toThrow();
  });

  it("ne lève jamais d'exception sur un spec vide", () => {
    expect(() => renderFigure({})).not.toThrow();
  });

  it("rend chaque kind connu sans exception avec des données minimales", () => {
    const specs = [
      { kind: "tree", branches: [{ label: "A", proba: "0,5", branches: [{ label: "X", proba: "0,5" }] }] },
      { kind: "venn", sets: ["A", "B"] },
      { kind: "nested-sets", labels: ["N", "Z", "Q"] },
      { kind: "numberline", min: 0, max: 10, marks: [{ value: 5, label: "5" }] },
      {
        kind: "bars",
        bars: [
          { value: 3, label: "A" },
          { value: 5, label: "B" },
        ],
      },
      {
        kind: "pie",
        slices: [
          { value: 1, label: "A" },
          { value: 2, label: "B" },
        ],
      },
      { kind: "boxplot", min: 0, q1: 2, median: 5, q3: 7, max: 10 },
      { kind: "solid", shape: "cube" },
      { kind: "pipeline", nodes: [{ titre: "x" }, { titre: "u(x)", sousTitre: "fonction intérieure" }] },
    ];
    for (const spec of specs) {
      expect(() => renderFigure(spec)).not.toThrow();
      expect(renderFigure(spec)).toContain("<svg");
    }
  });

  it("pie : une couleur nommée de la liste fermée s'applique, sinon la palette par rang", () => {
    const svg = renderFigure({
      kind: "pie",
      slices: [
        { value: 1, label: "rouge", color: "rouge" },
        { value: 4, label: "orange", color: "orange" },
        { value: 2, label: "autre", color: "url(javascript:x)" },
      ],
    });
    expect(svg).toContain("geom-pie-slice--c-rouge");
    expect(svg).toContain("geom-pie-slice--c-orange");
    expect(svg).toContain("geom-pie-slice--2");
    expect(svg).not.toContain("javascript");
  });
});

// ── kind: "pipeline" (refonte pédagogique des cours, 2026-10-23) — chaîne de
// calculs successifs, composant réutilisable pour toute notion présentée
// comme une suite d'étapes (composition de fonctions en premier lieu).
describe("geomSvg.js — renderFigure (kind: pipeline)", () => {
  it("rend une case par nœud, dans l'ordre, avec son titre", () => {
    const svg = renderFigure({
      kind: "pipeline",
      nodes: [{ titre: "x" }, { titre: "u(x) = 4x - 6" }, { titre: "f(x) = (4x-6)^3" }],
    });
    expect(svg).toContain("<svg");
    const iX = svg.indexOf("x</text>");
    const iU = svg.indexOf("u(x) = 4x - 6");
    const iF = svg.indexOf("f(x) = (4x-6)^3");
    expect(iX).toBeGreaterThan(-1);
    expect(iU).toBeGreaterThan(iX);
    expect(iF).toBeGreaterThan(iU);
  });

  it("affiche le sous-titre d'un nœud quand il est présent", () => {
    const svg = renderFigure({ kind: "pipeline", nodes: [{ titre: "u(x)", sousTitre: "fonction intérieure" }] });
    expect(svg).toContain("fonction intérieure");
  });

  it("échappe le texte des nœuds (jamais de HTML brut injecté)", () => {
    const svg = renderFigure({ kind: "pipeline", nodes: [{ titre: "<img onerror=alert(1)>" }] });
    expect(svg).not.toContain("<img");
    expect(svg).toContain("&lt;img");
  });

  it("ne lève jamais d'exception sans nodes", () => {
    expect(() => renderFigure({ kind: "pipeline" })).not.toThrow();
  });

  it("empile verticalement les chaînes de 3 cases ou plus (texte lisible dans une colonne étroite)", () => {
    const nodes = [{ titre: "a", sousTitre: "un" }, { titre: "b" }, { titre: "c" }, { titre: "d" }];
    const vertical = renderFigure({ kind: "pipeline", nodes });
    const [, w, h] = vertical.match(/viewBox="0 0 (\d+) (\d+)"/).map(Number);
    expect(vertical).toContain("geom-figure--pipeline-v");
    expect(w).toBeLessThan(400);
    expect(h).toBeGreaterThan(w);
    expect(vertical.match(/geom-pipeline-arrow"/g)).toHaveLength(3);
    const horizontal = renderFigure({ kind: "pipeline", nodes: nodes.slice(0, 2) });
    expect(horizontal).toContain("geom-figure--wide");
  });

  it("utilise un id de marker différent à chaque appel (pas de collision si deux figures sur la même page)", () => {
    const svg1 = renderFigure({ kind: "pipeline", nodes: [{ titre: "a" }, { titre: "b" }] });
    const svg2 = renderFigure({ kind: "pipeline", nodes: [{ titre: "a" }, { titre: "b" }] });
    const id1 = svg1.match(/marker id="([^"]+)"/)[1];
    const id2 = svg2.match(/marker id="([^"]+)"/)[1];
    expect(id1).not.toBe(id2);
  });
});

describe("geomSvg.js — renderFigure (kind: tableau)", () => {
  const spec = {
    kind: "tableau",
    xs: ["-\\infty", "-1", "3", "+\\infty"],
    rows: [
      { type: "signe", label: "f(x)", signs: ["+", "-", "+"], marks: ["", "0", "0", ""] },
      { type: "variation", label: "g", values: ["", "4", "-2", ""], levels: ["bas", "haut", "bas", "haut"] },
    ],
  };

  it("place une valeur de x par colonne et un signe par intervalle", () => {
    const svg = renderFigure(spec);
    expect(svg).toContain("geom-figure--tableau");
    expect((svg.match(/geom-tab-x/g) || []).length).toBe(4);
    expect((svg.match(/geom-tab-sign/g) || []).length).toBe(3);
    expect((svg.match(/geom-tab-zero/g) || []).length).toBe(2);
  });

  it("trace une flèche par intervalle de la ligne de variations et n'affiche que les valeurs fournies", () => {
    const svg = renderFigure(spec);
    expect((svg.match(/class="geom-tab-arrow"/g) || []).length).toBe(3);
    expect((svg.match(/geom-tab-value/g) || []).length).toBe(2);
  });

  it("dessine une double barre pour une valeur interdite", () => {
    const svg = renderFigure({
      kind: "tableau",
      xs: ["-\\infty", "0", "+\\infty"],
      rows: [{ type: "signe", label: "1/x", signs: ["-", "+"], marks: ["", "||", ""] }],
    });
    expect((svg.match(/geom-tab-bar/g) || []).length).toBe(2);
  });
});

describe("geomSvg.js — révélation progressive des points et des courbes", () => {
  it("un point marqué reveal n'apparaît qu'à l'étape indiquée (point et label)", () => {
    const svg = renderFigure({
      viewBox: [-1, -1, 4, 4],
      points: [
        { x: 0, y: 0, label: "A" },
        { x: 1, y: 1, label: "S", reveal: 2 },
      ],
    });
    expect((svg.match(/class="geom-point reveal-2"/g) || []).length).toBe(1);
    expect((svg.match(/class="geom-point"/g) || []).length).toBe(1);
    expect(svg).toMatch(/geom-label[^"]*reveal-2/);
  });

  it("une courbe peut porter une variante de couleur et une étape", () => {
    const svg = renderFigure({
      viewBox: [-1, -1, 4, 4],
      curves: [
        {
          points: [
            [0, 0],
            [1, 1],
          ],
          variant: "b",
          reveal: 3,
        },
      ],
    });
    expect(svg).toContain('class="geom-curve geom-curve--b reveal-3"');
  });
});

describe("geomSvg.js — toKatexSource", () => {
  it("rend la virgule décimale sans espace ({,})", () => {
    expect(toKatexSource("x₁ = 1,5")).toBe("x_{1}\\;=\\;1{,}5");
    expect(toKatexSource("e ≈ 2,718")).toContain("2{,}718");
  });

  it("ne touche pas aux autres virgules", () => {
    expect(toKatexSource("(0 ; 1)")).not.toContain("{,}");
  });
});
