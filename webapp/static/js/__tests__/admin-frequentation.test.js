// admin-frequentation.js : module "Fréquentation" (/admin/frequentation,
// Phase 2 Cloudflare, finalisé après introspection du schéma — 2026-10-21 ;
// état vide groupé + champ `status` discriminant — 2026-10-22).
// Prouve : le sélecteur de période est peuplé depuis /filters (jamais
// deviné côté client), les 3 appels overview/charts/rankings sont bien
// déclenchés avec la fenêtre sélectionnée, le contrat {available, value,
// reason, status} est respecté à l'affichage (jamais de donnée fabriquée),
// la note de définition "visites" (jamais confondue avec des visiteurs
// uniques) est toujours affichée, la note d'échantillonnage au-delà de 7
// jours s'affiche, les périodes sans trafic sont distinguées d'une erreur,
// le changement de période relance bien les 3 appels, la gestion d'erreur
// réseau, l'état de chargement (skeleton), et les 3 cas de l'état vide
// groupé (non configuré / erreur API / zéro réel confirmé) qui remplace les
// 3 sections détaillées par UNE SEULE carte compacte.
import { describe, it, expect, vi, afterEach } from "vitest";
import { loadPageBody } from "./testUtils.js";
import { loadFrequentation } from "../admin-frequentation.js";

const FILTERS_PAYLOAD = {
  windows: [
    { value: "7j", label: "7 jours" },
    { value: "30j", label: "30 jours" },
    { value: "90j", label: "90 jours" },
  ],
  default: "30j",
};

const NA = (reason, status) => ({ available: false, value: null, reason, status });
const VISITS_NOTE = "Mesure interne Cloudflare (RUM) — ne correspond pas à un nombre de visiteurs uniques identifiés.";
const NOT_CONFIGURED_REASON = "Intégration Cloudflare Web Analytics non configurée.";
const API_ERROR_REASON = "Délai d'attente dépassé en interrogeant l'API Cloudflare.";

// mode: "not_configured" (défaut) | "api_error" | "zero_real" | "data"
function overviewPayload(window_, { mode = "not_configured", samplingNote = null } = {}) {
  if (mode === "not_configured") {
    return {
      window: window_,
      pageviews: NA(NOT_CONFIGURED_REASON, "not_configured"),
      pageviews_previous_period: NA(NOT_CONFIGURED_REASON, "not_configured"),
      visits: NA(NOT_CONFIGURED_REASON, "not_configured"),
      visits_previous_period: NA(NOT_CONFIGURED_REASON, "not_configured"),
      sampling_note: samplingNote,
    };
  }
  if (mode === "api_error") {
    return {
      window: window_,
      pageviews: NA(API_ERROR_REASON, "api_error"),
      pageviews_previous_period: NA(API_ERROR_REASON, "api_error"),
      visits: NA(API_ERROR_REASON, "api_error"),
      visits_previous_period: NA(API_ERROR_REASON, "api_error"),
      sampling_note: samplingNote,
    };
  }
  if (mode === "zero_real") {
    return {
      window: window_,
      pageviews: { available: true, value: 0, status: "ok" },
      pageviews_previous_period: { available: true, value: 0, status: "ok", note: "Période précédente." },
      visits: { available: true, value: 0, status: "ok", note: VISITS_NOTE },
      visits_previous_period: { available: true, value: 0, status: "ok", note: `Période précédente. ${VISITS_NOTE}` },
      sampling_note: samplingNote,
    };
  }
  return {
    window: window_,
    pageviews: { available: true, value: 1234, status: "ok" },
    pageviews_previous_period: {
      available: true,
      value: 980,
      status: "ok",
      note: "Période précédente de même durée, pour comparaison.",
    },
    visits: { available: true, value: 500, status: "ok", note: VISITS_NOTE },
    visits_previous_period: {
      available: true,
      value: 420,
      status: "ok",
      note: `Période précédente de même durée, pour comparaison. ${VISITS_NOTE}`,
    },
    sampling_note: samplingNote,
  };
}

function chartsPayload(window_, { mode = "not_configured", days = null, samplingNote = null } = {}) {
  if (mode === "data") {
    return {
      window: window_,
      daily: {
        available: true,
        status: "ok",
        value: days !== null ? days : [{ date: "2026-10-14", pageviews: 10, visits: 4 }],
      },
      sampling_note: samplingNote,
    };
  }
  if (mode === "zero_real") {
    return {
      window: window_,
      daily: { available: true, status: "ok", value: [], note: "Aucune donnée." },
      sampling_note: samplingNote,
    };
  }
  if (mode === "api_error") {
    return { window: window_, daily: NA(API_ERROR_REASON, "api_error"), sampling_note: samplingNote };
  }
  return { window: window_, daily: NA(NOT_CONFIGURED_REASON, "not_configured"), sampling_note: samplingNote };
}

function rankingsPayload(window_, { mode = "not_configured" } = {}) {
  if (mode === "data") {
    return {
      window: window_,
      top_pages: { available: true, status: "ok", value: [{ label: "/cours", pageviews: 100, visits: 40 }] },
      top_countries: { available: true, status: "ok", value: [{ label: "FR", pageviews: 150, visits: 60 }] },
      top_referrers: { available: true, status: "ok", value: [{ label: "google.com", pageviews: 50, visits: 20 }] },
      top_browsers: { available: true, status: "ok", value: [{ label: "Chrome", pageviews: 120, visits: 50 }] },
      top_devices: { available: true, status: "ok", value: [{ label: "desktop", pageviews: 140, visits: 55 }] },
    };
  }
  if (mode === "zero_real") {
    const emptyOk = { available: true, status: "ok", value: [], note: "Aucune donnée." };
    return {
      window: window_,
      top_pages: emptyOk,
      top_countries: emptyOk,
      top_referrers: emptyOk,
      top_browsers: emptyOk,
      top_devices: emptyOk,
    };
  }
  const status = mode === "api_error" ? "api_error" : "not_configured";
  const reason = mode === "api_error" ? API_ERROR_REASON : NOT_CONFIGURED_REASON;
  return {
    window: window_,
    top_pages: NA(reason, status),
    top_countries: NA(reason, status),
    top_referrers: NA(reason, status),
    top_browsers: NA(reason, status),
    top_devices: NA(reason, status),
  };
}

let fetchLog;

function mockFetch({ mode = "not_configured", days = null, samplingNote = null, failAll = false } = {}) {
  fetchLog = [];
  global.fetch = vi.fn((url) => {
    fetchLog.push(url);
    if (failAll) return Promise.resolve({ ok: false, status: 500, json: () => Promise.resolve({ error: "boom" }) });
    if (url === "/api/admin/frequentation/filters") {
      return Promise.resolve({ ok: true, json: () => Promise.resolve(FILTERS_PAYLOAD) });
    }
    const match = url.match(/^\/api\/admin\/frequentation\/(overview|charts|rankings)\?window=([^&]+)$/);
    if (!match) return Promise.resolve({ ok: false, status: 404, json: () => Promise.resolve({}) });
    const [, kind, window_] = match;
    if (kind === "overview") {
      return Promise.resolve({
        ok: true,
        json: () => Promise.resolve(overviewPayload(window_, { mode, samplingNote })),
      });
    }
    if (kind === "charts") {
      return Promise.resolve({
        ok: true,
        json: () => Promise.resolve(chartsPayload(window_, { mode, days, samplingNote })),
      });
    }
    return Promise.resolve({ ok: true, json: () => Promise.resolve(rankingsPayload(window_, { mode })) });
  });
}

function mountTemplate() {
  document.body.innerHTML = loadPageBody("admin.html");
  const template = document.getElementById("admin-frequentation-template");
  document.getElementById("admin-content-body").appendChild(template.content.cloneNode(true));
}

afterEach(() => {
  vi.restoreAllMocks();
});

describe("admin-frequentation.js", () => {
  it("peuple le sélecteur de période depuis /filters, jamais deviné côté client", async () => {
    mockFetch();
    mountTemplate();
    await loadFrequentation();

    const select = document.getElementById("admin-frequentation-window-select");
    expect([...select.options].map((o) => o.value)).toEqual(["7j", "30j", "90j"]);
    expect(select.value).toBe("30j");
  });

  it("déclenche overview/charts/rankings avec la fenêtre par défaut", async () => {
    mockFetch();
    mountTemplate();
    await loadFrequentation();

    expect(fetchLog).toContain("/api/admin/frequentation/overview?window=30j");
    expect(fetchLog).toContain("/api/admin/frequentation/charts?window=30j");
    expect(fetchLog).toContain("/api/admin/frequentation/rankings?window=30j");
  });

  // ── État vide groupé : les 3 cas ────────────────────────────────────────
  it("état vide — non configuré : une seule carte compacte, lien vers .env.example, pas de bouton Réessayer", async () => {
    mockFetch({ mode: "not_configured" });
    mountTemplate();
    await loadFrequentation();

    const detail = document.getElementById("admin-frequentation-detail");
    const emptyState = document.getElementById("admin-frequentation-empty-state");
    expect(detail.hidden).toBe(true);
    expect(emptyState.hidden).toBe(false);
    expect(emptyState.textContent).toContain(".env.example");
    const retryBtn = document.getElementById("admin-frequentation-empty-state-retry");
    expect(retryBtn.hidden).toBe(true);
  });

  it("état vide — erreur API : message avec la raison réelle et un bouton Réessayer qui relance refresh()", async () => {
    mockFetch({ mode: "api_error" });
    mountTemplate();
    await loadFrequentation();

    const emptyState = document.getElementById("admin-frequentation-empty-state");
    expect(emptyState.hidden).toBe(false);
    expect(emptyState.textContent).toContain(API_ERROR_REASON);
    const retryBtn = document.getElementById("admin-frequentation-empty-state-retry");
    expect(retryBtn.hidden).toBe(false);

    // Réessayer avec des données disponibles : revient à l'affichage détaillé.
    mockFetch({ mode: "data" });
    retryBtn.click();
    await new Promise((resolve) => setTimeout(resolve, 0));
    expect(document.getElementById("admin-frequentation-detail").hidden).toBe(false);
    expect(document.getElementById("admin-frequentation-empty-state").hidden).toBe(true);
  });

  it("état vide — zéro réel confirmé : message rassurant, pas de bouton Réessayer, jamais confondu avec une erreur", async () => {
    mockFetch({ mode: "zero_real" });
    mountTemplate();
    await loadFrequentation();

    const emptyState = document.getElementById("admin-frequentation-empty-state");
    expect(emptyState.hidden).toBe(false);
    expect(emptyState.textContent).toContain("Aucune visite enregistrée");
    expect(emptyState.textContent).toContain("fonctionne normalement");
    const retryBtn = document.getElementById("admin-frequentation-empty-state-retry");
    expect(retryBtn.hidden).toBe(true);
  });

  it("dès qu'une métrique a une vraie donnée, l'affichage détaillé revient (pas l'état vide groupé)", async () => {
    mockFetch({ mode: "data" });
    mountTemplate();
    await loadFrequentation();

    expect(document.getElementById("admin-frequentation-detail").hidden).toBe(false);
    expect(document.getElementById("admin-frequentation-empty-state").hidden).toBe(true);
  });

  it("affiche un skeleton de chargement avant que les réponses arrivent", async () => {
    mountTemplate();
    fetchLog = [];
    let resolveOverview;
    global.fetch = vi.fn((url) => {
      fetchLog.push(url);
      if (url === "/api/admin/frequentation/filters") {
        return Promise.resolve({ ok: true, json: () => Promise.resolve(FILTERS_PAYLOAD) });
      }
      if (url.startsWith("/api/admin/frequentation/overview")) {
        return new Promise((resolve) => {
          resolveOverview = () =>
            resolve({ ok: true, json: () => Promise.resolve(overviewPayload("30j", { mode: "data" })) });
        });
      }
      if (url.startsWith("/api/admin/frequentation/charts")) {
        return Promise.resolve({ ok: true, json: () => Promise.resolve(chartsPayload("30j", { mode: "data" })) });
      }
      return Promise.resolve({ ok: true, json: () => Promise.resolve(rankingsPayload("30j", { mode: "data" })) });
    });

    const loadPromise = loadFrequentation();
    // Laisse le temps à /filters de se résoudre et à refresh() de démarrer
    // (rendu du skeleton) avant que /overview ne réponde.
    await new Promise((resolve) => setTimeout(resolve, 0));
    await new Promise((resolve) => setTimeout(resolve, 0));
    const cards = document.getElementById("admin-frequentation-overview-cards");
    expect(cards.querySelector(".admin-skeleton")).not.toBeNull();

    resolveOverview();
    await loadPromise;
    expect(cards.querySelector(".admin-skeleton")).toBeNull();
  });

  it("affiche les vraies valeurs de visites et pages vues avec comparaison à la période précédente", async () => {
    mockFetch({ mode: "data" });
    mountTemplate();
    await loadFrequentation();

    const cards = document.getElementById("admin-frequentation-overview-cards");
    expect(cards.textContent).toContain("500"); // visites
    expect(cards.textContent).toContain((1234).toLocaleString("fr-FR")); // pages vues
    expect(cards.textContent).toContain("Période précédente : 420"); // visites précédentes
    expect(cards.textContent).toContain("Période précédente : 980"); // pages vues précédentes
  });

  it("affiche toujours la définition de 'visites' — jamais confondue avec des visiteurs uniques", async () => {
    mockFetch({ mode: "data" });
    mountTemplate();
    await loadFrequentation();

    const cards = document.getElementById("admin-frequentation-overview-cards");
    expect(cards.textContent).toContain("ne correspond pas à un nombre de visiteurs uniques identifiés");
  });

  it("affiche la note d'échantillonnage au-delà de 7 jours", async () => {
    mockFetch({ mode: "data", samplingNote: "Fenêtre au-delà de 7 jours : échantillonnage." });
    mountTemplate();
    await loadFrequentation();

    const note = document.getElementById("admin-frequentation-sampling-note");
    expect(note.hidden).toBe(false);
    expect(note.textContent).toContain("échantillonnage");
  });

  it("n'affiche aucune note d'échantillonnage pour la fenêtre 7 jours", async () => {
    mockFetch({ mode: "data", samplingNote: null });
    mountTemplate();
    await loadFrequentation();

    const note = document.getElementById("admin-frequentation-sampling-note");
    expect(note.hidden).toBe(true);
  });

  it("distingue, dans un sous-bloc, une période réellement sans trafic (liste vide) d'une erreur — sans réserver les 240px fixes", async () => {
    // Overview/rankings avec données (pour sortir de l'état vide groupé), charts vide.
    mockFetch({ mode: "data", days: [] });
    mountTemplate();
    await loadFrequentation();

    const box = document.getElementById("admin-frequentation-evolution-chart");
    expect(box.querySelector("canvas")).toBeNull();
    expect(box.textContent).toContain("Aucune donnée");
    expect(box.textContent).not.toContain("Cette fonctionnalité n'est pas encore alimentée.");
    expect(box.classList.contains("admin-health-chart-box--compact")).toBe(true);
  });

  it("affiche le graphique combiné visites+pages vues quand les données sont disponibles, sans la classe compacte", async () => {
    mockFetch({
      mode: "data",
      days: [
        { date: "2026-10-14", pageviews: 10, visits: 4 },
        { date: "2026-10-15", pageviews: 20, visits: 8 },
      ],
    });
    mountTemplate();
    await loadFrequentation();

    const box = document.getElementById("admin-frequentation-evolution-chart");
    expect(box.querySelector("canvas")).not.toBeNull();
    expect(box.textContent).toContain("Visites et pages vues par jour");
    expect(box.classList.contains("admin-health-chart-box--compact")).toBe(false);
  });

  it("affiche les classements (pages/pays/référents/navigateurs/appareils) quand configuré", async () => {
    mockFetch({ mode: "data" });
    mountTemplate();
    await loadFrequentation();

    const rankings = document.getElementById("admin-frequentation-rankings");
    expect(rankings.textContent).toContain("/cours");
    expect(rankings.textContent).toContain("google.com");
    expect(rankings.querySelectorAll("canvas").length).toBe(3); // pays, navigateurs, appareils (camemberts)
  });

  it("le changement de période relance les 3 appels avec la nouvelle fenêtre", async () => {
    mockFetch({ mode: "data" });
    mountTemplate();
    await loadFrequentation();

    fetchLog = [];
    const select = document.getElementById("admin-frequentation-window-select");
    select.value = "7j";
    select.dispatchEvent(new Event("change"));
    await new Promise((resolve) => setTimeout(resolve, 0));

    expect(fetchLog).toContain("/api/admin/frequentation/overview?window=7j");
    expect(fetchLog).toContain("/api/admin/frequentation/charts?window=7j");
    expect(fetchLog).toContain("/api/admin/frequentation/rankings?window=7j");
  });

  it("affiche un message d'erreur explicite si les appels échouent, sans planter", async () => {
    mockFetch({ failAll: true });
    mountTemplate();
    await loadFrequentation();

    const errorEl = document.getElementById("admin-frequentation-error");
    expect(errorEl.hidden).toBe(false);
    expect(errorEl.textContent.length).toBeGreaterThan(0);
  });
});
