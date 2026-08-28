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
