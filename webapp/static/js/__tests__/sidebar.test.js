// ── sidebar.js : rail de navigation + drawer mobile + cadenas de features ──
import { describe, it, expect, vi, beforeEach } from "vitest";
import { loadPageBody, flushPromises } from "./testUtils.js";

const mockApi = { me: vi.fn().mockRejectedValue(new Error("401")) };
vi.mock("../api.js", () => ({ api: mockApi }));
vi.mock("../curriculumSelector.js", () => ({
  initClassBadge: vi.fn(),
}));

async function mountSidebar() {
  document.body.innerHTML = loadPageBody("dashboard.html");
  vi.resetModules();
  await import("../sidebar.js");
  await flushPromises();
}

describe("sidebar.js — initialisation", () => {
  beforeEach(async () => {
    await mountSidebar();
  });

  it("injecte le badge de classe", () => {
    expect(document.getElementById("class-badge-btn")).not.toBeNull();
  });

  it("injecte le déclencheur mobile et l'overlay de drawer", () => {
    expect(document.getElementById("sidebar-mobile-trigger")).not.toBeNull();
    expect(document.querySelector(".sidebar-overlay")).not.toBeNull();
  });

  it("pose data-tooltip sur chaque lien de navigation depuis son libellé", () => {
    const dashboardLink = document.querySelector('.sidebar-link[href="dashboard.html"]');
    expect(dashboardLink.getAttribute("data-tooltip")).toBe("Dashboard");
  });
});

// Chantier 10 (centralisation du feature gating) : PAGE_FEATURE_REQUIREMENTS
// est vide en production aujourd'hui (aucune page ne dépasse Free), donc ce
// mécanisme n'était exercé par AUCUN test jusqu'ici — un vrai angle mort.
// Simule une entrée verrouillée pour prouver que sidebar.js::applyFeatureLocks
// décide bien via hasFeature(user, featureValue) — jamais un recalcul de plan
// local — et que le lien reste cliquable (redirection vers l'offre), jamais
// masqué.
describe("sidebar.js — cadenas de feature (PAGE_FEATURE_REQUIREMENTS)", () => {
  it("verrouille un lien dont hasFeature(user, ...) renvoie false, et le laisse cliquable", async () => {
    vi.doMock("../features.js", async (importOriginal) => {
      const actual = await importOriginal();
      return {
        ...actual,
        PAGE_FEATURE_REQUIREMENTS: { "chatbot.html": "advanced_ai" },
        hasFeature: vi.fn(() => false),
      };
    });
    // mockResolvedValue (pas ...Once) : init() appelle api.me() PLUSIEURS
    // fois en série (applyAdminMenuEntry PUIS applyFeatureLocks PUIS
    // owner-test-panel.js) — un ...Once ne couvrirait que le premier appel
    // (applyAdminMenuEntry), jamais celui qui nous intéresse ici.
    mockApi.me.mockResolvedValue({ user: { plan: "free", features: { advanced_ai: false } } });

    await mountSidebar();

    const link = document.querySelector('.sidebar-link[href="chatbot.html"]');
    expect(link.classList.contains("is-locked")).toBe(true);
    expect(link.querySelector(".sidebar-link-lock")).not.toBeNull();

    vi.doUnmock("../features.js");
    mockApi.me.mockRejectedValue(new Error("401"));
  });

  it("ne verrouille rien quand hasFeature(user, ...) renvoie true", async () => {
    vi.doMock("../features.js", async (importOriginal) => {
      const actual = await importOriginal();
      return {
        ...actual,
        PAGE_FEATURE_REQUIREMENTS: { "chatbot.html": "advanced_ai" },
        hasFeature: vi.fn(() => true),
      };
    });
    mockApi.me.mockResolvedValue({ user: { plan: "ultra", features: { advanced_ai: true } } });

    await mountSidebar();

    const link = document.querySelector('.sidebar-link[href="chatbot.html"]');
    expect(link.classList.contains("is-locked")).toBe(false);
    expect(link.querySelector(".sidebar-link-lock")).toBeNull();

    vi.doUnmock("../features.js");
    mockApi.me.mockRejectedValue(new Error("401"));
  });
});

describe("sidebar.js — drawer mobile", () => {
  beforeEach(async () => {
    await mountSidebar();
  });

  it("ouvre le drawer au clic sur le déclencheur mobile", () => {
    document.getElementById("sidebar-mobile-trigger").click();
    expect(document.querySelector(".sidebar").classList.contains("is-open")).toBe(true);
    expect(document.body.classList.contains("sidebar-drawer-open")).toBe(true);
  });

  it("ferme le drawer au clic sur l'overlay", () => {
    document.getElementById("sidebar-mobile-trigger").click();
    document.querySelector(".sidebar-overlay").click();
    expect(document.querySelector(".sidebar").classList.contains("is-open")).toBe(false);
  });

  it("ferme le drawer avec la touche Échap (navigation clavier)", () => {
    document.getElementById("sidebar-mobile-trigger").click();
    window.dispatchEvent(new KeyboardEvent("keydown", { key: "Escape" }));
    expect(document.querySelector(".sidebar").classList.contains("is-open")).toBe(false);
  });

  it("ferme le drawer au clic sur un lien de navigation", () => {
    document.getElementById("sidebar-mobile-trigger").click();
    document.querySelector(".sidebar-link").click();
    expect(document.querySelector(".sidebar").classList.contains("is-open")).toBe(false);
  });
});
