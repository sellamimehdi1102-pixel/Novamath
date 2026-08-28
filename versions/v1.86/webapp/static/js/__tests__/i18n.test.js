// ── i18n.js : dictionnaires fr/en + application au DOM via [data-i18n] ─────
import { describe, it, expect, vi, beforeEach } from "vitest";

let mockLanguage = "fr";
const mockChangeHandlers = [];

vi.mock("../settingsManager.js", () => ({
  getSettings: () => ({ language: mockLanguage }),
  onSettingsChange: (cb) => {
    mockChangeHandlers.push(cb);
    return () => {};
  },
}));

import { t, currentLanguage, applyTranslations, bindLiveTranslations } from "../i18n.js";

describe("i18n.js — currentLanguage / t()", () => {
  beforeEach(() => {
    mockLanguage = "fr";
    mockChangeHandlers.length = 0;
  });

  it("currentLanguage() vaut 'fr' par défaut", () => {
    expect(currentLanguage()).toBe("fr");
  });

  it("currentLanguage() bascule sur 'en' si settings.language === 'en'", () => {
    mockLanguage = "en";
    expect(currentLanguage()).toBe("en");
  });

  it("toute langue autre que 'en' retombe sur 'fr'", () => {
    mockLanguage = "de";
    expect(currentLanguage()).toBe("fr");
  });

  it("t() traduit une clé connue en français", () => {
    expect(t("nav.dashboard")).toBe("Dashboard");
  });

  it("t() traduit une clé connue en anglais", () => {
    mockLanguage = "en";
    expect(t("nav.cours")).toBe("Courses");
  });

  it("t() retombe sur le fallback pour une clé inconnue", () => {
    expect(t("clef.inconnue", "Valeur par défaut")).toBe("Valeur par défaut");
  });

  it("t() retombe sur la clé elle-même sans fallback fourni", () => {
    expect(t("clef.inconnue")).toBe("clef.inconnue");
  });

  it("t() retombe sur le français si une clé manque dans le dictionnaire anglais", () => {
    mockLanguage = "en";
    expect(t("nav.dashboard")).toBe("Dashboard");
  });
});

describe("i18n.js — applyTranslations", () => {
  beforeEach(() => {
    mockLanguage = "fr";
  });

  it("remplace le textContent des éléments [data-i18n]", () => {
    document.body.innerHTML = '<span data-i18n="nav.dashboard">x</span>';
    applyTranslations();
    expect(document.querySelector("span").textContent).toBe("Dashboard");
  });

  it("remplace un attribut ciblé via [data-i18n-attr]", () => {
    document.body.innerHTML = '<input data-i18n="cmd_palette_placeholder" data-i18n-attr="placeholder">';
    applyTranslations();
    expect(document.querySelector("input").getAttribute("placeholder")).toBe("Rechercher ou naviguer…");
  });

  it("pose lang= sur <html>", () => {
    applyTranslations();
    expect(document.documentElement.getAttribute("lang")).toBe("fr");
  });

  it("accepte une racine restreinte (root autre que document)", () => {
    const container = document.createElement("div");
    container.innerHTML = '<span data-i18n="nav.chatbot"></span>';
    document.body.appendChild(container);
    applyTranslations(container);
    expect(container.querySelector("span").textContent).toBe("Chatbot");
  });
});

describe("i18n.js — bindLiveTranslations", () => {
  beforeEach(() => {
    mockLanguage = "fr";
    mockChangeHandlers.length = 0;
  });

  it("applique les traductions immédiatement à l'appel", () => {
    document.body.innerHTML = '<span data-i18n="nav.exercices"></span>';
    bindLiveTranslations();
    expect(document.querySelector("span").textContent).toBe("Exercices");
  });

  it("s'enregistre auprès de onSettingsChange pour réagir aux changements de langue", () => {
    bindLiveTranslations();
    expect(mockChangeHandlers.length).toBeGreaterThan(0);
  });

  it("réapplique les traductions quand category === 'language'", () => {
    document.body.innerHTML = '<span data-i18n="nav.chatbot"></span>';
    bindLiveTranslations();
    mockLanguage = "en";
    mockChangeHandlers.forEach((cb) => cb({ detail: { category: "language" } }));
    expect(document.querySelector("span").textContent).toBe("Chatbot");
  });

  it("ignore un changement d'une autre catégorie que 'language'/'*'", () => {
    document.body.innerHTML = '<span data-i18n="nav.cours"></span>';
    bindLiveTranslations();
    mockLanguage = "en";
    mockChangeHandlers.forEach((cb) => cb({ detail: { category: "training" } }));
    expect(document.querySelector("span").textContent).toBe("Cours");
  });
});
