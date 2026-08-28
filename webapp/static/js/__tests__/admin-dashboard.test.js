// admin-dashboard.js : Dashboard administrateur (/admin). Couvre en
// particulier la ligne "Erreurs serveur" ajoutée sous la carte Santé système
// (Chantier Administrateur, P1) — réutilise metrics_service.in_memory_snapshot()
// côté backend (voir test_admin_dashboard_service.py), jamais une fenêtre
// glissante de 24h fabriquée (le libellé dit explicitement "depuis le
// dernier redémarrage").
//
// Chantier Administrateur "Tri des informations" (Phase 2) : comparaison
// "hier" de la carte Utilisateurs actifs, badge "Erreurs serveur" repositionné
// (n'est plus une phrase libre en sous-texte) et les 2 nouvelles alertes
// ponctuelles avec lien "Voir les détails" (paiements en échec / consentements
// parentaux en attente).
import { describe, it, expect, vi, afterEach } from "vitest";
import { loadPageBody, flushPromises } from "./testUtils.js";

const NAV_WITH_DASHBOARD = [
  { id: "dashboard", label: "Dashboard", icon: "🏠", path: "/admin", implemented: true },
];

function snapshot(overrides = {}) {
  return {
    cards: {
      active_users_today: { available: true, value: { today: 12, yesterday: 5, delta: 7 } },
      ai_providers_status: { available: true, value: [{ name: "Gemini Flash", enabled: true, last_success: "2026-08-25T10:00:00+00:00", last_failure: null }] },
      health_status: { available: true, value: { total_services: 3, ok_count: 3, down_count: 0, degraded_count: 0, global_status: "ok" } },
      support_status: { available: true, value: { open_count: 0, total_count: 5 } },
      server_errors: { available: true, value: { total_requests: 250, total_errors: 0, avg_request_duration_ms: 42.1 } },
      ...overrides,
    },
    alerts: { available: true, value: [] },
  };
}

function mockFetchWith(dashboardPayload) {
  global.fetch = vi.fn((url) => {
    if (url === "/api/admin/me") {
      return Promise.resolve({ ok: true, json: () => Promise.resolve({ name: "Mehdi", email: "a@b.c", role: "super_admin", avatar: null }) });
    }
    if (url === "/api/admin/nav") {
      return Promise.resolve({ ok: true, json: () => Promise.resolve({ modules: NAV_WITH_DASHBOARD }) });
    }
    if (url === "/api/admin/dashboard") {
      return Promise.resolve({ ok: true, json: () => Promise.resolve(dashboardPayload) });
    }
    return Promise.resolve({ ok: false, status: 404, json: () => Promise.resolve({ error: "not found" }) });
  });
}

async function mount(dashboardPayload) {
  window.history.pushState({}, "", "/admin");
  document.body.innerHTML = loadPageBody("admin.html");
  document.cookie = "nm_csrf=test-csrf-token";
  mockFetchWith(dashboardPayload);
  vi.resetModules();
  const { initAdminShell } = await import("../admin-shell.js");
  await initAdminShell();
  await flushPromises();
}

afterEach(() => {
  vi.restoreAllMocks();
  document.cookie = "nm_csrf=; expires=Thu, 01 Jan 1970 00:00:00 UTC";
});

describe("admin-dashboard.js — carte Santé système + badge erreurs serveur", () => {
  it("aucune erreur : message rassurant avec le nombre réel de requêtes, jamais un 0 nu", async () => {
    await mount(snapshot());
    const cardsEl = document.getElementById("admin-cards");
    expect(cardsEl.textContent).toContain("Erreurs serveur");
    expect(cardsEl.textContent).toContain("Aucune depuis le dernier redémarrage");
    expect(cardsEl.textContent).toContain("250 requêtes");
  });

  it("des erreurs réelles : affichées avec leur nombre exact, jamais masquées", async () => {
    await mount(snapshot({ server_errors: { available: true, value: { total_requests: 300, total_errors: 4, avg_request_duration_ms: 55 } } }));
    const cardsEl = document.getElementById("admin-cards");
    expect(cardsEl.textContent).toContain("4 depuis le dernier redémarrage");
    expect(cardsEl.textContent).toContain("300 requêtes");
  });

  it("aucune requête enregistrée : libellé honnête, pas de 0/0 fabriqué", async () => {
    await mount(snapshot({ server_errors: { available: true, value: { total_requests: 0, total_errors: 0, avg_request_duration_ms: null } } }));
    const cardsEl = document.getElementById("admin-cards");
    expect(cardsEl.textContent).toContain("Aucune requête enregistrée depuis le dernier redémarrage");
  });

  it("donnée indisponible : jamais de 0 fabriqué, aucune ligne affichée", async () => {
    await mount(snapshot({ server_errors: { available: false, value: null, reason: "test" } }));
    const cardsEl = document.getElementById("admin-cards");
    // Pas de sous-ligne du tout plutôt qu'une valeur inventée :
    expect(cardsEl.textContent).not.toMatch(/depuis le dernier redémarrage/);
  });

  it("ne devient jamais une grosse carte séparée : reste un badge secondaire de la carte Santé système existante", async () => {
    await mount(snapshot());
    const cardsEl = document.getElementById("admin-cards");
    const cardLabels = [...cardsEl.querySelectorAll(".admin-card-label")].map((n) => n.textContent);
    expect(cardLabels).toEqual(["Santé système", "Support", "IA", "Utilisateurs actifs"]);
  });

  it("le badge erreurs serveur est visuellement secondaire (pas le statut principal de la carte)", async () => {
    await mount(snapshot({ server_errors: { available: true, value: { total_requests: 300, total_errors: 4, avg_request_duration_ms: 55 } } }));
    const cardsEl = document.getElementById("admin-cards");
    const healthCard = [...cardsEl.querySelectorAll(".admin-card")].find((c) => c.textContent.includes("Santé système"));
    const badge = healthCard.querySelector(".admin-badge--error");
    expect(badge).not.toBeNull();
    expect(badge.textContent).toContain("4 depuis le dernier redémarrage");
  });
});

describe("admin-dashboard.js — carte Utilisateurs actifs (comparaison avec hier)", () => {
  it("variation positive : affichée avec un signe +", async () => {
    await mount(snapshot({ active_users_today: { available: true, value: { today: 127, yesterday: 115, delta: 12 } } }));
    const cardsEl = document.getElementById("admin-cards");
    expect(cardsEl.textContent).toContain("127");
    expect(cardsEl.textContent).toContain("+12 vs hier");
  });

  it("variation négative : affichée avec un signe moins, jamais masquée", async () => {
    await mount(snapshot({ active_users_today: { available: true, value: { today: 40, yesterday: 48, delta: -8 } } }));
    const cardsEl = document.getElementById("admin-cards");
    expect(cardsEl.textContent).toContain("40");
    expect(cardsEl.textContent).toContain("−8 vs hier");
  });

  it("aucune variation : 0 explicite, pas de signe trompeur", async () => {
    await mount(snapshot({ active_users_today: { available: true, value: { today: 20, yesterday: 20, delta: 0 } } }));
    const cardsEl = document.getElementById("admin-cards");
    expect(cardsEl.textContent).toContain("0 vs hier");
  });

  it("personne d'actif hier : delta reste calculable (= aujourd'hui), jamais une comparaison manquante", async () => {
    await mount(snapshot({ active_users_today: { available: true, value: { today: 6, yesterday: 0, delta: 6 } } }));
    const cardsEl = document.getElementById("admin-cards");
    expect(cardsEl.textContent).toContain("6");
    expect(cardsEl.textContent).toContain("+6 vs hier");
  });

  it("donnée indisponible : jamais de valeur fabriquée", async () => {
    await mount(snapshot({ active_users_today: { available: false, value: null, reason: "test" } }));
    const cardsEl = document.getElementById("admin-cards");
    expect(cardsEl.textContent).toContain("Aucune donnée disponible");
    expect(cardsEl.textContent).not.toContain("vs hier");
  });
});

describe("admin-dashboard.js — alertes ponctuelles (paiements / consentements parentaux)", () => {
  it("alerte paiements en échec : affichée avec un lien vers Abonnements", async () => {
    await mount({
      ...snapshot(),
      alerts: {
        available: true,
        value: [{ level: "warning", code: "paiements_en_echec", message: "3 abonnement(s) en échec de paiement.", link: { path: "/admin/subscriptions", label: "Voir les abonnements" } }],
      },
    });
    const activityEl = document.getElementById("admin-activity-body");
    expect(activityEl.textContent).toContain("3 abonnement(s) en échec de paiement.");
    const link = [...activityEl.querySelectorAll(".admin-card-link-btn")].find((b) => b.textContent.includes("Voir les abonnements"));
    expect(link).not.toBeUndefined();
  });

  it("alerte consentements parentaux : affichée avec un lien vers Utilisateurs", async () => {
    await mount({
      ...snapshot(),
      alerts: {
        available: true,
        value: [{ level: "warning", code: "consentement_parental_attente", message: "4 compte(s) en attente de consentement parental.", link: { path: "/admin/users", label: "Voir les utilisateurs" } }],
      },
    });
    const activityEl = document.getElementById("admin-activity-body");
    expect(activityEl.textContent).toContain("4 compte(s) en attente de consentement parental.");
    const link = [...activityEl.querySelectorAll(".admin-card-link-btn")].find((b) => b.textContent.includes("Voir les utilisateurs"));
    expect(link).not.toBeUndefined();
  });

  it("aucune alerte quand la liste est vide : aucun compteur à 0 affiché", async () => {
    await mount(snapshot());
    const activityEl = document.getElementById("admin-activity-body");
    expect(activityEl.textContent).toContain("Aucune alerte aujourd'hui.");
    expect(activityEl.textContent).not.toMatch(/échec de paiement|consentement parental/);
  });

  it("alerte sans lien (alertes de tendance existantes) : aucun bouton, comportement inchangé", async () => {
    await mount({
      ...snapshot(),
      alerts: {
        available: true,
        value: [{ level: "critical", code: "hausse_erreurs", message: "Erreurs IA en hausse de 80%." }],
      },
    });
    const activityEl = document.getElementById("admin-activity-body");
    expect(activityEl.textContent).toContain("Erreurs IA en hausse de 80%.");
    expect(activityEl.querySelector(".admin-card-link-btn")).toBeNull();
  });
});
