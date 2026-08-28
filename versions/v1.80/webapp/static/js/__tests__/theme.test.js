// ── theme.js : thème clair/sombre + apparence (accent, taille police, radius) ─
import { describe, it, expect, vi } from "vitest";
import {
  currentTheme,
  setTheme,
  toggleTheme,
  bindThemeToggle,
  applyAppearance,
  getAccentColor,
  getAccentColorSecondary,
  accentRgba,
  getCachedAppearance,
  setAppearance,
  APPEARANCE_KEY,
} from "../theme.js";

describe("theme.js — currentTheme / setTheme / toggleTheme", () => {
  it("currentTheme() vaut 'light' par défaut (aucun attribut posé) — V4", () => {
    document.documentElement.removeAttribute("data-theme");
    expect(currentTheme()).toBe("light");
  });

  it("setTheme('light') pose l'attribut et persiste en localStorage", () => {
    setTheme("light");
    expect(document.documentElement.getAttribute("data-theme")).toBe("light");
    expect(currentTheme()).toBe("light");
  });

  it("toggleTheme() bascule dark <-> light", () => {
    setTheme("dark");
    expect(toggleTheme()).toBe("light");
    expect(toggleTheme()).toBe("dark");
  });

  it("bindThemeToggle() attache un handler de clic qui bascule le thème", () => {
    const btn = document.createElement("button");
    setTheme("dark");
    bindThemeToggle(btn);
    btn.click();
    expect(currentTheme()).toBe("light");
  });

  it("bindThemeToggle(null) ne lève aucune erreur", () => {
    expect(() => bindThemeToggle(null)).not.toThrow();
  });
});

describe("theme.js — applyAppearance", () => {
  it("applique un thème valide et retombe sur les valeurs par défaut pour le reste", () => {
    applyAppearance({ theme: "light" });
    const root = document.documentElement;
    expect(root.getAttribute("data-theme")).toBe("light");
    expect(root.getAttribute("data-accent")).toBe("purple");
    expect(root.getAttribute("data-font-size")).toBe("normal");
    expect(root.getAttribute("data-radius")).toBe("normal");
  });

  it("ignore un accent/fontSize/radius invalide (retombe sur défaut)", () => {
    applyAppearance({ accent: "invalide", fontSize: "gigantesque", radius: "carré" });
    const root = document.documentElement;
    expect(root.getAttribute("data-accent")).toBe("purple");
    expect(root.getAttribute("data-font-size")).toBe("normal");
    expect(root.getAttribute("data-radius")).toBe("normal");
  });

  it("accepte un accent/fontSize/radius valide", () => {
    applyAppearance({ accent: "blue", fontSize: "large", radius: "rounded" });
    const root = document.documentElement;
    expect(root.getAttribute("data-accent")).toBe("blue");
    expect(root.getAttribute("data-font-size")).toBe("large");
    expect(root.getAttribute("data-radius")).toBe("rounded");
  });

  it("data-animations passe à 'off' seulement si animations === false explicitement", () => {
    applyAppearance({ animations: false });
    expect(document.documentElement.getAttribute("data-animations")).toBe("off");
    applyAppearance({});
    expect(document.documentElement.getAttribute("data-animations")).toBe("on");
  });

  it("synchronise <meta name=theme-color> si présent", () => {
    const meta = document.createElement("meta");
    meta.setAttribute("name", "theme-color");
    document.head.appendChild(meta);
    applyAppearance({});
    expect(meta.getAttribute("content")).toBe(getAccentColor());
    document.head.removeChild(meta);
  });
});

describe("theme.js — getAccentColor / accentRgba", () => {
  it("retombe sur la couleur indigo par défaut hors CSS chargé (jsdom)", () => {
    expect(getAccentColor()).toBe("#5b57d6");
  });

  it("retombe sur la couleur violette secondaire par défaut", () => {
    expect(getAccentColorSecondary()).toBe("#8f63e0");
  });

  it("accentRgba() construit une chaîne rgba() avec l'alpha demandé", () => {
    expect(accentRgba(0.5)).toBe("rgba(117, 67, 223, 0.5)");
  });

  it("accentRgba() sans argument utilise alpha=1", () => {
    expect(accentRgba()).toBe("rgba(117, 67, 223, 1)");
  });
});

describe("theme.js — cache d'apparence (localStorage)", () => {
  it("getCachedAppearance() renvoie les valeurs par défaut si aucun cache", () => {
    expect(getCachedAppearance().theme).toBe("light");
    expect(getCachedAppearance().accent).toBe("purple");
  });

  it("setAppearance() fusionne un patch partiel sans écraser les autres clés", () => {
    setAppearance({ accent: "green" });
    setAppearance({ fontSize: "small" });
    const cached = getCachedAppearance();
    expect(cached.accent).toBe("green");
    expect(cached.fontSize).toBe("small");
  });

  it("setAppearance() applique immédiatement le changement au DOM", () => {
    setAppearance({ accent: "red" });
    expect(document.documentElement.getAttribute("data-accent")).toBe("red");
  });

  it("préserve les catégories déjà en cache (ex: training) hors 'appearance'", () => {
    localStorage.setItem(APPEARANCE_KEY, JSON.stringify({ training: { mode: "libre" } }));
    setAppearance({ accent: "orange" });
    const full = JSON.parse(localStorage.getItem(APPEARANCE_KEY));
    expect(full.training).toEqual({ mode: "libre" });
    expect(full.appearance.accent).toBe("orange");
  });

  it("récupère proprement d'un JSON corrompu en localStorage", () => {
    localStorage.setItem(APPEARANCE_KEY, "{ceci n'est pas du JSON");
    expect(getCachedAppearance().theme).toBe("light");
  });
});

describe("theme.js — initTheme() au chargement du module", () => {
  it("applique le thème sauvegardé en localStorage dès l'import", async () => {
    vi.resetModules();
    localStorage.setItem("lumis:theme", "light");
    document.documentElement.removeAttribute("data-theme");
    await import("../theme.js");
    expect(document.documentElement.getAttribute("data-theme")).toBe("light");
  });
});
