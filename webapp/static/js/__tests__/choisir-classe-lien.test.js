// ── choisirClasse.js : entrée par lien /maths-<classe> (?classe=...) ────────
// Classe présélectionnée pour l'onglet, mode invité sans compte, préférence
// persistante du profil jamais modifiée.
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { loadPageBody, flushPromises } from "./testUtils.js";

const mockApi = { me: vi.fn(), enterGuest: vi.fn(), getCurricula: vi.fn() };
vi.mock("../api.js", () => ({ api: mockApi }));

const CURRICULA = ["quatrieme", "troisieme", "seconde", "premiere", "premiere_specifique"].map((classLevel) => ({
  classLevel,
  label: classLevel,
}));
const originalLocation = window.location;
let replace;

async function openWith(search) {
  document.body.innerHTML = loadPageBody("choisir-classe.html");
  delete window.location;
  replace = vi.fn();
  window.location = { search, href: "", replace };
  vi.resetModules();
  await import("../choisirClasse.js");
  await flushPromises();
  await flushPromises();
}

beforeEach(() => {
  localStorage.clear();
  sessionStorage.clear();
  mockApi.me.mockReset();
  mockApi.enterGuest.mockReset().mockResolvedValue({ user: { id: 1 } });
  mockApi.getCurricula.mockReset().mockResolvedValue(CURRICULA);
});
afterEach(() => {
  window.location = originalLocation;
});

describe("choisirClasse.js — lien direct vers une classe", () => {
  it("visiteur sans compte : crée une session invité, présélectionne la classe et ouvre les questions", async () => {
    mockApi.me.mockRejectedValue(Object.assign(new Error("401"), { status: 401 }));
    localStorage.setItem("novamath:class_level", "seconde");
    await openWith("?classe=troisieme");
    expect(mockApi.enterGuest).toHaveBeenCalledTimes(1);
    expect(replace).toHaveBeenCalledWith("/chapitres.html");
    const { getStoredClassLevel } = await import("../curriculumSelector.js");
    expect(getStoredClassLevel()).toBe("troisieme");
    // survit au rechargement de l'onglet (modules rechargés, sessionStorage conservé)
    vi.resetModules();
    expect((await import("../curriculumSelector.js")).getStoredClassLevel()).toBe("troisieme");
    // la préférence persistante n'est pas modifiée
    expect(localStorage.getItem("novamath:class_level")).toBe("seconde");
  });

  it("utilisateur connecté : aucune session invité, préférence du profil intacte", async () => {
    mockApi.me.mockResolvedValue({ user: { id: 7, is_guest: false } });
    localStorage.setItem("novamath:class_level", "premiere");
    await openWith("?classe=quatrieme");
    expect(mockApi.enterGuest).not.toHaveBeenCalled();
    expect(replace).toHaveBeenCalledWith("/chapitres.html");
    expect(localStorage.getItem("novamath:class_level")).toBe("premiere");
    expect((await import("../curriculumSelector.js")).getStoredClassLevel()).toBe("quatrieme");
  });

  it("un choix explicite de classe efface la classe de session", async () => {
    sessionStorage.setItem("novamath:class_level_session", "troisieme");
    const { getStoredClassLevel, setStoredClassLevel } = await import("../curriculumSelector.js");
    setStoredClassLevel("seconde");
    expect(getStoredClassLevel()).toBe("seconde");
    expect(sessionStorage.getItem("novamath:class_level_session")).toBeNull();
  });

  it("classe inconnue : aucun compte créé, aucune redirection (sélecteur habituel)", async () => {
    mockApi.me.mockRejectedValue(new Error("401"));
    await openWith("?classe=terminale");
    expect(mockApi.enterGuest).not.toHaveBeenCalled();
    expect(replace).not.toHaveBeenCalled();
  });

  it("échec de création de l'invité : retombe sur le sélecteur, sans changer la classe", async () => {
    mockApi.me.mockRejectedValue(new Error("401"));
    mockApi.enterGuest.mockRejectedValue(new Error("réseau"));
    await openWith("?classe=seconde");
    expect(replace).not.toHaveBeenCalled();
    expect(sessionStorage.getItem("novamath:class_level_session")).toBeNull();
  });
});
