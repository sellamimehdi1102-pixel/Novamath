// ── landing.js : bandeau de statistiques animées + FAQ + thème + badge classe ─
import { describe, it, expect, vi, beforeEach } from "vitest";
import { loadPageBody, flushPromises } from "./testUtils.js";

const mockApi = { getSiteStats: vi.fn() };
vi.mock("../api.js", () => ({ api: mockApi }));
vi.mock("../curriculumSelector.js", () => ({
  getStoredClassLevel: () => "seconde",
  initClassBadge: vi.fn(),
  fetchCurricula: vi.fn().mockResolvedValue([{ classLevel: "seconde", label: "Seconde" }]),
}));

async function mountLanding() {
  document.body.innerHTML = loadPageBody("index.html");
  mockApi.getSiteStats.mockReset();
  mockApi.getSiteStats.mockResolvedValue({ totalExercises: 1234, chapters: 12, notions: 40, difficultyLevels: 5 });
  vi.resetModules();
  await import("../landing.js");
  await flushPromises();
}

describe("landing.js — FAQ accordéon", () => {
  beforeEach(async () => {
    await mountLanding();
  });

  it("ouvre un item de FAQ au clic sur sa question", () => {
    const item = document.querySelector(".faq-item");
    item.querySelector(".faq-question").click();
    expect(item.classList.contains("open")).toBe(true);
  });

  it("un second clic referme l'item (bascule)", () => {
    const item = document.querySelector(".faq-item");
    item.querySelector(".faq-question").click();
    item.querySelector(".faq-question").click();
    expect(item.classList.contains("open")).toBe(false);
  });
});

describe("landing.js — libellé de classe (bandeau + FAQ)", () => {
  it("met à jour #stats-class-label et #faq-class-label avec le libellé du cursus actif", async () => {
    await mountLanding();
    expect(document.getElementById("stats-class-label").textContent).toBe("Seconde");
    expect(document.getElementById("faq-class-label").textContent).toBe("Seconde");
  });
});

describe("landing.js — statistiques du bandeau (/api/site/stats)", () => {
  it("appelle getSiteStats avec la classe active", async () => {
    await mountLanding();
    expect(mockApi.getSiteStats).toHaveBeenCalledWith("seconde");
  });

  it("met à jour le nombre de chapitres dans la FAQ", async () => {
    await mountLanding();
    expect(document.getElementById("faq-chapter-count").textContent).toBe("12");
  });

  it("anime les compteurs jusqu'à la valeur cible", async () => {
    await mountLanding();
    const notionsEl = document.querySelector('.stat-item[data-stat="notions"] .stat-value');
    const target = (40).toLocaleString("fr-FR");
    // requestAnimationFrame en jsdom n'a pas une cadence garantie identique à
    // un vrai navigateur — on scrute au lieu d'attendre une durée fixe unique,
    // pour ne jamais dépendre d'un minutage exact non garanti par jsdom.
    const deadline = Date.now() + 4000;
    while (notionsEl.textContent !== target && Date.now() < deadline) {
      await new Promise((r) => setTimeout(r, 100));
    }
    expect(notionsEl.textContent).toBe(target);
  }, 10000);

  it("ne plante pas si l'appel /api/site/stats échoue", async () => {
    document.body.innerHTML = loadPageBody("index.html");
    mockApi.getSiteStats.mockReset();
    mockApi.getSiteStats.mockRejectedValue(new Error("réseau"));
    vi.resetModules();
    await expect(import("../landing.js")).resolves.toBeDefined();
    await flushPromises();
  });
});
