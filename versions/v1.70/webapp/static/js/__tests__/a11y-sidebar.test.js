// ── Accessibilité : sidebar.js — fichier séparé de a11y.test.js ────────────
// sidebar.js appelle api.me()/curriculumSelector.fetchCurricula() au montage :
// mock nécessaire ici (contrairement à a11y.test.js, qui teste des composants
// sans aucun appel réseau) — voir sidebar.test.js pour le même mock, déjà
// éprouvé là-bas.
import { describe, it, expect, vi } from "vitest";
import axe from "axe-core";
import { loadPageBody, flushPromises } from "./testUtils.js";

const mockApi = { me: vi.fn().mockRejectedValue(new Error("401")) };
vi.mock("../api.js", () => ({ api: mockApi }));
vi.mock("../curriculumSelector.js", () => ({ initClassBadge: vi.fn() }));

const AXE_OPTIONS = {
  rules: {
    "color-contrast": { enabled: false },
    "landmark-one-main": { enabled: false },
    region: { enabled: false },
  },
};

describe("a11y — sidebar.js (navigation, aria-expanded, tooltips clavier)", () => {
  async function mountSidebar() {
    document.body.innerHTML = loadPageBody("dashboard.html");
    vi.resetModules();
    await import("../sidebar.js");
    await flushPromises();
  }

  it("le bouton de repli expose aria-expanded et un aria-label", async () => {
    await mountSidebar();
    const btn = document.getElementById("sidebar-collapse-btn");
    expect(btn.getAttribute("aria-expanded")).toBe("true");
    expect(btn.getAttribute("aria-label")).toBeTruthy();
  });

  it("aria-expanded reste synchronisé après une bascule clavier (Entrée sur le bouton)", async () => {
    await mountSidebar();
    const btn = document.getElementById("sidebar-collapse-btn");
    btn.focus();
    btn.click(); // activation clavier native (Entrée/Espace) déclenche le même événement click
    expect(btn.getAttribute("aria-expanded")).toBe("false");
  });

  it("ne produit aucune violation axe-core critique sur la sidebar rendue", async () => {
    await mountSidebar();
    const results = await axe.run(document.querySelector(".sidebar"), AXE_OPTIONS);
    const critical = results.violations.filter((v) => v.impact === "critical");
    expect(critical).toEqual([]);
  });
});
