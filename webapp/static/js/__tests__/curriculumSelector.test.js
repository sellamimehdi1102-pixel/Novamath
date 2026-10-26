// ── curriculumSelector.js : sélection du cursus (classe active) ────────────
import { describe, it, expect, vi } from "vitest";

const mockGetCurricula = vi.fn();
vi.mock("../api.js", () => ({ api: { getCurricula: (...a) => mockGetCurricula(...a) } }));

import {
  CLASS_LEVEL_KEY,
  getStoredClassLevel,
  setStoredClassLevel,
  renderCurriculumCard,
  hasExplicitClassLevel,
  ALLOWED_NEXT_PAGES,
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

describe("curriculumSelector.js — hasExplicitClassLevel (Phase 5, onboarding)", () => {
  it("false si la clé n'a jamais été écrite, même si getStoredClassLevel() retombe sur 'seconde'", () => {
    localStorage.removeItem(CLASS_LEVEL_KEY);
    expect(hasExplicitClassLevel()).toBe(false);
    expect(getStoredClassLevel()).toBe("seconde");
  });

  it("true après un choix explicite via setStoredClassLevel", () => {
    localStorage.removeItem(CLASS_LEVEL_KEY);
    setStoredClassLevel("seconde");
    expect(hasExplicitClassLevel()).toBe(true);
  });
});

describe("curriculumSelector.js — ALLOWED_NEXT_PAGES (Phase 5, onboarding)", () => {
  it("liste exactement les 4 destinations internes historiques", () => {
    expect(ALLOWED_NEXT_PAGES).toEqual(["dashboard.html", "chapitres.html", "exercice.html", "profil.html"]);
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

  it("programme en prévisualisation (published: false) : annoncé en préparation, jamais « Programme officiel »", () => {
    const card = renderCurriculumCard({
      ...CURRICULA[0],
      classLevel: "quatrieme",
      label: "Quatrième",
      published: false,
    });
    expect(card.querySelector(".cursus-card-desc").textContent).toBe("En préparation — aperçu local, non publié");
    expect(card.getAttribute("aria-label")).toBe("Quatrième — En préparation — aperçu local, non publié");
    expect(card.textContent).not.toContain("Programme officiel");
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

  describe("classe mémorisée qui n'est plus servie (prévisualisation arrêtée)", () => {
    function stubReload() {
      const original = window.location;
      const reload = vi.fn();
      Object.defineProperty(window, "location", { value: { ...original, reload }, writable: true, configurable: true });
      return {
        reload,
        restore: () =>
          Object.defineProperty(window, "location", { value: original, writable: true, configurable: true }),
      };
    }

    it("oublie le choix et recharge une seule fois sur la classe par défaut", async () => {
      const { reload, restore } = stubReload();
      localStorage.setItem(CLASS_LEVEL_KEY, "quatrieme");
      mockGetCurricula.mockResolvedValue(CURRICULA);
      const initClassBadgeFresh = await freshInitClassBadge();
      initClassBadgeFresh(buildButton());
      await new Promise((r) => setTimeout(r, 0));
      expect(localStorage.getItem(CLASS_LEVEL_KEY)).toBeNull();
      expect(reload).toHaveBeenCalledTimes(1);
      restore();
    });

    it("ne touche à rien quand la classe mémorisée est servie, ou si la liste n'a pas pu être chargée", async () => {
      const { reload, restore } = stubReload();
      localStorage.setItem(CLASS_LEVEL_KEY, "premiere");
      mockGetCurricula.mockResolvedValue(CURRICULA);
      let initClassBadgeFresh = await freshInitClassBadge();
      const btn = buildButton();
      initClassBadgeFresh(btn);
      await new Promise((r) => setTimeout(r, 0));
      expect(btn.querySelector(".class-badge-label").textContent).toBe("Première");

      localStorage.setItem(CLASS_LEVEL_KEY, "quatrieme");
      mockGetCurricula.mockRejectedValue(new Error("réseau"));
      initClassBadgeFresh = await freshInitClassBadge();
      initClassBadgeFresh(buildButton());
      await new Promise((r) => setTimeout(r, 0));
      expect(localStorage.getItem(CLASS_LEVEL_KEY)).toBe("quatrieme");
      expect(reload).not.toHaveBeenCalled();
      localStorage.removeItem(CLASS_LEVEL_KEY);
      restore();
    });
  });
});
