// ── choisirClasse.js : page dédiée /choisir-classe.html — Phase 5 (onboarding).
// Vérifie que la sélection d'un cursus persiste le choix ET honore un ?next=
// interne valide (posé par auth.js::redirectAfterSignup) sans jamais permettre
// une redirection externe (open redirect).
import { describe, it, expect, vi } from "vitest";
import { loadPageBody, withMockedLocation, flushPromises } from "./testUtils.js";
import { CLASS_LEVEL_KEY } from "../curriculumSelector.js";

const mockGetCurricula = vi.fn();
vi.mock("../api.js", () => ({ api: { getCurricula: (...a) => mockGetCurricula(...a) } }));
vi.mock("../theme.js", () => ({ bindThemeToggle: vi.fn() }));
vi.mock("../scroll-reveal.js", () => ({ initScrollReveal: vi.fn() }));

const CURRICULA = [
  { classLevel: "seconde", label: "Seconde", totalExercises: 1200, chapters: 12, notions: 40 },
  { classLevel: "premiere", label: "Première", totalExercises: 900, chapters: 10, notions: 35 },
];

// `url` : window.location persiste entre tests d'un même fichier (un seul
// jsdom par fichier) — toujours la réassigner explicitement (même convention
// que auth.test.js::mountAuth) pour qu'un ?next= ne reste jamais collé au
// test suivant.
async function mountChoisirClasse(url = "/choisir-classe.html") {
  window.history.pushState({}, "", url);
  document.body.innerHTML = loadPageBody("choisir-classe.html");
  mockGetCurricula.mockReset();
  mockGetCurricula.mockResolvedValue(CURRICULA);
  vi.resetModules();
  await import("../choisirClasse.js");
  await flushPromises();
  await flushPromises();
}

function clickCurriculum(label) {
  const cta = [...document.querySelectorAll(".cursus-card")]
    .find((card) => card.querySelector(".cursus-card-title").textContent === label)
    .querySelector(".cursus-card-cta");
  cta.click();
}

describe("choisirClasse.js — sélection sans ?next= (comportement historique)", () => {
  it("persiste la classe et retourne vers index.html", async () => {
    localStorage.removeItem(CLASS_LEVEL_KEY);
    await mountChoisirClasse();
    await withMockedLocation(async () => {
      clickCurriculum("Première");
      expect(localStorage.getItem(CLASS_LEVEL_KEY)).toBe("premiere");
      expect(window.location.href).toBe("index.html");
    });
  });
});

describe("choisirClasse.js — Phase 5 (onboarding) : détour depuis auth.js via ?next=", () => {
  it("next=dashboard.html : redirige vers /dashboard.html après le choix", async () => {
    await mountChoisirClasse("/choisir-classe.html?next=dashboard.html");
    await withMockedLocation(async () => {
      clickCurriculum("Seconde");
      expect(window.location.href).toBe("/dashboard.html");
    });
  });

  it("next=chapitres.html : redirige vers /chapitres.html après le choix", async () => {
    await mountChoisirClasse("/choisir-classe.html?next=chapitres.html");
    await withMockedLocation(async () => {
      clickCurriculum("Seconde");
      expect(window.location.href).toBe("/chapitres.html");
    });
  });

  it("next externe (open redirect) : ignoré, retombe sur le comportement historique (index.html)", async () => {
    await mountChoisirClasse("/choisir-classe.html?next=https://evil.example.com");
    await withMockedLocation(async () => {
      clickCurriculum("Seconde");
      expect(window.location.href).toBe("index.html");
    });
  });

  it("next inconnu (hors liste blanche) : ignoré, retombe sur index.html", async () => {
    await mountChoisirClasse("/choisir-classe.html?next=admin.html");
    await withMockedLocation(async () => {
      clickCurriculum("Seconde");
      expect(window.location.href).toBe("index.html");
    });
  });

  it("marque le choix comme explicite (setStoredClassLevel appelé) même avec ?next=", async () => {
    localStorage.removeItem(CLASS_LEVEL_KEY);
    await mountChoisirClasse("/choisir-classe.html?next=dashboard.html");
    await withMockedLocation(async () => {
      clickCurriculum("Première");
      expect(localStorage.getItem(CLASS_LEVEL_KEY)).toBe("premiere");
    });
  });
});
