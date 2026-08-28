// ── curriculumSelector.js : sélection du cursus (classe active) ────────────
import { describe, it, expect, vi } from "vitest";

const mockGetCurricula = vi.fn();
vi.mock("../api.js", () => ({ api: { getCurricula: (...a) => mockGetCurricula(...a) } }));

import {
  CLASS_LEVEL_KEY,
  getStoredClassLevel,
  setStoredClassLevel,
  renderCurriculumCard,
} from "../curriculumSelector.js";

const CURRICULA = [
  { classLevel: "seconde", label: "Seconde", totalExercises: 1200, chapters: 12, notions: 40 },
  { classLevel: "premiere", label: "Première", totalExercises: 900, chapters: 10, notions: 35 },
];

describe("curriculumSelector.js — getStoredClassLevel / setStoredClassLevel", () => {
  it("renvoie 'seconde' par défaut", () => {
    expect(getStoredClassLevel()).toBe("seconde");
  });

  it("persiste et relit la classe choisie", () => {
    setStoredClassLevel("premiere");
    expect(getStoredClassLevel()).toBe("premiere");
    expect(localStorage.getItem(CLASS_LEVEL_KEY)).toBe("premiere");
  });
});

describe("curriculumSelector.js — renderCurriculumCard", () => {
  it("construit une carte avec titre, stats et bouton CTA", () => {
    const card = renderCurriculumCard(CURRICULA[0]);
    expect(card.querySelector(".cursus-card-title").textContent).toBe("Seconde");
    expect(card.querySelectorAll(".cursus-stat")).toHaveLength(3);
    expect(card.querySelector(".cursus-card-cta")).not.toBeNull();
  });

  it("ajoute le badge 'Cursus actuel' si isCurrent=true", () => {
    const card = renderCurriculumCard(CURRICULA[0], { isCurrent: true });
    expect(card.classList.contains("is-current")).toBe(true);
    expect(card.querySelector(".cursus-card-current-badge")).not.toBeNull();
  });

  it("n'ajoute pas de badge si isCurrent=false", () => {
    const card = renderCurriculumCard(CURRICULA[0], { isCurrent: false });
    expect(card.querySelector(".cursus-card-current-badge")).toBeNull();
  });

  it("appelle onEnter(classLevel) au clic sur le CTA", () => {
    const onEnter = vi.fn();
    const card = renderCurriculumCard(CURRICULA[1], { onEnter });
    card.querySelector(".cursus-card-cta").dispatchEvent(new MouseEvent("click", { bubbles: true }));
    expect(onEnter).toHaveBeenCalledWith("premiere");
  });

  it("appelle onEnter(classLevel) au clic sur la carte elle-même", () => {
    const onEnter = vi.fn();
    const card = renderCurriculumCard(CURRICULA[1], { onEnter });
    card.dispatchEvent(new MouseEvent("click", { bubbles: true }));
    expect(onEnter).toHaveBeenCalledWith("premiere");
  });

  it("pose un aria-label descriptif (accessibilité)", () => {
    const card = renderCurriculumCard(CURRICULA[0]);
    expect(card.getAttribute("aria-label")).toBe("Seconde — Programme officiel");
  });
});

describe("curriculumSelector.js — initClassBadge", () => {
  // `_panel`/`_curriculaPromise` (curriculumSelector.js) sont un état privé
  // au niveau du module : un import statique unique (comme dans les describe
  // ci-dessus) ferait fuiter cet état d'un test à l'autre (un panneau resté
  // ouvert dans un test fausserait le comptage de clics du suivant). Import
  // dynamique + `vi.resetModules()` : chaque test repart d'un module vierge,
  // exactement comme un vrai rechargement de page.
  async function freshInitClassBadge() {
    vi.resetModules();
    const mod = await import("../curriculumSelector.js");
    return mod.initClassBadge;
  }

  function buildButton() {
    const btn = document.createElement("button");
    btn.innerHTML = '<span class="class-badge-label"></span>';
    document.body.appendChild(btn);
    return btn;
  }

  it("ne lève aucune erreur si buttonEl est null", async () => {
    const initClassBadgeFresh = await freshInitClassBadge();
    expect(() => initClassBadgeFresh(null)).not.toThrow();
  });

  it("pose aria-haspopup et câble le clic pour ouvrir le panneau", async () => {
    mockGetCurricula.mockResolvedValue(CURRICULA);
    const initClassBadgeFresh = await freshInitClassBadge();
    const btn = buildButton();
    initClassBadgeFresh(btn);
    expect(btn.getAttribute("aria-haspopup")).toBe("true");
  });

  it("ouvre un panneau flottant au clic, avec role=menu", async () => {
    mockGetCurricula.mockResolvedValue(CURRICULA);
    const initClassBadgeFresh = await freshInitClassBadge();
    const btn = buildButton();
    initClassBadgeFresh(btn);
    btn.click();
    expect(document.querySelector(".class-badge-panel[role='menu']")).not.toBeNull();
  });

  it("un second clic referme le panneau déjà ouvert (bascule)", async () => {
    mockGetCurricula.mockResolvedValue(CURRICULA);
    const initClassBadgeFresh = await freshInitClassBadge();
    const btn = buildButton();
    initClassBadgeFresh(btn);
    btn.click();
    btn.click();
    expect(document.querySelector(".class-badge-panel")).toBeNull();
  });
});
