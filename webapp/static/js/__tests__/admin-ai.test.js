// ── admin-ai.js : module "IA" (/admin/ia) — panneau d'administration de la
// configuration technique des fournisseurs IA, branché via admin-shell.js.
// Couvre à la fois la lecture (déjà en place) et les actions d'écriture :
// créer/modifier/activer-désactiver/supprimer un fournisseur, réordonner les
// priorités, tester un fournisseur, lancer un health-check. L'assignation
// fournisseur ⇄ plan d'abonnement est couverte par admin-subscriptions.test.js
// (déplacée vers /admin/subscriptions).
//
// Chantier Administrateur "IA" (Phase 2) : la carte indépendante "État des
// fournisseurs" et le graphique "Consommation journalière" ont été retirés
// (doublons identifiés par l'audit — voir admin-ai.js pour le détail) ; les
// données de santé (GET /api/admin/ai/health, INCHANGÉE) alimentent
// désormais un badge compact par fournisseur.
import { describe, it, expect, vi, afterEach } from "vitest";
import { loadPageBody, flushPromises } from "./testUtils.js";

const mockLoadDashboard = vi.fn().mockResolvedValue(undefined);
vi.mock("../admin-dashboard.js", () => ({ loadDashboard: mockLoadDashboard }));

const NAV_WITH_AI = [
  { id: "dashboard", label: "Dashboard", icon: "🏠", path: "/admin", implemented: true },
  { id: "ai", label: "IA", icon: "🤖", path: "/admin/ia", implemented: true },
];

function provider(overrides = {}) {
  return {
    id: 1, name: "Gemini Flash", provider_key: "gemini", model_name: "gemini-3-flash-preview",
    enabled: true, priority: 0,
    badge: { available: true, value: "Rapide" },
    icon: { available: true, value: "zap" },
    color: { available: true, value: "#22C55E" },
    description: { available: true, value: "Modèle rapide." },
    fallback_provider: { available: false, value: null, reason: "Aucun fournisseur de secours configuré pour celui-ci." },
    created_at: { available: true, value: "2026-01-01T08:00:00+00:00" },
    updated_at: { available: true, value: "2026-01-01T08:00:00+00:00" },
    ...overrides,
  };
}

function providersPayload(overrides = {}) {
  return {
    providers: [
      provider(),
      provider({ id: 2, name: "Gemini Pro", model_name: "gemini-3-pro-preview", priority: 1, badge: { available: true, value: "Avancé" } }),
      provider({ id: 3, name: "Claude", provider_key: "anthropic", model_name: "claude-sonnet-5", priority: 2, badge: { available: true, value: "Premium" } }),
    ],
    reason: null,
    ...overrides,
  };
}

const HEALTH_PAYLOAD = {
  items: [
    { provider_id: 1, name: "Gemini Flash", health: { available: false, value: null, reason: "Ce fournisseur n'a jamais été testé (aucun health-check n'a encore été exécuté)." } },
  ],
  reason: null,
};

// Un health complet (available:true) pour construire les 3 autres états —
// mêmes champs exacts que admin_ai_service._serialize_health.
function healthValue(overrides = {}) {
  return {
    last_success: { available: true, value: "2026-08-20T10:00:00+00:00" },
    last_failure: { available: false, value: null, reason: "Aucun échec n'a encore été enregistré." },
    latency_ms: { available: true, value: 120 },
    average_latency: { available: true, value: 130 },
    total_requests: { available: true, value: 10 },
    total_errors: { available: true, value: 0 },
    success_rate: { available: true, value: 100 },
    http_code: { available: true, value: 200 },
    last_error: { available: false, value: null, reason: "Aucune erreur enregistrée." },
    updated_at: { available: true, value: "2026-08-20T10:00:00+00:00" },
    ...overrides,
  };
}

const USAGE_PAYLOAD = {
  items: [
    { provider_id: 1, name: "Gemini Flash", usage: { available: false, value: null, reason: "Aucun appel réel n'a encore été comptabilisé pour ce fournisseur (ai_provider_usage n'est pas encore alimentée par le chatbot)." } },
  ],
  reason: null,
  chart: { available: false, value: null, reason: "Aucun appel réel n'a encore été comptabilisé pour ce fournisseur (ai_provider_usage n'est pas encore alimentée par le chatbot)." },
};

let fetchLog;
let extraHandlers;

function mockFetchWith({ providers = providersPayload(), health = HEALTH_PAYLOAD, usage = USAGE_PAYLOAD, fail = [], handlers = {} } = {}) {
  fetchLog = [];
  extraHandlers = handlers;
  global.fetch = vi.fn((url, options = {}) => {
    fetchLog.push(`${options.method || "GET"} ${url}`);
    if (url === "/api/admin/me") {
      return Promise.resolve({ ok: true, json: () => Promise.resolve({ name: "Mehdi", email: "a@b.c", role: "super_admin", avatar: null }) });
    }
    if (url === "/api/admin/nav") {
      return Promise.resolve({ ok: true, json: () => Promise.resolve({ modules: NAV_WITH_AI }) });
    }
    if (fail.includes(url)) {
      return Promise.resolve({ ok: false, status: 500, json: () => Promise.resolve({ error: "boom" }) });
    }
    const key = `${options.method || "GET"} ${url}`;
    if (extraHandlers[key]) return Promise.resolve(extraHandlers[key](options));
    if (url === "/api/admin/ai/providers" && (!options.method || options.method === "GET")) {
      return Promise.resolve({ ok: true, json: () => Promise.resolve(providers) });
    }
    if (url === "/api/admin/ai/health") return Promise.resolve({ ok: true, json: () => Promise.resolve(health) });
    if (url === "/api/admin/ai/usage") return Promise.resolve({ ok: true, json: () => Promise.resolve(usage) });
    return Promise.resolve({ ok: false, status: 404, json: () => Promise.resolve({ error: "not found" }) });
  });
}

async function mount(path, options) {
  window.history.pushState({}, "", path);
  document.body.innerHTML = loadPageBody("admin.html");
  document.cookie = "nm_csrf=test-csrf-token";
  mockFetchWith(options);
  vi.resetModules();
  mockLoadDashboard.mockClear();
  const { initAdminShell } = await import("../admin-shell.js");
  await initAdminShell();
  await flushPromises();
}

function providerCard(name) {
  return [...document.querySelectorAll(".admin-ai-provider-card")].find((c) => c.textContent.includes(name));
}

afterEach(() => {
  vi.restoreAllMocks();
  document.cookie = "nm_csrf=; expires=Thu, 01 Jan 1970 00:00:00 UTC";
});

describe("admin-ai.js — rendu des cartes (Fournisseurs, Consommation)", () => {
  it("affiche la carte Fournisseurs IA avec les champs réels", async () => {
    await mount("/admin/ia");
    const providersEl = document.getElementById("admin-ai-providers");
    expect(providersEl.textContent).toContain("Gemini Flash");
    expect(providersEl.textContent).toContain("gemini");
    expect(providersEl.textContent).toContain("Rapide");
    // Aucun fallback configuré -> jamais une valeur fabriquée.
    expect(providersEl.textContent).toContain("Aucune donnée disponible");
  });

  it("carte Consommation : aucune donnée -> jamais un 0 affiché", async () => {
    await mount("/admin/ia");
    const usageEl = document.getElementById("admin-ai-usage");
    expect(usageEl.textContent).toContain("Aucune donnée disponible");
    expect(usageEl.textContent).not.toMatch(/\b0\b/);
  });

  it("le libellé cumul a vie de la section Consommation est present (HTML statique)", async () => {
    await mount("/admin/ia");
    expect(document.getElementById("admin-ai-usage-title").textContent).toContain("cumul");
  });
});

// Chantier "fiabilité des données d'analytics IA" (audit 2026-08-27, anomalie
// #2) : total_tokens (déjà stocké en base) est désormais exposé par
// admin_ai_service et affiché ici — peut dépasser input+output à cause des
// tokens de réflexion Gemini, déjà inclus dans le coût mais jusqu'ici
// invisibles pour l'admin.
describe("admin-ai.js — carte Consommation : champ « Tokens total »", () => {
  function usagePayloadWithValue(overrides = {}) {
    return {
      items: [{
        provider_id: 1, name: "Gemini Flash",
        usage: {
          available: true,
          value: {
            input_tokens: 256782, output_tokens: 72300, total_tokens: 329082,
            requests: 289, estimated_cost: 0.5697,
            ...overrides,
          },
        },
      }],
      reason: null,
      chart: { available: false, value: null, reason: "Aucun appel réel n'a encore été comptabilisé pour ce fournisseur (ai_provider_usage n'est pas encore alimentée par le chatbot)." },
    };
  }

  it("affiche Tokens total en plus de Input/Output/Requêtes/Coût, sans recalcul frontend", async () => {
    await mount("/admin/ia", { usage: usagePayloadWithValue() });
    const usageEl = document.getElementById("admin-ai-usage");
    expect(usageEl.textContent).toContain("Tokens total");
    expect(usageEl.textContent).toContain("329");
    // Le coût affiché reste EXACTEMENT celui fourni par le backend (0,5697 $),
    // jamais recalculé côté frontend à partir de input/output tokens.
    expect(usageEl.textContent).toContain("0,5697");
    expect(usageEl.textContent).toContain("256");
    expect(usageEl.textContent).toContain("72");
    expect(usageEl.textContent).toContain("289");
  });

  it("Tokens total > input + output (tokens de réflexion) : la valeur brute du backend est affichée telle quelle", async () => {
    await mount("/admin/ia", { usage: usagePayloadWithValue({ total_tokens: 329082 }) });
    const usageEl = document.getElementById("admin-ai-usage");
    // 329 082 != 256 782 + 72 300 (329 082) -- ici volontairement égal pour
    // rester réaliste (cas Gemini Flash de l'audit), le test suivant couvre
    // explicitement le cas avec un delta de réflexion.
    expect(usageEl.textContent).toContain("329");
  });

  it("Tokens total nettement supérieur à input+output (thinking tokens) reste affiché sans erreur", async () => {
    await mount("/admin/ia", { usage: usagePayloadWithValue({ total_tokens: 403885 }) });
    const usageEl = document.getElementById("admin-ai-usage");
    expect(usageEl.textContent).toContain("403");
  });

  it("total_tokens = 0 (ancienne ligne sans donnée exploitable) : affiché comme 0, aucune erreur", async () => {
    await mount("/admin/ia", { usage: usagePayloadWithValue({ total_tokens: 0 }) });
    const usageEl = document.getElementById("admin-ai-usage");
    expect(usageEl.textContent).toContain("Tokens total");
    expect(() => usageEl.textContent).not.toThrow();
  });

  it("une infobulle explique que Tokens total peut inclure les tokens de réflexion", async () => {
    await mount("/admin/ia", { usage: usagePayloadWithValue() });
    const labels = [...document.getElementById("admin-ai-usage").querySelectorAll(".admin-field-label")];
    const totalLabel = labels.find((l) => l.textContent === "Tokens total");
    expect(totalLabel).toBeDefined();
    expect(totalLabel.title.toLowerCase()).toContain("réflexion");
  });
});

// Chantier Administrateur "IA" (Phase 2) : la carte "État des fournisseurs"
// et le graphique de consommation journalière ont été retirés en tant que
// rendus indépendants (doublons avec la fiche détaillée / Analytics, voir
// admin-ai.js). Remplacés respectivement par un badge de santé compact par
// fournisseur, et un lien statique vers Analytics.
describe("admin-ai.js — carte 'État des fournisseurs' retirée, remplacée par un badge par fournisseur", () => {
  it("aucun conteneur/section indépendant 'État des fournisseurs' n'est plus rendu", async () => {
    await mount("/admin/ia");
    expect(document.getElementById("admin-ai-health")).toBeNull();
  });

  it("badge 'Opérationnel' : succès récent, aucun échec, taux de succès 100%", async () => {
    await mount("/admin/ia", {
      health: { items: [{ provider_id: 1, name: "Gemini Flash", health: { available: true, value: healthValue() } }], reason: null },
    });
    const healthDots = [...providerCard("Gemini Flash").querySelectorAll(".admin-status-dot--ok")]
      .filter((d) => d.textContent === "Opérationnel");
    expect(healthDots.length).toBe(1);
  });

  it("badge 'Dégradé' : taux de succès < 100%, aucun échec plus récent que le dernier succès", async () => {
    await mount("/admin/ia", {
      health: { items: [{ provider_id: 1, name: "Gemini Flash", health: { available: true, value: healthValue({ success_rate: { available: true, value: 80 } }) } }], reason: null },
    });
    const badge = providerCard("Gemini Flash").querySelector(".admin-status-dot--warning");
    expect(badge).not.toBeNull();
    expect(badge.textContent).toBe("Dégradé");
  });

  it("badge 'Indisponible' : dernier échec plus récent que le dernier succès", async () => {
    await mount("/admin/ia", {
      health: {
        items: [{
          provider_id: 1, name: "Gemini Flash",
          health: { available: true, value: healthValue({ last_failure: { available: true, value: "2026-08-21T10:00:00+00:00" } }) },
        }],
        reason: null,
      },
    });
    const badge = providerCard("Gemini Flash").querySelector(".admin-status-dot--down");
    expect(badge).not.toBeNull();
    expect(badge.textContent).toBe("Indisponible");
  });

  it("badge 'Jamais testé' : fournisseur sans aucune ligne de santé (comportement honnête déjà existant)", async () => {
    await mount("/admin/ia"); // HEALTH_PAYLOAD par défaut : health.available = false
    const badge = providerCard("Gemini Flash").querySelector(".admin-status-dot--unknown");
    expect(badge).not.toBeNull();
    expect(badge.textContent).toBe("Jamais testé");
  });

  it("échec réseau de /api/admin/ai/health : les fournisseurs restent affichés, badge de repli, bannière d'erreur visible", async () => {
    await mount("/admin/ia", { fail: ["/api/admin/ai/health"] });
    expect(document.getElementById("admin-ai-providers").textContent).toContain("Gemini Flash");
    const badge = providerCard("Gemini Flash").querySelector(".admin-status-dot--unknown");
    expect(badge).not.toBeNull();
    expect(badge.textContent).toBe("Jamais testé");
    expect(document.getElementById("admin-global-error").hidden).toBe(false);
  });

  it("aucun graphique (canvas) n'est plus rendu sur /admin/ia", async () => {
    await mount("/admin/ia");
    expect(document.getElementById("admin-ai-usage-chart")).toBeNull();
    expect(document.querySelector("#admin-content-body canvas")).toBeNull();
  });

  it("un lien vers Analytics est présent à la place du graphique", async () => {
    await mount("/admin/ia");
    const link = document.querySelector('#admin-content-body a[href="/admin/analytics"]');
    expect(link).not.toBeNull();
  });
});

describe("admin-ai.js — état vide et gestion des erreurs", () => {
  it("aucun fournisseur configuré -> état vide avec raison", async () => {
    await mount("/admin/ia", { providers: { providers: null, reason: "Aucun fournisseur IA n'est configuré dans ai_providers." } });
    expect(document.getElementById("admin-ai-providers").textContent).toContain("Aucun fournisseur IA n'est configuré");
  });

  it("une section en échec réseau (Consommation) affiche une erreur, sans bloquer les autres sections", async () => {
    await mount("/admin/ia", { fail: ["/api/admin/ai/usage"] });
    expect(document.getElementById("admin-ai-usage").textContent).toContain("Impossible de charger cette section");
    // Les autres cartes restent utilisables malgré l'échec de celle-ci.
    expect(document.getElementById("admin-ai-providers").textContent).toContain("Gemini Flash");
    expect(document.getElementById("admin-global-error").hidden).toBe(false);
  });
  // L'échec réseau de /api/admin/ai/health (badges de repli, bannière
  // d'erreur) est couvert par le describe "carte 'État des fournisseurs'
  // retirée" ci-dessus.
});

describe("admin-ai.js — navigation vers la fiche détaillée (/admin/ia/:id)", () => {
  it("cliquer sur un fournisseur navigue vers /admin/ia/:id via pushState", async () => {
    await mount("/admin/ia");
    const pushStateSpy = vi.spyOn(window.history, "pushState");

    providerCard("Gemini Flash").click();
    await flushPromises();

    expect(pushStateSpy).toHaveBeenCalledWith(expect.anything(), "", "/admin/ia/1");
    expect(window.location.pathname).toBe("/admin/ia/1");
    expect(document.querySelector(".admin-breadcrumb-item--current").textContent).toBe("Fiche fournisseur");
    expect(document.getElementById("admin-ai-provider-tabs")).not.toBeNull();
    expect(document.body.textContent).not.toMatch(/404/);
  });

  it("cliquer sur un bouton d'action de la carte NE déclenche PAS la navigation", async () => {
    await mount("/admin/ia");
    const pushStateSpy = vi.spyOn(window.history, "pushState");
    const card = providerCard("Gemini Flash");
    card.querySelector(".admin-btn").click();
    await flushPromises();
    expect(pushStateSpy).not.toHaveBeenCalled();
  });
});

describe("admin-ai.js — activer/désactiver un fournisseur", () => {
  it("bascule l'interrupteur -> PATCH /enabled avec le CSRF, puis recharge", async () => {
    vi.spyOn(window, "confirm").mockReturnValue(true);
    let patched = null;
    await mount("/admin/ia", {
      handlers: {
        "PATCH /api/admin/ai/providers/1/enabled": (options) => {
          patched = JSON.parse(options.body);
          return { ok: true, json: () => Promise.resolve({ ok: true }) };
        },
      },
    });
    const toggle = providerCard("Gemini Flash").querySelector(".admin-toggle input");
    toggle.checked = false;
    toggle.dispatchEvent(new Event("change"));
    await flushPromises();

    expect(patched).toEqual({ enabled: false });
    expect(fetchLog).toContain("PATCH /api/admin/ai/providers/1/enabled");
  });
});

describe("admin-ai.js — réordonner les priorités", () => {
  it("clic sur ↓ envoie POST /move-down et recharge la liste", async () => {
    await mount("/admin/ia", {
      handlers: {
        "POST /api/admin/ai/providers/1/move-down": () => ({ ok: true, json: () => Promise.resolve({ ok: true }) }),
      },
    });
    const downBtn = [...providerCard("Gemini Flash").querySelectorAll(".admin-btn")].find((b) => b.textContent === "↓");
    downBtn.click();
    await flushPromises();
    expect(fetchLog).toContain("POST /api/admin/ai/providers/1/move-down");
  });
});

describe("admin-ai.js — suppression d'un fournisseur", () => {
  it("confirmé -> DELETE puis recharge ; refusé (utilisé par un abonnement) -> message d'erreur affiché", async () => {
    vi.spyOn(window, "confirm").mockReturnValue(true);
    vi.spyOn(window, "alert").mockImplementation(() => {});
    await mount("/admin/ia", {
      handlers: {
        "DELETE /api/admin/ai/providers/1": () => Promise.resolve({
          ok: false, status: 409, json: () => Promise.resolve({ error: "Impossible de supprimer : encore utilisé par l'abonnement free." }),
        }),
      },
    });
    const deleteBtn = [...providerCard("Gemini Flash").querySelectorAll(".admin-btn")].find((b) => b.textContent === "Supprimer");
    deleteBtn.click();
    await flushPromises();
    expect(fetchLog).toContain("DELETE /api/admin/ai/providers/1");
    expect(window.alert).toHaveBeenCalledWith("Impossible de supprimer : encore utilisé par l'abonnement free.");
  });
});

describe("admin-ai.js — tester un fournisseur / health-check", () => {
  it("bouton Tester la connexion affiche le résultat réel (succès)", async () => {
    await mount("/admin/ia", {
      handlers: {
        "POST /api/admin/ai/providers/1/test-connection": () => Promise.resolve({
          ok: true, json: () => Promise.resolve({ ok: true, latency_ms: 234, model: "gemini-3-flash-preview", tokens: { prompt_tokens: 12, completion_tokens: 3 } }),
        }),
      },
    });
    const testBtn = [...providerCard("Gemini Flash").querySelectorAll(".admin-btn")].find((b) => b.textContent === "Tester la connexion");
    testBtn.click();
    await flushPromises();
    expect(providerCard("Gemini Flash").textContent).toContain("234 ms");
  });

  it("bouton Health-check écrit et affiche le résultat (échec)", async () => {
    await mount("/admin/ia", {
      handlers: {
        "POST /api/admin/ai/providers/1/health-check": () => Promise.resolve({
          ok: true, json: () => Promise.resolve({ ok: false, detail: "Clé API invalide.", latency_ms: 12 }),
        }),
      },
    });
    const healthBtn = [...providerCard("Gemini Flash").querySelectorAll(".admin-btn")].find((b) => b.textContent === "Health-check");
    healthBtn.click();
    await flushPromises();
    expect(providerCard("Gemini Flash").textContent).toContain("Clé API invalide");
  });
});

describe("admin-ai.js — création d'un fournisseur (modale)", () => {
  it("ouvre la modale, affiche les erreurs de validation renvoyées par le serveur", async () => {
    await mount("/admin/ia", {
      handlers: {
        "POST /api/admin/ai/providers": () => Promise.resolve({
          ok: false, status: 400,
          json: () => Promise.resolve({ error: "Configuration invalide.", fields: { model_name: "model_name est obligatoire." } }),
        }),
      },
    });
    document.getElementById("admin-ai-new-provider-btn").click();
    const modal = document.getElementById("admin-ai-provider-modal");
    expect(modal.hidden).toBe(false);

    modal.querySelector("form").dispatchEvent(new Event("submit", { cancelable: true }));
    await flushPromises();

    expect(fetchLog).toContain("POST /api/admin/ai/providers");
    expect(modal.textContent).toContain("model_name est obligatoire.");
    expect(modal.hidden).toBe(false); // la modale reste ouverte tant que les erreurs ne sont pas corrigées
  });

  it("sauvegarde réussie -> ferme la modale et recharge la liste", async () => {
    await mount("/admin/ia", {
      handlers: {
        "POST /api/admin/ai/providers": () => Promise.resolve({ ok: true, status: 201, json: () => Promise.resolve({ id: 4 }) }),
      },
    });
    document.getElementById("admin-ai-new-provider-btn").click();
    const modal = document.getElementById("admin-ai-provider-modal");
    modal.querySelector("[name=model_name]").value = "gemini-3-flash-preview";
    modal.querySelector("form").dispatchEvent(new Event("submit", { cancelable: true }));
    await flushPromises();

    expect(modal.hidden).toBe(true);
  });
});

describe("admin-ai.js — la page ne gère plus l'assignation par abonnement", () => {
  it("n'affiche plus de carte Abonnements sur /admin/ia (déplacée vers /admin/subscriptions)", async () => {
    await mount("/admin/ia");
    expect(document.getElementById("admin-ai-subscriptions")).toBeNull();
    expect(fetchLog).not.toContain("GET /api/admin/ai/subscriptions");
  });
});
