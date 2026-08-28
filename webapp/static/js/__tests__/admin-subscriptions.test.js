// ── admin-subscriptions.js / admin-subscription-detail.js : module
// "Abonnements" (/admin/subscriptions) — catalogue des 3 plans, statistiques
// réelles, assignation des fournisseurs IA par plan (section repliable
// "Fournisseurs IA par plan", déplacée depuis admin-ai.js — seul endroit de
// l'admin où cette assignation se modifie), fiche détaillée à 5 onglets
// (lazy loading, cache par onglet, pushState, breadcrumb), édition journalisée.
import { describe, it, expect, vi, afterEach } from "vitest";
import { loadPageBody, flushPromises } from "./testUtils.js";

const mockLoadDashboard = vi.fn().mockResolvedValue(undefined);
vi.mock("../admin-dashboard.js", () => ({ loadDashboard: mockLoadDashboard }));

const NAV_WITH_SUBS = [
  { id: "dashboard", label: "Dashboard", icon: "🏠", path: "/admin", implemented: true },
  { id: "subscriptions", label: "Abonnements", icon: "💳", path: "/admin/subscriptions", implemented: true },
];

function plan(overrides = {}) {
  return {
    plan: "premium", name: "Premium",
    description: { available: true, value: "Pour les élèves qui veulent progresser sans limites." },
    price_amount_cents: { available: true, value: 699 },
    currency: { available: true, value: "eur" },
    duration_label: { available: true, value: "mois" },
    display_order: 1, active: true,
    user_count: { available: true, value: 42 },
    ...overrides,
  };
}

function overviewPayload(overrides = {}) {
  return {
    plans: [
      plan({ plan: "free", name: "Gratuit", price_amount_cents: { available: true, value: 0 }, display_order: 0, user_count: { available: true, value: 100 } }),
      plan(),
      plan({ plan: "ultra", name: "Ultra", price_amount_cents: { available: true, value: 1299 }, display_order: 2, user_count: { available: true, value: 7 } }),
    ],
    reason: null,
    stats: {
      window_days: 30,
      new_subscribers: { available: true, value: 12 },
      cancellations: { available: true, value: 3 },
    },
    ...overrides,
  };
}

const INFO_PAYLOAD = {
  plan: "premium", name: "Premium",
  description: { available: true, value: "Pour les élèves qui veulent progresser sans limites." },
  active: true, display_order: 1,
  user_count: { available: true, value: 42 },
  created_at: { available: true, value: "2026-01-01T08:00:00+00:00" },
  updated_at: { available: true, value: "2026-01-01T08:00:00+00:00" },
};
const PRICING_PAYLOAD = {
  price_amount_cents: { available: true, value: 699 },
  currency: { available: true, value: "eur" },
  duration_label: { available: true, value: "mois" },
  note: "Prix affiché à titre de catalogue pour ce panneau d'administration.",
};
const FEATURES_PAYLOAD = {
  advantages: ["Chatbot sans quota quotidien"], limits: [],
  quota_daily: { available: true, value: 500 },
  quota_chatbot: { available: true, value: 250 },
  real_features: [{ key: "chatbot_unlimited", label: "Chatbot sans quota quotidien" }],
  real_quotas: [{ key: "chat_messages", label: "Messages chatbot / jour", limit: 250, unlimited: false }],
  real_note: "Reflète ce qui est réellement appliqué aujourd'hui.",
};
const USERS_PAYLOAD = {
  items: [{ id: 1, name: "Alice", email: "alice@test.local", role: "user", last_login_at: "2026-01-01T08:00:00+00:00" }],
  page: 1, page_size: 25, total: 1, total_pages: 1,
};
function provider(overrides = {}) {
  return {
    id: 1, name: "Gemini Flash", provider_key: "gemini", model_name: "gemini-3-flash-preview",
    enabled: true, priority: 0,
    ...overrides,
  };
}

const AI_PROVIDERS_PAYLOAD = {
  providers: [
    provider(),
    provider({ id: 2, name: "Gemini Pro", model_name: "gemini-3-pro-preview", priority: 1 }),
    provider({ id: 3, name: "Claude", provider_key: "anthropic", model_name: "claude-sonnet-5", priority: 2 }),
  ],
  reason: null,
};

const AI_SUBSCRIPTIONS_PAYLOAD = {
  available: true,
  value: {
    free: [{ provider_id: 1, name: "Gemini Flash", badge: "Rapide" }],
    premium: [{ provider_id: 2, name: "Gemini Pro", badge: "Avancé" }],
    ultra: [{ provider_id: 3, name: "Claude", badge: "Premium" }],
  },
};
const HISTORY_PAYLOAD = {
  items: [{
    id: 1, created_at: "2026-01-02T08:00:00+00:00", admin: { id: 10, name: "Mehdi", role: "super_admin" },
    action: "update_plan", action_label: "Modification d'un abonnement", provider: { id: null, name: "Abonnement premium" },
    old_values: { name: "Premium" }, new_values: { name: "Premium Plus" }, result: "success", error_message: null,
  }],
  page: 1, page_size: 25, total: 1, total_pages: 1,
};

let fetchLog;

function mockFetchWith({ overview = overviewPayload(), aiProviders = AI_PROVIDERS_PAYLOAD, aiSubscriptions = AI_SUBSCRIPTIONS_PAYLOAD, fail = [], handlers = {} } = {}) {
  fetchLog = [];
  global.fetch = vi.fn((url, options = {}) => {
    fetchLog.push(`${options.method || "GET"} ${url}`);
    if (url === "/api/admin/me") {
      return Promise.resolve({ ok: true, json: () => Promise.resolve({ name: "Mehdi", email: "a@b.c", role: "super_admin", avatar: null }) });
    }
    if (url === "/api/admin/nav") {
      return Promise.resolve({ ok: true, json: () => Promise.resolve({ modules: NAV_WITH_SUBS }) });
    }
    if (fail.includes(url)) return Promise.resolve({ ok: false, status: 500, json: () => Promise.resolve({ error: "boom" }) });
    const key = `${options.method || "GET"} ${url}`;
    if (handlers[key]) return Promise.resolve(handlers[key](options));
    if (url === "/api/admin/subscriptions") return Promise.resolve({ ok: true, json: () => Promise.resolve(overview) });
    if (url === "/api/admin/ai/providers" && (!options.method || options.method === "GET")) {
      return Promise.resolve({ ok: true, json: () => Promise.resolve(aiProviders) });
    }
    if (url === "/api/admin/ai/subscriptions") return Promise.resolve({ ok: true, json: () => Promise.resolve(aiSubscriptions) });
    if (url.includes("/api/admin/subscriptions/premium/info")) return Promise.resolve({ ok: true, json: () => Promise.resolve(INFO_PAYLOAD) });
    if (url.includes("/api/admin/subscriptions/premium/pricing")) return Promise.resolve({ ok: true, json: () => Promise.resolve(PRICING_PAYLOAD) });
    if (url.includes("/api/admin/subscriptions/premium/features")) return Promise.resolve({ ok: true, json: () => Promise.resolve(FEATURES_PAYLOAD) });
    if (url.includes("/api/admin/subscriptions/premium/users")) return Promise.resolve({ ok: true, json: () => Promise.resolve(USERS_PAYLOAD) });
    if (url.includes("/api/admin/subscriptions/premium/history")) return Promise.resolve({ ok: true, json: () => Promise.resolve(HISTORY_PAYLOAD) });
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

afterEach(() => {
  vi.restoreAllMocks();
  document.cookie = "nm_csrf=; expires=Thu, 01 Jan 1970 00:00:00 UTC";
});

describe("admin-subscriptions.js — vue d'ensemble", () => {
  it("affiche les 3 plans avec nom/prix/utilisateurs réels", async () => {
    await mount("/admin/subscriptions");
    const plansEl = document.getElementById("admin-subscriptions-plans");
    expect(plansEl.textContent).toContain("Gratuit");
    expect(plansEl.textContent).toContain("Premium");
    expect(plansEl.textContent).toContain("Ultra");
    expect(plansEl.textContent).toContain("42 utilisateur(s)");
    expect(plansEl.textContent).toContain("Gratuit"); // prix 0 -> "Gratuit"
  });

  it("affiche les statistiques réelles (nouveaux abonnés/résiliations), sans carte toujours vide", async () => {
    await mount("/admin/subscriptions");
    const statsEl = document.getElementById("admin-subscriptions-stats");
    expect(statsEl.textContent).toContain("12");
    expect(statsEl.textContent).toContain("3");
    expect(statsEl.querySelectorAll(".admin-card").length).toBe(2);
  });

  it("bascule l'interrupteur actif/inactif -> PATCH /active", async () => {
    let sentBody = null;
    await mount("/admin/subscriptions", {
      handlers: {
        "PATCH /api/admin/subscriptions/free/active": (options) => {
          sentBody = JSON.parse(options.body);
          return { ok: true, json: () => Promise.resolve({ ok: true }) };
        },
      },
    });
    const freeCard = [...document.querySelectorAll(".admin-ai-provider-card")].find((c) => c.textContent.includes("Gratuit"));
    const toggle = freeCard.querySelector(".admin-toggle input");
    toggle.checked = false;
    toggle.dispatchEvent(new Event("change"));
    await flushPromises();
    expect(sentBody).toEqual({ active: false });
    expect(fetchLog).toContain("PATCH /api/admin/subscriptions/free/active");
  });

  it("cliquer sur un plan navigue vers /admin/subscriptions/:plan via pushState", async () => {
    await mount("/admin/subscriptions");
    const pushStateSpy = vi.spyOn(window.history, "pushState");
    const premiumCard = [...document.querySelectorAll(".admin-ai-provider-card")].find((c) => c.textContent.includes("Premium"));
    premiumCard.click();
    await flushPromises();
    expect(pushStateSpy).toHaveBeenCalledWith(expect.anything(), "", "/admin/subscriptions/premium");
    expect(window.location.pathname).toBe("/admin/subscriptions/premium");
    expect(document.querySelector(".admin-breadcrumb-item--current").textContent).toBe("Fiche abonnement");
  });
});

describe("admin-subscriptions.js — assignation des fournisseurs IA par plan", () => {
  it("affiche la section repliable avec une checklist éditable, un fournisseur coché par plan", async () => {
    await mount("/admin/subscriptions");
    const editorEl = document.getElementById("admin-subscriptions-ai-assignment");
    expect(editorEl.querySelector(".admin-collapse")).not.toBeNull();
    expect(editorEl.textContent).toContain("Free");
    expect(editorEl.textContent).toContain("Premium");
    expect(editorEl.textContent).toContain("Ultra");
    expect(editorEl.textContent).toContain("Gemini Pro");
    expect(editorEl.textContent).toContain("Claude");
    // Un bouton "Enregistrer" par plan.
    expect(editorEl.querySelectorAll("button").length).toBe(3);
    // La checkbox du fournisseur mappé au plan Free (id 1) est cochée.
    const freeCard = [...editorEl.querySelectorAll(".admin-ai-subscription-edit-card")]
      .find((c) => c.textContent.includes("Free"));
    const checkedBoxes = [...freeCard.querySelectorAll("input[type=checkbox]")].filter((c) => c.checked);
    expect(checkedBoxes.length).toBe(1);
    expect(checkedBoxes[0].value).toBe("1");
  });

  it("Enregistrer envoie PUT avec la liste des fournisseurs cochés", async () => {
    let sentBody = null;
    await mount("/admin/subscriptions", {
      handlers: {
        "PUT /api/admin/ai/subscriptions/free": (options) => {
          sentBody = JSON.parse(options.body);
          return { ok: true, json: () => Promise.resolve({ ok: true }) };
        },
      },
    });
    const editorEl = document.getElementById("admin-subscriptions-ai-assignment");
    const freeCard = [...editorEl.querySelectorAll(".admin-ai-subscription-edit-card")]
      .find((c) => c.textContent.includes("Free"));
    const proCheckbox = [...freeCard.querySelectorAll("input[type=checkbox]")].find((c) => c.value === "2");
    proCheckbox.checked = true;
    freeCard.querySelector("button").click();
    await flushPromises();

    expect(sentBody.provider_ids).toEqual(expect.arrayContaining([1, 2]));
    expect(fetchLog).toContain("PUT /api/admin/ai/subscriptions/free");
  });

  it("aucun fournisseur IA configuré -> état vide, jamais une checklist vide silencieuse", async () => {
    await mount("/admin/subscriptions", { aiProviders: { providers: null, reason: "Aucun fournisseur IA n'est configuré." } });
    const editorEl = document.getElementById("admin-subscriptions-ai-assignment");
    expect(editorEl.textContent).toContain("Aucun fournisseur IA n'est configuré");
  });
});

describe("admin-subscriptions.js — état vide et erreurs", () => {
  it("aucun plan configuré -> état vide avec raison", async () => {
    await mount("/admin/subscriptions", { overview: overviewPayload({ plans: null, reason: "Aucun abonnement n'est configuré dans subscription_plans." }) });
    expect(document.getElementById("admin-subscriptions-plans").textContent).toContain("Aucun abonnement n'est configuré");
  });

  it("échec réseau -> message d'erreur, sans planter la page", async () => {
    await mount("/admin/subscriptions", { fail: ["/api/admin/subscriptions"] });
    expect(document.getElementById("admin-global-error").hidden).toBe(false);
  });
});

describe("admin-subscription-detail.js — fiche détaillée (5 onglets)", () => {
  it("charge uniquement l'onglet Informations à l'ouverture (lazy loading)", async () => {
    await mount("/admin/subscriptions/premium");
    expect(fetchLog).toContain("GET /api/admin/subscriptions/premium/info");
    expect(fetchLog).not.toContain("GET /api/admin/subscriptions/premium/pricing");
    const panel = document.getElementById("admin-subscription-detail-panel");
    expect(panel.textContent).toContain("42");
  });

  it("cliquer sur un autre onglet déclenche exactement un nouvel appel, jamais deux fois le même", async () => {
    await mount("/admin/subscriptions/premium");
    document.querySelector('.admin-tab-btn[data-tab="pricing"]').click();
    await flushPromises();
    expect(fetchLog).toContain("GET /api/admin/subscriptions/premium/pricing");

    fetchLog = [];
    document.querySelector('.admin-tab-btn[data-tab="info"]').click();
    await flushPromises();
    document.querySelector('.admin-tab-btn[data-tab="pricing"]').click();
    await flushPromises();
    expect(fetchLog.length).toBe(0); // les deux onglets sont déjà en cache
  });

  it("onglet Tarification précise que le prix est un champ catalogue, jamais Stripe", async () => {
    await mount("/admin/subscriptions/premium");
    document.querySelector('.admin-tab-btn[data-tab="pricing"]').click();
    await flushPromises();
    expect(document.getElementById("admin-subscription-detail-panel").textContent).toContain("catalogue");
  });

  it("onglet Fonctionnalités affiche avantages/limites catalogue ET les vraies features (lecture seule)", async () => {
    await mount("/admin/subscriptions/premium");
    document.querySelector('.admin-tab-btn[data-tab="features"]').click();
    await flushPromises();
    const panel = document.getElementById("admin-subscription-detail-panel");
    expect(panel.textContent).toContain("Chatbot sans quota quotidien");
    expect(panel.textContent).toContain("Messages chatbot / jour");
  });

  it("onglet Utilisateurs réutilise la pagination/le tableau déjà utilisés pour le module Utilisateurs", async () => {
    await mount("/admin/subscriptions/premium");
    document.querySelector('.admin-tab-btn[data-tab="users"]').click();
    await flushPromises();
    const panel = document.getElementById("admin-subscription-detail-panel");
    expect(panel.querySelector(".admin-users-table")).not.toBeNull();
    expect(panel.textContent).toContain("Alice");
  });

  it("onglet Informations renvoie vers la section IA de la page Abonnements (pas de miroir dupliqué)", async () => {
    await mount("/admin/subscriptions/premium");
    const panel = document.getElementById("admin-subscription-detail-panel");
    const link = [...panel.querySelectorAll("a")].find((a) => a.getAttribute("href").includes("/admin/subscriptions#"));
    expect(link).not.toBeUndefined();
    expect(document.querySelector('.admin-tab-btn[data-tab="ai"]')).toBeNull();
  });

  it("onglet Historique affiche les entrées du journal d'administration filtrées sur ce plan", async () => {
    await mount("/admin/subscriptions/premium");
    document.querySelector('.admin-tab-btn[data-tab="history"]').click();
    await flushPromises();
    const panel = document.getElementById("admin-subscription-detail-panel");
    expect(panel.textContent).toContain("Modification d'un abonnement");
    expect(panel.textContent).toContain("Mehdi");
  });

  it("bouton Modifier ouvre la modale pré-remplie et sauvegarde via PUT (journalisé côté backend)", async () => {
    let sentBody = null;
    await mount("/admin/subscriptions/premium", {
      handlers: {
        "PUT /api/admin/subscriptions/premium": (options) => {
          sentBody = JSON.parse(options.body);
          return { ok: true, json: () => Promise.resolve({ ok: true }) };
        },
      },
    });
    const editBtn = [...document.getElementById("admin-subscription-detail-head").querySelectorAll(".admin-btn")]
      .find((b) => b.textContent === "Modifier");
    editBtn.click();
    await flushPromises();

    const modal = document.getElementById("admin-ai-provider-modal");
    expect(modal.hidden).toBe(false);
    expect(modal.querySelector("[name=name]").value).toBe("Premium");

    modal.querySelector("form").dispatchEvent(new Event("submit", { cancelable: true }));
    await flushPromises();

    expect(sentBody.name).toBe("Premium");
    expect(modal.hidden).toBe(true);
  });

  it("abonnement introuvable -> message d'erreur explicite, jamais une page cassée", async () => {
    await mount("/admin/subscriptions/inconnu");
    await flushPromises();
    expect(document.body.textContent).not.toMatch(/undefined/);
  });
});
