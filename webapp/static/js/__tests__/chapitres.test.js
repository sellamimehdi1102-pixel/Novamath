// ── chapitres.js : sélection multiple (chapitres entiers + notions isolées,
// tous chapitres confondus) fusionnée en une seule série — voir
// chapitres.js::selectedNotions/chapterSelectionState/updateSelectionBar/
// launchMergedSeries. Restaure l'ancienne UX de sélection de chapitre (bouton
// à 3 états + barre flottante), sans réintroduire le test de placement
// (aucune dépendance à evaluation.html/lumis:selected_chapters).
import { describe, it, expect, vi, beforeEach } from "vitest";
import { loadPageBody, flushPromises } from "./testUtils.js";

const mockApi = { chapters: vi.fn(), me: vi.fn() };
vi.mock("../api.js", () => ({ api: mockApi }));
vi.mock("../settingsManager.js", () => ({ initSettingsManager: () => Promise.resolve() }));
vi.mock("../settingsPopup.js", () => ({ bindSettingsButton: vi.fn() }));
vi.mock("../i18n.js", () => ({ bindLiveTranslations: vi.fn() }));
vi.mock("../resume.js", () => ({ renderResumeCard: vi.fn() }));
vi.mock("../curriculumSelector.js", () => ({ getStoredClassLevel: () => "seconde" }));
vi.mock("../chapterTitleByNotions.js", () => ({ resolveChapterTitle: (title) => title }));
vi.mock("../favorites.js", () => ({
  getFavoriteChapters: () => new Set(),
  toggleFavoriteChapter: vi.fn(),
  favoriteIconSvg: () => "",
}));
// `mock` prefix requis par Vitest pour être référencée depuis la factory
// vi.mock ci-dessous (hoisting) — voir mockApi plus haut pour le même besoin.
const mockScopedStats = vi.fn(() => ({ history: [] }));
vi.mock("../store.js", () => ({
  getState: () => ({}),
  scopedStats: (...args) => mockScopedStats(...args),
  coverageByChapter: () => ({}),
  coverageByNotion: () => ({}),
  masteryByChapter: () => ({}),
  masteryByNotion: () => ({}),
  getInProgressSeries: () => null,
  getChapterStatus: () => "todo",
  MASTERY_ACCURACY_THRESHOLD: 0.70,
  MASTERY_MIN_ATTEMPTS: 10,
}));

function makeChapter(id, notionLabels) {
  return {
    id,
    title: id.replace("_", " "),
    notions_cours: [],
    n_exercises: notionLabels.length * 10,
    n_notions: notionLabels.length,
    difficulty_dominant: 1,
    notions_detail: notionLabels.map((label, i) => ({
      notion: label,
      difficulty_dominant: 1,
      difficulties_available: [1],
      n_natural_variants: 0,
      n_exercises: 10,
      exercise_ids: Array.from({ length: 10 }, (_, k) => id.charCodeAt(id.length - 1) * 1000 + i * 10 + k),
    })),
  };
}

const CHAPTERS = [
  makeChapter("Chapitre_1", ["Notion A", "Notion B"]),
  makeChapter("Chapitre_2", ["Notion C", "Notion D", "Notion E"]),
];

function defaultMocks() {
  mockApi.chapters.mockReset();
  mockApi.me.mockReset();
  mockScopedStats.mockReset();
  mockApi.chapters.mockResolvedValue({ chapters_meta: CHAPTERS });
  mockApi.me.mockResolvedValue({ user: { is_guest: false } });
  mockScopedStats.mockReturnValue({ history: [] });
}

// `overrides` (optionnel) : appelé APRÈS defaultMocks() mais AVANT l'import
// du module, pour personnaliser un mock (ex: mockApi.me, mockScopedStats)
// sans qu'il soit écrasé par les valeurs par défaut — nécessaire pour les
// tests d'accueil invité ci-dessous (Phase 5), qui doivent contrôler
// is_guest/history AVANT que le Promise.all() top-level de chapitres.js ne
// s'exécute.
async function mountChapitres(overrides) {
  document.body.innerHTML = loadPageBody("chapitres.html");
  defaultMocks();
  if (overrides) overrides();
  vi.resetModules();
  await import("../chapitres.js");
  await flushPromises();
  await flushPromises();
}

const $ = (sel) => document.querySelector(sel);
const $all = (sel) => [...document.querySelectorAll(sel)];

describe("chapitres.js — sélection d'un chapitre entier (bouton chapitre)", () => {
  beforeEach(async () => {
    await mountChapitres();
  });

  it("sélectionne toutes les notions du chapitre et passe le bouton à l'état 'full'", () => {
    const card = $all(".chapter-card")[0];
    card.querySelector(".chapter-select-btn").click();

    expect(card.querySelector(".chapter-select-btn").dataset.state).toBe("full");
    expect(card.querySelectorAll(".notion-row--selectable:not(.selected)").length).toBe(0);
    expect(card.querySelector(".notions-start-btn").disabled).toBe(false);
  });

  it("désélectionne tout le chapitre si on reclique alors qu'il est déjà 'full'", () => {
    const card = $all(".chapter-card")[0];
    const btn = card.querySelector(".chapter-select-btn");
    btn.click();
    btn.click();

    expect(btn.dataset.state).toBe("empty");
    expect(card.querySelectorAll(".notion-row.selected").length).toBe(0);
    expect(card.querySelector(".notions-start-btn").disabled).toBe(true);
  });
});

describe("chapitres.js — synchronisation bidirectionnelle chapitre <-> notions", () => {
  let card;
  beforeEach(async () => {
    await mountChapitres();
    card = $all(".chapter-card")[0]; // Chapitre_1 : Notion A, Notion B
  });

  it("CAS 1 — sélectionner le chapitre coche toutes ses notions", () => {
    card.querySelector(".chapter-select-btn").click();
    expect(card.querySelectorAll(".notion-row--selectable.selected").length).toBe(2);
  });

  it("CAS 2 — décocher une seule notion rend le chapitre 'partial'", () => {
    card.querySelector(".chapter-select-btn").click(); // full
    card.querySelectorAll(".notion-row--selectable")[0].click(); // décoche 1/2

    expect(card.querySelector(".chapter-select-btn").dataset.state).toBe("partial");
  });

  it("CAS 3 — recocher la dernière notion manquante rend le chapitre 'full'", () => {
    const rows = card.querySelectorAll(".notion-row--selectable");
    rows[0].click(); // 1/2 -> partial
    expect(card.querySelector(".chapter-select-btn").dataset.state).toBe("partial");

    rows[1].click(); // 2/2 -> full
    expect(card.querySelector(".chapter-select-btn").dataset.state).toBe("full");
  });

  it("aucun état incohérent : 0 notion cochée => toujours 'empty'", () => {
    const rows = card.querySelectorAll(".notion-row--selectable");
    rows[0].click();
    rows[0].click(); // recoche/décoche -> retour à 0
    expect(card.querySelector(".chapter-select-btn").dataset.state).toBe("empty");
  });
});

describe("chapitres.js — sélection multiple à travers plusieurs chapitres + barre flottante", () => {
  beforeEach(async () => {
    await mountChapitres();
  });

  it("mélange un chapitre entier et une notion isolée d'un autre chapitre dans la barre flottante", () => {
    const [card1, card2] = $all(".chapter-card");
    card1.querySelector(".chapter-select-btn").click(); // Chapitre_1 entier (2 notions)
    card2.querySelectorAll(".notion-row--selectable")[0].click(); // 1 notion de Chapitre_2

    const bar = $("#series-selection-bar");
    expect(bar.classList.contains("visible")).toBe(true);
    expect($("#series-selection-chapters").textContent).toBe("1"); // seul Chapitre_1 est "full"
    expect($("#series-selection-notions").textContent).toBe("3"); // 2 + 1
  });

  it("calcule le nombre total d'exercices sans doublon", () => {
    const [card1] = $all(".chapter-card");
    card1.querySelector(".chapter-select-btn").click();
    // Chapitre_1 : 2 notions x 10 exercices, ids distincts par construction du fixture.
    expect($("#series-selection-exercises").textContent).toBe("20");
  });

  it("le clic sur 'Lancer la série' construit lumis:pending_series et redirige vers exercice.html", async () => {
    const [card1, card2] = $all(".chapter-card");
    card1.querySelector(".chapter-select-btn").click();
    card2.querySelectorAll(".notion-row--selectable")[0].click();

    await import("./testUtils.js").then(({ withMockedLocation }) =>
      withMockedLocation(async () => {
        document.getElementById("series-selection-launch").click();
        await flushPromises();

        const raw = localStorage.getItem("lumis:pending_series");
        expect(raw).not.toBeNull();
        const payload = JSON.parse(raw);
        expect(payload.mode).toBe("notion");
        expect(payload.exerciseIds.length).toBe(30); // 20 (chapitre 1 entier) + 10 (1 notion chapitre 2)
        expect(new Set(payload.exerciseIds).size).toBe(30); // pas de doublon
        expect(window.location.href).toBe("exercice.html");
      })
    );
  });
});

describe("chapitres.js — accueil éditorial invité (Phase 5, onboarding)", () => {
  const $subtitle = () => document.getElementById("chapters-page-subtitle");

  it("invité sans historique : le sous-titre invite à commencer la première série", async () => {
    await mountChapitres(() => {
      mockApi.me.mockResolvedValue({ user: { is_guest: true } });
      mockScopedStats.mockReturnValue({ history: [] });
    });
    expect($subtitle().textContent).toBe("Choisis un chapitre ci-dessous pour commencer ta toute première série d'exercices.");
  });

  it("invité avec un historique déjà pertinent : le sous-titre par défaut est conservé", async () => {
    await mountChapitres(() => {
      mockApi.me.mockResolvedValue({ user: { is_guest: true } });
      mockScopedStats.mockReturnValue({ history: [{ chapter: "Chapitre_1", notion: "Notion A", correct: true }] });
    });
    expect($subtitle().textContent).toBe("Choisis les chapitres à évaluer, ou explore ta progression par notion.");
  });

  it("compte réel sans historique : le sous-titre par défaut est conservé (pas de message invité)", async () => {
    await mountChapitres(() => {
      mockApi.me.mockResolvedValue({ user: { is_guest: false } });
      mockScopedStats.mockReturnValue({ history: [] });
    });
    expect($subtitle().textContent).toBe("Choisis les chapitres à évaluer, ou explore ta progression par notion.");
  });
});
