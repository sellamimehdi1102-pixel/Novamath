// ── customExercise.js : génération d'exercices sur mesure (Ultra) ──────────
// Chantier "Différenciateurs Premium/Ultra" (2026-08-27). Module autonome,
// aucune dépendance sur exercice.js (non importé ici) — vérifie
// exclusivement le gating par Feature.custom_exercises et le flux
// génération -> affichage -> correction différée.
import { describe, it, expect, vi, beforeEach } from "vitest";
import { loadPageBody, flushPromises } from "./testUtils.js";

// Pas d'import statique de curriculumSelector.js ici : il importe api.js
// réellement (getCurricula), ce qui exécuterait la factory vi.mock("../api.js"
// ci-dessous AVANT l'initialisation de `mockApi` (déclaré plus bas dans ce
// fichier) — voir curriculumSelector.js::CLASS_LEVEL_KEY, dupliqué en
// littéral ici pour cette seule raison technique.
const CLASS_LEVEL_KEY = "novamath:class_level";

vi.mock("../icons.js", () => ({ icon: () => "" }));

const mockApi = {
  me: vi.fn(),
  practiceGenerateOptions: vi.fn(),
  practiceGenerate: vi.fn(),
};
vi.mock("../api.js", () => ({ api: mockApi }));

function user(overrides = {}) {
  return { id: 1, plan: "free", features: undefined, ...overrides };
}

function notionsFixture() {
  return [
    {
      class_level: "seconde", chapter_id: "Chapitre_6", notion: "Droites",
      families: [{ family_id: "fam_a", label: "Type A", level: 1 }, { family_id: "fam_b", label: "Type B", level: 2 }],
    },
    {
      class_level: "premiere", chapter_id: "Chapitre_2", notion: "Second degré",
      families: [{ family_id: "fam_c", label: "Type C", level: 1 }],
    },
  ];
}

function exerciseFixture(overrides = {}) {
  return {
    id: "generated:fam_a:abc123", chapter_id: "Chapitre_6", notion: "Droites",
    difficulty: 1, difficulty_label: "Facile", difficulty_emoji: "🟢",
    enonce: "Calculer $2+2$.", answer: "$4$", hint: "Additionne.",
    solution_steps: ["Étape 1 — on additionne."], source: "generated",
    ...overrides,
  };
}

async function mount({ planUser = {}, notions = notionsFixture(), classLevel = "seconde", optionsRejects = false } = {}) {
  localStorage.setItem(CLASS_LEVEL_KEY, classLevel);
  document.body.innerHTML = loadPageBody("exercice.html");
  mockApi.me.mockReset().mockResolvedValue({ user: user(planUser) });
  mockApi.practiceGenerateOptions.mockReset();
  if (optionsRejects) {
    mockApi.practiceGenerateOptions.mockRejectedValueOnce(new Error("réseau"));
  } else {
    mockApi.practiceGenerateOptions.mockResolvedValueOnce({ notions });
  }
  mockApi.practiceGenerate.mockReset().mockResolvedValue({ exercise: exerciseFixture() });
  vi.resetModules();
  await import("../customExercise.js");
  await flushPromises();
  await flushPromises();
}

describe("customExercise.js — gating par plan", () => {
  it("Free : carte verrouillée, aucun sélecteur", async () => {
    await mount({ planUser: { plan: "free" } });
    expect(document.querySelector(".dashboard-locked-card")).not.toBeNull();
    expect(document.getElementById("custom-ex-generate")).toBeNull();
  });

  it("Premium : carte verrouillée également (Ultra seul)", async () => {
    await mount({ planUser: { plan: "premium" } });
    expect(document.querySelector(".dashboard-locked-card")).not.toBeNull();
  });

  it("Ultra : sélecteur visible, pas de verrou", async () => {
    await mount({ planUser: { plan: "ultra" } });
    expect(document.querySelector(".dashboard-locked-card")).toBeNull();
    expect(document.getElementById("custom-ex-generate")).not.toBeNull();
  });

  it("respecte user.features quand présent (mode test Owner déjà résolu côté backend)", async () => {
    await mount({ planUser: { plan: "free", features: { custom_exercises: true } } });
    expect(document.querySelector(".dashboard-locked-card")).toBeNull();
  });
});

describe("customExercise.js — sélection et génération", () => {
  it("ne propose que les notions de la classe active (seconde)", async () => {
    await mount({ planUser: { plan: "ultra" }, classLevel: "seconde" });
    const options = document.querySelectorAll("#custom-ex-notion option");
    expect(options.length).toBe(1);
    expect(options[0].textContent).toContain("Droites");
  });

  it("aucune notion pour la classe active -> message, pas de sélecteur", async () => {
    await mount({ planUser: { plan: "ultra" }, notions: [notionsFixture()[1]], classLevel: "seconde" });
    expect(document.getElementById("custom-ex-notion")).toBeNull();
    expect(document.getElementById("custom-exercise-body").textContent).toMatch(/Aucune génération disponible/);
  });

  it("le sélecteur de famille se remplit avec les familles de la notion choisie", async () => {
    await mount({ planUser: { plan: "ultra" } });
    const familyOptions = document.querySelectorAll("#custom-ex-family option");
    expect(familyOptions.length).toBe(2);
    expect(familyOptions[0].value).toBe("fam_a");
  });

  it("cliquer sur Générer appelle api.practiceGenerate avec les bons paramètres", async () => {
    await mount({ planUser: { plan: "ultra" }, classLevel: "seconde" });
    document.getElementById("custom-ex-generate").click();
    await flushPromises();
    expect(mockApi.practiceGenerate).toHaveBeenCalledWith({
      classLevel: "seconde", chapterId: "Chapitre_6", notion: "Droites", familyId: "fam_a",
    });
  });

  it("affiche l'énoncé de l'exercice généré", async () => {
    await mount({ planUser: { plan: "ultra" } });
    document.getElementById("custom-ex-generate").click();
    await flushPromises();
    expect(document.getElementById("custom-ex-enonce").textContent).toContain("2");
  });

  it("la correction reste masquée tant qu'on ne clique pas sur 'Voir la correction'", async () => {
    await mount({ planUser: { plan: "ultra" } });
    document.getElementById("custom-ex-generate").click();
    await flushPromises();
    expect(document.getElementById("custom-ex-correction").hidden).toBe(true);
  });

  it("cliquer sur 'Voir la correction' révèle la réponse et les étapes", async () => {
    await mount({ planUser: { plan: "ultra" } });
    document.getElementById("custom-ex-generate").click();
    await flushPromises();
    document.getElementById("custom-ex-toggle-correction").click();
    const box = document.getElementById("custom-ex-correction");
    expect(box.hidden).toBe(false);
    expect(box.textContent).toContain("4");
    expect(box.textContent).toContain("Étape 1");
  });

  it("échec de la génération : message d'erreur, aucune exception", async () => {
    await mount({ planUser: { plan: "ultra" } });
    mockApi.practiceGenerate.mockRejectedValueOnce(new Error("réseau"));
    document.getElementById("custom-ex-generate").click();
    await flushPromises();
    expect(document.getElementById("custom-ex-result").textContent).toMatch(/Impossible de générer/);
  });

  it("échec du chargement des options : message d'invitation, aucune exception", async () => {
    await mount({ planUser: { plan: "ultra" }, optionsRejects: true });
    expect(document.getElementById("custom-exercise-body").textContent).toMatch(/Aucune génération disponible/);
  });
});
