// ── icons.js : bibliothèque d'icônes inline (style Lucide) ─────────────────
import { describe, it, expect } from "vitest";
import { ICONS, icon } from "../icons.js";

describe("icons.js — ICONS", () => {
  it("expose un dictionnaire non vide de SVG inline", () => {
    expect(Object.keys(ICONS).length).toBeGreaterThan(20);
  });

  it("chaque icône est un <svg> valide avec viewBox", () => {
    Object.entries(ICONS).forEach(([name, svg]) => {
      expect(svg, `icône '${name}'`).toMatch(/^<svg viewBox="0 0 24 24"/);
      expect(svg).toContain("</svg>");
    });
  });

  it("contient les icônes couramment utilisées par les autres modules", () => {
    ["check", "x", "search", "trash", "bookOpen", "settings", "lock"].forEach((name) => {
      expect(ICONS[name]).toBeDefined();
    });
  });
});

describe("icons.js — icon()", () => {
  it("enveloppe une icône connue dans un <span class='btn-icon'>", () => {
    expect(icon("check")).toBe(`<span class="btn-icon ">${ICONS.check}</span>`);
  });

  it("ajoute une classe supplémentaire si fournie", () => {
    expect(icon("x", "large")).toBe(`<span class="btn-icon large">${ICONS.x}</span>`);
  });

  it("renvoie un span vide pour un nom d'icône inconnu (jamais d'exception)", () => {
    expect(icon("icone-inexistante")).toBe('<span class="btn-icon "></span>');
  });
});
