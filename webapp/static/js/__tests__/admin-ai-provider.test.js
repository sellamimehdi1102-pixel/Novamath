// ── admin-ai-provider.js : fiche détaillée d'un fournisseur IA (/admin/ia/:id)
// 3 onglets (Informations fusionne les anciens Informations générales +
// Configuration), CHACUN chargé par sa propre API, uniquement à l'ouverture
// (lazy loading) — ce fichier prouve : le lazy loading réel, le cache par
// onglet, le skeleton, l'état vide, la gestion d'erreur/404, et l'absence de
// données fabriquées (contrat {available, value, reason}).
import { describe, it, expect, vi, afterEach } from "vitest";
import { loadPageBody, flushPromises } from "./testUtils.js";
import { loadAiProviderDetail } from "../admin-ai-provider.js";

const INFO_PAYLOAD = {
  id: 7, name: "Gemini Flash", provider_key: "gemini", model_name: "gemini-3-flash-preview",
  enabled: true, priority: 0,
  badge: { available: true, value: "Rapide" },
  icon: { available: true, value: "zap" },
  color: { available: true, value: "#22C55E" },
  description: { available: true, value: "Modèle rapide." },
  fallback_provider: { available: false, value: null, reason: "Aucun fournisseur de secours configuré pour celui-ci." },
  created_at: { available: true, value: "2026-01-01T08:00:00+00:00" },
  updated_at: { available: true, value: "2026-01-01T08:00:00+00:00" },
};

const HEALTH_UNAVAILABLE = { available: false, value: null, reason: "Ce fournisseur n'a jamais été testé (aucun health-check n'a encore été exécuté)." };
const USAGE_UNAVAILABLE = { available: false, value: null, reason: "Aucun appel réel n'a encore été comptabilisé pour ce fournisseur (ai_provider_usage n'est pas encore alimentée par le chatbot)." };

const CONFIG_PAYLOAD = {
  provider_key: { available: true, value: "gemini" },
  model_name: { available: true, value: "gemini-3-flash-preview" },
  priority: { available: true, value: 0 },
  fallback_provider: { available: false, value: null, reason: "Aucun fournisseur de secours configuré pour celui-ci." },
  enabled: { available: true, value: true },
  code: { available: true, value: "gemini_flash" },
  badge: { available: true, value: "Rapide" },
  description: { available: true, value: "Modèle rapide." },
  icon: { available: true, value: "zap" },
  color: { available: true, value: "#22C55E" },
};

const TAB_PAYLOADS = { info: INFO_PAYLOAD, health: HEALTH_UNAVAILABLE, usage: USAGE_UNAVAILABLE, config: CONFIG_PAYLOAD };

let fetchLog;

function mockFetch(providerId, { failTab = null, overrides = {} } = {}) {
  fetchLog = [];
  global.fetch = vi.fn((url) => {
    fetchLog.push(url);
    const match = url.match(/^\/api\/admin\/ai\/providers\/(\d+)\/(\w+)$/);
    if (!match) return Promise.resolve({ ok: false, status: 404, json: () => Promise.resolve({}) });
    const [, id, tab] = match;
    if (Number(id) !== providerId) {
      return Promise.resolve({ ok: false, status: 404, json: () => Promise.resolve({ error: "introuvable" }) });
    }
    if (tab === failTab) {
      return Promise.resolve({ ok: false, status: 500, json: () => Promise.resolve({ error: "boom" }) });
    }
    const payload = overrides[tab] || TAB_PAYLOADS[tab];
    return Promise.resolve({ ok: true, json: () => Promise.resolve(payload) });
  });
}

function mountTemplate() {
  document.body.innerHTML = loadPageBody("admin.html");
  const template = document.getElementById("admin-ai-provider-template");
  document.getElementById("admin-content-body").appendChild(template.content.cloneNode(true));
}

afterEach(() => {
  vi.restoreAllMocks();
});

describe("admin-ai-provider.js — lazy loading réel", () => {
  it("l'onglet 'Informations' fusionné appelle /info ET /config à l'ouverture (une seule fois chacun)", async () => {
    mockFetch(7);
    mountTemplate();
    await loadAiProviderDetail(7);

    expect(fetchLog).toEqual(["/api/admin/ai/providers/7/info", "/api/admin/ai/providers/7/config"]);
  });

  it("cliquer sur un autre onglet déclenche exactement UN nouvel appel", async () => {
    mockFetch(7);
    mountTemplate();
    await loadAiProviderDetail(7);

    document.querySelector('.admin-tab-btn[data-tab="usage"]').click();
    await flushPromises();

    expect(fetchLog).toEqual(["/api/admin/ai/providers/7/info", "/api/admin/ai/providers/7/config", "/api/admin/ai/providers/7/usage"]);
  });

  it("rouvrir un onglet déjà chargé ne refait AUCUN appel réseau (cache par onglet)", async () => {
    mockFetch(7);
    mountTemplate();
    await loadAiProviderDetail(7);

    document.querySelector('.admin-tab-btn[data-tab="usage"]').click();
    await flushPromises();
    document.querySelector('.admin-tab-btn[data-tab="info"]').click();
    await flushPromises();
    document.querySelector('.admin-tab-btn[data-tab="usage"]').click();
    await flushPromises();

    expect(fetchLog).toEqual(["/api/admin/ai/providers/7/info", "/api/admin/ai/providers/7/config", "/api/admin/ai/providers/7/usage"]);
  });
});

describe("admin-ai-provider.js — rendu et absence de données fabriquées", () => {
  it("affiche l'en-tête (nom/badge/statut) et les champs fusionnés de l'onglet Informations (dont 'code')", async () => {
    mockFetch(7);
    mountTemplate();
    await loadAiProviderDetail(7);

    expect(document.getElementById("admin-ai-provider-head").textContent).toContain("Gemini Flash");
    expect(document.getElementById("admin-ai-provider-head").textContent).toContain("Activé");
    const panelText = document.getElementById("admin-ai-provider-panel").textContent;
    expect(panelText).toContain("gemini-3-flash-preview");
    expect(panelText).toContain("gemini_flash");
    expect(panelText).toContain("Aucune donnée disponible");
    expect(panelText).toContain("Aucun fournisseur de secours configuré");
  });

  it("onglet État sans health-check : raison exacte, jamais un taux inventé", async () => {
    mockFetch(7);
    mountTemplate();
    await loadAiProviderDetail(7);
    document.querySelector('.admin-tab-btn[data-tab="health"]').click();
    await flushPromises();

    const panelText = document.getElementById("admin-ai-provider-panel").textContent;
    expect(panelText).toContain("Ce fournisseur n'a jamais été testé");
    expect(panelText).not.toMatch(/\b0%/);
  });

  it("onglet Informations : lecture seule, aucun bouton d'action", async () => {
    mockFetch(7);
    mountTemplate();
    await loadAiProviderDetail(7);

    expect(document.getElementById("admin-ai-provider-panel").querySelector("button")).toBeNull();
  });
});

describe("admin-ai-provider.js — gestion des erreurs et 404", () => {
  it("un onglet en échec réseau affiche un message d'erreur", async () => {
    mockFetch(7, { failTab: "usage" });
    mountTemplate();
    await loadAiProviderDetail(7);
    document.querySelector('.admin-tab-btn[data-tab="usage"]').click();
    await flushPromises();

    expect(document.getElementById("admin-ai-provider-panel").textContent).toContain("Impossible de charger cet onglet");
  });

  it("fournisseur introuvable (404) affiche un message explicite", async () => {
    mockFetch(999);
    mountTemplate();
    await loadAiProviderDetail(7); // 7 !== 999 -> toutes les requêtes émulent un 404

    expect(document.getElementById("admin-ai-provider-panel").textContent).toContain("introuvable");
  });
});

describe("admin-ai-provider.js — skeleton loading", () => {
  it("affiche un skeleton pendant le chargement d'un nouvel onglet", async () => {
    let resolveFetch;
    global.fetch = vi.fn((url) => {
      if (url === "/api/admin/ai/providers/7/info") {
        return Promise.resolve({ ok: true, json: () => Promise.resolve(INFO_PAYLOAD) });
      }
      if (url === "/api/admin/ai/providers/7/config") {
        return Promise.resolve({ ok: true, json: () => Promise.resolve(CONFIG_PAYLOAD) });
      }
      return new Promise((resolve) => { resolveFetch = () => resolve({ ok: true, json: () => Promise.resolve(USAGE_UNAVAILABLE) }); });
    });
    mountTemplate();
    await loadAiProviderDetail(7);

    document.querySelector('.admin-tab-btn[data-tab="usage"]').click();
    await Promise.resolve();
    expect(document.querySelectorAll(".admin-tab-skeleton-row").length).toBeGreaterThan(0);

    resolveFetch();
    await flushPromises();
    expect(document.querySelectorAll(".admin-tab-skeleton-row").length).toBe(0);
  });
});

// ── Actions d'en-tête introduites dans cette phase : Modifier/Actualiser/
// Tester/Lancer un health-check — toutes en dehors de #admin-ai-provider-panel
// (l'onglet Informations reste un pur affichage, voir le test ci-dessus
// "lecture seule, aucun bouton d'action").
describe("admin-ai-provider.js — actions d'en-tête", () => {
  function mockFetchWithActions(actionHandlers = {}) {
    fetchLog = [];
    global.fetch = vi.fn((url, options = {}) => {
      fetchLog.push(url);
      const key = `${options.method || "GET"} ${url}`;
      if (actionHandlers[key]) return Promise.resolve(actionHandlers[key](options));
      const match = url.match(/^\/api\/admin\/ai\/providers\/(\d+)\/(\w+)$/);
      if (match && Number(match[1]) === 7 && TAB_PAYLOADS[match[2]]) {
        return Promise.resolve({ ok: true, json: () => Promise.resolve(TAB_PAYLOADS[match[2]]) });
      }
      if (url === "/api/admin/ai/providers") {
        return Promise.resolve({ ok: true, json: () => Promise.resolve({ providers: [], reason: null }) });
      }
      return Promise.resolve({ ok: false, status: 404, json: () => Promise.resolve({}) });
    });
  }

  it("bouton 'Tester la connexion' affiche le résultat réel renvoyé par l'API", async () => {
    mockFetchWithActions({
      "POST /api/admin/ai/providers/7/test-connection": () => ({
        ok: true, json: () => Promise.resolve({ ok: true, latency_ms: 180, model: "gemini-3-flash-preview", tokens: { prompt_tokens: 5, completion_tokens: 1 } }),
      }),
    });
    mountTemplate();
    await loadAiProviderDetail(7);

    const testBtn = [...document.getElementById("admin-ai-provider-head").querySelectorAll(".admin-btn")]
      .find((b) => b.textContent === "Tester la connexion");
    testBtn.click();
    await flushPromises();

    expect(document.getElementById("admin-ai-provider-head").textContent).toContain("180 ms");
  });

  it("bouton 'Lancer un health-check' écrit réellement (POST) et affiche le résultat", async () => {
    let called = false;
    mockFetchWithActions({
      "POST /api/admin/ai/providers/7/health-check": () => {
        called = true;
        return { ok: true, json: () => Promise.resolve({ ok: true, detail: "", latency_ms: 90 }) };
      },
    });
    mountTemplate();
    await loadAiProviderDetail(7);

    const healthBtn = [...document.getElementById("admin-ai-provider-head").querySelectorAll(".admin-btn")]
      .find((b) => b.textContent === "Lancer un health-check");
    healthBtn.click();
    await flushPromises();

    expect(called).toBe(true);
    expect(document.getElementById("admin-ai-provider-head").textContent).toContain("Health-check OK");
  });

  it("bouton 'Actualiser' revide le cache et refait un appel réseau pour l'onglet actif", async () => {
    mockFetchWithActions({});
    mountTemplate();
    await loadAiProviderDetail(7);
    fetchLog = [];

    const refreshBtn = [...document.getElementById("admin-ai-provider-head").querySelectorAll(".admin-btn")]
      .find((b) => b.textContent === "Actualiser");
    refreshBtn.click();
    await flushPromises();

    expect(fetchLog).toContain("/api/admin/ai/providers/7/info");
  });

  it("bouton 'Modifier' ouvre la modale partagée pré-remplie avec les données du fournisseur", async () => {
    mockFetchWithActions({});
    mountTemplate();
    await loadAiProviderDetail(7);

    const editBtn = [...document.getElementById("admin-ai-provider-head").querySelectorAll(".admin-btn")]
      .find((b) => b.textContent === "Modifier");
    editBtn.click();
    await flushPromises();

    const modal = document.getElementById("admin-ai-provider-modal");
    expect(modal.hidden).toBe(false);
    expect(modal.querySelector("[name=name]").value).toBe("Gemini Flash");
    expect(modal.querySelector("[name=model_name]").value).toBe("gemini-3-flash-preview");
  });
});
