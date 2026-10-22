// ── admin-finance.js : module "Finance" (/admin/finance), Phase 2A de
// l'audit admin (2026-10-21). Couvre : chargement automatique des
// abonnements/MRR (local), garde-fou Stripe production (bouton désactivé/
// confirmation demandée, identique en esprit au module Abonnements),
// affichage des revenus/paiements, erreurs explicites (jamais un montant à
// 0 € silencieux).
import { describe, it, expect, vi, afterEach } from "vitest";
import { loadPageBody, flushPromises } from "./testUtils.js";

const mockLoadDashboard = vi.fn().mockResolvedValue(undefined);
vi.mock("../admin-dashboard.js", () => ({ loadDashboard: mockLoadDashboard }));

const NAV_WITH_FINANCE = [
  { id: "dashboard", label: "Dashboard", icon: "🏠", path: "/admin", implemented: true },
  { id: "finance", label: "Finance", icon: "💰", path: "/admin/finance", implemented: true },
];

function overview(overrides = {}) {
  return {
    stripe_environment: {
      mode: "test",
      app_environment: "developpement",
      reconciliation_blocked: false,
      reconciliation_requires_confirmation: false,
    },
    subscriptions: {
      window_days: 30,
      active_subscriptions_by_plan: { available: true, value: { premium: 10, ultra: 3 }, note: "note" },
      past_due_or_unpaid: { available: true, value: 2 },
      canceled: { available: true, value: 5 },
      new_subscriptions: { available: true, value: 4 },
      cancellations: { available: true, value: 1 },
      mrr_cents: { available: true, value: 10986, note: "estimation" },
    },
    ...overrides,
  };
}

let fetchLog;

function mockFetchWith({ overviewPayload = overview(), fail = [], handlers = {} } = {}) {
  fetchLog = [];
  global.fetch = vi.fn((url, options = {}) => {
    fetchLog.push(`${options.method || "GET"} ${url}`);
    if (url === "/api/admin/me") {
      return Promise.resolve({
        ok: true,
        json: () => Promise.resolve({ name: "Mehdi", email: "a@b.c", role: "super_admin", avatar: null }),
      });
    }
    if (url === "/api/admin/nav") {
      return Promise.resolve({ ok: true, json: () => Promise.resolve({ modules: NAV_WITH_FINANCE }) });
    }
    if (fail.includes(url))
      return Promise.resolve({ ok: false, status: 500, json: () => Promise.resolve({ error: "boom" }) });
    // Comparaison sur le chemin SANS la query string : "/revenue" et
    // "/revenue/series" partagent un préfixe mais ne doivent jamais être
    // confondus (contrairement à un simple startsWith).
    const path = url.split("?")[0];
    if (handlers[path]) return Promise.resolve(handlers[path](url));
    if (url === "/api/admin/finance/overview")
      return Promise.resolve({ ok: true, json: () => Promise.resolve(overviewPayload) });
    return Promise.resolve({ ok: false, status: 404, json: () => Promise.resolve({ error: "not found" }) });
  });
}

async function mount(options) {
  window.history.pushState({}, "", "/admin/finance");
  document.body.innerHTML = loadPageBody("admin.html");
  mockFetchWith(options);
  vi.resetModules();
  mockLoadDashboard.mockClear();
  const { initAdminShell } = await import("../admin-shell.js");
  await initAdminShell();
  await flushPromises();
}

afterEach(() => {
  vi.restoreAllMocks();
});

describe("admin-finance.js — vue d'ensemble (local, automatique)", () => {
  it("affiche les abonnements actifs par plan et le MRR estimé", async () => {
    await mount();
    const subsEl = document.getElementById("admin-finance-subscriptions");
    expect(subsEl.textContent).toContain("10");
    expect(subsEl.textContent).toContain("3");
    expect(subsEl.textContent).toContain("MRR estimé");
  });

  it("affiche la source de données (mode Stripe + environnement serveur)", async () => {
    await mount();
    const envEl = document.getElementById("admin-finance-stripe-environment");
    expect(envEl.textContent).toMatch(/mode TEST/);
    expect(envEl.textContent).toMatch(/développement/);
  });

  it("affiche l'heure de dernière actualisation", async () => {
    await mount();
    expect(document.getElementById("admin-finance-last-refresh").textContent).toMatch(/Dernière actualisation/);
  });

  it("échec réseau -> message d'erreur + bouton Réessayer, jamais une page cassée", async () => {
    await mount({ fail: ["/api/admin/finance/overview"] });
    expect(document.getElementById("admin-global-error").hidden).toBe(false);
    expect(document.getElementById("admin-finance-retry-btn").hidden).toBe(false);
  });

  it("une donnée locale indisponible affiche la raison, jamais un 0 silencieux", async () => {
    await mount({
      overviewPayload: overview({
        subscriptions: {
          ...overview().subscriptions,
          mrr_cents: { available: false, value: null, reason: "Catalogue non configuré." },
        },
      }),
    });
    const subsEl = document.getElementById("admin-finance-subscriptions");
    expect(subsEl.textContent).toContain("Catalogue non configuré");
  });
});

describe("admin-finance.js — garde-fou Stripe production (revenus/paiements)", () => {
  it("Stripe production + serveur développement : boutons désactivés, aucun appel réseau", async () => {
    await mount({
      overviewPayload: overview({
        stripe_environment: {
          mode: "production",
          app_environment: "developpement",
          reconciliation_blocked: true,
          reconciliation_requires_confirmation: false,
        },
      }),
    });
    const revenueBtn = document.getElementById("admin-finance-revenue-btn");
    const paymentsBtn = document.getElementById("admin-finance-payments-btn");
    expect(revenueBtn.disabled).toBe(true);
    expect(paymentsBtn.disabled).toBe(true);

    fetchLog = [];
    revenueBtn.click();
    paymentsBtn.click();
    await flushPromises();
    expect(fetchLog.some((l) => l.includes("/api/admin/finance/revenue"))).toBe(false);
    expect(fetchLog.some((l) => l.includes("/api/admin/finance/payments"))).toBe(false);
  });

  // Audit admin (2026-10-22), bug corrigé : auparavant, "non_configure"/
  // "etat_inconnu" n'étaient PAS traités comme "reconciliation_blocked" au
  // chargement — le sélecteur de période et le bouton Revenus restaient
  // actifs, menant à un 501 après clic, avec un graphique vide de 240px
  // affiché en permanence. Ces 2 tests couvrent le nouveau comportement :
  // désactivation dès le chargement, sélecteur masqué, pas de zone de
  // graphique vide réservée.
  it("Stripe non configuré (mode non_configure) : boutons désactivés dès le chargement, période masquée, pas de 240px vide", async () => {
    await mount({
      overviewPayload: overview({
        stripe_environment: {
          mode: "non_configure",
          app_environment: "developpement",
          reconciliation_blocked: false,
          reconciliation_requires_confirmation: false,
        },
      }),
    });
    const revenueBtn = document.getElementById("admin-finance-revenue-btn");
    const paymentsBtn = document.getElementById("admin-finance-payments-btn");
    const controls = document.getElementById("admin-finance-revenue-controls");
    const unavailable = document.getElementById("admin-finance-revenue-unavailable");
    const chartBox = document.getElementById("admin-finance-revenue-chart");

    expect(revenueBtn.disabled).toBe(true);
    expect(paymentsBtn.disabled).toBe(true);
    expect(controls.hidden).toBe(true);
    expect(unavailable.hidden).toBe(false);
    expect(unavailable.textContent).toMatch(/pas configuré/);
    // Le conteneur du graphique ne porte jamais la classe qui réserve 240px
    // tant qu'aucune série n'a été réellement rendue.
    expect(chartBox.classList.contains("admin-health-chart-box")).toBe(false);

    fetchLog = [];
    revenueBtn.click();
    paymentsBtn.click();
    await flushPromises();
    expect(fetchLog.some((l) => l.includes("/api/admin/finance/revenue"))).toBe(false);
    expect(fetchLog.some((l) => l.includes("/api/admin/finance/payments"))).toBe(false);
  });

  it("Stripe en état inconnu (mode etat_inconnu) : même traitement que non_configure, sans bouton Réessayer", async () => {
    await mount({
      overviewPayload: overview({
        stripe_environment: {
          mode: "etat_inconnu",
          app_environment: "developpement",
          reconciliation_blocked: false,
          reconciliation_requires_confirmation: false,
        },
      }),
    });
    const revenueBtn = document.getElementById("admin-finance-revenue-btn");
    const unavailable = document.getElementById("admin-finance-revenue-unavailable");
    expect(revenueBtn.disabled).toBe(true);
    expect(unavailable.hidden).toBe(false);
    expect(unavailable.textContent).toMatch(/aucun préfixe reconnu/);
    // Pas de bouton "Réessayer" dans ce bloc compact : ni non_configure ni
    // etat_inconnu ne sont des erreurs transitoires.
    expect(unavailable.querySelector("button")).toBeNull();

    const envEl = document.getElementById("admin-finance-stripe-environment");
    expect(envEl.textContent).toMatch(/aucun préfixe reconnu/);
  });

  it("3ᵉ état de la bannière Source des données pour mode non_configure", async () => {
    await mount({
      overviewPayload: overview({
        stripe_environment: {
          mode: "non_configure",
          app_environment: "developpement",
          reconciliation_blocked: false,
          reconciliation_requires_confirmation: false,
        },
      }),
    });
    const envEl = document.getElementById("admin-finance-stripe-environment");
    expect(envEl.textContent).toMatch(/non configuré/);
    expect(envEl.querySelector(".admin-form-hint--warning")).not.toBeNull();
    expect(envEl.textContent).toMatch(/Revenus\/Paiements|revenus\/paiements/);
  });

  it("non-régression : Stripe en mode test (accessible) -> contrôles Revenus visibles, boutons actifs", async () => {
    await mount({
      overviewPayload: overview({
        stripe_environment: {
          mode: "test",
          app_environment: "developpement",
          reconciliation_blocked: false,
          reconciliation_requires_confirmation: false,
        },
      }),
    });
    const revenueBtn = document.getElementById("admin-finance-revenue-btn");
    const paymentsBtn = document.getElementById("admin-finance-payments-btn");
    const controls = document.getElementById("admin-finance-revenue-controls");
    const unavailable = document.getElementById("admin-finance-revenue-unavailable");
    expect(revenueBtn.disabled).toBe(false);
    expect(paymentsBtn.disabled).toBe(false);
    expect(controls.hidden).toBe(false);
    expect(unavailable.hidden).toBe(true);
  });

  it("Stripe production + serveur production : confirmation demandée avant tout appel réseau", async () => {
    const confirmSpy = vi.spyOn(window, "confirm").mockReturnValue(false);
    await mount({
      overviewPayload: overview({
        stripe_environment: {
          mode: "production",
          app_environment: "production",
          reconciliation_blocked: false,
          reconciliation_requires_confirmation: true,
        },
      }),
    });
    const revenueBtn = document.getElementById("admin-finance-revenue-btn");
    fetchLog = [];
    revenueBtn.click();
    await flushPromises();
    expect(confirmSpy).toHaveBeenCalled();
    expect(fetchLog.some((l) => l.includes("/api/admin/finance/revenue"))).toBe(false);
  });

  it("confirmation acceptée : envoie confirmed=true au serveur", async () => {
    vi.spyOn(window, "confirm").mockReturnValue(true);
    await mount({
      overviewPayload: overview({
        stripe_environment: {
          mode: "production",
          app_environment: "production",
          reconciliation_blocked: false,
          reconciliation_requires_confirmation: true,
        },
      }),
      handlers: {
        "/api/admin/finance/revenue": () => ({
          ok: true,
          json: () =>
            Promise.resolve({
              mode: "production",
              window_days: 30,
              gross_revenue_cents_by_currency: {},
              gross_revenue_cents_by_plan: {},
              refunded_cents_by_currency: {},
              net_of_refunds_cents_by_currency: {},
              invoices_checked: 0,
              refunds_checked: 0,
              capped: false,
            }),
        }),
      },
    });
    document.getElementById("admin-finance-revenue-btn").click();
    await flushPromises();
    expect(fetchLog.some((l) => l.includes("confirmed=true"))).toBe(true);
  });
});

describe("admin-finance.js — revenus et paiements (Stripe, déclenchement manuel)", () => {
  it("clic sur Charger les revenus affiche brut/remboursé/net par devise", async () => {
    await mount({
      handlers: {
        "/api/admin/finance/revenue/series": () => ({
          ok: true,
          json: () => Promise.resolve({ series: [], capped: false }),
        }),
        "/api/admin/finance/revenue": () => ({
          ok: true,
          json: () =>
            Promise.resolve({
              mode: "test",
              window_days: 30,
              gross_revenue_cents_by_currency: { eur: 1998 },
              gross_revenue_cents_by_plan: { premium: 699, ultra: 1299 },
              refunded_cents_by_currency: { eur: 200 },
              net_of_refunds_cents_by_currency: { eur: 1798 },
              invoices_checked: 2,
              refunds_checked: 1,
              capped: false,
            }),
        }),
      },
    });
    document.getElementById("admin-finance-revenue-btn").click();
    await flushPromises();
    const resultEl = document.getElementById("admin-finance-revenue-result");
    expect(resultEl.textContent).toMatch(/19,98/);
    expect(resultEl.textContent).toMatch(/premium/);
  });

  it("rapport plafonné (capped) affiche un avertissement explicite", async () => {
    await mount({
      handlers: {
        "/api/admin/finance/revenue/series": () => ({
          ok: true,
          json: () => Promise.resolve({ series: [], capped: false }),
        }),
        "/api/admin/finance/revenue": () => ({
          ok: true,
          json: () =>
            Promise.resolve({
              mode: "test",
              window_days: 30,
              gross_revenue_cents_by_currency: { eur: 100 },
              gross_revenue_cents_by_plan: {},
              refunded_cents_by_currency: {},
              net_of_refunds_cents_by_currency: { eur: 100 },
              invoices_checked: 2000,
              refunds_checked: 0,
              capped: true,
            }),
        }),
      },
    });
    document.getElementById("admin-finance-revenue-btn").click();
    await flushPromises();
    expect(document.getElementById("admin-finance-revenue-result").textContent).toMatch(/incomplet/);
  });

  it("Stripe non configuré (501) sur le clic Revenus -> message explicite", async () => {
    await mount({
      handlers: {
        "/api/admin/finance/revenue": () => ({
          ok: false,
          status: 501,
          json: () => Promise.resolve({ error: "Stripe n'est pas configuré sur ce serveur." }),
        }),
      },
    });
    document.getElementById("admin-finance-revenue-btn").click();
    await flushPromises();
    expect(document.getElementById("admin-finance-revenue-result").textContent).toMatch(/Stripe n'est pas configuré/);
  });

  it("clic sur Charger les derniers paiements affiche la liste avec succès/échecs", async () => {
    await mount({
      handlers: {
        "/api/admin/finance/payments": () => ({
          ok: true,
          json: () =>
            Promise.resolve({
              mode: "test",
              payments: [{ id: "pi_1", amount: 699, currency: "eur", status: "succeeded", created: 1700000000 }],
              has_more: false,
              succeeded_count: 1,
              failed_count: 0,
            }),
        }),
      },
    });
    document.getElementById("admin-finance-payments-btn").click();
    await flushPromises();
    const resultEl = document.getElementById("admin-finance-payments-result");
    expect(resultEl.textContent).toMatch(/1 paiement\(s\) réussi/);
    expect(resultEl.querySelector("table")).not.toBeNull();
  });

  it("aucun paiement -> état vide explicite, jamais un tableau vide silencieux", async () => {
    await mount({
      handlers: {
        "/api/admin/finance/payments": () => ({
          ok: true,
          json: () =>
            Promise.resolve({ mode: "test", payments: [], has_more: false, succeeded_count: 0, failed_count: 0 }),
        }),
      },
    });
    document.getElementById("admin-finance-payments-btn").click();
    await flushPromises();
    expect(document.getElementById("admin-finance-payments-result").textContent).toMatch(/Aucun paiement/);
  });
});
