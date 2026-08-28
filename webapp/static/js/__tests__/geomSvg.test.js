import { describe, it, expect } from "vitest";
import { renderFigure } from "../geomSvg.js";

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
      { kind: "bars", bars: [{ value: 3, label: "A" }, { value: 5, label: "B" }] },
      { kind: "pie", slices: [{ value: 1, label: "A" }, { value: 2, label: "B" }] },
      { kind: "boxplot", min: 0, q1: 2, median: 5, q3: 7, max: 10 },
      { kind: "solid", shape: "cube" },
    ];
    for (const spec of specs) {
      expect(() => renderFigure(spec)).not.toThrow();
      expect(renderFigure(spec)).toContain("<svg");
    }
  });
});
