// ── sidebar.js : sidebar rétractable + drawer mobile + cadenas de features ──
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

  it("injecte le bouton de réduction et le badge de classe", () => {
    expect(document.getElementById("sidebar-collapse-btn")).not.toBeNull();
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

describe("sidebar.js — repli/dépli (persisté en localStorage)", () => {
  beforeEach(async () => {
    await mountSidebar();
  });

  it("le clic sur le bouton de réduction replie la sidebar et persiste le choix", () => {
    const sidebar = document.querySelector(".sidebar");
    const btn = document.getElementById("sidebar-collapse-btn");
    btn.click();
    expect(sidebar.classList.contains("is-collapsed")).toBe(true);
    expect(localStorage.getItem("novamath:sidebarCollapsed")).toBe("1");
  });

  it("un second clic déplie à nouveau la sidebar", () => {
    const sidebar = document.querySelector(".sidebar");
    const btn = document.getElementById("sidebar-collapse-btn");
    btn.click();
    btn.click();
    expect(sidebar.classList.contains("is-collapsed")).toBe(false);
    expect(localStorage.getItem("novamath:sidebarCollapsed")).toBe("0");
  });

  it("met aria-expanded/aria-label à jour selon l'état", () => {
    const btn = document.getElementById("sidebar-collapse-btn");
    btn.click();
    expect(btn.getAttribute("aria-expanded")).toBe("false");
    expect(btn.getAttribute("aria-label")).toBe("Développer la barre latérale");
  });
});

describe("sidebar.js — restauration de l'état replié au chargement", () => {
  it("applique l'état 'replié' déjà persisté en localStorage", async () => {
    localStorage.setItem("novamath:sidebarCollapsed", "1");
    await mountSidebar();
    expect(document.querySelector(".sidebar").classList.contains("is-collapsed")).toBe(true);
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
